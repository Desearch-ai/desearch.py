# Architecture — desearch-py SDK

This document explains how the SDK is structured today, based on the checked-in source rather than intended future behavior.

## Overview

`desearch-py` is a thin async wrapper over the Desearch HTTP API, including the task-based People Search and Company Search APIs. The codebase is intentionally small and split across three public-facing package files:

- `desearch_py/api.py` contains the async client and every endpoint method.
- `desearch_py/models.py` contains enums plus permissive `pydantic` response models.
- `desearch_py/__init__.py` re-exports the supported public API.

Supporting repo files matter too:

- `pyproject.toml` contains Poetry metadata and dev dependencies.
- `setup.py` keeps setuptools packaging metadata in sync.
- `docs/` contains Markdown notes plus an older Sphinx scaffold.

## Package structure

```text
.
├── desearch_py/
│   ├── __init__.py
│   ├── api.py
│   ├── models.py
│   └── py.typed
├── docs/
│   ├── architecture.md
│   ├── features.md
│   ├── known-issues.md
│   ├── conf.py
│   └── index.rst
├── pyproject.toml
└── setup.py
```

## Core design

### 1. One client object owns all HTTP access

The SDK exposes a single client class, `Desearch`. Every networked feature hangs off that one object instead of being split into sub-clients.

Why this matters:

- auth is configured once at initialization time
- one `aiohttp.ClientSession` can be reused across calls
- the public API stays very small for consumers

### 2. Session creation is lazy

`__init__` stores configuration only. The actual `aiohttp.ClientSession` is created inside `_ensure_session()` when the first request is sent.

Consequence:

- lightweight object construction
- callers can instantiate the client without opening a socket immediately
- unclosed-session risk exists if callers do not use `async with` or `close()`

### 3. Most methods share one request path

`_handle_request()` is the common path for most JSON endpoints. It delegates to `_exchange()`, which centralizes:

- session acquisition
- query param encoding: `None` values are dropped and booleans become `"true"`/`"false"`, because yarl raises `TypeError` for `bool` query values
- a hardcoded `aiohttp.ClientTimeout(total=120)`
- HTTP failures as `DesearchAPIError` (status, reason, and response body only; request headers are not attached)
- JSON decoding
- optional cost metadata extraction from `X-Desearch-*` response headers
- error logging before raise

This keeps the repo small, but it also means the same timeout and JSON expectations are applied broadly.

### 4. Specialized response helpers handle non-JSON endpoints

`x_posts_by_urls()` calls `_exchange()` with repeated `urls` query params. `extract()` and `web_crawl()` share `_handle_text_request()`, which calls `_exchange(..., as_text=True)` instead of the JSON-oriented `_handle_request()`.

Why that appears to exist in the current code:

- `x_posts_by_urls()` needs repeated `urls` query params expressed as a tuple list
- the extraction endpoints return `response.text()` instead of JSON

People Search exports (`export_people_results`, `export_people_profiles`) and `export_company_results` reuse `_handle_text_request()` because the API returns a CSV or JSON Lines file, not JSON.

Tradeoff:

- these methods can support their special request shapes cleanly
- text extraction logic is shared between the canonical and legacy route methods
- all specialized paths still parse the same optional response cost metadata when callers pass `include_metadata=True`

## Data model design

### Permissive schemas over strict schemas

The models use `ConfigDict(extra="allow")` broadly. That is a deliberate tolerance choice visible in the source.

Why this matters:

- the SDK can survive additive API changes without breaking parsing
- unknown response fields remain accessible on model instances
- docs must not over-promise strict schema validation

### Typed when practical, tolerant when needed

Most methods instantiate `pydantic` models directly, but several methods return `Union[..., Dict[str, Any]]` and fall back to raw dictionaries when shape assumptions fail.

That pattern shows the SDK favors resilience over rigid typing for unstable or miner-shaped responses.


### Optional response metadata wrapper

Every public endpoint keeps its existing default return shape. For example, `await client.extract(url="https://desearch.ai")` and the legacy `await client.web_crawl(url="https://desearch.ai")` both return raw text, while `await client.x_search(query="desearch")` returns the parsed tweet list or raw dictionary.

Callers that pass `include_metadata=True` receive `DesearchResponse[data, metadata]` instead. The `data` field contains the same payload the method would have returned by default, and `metadata` is parsed from the same response headers: `X-Desearch-Cost-Usd` (for example `0.00015`), `X-Desearch-Usage-Count`, `X-Desearch-Service`, and `X-Desearch-Currency`. Numeric parse failures become `None` so successful API responses are not turned into SDK errors.

### 5. People Search is task-based

The four People Search methods (`x_profile_search`, `youtube_creator_search`, `linkedin_profile_search`, `tiktok_creator_search`) POST a request body built from typed request models and return a `PeopleTask` at once; the search runs on the server. An optional `idempotency_key` is sent as the `Idempotency-Key` header. The optional `metadata` dict goes in the body as is and comes back on `PeopleTask.metadata`; `list_people_tasks(metadata=...)` sends each pair as a `metadata.<key>=<value>` query param.

