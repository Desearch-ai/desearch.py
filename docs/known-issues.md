# Known Issues — desearch-py SDK

This list covers real current limitations verified from the repository source.

## 1. AI search streaming is not available in the SDK

**What happens**

`ai_search()` always sends `"streaming": False` in the request payload.

**Why unresolved**

The only streaming method is `stream_network_stats()`, which reads the network stats Server-Sent Events. There is no streaming path for AI search.

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
- the TikTok, Instagram, and Facebook methods that return a list, when the API answers with an object instead of a list

**Why unresolved**

The current design favors tolerance for API shape drift over strict schema enforcement.

**Impact**

Callers cannot assume those methods always return model instances.

**Workaround**

Check types at runtime before accessing model attributes.

## 3. Retry and backoff are not built in

**What happens**

The shared request path performs one request attempt. HTTP errors are raised as `DesearchAPIError` (status, reason, and response body, without request headers). Transport errors are still propagated to the caller.

**Why unresolved**

There is no retry helper, middleware, or configurable transport layer in the SDK.

**Impact**

Transient failures such as timeouts or temporary upstream instability must be handled by the caller.

**Workaround**

Wrap SDK calls in caller-side retry logic with bounded backoff.

## 4. Timeout is fixed at 120 seconds

**What happens**

The SDK hardcodes `aiohttp.ClientTimeout(total=120)` in `_exchange()`, which `_handle_request()`, `_handle_text_request()`, and `x_posts_by_urls()` all use.

**Why unresolved**

Timeout configuration is not exposed on the client or individual methods.

**Impact**

Long-running extraction or search calls cannot be tuned per environment. Large People Search exports (`export_people_profiles` returns up to 10,000 people) must also finish within 120 seconds. `wait_for_people_task()` is not affected: each poll is its own short request. `stream_network_stats()` has no total timeout but a fixed 60 second read timeout, also not configurable.

**Workaround**

Keep requests small where possible, or enforce higher-level timeout handling around SDK usage.

## 5. Pagination helpers are missing

**What happens**

Cursor-aware endpoints like `x_post_retweeters()`, `x_user_posts()`, `list_people_tasks()`, and `list_people_profiles()` return typed responses with cursor fields, but the SDK does not auto-follow them. The TikTok, Instagram, and Facebook list methods return one page; their cursor is only available as `metadata.next_cursor` with `include_metadata=True`. People Search task results are the exception: `iter_people_results()` follows `next_cursor` for you.

**Why unresolved**

No iterator abstraction or paginator helper exists in the current client.

**Impact**

Consumers must manage cursors manually across multiple requests.

**Workaround**

Persist `next_cursor` from each response (or from `response.metadata.next_cursor` for the social list methods) and pass it into the next request yourself. See the pagination example in the README.

## 6. Extraction methods return raw text only

**What happens**

`extract()` and the legacy `web_crawl()` method return `response.text()` directly, not a typed model.

**Why unresolved**

The method is implemented as a lightweight passthrough for `text` or `html` output.

**Impact**

Callers must parse returned content themselves.

**Workaround**

Treat the response as raw HTML or text and parse it in application code.

## 7. Specialized request paths still require coordinated transport updates

**What happens**

`x_posts_by_urls()` and `_handle_text_request()` (`extract` and `web_crawl`) bypass the JSON wrapper `_handle_request()` for their special response and parameter shapes. HTTP failures from all three paths go through `_exchange()` and are raised as `DesearchAPIError`.

**Why unresolved**

The SDK needs different success-path parsing for repeated query parameters, JSON responses, and text responses.

**Impact**

Success-path parsing is still separate. HTTP error handling is shared, so an API key in request headers is not copied onto the raised error.

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
| AI search streaming unavailable | Medium | Use full-response search only |
| Mixed typed and raw dict returns | Medium | Add runtime type checks |
| No retry/backoff | Medium | Retry in caller |
| Fixed 120 second timeout | Low | Control timeout behavior at the caller layer |
| No pagination helpers (except People Search results) | Low | Manually reuse cursor values |
| Extraction methods return raw text | Low | Parse returned content yourself |
| Specialized request paths | Low | Audit special-case methods during transport changes |
| Legacy Sphinx branding | Info | Ignore `docs/_build/` as a source of truth |
