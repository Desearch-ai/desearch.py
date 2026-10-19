# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` is a thin `aiohttp` client for the Desearch public API. It wraps search, X, extraction, and People Search endpoints behind a single async client class and returns `pydantic` models for most successful responses. The package metadata currently reports **version 1.5.0** and requires **Python 3.9+**.

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


### Read optional response cost metadata

Default calls continue to return the original typed payload only:

```python
result = await client.ai_search(
    prompt="What happened in Bittensor this week?",
    tools=["web", "twitter"],
)
print(result.text)
```

When you want per-request cost visibility, opt in with `include_metadata=True`:

```python
response = await client.ai_search(
    prompt="What happened in Bittensor this week?",
    tools=["web", "twitter"],
    include_metadata=True,
)

print(response.data.text)
print(response.metadata.cost_usd)
print(response.metadata.usage_count)
print(response.metadata.service)
print(response.metadata.currency)
```

The SDK reads metadata from the same API response headers (`X-Desearch-Cost-Usd`, for example `0.00015`, plus `X-Desearch-Usage-Count`, `X-Desearch-Service`, and `X-Desearch-Currency`). Missing or malformed numeric headers are exposed as `None` instead of breaking a successful API call.

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

## People Search

People Search finds people, not posts: X profiles, YouTube creators, LinkedIn members, and TikTok creators that match a plain-language description. Each search runs in the background as a task. You start it, wait for it, then read or export the people it found.

```python
import asyncio

from desearch_py import Desearch, TikTokCreatorSearchFilters


async def main() -> None:
    async with Desearch(api_key="your_api_key") as client:
        # 1. Start the search. This is the only billed call.
        task = await client.tiktok_creator_search(
            query="Skincare creators who review sunscreen",
            count=25,
            filters=TikTokCreatorSearchFilters(min_followers=10000),
            idempotency_key="sunscreen-creators-2026-10",
        )
        print(task.task_id, task.status, task.reserved_cost_usd)

        # 2. Wait until it ends (polls every 5 seconds, up to 10 minutes).
        task = await client.wait_for_people_task(task.task_id)
        print(task.status, task.result_count, task.final_cost_usd)

        # 3. Read every result, page by page.
        async for person in client.iter_people_results(task.task_id):
            score = person.score.value if person.score else None
            print(person.handle, score, person.metrics.get("followers"))

        # 4. Export only the creators with a public email, as CSV.
        csv_text = await client.export_people_results(
            task.task_id, format="csv", has="email"
        )
        with open("creators-with-email.csv", "w", encoding="utf-8", newline="") as handle:
            handle.write(csv_text)


asyncio.run(main())
```

### Pricing

You are billed per profile delivered. Starting a search reserves `count` people at the route price. When the search ends you pay only for the people it delivered, and the rest of the reservation is returned. A minimum applies to each search that finds anyone, and a search that finds nobody is free. Waiting, reading results, pausing, resuming, cancelling, exports, and the profiles library are all free. See <https://console.desearch.ai/pricing> for current prices.

Pass `idempotency_key` when you might retry a search call. A repeated key returns the earlier task and does not charge again.

### Methods

| Method | Route | Returns |
|---|---|---|
| `x_profile_search` | `POST /desearch/people/search/x` | `PeopleTask` |
| `youtube_creator_search` | `POST /desearch/people/search/youtube` | `PeopleTask` |
| `linkedin_profile_search` | `POST /desearch/people/search/linkedin` | `PeopleTask` |
| `tiktok_creator_search` | `POST /desearch/people/search/tiktok` | `PeopleTask` |
| `list_people_tasks` | `GET /desearch/people/tasks` | `PeopleTaskList` |
| `get_people_task` | `GET /desearch/people/tasks/{task_id}` | `PeopleTask` |
| `get_people_results` | `GET /desearch/people/tasks/{task_id}/results` | `PeopleResultsPage` |
| `pause_people_task` / `resume_people_task` / `cancel_people_task` | `POST /desearch/people/tasks/{task_id}/pause` (`/resume`, `/cancel`) | `PeopleTask` |
| `export_people_results` | `GET /desearch/people/tasks/{task_id}/export` | CSV or JSON Lines text |
| `list_people_profiles` | `GET /desearch/people/profiles` | `PeopleProfilesPage` |
| `export_people_profiles` | `GET /desearch/people/profiles/export` | CSV or JSON Lines text |
| `wait_for_people_task` | polls `get_people_task` | the ended `PeopleTask` |
| `iter_people_results` | follows `next_cursor` on `get_people_results` | async iterator of `Person` |

Every search method takes `query`, `count` (5-200), `min_score` (0-100), `exclude` (handles to skip), `filters`, and `metadata` (your own labels, see below). Each platform has its own filters model: `XProfileSearchFilters`, `YouTubeCreatorSearchFilters`, `LinkedInProfileSearchFilters`, and `TikTokCreatorSearchFilters`. A plain `dict` also works.

`wait_for_people_task` returns once the status is `completed`, `partial`, `failed`, `cancelled`, or `expired`. Tune it with `poll_interval` and `timeout` (seconds; `timeout=None` waits without a limit). On timeout it raises `PeopleTaskTimeoutError` with the last task state on `.task`. The search keeps running. A paused task stays paused until you resume it (the API cancels it after 7 days), so waiting on one runs until the timeout.

### Tagging searches with metadata

Pass `metadata` to label a search with your own keys, for example the campaign or workspace it belongs to. The task returns it as `task.metadata` (`{}` when none was sent), and `list_people_tasks` can filter by it. The search itself never uses it.

