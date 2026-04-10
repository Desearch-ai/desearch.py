# Known Issues — desearch-py SDK

This list covers real current limitations verified from the repository source.

## 1. Streaming is not actually available in the SDK

**What happens**

`ai_search()` always sends `"streaming": False` in the request payload.

**Why unresolved**

There is no streaming transport, async iterator response path, or SSE handling anywhere in `desearch_py/api.py`.

**Impact**

Consumers always wait for a full response payload. Incremental token or event delivery is not available.

**Workaround**

Use the full-response `ai_search()` flow only.

## 2. Some methods can return raw dictionaries instead of typed models

**What happens**

These methods fall back to raw `dict` values when the response shape is not what the local parser expects:

- `ai_search`
- `x_search`
- `x_posts_by_user`
- `x_user_replies`
- `x_post_replies`

**Why unresolved**

The current design favors tolerance for API shape drift over strict schema enforcement.

**Impact**

Callers cannot assume those methods always return model instances.

**Workaround**

Check types at runtime before accessing model attributes.

## 3. Retry and backoff are not built in

**What happens**

The shared request path performs one request attempt and re-raises transport or HTTP errors.

**Why unresolved**

There is no retry helper, middleware, or configurable transport layer in the SDK.

**Impact**

Transient failures such as timeouts or temporary upstream instability must be handled by the caller.

**Workaround**

Wrap SDK calls in caller-side retry logic with bounded backoff.

## 4. Timeout is fixed at 120 seconds

**What happens**

The SDK hardcodes `aiohttp.ClientTimeout(total=120)` in `_handle_request()`, `x_posts_by_urls()`, and `web_crawl()`.

**Why unresolved**

Timeout configuration is not exposed on the client or individual methods.

**Impact**

Long-running crawl or search calls cannot be tuned per environment.

**Workaround**

Keep requests small where possible, or enforce higher-level timeout handling around SDK usage.

## 5. Pagination helpers are missing

**What happens**

Cursor-aware endpoints like `x_post_retweeters()` and `x_user_posts()` return typed responses with cursor fields, but the SDK does not auto-follow them.

**Why unresolved**

No iterator abstraction or paginator helper exists in the current client.

**Impact**

Consumers must manage cursors manually across multiple requests.

**Workaround**

Persist `next_cursor` from each response and pass it into the next request yourself.

## 6. `web_crawl()` returns raw text only

**What happens**

`web_crawl()` returns `response.text()` directly, not a typed model.

**Why unresolved**

The method is implemented as a lightweight passthrough for `text` or `html` output.

**Impact**

Callers must parse returned content themselves.

**Workaround**

Treat the response as raw HTML or text and parse it in application code.

## 7. Request logic is duplicated in two special-case methods

**What happens**

`x_posts_by_urls()` and `web_crawl()` bypass `_handle_request()` and duplicate direct request and error-handling code.

**Why unresolved**

Each method needs a slightly different transport path, one for repeated query params and one for text responses.

**Impact**

Future transport-level changes can drift if contributors update `_handle_request()` but forget the duplicated paths.

**Workaround**

When changing request behavior, audit those two methods explicitly.

## 8. Sphinx docs scaffolding still has legacy branding

**What happens**

`docs/conf.py` still uses `project = 'datura-py'`, `author = 'Leva'`, and generated files in `docs/_build/` repeat that metadata.

**Why unresolved**

The repo contains an older Sphinx scaffold that has not been fully refreshed to match the current package identity.

**Impact**

Contributors can be misled if they treat generated docs output as authoritative.

**Workaround**

Use `README.md` and the Markdown files in `docs/` as the current documentation source of truth, and verify claims against the Python source.

## Summary

| Limitation | Severity | Workaround |
|---|---|---|
| Streaming unavailable | Medium | Use full-response search only |
| Mixed typed and raw dict returns | Medium | Add runtime type checks |
| No retry/backoff | Medium | Retry in caller |
| Fixed 120 second timeout | Low | Control timeout behavior at the caller layer |
| No pagination helpers | Low | Manually reuse cursor values |
| `web_crawl()` returns raw text | Low | Parse returned content yourself |
| Duplicated request logic | Low | Audit special-case methods during transport changes |
| Legacy Sphinx branding | Info | Ignore `docs/_build/` as a source of truth |
