# Known Issues and Limitations — desearch-py SDK

> Based on source inspection of `desearch_py/api.py` and `desearch_py/models.py`. Version 1.2.0.

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

The timeout is set in `_handle_request` and cannot be overridden per-method or per-call.

```python
timeout=aiohttp.ClientTimeout(total=120)
```

**Impact**: long-running `web_crawl` or `ai_search` calls with large result sets may be killed if they exceed 2 minutes.

---

### Streaming not exposed

`ai_search` accepts a `streaming` parameter in its payload but it is hardcoded to `False`:

```python
"streaming": False,
```

There is no streaming implementation, no async generator API, and no SSE handling in the codebase.

**Impact**: `ai_search` always returns a complete JSON response. No way to stream results as they arrive.

---

### Union return types cause type-checking uncertainty

Five methods return `Union[Model, Dict[str, Any]]`:

- `ai_search`
- `x_search`
- `x_posts_by_user`
- `x_user_replies`
- `x_post_replies`

These methods try to parse the response as a pydantic model first, then fall back to a raw `dict` if parsing fails. This means static type checkers cannot guarantee which type is returned at runtime.

```python
data = await self._handle_request("GET", url, params=params)
if isinstance(data, list):
    return [TwitterScraperTweet(**item) for item in data]
return data   # ← raw dict if not a list
```

**Impact**: consumers using strict type checkers (mypy, pyright) will see union-typed results and may need runtime `isinstance` checks.

---

### Authorization header format is non-standard

The SDK sends the API key as a raw token without a `Bearer` prefix:

```python
headers={"Authorization": self.api_key, ...}
```

If the Desearch API expects `Authorization: Bearer <key>`, all requests will return 401.

**Impact**: verify with the API documentation whether `Bearer` is required. Current implementation matches what is in `_ensure_session`.

---

### `x_posts_by_urls` uses a different request path

Unlike other GET methods that route through `_handle_request`, `x_posts_by_urls` builds its request directly:

```python
params: List[tuple] = [("urls", u) for u in urls]
async with client.request("GET", url, params=params, ...) as response:
```

URL encoding of repeated `urls` parameters may behave differently from the shared helper's query-string building.

**Impact**: test thoroughly when fetching more than a few URLs in a single call.

---

### `web_crawl` returns raw string, not a model

`web_crawl` calls `response.text()` and returns the raw response body as `str`, regardless of whether `format="html"` or `format="text"`.

There is no structured response model.

**Impact**: HTML responses are returned as raw HTML strings. Consumers must parse them separately.

---

### No cursor helper for paginated endpoints

Cursor-based pagination is present in:
- `x_post_retweeters` → `XRetweetersResponse.next_cursor`
- `x_user_posts` → `XUserPostsResponse.next_cursor`

There is no built-in iterator or helper to auto-fetch subsequent pages.

**Impact**: callers must manage cursors manually and implement their own pagination loops.

---

### `docs/` directory contains Sphinx scaffolding that has not been built

The repository ships a `docs/` directory with Sphinx configuration (`conf.py`, `index.rst`, `Makefile`). These files exist alongside the prose documentation (`features.md`, `architecture.md`, `known-issues.md`) in the same directory.

**Impact**: The Sphinx build files have not been built into a published HTML site. No generated `_build/` output is present in the repository.

---

## Summary table

| Issue | Severity | Workaround |
|---|---|---|
| No retry / backoff | Medium | Implement retry in caller |
| No custom exceptions | Low | Catch `aiohttp` errors directly |
| Hardcoded 120 s timeout | Low | Use signal/alarm to interrupt; none in async context |
| Streaming not exposed | Low | Not needed for current API surface |
| Union return types | Low | Runtime `isinstance` checks |
| Auth header format | **High** (if API expects `Bearer`) | Verify with API team |
| `x_posts_by_urls` param encoding | Low | Test multi-URL batches |
| `web_crawl` returns raw string | Low | Parse HTML with `BeautifulSoup` etc. |
| No pagination helpers | Low | Manage cursors manually |
| Sphinx scaffolding not built | Info | No `_build/` output present; browse `docs/*.md` directly |
