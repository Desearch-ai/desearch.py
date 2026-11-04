# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: the version in this repository is 1.13.0, but the latest release
> published on PyPI is 1.2.1. Versions 1.3.0 through 1.6.2 were never published
> to PyPI and are not recorded individually here.

## [1.13.0] - unreleased (not yet published to PyPI)

> Waits for the Monitors API release (desearch-public-api#625 and #630, on
> api-dev only, plus #635 and its console migration for TikTok and watched
> accounts, and #644 and its console migration for Instagram, Facebook, Meta
> ads, Threads accounts and `webhook.last_delivery`). Until then the
> production API returns 404 for these routes.
> 1.12.0 is the Company Search budget release (desearch.py#40); if this lands
> first, ship it as 1.12.0 instead.

### Added

- **Monitors**: searches that run on a schedule over web, X, Reddit, YouTube,
  Threads, TikTok and Meta ads, or read watched accounts (also on Instagram
  and Facebook), and keep only new items an AI classifier screens as
  relevant.
  `create_monitor`, `estimate_monitor`, `list_monitors`, `get_monitor`,
  `update_monitor` (only the given fields are sent; `remove_webhook=True`
  sends `webhook: null`), `pause_monitor`, `resume_monitor`,
  `delete_monitor`, `trigger_monitor`, `list_monitor_runs`,
  `get_monitor_run`, `list_monitor_items`, `test_monitor_webhook` and
  `rotate_monitor_webhook_secret`. Every route is free; runs are billed.
- TikTok as a monitor source (`MonitorSource.TIKTOK`, `options.tiktok.count`)
  and watched accounts, read instead of searching: `options.x.accounts`,
  `options.reddit.subreddits`, `options.youtube.channels` and
  `options.tiktok.accounts` (`MonitorXOptions`, `MonitorRedditOptions`,
  `MonitorYouTubeOptions`, `MonitorTikTokOptions`; at most 10 each). A TikTok
  keyword monitor finds a new video only when it reaches TikTok's top results;
  to follow creators, watch their accounts.
- Instagram, Facebook and Meta ads as monitor sources (`MonitorSource.INSTAGRAM`,
  `FACEBOOK`, `META_ADS`) and Threads watched accounts, following
  desearch-public-api#644: `options.instagram.accounts` and
  `options.facebook.pages` (1-10 each; those sources only read watched
  accounts, so create and update return 422 without any),
  `options.meta_ads.count` (10, 20 or 30 Ad Library results per run; the
  query should be a keyword) and `options.threads.accounts`
  (`MonitorInstagramOptions`, `MonitorFacebookOptions`,
  `MonitorMetaAdsOptions`, `MonitorThreadsOptions`). The docs list the item
  `data` fields of each (Threads `likes`; Instagram `likes`, `comments`,
  `views`, `media_type`, `thumbnail`; Facebook `reactions`, `comments`,
  `shares`; Meta ads `page`, `active`, `cta`, `link`, `platforms`,
  `thumbnail`) and `signals["criteria"]`.
- Watched hashtags on TikTok and Instagram: `options.tiktok.hashtags` and
  `options.instagram.hashtags` (`MonitorTikTokOptions.hashtags`,
  `MonitorInstagramOptions.hashtags`; at most 10 each, in any script, `skincare`,
  `#სილამაზე` or a tag URL). A hashtag feed lists posts from any account, so a
  monitor finds posts outside the accounts it watches. Instagram needs
  accounts or hashtags. A hashtag that cannot be read is listed in
  `stats["sources"][source]["hashtags_failed"]`, and items read from one have
  `data["hashtag"]`. TikTok, Instagram and Facebook items document `post_id`,
  `type`, `hashtags`, `mentions`, `media`, TikTok `saves` and Facebook
  `views`; `stats["screen"]` is `ai` or `keyword`.
- Monitors billing as documented: TikTok, Instagram, Facebook and Meta ads
  reads are billed per read ($3.00 per 1,000 reads), whatever the number of
  posts a read returns: one per watched account, hashtag, Facebook page,
  TikTok keyword search or Ad Library page. An empty or private TikTok
  account takes two reads. X timelines, subreddits, YouTube channels and
  Threads keep their list prices.
- `Monitor.webhook.last_delivery`, a `MonitorWebhookDelivery` (`event`,
  `status` `pending`/`delivered`/`failed`, `attempts`, `status_code`, `error`,
  `created_at`, `next_attempt_at`, `delivered_at`), `None` before the first
  delivery.
- `facebook_search(..., sort=...)`: `impressions` (the API default) or
  `recent`, which puts recently started ads first.
- `wait_for_monitor_run` (raises `MonitorRunTimeoutError`) and
  `iter_monitor_items`, which follows `next_cursor`.
- `verify_webhook_signature(secret, header, body)` in `desearch_py.webhooks`,
  re-exported from the package root, with `SIGNATURE_HEADER` and
  `DEFAULT_TOLERANCE_SECONDS`: checks `Desearch-Signature: t=<unix>,v1=<hex>`
  (HMAC-SHA256 of `"<t>.<raw body>"` keyed with the `webhook_secret`),
  rejects timestamps more than 5 minutes off and compares in constant time.
- Models `Monitor`, `MonitorList`, `MonitorRun`, `MonitorRunWithItems`,
  `MonitorRunList`, `MonitorItem`, `MonitorItemList`, `MonitorEstimate`,
  `MonitorDeleted`, `MonitorWebhook`, `MonitorWebhookTest`,
  `MonitorWebhookSecret`, `MonitorWebhookEvent` (a delivery body),
  `MonitorWebhookMonitor`, `MonitorLastRun` and `MonitorStats`; request
  models `MonitorCreateRequest`, `MonitorUpdateRequest`,
  `MonitorEstimateRequest`, `MonitorOptions`, `MonitorWebOptions`,
  `MonitorXOptions`, `MonitorRedditOptions`, `MonitorYouTubeOptions`,
  `MonitorTikTokOptions`, `MonitorThreadsOptions`, `MonitorInstagramOptions`,
  `MonitorFacebookOptions`, `MonitorMetaAdsOptions` and
  `MonitorWebhookConfig`; `MonitorWebhookDelivery`; enums `MonitorSource`,
  `MonitorInterval`, `MonitorEvent`, `MonitorStatus` and `MonitorRunStatus`;
  and `MONITOR_RUN_ENDED_STATUSES`.
- `scripts/e2e_monitors.py`, a live smoke test of every Monitors method
  (`--base-url`, `--key-env`, `--with-run` for one billed run, `--with-accounts`
  for TikTok and watched accounts, `--with-social` for Instagram, Facebook,
  Meta ads and Threads accounts without a run; it deletes every monitor it
  creates; not run by CI).

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
