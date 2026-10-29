# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: the version in this repository is 1.10.0, but the latest release
> published on PyPI is 1.2.1. Versions 1.3.0 through 1.6.2 were never published
> to PyPI and are not recorded individually here.

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
