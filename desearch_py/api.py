from __future__ import annotations

import inspect
import logging
import math
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, quote_plus

import aiohttp
from aiohttp import ClientResponseError
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from .models import (
    DesearchCostMetadata,
    DesearchResponse,
    ResponseData,
    WebSearchResponse,
    XLinksSearchResponse,
    TwitterScraperTweet,
    WebSearchResultsResponse,
    XRetweetersResponse,
    XUserPostsResponse,
    XTrendsResponse,
)

logger = logging.getLogger(__name__)

BASE_URL = "https://api.desearch.ai"


def _empty_headers() -> CIMultiDictProxy[str]:
    """Header mapping with no names and no values."""
    return CIMultiDictProxy(CIMultiDict())


def _request_info(method: str, url: URL) -> aiohttp.RequestInfo:
    """Build ``RequestInfo`` across aiohttp versions.

    ``real_url`` is a required field on some releases and optional on others
    (attrs default in 3.8–3.10, sentinel default from 3.11 on). Passing it
    only when the constructor accepts it keeps a single call site working for
    every aiohttp allowed by this package.
    """
    headers = _empty_headers()
    try:
        parameters = inspect.signature(aiohttp.RequestInfo).parameters
    except (TypeError, ValueError):
        parameters = {}
    kwargs: Dict[str, Any] = {"url": url, "method": method, "headers": headers}
    if "real_url" in parameters:
        kwargs["real_url"] = url
    try:
        return aiohttp.RequestInfo(**kwargs)
    except TypeError:
        if "real_url" in kwargs:
            kwargs.pop("real_url")
        else:
            kwargs["real_url"] = url
        return aiohttp.RequestInfo(**kwargs)


def _blank_request_info() -> aiohttp.RequestInfo:
    return _request_info("GET", URL(""))


class DesearchAPIError(ClientResponseError):
    """HTTP error returned by the Desearch API.

    This is an ``aiohttp.ClientResponseError``, so ``except
    aiohttp.ClientResponseError`` and ``.status`` keep working.

    ``status`` is the HTTP status code and ``body`` is the response body.
    ``request_info`` is a sanitized ``RequestInfo``: empty headers and a URL
    that does not carry the API key. The parent is constructed with
    ``history=()`` and ``headers=None``. The API key is never stored on this
    error.
    """

    def __init__(
        self,
        status: int,
        message: str = "",
        body: str = "",
        *,
        request_info: Optional[aiohttp.RequestInfo] = None,
    ) -> None:
        self.body = body
        super().__init__(
            request_info if request_info is not None else _blank_request_info(),
            (),
            status=status,
            message=message,
            headers=None,
        )
        self.status = status
        self.message = message
        self.body = body

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

    def _redact_url_text(self, value: Optional[str]) -> str:
        """Replace the API key, including percent-encoded forms, in a URL string."""
        text = "" if value is None else str(value)
        secret = self.api_key
        if not secret or not text:
            return text
        variants = [secret, quote(secret, safe=""), quote_plus(secret)]
        encoded = quote(secret, safe="")
        if encoded:
            variants.append(quote(encoded, safe=""))
        seen = set()
        for variant in sorted(variants, key=len, reverse=True):
            if not variant or variant in seen:
                continue
            seen.add(variant)
            text = text.replace(variant, "[REDACTED]")
        return text

    def _sanitized_url(self, url: Optional[str]) -> URL:
        """URL with the API key removed and with no query value left to carry it.

        The query and fragment are dropped before ``URL`` sees the string, so a
        query value cannot carry the key and the original string is not stored.
        """
        text = self._redact_url_text(url)
        cut = len(text)
        for separator in ("?", "#"):
            index = text.find(separator)
            if index != -1:
                cut = min(cut, index)
        text = text[:cut]
        try:
            return URL(text)
        except ValueError:
            return URL("")

    def _sanitized_request_info(self, method: str, url: str) -> aiohttp.RequestInfo:
        safe_method = self._redact(method) or "GET"
        return _request_info(safe_method, self._sanitized_url(url))

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
        request_info = self._sanitized_request_info(method, url)
        logger.error(
            "HTTP error %s for %s %s: %s",
            status,
            request_info.method,
            str(request_info.url),
            safe_message,
        )
        return DesearchAPIError(
            status=status,
            message=safe_message,
            body=safe_body,
            request_info=request_info,
        )

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
        except DesearchAPIError:
            # DesearchAPIError is a ClientResponseError. Re-raise it unchanged
            # so the response body is preserved and it is not wrapped again.
            raise
        except aiohttp.ClientResponseError as exc:
            # Raised only when a response has no status and raise_for_status()
            # built a ClientResponseError. Copy status and reason onto a new
            # error whose request_info is sanitized. Drop the original so the
            # key in its headers cannot survive on __cause__ or __context__.
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
