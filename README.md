# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` wraps Desearch search and crawling endpoints behind an `aiohttp` client and returns structured `pydantic` models for most responses. The current package version is **1.2.0** and it supports **Python 3.9+**.

## Installation

```bash
pip install desearch-py
```

## Requirements

- Python 3.9+
- `aiohttp>=3.8`
- `pydantic>=2.0`

These dependencies are declared in `pyproject.toml` and installed automatically with the package.

## Quick start

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

## Client overview

The SDK exposes a single async client, `Desearch`, with methods grouped into four areas:

### AI search

- `ai_search` for multi-source AI search
- `ai_web_links_search` for web-source link retrieval
- `ai_x_links_search` for X post link retrieval

### X / Twitter data

- `x_search`
- `x_posts_by_urls`
- `x_post_by_id`
- `x_posts_by_user`
- `x_post_retweeters`
- `x_user_posts`
- `x_user_replies`
- `x_post_replies`
- `x_trends`

### Web search and crawl

- `web_search`
- `web_crawl`

### Typed exports

The package also exports enums and models from `desearch_py.models`, including:

- `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`
- `ResponseData`
- `TwitterScraperTweet`, `TwitterScraperUser`
- `WebSearchResponse`, `WebSearchResultsResponse`
- `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, `XTrendsResponse`

## Usage patterns

### Reuse the client with `async with`

The client manages an internal `aiohttp.ClientSession` and closes it automatically when used as an async context manager.

```python
async with Desearch(api_key="your_api_key") as client:
    tweets = await client.x_search(query="bittensor", count=5)
```

### Close manually when needed

```python
client = Desearch(api_key="your_api_key")
try:
    results = await client.web_search(query="Desearch API")
finally:
    await client.close()
```

## Method examples

### AI search

```python
result = await client.ai_search(
    prompt="Recent open-source AI search releases",
    tools=["web", "hackernews", "reddit", "twitter"],
    date_filter="PAST_WEEK",
    result_type="LINKS_WITH_FINAL_SUMMARY",
    count=20,
)
```

### X search

```python
tweets = await client.x_search(
    query="bittensor",
    sort="Latest",
    lang="en",
    min_likes=50,
    count=20,
)
```

### Fetch posts by URL

```python
posts = await client.x_posts_by_urls(
    urls=["https://x.com/RacingTriple/status/1892527552029499853"],
)
```

### Web crawl

```python
content = await client.web_crawl(
    url="https://desearch.ai",
    format="text",
)
```

## Response behavior

Most methods return `pydantic` models, but some endpoints can also fall back to raw dictionaries when the response shape does not match the local model exactly:

- `ai_search`
- `x_search`
- `x_posts_by_user`
- `x_user_replies`
- `x_post_replies`

This makes the client more tolerant of API changes, but it also means consumers should check return types in code paths that depend on strict typing.

## API base URL

By default the client targets:

```text
https://api.desearch.ai
```

You can override it for testing or internal environments:

```python
client = Desearch(api_key="your_api_key", base_url="https://staging-api.desearch.ai")
```

## Docs

- [Feature inventory](docs/features.md)
- [Architecture notes](docs/architecture.md)
- [Known issues and limitations](docs/known-issues.md)

## Links

- Desearch: <https://desearch.ai>
- Console: <https://console.desearch.ai>
- API docs: <https://desearch.ai/docs/api-reference/>
