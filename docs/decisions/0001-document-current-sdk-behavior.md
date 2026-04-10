# ADR 0001: Document current SDK behavior as the source of truth

- Status: Accepted
- Date: 2026-04-10

## Context

This repository has a small Python SDK implementation, Markdown docs, and an older Sphinx scaffold with legacy `datura-py` branding. That combination makes it easy for contributors to accidentally document intended behavior, stale generated output, or cross-repo assumptions instead of what this SDK actually does today.

## Decision

When refreshing docs for `desearch-py`, contributors must treat the checked Python source and packaging files as the source of truth:

- `desearch_py/api.py`
- `desearch_py/models.py`
- `desearch_py/__init__.py`
- `pyproject.toml`
- `setup.py`

Documentation should describe current behavior, even when that behavior reveals gaps such as disabled streaming, raw-dict fallbacks, fixed timeouts, or stale Sphinx metadata.

Generated Sphinx output under `docs/_build/` is not authoritative.

## Alternatives considered

### Use generated docs as the source of truth

Rejected because the checked-in Sphinx output still contains legacy branding and does not fully describe the SDK surface.

### Document the intended future SDK shape

Rejected because it creates false expectations for consumers and leads to QA failures when claims cannot be verified in code.

## Consequences

- Docs remain auditable against source.
- Known limitations stay visible instead of being papered over.
- Contributors must verify claims before editing docs.
- The repo still carries legacy Sphinx artifacts until someone explicitly refreshes or removes them.
