# Feature Inventory — desearch-py SDK

> Status key: ✅ working · ⚠️ degraded · ❌ broken · 🚧 in progress

This inventory is derived from the current source in `desearch_py/api.py`, `desearch_py/models.py`, `pyproject.toml`, and `setup.py`. Current package version: **1.12.0**.

## Overview

The SDK exposes one async client class, `Desearch`, plus a large set of typed models and enums re-exported from `desearch_py/__init__.py`.

## Client lifecycle

| Surface | Status | Notes |
|---|---|---|
| `Desearch(api_key, base_url=...)` | ✅ | Base URL defaults to `https://api.desearch.ai` and is normalized with `rstrip("/")`. |
| Lazy session creation | ✅ | `aiohttp.ClientSession` is created only when first needed. |
| `async with Desearch(...)` | ✅ | `__aenter__` opens the session, `__aexit__` calls `close()`. |
| `close()` | ✅ | Closes the underlying session when present. |
| Shared request helper | ✅ | `_exchange()` applies a 120 second timeout. JSON methods use `_handle_request()`. HTTP failures raise `DesearchAPIError` with status and body only. |
| Response metadata | ✅ | `include_metadata=True` returns `DesearchResponse` with cost headers and `next_cursor` (`x-desearch-next-cursor`). |
| Path parameter encoding | ✅ | New path-parameter routes percent-encode the value as one segment, `/` included. |

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
| `extract` | `GET /web/extract` | ✅ | Canonical extraction method with text/HTML, JavaScript rendering, and optional wait controls. |
| `web_crawl` | `GET /web/crawl` | ⚠️ legacy | Deprecated compatibility method retained for existing clients. |

## Search API features

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `search_api` | `POST /search` | ✅ | Ranked pages with the best matching passage (`SearchApiResponse`). `mode` (`fast` / `balanced`), `count` (10, 15, 20), `start_date` / `end_date`, `highlights`, `page_text`; unset values are not sent. No method is named plain `search`. |

## TikTok, Instagram, and Facebook features

List methods return one page. `count` is a maximum (1-100). With `include_metadata=True`, `metadata.next_cursor` is the cursor for the next page (`None` on the last page); pass it back unchanged as `cursor`. A list method returns the raw `dict` when the API answers with an object instead of a list.

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `tiktok_search` | `POST /desearch/tiktok/search` | ✅ | `query`, `count`, `cursor`, `sort`. `List[TikTokPost]`. |
| `tiktok_post_by_id` | `GET /desearch/tiktok/post/{id}` | ✅ | `TikTokPost`. |
| `tiktok_profile` | `GET /desearch/tiktok/profile/{username}` | ✅ | `TikTokProfile`. |
| `tiktok_profile_posts` | `GET /desearch/tiktok/profile/{username}/posts` | ✅ | `count`, `cursor`. `List[TikTokPost]`. |
| `tiktok_comments` | `GET /desearch/tiktok/comments/{video_id}` | ✅ | `count`, `cursor`. `List[TikTokComment]`. |
| `tiktok_hashtag` | `GET /desearch/tiktok/hashtag/{tag}` | ✅ | `count`, `cursor`. `List[TikTokPost]`. |
| `tiktok_trending` | `GET /desearch/tiktok/trending` | ✅ | `region`, `count`; no pagination. `List[TikTokPost]`. |
| `instagram_search` | `POST /desearch/instagram/search` | ✅ | `query`, `count`; one page, no `cursor` (the API returns 422 for one). `List[InstagramSearchResult]`. |
| `instagram_media` | `GET /desearch/instagram/media/{id}` | ✅ | Shortcode, media ID, or post URL. `InstagramMedia`. |
| `instagram_profile` | `GET /desearch/instagram/profile/{username}` | ✅ | `InstagramProfile`. |
| `instagram_profile_posts` | `GET /desearch/instagram/profile/{username}/posts` | ✅ | `count`, `cursor`. `List[InstagramMedia]`. |
| `instagram_comments` | `GET /desearch/instagram/comments/{shortcode}` | ✅ | `count`, `cursor`. Shortcode only; numeric IDs return 404. `List[InstagramComment]`. |
| `instagram_hashtag` | `GET /desearch/instagram/hashtag/{tag}` | ✅ | `count`, `cursor`. `List[InstagramMedia]`. |
| `facebook_search` | `POST /desearch/facebook/search` | ✅ | Meta Ad Library records. `query`, `count`, `cursor`. `List[FacebookPost]`. |
| `facebook_post_by_id` | `GET /desearch/facebook/post/{id}` | ✅ | `FacebookPost`. |
| `facebook_profile` | `GET /desearch/facebook/profile/{profile_id}` | ✅ | `FacebookProfile`. |
| `facebook_profile_posts` | `GET /desearch/facebook/profile/{profile_id}/posts` | ✅ | `count`, `cursor`. `List[FacebookPost]`. |
| `facebook_comments` | `GET /desearch/facebook/comments/{post_id}` | ✅ | `count`, `cursor`; about 10 per page. `List[FacebookComment]`. |
| `facebook_hashtag` | `GET /desearch/facebook/hashtag/{tag}` | ✅ | Meta Ad Library records. `count`, `cursor`. `List[FacebookPost]`. |