Two helpers sit on top of the plain route methods:

- `wait_for_people_task()` polls `get_people_task()` with `asyncio.sleep` until the task status is one of `PEOPLE_TASK_ENDED_STATUSES`, or raises `PeopleTaskTimeoutError`.
- `iter_people_results()` follows `next_cursor` on `get_people_results()` until `has_more` is false.

Result filters are merged from a `PeopleResultFilters` object (or dict) and keyword arguments, then sent as query params: `has` comma-separated and booleans as `true`/`false`, because aiohttp rejects `bool` query values.

A 409 from pause, resume, or cancel is raised as `PeopleTaskConflictError`, a `DesearchAPIError` subclass that also carries the task parsed from the (already redacted) response body. Like other HTTP errors it is raised with no `__cause__` or `__context__`.

### 6. Company Search reuses the task pattern

Company Search and Company Enrich run on the People Search engine, so the SDK mirrors the People Search methods under `/desearch/companies`: `company_search()` and `company_enrich()` POST a body built from `CompanySearchRequest` or `CompanyEnrichRequest` and return a `CompanyTask`, with the same `idempotency_key`, `metadata`, and `include_metadata` handling. `list_company_tasks()` sends `type` (`search` or `enrich`) where `list_people_tasks()` sends `platform`. The routes only see company tasks: a People Search task ID is a 404 there.

The company models are separate from the People Search ones because the result shape differs (`Company` with emails, phones, socials, leaders, and per-stage `enrichment` instead of `Person`). Where the API reuses a People Search model, the SDK does too: `PeopleTaskStatus` and `PEOPLE_TASK_ENDED_STATUSES` for `CompanyTask.status` and `is_finished`, `PeopleTaskLinks`, `PeopleTaskCreatedBy`, `PeopleExportFormat`, and `PeopleCriterionCheck` in `CompanyScore.criteria_checks`. `CompanyScore.unverified_criteria` and `PeopleScore.unverified_criteria` share one rule.

Results fill in stage by stage after a company is published, so every field a later stage writes is optional (lists default to `[]`, objects to `None`), and every model keeps unknown fields. Value sets the API may extend (email types, check results, stage states) are typed as `str`, with enums only for the values callers pass or branch on.

`wait_for_company_task()` and `iter_company_results()` work like their People Search counterparts and raise `CompanyTaskTimeoutError`; a 409 from pause, resume, or cancel raises `CompanyTaskConflictError` with the task as a `CompanyTask`. Both errors are separate classes from the People Search ones, so catching `PeopleTaskConflictError` does not catch a company conflict.

## Public API boundary

`desearch_py/__init__.py` is the package boundary for consumers. It re-exports:

- `Desearch`
- `DesearchAPIError`, plus the People Search errors `PeopleTaskConflictError` and `PeopleTaskTimeoutError` and the Company Search errors `CompanyTaskConflictError` and `CompanyTaskTimeoutError`
- enums such as `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`
- response models
- response metadata wrapper models
- error models
- X/Twitter entity models

Practical effect:

- consumers can import from `desearch_py` directly
- internal file layout can change later without forcing deep import paths, as long as package-root exports stay stable

## Packaging design

The repo keeps both Poetry and setuptools metadata:

- `desearch_py.__version__` is `1.10.0` and is the single source of truth for the version
- `setup.py` packages the import module `desearch_py` and reads its version from `desearch_py/__init__.py` with a regex (it does not import the package)
- `pyproject.toml` names the package `desearch-py` and repeats version `1.10.0`, because `poetry-core` cannot read a dynamic version; `tests/test_version_consistency.py` fails if it drifts

This dual-metadata setup supports multiple install flows, but it creates a maintenance obligation: version and dependency drift between the two files would be a release bug.

## Documentation design

The repository currently has two documentation layers:

1. source-of-truth Markdown files such as this document
2. older Sphinx scaffold files and generated HTML under `docs/_build/`

Important current-state detail:

- `docs/conf.py` still names the project `datura-py` and author `Leva`
- generated HTML in `docs/_build/` repeats the same legacy branding

That means contributors should treat the checked source code and Markdown docs as authoritative, not the generated Sphinx output.

## Non-goals in the current architecture

The current implementation does **not** include:

- built-in retries or backoff
- automatic pagination helpers outside People Search and Company Search results (`iter_people_results`, `iter_company_results`)
- streaming response handling
- sync client support
- lint infrastructure inside this repo

## Key design decisions

- Keep the SDK async-only, centered on `aiohttp`.
- Prefer a tiny public client over a large layered abstraction tree.
- Use tolerant `pydantic` parsing to avoid breaking on additive API changes.
- Return raw dictionaries in a few unstable paths instead of throwing parsing errors.
- Keep docs honest about current behavior, even when that behavior is incomplete.
