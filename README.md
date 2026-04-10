# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` is a thin `aiohttp` client for the Desearch public API. It wraps search, X, and crawl endpoints behind a single async client class and returns `pydantic` models for most successful responses. The package metadata currently reports **version 1.2.0** and requires **Python 3.9+**.

## Package purpose

Use this SDK when you want to call Desearch from Python without hand-rolling HTTP requests, auth headers, or response parsing. The repository ships:

- an async client in `desearch_py/api.py`
- typed models and enums in `desearch_py/models.py`
- lightweight Sphinx scaffolding in `docs/`
- packaging metadata in both `pyproject.toml` and `setup.py`

Two names matter:

- package on PyPI and in Poetry metadata: `desearch-py`
- import path in Python code: `desearch_py`

## Quick Start

### Install

```bash
pip install desearch-py
```

### Run a basic AI search

```python
import asyncio
from desearch_py import Desearch


async def main() -> None:
    async with Desearch(api_key="your_api_key") as client:
        result = await client.ai_search(
            prompt="What happened in Bittensor this week?",
            tools=["web", "twitter", "reddit"],
            count=10,
        )
        print(result)


asyncio.run(main())
```

### Reuse the client manually

```python
import asyncio
from desearch_py import Desearch


async def main() -> None:
    client = Desearch(api_key="your_api_key")
    try:
        tweets = await client.x_search(query="desearch", sort="Latest", count=5)
        print(tweets)
    finally:
        await client.close()


asyncio.run(main())
```

## Requirements

Dependencies declared in source:

- Python `>=3.9` (`pyproject.toml`, `setup.py`)
- `aiohttp >=3.8`
- `pydantic >=2.0`

`setup.py` also lists `typing-extensions` as an install dependency.

## Commands

| Task | Command | Notes |
|---|---|---|
| Install published package | `pip install desearch-py` | For consumers |
| Install local repo editable | `pip install -e .` | Uses `setup.py` |
| Install local repo with Poetry | `poetry install` | Uses `pyproject.toml` |
| Build distributables | `poetry build` | Produces package artifacts |
| Publish package | `./publish.sh` | Repository script |
| Build Sphinx docs | `make -C docs html` | Requires Sphinx dev deps |

There are currently **no dedicated test, lint, or format commands configured in the repo**. This is an accurate reflection of the current source tree, not an omission in this README.

## Tech stack

- Python 3.9+
- `aiohttp` for async HTTP
- `pydantic` v2 models for typed responses
- Poetry + setuptools metadata side by side
- Sphinx scaffolding for docs

## Supported SDK surface

### AI search

- `ai_search`
- `ai_web_links_search`
- `ai_x_links_search`

### X / Twitter endpoints

- `x_search`
- `x_posts_by_urls`
- `x_post_by_id`
- `x_posts_by_user`
- `x_post_retweeters`
- `x_user_posts`
- `x_user_replies`
- `x_post_replies`
- `x_trends`

### Web endpoints

- `web_search`
- `web_crawl`

### Typed exports

The package re-exports the async client plus enums and models from `desearch_py.models`, including `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `ResponseData`, `TwitterScraperTweet`, `WebSearchResponse`, `WebSearchResultsResponse`, `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, and `XTrendsResponse`.

## Architecture overview

The SDK is intentionally small.

- `desearch_py/api.py` contains the `Desearch` client and every HTTP method.
- `desearch_py/models.py` contains enums and permissive `pydantic` schemas.
- `desearch_py/__init__.py` re-exports the public API.

Key design decisions visible in code:

- the HTTP session is created lazily on first use
- auth is sent as `Authorization: <api_key>` with no `Bearer` prefix
- most requests share a single helper with a fixed 120 second timeout
- `x_posts_by_urls` and `web_crawl` bypass that shared helper and make direct requests
- some endpoints fall back to raw `dict` values instead of failing model parsing
- `ai_search` always sends `"streaming": False`

## Usage notes

### Use `async with` when possible

```python
async with Desearch(api_key="your_api_key") as client:
    results = await client.web_search(query="Desearch API")
```

This is the safest pattern because it guarantees the underlying `aiohttp.ClientSession` gets closed.

### Expect mixed return types on some methods

The following methods may return a typed object on success or a raw `dict` when the API shape does not match the local parser exactly:

- `ai_search`
- `x_search`
- `x_posts_by_user`
- `x_user_replies`
- `x_post_replies`

If your app depends on strict typing, add runtime checks before dereferencing attributes.

### Override the base URL for non-production environments

```python
client = Desearch(
    api_key="your_api_key",
    base_url="https://staging-api.desearch.ai",
)
```

## Repo boundaries

Always:

- treat this repo as the Python SDK only
- verify docs against `desearch_py/api.py`, `desearch_py/models.py`, `pyproject.toml`, and `setup.py`
- document current behavior, even when it exposes limitations

Never:

- describe unsupported streaming or retry behavior as implemented
- assume generated files in `docs/_build/` are the source of truth
- confuse this repo with `desearch.js`, `desearch-public-api`, or `desearch-console`

## Additional docs

- [Feature inventory](docs/features.md)
- [Architecture notes](docs/architecture.md)
- [Known issues](docs/known-issues.md)
- [ADR: current behavior is the documentation source of truth](docs/decisions/0001-document-current-sdk-behavior.md)

## Links

- Desearch: <https://desearch.ai>
- Console: <https://console.desearch.ai>
- API docs: <https://desearch.ai/docs/api-reference/>