## YouTube, Reddit, and Threads features

Same paging as TikTok: `include_metadata=True` exposes `metadata.next_cursor`, sent back as `cursor`. These routes take no `count`; each call is billed as one request, including an empty page.

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `youtube_search` | `POST /desearch/youtube/search` | ✅ | `query`, `type`, `upload_date`, `sort_by`, `duration`, `cursor`. `List[YouTubeItem]`. |
| `youtube_video` | `GET /desearch/youtube/video/{id}` | ✅ | ID or URL. `YouTubeVideo`. |
| `youtube_transcript` | `GET /desearch/youtube/transcript/{video_id}` | ✅ | `language`. 404 when there are no captions. `YouTubeTranscript`. |
| `youtube_comments` | `GET /desearch/youtube/comments/{video_id}` | ✅ | `order`, `cursor`. `List[YouTubeComment]`. |
| `youtube_channel` | `GET /desearch/youtube/channel/{handle}` | ✅ | Handle or channel ID. `YouTubeChannel`. |
| `youtube_channel_videos` | `GET /desearch/youtube/channel/{handle}/videos` | ✅ | `sort`, `cursor`. `List[YouTubeItem]`. |
| `reddit_search` | `POST /desearch/reddit/search` | ✅ | `query`, `sort`, `timeframe`, `cursor`. `List[RedditPost]`. |
| `reddit_subreddit` | `GET /desearch/reddit/subreddit/{name}` | ✅ | Case-sensitive name. `RedditSubreddit`. |
| `reddit_subreddit_posts` | `GET /desearch/reddit/subreddit/{name}/posts` | ✅ | `sort`, `timeframe`, `cursor`. `List[RedditPost]`. |
| `reddit_post_by_id` | `GET /desearch/reddit/post/{id}` | ✅ | ID or URL. `RedditPost`. |
| `reddit_comments` | `GET /desearch/reddit/comments/{post_id}` | ✅ | `cursor`. Comment tree. `List[RedditComment]`. |
| `threads_search` | `POST /desearch/threads/search` | ✅ | `query`, `start_date`, `end_date`; no pagination. `List[ThreadsPost]`. |
| `threads_search_users` | `POST /desearch/threads/search/users` | ✅ | `query`. `List[ThreadsUser]`. |
| `threads_profile` | `GET /desearch/threads/profile/{username}` | ✅ | `ThreadsProfile`. |
| `threads_profile_posts` | `GET /desearch/threads/profile/{username}/posts` | ✅ | Latest posts; no pagination. `List[ThreadsPost]`. |
| `threads_post_by_id` | `GET /desearch/threads/post/{id}` | ✅ | URL or shortcode. `ThreadsPostDetail`. |

## Network stats features

Public routes: no API key is needed and they are free.

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `network_stats` | `GET /network/stats` | ✅ | `NetworkStatsResponse`: current counters and per-second rates (an estimate). |
| `network_stats_history` | `GET /network/stats/history` | ✅ | `NetworkStatsHistoryResponse`: one point per second for the last 20 minutes. |
| `stream_network_stats` | `GET /network/stats/stream` | ✅ | Async iterator of `NetworkStatsEvent` from Server-Sent Events. `last_event_id` resumes (replay up to 20 minutes). No auto-reconnect. 60 second read timeout, no total timeout. |

## People Search features

