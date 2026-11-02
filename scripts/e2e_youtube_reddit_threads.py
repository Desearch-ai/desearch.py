#!/usr/bin/env python3
"""Live smoke test for the YouTube, Reddit and Threads methods (desearch-py 1.11.0).

Calls the real Desearch API once per method, reads one more page wherever a
list method returns a cursor, checks the billing headers (1 unit per
request), and checks that an invalid cursor is a free 422. Prints one line per
call: ``PASS name`` or ``FAIL name: error``. Exits 1 if any call fails, 2 if
the API key is not set.

Usage::

    DESEARCH_API_KEY=... python scripts/e2e_youtube_reddit_threads.py
    python scripts/e2e_youtube_reddit_threads.py --base-url https://api-dev.desearch.ai \\
        --key-env DESEARCH_DEV_API_KEY

The key is read from the environment variable named by ``--key-env``
(default ``DESEARCH_API_KEY``), or from ``~/.config/desearch/e2e.env``. About
24 billed requests at $0.00207 each (about $0.05). A 5xx is retried once,
because the upstream provider sometimes returns a transient 503.

The script imports the SDK from this working tree, not from site-packages.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from desearch_py import (  # noqa: E402
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    RedditComment,
    RedditPost,
    RedditSubreddit,
    ThreadsPost,
    ThreadsPostDetail,
    ThreadsProfile,
    ThreadsUser,
    YouTubeChannel,
    YouTubeComment,
    YouTubeItem,
    YouTubeTranscript,
    YouTubeVideo,
)

# Public inputs that exist. The post IDs are fallbacks used only when the
# search before them returns nothing.
QUERY = "bittensor"
YOUTUBE_VIDEO_ID = "dQw4w9WgXcQ"
YOUTUBE_CHANNEL = "@MrBeast"
SUBREDDIT = "AskReddit"
FALLBACK_REDDIT_POST_ID = "1q6pxwn"
THREADS_USER = "zuck"
FALLBACK_THREADS_CODE = "DK-BydcJHkF"


def _load_env_file() -> None:
    path = Path.home() / ".config" / "desearch" / "e2e.env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if value and not os.environ.get(key):
            os.environ[key] = value


class SmokeRun:
    def __init__(self, client: Desearch) -> None:
        self.client = client
        self.failures = 0
        self.billed_usd = 0.0

    def report(self, name: str, error: Optional[str] = None, detail: str = "") -> None:
        if error is None:
            print(f"PASS {name}" + (f" ({detail})" if detail else ""), flush=True)
        else:
            self.failures += 1
            print(f"FAIL {name}: {error}", flush=True)

    async def call(
        self,
        name: str,
        make_call: Callable[[], Awaitable[Any]],
        check: Callable[[Any], str],
    ) -> Any:
        """Run one call (retried once after a 5xx). ``check`` returns a detail or raises."""
        try:
            try:
                result = await make_call()
            except DesearchAPIError as exc:
                if exc.status < 500:
                    raise
                print(f"RETRY {name}: HTTP {exc.status}", flush=True)
                result = await make_call()
            if isinstance(result, DesearchResponse):
                self._check_billing(result)
            detail = check(result)
        except Exception as exc:  # noqa: BLE001 - report every failure and go on
            self.report(name, f"{type(exc).__name__}: {exc}")
            return None
        self.report(name, detail=detail)
        return result

    def _check_billing(self, page: DesearchResponse) -> None:
        if page.metadata.usage_count != 1:
            raise AssertionError(f"usage_count {page.metadata.usage_count}, expected 1")
        if page.metadata.cost_usd is None:
            raise AssertionError("no X-Desearch-Cost-Usd header")
        self.billed_usd += page.metadata.cost_usd

    async def list_call(
        self,
        name: str,
        method: Callable[..., Awaitable[Any]],
        model: type,
        *args: Any,
        paginated: bool = True,
        **kwargs: Any,
    ) -> List[Any]:
        """Call a list method; if it returns a cursor, read one more page."""

        def check(page: Any) -> str:
            if not isinstance(page, DesearchResponse):
                raise TypeError(f"expected DesearchResponse, got {type(page).__name__}")
            if not isinstance(page.data, list):
                raise TypeError(f"expected a list body, got {page.data!r:.200}")
            for item in page.data:
                if not isinstance(item, model):
                    raise TypeError(f"expected {model.__name__}, got {type(item).__name__}")
            cursor = page.metadata.next_cursor
            if cursor is not None and not paginated:
                raise AssertionError("this route should not return a cursor")
            return (
                f"{len(page.data)} items, next_cursor={'yes' if cursor else 'no'}, "
                f"${page.metadata.cost_usd}"
            )

        page = await self.call(
            name, lambda: method(*args, include_metadata=True, **kwargs), check
        )
        if page is None:
            return []
        items = list(page.data)
        cursor = page.metadata.next_cursor
        if paginated and cursor:
            next_page = await self.call(
                f"{name} [page 2]",
                lambda: method(*args, cursor=cursor, include_metadata=True, **kwargs),
                check,
            )
            if next_page is not None:
                items.extend(next_page.data)
        return items

    async def object_call(
        self,
        name: str,
        method: Callable[..., Awaitable[Any]],
        model: type,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        def check(result: Any) -> str:
            if not isinstance(result, DesearchResponse):
                raise TypeError(f"expected DesearchResponse, got {type(result).__name__}")
            if not isinstance(result.data, model):
                raise TypeError(f"expected {model.__name__}, got {type(result.data).__name__}")
            if result.metadata.next_cursor is not None:
                raise AssertionError("an object route should not return a cursor")
            return f"${result.metadata.cost_usd}"

        page = await self.call(
            name, lambda: method(*args, include_metadata=True, **kwargs), check
        )
        return None if page is None else page.data

    async def expect_status(
        self, name: str, make_call: Callable[[], Awaitable[Any]], status: int
    ) -> None:
        try:
            await make_call()
        except DesearchAPIError as exc:
            if exc.status == status:
                self.report(name, detail=f"HTTP {status}, not billed")
            else:
                self.report(name, f"HTTP {exc.status}, expected {status}")
            return
        self.report(name, f"succeeded, expected HTTP {status}")


def _first(items: List[Any], attribute: str, fallback: str) -> str:
    for item in items:
        value = getattr(item, attribute, None)
        if value:
            return str(value)
    return fallback


async def run_youtube(run: SmokeRun) -> None:
    c = run.client
    await run.list_call("youtube_search", c.youtube_search, YouTubeItem, QUERY, type="videos")
    video = await run.object_call(
        "youtube_video", c.youtube_video, YouTubeVideo, YOUTUBE_VIDEO_ID
    )
    if video is not None and video.id != YOUTUBE_VIDEO_ID:
        run.report("youtube_video id", f"got {video.id!r}")
    await run.object_call(
        "youtube_video [URL id]",
        c.youtube_video,
        YouTubeVideo,
        f"https://youtu.be/{YOUTUBE_VIDEO_ID}",
    )
    transcript = await run.object_call(
        "youtube_transcript",
        c.youtube_transcript,
        YouTubeTranscript,
        YOUTUBE_VIDEO_ID,
        language="en",
    )
    if transcript is not None and not transcript.segments:
        run.report("youtube_transcript segments", "no segments")
    await run.list_call(
        "youtube_comments", c.youtube_comments, YouTubeComment, YOUTUBE_VIDEO_ID
    )
    await run.object_call(
        "youtube_channel", c.youtube_channel, YouTubeChannel, YOUTUBE_CHANNEL
    )
    await run.list_call(
        "youtube_channel_videos",
        c.youtube_channel_videos,
        YouTubeItem,
        YOUTUBE_CHANNEL,
        sort="latest",
    )


async def run_reddit(run: SmokeRun) -> None:
    c = run.client
    posts = await run.list_call("reddit_search", c.reddit_search, RedditPost, QUERY)
    await run.object_call(
        "reddit_subreddit", c.reddit_subreddit, RedditSubreddit, SUBREDDIT
    )
    await run.list_call(
        "reddit_subreddit_posts",
        c.reddit_subreddit_posts,
        RedditPost,
        SUBREDDIT,
        sort="top",
        timeframe="week",
    )
    post_id = _first(posts, "id", FALLBACK_REDDIT_POST_ID)
    await run.object_call("reddit_post_by_id", c.reddit_post_by_id, RedditPost, post_id)
    await run.list_call("reddit_comments", c.reddit_comments, RedditComment, post_id)
    await run.expect_status(
        "reddit_comments [invalid cursor]",
        lambda: c.reddit_comments(post_id, cursor="not-a-cursor"),
        422,
    )


async def run_threads(run: SmokeRun) -> None:
    c = run.client
    posts = await run.list_call(
        "threads_search", c.threads_search, ThreadsPost, QUERY, paginated=False
    )
    await run.list_call(
        "threads_search_users",
        c.threads_search_users,
        ThreadsUser,
        THREADS_USER,
        paginated=False,
    )
    await run.object_call(
        "threads_profile", c.threads_profile, ThreadsProfile, THREADS_USER
    )
    profile_posts = await run.list_call(
        "threads_profile_posts",
        c.threads_profile_posts,
        ThreadsPost,
        THREADS_USER,
        paginated=False,
    )
    code = _first(profile_posts or posts, "code", FALLBACK_THREADS_CODE)
    await run.object_call(
        "threads_post_by_id", c.threads_post_by_id, ThreadsPostDetail, code
    )


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DESEARCH_BASE_URL", "https://api.desearch.ai"),
        help="API base URL (default: $DESEARCH_BASE_URL or production)",
    )
    parser.add_argument(
        "--key-env",
        default="DESEARCH_API_KEY",
        help="environment variable that holds the API key (default: DESEARCH_API_KEY)",
    )
    args = parser.parse_args()

    _load_env_file()
    api_key = os.environ.get(args.key_env, "").strip()
    if not api_key:
        print(f"{args.key_env} is not set", file=sys.stderr)
        return 2

    async with Desearch(api_key=api_key, base_url=args.base_url) as client:
        run = SmokeRun(client)
        await run_youtube(run)
        await run_reddit(run)
        await run_threads(run)

    print(
        f"{run.failures} failure(s); billed ${run.billed_usd:.5f} on {args.base_url}",
        flush=True,
    )
    return 1 if run.failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
