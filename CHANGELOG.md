# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: the version in this repository is 1.8.0, but the latest release
> published on PyPI is 1.2.1. Versions 1.3.0 through 1.7.0 were never published
> to PyPI, and 1.3.0 through 1.6.2 are not recorded individually here.

## [1.8.0] - unreleased (not yet published to PyPI)

### Added

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