Searches run as background tasks. Only the four search methods are billed (per profile delivered); every task, results, export, and profiles call is free.

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `x_profile_search` | `POST /desearch/people/search/x` | ✅ | Typed `XProfileSearchFilters` or a dict. Optional `metadata` labels and `Idempotency-Key`. Returns `PeopleTask` (with `metadata`). |
| `youtube_creator_search` | `POST /desearch/people/search/youtube` | ✅ | Typed `YouTubeCreatorSearchFilters` or a dict. Optional `Idempotency-Key`. |
| `linkedin_profile_search` | `POST /desearch/people/search/linkedin` | ✅ | Typed `LinkedInProfileSearchFilters` or a dict. Optional `Idempotency-Key`. |
| `tiktok_creator_search` | `POST /desearch/people/search/tiktok` | ✅ | Typed `TikTokCreatorSearchFilters` or a dict. Optional `Idempotency-Key`. |
| `list_people_tasks` | `GET /desearch/people/tasks` | ✅ | `platform`, `status` (list or comma string), `limit`, `cursor`, and a `metadata` filter sent as `metadata.<key>=<value>` params. |
| `get_people_task` | `GET /desearch/people/tasks/{task_id}` | ✅ | Returns `PeopleTask`, with `completion_reason`, `coverage_limited`, and `warnings` (`PeopleTaskWarning`). |
| `get_people_results` | `GET /desearch/people/tasks/{task_id}/results` | ✅ | One page; pass `next_cursor` back as `cursor`. Each `Person` has `score.criteria_checks` (`PeopleCriterionCheck`), `score.fully_verified`, and the `enrichment` / `enrichment_error` properties. |
| `pause_people_task` / `resume_people_task` / `cancel_people_task` | `POST /desearch/people/tasks/{task_id}/{pause,resume,cancel}` | ✅ | HTTP 409 raises `PeopleTaskConflictError` with the task's current state. |
| `export_people_results` | `GET /desearch/people/tasks/{task_id}/export` | ✅ | CSV or JSON Lines text, with result filters. |
| `list_people_profiles` | `GET /desearch/people/profiles` | ✅ | `platform`, `q`, `sort`, `limit`, `cursor`, result filters. |
| `export_people_profiles` | `GET /desearch/people/profiles/export` | ✅ | CSV or JSON Lines text, with result filters. |
| `wait_for_people_task` | polls `GET /desearch/people/tasks/{task_id}` | ✅ | Defaults: every 5 s, 600 s timeout, then `PeopleTaskTimeoutError`. |
| `iter_people_results` | pages `GET /desearch/people/tasks/{task_id}/results` | ✅ | Async iterator of `Person`; stops when no more results are available now. |

### Result filter coverage

| Filter | Sent as | Status |
|---|---|---|
| `has` | comma-separated channels | ✅ |
| `min_audience` / `max_audience` | integers | ✅ |
| `min_score` | integer 0-100 | ✅ |
| `location` | text | ✅ |
| `verified` | `true` / `false` | ✅ |

## Company Search features

Company Search and Company Enrich run as background tasks on the People Search engine. Only `company_search` and `company_enrich` are billed (per company delivered); every task, results, and export call is free. A People Search task ID is a 404 on these routes.

