# Feature Inventory — desearch-py SDK

> Status key: ✅ working · ⚠️ degraded · ❌ broken · 🚧 in progress

This inventory is derived from the current source in `desearch_py/api.py`, `desearch_py/models.py`, `pyproject.toml`, and `setup.py`. Current package version: **1.2.0**.

## Overview

The SDK exposes one async client class, `Desearch`, plus a large set of typed models and enums re-exported from `desearch_py/__init__.py`.

## Client lifecycle

| Surface | Status | Notes |
|---|---|---|
| `Desearch(api_key, base_url=...)` | ✅ | Base URL defaults to `https://api.desearch.ai` and is normalized with `rstrip("/")`. |
| Lazy session creation | ✅ | `aiohttp.ClientSession` is created only when first needed. |
| `async with Desearch(...)` | ✅ | `__aenter__` opens the session, `__aexit__` calls `close()`. |
| `close()` | ✅ | Closes the underlying session when present. |
| Shared request helper | ✅ | `_handle_request()` applies a 120 second timeout and JSON parsing. |

## AI search features

| Method | Endpoint | Status | Why this status |
|---|---|---|---|
| `ai_search` | `POST /desearch/ai/search` | ⚠️ degraded | Works, but streaming is hardcoded off and the method can fall back to raw `dict` output when model parsing fails. |
| `ai_web_links_search` | `POST /desearch/ai/search/links/web` | ✅ | Returns typed `WebSearchResponse` data from supported web-like sources. |
| `ai_x_links_search` | `POST /desearch/ai/search/links/twitter` | ✅ | Returns typed `XLinksSearchResponse` results for X links. |

### Supported AI tools

| Tool string | Source | `ai_search` | `ai_web_links_search` |
|---|---|---|---|
| `web` | General web | ✅ | ✅ |
| `hackernews` | Hacker News | ✅ | ✅ |
| `reddit` | Reddit | ✅ | ✅ |
| `wikipedia` | Wikipedia | ✅ | ✅ |
| `youtube` | YouTube | ✅ | ✅ |
| `arxiv` | arXiv | ✅ | ✅ |
| `twitter` | X / Twitter | ✅ | ❌ |

`twitter` is excluded from `ai_web_links_search` because that method has a dedicated X-specific sibling, `ai_x_links_search`.

### AI search option coverage

| Option | Status | Notes |
|---|---|---|
| `date_filter` | ✅ | Defaults to `PAST_24_HOURS`. |
| explicit `start_date` / `end_date` | ✅ | Included when provided. |
| `result_type` | ✅ | Defaults to `LINKS_WITH_FINAL_SUMMARY`. |
| `system_message` | ✅ | Passed through when provided. |
| `scoring_system_message` | ✅ | Passed through when provided. |
| `count` | ✅ | Optional per-source result count. |
| streaming responses | ❌ | Public SDK path is not implemented, `streaming` is always sent as `False`. |

## X / Twitter features

| Method | Endpoint | Status | Why this status |
|---|---|---|---|
| `x_search` | `GET /twitter` | ⚠️ degraded | Works with many filters, but returns raw `dict` output if the API does not return a list. |
| `x_posts_by_urls` | `GET /twitter/urls` | ✅ | Batch URL lookup works and returns typed tweet models. |
| `x_post_by_id` | `GET /twitter/post` | ✅ | Single post lookup returns a typed tweet model. |
| `x_posts_by_user` | `GET /twitter/post/user` | ⚠️ degraded | Works, but may return raw `dict` output instead of typed tweets. |
| `x_post_retweeters` | `GET /twitter/post/retweeters` | ⚠️ degraded | Typed response works, but pagination is manual via `next_cursor`. |
| `x_user_posts` | `GET /twitter/user/posts` | ⚠️ degraded | Typed response works, but pagination is manual via `next_cursor`. |
| `x_user_replies` | `GET /twitter/replies` | ⚠️ degraded | Works, but may return raw `dict` output instead of typed tweets. |
| `x_post_replies` | `GET /twitter/replies/post` | ⚠️ degraded | Works, but may return raw `dict` output instead of typed tweets. |
| `x_trends` | `GET /twitter/trends` | ✅ | Returns typed trends plus location metadata. |

### X filter coverage in `x_search`

| Filter | Status |
|---|---|
| `sort` | ✅ |
| `user` | ✅ |
| `start_date` / `end_date` | ✅ |
| `lang` | ✅ |
| `verified` / `blue_verified` | ✅ |
| `is_quote` / `is_video` / `is_image` | ✅ |
| `min_retweets` / `min_replies` / `min_likes` | ✅ |
| `count` | ✅ |

## Web features

| Method | Endpoint | Status | Why this status |
|---|---|---|---|
| `web_search` | `GET /web` | ✅ | Returns typed `WebSearchResultsResponse` data. |
| `web_crawl` | `GET /web/crawl` | ⚠️ degraded | Works, but returns raw text instead of a typed model and duplicates direct request logic. |

## Models and exports

| Surface | Status | Notes |
|---|---|---|
| Enums exported from package root | ✅ | `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort` are all re-exported. |
| Response models exported from package root | ✅ | Core search, web, X, and error models are re-exported. |
| Forward-compatible parsing | ✅ | Models use `ConfigDict(extra="allow")` to tolerate extra API fields. |
| Strict schema enforcement | ❌ | The SDK intentionally does not reject unknown fields. |
| Type marker file | ✅ | `desearch_py/py.typed` is included in package data. |

## Packaging and docs tooling

| Surface | Status | Notes |
|---|---|---|
| Poetry metadata in `pyproject.toml` | ✅ | Declares package name `desearch-py`, version `1.2.0`, and runtime deps. |
| setuptools metadata in `setup.py` | ✅ | Declares import package `desearch_py`, version `1.2.0`, and package data. |
| Version parity between Poetry and setuptools | ✅ | Both files currently declare `1.2.0`. |
| Sphinx source files | ✅ | `docs/conf.py`, `docs/index.rst`, `docs/Makefile`, and `docs/make.bat` are present. |
| Sphinx branding correctness | ❌ | `docs/conf.py` and generated `docs/_build/` still carry legacy `datura-py` / `Leva` metadata. |

## Status summary

| Category | ✅ | ⚠️ | ❌ | 🚧 |
|---|---|---|---|---|
| Client lifecycle | 5 | 0 | 0 | 0 |
| AI search | 2 | 1 | 1 | 0 |
| X / Twitter | 3 | 6 | 0 | 0 |
| Web | 1 | 1 | 0 | 0 |
| Models / exports | 4 | 0 | 1 | 0 |
| Packaging / docs tooling | 4 | 0 | 1 | 0 |
