# Desearch

The official Python SDK for the Desearch API — AI-powered search, X (Twitter) data retrieval, web search, and crawling.

## Table of Contents

- [Installation](#installation)
- [Quick Start](#quick-start)
- [AI Contextual Search](#ai-contextual-search)
- [AI Web Links Search](#ai-web-links-search)
- [AI X Posts Links Search](#ai-x-posts-links-search)
- [X Search](#x-search)
- [Fetch Posts by URLs](#fetch-posts-by-urls)
- [Retrieve Post by ID](#retrieve-post-by-id)
- [Search X Posts by User](#search-x-posts-by-user)
- [Get Retweeters of a Post](#get-retweeters-of-a-post)
- [Get X Posts by Username](#get-x-posts-by-username)
- [Fetch User's Tweets and Replies](#fetch-users-tweets-and-replies)
- [Retrieve Replies for a Post](#retrieve-replies-for-a-post)
- [SERP Web Search](#serp-web-search)
- [Crawl a URL](#crawl-a-url)
- [Links](#links)

## Installation

```bash
pip install desearch-py
```

## Quick Start

```python
import asyncio
from desearch_py import Desearch

async def main():
    async with Desearch(api_key="your_api_key") as desearch:
        result = await desearch.ai_search(
            prompt="Bittensor",
            tools=["web", "twitter"],
        )
        print(result)

asyncio.run(main())
```

## AI Contextual Search

`ai_search`

AI-powered multi-source contextual search. Searches across web, X (Twitter), Reddit, YouTube, HackerNews, Wikipedia, and arXiv and returns results with optional AI-generated summaries. Supports streaming responses.

| Parameter                | Type            | Required | Default                    | Description                                                                                                   |
| ------------------------ | --------------- | -------- | -------------------------- | ------------------------------------------------------------------------------------------------------------- |
| `prompt`                 | `str`           | Yes      | —                          | Search query prompt                                                                                           |
| `tools`                  | `List[str]`     | Yes      | —                          | List of tools to search with (e.g. `web`, `twitter`, `reddit`, `hackernews`, `youtube`, `wikipedia`, `arxiv`) |
| `start_date`             | `Optional[str]` | No       | `None`                     | Start date in UTC (YYYY-MM-DDTHH:MM:SSZ)                                                                      |
| `end_date`               | `Optional[str]` | No       | `None`                     | End date in UTC (YYYY-MM-DDTHH:MM:SSZ)                                                                        |
| `date_filter`            | `Optional[str]` | No       | `PAST_24_HOURS`            | Predefined date filter for search results                                                                     |
| `result_type`            | `Optional[str]` | No       | `LINKS_WITH_FINAL_SUMMARY` | Result type (`ONLY_LINKS` or `LINKS_WITH_FINAL_SUMMARY`)                                                      |
| `system_message`         | `Optional[str]` | No       | `None`                     | System message for the search                                                                                 |
| `scoring_system_message` | `Optional[str]` | No       | `None`                     | System message for scoring the response                                                                       |
| `count`                  | `Optional[int]` | No       | `None`                     | Number of results per source (10–200)                                                                         |

```python
result = await desearch.ai_search(
    prompt="Bittensor",
    tools=["web", "hackernews", "reddit", "wikipedia", "youtube", "twitter", "arxiv"],
    date_filter="PAST_24_HOURS",
    result_type="LINKS_WITH_FINAL_SUMMARY",
    count=20,
)
```

## AI Web Links Search

`ai_web_links_search`

Search for raw links across web sources (web, HackerNews, Reddit, Wikipedia, YouTube, arXiv). Returns structured link results without AI summaries.

| Parameter | Type            | Required | Default | Description                                                                                            |
| --------- | --------------- | -------- | ------- | ------------------------------------------------------------------------------------------------------ |
| `prompt`  | `str`           | Yes      | —       | Search query prompt                                                                                    |
| `tools`   | `List[str]`     | Yes      | —       | List of web tools to search with (e.g. `web`, `hackernews`, `reddit`, `wikipedia`, `youtube`, `arxiv`) |
| `count`   | `Optional[int]` | No       | `None`  | Number of results per source (10–200)                                                                  |

```python
result = await desearch.ai_web_links_search(
    prompt="What are the recent sport events?",
    tools=["web", "hackernews", "reddit", "wikipedia", "youtube", "arxiv"],
    count=20,
)
```

## AI X Posts Links Search

`ai_x_links_search`

Search for X (Twitter) post links matching a prompt using AI-powered models. Returns tweet objects from the miner network.

| Parameter | Type            | Required | Default | Description                          |
| --------- | --------------- | -------- | ------- | ------------------------------------ |
| `prompt`  | `str`           | Yes      | —       | Search query prompt                  |
| `count`   | `Optional[int]` | No       | `None`  | Number of results to return (10–200) |

```python
result = await desearch.ai_x_links_search(
    prompt="What are the recent sport events?",
    count=20,
)
```

## X Search

`x_search`

X (Twitter) search with extensive filtering options: date range, user, language, verification status, media type (image/video/quote), and engagement thresholds (min likes, retweets, replies). Sort by Top or Latest.

| Parameter       | Type                        | Required | Default | Description                              |
| --------------- | --------------------------- | -------- | ------- | ---------------------------------------- |
| `query`         | `str`                       | Yes      | —       | Advanced search query                    |
| `sort`          | `Optional[str]`             | No       | `Top`   | Sort by `Top` or `Latest`                |
| `user`          | `Optional[str]`             | No       | `None`  | User to search for                       |
| `start_date`    | `Optional[str]`             | No       | `None`  | Start date in UTC (YYYY-MM-DD)           |
| `end_date`      | `Optional[str]`             | No       | `None`  | End date in UTC (YYYY-MM-DD)             |
| `lang`          | `Optional[str]`             | No       | `None`  | Language code (e.g. `en`, `es`, `fr`)    |
| `verified`      | `Optional[bool]`            | No       | `None`  | Filter for verified users                |
| `blue_verified` | `Optional[bool]`            | No       | `None`  | Filter for blue checkmark verified users |
| `is_quote`      | `Optional[bool]`            | No       | `None`  | Include only tweets with quotes          |
| `is_video`      | `Optional[bool]`            | No       | `None`  | Include only tweets with videos          |
| `is_image`      | `Optional[bool]`            | No       | `None`  | Include only tweets with images          |
| `min_retweets`  | `Optional[Union[int, str]]` | No       | `None`  | Minimum number of retweets               |
| `min_replies`   | `Optional[Union[int, str]]` | No       | `None`  | Minimum number of replies                |
| `min_likes`     | `Optional[Union[int, str]]` | No       | `None`  | Minimum number of likes                  |
| `count`         | `Optional[int]`             | No       | `20`    | Number of tweets to retrieve (1–100)     |

```python
result = await desearch.x_search(
    query="Whats going on with Bittensor",
    sort="Top",
    user="elonmusk",
    start_date="2024-12-01",
    end_date="2025-02-25",
    lang="en",
    verified=True,
    blue_verified=True,
    count=20,
)
```

## Fetch Posts by URLs

`x_posts_by_urls`

Fetch full post data for a list of X (Twitter) post URLs. Returns metadata, content, and engagement metrics for each URL.

| Parameter | Type        | Required | Default | Description                    |
| --------- | ----------- | -------- | ------- | ------------------------------ |
| `urls`    | `List[str]` | Yes      | —       | List of tweet URLs to retrieve |

```python
result = await desearch.x_posts_by_urls(
    urls=["https://x.com/RacingTriple/status/1892527552029499853"],
)
```

## Retrieve Post by ID

`x_post_by_id`

Fetch a single X (Twitter) post by its unique ID. Returns metadata, content, and engagement metrics.

| Parameter | Type  | Required | Default | Description               |
| --------- | ----- | -------- | ------- | ------------------------- |
| `id`      | `str` | Yes      | —       | The unique ID of the post |

```python
result = await desearch.x_post_by_id(
    id="1892527552029499853",
)
```

## Search X Posts by User

`x_posts_by_user`

Search X (Twitter) posts by a specific user, with optional keyword filtering.

| Parameter | Type            | Required | Default | Description                          |
| --------- | --------------- | -------- | ------- | ------------------------------------ |
| `user`    | `str`           | Yes      | —       | User to search for                   |
| `query`   | `Optional[str]` | No       | `None`  | Advanced search query                |
| `count`   | `Optional[int]` | No       | `None`  | Number of tweets to retrieve (1–100) |

```python
result = await desearch.x_posts_by_user(
    user="elonmusk",
    query="Whats going on with Bittensor",
    count=20,
)
```

## Get Retweeters of a Post

`x_post_retweeters`

Retrieve the list of users who retweeted a specific post by its ID. Supports cursor-based pagination.

| Parameter | Type            | Required | Default | Description                              |
| --------- | --------------- | -------- | ------- | ---------------------------------------- |
| `id`      | `str`           | Yes      | —       | The ID of the post to get retweeters for |
| `cursor`  | `Optional[str]` | No       | `None`  | Cursor for pagination                    |

```python
result = await desearch.x_post_retweeters(
    id="1982770537081532854",
)
```

## Get X Posts by Username

`x_user_posts`

Retrieve a user's timeline posts by their username. Fetches the latest tweets posted by that user. Supports cursor-based pagination.

| Parameter  | Type            | Required | Default | Description                 |
| ---------- | --------------- | -------- | ------- | --------------------------- |
| `username` | `str`           | Yes      | —       | Username to fetch posts for |
| `cursor`   | `Optional[str]` | No       | `None`  | Cursor for pagination       |

```python
result = await desearch.x_user_posts(
    username="elonmusk",
)
```

## Fetch User's Tweets and Replies

`x_user_replies`

Fetch tweets and replies posted by a specific user, with optional keyword filtering.

| Parameter | Type            | Required | Default | Description                            |
| --------- | --------------- | -------- | ------- | -------------------------------------- |
| `user`    | `str`           | Yes      | —       | The username of the user to search for |
| `count`   | `Optional[int]` | No       | `None`  | The number of tweets to fetch (1–100)  |
| `query`   | `Optional[str]` | No       | `None`  | Advanced search query                  |

```python
result = await desearch.x_user_replies(
    user="elonmusk",
    query="latest news on AI",
    count=20,
)
```

## Retrieve Replies for a Post

`x_post_replies`

Fetch replies to a specific X (Twitter) post by its post ID.

| Parameter | Type            | Required | Default | Description                           |
| --------- | --------------- | -------- | ------- | ------------------------------------- |
| `post_id` | `str`           | Yes      | —       | The ID of the post to search for      |
| `count`   | `Optional[int]` | No       | `None`  | The number of tweets to fetch (1–100) |
| `query`   | `Optional[str]` | No       | `None`  | Advanced search query                 |

```python
result = await desearch.x_post_replies(
    post_id="1234567890",
    query="latest news on AI",
    count=20,
)
```

## SERP Web Search

`web_search`

SERP web search. Returns paginated web search results, replicating a typical search engine experience.

| Parameter | Type            | Required | Default | Description                              |
| --------- | --------------- | -------- | ------- | ---------------------------------------- |
| `query`   | `str`           | Yes      | —       | The search query string                  |
| `start`   | `Optional[int]` | No       | `0`     | Number of results to skip for pagination |

```python
result = await desearch.web_search(
    query="latest news on AI",
    start=10,
)
```

## Crawl a URL

`web_crawl`

Crawl a URL and return its content as plain text or HTML.

| Parameter | Type            | Required | Default | Description                          |
| --------- | --------------- | -------- | ------- | ------------------------------------ |
| `url`     | `str`           | Yes      | —       | URL to crawl                         |
| `format`  | `Optional[str]` | No       | `text`  | Format of content (`html` or `text`) |

```python
result = await desearch.web_crawl(
    url="https://en.wikipedia.org/wiki/Artificial_intelligence",
    format="html",
)
```

## Links

- [Desearch](https://desearch.ai)
- [API Console](https://console.desearch.ai)
- [API Reference](https://desearch.ai/docs/api-reference/)
