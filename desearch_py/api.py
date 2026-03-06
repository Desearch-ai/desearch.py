from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Dict, List, Optional, Union

import aiohttp

from .models import (
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
                headers={"Authorization": self.api_key}
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

    async def _handle_request(self, method: str, url: str, **kwargs: Any) -> Any:
        """
        Send an HTTP request and return the parsed JSON response.

        Args:
            method (str): HTTP method (GET, POST, etc.).
            url (str): Full request URL.
            **kwargs: Additional arguments passed to the request.

        Returns:
            Any: Parsed JSON response.

        Raises:
            aiohttp.ClientResponseError: On HTTP error responses.
            aiohttp.ClientError: On connection-level errors.
        """
        client = await self._ensure_session()
        try:
            async with client.request(
                method, url, timeout=aiohttp.ClientTimeout(total=120), **kwargs
            ) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error("HTTP error %s for %s %s: %s", e.status, method, url, e.message)
            raise
        except aiohttp.ClientError as e:
            logger.error("Client error for %s %s: %s", method, url, str(e))
            raise

    async def ai_search(
        self,
        prompt: str,
        tools: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        date_filter: Optional[str] = "PAST_24_HOURS",
        result_type: Optional[str] = "LINKS_WITH_FINAL_SUMMARY",
        system_message: Optional[str] = None,
        scoring_system_message: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Union[ResponseData, Dict[str, Any]]:
        """
        AI-powered multi-source contextual search.

        Args:
            prompt (str): Search query prompt.
            tools (List[str]): List of tools to search with (e.g. web, twitter, reddit).
            start_date (Optional[str]): Start date in UTC (YYYY-MM-DDTHH:MM:SSZ).
            end_date (Optional[str]): End date in UTC (YYYY-MM-DDTHH:MM:SSZ).
            date_filter (Optional[str]): Predefined date filter for search results.
            result_type (Optional[str]): Result type (ONLY_LINKS or LINKS_WITH_FINAL_SUMMARY).
            system_message (Optional[str]): System message for the search.
            scoring_system_message (Optional[str]): System message for scoring the response.
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
                "count": count,
            }.items()
            if v is not None
        }

        data = await self._handle_request("POST", url, json=payload)
        if isinstance(data, dict):
            try:
                return ResponseData(**data)
            except Exception:
                return data
        return data

    async def ai_web_links_search(
        self,
        prompt: str,
        tools: List[str],
        count: Optional[int] = None,
    ) -> WebSearchResponse:
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
        data = await self._handle_request("POST", url, json=payload)
        return WebSearchResponse(**data)

    async def ai_x_links_search(
        self,
        prompt: str,
        count: Optional[int] = None,
    ) -> XLinksSearchResponse:
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
        data = await self._handle_request("POST", url, json=payload)
        return XLinksSearchResponse(**data)

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
    ) -> Union[List[TwitterScraperTweet], Dict[str, Any]]:
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
        data = await self._handle_request("GET", url, params=params)
        if isinstance(data, list):
            return [TwitterScraperTweet(**item) for item in data]
        return data

    async def x_posts_by_urls(
        self,
        urls: List[str],
    ) -> List[TwitterScraperTweet]:
        """
        Fetch full post data for a list of X (Twitter) post URLs.

        Args:
            urls (List[str]): List of tweet URLs to retrieve.

        Returns:
            List[TwitterScraperTweet]: List of tweet details.
        """
        url = f"{self.base_url}/twitter/urls"
        params: List[tuple] = [("urls", u) for u in urls]
        client = await self._ensure_session()
        try:
            async with client.request(
                "GET", url, params=params, timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                response.raise_for_status()
                data = await response.json()
        except aiohttp.ClientResponseError as e:
            logger.error("HTTP error %s for GET %s: %s", e.status, url, e.message)
            raise
        except aiohttp.ClientError as e:
            logger.error("Client error for GET %s: %s", url, str(e))
            raise
        return [TwitterScraperTweet(**item) for item in data]

    async def x_post_by_id(
        self,
        id: str,
    ) -> TwitterScraperTweet:
        """
        Fetch a single X (Twitter) post by its unique ID.

        Args:
            id (str): The unique ID of the post.

        Returns:
            TwitterScraperTweet: The post details.
        """
        url = f"{self.base_url}/twitter/post"
        params = {"id": id}
        data = await self._handle_request("GET", url, params=params)
        return TwitterScraperTweet(**data)

    async def x_posts_by_user(
        self,
        user: str,
        query: Optional[str] = None,
        count: Optional[int] = None,
    ) -> Union[List[TwitterScraperTweet], Dict[str, Any]]:
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
        data = await self._handle_request("GET", url, params=params)
        if isinstance(data, list):
            return [TwitterScraperTweet(**item) for item in data]
        return data

    async def x_post_retweeters(
        self,
        id: str,
        cursor: Optional[str] = None,
    ) -> XRetweetersResponse:
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
        data = await self._handle_request("GET", url, params=params)
        return XRetweetersResponse(**data)

    async def x_user_posts(
        self,
        username: str,
        cursor: Optional[str] = None,
    ) -> XUserPostsResponse:
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
        data = await self._handle_request("GET", url, params=params)
        return XUserPostsResponse(**data)

    async def x_user_replies(
        self,
        user: str,
        count: Optional[int] = None,
        query: Optional[str] = None,
    ) -> Union[List[TwitterScraperTweet], Dict[str, Any]]:
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
        data = await self._handle_request("GET", url, params=params)
        if isinstance(data, list):
            return [TwitterScraperTweet(**item) for item in data]
        return data

    async def x_post_replies(
        self,
        post_id: str,
        count: Optional[int] = None,
        query: Optional[str] = None,
    ) -> Union[List[TwitterScraperTweet], Dict[str, Any]]:
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
        data = await self._handle_request("GET", url, params=params)
        if isinstance(data, list):
            return [TwitterScraperTweet(**item) for item in data]
        return data

    async def x_trends(
        self,
        woeid: int,
        count: Optional[int] = None,
    ) -> XTrendsResponse:
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
        data = await self._handle_request("GET", url, params=params)
        return XTrendsResponse(**data)

    async def web_search(
        self,
        query: str,
        start: Optional[int] = 0,
    ) -> WebSearchResultsResponse:
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
        data = await self._handle_request("GET", url, params=params)
        return WebSearchResultsResponse(**data)

    async def web_crawl(
        self,
        url: str,
        format: Optional[str] = "text",
    ) -> str:
        """
        Crawl a URL and return its content as plain text or HTML.

        Args:
            url (str): URL to crawl.
            format (Optional[str]): Format of content ('html' or 'text'). Defaults to 'text'.

        Returns:
            str: The crawled content.
        """
        request_url = f"{self.base_url}/web/crawl"
        params = {
            k: v
            for k, v in {
                "url": url,
                "format": format,
            }.items()
            if v is not None
        }
        client = await self._ensure_session()
        try:
            async with client.request(
                "GET", request_url, params=params, timeout=aiohttp.ClientTimeout(total=120)
            ) as response:
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientResponseError as e:
            logger.error("HTTP error %s for GET %s: %s", e.status, request_url, e.message)
            raise
        except aiohttp.ClientError as e:
            logger.error("Client error for GET %s: %s", request_url, str(e))
            raise