| Method | Endpoint | Status | Notes |
|---|---|---|---|
| `company_search` | `POST /desearch/companies/search` | ✅ | `query`, `count`, `min_score`, `exclude`, `roles` (`CompanyRole`), `infer_emails`, `verify_emails`, typed `CompanySearchFilters` (`countries`, `require`) or a dict, `metadata`, and keyword-only `max_cost_usd` (search budget) and `continue_from` (an ended search's `task_id`), sent only when given. Optional `Idempotency-Key`. Returns `CompanyTask`. |
| `company_enrich` | `POST /desearch/companies/enrich` | ✅ | `domains` (1-200 domains or URLs), `roles`, `infer_emails`, `verify_emails`, `metadata`. Optional `Idempotency-Key`. Returns `CompanyTask`. |
| `list_company_tasks` | `GET /desearch/companies/tasks` | ✅ | `type` (`search` or `enrich`), `status` (list or comma string), `limit`, `cursor`, and a `metadata` filter sent as `metadata.<key>=<value>` params. |
| `get_company_task` | `GET /desearch/companies/tasks/{task_id}` | ✅ | Returns `CompanyTask`, with `stage` (`enriching` while published companies are filled in), `progress`, `completion_reason` (`CompanyCompletionReason`), `coverage_limited`, and `warnings` (`CompanyTaskWarning`). |
| `get_company_results` | `GET /desearch/companies/tasks/{task_id}/results` | ✅ | One page of `Company`; pass `next_cursor` back as `cursor` for new companies only, or read without it for the latest version of each. Every field a later stage fills in is optional. |
| `pause_company_task` / `resume_company_task` / `cancel_company_task` | `POST /desearch/companies/tasks/{task_id}/{pause,resume,cancel}` | ✅ | HTTP 409 raises `CompanyTaskConflictError` with the task's current state. |
| `export_company_results` | `GET /desearch/companies/tasks/{task_id}/export` | ✅ | CSV (one row per company) or JSON Lines text. |
| `wait_for_company_task` | polls `GET /desearch/companies/tasks/{task_id}` | ✅ | Defaults: every 5 s, 600 s timeout, then `CompanyTaskTimeoutError`. |
| `iter_company_results` | pages `GET /desearch/companies/tasks/{task_id}/results` | ✅ | Async iterator of `Company`; stops when no more companies are available now. |

### Company result coverage

| Field | Model | Status |
|---|---|---|
| `emails`, `primary_email`, `people[].emails` | `CompanyEmail`, with `verification` (`CompanyEmailVerification`, `CompanyEmailChecks`) | ✅ |
| `phones`, `socials`, `pages`, `location` | `CompanyPhone`, `CompanySocial`, `CompanyPage`, `CompanyLocation` | ✅ |
| `people` | `CompanyPerson`, with `evidence` (`CompanyPersonEvidence`) | ✅ |
| `primary_contact`, `contact_coverage` | `CompanyPrimaryContact`, `CompanyContactCoverage` | ✅ |
| `enrichment` | `CompanyEnrichment`, `CompanyEnrichmentStages`, `CompanyEnrichmentError` | ✅ |
| `score` (`None` for Company Enrich) | `CompanyScore`, with `criteria_checks` (`PeopleCriterionCheck`) and `unverified_criteria` | ✅ |
| `found_by` | `CompanyFoundBy` | ✅ |

## Models and exports

| Surface | Status | Notes |
|---|---|---|
| Enums exported from package root | ✅ | `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `SearchApiMode`, `PeoplePlatform`, `PeopleTaskStatus`, `PeopleProfileSort`, `PeopleExportFormat`, `PeopleChannel`, `PeopleCompletionReason`, `PeopleCriterionVerdict`, `PeopleEnrichment`, `PeopleEnrichmentError`, `CompanyTaskType`, `CompanyRole`, `CompanyRequirement`, `CompanyCompletionReason`, `CompanyEmailStatus` are all re-exported. |
| Response models exported from package root | ✅ | Core search, Search API, web, X, TikTok, Instagram, Facebook, YouTube, Reddit, Threads, network stats, People Search, Company Search, and error models are re-exported. |
| Forward-compatible parsing | ✅ | Models use `ConfigDict(extra="allow")` to tolerate extra API fields. |
| Strict schema enforcement | ❌ | The SDK intentionally does not reject unknown fields. |
| Type marker file | ✅ | `desearch_py/py.typed` is included in package data. |

## Packaging and docs tooling

| Surface | Status | Notes |
|---|---|---|
| Poetry metadata in `pyproject.toml` | ✅ | Declares package name `desearch-py`, version `1.12.0`, and runtime deps. |
| setuptools metadata in `setup.py` | ✅ | Declares import package `desearch_py` and package data; reads the version from `desearch_py.__version__`. |
| Version parity between Poetry and setuptools | ✅ | `desearch_py.__version__` (`1.12.0`) is the source of truth; `tests/test_version_consistency.py` checks `pyproject.toml` and `setup.py` match it. |
| Sphinx source files | ✅ | `docs/conf.py`, `docs/index.rst`, `docs/endpoints.rst` (the social, Search API, and network stats methods), `docs/Makefile`, and `docs/make.bat` are present. |
| Sphinx branding correctness | ❌ | `docs/conf.py` and generated `docs/_build/` still carry legacy `datura-py` / `Leva` metadata. |

## Status summary

| Category | ✅ | ⚠️ | ❌ | 🚧 |
|---|---|---|---|---|
| Client lifecycle | 7 | 0 | 0 | 0 |
| AI search | 2 | 1 | 1 | 0 |
| Search API | 1 | 0 | 0 | 0 |
| TikTok / Instagram / Facebook | 19 | 0 | 0 | 0 |
| YouTube / Reddit / Threads | 16 | 0 | 0 | 0 |
| Network stats | 3 | 0 | 0 | 0 |
| X / Twitter | 3 | 6 | 0 | 0 |
| Web | 1 | 1 | 0 | 0 |
| People Search | 13 | 0 | 0 | 0 |
| Company Search | 9 | 0 | 0 | 0 |
| Models / exports | 4 | 0 | 1 | 0 |
| Packaging / docs tooling | 4 | 0 | 1 | 0 |
