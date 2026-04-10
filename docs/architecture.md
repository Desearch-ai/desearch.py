# Architecture — desearch-py SDK

> Internal design notes for contributors. Based on source at `desearch_py/api.py` and `desearch_py/models.py`.

---

## Overview

The SDK is a thin async HTTP wrapper. It does not ship its own retry logic, rate-limit handling, or streaming infrastructure. The two main building blocks are:

1. **`Desearch` (api.py)** — async client managing an `aiohttp.ClientSession`.
2. **`models.py`** — pydantic `BaseModel` subclasses for all known API response shapes.

---

## Async client (`Desearch`)

### Initialization

```python
client = Desearch(api_key="...", base_url="https://api.desearch.ai")
```

- `api_key` is stored on the instance and sent as the `Authorization` header on every request.
- `base_url` defaults to `https://api.desearch.ai` and is stripped of any trailing slash.
- No HTTP session is opened until the first request (`lazy` initialization).

### Session management

```python
async def _ensure_session(self) -> aiohttp.ClientSession:
    if self.client is None or self.client.closed:
        self.client = aiohttp.ClientSession(
            headers={
                "Authorization": self.api_key,
                "Accept-Encoding": "gzip, deflate",
            }
        )
    return self.client
```

- Sessions are opened lazily on first use and closed via `await client.close()`.
- The `async with` context manager (`__aenter__` / `__aexit__`) handles open/close automatically.
- Compression is enabled via `Accept-Encoding: gzip, deflate`.

### Request dispatch (`_handle_request`)

All methods funnel through a shared helper:

```python
async def _handle_request(self, method: str, url: str, **kwargs) -> Any:
    client = await self._ensure_session()
    async with client.request(
        method, url, timeout=aiohttp.ClientTimeout(total=120), **kwargs
    ) as response:
        response.raise_for_status()
        return await response.json()
```

- **Timeout**: 120 s hardcoded. No per-method override.
- **Errors**: raises `aiohttp.ClientResponseError` (HTTP errors) or `aiohttp.ClientError` (connection errors). No SDK-level translation to custom exceptions.
- **Logging**: errors are logged via `logger.error` before re-raising.

### Method return types

Most methods return typed pydantic models. A few return `Union[Model, Dict[str, Any]]` to handle unexpected response shapes gracefully:

| Method | Return type |
|---|---|
| `ai_search` | `ResponseData` or `dict` |
| `ai_web_links_search` | `WebSearchResponse` |
| `ai_x_links_search` | `XLinksSearchResponse` |
| `x_search` | `List[TwitterScraperTweet]` or `dict` |
| `x_posts_by_urls` | `List[TwitterScraperTweet]` |
| `x_post_by_id` | `TwitterScraperTweet` |
| `x_posts_by_user` | `List[TwitterScraperTweet]` or `dict` |
| `x_post_retweeters` | `XRetweetersResponse` |
| `x_user_posts` | `XUserPostsResponse` |
| `x_user_replies` | `List[TwitterScraperTweet]` or `dict` |
| `x_post_replies` | `List[TwitterScraperTweet]` or `dict` |
| `x_trends` | `XTrendsResponse` |
| `web_search` | `WebSearchResultsResponse` |
| `web_crawl` | `str` (raw response text) |

---

## Pydantic models (`models.py`)

### Design choices

- `model_config = ConfigDict(extra="allow")` is set on all models. The API may return fields not defined in the local schema; this prevents parse failures and allows forward compatibility.
- Most fields are typed as `Optional` with sensible defaults (`None` or `""`).
- Nested models mirror the API's JSON structure for Twitter entities (user, tweet, media, entities, extended_entities).

### Model groups

**Twitter core**
- `TwitterScraperTweet` — top-level tweet object
- `TwitterScraperUser` — user profile
- `TwitterScraperEntities` — hashtags, mentions, URLs, media
- `TwitterScraperEntitiesMedia` — media attachment (photos, videos, GIFs)
- `TwitterScraperExtendedEntities` — alternative media container
- `TwitterScraperMedia` — simplified media reference

**AI search**
- `ResponseData` — multi-source AI search results; returns raw `dict` values per source
- `XLinksSearchResponse` — wraps `List[TwitterScraperTweet]` from the miner network
- `WebSearchResponse` — per-source link results (YouTube, HN, Reddit, arXiv, Wikipedia, web)
- `WebSearchResultItem` — individual SERP result with `title`, `snippet`, `link`

**X utility**
- `XRetweetersResponse` — retweeter list + pagination cursor
- `XUserPostsResponse` — user info + tweet list + pagination cursor
- `XTrendsResponse` — trend items + location metadata

**Enums**
- `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`

**Errors**
- `ValidationError`, `HTTPValidationError`, `UnauthorizedResponse`, `TooManyRequestsResponse`, `InternalServerErrorResponse`, `MovedPermanentlyResponse`

---

## Exports (`__init__.py`)

`desearch_py/__init__.py` re-exports:

- The `Desearch` client class
- All enums: `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`
- All response models
- All error models
- All Twitter entity models

Users only need:

```python
from desearch_py import Desearch, Tool, DateFilter
```

---

## HTTP details

| Detail | Value |
|---|---|
| Base URL | `https://api.desearch.ai` |
| Auth method | `Authorization: <api_key>` (raw token, no `Bearer` prefix) |
| Timeout | 120 s global, no per-method override |
| Compression | `Accept-Encoding: gzip, deflate` |
| Response format | JSON (all methods except `web_crawl`, which returns raw text/HTML via `response.text()`) |
| Retry logic | None built in |
| Rate-limit handling | None built in |

---

## Missing / unimplemented

- **Streaming**: `ai_search` hardcodes `streaming=False`. No public streaming API is exposed.
- **Custom exceptions**: all errors propagate as raw `aiohttp` exceptions.
- **Retry / backoff**: not implemented.
- **Pagination helpers**: cursor-based endpoints (`x_post_retweeters`, `x_user_posts`) return raw cursors; no high-level iterator is provided.
