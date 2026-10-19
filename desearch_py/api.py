from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Any, AsyncIterator, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import quote
from uuid import UUID

import aiohttp
from pydantic import BaseModel, ValidationError

from .models import (
    DesearchCostMetadata,
    DesearchResponse,
    LinkedInProfileSearchFilters,
    LinkedInProfileSearchRequest,
    PeopleExportFormat,
    PeoplePlatform,
    PeopleProfileSort,
    PeopleProfilesPage,
    PeopleResultFilters,
    PeopleResultsPage,
    PeopleTask,
    PeopleTaskList,
    PeopleTaskStatus,
    Person,
    ResponseData,
    TikTokCreatorSearchFilters,
    TikTokCreatorSearchRequest,
    WebSearchResponse,
    XLinksSearchResponse,
    XProfileSearchFilters,
    XProfileSearchRequest,
    TwitterScraperTweet,
    WebSearchResultsResponse,
    XRetweetersResponse,
    XUserPostsResponse,
    XTrendsResponse,
    YouTubeCreatorSearchFilters,
    YouTubeCreatorSearchRequest,
    _enum_value,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.desearch.ai"


class DesearchAPIError(Exception):
    """HTTP error returned by the Desearch API.

    ``status`` is the HTTP status code and ``body`` is the response body.
    Request headers, including the API key, are never stored on this error.
    """

    def __init__(self, status: int, message: str = "", body: str = "") -> None:
        self.status = status
        self.message = message
        self.body = body
        super().__init__(status, message, body)

    def __str__(self) -> str:
        text = f"{self.status}, message={self.message!r}"
        if self.body:
            text += f", body={self.body!r}"
        return text

    def __repr__(self) -> str:
        return (
            f"{type(self).__name__}(status={self.status!r}, "
            f"message={self.message!r}, body={self.body!r})"
        )


class PeopleTaskConflictError(DesearchAPIError):
    """HTTP 409 from a People Search pause, resume or cancel call.

    The task is not in a state that allows the action. ``detail`` is the API's
    explanation and ``task`` is the task's current state from the response
    body (``None`` when the body could not be parsed).
    """

    def __init__(
        self,
        status: int,
        message: str = "",
        body: str = "",
        detail: str = "",
        task: Optional[PeopleTask] = None,
    ) -> None:
        super().__init__(status=status, message=message, body=body)
        self.detail = detail
        self.task = task


class PeopleTaskTimeoutError(TimeoutError):
    """Raised by ``wait_for_people_task`` when a task has not ended in time.

    ``task`` is the last state read. The search keeps running on the server;
    call ``cancel_people_task`` if you no longer need it.
    """

    def __init__(self, task: PeopleTask, timeout: float) -> None:
        self.task = task
        self.timeout = timeout
        super().__init__(
            f"People Search task {task.task_id} is still {task.status} "
            f"after {timeout:g} seconds"
        )


PeopleFiltersInput = Union[PeopleResultFilters, Dict[str, Any]]


def _raise_without_chain(exc: BaseException) -> None:
    """Raise ``exc`` with no ``__cause__`` and no ``__context__``.

    Call this only after the ``except`` block has finished. Raising inside the
    handler, even with ``from None``, still stores the original error on
    ``__context__``.
    """
    exc.__cause__ = None
    exc.__context__ = None
    exc.__suppress_context__ = True
    raise exc


class Desearch:
    """Async Python SDK client for the Desearch API."""

    def __init__(self, api_key: str, base_url: str = BASE_URL) -> None:
        """
        Initialize the Desearch client.

        Args:
            api_key (str): Your Desearch API key.
            base_url (str): Base URL for the API. Defaults to the production endpoint.
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.client: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.client is None or self.client.closed:
            self.client = aiohttp.ClientSession(
                headers={
                    "Authorization": self.api_key,
                    "Accept-Encoding": "gzip, deflate",
                }
            )
        return self.client

    async def __aenter__(self) -> Desearch:
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP session."""
        if self.client and not self.client.closed:
            await self.client.close()

    @staticmethod
    def _parse_float(value: Optional[str]) -> Optional[float]:
        if value is None:
            return None
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(parsed):
            return None
        return parsed

    @staticmethod
    def _parse_int(value: Optional[str]) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @classmethod
    def _extract_cost_metadata(cls, headers: Any) -> DesearchCostMetadata:
        """Parse optional Desearch per-request cost metadata from response headers."""
        return DesearchCostMetadata(
            cost_usd=cls._parse_float(headers.get("X-Desearch-Cost-Usd")),
            usage_count=cls._parse_int(headers.get("X-Desearch-Usage-Count")),
            service=headers.get("X-Desearch-Service"),
            currency=headers.get("X-Desearch-Currency"),
        )

    @staticmethod
    def _split_response(
        result: Any, include_metadata: bool
    ) -> Tuple[Any, Optional[DesearchCostMetadata]]:
        if include_metadata and isinstance(result, DesearchResponse):
            return result.data, result.metadata
        return result, None

    @staticmethod
    def _with_metadata(
        data: Any,
        metadata: Optional[DesearchCostMetadata],
        include_metadata: bool,
    ) -> Any:
        if include_metadata:
            return DesearchResponse(
                data=data, metadata=metadata or DesearchCostMetadata()
            )
        return data

    def _redact(self, value: Optional[str]) -> str:
        text = "" if value is None else str(value)
        secret = self.api_key
        if not secret or not text:
            return text
        return text.replace(secret, "[REDACTED]")

    def _make_api_error(
        self,
        status: int,
        message: Optional[str],
        body: Optional[str],
        method: str,
        url: str,
    ) -> DesearchAPIError:
        safe_message = self._redact(message)
        safe_body = self._redact(body)
        logger.error(
            "HTTP error %s for %s %s: %s",
            status,
            method,
            self._redact(url),
            safe_message,
        )
        return DesearchAPIError(status=status, message=safe_message, body=safe_body)

    async def _read_error_body(self, response: Any) -> str:
        reader = getattr(response, "text", None)
        if reader is None:
            return ""
        try:
            body = await reader()
        except Exception:
            return ""
        if body is None:
            return ""
        return body if isinstance(body, str) else str(body)

    async def _raise_if_http_error(self, response: Any, method: str, url: str) -> None:
        """Raise ``DesearchAPIError`` for HTTP statuses >= 400.

        Responses without ``status`` (test doubles) fall back to
        ``raise_for_status()``. A real aiohttp response always has ``status``,
        so this path reads the body and never builds ``ClientResponseError``.
        """
        status = getattr(response, "status", None)
        if status is None:
            response.raise_for_status()
            return
        if int(status) < 400:
            return
        body = await self._read_error_body(response)
        reason = getattr(response, "reason", "") or ""
        _raise_without_chain(
            self._make_api_error(int(status), str(reason), body, method, url)
        )

    def _api_error_from_client_response(
        self, exc: aiohttp.ClientResponseError, method: str, url: str
    ) -> DesearchAPIError:
        # ``repr(exc)`` includes request headers. Copy only status and reason.
        status = int(getattr(exc, "status", 0) or 0)
        message = getattr(exc, "message", "") or ""
        return self._make_api_error(status, str(message), "", method, url)

    async def _exchange(
        self,
        method: str,
        url: str,
        *,
        as_text: bool = False,
        **kwargs: Any,
    ) -> Tuple[Any, DesearchCostMetadata]:
        """Perform one request. HTTP failures raise ``DesearchAPIError`` with no chain."""
        client = await self._ensure_session()
        http_error: Optional[DesearchAPIError] = None
        try:
            async with client.request(
                method, url, timeout=aiohttp.ClientTimeout(total=120), **kwargs
            ) as response:
                await self._raise_if_http_error(response, method, url)
                metadata = self._extract_cost_metadata(response.headers)
                if as_text:
                    data = await response.text()
                else:
                    data = await response.json()
                return data, metadata
        except aiohttp.ClientResponseError as exc:
            # Raised only when a response has no status and raise_for_status()
            # built a ClientResponseError. Drop it so the key in its request
            # headers cannot survive on __cause__ or __context__.
            http_error = self._api_error_from_client_response(exc, method, url)
        except aiohttp.ClientError as exc:
            logger.error(
                "Client error for %s %s: %s",
                method,
                self._redact(url),
                self._redact(str(exc)),
            )
            raise
        if http_error is None:
            http_error = DesearchAPIError(
                status=0, message="HTTP request failed", body=""
            )
        _raise_without_chain(http_error)

    async def _handle_request(
        self,
        method: str,
        url: str,
        *,
        include_metadata: bool = False,
        **kwargs: Any,
    ) -> Any:
        """
        Send an HTTP request and return the parsed JSON response.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            url (str): Full request URL.
            include_metadata (bool): When true, wrap data with parsed response metadata.
            **kwargs: Additional arguments passed to the request.

        Returns:
            Any: Parsed JSON response, or DesearchResponse when metadata is requested.

        Raises:
            DesearchAPIError: On HTTP error responses. The API key is not included.
            aiohttp.ClientError: On connection-level errors.
        """
        data, metadata = await self._exchange(method, url, **kwargs)
        return self._with_metadata(data, metadata, include_metadata)

    async def _handle_text_request(
        self,
        path: str,
        *,
        params: Dict[str, Any],
        include_metadata: bool = False,
    ) -> Union[str, DesearchResponse[str]]:
        """Send a GET request for an endpoint that returns text or HTML.

        Raises:
            DesearchAPIError: On HTTP error responses. The API key is not included.
            aiohttp.ClientError: On connection-level errors.
        """
        request_url = f"{self.base_url}{path}"
        data, metadata = await self._exchange(
            "GET", request_url, as_text=True, params=params
        )
        return self._with_metadata(data, metadata, include_metadata)

    async def ai_search(
        self,
        prompt: str,
        tools: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_filter: Optional[str] = None,
        result_type: Optional[str] = "LINKS_WITH_FINAL_SUMMARY",
        system_message: Optional[str] = None,
        scoring_system_message: Optional[str] = None,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
        count: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[
        ResponseData,
        Dict[str, Any],
        DesearchResponse[Union[ResponseData, Dict[str, Any]]],
    ]:
        """
        AI-powered multi-source contextual search.

        Args:
            prompt (str): Search query prompt.
            tools (List[str]): List of tools to search with (e.g. web, twitter, reddit).
            start_date (Optional[str]): Start date in UTC (YYYY-MM-DDTHH:MM:SSZ).
            end_date (Optional[str]): End date in UTC (YYYY-MM-DDTHH:MM:SSZ).
            date_filter (Optional[str]): Deprecated relative window; the API translates it to start_date/end_date. Prefer start_date/end_date.
            result_type (Optional[str]): Result type (ONLY_LINKS or LINKS_WITH_FINAL_SUMMARY).
            system_message (Optional[str]): System message for the search.
            scoring_system_message (Optional[str]): System message for scoring the response.
            include_domains (Optional[List[str]]): Restrict Web Search results to these domains.
            exclude_domains (Optional[List[str]]): Drop Web Search results from these domains.
            count (Optional[int]): Number of results to return per source (10-200).

        Returns:
            Union[ResponseData, Dict[str, Any]]: Search results.
        """
        url = f"{self.base_url}/desearch/ai/search"
        payload = {
            k: v
            for k, v in {
                "prompt": prompt,
                "tools": tools,
                "start_date": start_date,
                "end_date": end_date,
                "date_filter": date_filter,
                "streaming": False,
                "result_type": result_type,
                "system_message": system_message,
                "scoring_system_message": scoring_system_message,
                "include_domains": include_domains,
                "exclude_domains": exclude_domains,
                "count": count,
            }.items()
            if v is not None
        }

        result = await self._handle_request(
            "POST", url, json=payload, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        parsed_data = data
        if isinstance(data, dict):
            try:
                parsed_data = ResponseData(**data)
            except Exception:
                parsed_data = data
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def ai_web_links_search(
        self,
        prompt: str,
        tools: List[str],
        count: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[WebSearchResponse, DesearchResponse[WebSearchResponse]]:
        """
        Search for raw links across web sources using AI.

        Args:
            prompt (str): Search query prompt.
            tools (List[str]): List of web tools to search with.
            count (Optional[int]): Number of results to return per source (10-200).

        Returns:
            WebSearchResponse: Structured link results from selected platforms.
        """
        url = f"{self.base_url}/desearch/ai/search/links/web"
        payload = {
            k: v
            for k, v in {
                "prompt": prompt,
                "tools": tools,
                "count": count,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "POST", url, json=payload, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            WebSearchResponse(**data), metadata, include_metadata
        )

    async def ai_x_links_search(
        self,
        prompt: str,
        count: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[XLinksSearchResponse, DesearchResponse[XLinksSearchResponse]]:
        """
        Search for X (Twitter) post links matching a prompt using AI.

        Args:
            prompt (str): Search query prompt.
            count (Optional[int]): Number of results to return (10-200).

        Returns:
            XLinksSearchResponse: Tweet objects matching the search.
        """
        url = f"{self.base_url}/desearch/ai/search/links/twitter"
        payload = {
            k: v
            for k, v in {
                "prompt": prompt,
                "count": count,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "POST", url, json=payload, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            XLinksSearchResponse(**data), metadata, include_metadata
        )

    async def x_search(
        self,
        query: str,
        sort: Optional[str] = "Top",
        user: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        lang: Optional[str] = None,
        verified: Optional[bool] = None,
        blue_verified: Optional[bool] = None,
        is_quote: Optional[bool] = None,
        is_video: Optional[bool] = None,
        is_image: Optional[bool] = None,
        min_retweets: Optional[Union[int, str]] = None,
        min_replies: Optional[Union[int, str]] = None,
        min_likes: Optional[Union[int, str]] = None,
        count: Optional[int] = 20,
        *,
        include_metadata: bool = False,
    ) -> Union[
        List[TwitterScraperTweet],
        Dict[str, Any],
        DesearchResponse[Union[List[TwitterScraperTweet], Dict[str, Any]]],
    ]:
        """
        Search X (Twitter) with extensive filtering options.

        Args:
            query (str): Advanced search query.
            sort (Optional[str]): Sort by 'Top' or 'Latest'.
            user (Optional[str]): User to search for.
            start_date (Optional[str]): Start date in UTC (YYYY-MM-DD).
            end_date (Optional[str]): End date in UTC (YYYY-MM-DD).
            lang (Optional[str]): Language code (e.g. en, es, fr).
            verified (Optional[bool]): Filter for verified users.
            blue_verified (Optional[bool]): Filter for blue checkmark verified users.
            is_quote (Optional[bool]): Include only tweets with quotes.
            is_video (Optional[bool]): Include only tweets with videos.
            is_image (Optional[bool]): Include only tweets with images.
            min_retweets (Optional[Union[int, str]]): Minimum number of retweets.
            min_replies (Optional[Union[int, str]]): Minimum number of replies.
            min_likes (Optional[Union[int, str]]): Minimum number of likes.
            count (Optional[int]): Number of tweets to retrieve (1-100).

        Returns:
            Union[List[TwitterScraperTweet], Dict[str, Any]]: List of tweets or raw dict.
        """
        url = f"{self.base_url}/twitter"
        params = {
            k: v
            for k, v in {
                "query": query,
                "sort": sort,
                "user": user,
                "start_date": start_date,
                "end_date": end_date,
                "lang": lang,
                "verified": verified,
                "blue_verified": blue_verified,
                "is_quote": is_quote,
                "is_video": is_video,
                "is_image": is_image,
                "min_retweets": min_retweets,
                "min_replies": min_replies,
                "min_likes": min_likes,
                "count": count,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        parsed_data = data
        if isinstance(data, list):
            parsed_data = [TwitterScraperTweet(**item) for item in data]
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def x_posts_by_urls(
        self,
        urls: List[str],
        *,
        include_metadata: bool = False,
    ) -> Union[List[TwitterScraperTweet], DesearchResponse[List[TwitterScraperTweet]]]:
        """
        Fetch full post data for a list of X (Twitter) post URLs.

        Args:
            urls (List[str]): List of tweet URLs to retrieve.

        Returns:
            List[TwitterScraperTweet]: List of tweet details.
        """
        url = f"{self.base_url}/twitter/urls"
        params: List[tuple] = [("urls", u) for u in urls]
        data, metadata = await self._exchange("GET", url, params=params)
        parsed_data = [TwitterScraperTweet(**item) for item in data]
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def x_post_by_id(
        self,
        id: str,
        *,
        include_metadata: bool = False,
    ) -> Union[TwitterScraperTweet, DesearchResponse[TwitterScraperTweet]]:
        """
        Fetch a single X (Twitter) post by its unique ID.

        Args:
            id (str): The unique ID of the post.

        Returns:
            TwitterScraperTweet: The post details.
        """
        url = f"{self.base_url}/twitter/post"
        params = {"id": id}
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            TwitterScraperTweet(**data), metadata, include_metadata
        )

    async def x_posts_by_user(
        self,
        user: str,
        query: Optional[str] = None,
        count: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[
        List[TwitterScraperTweet],
        Dict[str, Any],
        DesearchResponse[Union[List[TwitterScraperTweet], Dict[str, Any]]],
    ]:
        """
        Search X (Twitter) posts by a specific user with optional keyword filtering.

        Args:
            user (str): User to search for.
            query (Optional[str]): Advanced search query.
            count (Optional[int]): Number of tweets to retrieve (1-100).

        Returns:
            Union[List[TwitterScraperTweet], Dict[str, Any]]: List of tweets or raw dict.
        """
        url = f"{self.base_url}/twitter/post/user"
        params = {
            k: v
            for k, v in {
                "user": user,
                "query": query,
                "count": count,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        parsed_data = data
        if isinstance(data, list):
            parsed_data = [TwitterScraperTweet(**item) for item in data]
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def x_post_retweeters(
        self,
        id: str,
        cursor: Optional[str] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[XRetweetersResponse, DesearchResponse[XRetweetersResponse]]:
        """
        Retrieve the list of users who retweeted a specific post.

        Args:
            id (str): The ID of the post to get retweeters for.
            cursor (Optional[str]): Cursor for pagination.

        Returns:
            XRetweetersResponse: List of retweeter users with pagination cursor.
        """
        url = f"{self.base_url}/twitter/post/retweeters"
        params = {
            k: v
            for k, v in {
                "id": id,
                "cursor": cursor,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            XRetweetersResponse(**data), metadata, include_metadata
        )

    async def x_user_posts(
        self,
        username: str,
        cursor: Optional[str] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[XUserPostsResponse, DesearchResponse[XUserPostsResponse]]:
        """
        Retrieve a user's timeline posts by their username.

        Args:
            username (str): Username to fetch posts for.
            cursor (Optional[str]): Cursor for pagination.

        Returns:
            XUserPostsResponse: User info, tweets, and pagination cursor.
        """
        url = f"{self.base_url}/twitter/user/posts"
        params = {
            k: v
            for k, v in {
                "username": username,
                "cursor": cursor,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            XUserPostsResponse(**data), metadata, include_metadata
        )

    async def x_user_replies(
        self,
        user: str,
        count: Optional[int] = None,
        query: Optional[str] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[
        List[TwitterScraperTweet],
        Dict[str, Any],
        DesearchResponse[Union[List[TwitterScraperTweet], Dict[str, Any]]],
    ]:
        """
        Fetch tweets and replies posted by a specific user.

        Args:
            user (str): The username of the user to search for.
            count (Optional[int]): The number of tweets to fetch (1-100).
            query (Optional[str]): Advanced search query.

        Returns:
            Union[List[TwitterScraperTweet], Dict[str, Any]]: List of tweets or raw dict.
        """
        url = f"{self.base_url}/twitter/replies"
        params = {
            k: v
            for k, v in {
                "user": user,
                "count": count,
                "query": query,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        parsed_data = data
        if isinstance(data, list):
            parsed_data = [TwitterScraperTweet(**item) for item in data]
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def x_post_replies(
        self,
        post_id: str,
        count: Optional[int] = None,
        query: Optional[str] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[
        List[TwitterScraperTweet],
        Dict[str, Any],
        DesearchResponse[Union[List[TwitterScraperTweet], Dict[str, Any]]],
    ]:
        """
        Fetch replies to a specific X (Twitter) post by its post ID.

        Args:
            post_id (str): The ID of the post to search for.
            count (Optional[int]): The number of tweets to fetch (1-100).
            query (Optional[str]): Advanced search query.

        Returns:
            Union[List[TwitterScraperTweet], Dict[str, Any]]: List of tweets or raw dict.
        """
        url = f"{self.base_url}/twitter/replies/post"
        params = {
            k: v
            for k, v in {
                "post_id": post_id,
                "count": count,
                "query": query,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        parsed_data = data
        if isinstance(data, list):
            parsed_data = [TwitterScraperTweet(**item) for item in data]
        return self._with_metadata(parsed_data, metadata, include_metadata)

    async def x_trends(
        self,
        woeid: int,
        count: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[XTrendsResponse, DesearchResponse[XTrendsResponse]]:
        """
        Retrieve trending topics on X for a given location using its WOEID.

        Args:
            woeid (int): The WOEID of the location (e.g. 23424977 for United States).
            count (Optional[int]): The number of trends to return (30-100).

        Returns:
            XTrendsResponse: List of trending topics and location info.
        """
        url = f"{self.base_url}/twitter/trends"
        params = {
            k: v
            for k, v in {
                "woeid": woeid,
                "count": count,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(XTrendsResponse(**data), metadata, include_metadata)

    async def web_search(
        self,
        query: str,
        start: Optional[int] = 0,
        *,
        include_metadata: bool = False,
    ) -> Union[WebSearchResultsResponse, DesearchResponse[WebSearchResultsResponse]]:
        """
        SERP web search returning paginated web search results.

        Args:
            query (str): The search query string.
            start (Optional[int]): Number of results to skip for pagination.

        Returns:
            WebSearchResultsResponse: Paginated web search results.
        """
        url = f"{self.base_url}/web"
        params = {
            k: v
            for k, v in {
                "query": query,
                "start": start,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            WebSearchResultsResponse(**data), metadata, include_metadata
        )

    async def extract(
        self,
        url: str,
        format: Optional[str] = "text",
        js: bool = False,
        wait: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[str, DesearchResponse[str]]:
        """Extract a URL through the canonical ``GET /web/extract`` endpoint.

        Args:
            url (str): Public URL to extract content from.
            format (Optional[str]): Output format (``html`` or ``text``).
            js (bool): Render JavaScript before extraction.
            wait (Optional[int]): Extra post-load wait in milliseconds when
                JavaScript rendering is enabled.

        Returns:
            str: The extracted content, optionally wrapped with response metadata.
        """
        params = {
            k: v
            for k, v in {
                "url": url,
                "format": format,
                "js": "true" if js else "false",
                "wait": wait,
            }.items()
            if v is not None
        }
        return await self._handle_text_request(
            "/web/extract", params=params, include_metadata=include_metadata
        )

    async def web_crawl(
        self,
        url: str,
        format: Optional[str] = "text",
        *,
        include_metadata: bool = False,
    ) -> Union[str, DesearchResponse[str]]:
        """
        Crawl a URL through the deprecated ``GET /web/crawl`` compatibility route.

        Use :meth:`extract` for new integrations. This method remains fully
        functional for existing clients during the migration.

        Args:
            url (str): URL to crawl.
            format (Optional[str]): Format of content ('html' or 'text').
                Defaults to 'text'.

        Returns:
            str: The crawled content.
        """
        params = {
            k: v
            for k, v in {
                "url": url,
                "format": format,
            }.items()
            if v is not None
        }
        return await self._handle_text_request(
            "/web/crawl", params=params, include_metadata=include_metadata
        )

    # ─── People Search ───────────────────────────────────────────────────────

    @staticmethod
    def _people_task_path(task_id: Union[str, UUID], suffix: str = "") -> str:
        return f"/desearch/people/tasks/{quote(str(task_id), safe='')}{suffix}"

    @staticmethod
    def _people_filter_params(
        filters: Optional[PeopleFiltersInput], **overrides: Any
    ) -> Dict[str, Union[str, int]]:
        """Merge a filters object (or dict) with keyword filters into query params.

        Keyword values win over the same field in ``filters``.
        """
        values: Dict[str, Any] = {}
        if isinstance(filters, PeopleResultFilters):
            values = filters.model_dump(exclude_none=True)
        elif filters is not None:
            values = {k: v for k, v in dict(filters).items() if v is not None}
        values.update({k: v for k, v in overrides.items() if v is not None})
        return PeopleResultFilters(**values).to_params()

    async def _create_people_search(
        self,
        platform: str,
        request: BaseModel,
        idempotency_key: Optional[str],
        include_metadata: bool,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        url = f"{self.base_url}/desearch/people/search/{platform}"
        kwargs: Dict[str, Any] = {
            "json": request.model_dump(exclude_none=True, mode="json")
        }
        if idempotency_key:
            kwargs["headers"] = {"Idempotency-Key": str(idempotency_key)}
        result = await self._handle_request(
            "POST", url, include_metadata=include_metadata, **kwargs
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(PeopleTask(**data), metadata, include_metadata)

    async def x_profile_search(
        self,
        query: str,
        count: Optional[int] = None,
        min_score: Optional[int] = None,
        exclude: Optional[List[str]] = None,
        filters: Optional[Union[XProfileSearchFilters, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None,
        *,
        idempotency_key: Optional[str] = None,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Start an X Profile Search: X accounts that match what they post and how they describe themselves.

        The search runs in the background and this returns its task at once.
        Wait with :meth:`wait_for_people_task`, then read people with
        :meth:`iter_people_results` or :meth:`export_people_results`.

        Billing: ``count`` profiles are reserved at the route price. When the
        search ends you pay only for the profiles it delivered (a per-search
        minimum applies when it finds anyone; a search that finds nobody is
        free). See https://console.desearch.ai/pricing.

        Args:
            query (str): Who you are looking for, in plain language (3-1000 characters).
            count (Optional[int]): How many qualified profiles to find (5-200; the API default is 25).
            min_score (Optional[int]): Only return profiles with at least this fit score (0-100).
            exclude (Optional[List[str]]): Handles to leave out, e.g. people you already contacted.
            filters (Optional[Union[XProfileSearchFilters, Dict[str, Any]]]): ``min_followers``,
                ``max_followers``, ``verified_only``, ``countries``, ``keywords``, ``exclude_keywords``.
            metadata (Optional[Dict[str, str]]): Your own labels for this search, e.g.
                ``{"campaign": "q4-outbound"}``. At most 10 keys; keys are 1-40 characters of
                a-z, 0-9, ``_``, ``.`` or ``-``; values are strings of at most 200 characters.
                Returned as ``task.metadata`` and usable as a :meth:`list_people_tasks` filter.
                Never used by the search itself.
            idempotency_key (Optional[str]): Sent as the ``Idempotency-Key`` header. Reusing a key
                returns the earlier task (HTTP 200) and is not charged again.

        Returns:
            PeopleTask: The created task.
        """
        request = XProfileSearchRequest.model_validate(
            {
                "query": query,
                "count": count,
                "min_score": min_score,
                "exclude": exclude,
                "filters": filters,
                "metadata": metadata,
            }
        )
        return await self._create_people_search(
            "x", request, idempotency_key, include_metadata
        )

    async def youtube_creator_search(
        self,
        query: str,
        count: Optional[int] = None,
        min_score: Optional[int] = None,
        exclude: Optional[List[str]] = None,
        filters: Optional[Union[YouTubeCreatorSearchFilters, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None,
        *,
        idempotency_key: Optional[str] = None,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Start a YouTube Creator Search: creators that match what their videos are about.

        Runs in the background and is billed like :meth:`x_profile_search`
        (per creator delivered).

        Args:
            query (str): Which creators you are looking for, in plain language (3-1000 characters).
            count (Optional[int]): How many qualified creators to find (5-200; the API default is 25).
            min_score (Optional[int]): Only return creators with at least this fit score (0-100).
            exclude (Optional[List[str]]): Handles to leave out.
            filters (Optional[Union[YouTubeCreatorSearchFilters, Dict[str, Any]]]): ``min_subscribers``,
                ``max_subscribers``, ``countries``, ``require_contact``, ``keywords``, ``exclude_keywords``.
            metadata (Optional[Dict[str, str]]): Your own labels for this search, e.g.
                ``{"campaign": "q4-outbound"}``. At most 10 keys; keys are 1-40 characters of
                a-z, 0-9, ``_``, ``.`` or ``-``; values are strings of at most 200 characters.
                Returned as ``task.metadata`` and usable as a :meth:`list_people_tasks` filter.
                Never used by the search itself.
            idempotency_key (Optional[str]): Sent as the ``Idempotency-Key`` header. Reusing a key
                returns the earlier task (HTTP 200) and is not charged again.

        Returns:
            PeopleTask: The created task.
        """
        request = YouTubeCreatorSearchRequest.model_validate(
            {
                "query": query,
                "count": count,
                "min_score": min_score,
                "exclude": exclude,
                "filters": filters,
                "metadata": metadata,
            }
        )
        return await self._create_people_search(
            "youtube", request, idempotency_key, include_metadata
        )

    async def linkedin_profile_search(
        self,
        query: str,
        count: Optional[int] = None,
        min_score: Optional[int] = None,
        exclude: Optional[List[str]] = None,
        filters: Optional[Union[LinkedInProfileSearchFilters, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None,
        *,
        idempotency_key: Optional[str] = None,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Start a LinkedIn Profile Search: members that match what they post and their role.

        Runs in the background and is billed like :meth:`x_profile_search`
        (per profile delivered).

        Args:
            query (str): Who you are looking for, in plain language (3-1000 characters).
            count (Optional[int]): How many qualified profiles to find (5-200; the API default is 25).
            min_score (Optional[int]): Only return profiles with at least this fit score (0-100).
            exclude (Optional[List[str]]): Handles to leave out.
            filters (Optional[Union[LinkedInProfileSearchFilters, Dict[str, Any]]]): ``min_followers``,
                ``max_followers``, ``countries``, ``keywords``, ``exclude_keywords``.
            metadata (Optional[Dict[str, str]]): Your own labels for this search, e.g.
                ``{"campaign": "q4-outbound"}``. At most 10 keys; keys are 1-40 characters of
                a-z, 0-9, ``_``, ``.`` or ``-``; values are strings of at most 200 characters.
                Returned as ``task.metadata`` and usable as a :meth:`list_people_tasks` filter.
                Never used by the search itself.
            idempotency_key (Optional[str]): Sent as the ``Idempotency-Key`` header. Reusing a key
                returns the earlier task (HTTP 200) and is not charged again.

        Returns:
            PeopleTask: The created task.
        """
        request = LinkedInProfileSearchRequest.model_validate(
            {
                "query": query,
                "count": count,
                "min_score": min_score,
                "exclude": exclude,
                "filters": filters,
                "metadata": metadata,
            }
        )
        return await self._create_people_search(
            "linkedin", request, idempotency_key, include_metadata
        )

    async def tiktok_creator_search(
        self,
        query: str,
        count: Optional[int] = None,
        min_score: Optional[int] = None,
        exclude: Optional[List[str]] = None,
        filters: Optional[Union[TikTokCreatorSearchFilters, Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, str]] = None,
        *,
        idempotency_key: Optional[str] = None,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Start a TikTok Creator Search: creators that match what their videos are about.

        Runs in the background and is billed like :meth:`x_profile_search`
        (per creator delivered).

        Args:
            query (str): Which creators you are looking for, in plain language (3-1000 characters).
            count (Optional[int]): How many qualified creators to find (5-200; the API default is 25).
            min_score (Optional[int]): Only return creators with at least this fit score (0-100).
            exclude (Optional[List[str]]): Handles to leave out.
            filters (Optional[Union[TikTokCreatorSearchFilters, Dict[str, Any]]]): ``min_followers``,
                ``max_followers``, ``require_contact``, ``keywords``, ``exclude_keywords``.
            metadata (Optional[Dict[str, str]]): Your own labels for this search, e.g.
                ``{"campaign": "q4-outbound"}``. At most 10 keys; keys are 1-40 characters of
                a-z, 0-9, ``_``, ``.`` or ``-``; values are strings of at most 200 characters.
                Returned as ``task.metadata`` and usable as a :meth:`list_people_tasks` filter.
                Never used by the search itself.
            idempotency_key (Optional[str]): Sent as the ``Idempotency-Key`` header. Reusing a key
                returns the earlier task (HTTP 200) and is not charged again.

        Returns:
            PeopleTask: The created task.
        """
        request = TikTokCreatorSearchRequest.model_validate(
            {
                "query": query,
                "count": count,
                "min_score": min_score,
                "exclude": exclude,
                "filters": filters,
                "metadata": metadata,
            }
        )
        return await self._create_people_search(
            "tiktok", request, idempotency_key, include_metadata
        )

    async def list_people_tasks(
        self,
        platform: Optional[Union[PeoplePlatform, str]] = None,
        status: Optional[
            Union[PeopleTaskStatus, str, List[Union[PeopleTaskStatus, str]]]
        ] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleTaskList, DesearchResponse[PeopleTaskList]]:
        """
        List your company's People Search tasks, newest first. Free.

        Args:
            platform (Optional[Union[PeoplePlatform, str]]): x, youtube, linkedin or tiktok.
            status (Optional[Union[PeopleTaskStatus, str, List]]): One status, a list, or a
                comma-separated string (e.g. ``"running,paused"``).
            limit (Optional[int]): Page size (1-100; the API default is 20).
            cursor (Optional[str]): ``next_cursor`` from the previous page.
            metadata (Optional[Dict[str, str]]): Only tasks whose ``metadata`` has all of these
                key/value pairs (exact match, at most 3). Each pair is sent as a
                ``metadata.<key>=<value>`` query parameter. Keep the same filter when you page
                with ``cursor``.

        Returns:
            PeopleTaskList: Tasks and the cursor for the next page (``None`` on the last page).
        """
        url = f"{self.base_url}/desearch/people/tasks"
        if isinstance(status, (list, tuple)):
            status = ",".join(str(_enum_value(s)) for s in status)
        params = {
            k: v
            for k, v in {
                "platform": _enum_value(platform),
                "status": _enum_value(status),
                "limit": limit,
                "cursor": cursor,
            }.items()
            if v is not None
        }
        for key, value in (metadata or {}).items():
            params[f"metadata.{key}"] = str(value)
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, cost_metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            PeopleTaskList(**data), cost_metadata, include_metadata
        )

    async def get_people_task(
        self,
        task_id: Union[str, UUID],
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Get the status, progress and cost of one People Search task. Free.

        Args:
            task_id (Union[str, UUID]): The task ID returned when the search was created.

        Returns:
            PeopleTask: The task.
        """
        url = f"{self.base_url}{self._people_task_path(task_id)}"
        result = await self._handle_request(
            "GET", url, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(PeopleTask(**data), metadata, include_metadata)

    async def get_people_results(
        self,
        task_id: Union[str, UUID],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleResultsPage, DesearchResponse[PeopleResultsPage]]:
        """
        Read one page of qualified people found so far, in the order they were found. Free.

        Results arrive while the search is still running. Keep ``next_cursor``
        and call again to get only new people. The API returns 410 once the
        results have expired (30 days after the search ended).

        Args:
            task_id (Union[str, UUID]): The task ID.
            cursor (Optional[str]): ``next_cursor`` from the previous page.
            limit (Optional[int]): Page size (1-500; the API default is 100).

        Returns:
            PeopleResultsPage: People, the next cursor and whether more are available now.
        """
        url = f"{self.base_url}{self._people_task_path(task_id, '/results')}"
        params = {
            k: v
            for k, v in {
                "cursor": cursor,
                "limit": limit,
            }.items()
            if v is not None
        }
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            PeopleResultsPage(**data), metadata, include_metadata
        )

    @staticmethod
    def _people_conflict_error(exc: DesearchAPIError) -> PeopleTaskConflictError:
        detail = ""
        task: Optional[PeopleTask] = None
        try:
            body = json.loads(exc.body) if exc.body else None
        except ValueError:
            body = None
        if isinstance(body, dict):
            detail = str(body.get("detail") or "")
            raw_task = body.get("task")
            if isinstance(raw_task, dict):
                try:
                    task = PeopleTask(**raw_task)
                except ValidationError:
                    task = None
        return PeopleTaskConflictError(
            status=exc.status,
            message=exc.message,
            body=exc.body,
            detail=detail,
            task=task,
        )

    async def _control_people_task(
        self,
        task_id: Union[str, UUID],
        action: str,
        include_metadata: bool,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        url = f"{self.base_url}{self._people_task_path(task_id, '/' + action)}"
        result: Any = None
        conflict: Optional[PeopleTaskConflictError] = None
        try:
            result = await self._handle_request(
                "POST", url, include_metadata=include_metadata
            )
        except DesearchAPIError as exc:
            if exc.status != 409:
                raise
            conflict = self._people_conflict_error(exc)
        if conflict is not None:
            _raise_without_chain(conflict)
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(PeopleTask(**data), metadata, include_metadata)

    async def pause_people_task(
        self,
        task_id: Union[str, UUID],
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Pause a People Search task. Free.

        A queued search pauses at once; a running one finishes its current
        batch first (status ``pausing``, then ``paused``). A search paused for
        more than 7 days is cancelled.

        Args:
            task_id (Union[str, UUID]): The task ID.

        Returns:
            PeopleTask: The task after the request.

        Raises:
            PeopleTaskConflictError: HTTP 409, the task cannot be paused. ``task`` holds its state.
        """
        return await self._control_people_task(task_id, "pause", include_metadata)

    async def resume_people_task(
        self,
        task_id: Union[str, UUID],
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Resume a paused People Search task from where it stopped. Not charged again.

        Args:
            task_id (Union[str, UUID]): The task ID.

        Returns:
            PeopleTask: The task after the request.

        Raises:
            PeopleTaskConflictError: HTTP 409, the task is not paused. ``task`` holds its state.
        """
        return await self._control_people_task(task_id, "resume", include_metadata)

    async def cancel_people_task(
        self,
        task_id: Union[str, UUID],
        *,
        include_metadata: bool = False,
    ) -> Union[PeopleTask, DesearchResponse[PeopleTask]]:
        """
        Cancel a People Search task. Free.

        You pay only for the people it delivered (a search cancelled before it
        starts costs nothing); the rest of the reservation is returned. People
        found so far stay available for 30 days.

        Args:
            task_id (Union[str, UUID]): The task ID.

        Returns:
            PeopleTask: The task after the request.

        Raises:
            PeopleTaskConflictError: HTTP 409, the task has already ended. ``task`` holds its state.
        """
        return await self._control_people_task(task_id, "cancel", include_metadata)

    async def export_people_results(
        self,
        task_id: Union[str, UUID],
        format: Union[PeopleExportFormat, str] = "csv",
        filters: Optional[PeopleFiltersInput] = None,
        *,
        has: Optional[Union[str, List[str]]] = None,
        min_audience: Optional[int] = None,
        max_audience: Optional[int] = None,
        min_score: Optional[int] = None,
        location: Optional[str] = None,
        verified: Optional[bool] = None,
        include_metadata: bool = False,
    ) -> Union[str, DesearchResponse[str]]:
        """
        Download every person a task found so far as CSV or JSON Lines. Free.

        Filters can be passed as a ``PeopleResultFilters`` object (or dict),
        as keyword arguments, or both; keyword arguments win.

        Args:
            task_id (Union[str, UUID]): The task ID.
            format (Union[PeopleExportFormat, str]): ``csv`` (default) or ``jsonl``.
            filters (Optional[Union[PeopleResultFilters, Dict[str, Any]]]): Result filters.
            has (Optional[Union[str, List[str]]]): Channels every person must have:
                email, website, x, linkedin, instagram, youtube, tiktok.
            min_audience (Optional[int]): Minimum followers (subscribers on YouTube).
            max_audience (Optional[int]): Maximum followers (subscribers on YouTube).
            min_score (Optional[int]): Minimum fit score (0-100).
            location (Optional[str]): Text in the location, e.g. ``"united states"``.
            verified (Optional[bool]): ``True`` keeps only verified accounts (X, TikTok).

        Returns:
            str: The file contents.
        """
        params: Dict[str, Any] = {"format": _enum_value(format)}
        params.update(
            self._people_filter_params(
                filters,
                has=has,
                min_audience=min_audience,
                max_audience=max_audience,
                min_score=min_score,
                location=location,
                verified=verified,
            )
        )
        return await self._handle_text_request(
            self._people_task_path(task_id, "/export"),
            params=params,
            include_metadata=include_metadata,
        )

    async def list_people_profiles(
        self,
        platform: Union[PeoplePlatform, str],
        q: Optional[str] = None,
        sort: Optional[Union[PeopleProfileSort, str]] = None,
        limit: Optional[int] = None,
        cursor: Optional[str] = None,
        filters: Optional[PeopleFiltersInput] = None,
        *,
        has: Optional[Union[str, List[str]]] = None,
        min_audience: Optional[int] = None,
        max_audience: Optional[int] = None,
        min_score: Optional[int] = None,
        location: Optional[str] = None,
        verified: Optional[bool] = None,
        include_metadata: bool = False,
    ) -> Union[PeopleProfilesPage, DesearchResponse[PeopleProfilesPage]]:
        """
        List everyone your searches on one platform found, one entry per person. Free.

        Each profile is the person's best-scoring result, with the search that
        found them in ``found_by``. Searches whose results expired are left out.
        Filters work as in :meth:`export_people_results`.

        Args:
            platform (Union[PeoplePlatform, str]): x, youtube, linkedin or tiktok.
            q (Optional[str]): Text in the name, handle, bio or location.
            sort (Optional[Union[PeopleProfileSort, str]]): ``score`` (API default), ``recent`` or ``audience``.
            limit (Optional[int]): Page size (1-200; the API default is 50).
            cursor (Optional[str]): ``next_cursor`` from the previous page.
            filters (Optional[Union[PeopleResultFilters, Dict[str, Any]]]): Result filters.
            has, min_audience, max_audience, min_score, location, verified: Result filters
                as keyword arguments (see :meth:`export_people_results`).

        Returns:
            PeopleProfilesPage: Profiles, the total that match, and the next cursor.
        """
        url = f"{self.base_url}/desearch/people/profiles"
        params: Dict[str, Any] = {
            k: v
            for k, v in {
                "platform": _enum_value(platform),
                "q": q,
                "sort": _enum_value(sort),
                "limit": limit,
                "cursor": cursor,
            }.items()
            if v is not None
        }
        params.update(
            self._people_filter_params(
                filters,
                has=has,
                min_audience=min_audience,
                max_audience=max_audience,
                min_score=min_score,
                location=location,
                verified=verified,
            )
        )
        result = await self._handle_request(
            "GET", url, params=params, include_metadata=include_metadata
        )
        data, metadata = self._split_response(result, include_metadata)
        return self._with_metadata(
            PeopleProfilesPage(**data), metadata, include_metadata
        )

    async def export_people_profiles(
        self,
        platform: Union[PeoplePlatform, str],
        format: Union[PeopleExportFormat, str] = "csv",
        q: Optional[str] = None,
        sort: Optional[Union[PeopleProfileSort, str]] = None,
        filters: Optional[PeopleFiltersInput] = None,
        *,
        has: Optional[Union[str, List[str]]] = None,
        min_audience: Optional[int] = None,
        max_audience: Optional[int] = None,
        min_score: Optional[int] = None,
        location: Optional[str] = None,
        verified: Optional[bool] = None,
        include_metadata: bool = False,
    ) -> Union[str, DesearchResponse[str]]:
        """
        Download what :meth:`list_people_profiles` lists, as CSV or JSON Lines. Free.

        The API exports up to 10,000 people.

        Args:
            platform (Union[PeoplePlatform, str]): x, youtube, linkedin or tiktok.
            format (Union[PeopleExportFormat, str]): ``csv`` (default) or ``jsonl``.
            q (Optional[str]): Text in the name, handle, bio or location.
            sort (Optional[Union[PeopleProfileSort, str]]): ``score``, ``recent`` or ``audience``.
            filters (Optional[Union[PeopleResultFilters, Dict[str, Any]]]): Result filters.
            has, min_audience, max_audience, min_score, location, verified: Result filters
                as keyword arguments (see :meth:`export_people_results`).

        Returns:
            str: The file contents.
        """
        params: Dict[str, Any] = {
            k: v
            for k, v in {
                "platform": _enum_value(platform),
                "format": _enum_value(format),
                "q": q,
                "sort": _enum_value(sort),
            }.items()
            if v is not None
        }
        params.update(
            self._people_filter_params(
                filters,
                has=has,
                min_audience=min_audience,
                max_audience=max_audience,
                min_score=min_score,
                location=location,
                verified=verified,
            )
        )
        return await self._handle_text_request(
            "/desearch/people/profiles/export",
            params=params,
            include_metadata=include_metadata,
        )

    async def wait_for_people_task(
        self,
        task_id: Union[str, UUID],
        *,
        poll_interval: float = 5.0,
        timeout: Optional[float] = 600.0,
    ) -> PeopleTask:
        """
        Poll a People Search task until it ends (completed, partial, failed, cancelled or expired).

        Polling is free. A paused task stays paused until it is resumed (the
        API cancels it after 7 days), so waiting on one runs until ``timeout``.

        Args:
            task_id (Union[str, UUID]): The task ID.
            poll_interval (float): Seconds between polls. Defaults to 5.
            timeout (Optional[float]): Seconds to wait before raising
                ``PeopleTaskTimeoutError``. ``None`` waits without a limit. Defaults to 600.

        Returns:
            PeopleTask: The ended task.

        Raises:
            PeopleTaskTimeoutError: The task had not ended in time. The search keeps running.
        """
        loop = asyncio.get_running_loop()
        started = loop.time()
        while True:
            task = cast(PeopleTask, await self.get_people_task(task_id))
            if task.is_finished:
                return task
            delay = poll_interval
            if timeout is not None:
                remaining = timeout - (loop.time() - started)
                if remaining <= 0:
                    raise PeopleTaskTimeoutError(task, timeout)
                delay = min(poll_interval, remaining)
            await asyncio.sleep(delay)

    async def iter_people_results(
        self,
        task_id: Union[str, UUID],
        *,
        cursor: Optional[str] = None,
        page_size: int = 100,
    ) -> AsyncIterator[Person]:
        """
        Yield every person a task has found so far, following ``next_cursor`` page by page. Free.

        Stops when the API reports no more results available now. Call
        :meth:`wait_for_people_task` first to read a finished search in full.

        Args:
            task_id (Union[str, UUID]): The task ID.
            cursor (Optional[str]): Start after this cursor instead of the beginning.
            page_size (int): People per request (1-500). Defaults to 100.

        Yields:
            Person: Each qualified person, in the order found.
        """
        while True:
            page = cast(
                PeopleResultsPage,
                await self.get_people_results(task_id, cursor=cursor, limit=page_size),
            )
            for person in page.results:
                yield person
            cursor = page.next_cursor
            if not page.has_more or not page.results:
                return
