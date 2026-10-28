# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

> Note: the version in this repository is currently 1.6.1, but the latest release
> published on PyPI is 1.2.1. Versions 1.3.1 through 1.6.1 were not released
> individually and are not recorded here.

## [Unreleased]

### Removed

- **Breaking change: YouTube removed from AI search tool options** ([#21]).
  `Tool.YOUTUBE` and `WebTool.YOUTUBE` are gone, along with
  `WebSearchResponse.youtube_search_results` and `ResponseData.youtube_search`.
  The API already rejects `'youtube'` / `'Youtube Search'` with HTTP 422, so
  callers passing them were getting errors anyway.
- **Breaking change: Python 3.9 no longer supported.** `python_requires` is now
  `>=3.10`, and CI tests on Python 3.10 and 3.12.

### Changed

- The version is single-sourced from `desearch_py.__version__`. `setup.py`
  reads it from `desearch_py/__init__.py`, and
  `tests/test_version_consistency.py` checks that `pyproject.toml` matches.

[#21]: https://github.com/Desearch-ai/desearch.py/pull/21
