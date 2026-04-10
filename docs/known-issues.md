# Known Issues and Limitations — desearch-py SDK

> Based on source inspection of `desearch_py/api.py`, `desearch_py/models.py`, and repository docs contents. Version 1.2.0.

---

## Confirmed limitations

### No retry or backoff logic

`_handle_request` makes a single HTTP attempt. Network failures, 502/503 errors, and transient timeouts are not retried.

**Impact**: callers must implement their own retry loops if reliability is required.

---

### No custom exception types

All errors propagate as raw `aiohttp` exceptions:

- `aiohttp.ClientResponseError` for HTTP 4xx/5xx responses
- `aiohttp.ClientError` for connection-level failures
- `asyncio.TimeoutError` if the 120 s timeout is hit

There is no `DesearchError`, `AuthenticationError`, or `RateLimitError` wrapper.

**Impact**: consumer code must catch `aiohttp` exceptions directly. Error messages are logged but not translated to SDK-specific types.

---

### Hardcoded 120 s timeout

The timeout is set in `_handle_request`, `x_posts_by_urls`, and `web_crawl`, and cannot be overridden per-method or per-call.

```python
timeout=aiohttp.ClientTimeout(total=120)
```

**Impact**: long-running `web_crawl` or `ai_search` calls may fail if they exceed 2 minutes.

---

### Streaming not exposed

`ai_search` includes `streaming` in its payload, but the value is hardcoded to `False`:

```python
"streaming": False,
```

There is no streaming implementation, no async generator API, and no SSE handling in the SDK.

**Impact**: `ai_search` always returns a complete response. There is no SDK path for incremental output.

---

### Some methods may return raw `dict` data instead of typed models

Five methods fall back to raw dictionaries when the response shape does not match the local model logic:

- `ai_search`
- `x_search`
- `x_posts_by_user`
- `x_user_replies`
- `x_post_replies`

Example pattern:

```python
data = await self._handle_request("GET", url, params=params)
if isinstance(data, list):
    return [TwitterScraperTweet(**item) for item in data]
return data
```

**Impact**: callers that rely on strict typing need runtime checks before accessing model attributes.

---

### `x_posts_by_urls` bypasses the shared request helper

Unlike most methods, `x_posts_by_urls` does not use `_handle_request`. It builds a repeated `urls` query parameter list and issues the request directly:

```python
params: List[tuple] = [("urls", u) for u in urls]
async with client.request("GET", url, params=params, ...) as response:
```

**Impact**: this endpoint duplicates request/error-handling logic instead of reusing the common helper, so future behavior changes must be updated in two places.

---

### `web_crawl` returns raw text, not a typed response model

`web_crawl` calls `response.text()` and returns the response body as `str` for both supported formats:

```python
return await response.text()
```

There is no pydantic model for crawl responses.

**Impact**: callers must parse returned HTML or plain text themselves.

---

### Cursor pagination is manual

Cursor-based pagination is present in:

- `x_post_retweeters` → `XRetweetersResponse.next_cursor`
- `x_user_posts` → `XUserPostsResponse.next_cursor`

The SDK does not provide an iterator or helper that automatically follows cursors.

**Impact**: callers must store `next_cursor` and make follow-up requests manually.

---

### Built Sphinx output is checked into the repository

The repository contains both Sphinx source files (`docs/conf.py`, `docs/index.rst`, `docs/Makefile`) and generated output under `docs/_build/`, including:

- `docs/_build/index.html`
- `docs/_build/genindex.html`
- `docs/_build/search.html`

**Impact**: documentation changes can drift from checked-in generated HTML if contributors update Markdown or source files without rebuilding `docs/_build/`.

---

## Summary table

| Issue | Severity | Workaround |
|---|---|---|
| No retry / backoff | Medium | Implement retry in caller |
| No custom exceptions | Low | Catch `aiohttp` errors directly |
| Hardcoded 120 s timeout | Low | Split large operations or wrap calls with caller-side timeout handling |
| Streaming not exposed | Low | Use full-response flow only |
| Raw `dict` fallback on some methods | Low | Add runtime type checks |
| `x_posts_by_urls` duplicates request logic | Low | Test URL-batch flows carefully |
| `web_crawl` returns raw string | Low | Parse content in caller |
| Manual cursor pagination | Low | Store and reuse `next_cursor` |
| Built docs checked into repo | Info | Rebuild `docs/_build/` when docs sources change |
