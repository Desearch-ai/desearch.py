# Feature Inventory — desearch-py SDK

> Status key: ✅ working · ⚠️ degraded (partial/caveats) · ❌ broken · 🚧 in progress

All methods are implemented in `desearch_py/api.py` and exposed via `desearch_py/__init__.py`. Version: **1.2.0**.

---

## AI Search

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `ai_search` | `POST /desearch/ai/search` | ✅ | Multi-source AI search. Returns `ResponseData` or raw `dict` on parse failure. `streaming` is hardcoded to `False` (streaming not yet exposed publicly). |
| `ai_web_links_search` | `POST /desearch/ai/search/links/web` | ✅ | Raw link results from web sources. Returns `WebSearchResponse`. |
| `ai_x_links_search` | `POST /desearch/ai/search/links/twitter` | ✅ | X post links via AI. Returns `XLinksSearchResponse`. |

### Supported AI tools

Tools are passed as string literals to the `tools` parameter of `ai_search`, `ai_web_links_search`.

| Tool string | Source | Valid in `ai_search` | Valid in `ai_web_links_search` |
|---|---|---|---|
| `web` | General web | ✅ | ✅ |
| `twitter` | X / Twitter | ✅ | ❌ (uses `ai_x_links_search`) |
| `reddit` | Reddit | ✅ | ✅ |
| `hackernews` | Hacker News | ✅ | ✅ |
| `wikipedia` | Wikipedia | ✅ | ✅ |
| `youtube` | YouTube | ✅ | ✅ |
| `arxiv` | arXiv | ✅ | ✅ |

### Supported date filters

Used via `DateFilter` enum or string literal in `ai_search`:

- `PAST_24_HOURS` (default)
- `PAST_2_DAYS`
- `PAST_WEEK`
- `PAST_2_WEEKS`
- `PAST_MONTH`
- `PAST_2_MONTHS`
- `PAST_YEAR`
- `PAST_2_YEARS`

---

## X / Twitter Data

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `x_search` | `GET /twitter` | ✅ | Full X search with filters. Falls back to `dict` if response is not a list. |
| `x_posts_by_urls` | `GET /twitter/urls` | ✅ | Batch-fetch tweets by URL. |
| `x_post_by_id` | `GET /twitter/post` | ✅ | Single tweet by ID. |
| `x_posts_by_user` | `GET /twitter/post/user` | ✅ | User timeline with optional query. Falls back to `dict`. |
| `x_post_retweeters` | `GET /twitter/post/retweeters` | ✅ | Retweeter list with cursor pagination. |
| `x_user_posts` | `GET /twitter/user/posts` | ✅ | User timeline. |
| `x_user_replies` | `GET /twitter/replies` | ✅ | User's tweets + replies. Falls back to `dict`. |
| `x_post_replies` | `GET /twitter/replies/post` | ✅ | Replies to a tweet. Falls back to `dict`. |
| `x_trends` | `GET /twitter/trends` | ✅ | Trending topics by WOEID. |

---

## Web Search and Crawl

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `web_search` | `GET /web` | ✅ | SERP-style results. Returns `WebSearchResultsResponse`. |
| `web_crawl` | `GET /web/crawl` | ✅ | Returns raw `str` (HTML or plain text). 120 s timeout. |

---

## Pydantic Models (exported)

### Core response models

| Model | Used by |
|---|---|
| `ResponseData` | `ai_search` |
| `WebSearchResponse` | `ai_web_links_search` |
| `WebSearchResultsResponse` | `web_search` |
| `XLinksSearchResponse` | `ai_x_links_search` |
| `XRetweetersResponse` | `x_post_retweeters` |
| `XUserPostsResponse` | `x_user_posts` |
| `XTrendsResponse` | `x_trends` |

### Twitter / X models

| Model | Description |
|---|---|
| `TwitterScraperTweet` | Individual tweet with user, counts, media, entities |
| `TwitterScraperUser` | User profile data |
| `TwitterScraperEntities` | Tweet entities (hashtags, mentions, URLs, media) |
| `TwitterScraperEntitiesMedia` | Media attachment (image, video, animated GIF) |
| `TwitterScraperExtendedEntities` | Extended media variant |
| `TwitterScraperMedia` | Simplified media reference |
| `XTrendItem` | Single trend entry |
| `XTrendsWoeid` | Location metadata for trends |

### Enums

| Enum | Values |
|---|---|
| `Tool` | `web`, `hackernews`, `reddit`, `wikipedia`, `youtube`, `twitter`, `arxiv` |
| `WebTool` | Same as `Tool` minus `twitter` |
| `DateFilter` | `PAST_24_HOURS` … `PAST_2_YEARS` |
| `ResultType` | `ONLY_LINKS`, `LINKS_WITH_FINAL_SUMMARY` |
| `Sort` | `Top`, `Latest` |

### Error models

| Model | HTTP status |
|---|---|
| `ValidationError` | 422 |
| `HTTPValidationError` | 422 |
| `UnauthorizedResponse` | 401 |
| `TooManyRequestsResponse` | 429 |
| `InternalServerErrorResponse` | 500 |
| `MovedPermanentlyResponse` | 301 |

---

## Feature status summary

| Category | ✅ | ⚠️ | ❌ | 🚧 |
|---|---|---|---|---|
| AI Search | 3 | 0 | 0 | 0 |
| X / Twitter | 9 | 0 | 0 | 0 |
| Web | 2 | 0 | 0 | 0 |
| Models / Enums | all exported | — | — | — |
