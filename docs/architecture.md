# Architecture — desearch-py SDK

This document explains how the SDK is structured today, based on the checked-in source rather than intended future behavior.

## Overview

`desearch-py` is a thin async wrapper over the Desearch HTTP API. The codebase is intentionally small and split across three public-facing package files:

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

`_handle_request()` is the common path for most endpoints. It centralizes:

- session acquisition
- a hardcoded `aiohttp.ClientTimeout(total=120)`
- `response.raise_for_status()`
- JSON decoding
- error logging before re-raise

This keeps the repo small, but it also means the same timeout and JSON expectations are applied broadly.

### 4. Two methods intentionally bypass the shared helper

`x_posts_by_urls()` and `web_crawl()` build direct `client.request(...)` calls instead of delegating to `_handle_request()`.

Why that appears to exist in the current code:

- `x_posts_by_urls()` needs repeated `urls` query params expressed as a tuple list
- `web_crawl()` returns `response.text()` instead of JSON

Tradeoff:

- these methods can support their special request shapes cleanly
- request/error logic is duplicated, so future transport changes must be updated in more than one place

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

## Public API boundary

`desearch_py/__init__.py` is the package boundary for consumers. It re-exports:

- `Desearch`
- enums such as `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`
- response models
- error models
- X/Twitter entity models

Practical effect:

- consumers can import from `desearch_py` directly
- internal file layout can change later without forcing deep import paths, as long as package-root exports stay stable

## Packaging design

The repo keeps both Poetry and setuptools metadata:

- `pyproject.toml` names the package `desearch-py` and declares version `1.2.0`
- `setup.py` packages the import module `desearch_py` and also declares version `1.2.0`

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
- SDK-specific exception classes
- automatic pagination helpers
- streaming response handling
- sync client support
- test or lint infrastructure inside this repo

## Key design decisions

- Keep the SDK async-only, centered on `aiohttp`.
- Prefer a tiny public client over a large layered abstraction tree.
- Use tolerant `pydantic` parsing to avoid breaking on additive API changes.
- Return raw dictionaries in a few unstable paths instead of throwing parsing errors.
- Keep docs honest about current behavior, even when that behavior is incomplete.
