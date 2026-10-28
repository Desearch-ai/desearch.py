# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` is a thin `aiohttp` client for the Desearch public API. It wraps AI search, the Search API, X, TikTok, Instagram, Facebook, extraction, People Search, and the public network stats behind a single async client class and returns `pydantic` models for most successful responses. The package metadata currently reports **version 1.8.0** and requires **Python 3.10+**. See [CHANGELOG.md](CHANGELOG.md) for unreleased and breaking changes.

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

`response.metadata.next_cursor` holds the `x-desearch-next-cursor` header, which the TikTok, Instagram, and Facebook list methods send when another page exists. See [Pagination](#pagination).

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

## Search API

`search_api` calls `POST /search`: it searches the web and returns ranked pages, each with the passage that best matches the query.

```python
from desearch_py import SearchApiMode

response = await client.search_api(
    "Who won the 2024 Nobel Prize in Physics?",
    mode=SearchApiMode.FAST,  # or "balanced" (the API default)
    count=10,                 # 10, 15 or 20
    start_date="2024-01-01",  # optional, YYYY-MM-DD
    page_text=False,          # True adds the full page text
)
for result in response.results:
    print(result.title, result.url, result.published_date)
    print(result.highlights)
print(response.cost_usd, response.currency)
```

Unset arguments are not sent, so the API defaults apply (`mode="balanced"`, `count=10`, `highlights=True`, `page_text=False`). The SDK has no method named plain `search`.

## TikTok, Instagram, and Facebook

Public posts, profiles, comments, and hashtags. Path parameters (IDs, usernames, tags) are percent-encoded, so an Instagram post URL or an ID that contains `/` works as is.

| Method | Route | Returns | Pages with `cursor` |
|---|---|---|---|
| `tiktok_search(query, count=None, cursor=None, sort=None)` | `POST /desearch/tiktok/search` | `List[TikTokPost]` | yes |
| `tiktok_post_by_id(id)` | `GET /desearch/tiktok/post/{id}` | `TikTokPost` | no |
| `tiktok_profile(username)` | `GET /desearch/tiktok/profile/{username}` | `TikTokProfile` | no |
| `tiktok_profile_posts(username, count=None, cursor=None)` | `GET /desearch/tiktok/profile/{username}/posts` | `List[TikTokPost]` | yes |
| `tiktok_comments(video_id, count=None, cursor=None)` | `GET /desearch/tiktok/comments/{video_id}` | `List[TikTokComment]` | yes |
| `tiktok_hashtag(tag, count=None, cursor=None)` | `GET /desearch/tiktok/hashtag/{tag}` | `List[TikTokPost]` | yes |
| `tiktok_trending(region=None, count=None)` | `GET /desearch/tiktok/trending` | `List[TikTokPost]` | no |
| `instagram_search(query, count=None)` | `POST /desearch/instagram/search` | `List[InstagramSearchResult]` | no |
| `instagram_media(id)` | `GET /desearch/instagram/media/{id}` | `InstagramMedia` | no |
| `instagram_profile(username)` | `GET /desearch/instagram/profile/{username}` | `InstagramProfile` | no |
| `instagram_profile_posts(username, count=None, cursor=None)` | `GET /desearch/instagram/profile/{username}/posts` | `List[InstagramMedia]` | yes |
| `instagram_comments(shortcode, count=None, cursor=None)` | `GET /desearch/instagram/comments/{shortcode}` | `List[InstagramComment]` | yes |
| `instagram_hashtag(tag, count=None, cursor=None)` | `GET /desearch/instagram/hashtag/{tag}` | `List[InstagramMedia]` | yes |
| `facebook_search(query, count=None, cursor=None)` | `POST /desearch/facebook/search` | `List[FacebookPost]` (Ad Library records) | yes |
| `facebook_post_by_id(id)` | `GET /desearch/facebook/post/{id}` | `FacebookPost` | no |
| `facebook_profile(profile_id)` | `GET /desearch/facebook/profile/{profile_id}` | `FacebookProfile` | no |
| `facebook_profile_posts(profile_id, count=None, cursor=None)` | `GET /desearch/facebook/profile/{profile_id}/posts` | `List[FacebookPost]` | yes |
| `facebook_comments(post_id, count=None, cursor=None)` | `GET /desearch/facebook/comments/{post_id}` | `List[FacebookComment]` | yes |
| `facebook_hashtag(tag, count=None, cursor=None)` | `GET /desearch/facebook/hashtag/{tag}` | `List[FacebookPost]` (Ad Library records) | yes |

Every method also takes the keyword-only `include_metadata`. `count` is a maximum (1-100); the API default is 10 for the three search methods and 20 elsewhere. Model fields keep the API's camelCase names (`createTime`, `playCount`, `fullName`), and every field is optional because the public sources do not always send it.

- Pass usernames without `@` and hashtags without `#`.
- `TikTokPost.id` is the video ID that `tiktok_comments` takes. `instagram_comments` takes the post shortcode (`InstagramMedia.shortcode`, the code in `instagram.com/p/<shortcode>/`); a numeric media ID returns 404.
- `facebook_search` and `facebook_hashtag` search the public Meta Ad Library, not organic posts. Their results set the ad fields of `FacebookPost`: `linkUrl`, `cta`, `headline`, `linkDescription`, `endDate`, `active`, and `platforms`.
- `instagram_search` finds profiles and returns one page; the API rejects a cursor there, so the method takes none.
- Like `x_search`, a list method returns the raw body (a `dict`) when the API does not answer with a list.

### Pagination

List methods return one page. The next-page cursor comes back in the `x-desearch-next-cursor` response header, which the SDK exposes as `metadata.next_cursor` when you pass `include_metadata=True`:

```python
import asyncio

from desearch_py import Desearch


async def main() -> None:
    async with Desearch(api_key="your_api_key") as client:
        cursor = None
        for _ in range(3):  # read up to three pages
            page = await client.tiktok_hashtag(
                "ai", count=20, cursor=cursor, include_metadata=True
            )
            for post in page.data:
                print(post.id, post.text)
            cursor = page.metadata.next_cursor
            if cursor is None:  # no header: this was the last page
                break


asyncio.run(main())
```

- Send the cursor back unchanged, to the same method with the same target (username, tag, post ID, or query; for `tiktok_search`, also the same `sort`). It is opaque: never build, edit, or reuse one elsewhere.
- A cursor is valid for 24 hours. An expired cursor, one from another route or target, or any value the API did not issue gets HTTP 422 (raised as `DesearchAPIError`) and is not charged.
- `next_cursor` is `None` on the last page. A page shorter than `count` is not the end: one request reads one provider page, which can be smaller (about 3 for Facebook profile posts, 10 for Facebook comments, 12 for Instagram profile posts).
- Items the previous page already returned are dropped from the next one, so a page can hold fewer items than the provider sent.
- `tiktok_trending` and `instagram_search` do not paginate.

## Network stats

Public counters for the Desearch network. These routes need no API key (the API does not check it) and are free.

```python
from contextlib import aclosing

stats = await client.network_stats()
print(stats.total_searchable_pages, stats.rates_per_second.total_searchable_pages)

history = await client.network_stats_history()  # one point per second, last 20 minutes
print(history.window_started_at, len(history.points))

# One `stats` Server-Sent Event per second. aclosing() closes the connection
# as soon as you leave the loop.
last_event_id = None
async with aclosing(client.stream_network_stats()) as events:
    async for event in events:
        last_event_id = event.id
        print(event.data.updated_at, event.data.searches_completed_today)
        if event.data.searches_completed_today > 1_000_000:
            break

# Resume later: the API replays the events you missed (up to 20 minutes).
async with aclosing(client.stream_network_stats(last_event_id=last_event_id)) as events:
    async for event in events:
        ...
```

- `stream_network_stats` is an async iterator of `NetworkStatsEvent` (`id`, `event`, and `data`, a `NetworkStatsResponse`). It does not reconnect on its own; call it again with `last_event_id` to resume.
- The 120 second timeout of other methods does not apply to the stream. It fails with a timeout error if no data arrives for 60 seconds.
- The counters are an estimate: `telemetry_kind` is `estimated` and `methodology` is `fixed_rate_projection`.

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

### Reading a finished search

A finished task says why it ended and how complete it is, and each result says which criteria its profile confirms (1.6.0 and later):

```python
task = await client.wait_for_people_task(task.task_id)

# count_reached, rounds_exhausted, no_candidates, zero_qualified,
# candidate_budget, cost_limit, time_limit, cancelled or failed.
print(task.completion_reason)
if task.coverage_limited:
    print("A budget stopped the search before `count`: there may be more people.")
for warning in task.warnings:
    # partial_enrichment: some profiles could not be read after search.
    print(warning.code, warning.platform, warning.failed, warning.attempted, warning.by_reason)

async for person in client.iter_people_results(task.task_id):
    score = person.score
    # Criteria not confirmed, and disqualifiers that apply (verdict "met").
    unverified = [
        f"{check.criterion} ({check.verdict})"
        for check in (score.unverified_criteria if score else [])
    ]
    print(person.handle, score.fully_verified if score else None, unverified)
    if person.enrichment == "failed":
        # Scored on the search hit only; enrichment_error says why.
        print("profile not read:", person.enrichment_error)
```

- `completion_reason` is `None` while the task is queued, running, or paused (`PeopleCompletionReason` lists the values). A search that a budget stopped is still `completed`, so check `coverage_limited`.
- `score.criteria_checks` holds one `PeopleCriterionCheck` per criterion: `verdict` is `met`, `not_met`, or `unknown`, with the `quote` and `source_url` behind a `met`. It is information only: a qualified person can still have `unknown` criteria. For a disqualifier (`is_disqualifier`, 1.6.1 and later), `met` means it applies.
- `score.fully_verified` is true when every criterion is `met` and no disqualifier is. Results scored before 2026-10-20 have no checks and `fully_verified` is `None`.
- `person.enrichment` and `person.enrichment_error` read `attributes["enrichment"]` and `attributes["enrichment_error"]` (LinkedIn, TikTok, YouTube).
- `score.unverified_criteria` returns the checks that are not confirmed: every criterion that is not `met`, and every disqualifier that is `met`. It reads each check's `is_disqualifier`, and the API's keyword rule for older checks without it (`check.disqualifier` gives the answer for one check). Their `criterion` texts are what the CSV export lists in its new `unverified_criteria` column, next to `fully_verified`.

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

- Python `>=3.10` (`pyproject.toml`, `setup.py`)
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

A unittest suite covers response metadata and pagination cursors, API key redaction, People Search, the social, Search API, and network stats methods, and the Server-Sent Events decoder, with HTTP mocked or served from a local test server. There is still no dedicated lint or format command configured in the repo.

`scripts/e2e_full_coverage.py` is a live smoke test of the 1.8.0 methods. It calls the real API, so it is not part of the unit suite:

```bash
DESEARCH_API_KEY=your_api_key python scripts/e2e_full_coverage.py
```

It calls each new method once with the smallest counts, reads one more page wherever a list method returns a cursor, prints `PASS name` or `FAIL name: error` per call, and exits non-zero on any failure. `--base-url` points it at another environment. It never starts a People Search (a paid job) unless you pass `--with-people`.

## Tech stack

- Python 3.10+
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

### Search API

- `search_api` — `POST /search`, ranked pages with the best matching passage. See [Search API](#search-api).

### TikTok, Instagram, and Facebook endpoints

- TikTok: `tiktok_search`, `tiktok_post_by_id`, `tiktok_profile`, `tiktok_profile_posts`, `tiktok_comments`, `tiktok_hashtag`, `tiktok_trending`
- Instagram: `instagram_search`, `instagram_media`, `instagram_profile`, `instagram_profile_posts`, `instagram_comments`, `instagram_hashtag`
- Facebook: `facebook_search`, `facebook_post_by_id`, `facebook_profile`, `facebook_profile_posts`, `facebook_comments`, `facebook_hashtag`

See [TikTok, Instagram, and Facebook](#tiktok-instagram-and-facebook) for the routes and [Pagination](#pagination) for cursors.

### Network stats endpoints

- `network_stats`, `network_stats_history`
- `stream_network_stats` — async iterator over the `GET /network/stats/stream` Server-Sent Events

See [Network stats](#network-stats).

### People Search endpoints

- `x_profile_search`, `youtube_creator_search`, `linkedin_profile_search`, `tiktok_creator_search`
- `list_people_tasks`, `get_people_task`, `get_people_results`
- `pause_people_task`, `resume_people_task`, `cancel_people_task`
- `export_people_results`, `list_people_profiles`, `export_people_profiles`
- helpers: `wait_for_people_task`, `iter_people_results`

See [People Search](#people-search) for an example, pricing, and filters.

### Typed exports

The package re-exports the async client plus enums and models from `desearch_py.models`, including `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `ResponseData`, `DesearchCostMetadata`, `DesearchResponse`, `TwitterScraperTweet`, `WebSearchResponse`, `WebSearchResultsResponse`, `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, and `XTrendsResponse`. 1.8.0 adds the Search API models `SearchApiResponse`, `SearchApiResult`, and the enum `SearchApiMode`; the TikTok models `TikTokPost`, `TikTokProfile`, `TikTokComment`, `TikTokAuthor`, `TikTokStats`, and `TikTokMusic`; the Instagram models `InstagramMedia`, `InstagramProfile`, `InstagramComment`, `InstagramSearchResult`, and `InstagramStats`; the Facebook models `FacebookPost`, `FacebookProfile`, `FacebookComment`, `FacebookMedia`, and `FacebookPostStats`; and the network stats models `NetworkStatsResponse`, `NetworkStatsRates`, `NetworkStatsHistoryResponse`, `NetworkStatsHistoryPoint`, and `NetworkStatsEvent`. People Search adds `PeopleTask`, `PeopleTaskList`, `PeopleResultsPage`, `Person`, `PeopleProfile`, `PeopleProfilesPage`, `PeopleResultFilters`, the four request and filters models, the result models `PeopleTaskWarning` and `PeopleCriterionCheck`, the enums `PeoplePlatform`, `PeopleTaskStatus`, `PeopleProfileSort`, `PeopleExportFormat`, `PeopleChannel`, `PeopleCompletionReason`, `PeopleCriterionVerdict`, `PeopleEnrichment`, and `PeopleEnrichmentError`, and the errors `PeopleTaskConflictError` and `PeopleTaskTimeoutError`.

## Architecture overview

The SDK is intentionally small.

- `desearch_py/api.py` contains the `Desearch` client and every HTTP method.
- `desearch_py/models.py` contains enums and permissive `pydantic` schemas.
- `desearch_py/__init__.py` re-exports the public API.

Key design decisions visible in code:

- the HTTP session is created lazily on first use
- auth is sent as `Authorization: <api_key>` with no `Bearer` prefix
- most requests share a single helper with a fixed 120 second timeout
- successful responses can opt in to a `DesearchResponse` wrapper with parsed cost metadata and the social `next_cursor` from response headers
- path parameters are percent-encoded as one segment, `/` included
- `x_posts_by_urls` and the extraction methods use specialized request paths for repeated query parameters and text responses, while still supporting the metadata wrapper
- some endpoints fall back to raw `dict` values instead of failing model parsing
- `ai_search` always sends `"streaming": False`; `stream_network_stats` is the only streaming method, with its own Server-Sent Events decoder
- People Search searches are background tasks; `wait_for_people_task` and `iter_people_results` are the SDK's only polling and pagination helpers (social list methods return one page and leave the cursor to you)

## Usage notes

### HTTP error compatibility contract

Every public SDK method raises `DesearchAPIError` for an HTTP 4xx or 5xx response. The exception exposes:

- `status`: the integer HTTP status code
- `message`: the HTTP reason phrase
- `body`: the response body as text, whether it is JSON, non-JSON text, or an empty string
- `args`: `(status, message, body)` for callers that inspect standard exception arguments

The API key is redacted from `message`, `body`, `str(error)`, `repr(error)`, `error.args`, and SDK error logs. An underlying `aiohttp.ClientResponseError` is not retained as the exception cause or context because its request headers may contain the API key.

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
- the TikTok, Instagram, and Facebook methods that return a list: they return the raw `dict` when the API answers with an object instead of a list

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

- describe unsupported streaming or retry behavior as implemented (only `stream_network_stats` streams)
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
