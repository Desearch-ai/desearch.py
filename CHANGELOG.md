# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: the version in this repository is 1.12.0, but the latest release
> published on PyPI is 1.2.1. Versions 1.3.0 through 1.6.2 were never published
> to PyPI and are not recorded individually here.

## [1.12.0] - unreleased (not yet published to PyPI)

> Waits for the Company Search API release that adds `max_cost_usd` and
> `continue_from` (desearch-public-api#624). Until then the API rejects a
> request that sends either one with HTTP 422; requests without them work as
> before.

### Added

- `company_search(..., max_cost_usd=...)`: a search budget in USD (above 0, at
  most 100, at least what `count` reserves at the route price; the API returns
  422 below that). Without it, a search stops once it costs more than the
  companies it found pay for (`completion_reason` `cost_limit`,
  `coverage_limited`). With it, the whole budget is reserved, the search keeps
  going until it delivers `count` or spends the budget, and its search effort
  is billed where the companies delivered do not cover it, up to the budget,
  even when it finds few companies or none. The unused budget is returned.
- `company_search(..., continue_from=...)`: the `task_id` (string or `UUID`)
  of an ended Company Search of the same account. The new search leaves out
  every company that one delivered, held for review or excluded. The API
  returns 409 while that task is running or paused, and 404 if it is not the
  caller's Company Search.
- Both are keyword-only, sent only when given, and fields of
  `CompanySearchRequest`.
- Documented the task fields that come with them: `progress["effort_units"]`
  (budgeted searches only), `request.max_cost_usd` and
  `request.continue_from`. Also documented a query that names the only
  companies wanted with their websites: it checks only those domains
  (`interpreted["interpretation"]["only_domains"]`) and ends with
  `completion_reason` `all_domains_processed`, or gets the warning
  `scope_not_applied` when it names them without their websites.

### Fixed

- The `company_search` docstring and the README said Company Search bills a
  minimum of 2 companies when it delivers any. Since the 2026-11-02 price
  release the minimum is 1, as for Company Enrich.

## [1.11.0] - unreleased (not yet published to PyPI)

Full API coverage (TikTok, Instagram, Facebook, Search API, network stats;
desearch.py#35) and YouTube, Reddit and Threads (desearch.py#38) ship together
in this release.

### Added

- **YouTube**: `youtube_search`, `youtube_video`, `youtube_transcript`,
  `youtube_comments`, `youtube_channel`, and `youtube_channel_videos`, with the
  models `YouTubeItem`, `YouTubeVideo`, `YouTubeTranscript`,
  `YouTubeTranscriptSegment`, `YouTubeComment`, `YouTubeCommentAuthor`,
  `YouTubeChannel`, `YouTubeChannelRef`, `YouTubeChapter`, and
  `YouTubeCaptionLanguage`.
- **Reddit**: `reddit_search`, `reddit_subreddit`, `reddit_subreddit_posts`,
  `reddit_post_by_id`, and `reddit_comments`, with the models `RedditPost`,
  `RedditComment` (a tree: `replies` holds nested `RedditComment` items), and
  `RedditSubreddit`.
- **Threads**: `threads_search`, `threads_search_users`, `threads_profile`,
  `threads_profile_posts`, and `threads_post_by_id`, with the models
  `ThreadsPost`, `ThreadsPostDetail`, `ThreadsProfile`, and `ThreadsUser`.
- The six YouTube and Reddit list methods page like the TikTok ones: the
  `x-desearch-next-cursor` header comes back as `metadata.next_cursor` with
  `include_metadata=True`, and goes back as `cursor`. Threads never pages.
  Each call is billed as one request, including an empty page.
- `scripts/e2e_youtube_reddit_threads.py`, a live smoke test of the new
  methods with billing-header checks (`--base-url`, `--key-env`; not run by
  CI).
- **Search API**: `search_api()` for `POST /search`, ranked pages each with
  the passage that best matches the query. Returns `SearchApiResponse`
  (`SearchApiResult` items); `mode` takes `SearchApiMode` or a string. It is
  deliberately not named `search`: llama-index-desearch 0.0.2 still calls a
  legacy `client.search(...)`.
- **TikTok**: `tiktok_search`, `tiktok_post_by_id`, `tiktok_profile`,
  `tiktok_profile_posts`, `tiktok_comments`, `tiktok_hashtag`, and
  `tiktok_trending`, with the models `TikTokPost`, `TikTokProfile`,
  `TikTokComment`, `TikTokAuthor`, `TikTokStats`, and `TikTokMusic`.
- **Instagram**: `instagram_search`, `instagram_media`, `instagram_profile`,
  `instagram_profile_posts`, `instagram_comments`, and `instagram_hashtag`,
  with the models `InstagramMedia`, `InstagramProfile`, `InstagramComment`,
  `InstagramSearchResult`, and `InstagramStats`.
- **Facebook**: `facebook_search`, `facebook_post_by_id`, `facebook_profile`,
  `facebook_profile_posts`, `facebook_comments`, and `facebook_hashtag`, with
  the models `FacebookPost`, `FacebookProfile`, `FacebookComment`,
  `FacebookMedia`, and `FacebookPostStats`. Search and hashtag results are
  Meta Ad Library records.
- **Social pagination**: the TikTok, Instagram, and Facebook list methods take
  `cursor`. `DesearchCostMetadata` has a new `next_cursor` field read from the
  `x-desearch-next-cursor` response header, so `include_metadata=True` returns
  the cursor for the next page (`None` on the last page).
- **Network stats**: `network_stats()`, `network_stats_history()`, and
  `stream_network_stats()`, an async iterator over the
  `GET /network/stats/stream` Server-Sent Events that yields
  `NetworkStatsEvent` items and resumes with `last_event_id`. Models:
  `NetworkStatsResponse`, `NetworkStatsRates`, `NetworkStatsHistoryResponse`,
  `NetworkStatsHistoryPoint`, and `NetworkStatsEvent`. These routes need no API
  key.
- Path parameters of the new methods are percent-encoded as one segment, `/`
  included, so an Instagram post URL works as `instagram_media(id=...)`.
- `scripts/e2e_full_coverage.py`, a live smoke test of the new methods (needs
  `DESEARCH_API_KEY`; not run by CI).

## [1.10.0] - unreleased (not yet published to PyPI)

### Added

- **Company Search and Company Enrich.** Find companies on the web from a
  description (`company_search`), or start from up to 200 domains
  (`company_enrich`), and get each company's public emails, phones, social
  profiles and leaders (CEO, founders, CTO, CFO by default) with their LinkedIn
  profiles and emails. Both run as background tasks on the People Search
  engine, with an optional `idempotency_key`, `metadata` labels and
  `include_metadata=True`, and are billed per company delivered.
- Task methods: `list_company_tasks` (`type` `search` or `enrich`, `status`,
  `limit`, `cursor`, `metadata` filter), `get_company_task`,
  `get_company_results`, `pause_company_task`, `resume_company_task`,
  `cancel_company_task`, and `export_company_results` (CSV or JSON Lines).
- Helpers: `wait_for_company_task` (raises `CompanyTaskTimeoutError`) and
  `iter_company_results` (follows `next_cursor`).
- A 409 from pause, resume or cancel raises `CompanyTaskConflictError`, a
  `DesearchAPIError` subclass carrying the task's current state.
- Request models `CompanySearchRequest`, `CompanySearchFilters` and
  `CompanyEnrichRequest`; task models `CompanyTask`, `CompanyTaskList` and
  `CompanyTaskWarning`; result models `CompanyResultsPage`, `Company`,
  `CompanyEmail`, `CompanyEmailVerification`, `CompanyEmailChecks`,
  `CompanyPhone`, `CompanySocial`, `CompanyPage`, `CompanyLocation`,
  `CompanyPerson`, `CompanyPersonEvidence`, `CompanyPrimaryContact`,
  `CompanyContactCoverage`, `CompanyEnrichment`, `CompanyEnrichmentStages`,
  `CompanyEnrichmentError`, `CompanyScore` (with `unverified_criteria`) and
  `CompanyFoundBy`. Companies fill in stage by stage after they are published
  (`enrichment.status` `partial`, then `complete`), so every field a later
  stage writes is optional. `score` is `None` for Company Enrich.
- Enums `CompanyTaskType`, `CompanyRole`, `CompanyRequirement`,
  `CompanyCompletionReason` (adds `all_domains_processed`) and
  `CompanyEmailStatus`.

## [1.9.0] - unreleased (not yet published to PyPI)

### Added

- `extract(..., format="markdown")` returns the page as markdown (headings,
  lists, tables and code). `full_page` applies to `format="text"` only.

## [1.8.0] - unreleased (not yet published to PyPI)

### Added

- `extract(..., full_page=True)` returns all visible text of the page instead
  of its main content (with `format="text"`).

## [1.7.0] - unreleased (not yet published to PyPI)

### Breaking changes

- **Breaking change: YouTube removed from AI search tool options** ([#21]).
  `Tool.YOUTUBE` and `WebTool.YOUTUBE` are gone, along with
  `WebSearchResponse.youtube_search_results` and `ResponseData.youtube_search`.
  The API already rejects `'youtube'` / `'Youtube Search'` with HTTP 422, so
  callers passing them were getting errors anyway.
- **Breaking change: Python 3.9 no longer supported.** `python_requires` is now
  `>=3.10`, and CI tests on Python 3.10 and 3.12.

### Fixed

- Boolean query params are sent as `"true"` / `"false"` ([#25]). yarl rejects
  bool query values, so `x_search(verified=True)` and the other boolean filters
  failed before any request was sent. `None` params are now dropped.

### Changed

- Tests check that HTTP 422 errors keep their status and diagnostic body
  ([#20]).
- CI runs the test suite on every pull request and push to main, and the PyPI
  publish workflow is gated on it ([#26]).
- The retired-YouTube test is scoped to AI-search tool options, so People
  Search's YouTube Creator Search no longer trips it ([#30]).
- The version is single-sourced from `desearch_py.__version__`. `setup.py`
  reads it from `desearch_py/__init__.py`, and
  `tests/test_version_consistency.py` checks that `pyproject.toml` matches.

[#20]: https://github.com/Desearch-ai/desearch.py/pull/20
[#21]: https://github.com/Desearch-ai/desearch.py/pull/21
[#25]: https://github.com/Desearch-ai/desearch.py/pull/25
[#26]: https://github.com/Desearch-ai/desearch.py/pull/26
[#30]: https://github.com/Desearch-ai/desearch.py/pull/30
