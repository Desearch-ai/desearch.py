#!/usr/bin/env python3
"""Live smoke test for the methods added in desearch-py 1.8.0.

Calls the real Desearch API once per new method with the smallest counts,
follows one more page wherever a social list method returns a cursor, and
prints one line per call: ``PASS name`` or ``FAIL name: error``. Exits 1 if
any call fails, 2 if ``DESEARCH_API_KEY`` is not set.

Usage::

    DESEARCH_API_KEY=... python scripts/e2e_full_coverage.py
    DESEARCH_API_KEY=... python scripts/e2e_full_coverage.py --base-url https://staging-api.desearch.ai

These calls are billed at normal prices (a few cents in total). People Search
is a paid background job and is never started unless you pass
``--with-people``; that option starts one TikTok Creator Search with the
minimum count and cancels it at once.

The script imports the SDK from this working tree, not from site-packages.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from contextlib import aclosing
from pathlib import Path
from typing import Any, Awaitable, Callable, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from desearch_py import (  # noqa: E402
    Desearch,
    DesearchResponse,
    FacebookComment,
    FacebookPost,
    FacebookProfile,
    InstagramComment,
    InstagramMedia,
    InstagramProfile,
    InstagramSearchResult,
    NetworkStatsEvent,
    NetworkStatsHistoryResponse,
    NetworkStatsResponse,
    PeopleTask,
    PeopleTaskConflictError,
    SearchApiResponse,
    TikTokComment,
    TikTokPost,
    TikTokProfile,
)

# Public inputs that exist. The post IDs are fallbacks used only when the
# profile-posts call before them returns nothing.
TIKTOK_USER = "tiktok"
INSTAGRAM_USER = "instagram"
FACEBOOK_PAGE = "facebook"
HASHTAG = "ai"
FALLBACK_TIKTOK_VIDEO_ID = "7620891413932166433"
FALLBACK_INSTAGRAM_SHORTCODE = "DY79rTVS6OK"
FALLBACK_FACEBOOK_POST_ID = "1525856912919657"
STREAM_TIMEOUT_SECONDS = 15


class SmokeRun:
    def __init__(self, client: Desearch) -> None:
        self.client = client
        self.failures = 0

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
        """Run one call. ``check`` returns a short detail or raises on a bad result."""
        try:
            result = await make_call()
            detail = check(result)
        except Exception as exc:  # noqa: BLE001 - report every failure and go on
            self.report(name, f"{type(exc).__name__}: {exc}")
            return None
        self.report(name, detail=detail)
        return result

    async def list_call(
        self,
        name: str,
        method: Callable[..., Awaitable[Any]],
        model: type,
        *args: Any,
        paginated: bool = True,
        **kwargs: Any,
    ) -> List[Any]:
        """Call a social list method; if it returns a cursor, read one more page."""

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
            return f"{len(page.data)} items, next_cursor={'yes' if cursor else 'no'}"

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
    ) -> Any:
        def check(result: Any) -> str:
            if not isinstance(result, model):
                raise TypeError(f"expected {model.__name__}, got {type(result).__name__}")
            return ""

        return await self.call(name, lambda: method(*args), check)


def _first(items: List[Any], attribute: str, fallback: str) -> str:
    for item in items:
        value = getattr(item, attribute, None)
        if value:
            return str(value)
    return fallback


async def run_search_api(run: SmokeRun) -> None:
    def check(result: Any) -> str:
        if not isinstance(result, SearchApiResponse):
            raise TypeError(f"expected SearchApiResponse, got {type(result).__name__}")
        if not result.results:
            raise AssertionError("no results")
        return f"{len(result.results)} results"

    await run.call(
        "search_api",
        lambda: run.client.search_api("What is Bittensor?", mode="fast", count=10),
        check,
    )


async def run_tiktok(run: SmokeRun) -> None:
    c = run.client
    await run.list_call("tiktok_search", c.tiktok_search, TikTokPost, HASHTAG, count=2)
    await run.object_call("tiktok_profile", c.tiktok_profile, TikTokProfile, TIKTOK_USER)
    posts = await run.list_call(
        "tiktok_profile_posts", c.tiktok_profile_posts, TikTokPost, TIKTOK_USER, count=2
    )
    video_id = _first(posts, "id", FALLBACK_TIKTOK_VIDEO_ID)
    await run.object_call("tiktok_post_by_id", c.tiktok_post_by_id, TikTokPost, video_id)
    await run.list_call(
        "tiktok_comments", c.tiktok_comments, TikTokComment, video_id, count=2
    )
    await run.list_call("tiktok_hashtag", c.tiktok_hashtag, TikTokPost, HASHTAG, count=2)
    await run.list_call(
        "tiktok_trending",
        c.tiktok_trending,
        TikTokPost,
        region="US",
        count=2,
        paginated=False,
    )


async def run_instagram(run: SmokeRun) -> None:
    c = run.client
    await run.list_call(
        "instagram_search",
        c.instagram_search,
        InstagramSearchResult,
        INSTAGRAM_USER,
        count=2,
        paginated=False,
    )
    await run.object_call(
        "instagram_profile", c.instagram_profile, InstagramProfile, INSTAGRAM_USER
    )
    posts = await run.list_call(
        "instagram_profile_posts",
        c.instagram_profile_posts,
        InstagramMedia,
        INSTAGRAM_USER,
        count=2,
    )
    shortcode = _first(posts, "shortcode", FALLBACK_INSTAGRAM_SHORTCODE)
    await run.object_call(
        "instagram_media", c.instagram_media, InstagramMedia, shortcode
    )
    await run.list_call(
        "instagram_comments", c.instagram_comments, InstagramComment, shortcode, count=2
    )
    await run.list_call(
        "instagram_hashtag", c.instagram_hashtag, InstagramMedia, HASHTAG, count=2
    )


async def run_facebook(run: SmokeRun) -> None:
    c = run.client
    await run.list_call(
        "facebook_search", c.facebook_search, FacebookPost, "running", count=2
    )
    await run.object_call(
        "facebook_profile", c.facebook_profile, FacebookProfile, FACEBOOK_PAGE
    )
    posts = await run.list_call(
        "facebook_profile_posts",
        c.facebook_profile_posts,
        FacebookPost,
        FACEBOOK_PAGE,
        count=2,
    )
    post_id = _first(posts, "id", FALLBACK_FACEBOOK_POST_ID)
    await run.object_call(
        "facebook_post_by_id", c.facebook_post_by_id, FacebookPost, post_id
    )
    await run.list_call(
        "facebook_comments", c.facebook_comments, FacebookComment, post_id, count=2
    )
    await run.list_call(
        "facebook_hashtag", c.facebook_hashtag, FacebookPost, HASHTAG, count=2
    )


async def run_network_stats(run: SmokeRun) -> None:
    c = run.client
    await run.object_call("network_stats", c.network_stats, NetworkStatsResponse)

    def check_history(result: Any) -> str:
        if not isinstance(result, NetworkStatsHistoryResponse):
            raise TypeError(f"expected NetworkStatsHistoryResponse, got {type(result).__name__}")
        return f"{len(result.points)} points"

    await run.call("network_stats_history", c.network_stats_history, check_history)

    async def first_event() -> NetworkStatsEvent:
        async with aclosing(c.stream_network_stats()) as events:
            return await asyncio.wait_for(anext(events), STREAM_TIMEOUT_SECONDS)

    def check_event(event: Any) -> str:
        if not isinstance(event, NetworkStatsEvent):
            raise TypeError(f"expected NetworkStatsEvent, got {type(event).__name__}")
        return f"event id {event.id}"

    await run.call("stream_network_stats", first_event, check_event)


async def run_people(run: SmokeRun) -> None:
    """Opt-in (--with-people): start one paid People Search and cancel it."""
    c = run.client

    def check_task(task: Any) -> str:
        if not isinstance(task, PeopleTask):
            raise TypeError(f"expected PeopleTask, got {type(task).__name__}")
        return f"task {task.task_id} {task.status}"

    task = await run.call(
        "tiktok_creator_search",
        lambda: c.tiktok_creator_search(
            query="Creators who review AI search tools", count=5
        ),
        check_task,
    )
    if task is None:
        return

    async def cancel() -> Any:
        try:
            return await c.cancel_people_task(task.task_id)
        except PeopleTaskConflictError as exc:  # it already ended
            return exc.task or task

    await run.call("cancel_people_task", cancel, check_task)


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument(
        "--base-url",
        default=os.environ.get("DESEARCH_BASE_URL", "https://api.desearch.ai"),
        help="API base URL (default: $DESEARCH_BASE_URL or production)",
    )
    parser.add_argument(
        "--with-people",
        action="store_true",
        help="also start one paid People Search (count=5) and cancel it at once",
    )
    args = parser.parse_args()

    api_key = os.environ.get("DESEARCH_API_KEY", "").strip()
    if not api_key:
        print("DESEARCH_API_KEY is not set", file=sys.stderr)
        return 2

    async with Desearch(api_key=api_key, base_url=args.base_url) as client:
        run = SmokeRun(client)
        await run_search_api(run)
        await run_tiktok(run)
        await run_instagram(run)
        await run_facebook(run)
        await run_network_stats(run)
        if args.with_people:
            await run_people(run)

    print(f"{run.failures} failure(s)", flush=True)
    return 1 if run.failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
