# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` is a thin `aiohttp` client for the Desearch public API. It wraps AI search, the Search API, X, TikTok, Instagram, Facebook, YouTube, Reddit, Threads, extraction, People Search, Company Search, and the public network stats behind a single async client class and returns `pydantic` models for most successful responses. The package metadata currently reports **version 1.13.0** and requires **Python 3.10+**. See [CHANGELOG.md](CHANGELOG.md) for unreleased and breaking changes.

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

`response.metadata.next_cursor` holds the `x-desearch-next-cursor` header, which the TikTok, Instagram, Facebook, YouTube, and Reddit list methods send when another page exists. See [Pagination](#pagination).

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
| `facebook_search(query, count=None, cursor=None, sort=None)` | `POST /desearch/facebook/search` | `List[FacebookPost]` (Ad Library records) | yes |
| `facebook_post_by_id(id)` | `GET /desearch/facebook/post/{id}` | `FacebookPost` | no |
| `facebook_profile(profile_id)` | `GET /desearch/facebook/profile/{profile_id}` | `FacebookProfile` | no |
| `facebook_profile_posts(profile_id, count=None, cursor=None)` | `GET /desearch/facebook/profile/{profile_id}/posts` | `List[FacebookPost]` | yes |
| `facebook_comments(post_id, count=None, cursor=None)` | `GET /desearch/facebook/comments/{post_id}` | `List[FacebookComment]` | yes |
| `facebook_hashtag(tag, count=None, cursor=None)` | `GET /desearch/facebook/hashtag/{tag}` | `List[FacebookPost]` (Ad Library records) | yes |

Every method also takes the keyword-only `include_metadata`. `count` is a maximum (1-100); the API default is 10 for the three search methods and 20 elsewhere. Model fields keep the API's camelCase names (`createTime`, `playCount`, `fullName`), and every field is optional because the public sources do not always send it.

- Pass usernames without `@` and hashtags without `#`.
- `TikTokPost.id` is the video ID that `tiktok_comments` takes. `instagram_comments` takes the post shortcode (`InstagramMedia.shortcode`, the code in `instagram.com/p/<shortcode>/`); a numeric media ID returns 404.
- `facebook_search` and `facebook_hashtag` search the public Meta Ad Library, not organic posts. Their results set the ad fields of `FacebookPost`: `linkUrl`, `cta`, `headline`, `linkDescription`, `endDate`, `active`, and `platforms`. `facebook_search(sort=...)` is `impressions` (the API default: most seen first) or `recent` (Meta's monthly relevance grouping, which puts recently started ads first).
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

- Send the cursor back unchanged, to the same method with the same target (username, tag, post ID, or query; for `tiktok_search` and `facebook_search`, also the same `sort`). It is opaque: never build, edit, or reuse one elsewhere.
- A cursor is valid for 24 hours. An expired cursor, one from another route or target, or any value the API did not issue gets HTTP 422 (raised as `DesearchAPIError`) and is not charged.
- `next_cursor` is `None` on the last page. A page shorter than `count` is not the end: one request reads one provider page, which can be smaller (about 3 for Facebook profile posts, 10 for Facebook comments, 12 for Instagram profile posts).
- Items the previous page already returned are dropped from the next one, so a page can hold fewer items than the provider sent.
- `tiktok_trending`, `instagram_search`, and the Threads methods do not paginate.

## YouTube, Reddit, and Threads

Public YouTube videos, transcripts, comments and channels; Reddit posts, subreddits and comment trees; and Threads posts and profiles. Each call is billed as one request ($2.07 per 1,000), including an empty page; a 404, a 422, and a 5xx are not charged. Path parameters are percent-encoded, so a full video, post, or thread URL works where an ID does.

| Method | Route | Returns | Pages with `cursor` |
|---|---|---|---|
| `youtube_search(query, type=None, upload_date=None, sort_by=None, duration=None, cursor=None)` | `POST /desearch/youtube/search` | `List[YouTubeItem]` | yes |
| `youtube_video(id)` | `GET /desearch/youtube/video/{id}` | `YouTubeVideo` | no |
| `youtube_transcript(video_id, language=None)` | `GET /desearch/youtube/transcript/{video_id}` | `YouTubeTranscript` | no |
| `youtube_comments(video_id, order=None, cursor=None)` | `GET /desearch/youtube/comments/{video_id}` | `List[YouTubeComment]` | yes |
| `youtube_channel(handle)` | `GET /desearch/youtube/channel/{handle}` | `YouTubeChannel` | no |
| `youtube_channel_videos(handle, sort=None, cursor=None)` | `GET /desearch/youtube/channel/{handle}/videos` | `List[YouTubeItem]` | yes |
| `reddit_search(query, sort=None, timeframe=None, cursor=None)` | `POST /desearch/reddit/search` | `List[RedditPost]` | yes |
| `reddit_subreddit(name)` | `GET /desearch/reddit/subreddit/{name}` | `RedditSubreddit` | no |
| `reddit_subreddit_posts(name, sort=None, timeframe=None, cursor=None)` | `GET /desearch/reddit/subreddit/{name}/posts` | `List[RedditPost]` | yes |
| `reddit_post_by_id(id)` | `GET /desearch/reddit/post/{id}` | `RedditPost` | no |
| `reddit_comments(post_id, cursor=None)` | `GET /desearch/reddit/comments/{post_id}` | `List[RedditComment]` | yes |
| `threads_search(query, start_date=None, end_date=None)` | `POST /desearch/threads/search` | `List[ThreadsPost]` | no |
| `threads_search_users(query)` | `POST /desearch/threads/search/users` | `List[ThreadsUser]` | no |
| `threads_profile(username)` | `GET /desearch/threads/profile/{username}` | `ThreadsProfile` | no |
| `threads_profile_posts(username)` | `GET /desearch/threads/profile/{username}/posts` | `List[ThreadsPost]` | no |
| `threads_post_by_id(id)` | `GET /desearch/threads/post/{id}` | `ThreadsPostDetail` | no |

Every method also takes the keyword-only `include_metadata`. These routes take no `count`: a page is whatever YouTube or Reddit returns (about 20 YouTube results, 30 channel videos, a few Reddit posts). Unset filters are not sent, so the API defaults apply.

- Filter values: `youtube_search` `type` is `videos`, `shorts`, `channels` or `playlists`; `upload_date` is `today`, `this_week`, `this_month` or `this_year`; `sort_by` is `relevance` or `popular`; `duration` is `under_3_min`, `between_3_and_20_min` or `over_20_min`. `youtube_comments` `order` is `top` or `newest`; `youtube_channel_videos` `sort` is `latest` (default) or `popular`. `reddit_search` `sort` is `relevance`, `new`, `top` or `comment_count`; `reddit_subreddit_posts` `sort` is `best`, `hot`, `new`, `top` or `rising`; `timeframe` is `all`, `day`, `week`, `month` or `year`.
- `YouTubeItem.type` is `video`, `short`, `live`, `channel` or `playlist`. List items only carry a relative date (`publishedText`, such as "9 days ago"); `publishedAt` is derived from it.
- `youtube_transcript` raises `DesearchAPIError` with status 404 (not charged) when the video has no captions. `YouTubeVideo.captionLanguages` lists the `languageCode` values it takes.
- `youtube_channel` and `youtube_channel_videos` take a handle with or without `@`, or a channel ID (`UC…`).
- Subreddit names are case-sensitive (`AskReddit`, not `askreddit`). On `reddit_subreddit_posts`, `timeframe` applies to `sort="top"`; without a `sort` it means top.
- `reddit_comments` returns top-level comments with the replies Reddit loaded alongside them in `RedditComment.replies`; `hasMoreReplies` says Reddit has more than it loaded.
- Threads routes never page. `ThreadsPost.replies` is the reply count; `threads_post_by_id` returns the replies themselves in `ThreadsPostDetail.comments`, and the author's continuation posts in `threadItems`.

Paging works as for TikTok (see [Pagination](#pagination)): pass `include_metadata=True`, read `page.metadata.next_cursor`, and send it back as `cursor` with the same target and filters.

```python
async with Desearch(api_key="your_api_key") as client:
    cursor = None
    for _ in range(3):  # read up to three pages of a channel's uploads
        page = await client.youtube_channel_videos(
            "@MrBeast", sort="latest", cursor=cursor, include_metadata=True
        )
        for video in page.data:
            print(video.id, video.title, video.views)
        cursor = page.metadata.next_cursor
        if cursor is None:
            break
```

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

## Company Search

Company Search finds companies, not pages. Describe the companies you want in plain language and get each one with a fit score, its public emails, phones, and social profiles, and its leaders (by default the CEO, founders, CTO, and CFO) with their LinkedIn profiles and emails. Company Enrich collects the same data for domains you already have. Every contact keeps the page it came from (`source_url`). Both run in the background as tasks on the People Search engine: you start one, wait for it, then read or export the companies (1.10.0 and later).

```python
import asyncio

from desearch_py import CompanyRequirement, CompanySearchFilters, Desearch


async def main() -> None:
    async with Desearch(api_key="your_api_key") as client:
        # 1. Start the search. This is the only billed call.
        task = await client.company_search(
            query="Series A fintech startups in Berlin building payment infrastructure",
            count=25,
            min_score=60,
            exclude=["stripe.com"],
            filters=CompanySearchFilters(
                countries=["DE"], require=[CompanyRequirement.EMAIL]
            ),
            idempotency_key="berlin-fintech-2026-10",
        )
        print(task.task_id, task.status, task.reserved_cost_usd)

        # 2. Wait until it ends (polls every 5 seconds, up to 10 minutes).
        task = await client.wait_for_company_task(task.task_id)
        print(task.status, task.completion_reason, task.result_count, task.final_cost_usd)

        # 3. Read every company, page by page.
        async for company in client.iter_company_results(task.task_id):
            score = company.score.value if company.score else None
            primary = company.primary_email.value if company.primary_email else None
            print(company.domain, company.name, score, primary)

        # 4. Or download them all as CSV, one row per company.
        csv_text = await client.export_company_results(task.task_id, format="csv")
        with open("companies.csv", "w", encoding="utf-8", newline="") as handle:
            handle.write(csv_text)


asyncio.run(main())
```

Company Enrich starts from domains or URLs instead of a description. The API reduces each one to its host without `www.`, lowercases and deduplicates them, and the task's `count` is the number left:

```python
task = await client.company_enrich(
    domains=["acme.com", "https://www.beta.io/about"],
    roles=["ceo", "cto"],
)
print(task.count, task.query)  # 2 "acme.com, beta.io"

task = await client.wait_for_company_task(task.task_id)
async for company in client.iter_company_results(task.task_id):
    print(company.domain, company.score)  # score is None for Company Enrich
```

### Company Search pricing

You are billed per company delivered. Company Search reserves `count` companies at the route price; when it ends you pay only for the companies it delivered, with a minimum of 1 when it delivers any. Such a search stops once it costs more than the companies it found pay for (`completion_reason` `cost_limit`, `coverage_limited` true). With a search budget (`max_cost_usd`, see [Search budget and continuing a search](#search-budget-and-continuing-a-search)) the whole budget is reserved instead, and the search effort is billed where the companies delivered do not cover it, up to the budget. Company Enrich reserves one company per domain you send, with the same minimum of 1; the rest of the reservation, including duplicate domains, is returned. A company left out by `min_score` or `filters.require` is not billed, and a task that delivers no companies is free. Waiting, reading results, exports, listing tasks, pausing, resuming, and cancelling are free. Results are kept 30 days after the task ends. See <https://desearch.ai/pricing> for current prices.

### Company Search methods

| Method | Route | Returns |
|---|---|---|
| `company_search` | `POST /desearch/companies/search` | `CompanyTask` |
| `company_enrich` | `POST /desearch/companies/enrich` | `CompanyTask` |
| `list_company_tasks` | `GET /desearch/companies/tasks` | `CompanyTaskList` |
| `get_company_task` | `GET /desearch/companies/tasks/{task_id}` | `CompanyTask` |
| `get_company_results` | `GET /desearch/companies/tasks/{task_id}/results` | `CompanyResultsPage` |
| `pause_company_task` / `resume_company_task` / `cancel_company_task` | `POST /desearch/companies/tasks/{task_id}/pause` (`/resume`, `/cancel`) | `CompanyTask` |
| `export_company_results` | `GET /desearch/companies/tasks/{task_id}/export` | CSV or JSON Lines text |
| `wait_for_company_task` | polls `get_company_task` | the ended `CompanyTask` |
| `iter_company_results` | follows `next_cursor` on `get_company_results` | async iterator of `Company` |

`company_search` takes `query` (3-1000 characters), `count` (5-200, API default 25), `min_score` (0-100), `exclude` (domains or URLs to skip, up to 1000), `roles`, `infer_emails`, `verify_emails`, `filters`, and `metadata`, and the keyword-only `max_cost_usd` and `continue_from` (1.12.0 and later; see below). `company_enrich` takes `domains` (1-200 domains or URLs), `roles`, `infer_emails`, `verify_emails`, and `metadata`.

- `roles` lists the leaders to look for (`CompanyRole`): `ceo`, `founder`, `cto`, `cfo`, `coo`, `cmo`, `president`, `owner`, `managing_director`. The API default is `ceo`, `founder`, `cto`, `cfo`. A managing director (Geschäftsführer) counts as `ceo` when `ceo` is asked for.
- `infer_emails` (API default `True`) guesses leaders' emails from the company's address pattern. `verify_emails` (API default `True`) checks every email; turn it off to finish sooner without `verification`.
- `filters` is a `CompanySearchFilters` or a dict: `countries` (ISO 3166-1 alpha-2 codes or names, up to 20; scoring treats them as a location criterion) and `require` (`CompanyRequirement`: `email`, `phone`, `linkedin`, `leader`, `leader_email`). A company that does not have what you require is not delivered and not billed.
- `metadata`, `idempotency_key`, and `include_metadata=True` work as in People Search. `list_company_tasks` takes `type` (`search` or `enrich`, see `CompanyTaskType`), `status`, `limit`, `cursor`, and a `metadata` filter, like `list_people_tasks`. People Search tasks are not listed there.
- `wait_for_company_task` works like `wait_for_people_task` and raises `CompanyTaskTimeoutError` (with the last state on `.task`) on timeout.
- A `query` that names the only companies wanted with their websites ("Restrict this search to Acme (acme.com.au) and Beta (beta.co.uk). Return only those.") checks only those domains: `task.interpreted["interpretation"]["only_domains"]` lists them, and the task ends with `completion_reason` `all_domains_processed`. Companies named without their websites cannot restrict the search: it runs as usual, with the task warning `scope_not_applied`.

### Search budget and continuing a search

Without a budget, a Company Search stops once it costs more than the companies it found pay for: `completion_reason` is `cost_limit` and `coverage_limited` is true, with fewer than `count` companies. Two keyword-only arguments of `company_search` (1.12.0 and later) take it further:

- `max_cost_usd`: your search budget in USD, above 0 and at most 100, and at least what `count` reserves (`count` times the route price; below that the API returns 422). The whole budget is reserved, and the search keeps going until it delivers `count` or spends the budget. Its search effort (`task.progress["effort_units"]`, in companies at the route price) is billed where the companies delivered do not cover it, up to the budget, even when it finds few companies or none. The unused budget is returned. Only set it when you are willing to spend that amount.
- `continue_from`: the `task_id` (a string or `UUID`) of an ended Company Search of yours. The new search leaves out every company that one delivered, held for review (`progress["review"]`) or excluded, so it only finds new ones. Send the same `query` and filters with the `count` still wanted. The API returns 409 while that task is running or paused, and 404 if it is not your Company Search.

Both are sent only when given, and `task.request` keeps them.

```python
task = await client.wait_for_company_task(task.task_id)
if task.coverage_limited and task.completion_reason == "cost_limit":
    more = await client.company_search(
        query="Series A fintech startups in Berlin building payment infrastructure",
        count=max(5, task.count - task.result_count),
        min_score=60,
        exclude=["stripe.com"],
        filters=CompanySearchFilters(countries=["DE"], require=[CompanyRequirement.EMAIL]),
        continue_from=task.task_id,
        max_cost_usd=5,  # billed for search effort up to $5, even if it finds few companies
    )
```

### How companies fill in

Each company goes through five stages: `profile` (the homepage, and for Company Search the fit score), `contacts` (up to 4 contact, imprint, team, and about pages), `people` (leaders from the site's own pages, then LinkedIn), `email_patterns` (leaders' emails inferred from the company's pattern), and `email_check` (every email checked). A company is published as soon as the stages its request needs have run, with `enrichment.status` `partial`. The later stages fill it in on the server, and it is `complete` once no stage is `pending` (a stage cut by the time limit is `skipped`).

| `filters.require` contains | Published after |
|---|---|
| nothing (and every Company Enrich) | `profile` |
| `email`, `phone`, `linkedin` | `contacts` |
| `leader` | `people` |
| `leader_email` | `email_check` |

- While companies already published are still being filled in, the task is `running` with `stage` `enriching`. Read the companies after `wait_for_company_task` returns to get their final version.
- `get_company_results` and `iter_company_results` return each company as it is when read. Keep `next_cursor` to get only new companies, and read again without `cursor` to get the latest version of the ones you have.
- Fields a later stage fills in are optional: `people`, `phones`, and `socials` are `[]`, and `primary_email`, `primary_contact`, `contact_coverage`, and each email's `verification` are `None` until their stage has run.
- `enrichment.stages` says where a company is: each stage is `pending`, `done`, `failed`, or `skipped` (turned off by the request, such as `infer_emails=False`, or nothing to do). `enrichment.errors` lists what failed.

### Reading a company

```python
async for company in client.iter_company_results(task.task_id):
    print(company.name, company.domain, company.industry)
    for email in company.emails:
        print("  company email:", email.value, email.type, email.source_url)
    if company.score:  # None for Company Enrich
        unverified = [check.criterion for check in company.score.unverified_criteria]
        print("  score:", company.score.value, company.score.fully_verified, unverified)
    for leader in company.people:
        print("  leader:", leader.name, leader.title, leader.roles, leader.linkedin_url)
        for email in leader.emails:
            status = email.verification.status if email.verification else None
            # An inferred email is guessed from the company's address pattern.
            print("    ", email.value, email.source, email.confidence, email.pattern, status)
```

- `emails[].type` is `personal`, `leadership`, `sales`, `general`, `press`, `support`, `careers`, `legal`, or `other`. `primary_email` is only ever `personal`, `leadership`, `sales`, or `general`, and an inferred one only when it is `valid`. `primary_contact` is the person to contact first, with the `reason` they were picked.
- `source` (`website`, `search`, `linkedin`, or `inferred`) and `source_url` say where each email, phone, and social profile came from. An inferred email has no `source_url`, a `confidence` of `high` (pattern learned from the company's own addresses) or `low` (a common pattern), and the `pattern` used, such as `first.last`.
- `verification.status` (`CompanyEmailStatus`) is `valid`, `invalid`, `risky` (catch-all domain, or no MX record but an A record), or `unknown` (nothing could confirm or refute it). `verification.checks` has `syntax`, `mx`, `smtp`, and `web`.
- `people[].verified` is true when a quote on the company's own site or the person's current LinkedIn position shows the role. `people[].evidence` holds the quote and its page.
- `contact_coverage` says what was found, under the names `filters.require` uses.
- `score.criteria_checks` reuses `PeopleCriterionCheck`, and `score.unverified_criteria` and `score.fully_verified` work as in People Search, against the company's own pages. `score.relevance` is `high`, `medium`, or `low`.
- `task.completion_reason` (`CompanyCompletionReason`) adds `all_domains_processed` (Company Enrich, or a Company Search restricted to the domains its query names, read every domain) to the People Search reasons. `coverage_limited` works as in People Search, and `warnings` holds `CompanyTaskWarning` items such as `enrichment_time_limit`. `task.request` is the normalized request.
- The CSV export has one row per company: domain, name, score, location, primary email, emails, phones, and social profiles, then the CEO (or managing director), founder, CTO, and CFO with title, email, email status, and LinkedIn, and `fully_verified`, `unverified_criteria`, and `enrichment_status`. JSON Lines has every field.

### Company Search errors

HTTP errors raise `DesearchAPIError`, with the same statuses as People Search:

- `402`: the account has no credits for the reservation.
- `422`: an invalid request, for example a domain that is an IP address or `localhost`, or a `max_cost_usd` below what `count` reserves.
- `409` from `company_search` with `continue_from`: the search to continue from is still running or paused. It is a plain `DesearchAPIError`, not a `CompanyTaskConflictError`.
- `429`: too many People Search and Company Search tasks are already queued, running, or paused.
- `404`: the task does not exist or belongs to another account. A People Search task ID is a 404 on the company routes, and a company task ID on the People Search routes. `continue_from` gets a 404 for a task that is not your Company Search (a People Search or Company Enrich task included).
- `410`: the results expired (they are kept 30 days after the task ends).
- `409` from pause, resume, or cancel raises `CompanyTaskConflictError`, a `DesearchAPIError` subclass. `.detail` explains why, and `.task` holds the task's current state as a `CompanyTask`.

## Monitors

A monitor is a search that runs on a schedule and returns only what is new since its last run. Each run searches its sources (`web`, `x`, `reddit`, `youtube`, `threads`, `tiktok`, `meta_ads`), or reads the accounts and hashtags it watches (also on `instagram` and `facebook`, which only watch accounts or hashtags), inside a time window that starts where the previous run ended, drops everything the monitor has already seen, screens the rest with an AI classifier against your `query` and `criteria`, and keeps the items that score at least `min_score`. Kept items stay readable through the API and go to your webhook (1.13.0 and later).

```python
import asyncio

from desearch_py import Desearch, MonitorEvent, MonitorInterval, MonitorSource


async def main() -> None:
    async with Desearch(api_key="your_api_key") as client:
        # The most one run, and a month of runs, can cost. Free.
        estimate = await client.estimate_monitor(
            sources=[MonitorSource.WEB, MonitorSource.X], interval=MonitorInterval.ONE_DAY
        )
        print(estimate.max_run_cost_usd, estimate.max_monthly_cost_usd)

        # Create it. Free; the first run is queued at once (run_now=False to wait).
        monitor = await client.create_monitor(
            query="Bittensor subnet launches and updates",
            name="Bittensor subnet news",
            criteria=["Announces a new subnet, release or partnership"],
            sources=[MonitorSource.WEB, MonitorSource.X, MonitorSource.REDDIT],
            interval=MonitorInterval.ONE_DAY,
            options={"x": {"count": 20, "lang": "en"}, "web": {"count": 10}},
            webhook={
                "url": "https://example.com/hooks/desearch",
                "events": [MonitorEvent.ITEMS_FOUND, MonitorEvent.RUN_FAILED],
            },
            metadata={"team": "growth"},
        )
        # Shown only now (and by rotate_monitor_webhook_secret). Store it.
        secret = monitor.webhook_secret

        # Run it now, wait for the run, and read what it kept.
        run = await client.trigger_monitor(monitor.monitor_id)
        run = await client.wait_for_monitor_run(monitor.monitor_id, run.run_id)
        print(run.status, run.item_count, run.cost_usd, run.stats["screen"])
        for item in run.items:
            print(item.score, item.source, item.url, item.title or item.text)

        # Everything it has kept so far, newest first, page by page.
        async for item in client.iter_monitor_items(monitor.monitor_id, source="x"):
            print(item.published_at, item.url)


asyncio.run(main())
```

### Watched accounts

Instead of searching, a source can read up to 10 accounts on every run: `options.x.accounts` (X usernames, at most 15 characters), `options.reddit.subreddits`, `options.youtube.channels` (`@handle` or a `UC…` channel ID), `options.tiktok.accounts`, and `options.threads.accounts`. Names can be pasted as `OpenAI`, `@OpenAI`, `r/LocalLLaMA`, or a profile URL; the API cleans them and returns them as `OpenAI`, `LocalLLaMA`, `@OpenAI` or `UC…`, `openai`, and `zuck`. An invalid name, or more than 10 in one list, is a 422. The `query` and `criteria` still decide what is kept, and `min_score=0` keeps every new post:

```python
monitor = await client.create_monitor(
    query="Model and API launches",
    sources=[MonitorSource.X, MonitorSource.REDDIT, MonitorSource.YOUTUBE, MonitorSource.TIKTOK],
    options={
        "x": {"accounts": ["OpenAI", "@AnthropicAI"], "min_likes": 50},
        "reddit": {"subreddits": ["r/LocalLLaMA"]},
        "youtube": {"channels": ["@OpenAI"]},
        "tiktok": {"count": 10, "accounts": ["openai"]},
    },
    min_score=0,  # keep every new post from these accounts
)
print(monitor.options["x"]["accounts"])  # ["OpenAI", "AnthropicAI"]
```

With `x.accounts`, X reads each account's timeline (20 posts), so `x.count` is not used, while `x.lang` and `x.min_likes` still filter. `tiktok.count` is per account. TikTok search has no working date filter and ranks by relevance, so a TikTok keyword monitor finds a new video only when it reaches TikTok's top results; to follow creators, watch their accounts. Threads keyword search returns loosely matched posts, so watching accounts works better there too. An account that cannot be read (unknown or private) is listed in `run.stats["sources"][source]["accounts_failed"]`; the source fails only when all of its accounts do.

### Watched hashtags

TikTok and Instagram can also watch up to 10 hashtags each: `options.tiktok.hashtags` and `options.instagram.hashtags`, in any script (`skincare`, `#სილამაზე`, or a tag URL such as `https://www.tiktok.com/tag/skincare` or `https://www.instagram.com/explore/tags/skincare/`). The API returns them without `#` (`skincare`). A hashtag feed lists popular as well as recent posts from any account, so a monitor finds posts outside the accounts it watches; the window drops the old ones and the monitor's seen items the rest. With accounts or hashtags, a source reads those feeds instead of searching by keyword. Each run reads `tiktok.count` posts per TikTok hashtag and up to 12 per Instagram hashtag. Facebook has no organic hashtag feed; for ads by keyword, use `meta_ads`. A hashtag that cannot be read is listed in `run.stats["sources"][source]["hashtags_failed"]`, and an item read from a hashtag has `data["hashtag"]`:

```python
monitor = await client.create_monitor(
    query="Posts about our skincare brand",
    sources=[MonitorSource.TIKTOK, MonitorSource.INSTAGRAM],
    options={
        "tiktok": {"count": 10, "hashtags": ["#სილამაზე", "https://www.tiktok.com/tag/skincare"]},
        "instagram": {"hashtags": ["skincare", "სილამაზე"]},  # no accounts needed
    },
    min_score=0,  # keep every new post with these hashtags
)
print(monitor.options["tiktok"]["hashtags"])  # ["სილამაზე", "skincare"]
```

### Instagram, Facebook, and Meta ads

`instagram` and `facebook` have no keyword search for posts, so they only read watched feeds: `options.instagram.accounts` (up to 10 usernames, `openai`, `@openai` or a profile URL) or `options.instagram.hashtags` (see [Watched hashtags](#watched-hashtags)), and `options.facebook.pages` (1-10 page names or numeric IDs, `NASA`, `100064869009429` or a page URL; `profile.php?id=…` and `/pages/Name/123…` links become the ID). Each run reads up to 12 posts per Instagram account or hashtag and 10 per Facebook page. Without any, `create_monitor` and `update_monitor` return 422 (`update_monitor` checks the monitor as changed: `sources` and `options` from the call, else the current ones); `estimate_monitor` prices one account instead.

`meta_ads` searches the Meta Ad Library by keyword, `options.meta_ads.count` (10, 20 or 30; default 10) ads per run. The Ad Library matches keywords, so the `query` should be a brand, product or short phrase (`ChatGPT`, `Midjourney`); a sentence finds nothing. It has no date filter: an ad counts as new the first time a run sees it, if it started within the last 30 days. Ads are screened with their own relevance question (is the ad about what the monitor watches) and have no `new_info`. For Facebook pages' own posts, watch them with `facebook` instead.

```python
monitor = await client.create_monitor(
    query="ChatGPT",
    sources=[MonitorSource.INSTAGRAM, MonitorSource.FACEBOOK, MonitorSource.META_ADS, MonitorSource.THREADS],
    options={
        "instagram": {"accounts": ["@openai"]},
        "facebook": {"pages": ["https://www.facebook.com/NASA"]},
        "meta_ads": {"count": 20},
        "threads": {"accounts": ["@zuck"]},
    },
)
print(monitor.options["facebook"]["pages"])  # ["NASA"]
```

### Monitors pricing

Creating, reading, and changing monitors is free. Each run pays for what it uses: its searches at their list price (the same as calling those endpoints yourself), AI screening per item screened ($0.05 per 1,000 items), and, with `summary=True`, the summary's LLM usage plus 50%. Runs with no new items still pay for their searches. TikTok, Instagram, Facebook and Meta ads are billed per read, $3.00 per 1,000 reads ($0.003 a read), whatever the number of posts a read returns: one read per watched account, hashtag or Facebook page, one per TikTok keyword search, and one per Ad Library page (`meta_ads`, whatever `meta_ads.count`). A read that returns nothing is free, except an empty or private TikTok account, which takes two reads, so a run's hold counts two reads per TikTok account. The other sources pay their feed's list price: an X timeline is 20 posts at the per-post X price (about $0.003), and a subreddit, YouTube channel or Threads profile is one request ($0.00207). `estimate_monitor` includes them in `breakdown`, keyed by source. When a run is queued, its `max_run_cost_usd` is held on the balance; when it ends it is billed what it used (never more than the hold) and the rest is released. A run that cannot be held fails with `insufficient_credits` and the monitor pauses until you resume it. See <https://desearch.ai/pricing>.

### Monitors methods

| Method | Route | Returns |
|---|---|---|
| `create_monitor` | `POST /desearch/monitors` | `Monitor` (with `webhook_secret` when a webhook is set) |
| `estimate_monitor` | `POST /desearch/monitors/estimate` | `MonitorEstimate` |
| `list_monitors` | `GET /desearch/monitors` | `MonitorList` |
| `get_monitor` | `GET /desearch/monitors/{monitor_id}` | `Monitor` |
| `update_monitor` | `PATCH /desearch/monitors/{monitor_id}` | `Monitor` |
| `pause_monitor` / `resume_monitor` | `PATCH /desearch/monitors/{monitor_id}` with `status` | `Monitor` |
| `delete_monitor` | `DELETE /desearch/monitors/{monitor_id}` | `MonitorDeleted` |
| `trigger_monitor` | `POST /desearch/monitors/{monitor_id}/trigger` | `MonitorRun` (queued) |
| `list_monitor_runs` | `GET /desearch/monitors/{monitor_id}/runs` | `MonitorRunList` |
| `get_monitor_run` | `GET /desearch/monitors/{monitor_id}/runs/{run_id}` | `MonitorRunWithItems` |
| `list_monitor_items` | `GET /desearch/monitors/{monitor_id}/items` | `MonitorItemList` |
| `test_monitor_webhook` | `POST /desearch/monitors/{monitor_id}/webhook/test` | `MonitorWebhookTest` |
| `rotate_monitor_webhook_secret` | `POST /desearch/monitors/{monitor_id}/webhook/rotate-secret` | `MonitorWebhookSecret` |
| `wait_for_monitor_run` | polls `get_monitor_run` | the ended `MonitorRunWithItems` |
| `iter_monitor_items` | follows `next_cursor` on `list_monitor_items` | async iterator of `MonitorItem` |

- `create_monitor` takes `query` (3-500 characters), `name`, `criteria` (up to 5, each up to 300 characters), `sources` (`MonitorSource`: `web`, `x`, `reddit`, `youtube`, `threads`, `tiktok`, `instagram`, `facebook`, `meta_ads`; API default `web` and `x`), `interval` (`MonitorInterval`: `1h`, `3h`, `6h`, `12h`, `1d`, `7d`; API default `1d`), `options` (`web.count` 10, 15 or 20; `x.count` 1-100, `x.lang`, `x.min_likes`; `tiktok.count` and `meta_ads.count` 10, 20 or 30; and the watched accounts and hashtags above, one of which `instagram` and `facebook` need), `min_score` (0-100, API default 60), `summary`, `webhook` (`url` HTTPS on a public address, `events` from `MonitorEvent`), `metadata` (up to 20 string keys, echoed in webhooks), and `run_now` (API default `True`). `estimate_monitor` takes `sources`, `options`, `summary`, and `interval`.
- `update_monitor` sends only the arguments you pass. `status="paused"` stops scheduled runs (`trigger_monitor` still works) and `status="active"` resumes them, also after a pause for `insufficient_credits` or `webhook_failing`. `remove_webhook=True` removes the webhook. `options` and `webhook` replace the current value as a whole (a `webhook` without `events` gets the default events), so read the monitor first to change one part of them. A new webhook URL gets a new `webhook_secret`, returned on that response.
- `list_monitors` takes `status` (`active`, `paused`, a list, or a comma-separated string), `limit` (1-100), and `cursor`. `list_monitor_runs` takes `limit` (1-100) and `cursor`; `list_monitor_items` takes `limit` (1-200), `cursor`, and `source` (any `MonitorSource`, such as `meta_ads`). Pass `next_cursor` back as `cursor`; it is `None` on the last page.
- `run.stats["sources"]` counts per source what was `fetched`, `in_window`, `new` and `passed` (with `accounts_failed` and `hashtags_failed` when a watched feed could not be read), and `run.stats["screen"]` is `ai` (screened by an AI classifier) or `keyword` (the fallback). An item's `score` (0-100) is the lowest of `relevant` and the criteria; `signals` has `relevant` and `new_info` (not on Meta ads), plus `criteria` (the lowest answer across the criteria) when the monitor has criteria, and `data` holds source fields (X `likes`, `reposts`, `replies`, `views`; Reddit `subreddit`, `score`, `comments`; YouTube `channel`, `views`, `thumbnail`; TikTok `views`, `likes`, `comments`, `shares`, `saves`, `duration_s`; Threads `likes`; Instagram `likes`, `comments`, `views`, `media_type`; Facebook `reactions`, `comments`, `shares`, `views`; Meta ads `page`, `active`, `cta`, `link` (the ad's landing page), `platforms`, `thumbnail`, with the ad headline as `item.title` and `item.url` the Ad Library record; web `highlights`, `domain`). TikTok, Instagram and Facebook items also have `post_id` (the ID `GET /desearch/social/post` gives the same post; an Instagram shortcode), `type` (`video`, `image`, `carousel`, `reel`, …), `hashtags`, `mentions` (TikTok and Instagram), `media` (links to the post's videos and pictures) and `thumbnail`; media and thumbnail links expire after a few days. The metrics are the post's when the run found it; `GET /desearch/social/post?url=<link>` reads them again (`author=true` adds the author's followers). An item read from a watched account also has `data["account"]`, and one read from a watched hashtag `data["hashtag"]`.
- `wait_for_monitor_run` polls every 5 seconds for up to 10 minutes and raises `MonitorRunTimeoutError` (with the last state on `.run`) on timeout.

### Verifying webhooks

Deliveries are `POST`s with `Desearch-Event`, `Desearch-Delivery`, and `Desearch-Signature: t=<unix>,v1=<hex>` headers. `verify_webhook_signature` checks the HMAC-SHA256 of `"<t>.<raw body>"` keyed with the monitor's `webhook_secret`, rejects a timestamp more than 5 minutes off, and compares in constant time. Pass the raw body, before any JSON parsing:

```python
from desearch_py import MonitorWebhookEvent, verify_webhook_signature

# e.g. in a Starlette/FastAPI handler
body = await request.body()
if not verify_webhook_signature(secret, request.headers.get("Desearch-Signature"), body):
    return Response(status_code=400)
event = MonitorWebhookEvent.model_validate_json(body)
if event.type == "monitor.items.found":
    for item in event.items:
        print(item.url, item.score)
```

Answer with a 2xx within 10 seconds. A delivery that does not get one is retried after 1, 5, 30, 120, and 360 minutes, and after 5 deliveries in a row fail every attempt, the monitor pauses with `paused_reason` `webhook_failing`. `monitor.webhook.last_delivery` (a `MonitorWebhookDelivery`, `None` before the first delivery) shows the newest one: `status` `pending` while it waits for its first or next attempt (`next_attempt_at`, with the last answer in `status_code` and `error`), `delivered`, or `failed` after every retry, plus `event`, `attempts`, `created_at`, and `delivered_at`. `test_monitor_webhook` sends a signed `monitor.test` event (with `run` `None`) and reports what your endpoint answered; it is not a delivery and leaves `last_delivery` as it was.

### Monitors errors

HTTP errors raise `DesearchAPIError`:

- `400`: an invalid body or cursor, a webhook URL that is not HTTPS on a public address, or a webhook test or secret rotation on a monitor without a webhook.
- `402`: the balance cannot hold one run (on create, also with `run_now=False`, and on trigger).
- `404`: the monitor or run does not exist or belongs to another account.
- `409`: the account already has 25 monitors (create), or a run is already queued or running (trigger).
- `422`: a value out of range or an invalid account name or hashtag (`detail` lists each), or `instagram` without watched accounts or hashtags or `facebook` without watched pages (create and update).

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

A unittest suite covers response metadata and pagination cursors, API key redaction, People Search, Company Search, the social, Search API, and network stats methods, and the Server-Sent Events decoder, with HTTP mocked or served from a local test server. There is still no dedicated lint or format command configured in the repo.

`scripts/e2e_full_coverage.py` is a live smoke test of the TikTok, Instagram, Facebook, Search API, and network stats methods, and `scripts/e2e_youtube_reddit_threads.py` of the YouTube, Reddit, and Threads methods (`--base-url`, `--key-env`). It calls the real API, so it is not part of the unit suite:

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

`format` is `"text"` (default), `"markdown"` or `"html"`. `"markdown"` keeps headings, lists, tables and code: the main content of articles and docs, and the whole page without its navigation otherwise.

```python
markdown = await client.extract(url="https://en.wikipedia.org/wiki/Artificial_intelligence", format="markdown")
```

`format="text"` returns the page's main content, which can leave out tables, notices and other sections. Pass `full_page=True` (text only) for all visible text of the page, one block per line:

```python
content = await client.extract(url="https://peles.ro/en/program-si-taxe/", full_page=True)
```

Pages that cannot be served raise `DesearchAPIError` and are not charged. The JSON body's `error_code` says why: `page_not_found` (404), `js_required` (422, retry with `js=True`), `blocked` (503, the site refused the request or answered with a bot check), `upstream_timeout` and `upstream_failed` (503).

Existing `web_crawl()` integrations continue to work through the legacy route. Use `extract()` for new integrations.

### Search API

- `search_api` — `POST /search`, ranked pages with the best matching passage. See [Search API](#search-api).

### TikTok, Instagram, and Facebook endpoints

- TikTok: `tiktok_search`, `tiktok_post_by_id`, `tiktok_profile`, `tiktok_profile_posts`, `tiktok_comments`, `tiktok_hashtag`, `tiktok_trending`
- Instagram: `instagram_search`, `instagram_media`, `instagram_profile`, `instagram_profile_posts`, `instagram_comments`, `instagram_hashtag`
- Facebook: `facebook_search`, `facebook_post_by_id`, `facebook_profile`, `facebook_profile_posts`, `facebook_comments`, `facebook_hashtag`

See [TikTok, Instagram, and Facebook](#tiktok-instagram-and-facebook) for the routes and [Pagination](#pagination) for cursors.

### YouTube, Reddit, and Threads endpoints

- YouTube: `youtube_search`, `youtube_video`, `youtube_transcript`, `youtube_comments`, `youtube_channel`, `youtube_channel_videos`
- Reddit: `reddit_search`, `reddit_subreddit`, `reddit_subreddit_posts`, `reddit_post_by_id`, `reddit_comments`
- Threads: `threads_search`, `threads_search_users`, `threads_profile`, `threads_profile_posts`, `threads_post_by_id`

See [YouTube, Reddit, and Threads](#youtube-reddit-and-threads).

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

### Company Search endpoints

- `company_search`, `company_enrich`
- `list_company_tasks`, `get_company_task`, `get_company_results`
- `pause_company_task`, `resume_company_task`, `cancel_company_task`
- `export_company_results`
- helpers: `wait_for_company_task`, `iter_company_results`

See [Company Search](#company-search) for an example, pricing, and how results fill in.

### Monitors endpoints

- `create_monitor`, `estimate_monitor`, `list_monitors`, `get_monitor`, `update_monitor`, `delete_monitor`
- `pause_monitor`, `resume_monitor`, `trigger_monitor`
- `list_monitor_runs`, `get_monitor_run`, `list_monitor_items`
- `test_monitor_webhook`, `rotate_monitor_webhook_secret`
- helpers: `wait_for_monitor_run`, `iter_monitor_items`, and `verify_webhook_signature`

See [Monitors](#monitors) for an example, pricing, and webhook verification.

### Typed exports

The package re-exports the async client plus enums and models from `desearch_py.models`, including `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `ResponseData`, `DesearchCostMetadata`, `DesearchResponse`, `TwitterScraperTweet`, `WebSearchResponse`, `WebSearchResultsResponse`, `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, and `XTrendsResponse`. 1.11.0 adds the Search API models `SearchApiResponse`, `SearchApiResult`, and the enum `SearchApiMode`; the TikTok models `TikTokPost`, `TikTokProfile`, `TikTokComment`, `TikTokAuthor`, `TikTokStats`, and `TikTokMusic`; the Instagram models `InstagramMedia`, `InstagramProfile`, `InstagramComment`, `InstagramSearchResult`, and `InstagramStats`; the Facebook models `FacebookPost`, `FacebookProfile`, `FacebookComment`, `FacebookMedia`, and `FacebookPostStats`; and the network stats models `NetworkStatsResponse`, `NetworkStatsRates`, `NetworkStatsHistoryResponse`, `NetworkStatsHistoryPoint`, and `NetworkStatsEvent`. It also adds the YouTube models `YouTubeItem`, `YouTubeVideo`, `YouTubeTranscript`, `YouTubeTranscriptSegment`, `YouTubeComment`, `YouTubeCommentAuthor`, `YouTubeChannel`, `YouTubeChannelRef`, `YouTubeChapter`, and `YouTubeCaptionLanguage`; the Reddit models `RedditPost`, `RedditComment`, and `RedditSubreddit`; and the Threads models `ThreadsPost`, `ThreadsPostDetail`, `ThreadsProfile`, and `ThreadsUser`. People Search adds `PeopleTask`, `PeopleTaskList`, `PeopleResultsPage`, `Person`, `PeopleProfile`, `PeopleProfilesPage`, `PeopleResultFilters`, the four request and filters models, the result models `PeopleTaskWarning` and `PeopleCriterionCheck`, the enums `PeoplePlatform`, `PeopleTaskStatus`, `PeopleProfileSort`, `PeopleExportFormat`, `PeopleChannel`, `PeopleCompletionReason`, `PeopleCriterionVerdict`, `PeopleEnrichment`, and `PeopleEnrichmentError`, and the errors `PeopleTaskConflictError` and `PeopleTaskTimeoutError`. Company Search adds the request models `CompanySearchRequest`, `CompanySearchFilters`, and `CompanyEnrichRequest`, the task models `CompanyTask`, `CompanyTaskList`, and `CompanyTaskWarning`, the result models `CompanyResultsPage`, `Company`, `CompanyEmail`, `CompanyEmailVerification`, `CompanyEmailChecks`, `CompanyPhone`, `CompanySocial`, `CompanyPage`, `CompanyLocation`, `CompanyPerson`, `CompanyPersonEvidence`, `CompanyPrimaryContact`, `CompanyContactCoverage`, `CompanyEnrichment`, `CompanyEnrichmentStages`, `CompanyEnrichmentError`, `CompanyScore`, and `CompanyFoundBy`, the enums `CompanyTaskType`, `CompanyRole`, `CompanyRequirement`, `CompanyCompletionReason`, and `CompanyEmailStatus`, and the errors `CompanyTaskConflictError` and `CompanyTaskTimeoutError`. It reuses `PeopleTaskStatus`, `PeopleExportFormat`, `PeopleCriterionCheck`, `PeopleTaskLinks`, and `PeopleTaskCreatedBy`. 1.13.0 adds Monitors: `Monitor`, `MonitorList`, `MonitorRun`, `MonitorRunWithItems`, `MonitorRunList`, `MonitorItem`, `MonitorItemList`, `MonitorEstimate`, `MonitorDeleted`, `MonitorWebhook`, `MonitorWebhookTest`, `MonitorWebhookSecret`, `MonitorWebhookEvent`, `MonitorWebhookMonitor`, `MonitorLastRun`, `MonitorStats`, the request models `MonitorCreateRequest`, `MonitorUpdateRequest`, `MonitorEstimateRequest`, `MonitorOptions`, `MonitorWebOptions`, `MonitorXOptions`, `MonitorRedditOptions`, `MonitorYouTubeOptions`, `MonitorTikTokOptions`, `MonitorThreadsOptions`, `MonitorInstagramOptions`, `MonitorFacebookOptions`, `MonitorMetaAdsOptions`, and `MonitorWebhookConfig`, the webhook delivery model `MonitorWebhookDelivery`, the enums `MonitorSource`, `MonitorInterval`, `MonitorEvent`, `MonitorStatus`, and `MonitorRunStatus`, `MONITOR_RUN_ENDED_STATUSES`, the error `MonitorRunTimeoutError`, `verify_webhook_signature` with `SIGNATURE_HEADER` and `DEFAULT_TOLERANCE_SECONDS`.

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
- People Search and Company Search run as background tasks; `wait_for_people_task`, `iter_people_results`, `wait_for_company_task`, and `iter_company_results` are the SDK's only polling and pagination helpers (social list methods return one page and leave the cursor to you)

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
