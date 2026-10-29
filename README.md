# desearch-py

Official async Python SDK for the Desearch API.

`desearch-py` is a thin `aiohttp` client for the Desearch public API. It wraps search, X, extraction, People Search, and Company Search endpoints behind a single async client class and returns `pydantic` models for most successful responses. The package metadata currently reports **version 1.10.0** and requires **Python 3.10+**. See [CHANGELOG.md](CHANGELOG.md) for unreleased and breaking changes.

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

You are billed per company delivered. Company Search reserves `count` companies at the route price; when it ends you pay only for the companies it delivered, with a minimum of 2 when it delivers any. Company Enrich reserves one company per domain you send and bills a minimum of 1; the rest of the reservation, including duplicate domains, is returned. A company left out by `min_score` or `filters.require` is not billed, and a task that delivers no companies is free. Waiting, reading results, exports, listing tasks, pausing, resuming, and cancelling are free. Results are kept 30 days after the task ends. See <https://desearch.ai/pricing> for current prices.

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

`company_search` takes `query` (3-1000 characters), `count` (5-200, API default 25), `min_score` (0-100), `exclude` (domains or URLs to skip, up to 1000), `roles`, `infer_emails`, `verify_emails`, `filters`, and `metadata`. `company_enrich` takes `domains` (1-200 domains or URLs), `roles`, `infer_emails`, `verify_emails`, and `metadata`.

- `roles` lists the leaders to look for (`CompanyRole`): `ceo`, `founder`, `cto`, `cfo`, `coo`, `cmo`, `president`, `owner`, `managing_director`. The API default is `ceo`, `founder`, `cto`, `cfo`. A managing director (Geschäftsführer) counts as `ceo` when `ceo` is asked for.
- `infer_emails` (API default `True`) guesses leaders' emails from the company's address pattern. `verify_emails` (API default `True`) checks every email; turn it off to finish sooner without `verification`.
- `filters` is a `CompanySearchFilters` or a dict: `countries` (ISO 3166-1 alpha-2 codes or names, up to 20; scoring treats them as a location criterion) and `require` (`CompanyRequirement`: `email`, `phone`, `linkedin`, `leader`, `leader_email`). A company that does not have what you require is not delivered and not billed.
- `metadata`, `idempotency_key`, and `include_metadata=True` work as in People Search. `list_company_tasks` takes `type` (`search` or `enrich`, see `CompanyTaskType`), `status`, `limit`, `cursor`, and a `metadata` filter, like `list_people_tasks`. People Search tasks are not listed there.
- `wait_for_company_task` works like `wait_for_people_task` and raises `CompanyTaskTimeoutError` (with the last state on `.task`) on timeout.

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
- `task.completion_reason` (`CompanyCompletionReason`) adds `all_domains_processed` (Company Enrich read every domain) to the People Search reasons. `coverage_limited` works as in People Search, and `warnings` holds `CompanyTaskWarning` items such as `enrichment_time_limit`. `task.request` is the normalized request.
- The CSV export has one row per company: domain, name, score, location, primary email, emails, phones, and social profiles, then the CEO (or managing director), founder, CTO, and CFO with title, email, email status, and LinkedIn, and `fully_verified`, `unverified_criteria`, and `enrichment_status`. JSON Lines has every field.

### Company Search errors

HTTP errors raise `DesearchAPIError`, with the same statuses as People Search:

- `402`: the account has no credits for the reservation.
- `422`: an invalid request, for example a domain that is an IP address or `localhost`.
- `429`: too many People Search and Company Search tasks are already queued, running, or paused.
- `404`: the task does not exist or belongs to another account. A People Search task ID is a 404 on the company routes, and a company task ID on the People Search routes.
- `410`: the results expired (they are kept 30 days after the task ends).
- `409` from pause, resume, or cancel raises `CompanyTaskConflictError`, a `DesearchAPIError` subclass. `.detail` explains why, and `.task` holds the task's current state as a `CompanyTask`.

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

A unittest suite covers response metadata, API key redaction, People Search, and Company Search, with HTTP mocked or served from a local test server. There is still no dedicated lint or format command configured in the repo.

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

### Typed exports

The package re-exports the async client plus enums and models from `desearch_py.models`, including `Tool`, `WebTool`, `DateFilter`, `ResultType`, `Sort`, `ResponseData`, `DesearchCostMetadata`, `DesearchResponse`, `TwitterScraperTweet`, `WebSearchResponse`, `WebSearchResultsResponse`, `XLinksSearchResponse`, `XRetweetersResponse`, `XUserPostsResponse`, and `XTrendsResponse`. People Search adds `PeopleTask`, `PeopleTaskList`, `PeopleResultsPage`, `Person`, `PeopleProfile`, `PeopleProfilesPage`, `PeopleResultFilters`, the four request and filters models, the result models `PeopleTaskWarning` and `PeopleCriterionCheck`, the enums `PeoplePlatform`, `PeopleTaskStatus`, `PeopleProfileSort`, `PeopleExportFormat`, `PeopleChannel`, `PeopleCompletionReason`, `PeopleCriterionVerdict`, `PeopleEnrichment`, and `PeopleEnrichmentError`, and the errors `PeopleTaskConflictError` and `PeopleTaskTimeoutError`. Company Search adds the request models `CompanySearchRequest`, `CompanySearchFilters`, and `CompanyEnrichRequest`, the task models `CompanyTask`, `CompanyTaskList`, and `CompanyTaskWarning`, the result models `CompanyResultsPage`, `Company`, `CompanyEmail`, `CompanyEmailVerification`, `CompanyEmailChecks`, `CompanyPhone`, `CompanySocial`, `CompanyPage`, `CompanyLocation`, `CompanyPerson`, `CompanyPersonEvidence`, `CompanyPrimaryContact`, `CompanyContactCoverage`, `CompanyEnrichment`, `CompanyEnrichmentStages`, `CompanyEnrichmentError`, `CompanyScore`, and `CompanyFoundBy`, the enums `CompanyTaskType`, `CompanyRole`, `CompanyRequirement`, `CompanyCompletionReason`, and `CompanyEmailStatus`, and the errors `CompanyTaskConflictError` and `CompanyTaskTimeoutError`. It reuses `PeopleTaskStatus`, `PeopleExportFormat`, `PeopleCriterionCheck`, `PeopleTaskLinks`, and `PeopleTaskCreatedBy`.

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
- People Search and Company Search run as background tasks; `wait_for_people_task`, `iter_people_results`, `wait_for_company_task`, and `iter_company_results` are the SDK's only polling and pagination helpers

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