```python
await client.linkedin_profile_search(
    query="Heads of sales at fintech startups who post about outbound",
    count=25,
    metadata={"campaign": "q4-outbound", "workspace_id": "ws_42"},
)

# Later: every search of that campaign, newest first.
page = await client.list_people_tasks(metadata={"campaign": "q4-outbound"})
for task in page.tasks:
    print(task.task_id, task.status, task.metadata.get("workspace_id"))
```

- A search takes at most 10 keys. Keys are 1-40 characters of `a-z`, `0-9`, `_`, `.` or `-`; values are strings of at most 200 characters. The API answers 422 otherwise (raised as `DesearchAPIError`).
- `list_people_tasks` takes up to 3 pairs. The SDK sends each as a `metadata.<key>=<value>` query parameter, and a task must match all of them exactly. Keep the same filter when you page with `cursor`.
- `metadata` here is the task's labels. It is not the `include_metadata=True` response cost wrapper.

### Result filters

`export_people_results`, `list_people_profiles`, and `export_people_profiles` take the same result filters, as keyword arguments or as a `PeopleResultFilters` object (keyword arguments win):

| Filter | Meaning |
|---|---|
| `has` | Channels every person must have: `email`, `website`, `x`, `linkedin`, `instagram`, `youtube`, `tiktok`. A list or a comma-separated string. |
| `min_audience` / `max_audience` | Followers (subscribers on YouTube). |
| `min_score` | Minimum fit score, 0-100. |
| `location` | Text in the location, for example `"united states"`. |
| `verified` | `True` keeps only verified accounts (X, TikTok). |

```python
from desearch_py import PeopleResultFilters

page = await client.list_people_profiles(
    "tiktok",
    sort="audience",
    filters=PeopleResultFilters(has=["email", "instagram"], min_audience=50000),
)
for profile in page.profiles:
    print(profile.handle, profile.found_by.query, profile.found_by.times_found)
```

### People Search errors

HTTP errors raise `DesearchAPIError`, as elsewhere in the SDK. Statuses specific to People Search:

- `402`: the account has no credits for the reservation.
- `429`: too many searches are already queued, running, or paused.
- `404`: the task does not exist or belongs to another account.
- `410`: the results expired (they are kept 30 days after the search ends).
- `409` from pause, resume, or cancel raises `PeopleTaskConflictError`, a `DesearchAPIError` subclass. `.detail` explains why, and `.task` holds the task's current state.

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
| Run tests | `poetry run python -m unittest discover -s tests -v` | Uses the stdlib unittest runner |
| Build Sphinx docs | `make -C docs html` | Requires Sphinx dev deps |

A unittest suite covers response metadata, API key redaction, and People Search, with HTTP mocked or served from a local test server. There is still no dedicated lint or format command configured in the repo.

## Tech stack

- Python 3.9+
- `aiohttp` for async HTTP
- `pydantic` v2 models for typed responses
- Poetry + setuptools metadata side by side
- Sphinx scaffolding for docs

## Supported SDK surface

### AI search

- `ai_search` — also accepts `start_date`/`end_date` (UTC `YYYY-MM-DDTHH:MM:SSZ`), `include_domains`/`exclude_domains`, and `result_type` (`ONLY_LINKS` / `LINKS_WITH_FINAL_SUMMARY`). `date_filter` is a deprecated relative window the API translates into a date range.
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
- `extract` — canonical `GET /web/extract` method
- `web_crawl` — deprecated compatibility method for `GET /web/crawl`

```python
content = await client.extract(
    url="https://desearch.ai",
    format="text",
    js=True,
    wait=250,
)
```

Existing `web_crawl()` integrations continue to work through the legacy route. Use `extract()` for new integrations.

### People Search endpoints

- `x_profile_search`, `youtube_creator_search`, `linkedin_profile_search`, `tiktok_creator_search`
- `list_people_tasks`, `get_people_task`, `get_people_results`
- `pause_people_task`, `resume_people_task`, `cancel_people_task`
- `export_people_results`, `list_people_profiles`, `export_people_profiles`
- helpers: `wait_for_people_task`, `iter_people_results`

See [People Search](#people-search) for an example, pricing, and filters.

### Typed exports

The package re-exports the async client plus enums and models from `desearch_py.models`, including `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `ResponseData`, `DesearchCostMetadata`, `DesearchResponse`, `TwitterScraperTweet`, `WebSearchResponse`, `WebSearchResultsResponse`, `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, and `XTrendsResponse`. People Search adds `PeopleTask`, `PeopleTaskList`, `PeopleResultsPage`, `Person`, `PeopleProfile`, `PeopleProfilesPage`, `PeopleResultFilters`, the four request and filters models, the enums `PeoplePlatform`, `PeopleTaskStatus`, `PeopleProfileSort`, `PeopleExportFormat`, and `PeopleChannel`, and the errors `PeopleTaskConflictError` and `PeopleTaskTimeoutError`.

## Architecture overview

The SDK is intentionally small.

- `desearch_py/api.py` contains the `Desearch` client and every HTTP method.
- `desearch_py/models.py` contains enums and permissive `pydantic` schemas.
- `desearch_py/__init__.py` re-exports the public API.

Key design decisions visible in code:

- the HTTP session is created lazily on first use
- auth is sent as `Authorization: <api_key>` with no `Bearer` prefix
- most requests share a single helper with a fixed 120 second timeout
- successful responses can opt in to a `DesearchResponse` wrapper with parsed cost metadata from response headers
- `x_posts_by_urls` and the extraction methods use specialized request paths for repeated query parameters and text responses, while still supporting the metadata wrapper
- some endpoints fall back to raw `dict` values instead of failing model parsing
- `ai_search` always sends `"streaming": False`
- People Search searches are background tasks; `wait_for_people_task` and `iter_people_results` are the SDK's only polling and pagination helpers

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
