#!/usr/bin/env python3
"""Live smoke test for the Monitors methods (desearch-py 1.13.0).

Creates one monitor without running it, calls every free Monitors method on
it, and deletes it. With ``--with-run`` it also triggers one run, waits for
it and reads its items (billed: an X search of 5 posts plus Jev screening,
about $0.002-0.01). With ``--with-accounts`` it also creates a free TikTok
monitor that watches accounts on every source (desearch-public-api#635) and
checks the names come back cleaned; with both flags it also runs that monitor
once (billed, about $0.03-0.06) and checks every item names the account it was
read from. With ``--with-social`` it checks the Instagram, Facebook and Meta
ads sources and Threads accounts (desearch-public-api#644) without running a
monitor: cleaned names, the 422 for Instagram or Facebook without accounts on
create and update, the estimate's breakdown, ``webhook.last_delivery`` and
the ``meta_ads`` items filter, plus one ``facebook_search(sort="recent",
count=2)`` call (billed, about $0.004). Every monitor the script creates is
deleted before it exits, also when a check fails. Prints one line per call:
``PASS name`` or ``FAIL name: error``. Exits 1 if any call fails, 2 if the API
key is not set.

Usage::

    DESEARCH_API_KEY=... python scripts/e2e_monitors.py
    python scripts/e2e_monitors.py --base-url https://api-dev.desearch.ai \\
        --key-env DESEARCH_DEV_API_KEY --with-run --with-accounts --with-social

The key is read from the environment variable named by ``--key-env``
(default ``DESEARCH_API_KEY``), or from ``~/.config/desearch/e2e.env``. The
webhook points at https://example.com, which does not answer POSTs with a
2xx, so the webhook test checks the response shape only.

The script imports the SDK from this working tree, not from site-packages.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from pathlib import Path
from typing import Any, Awaitable, Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from desearch_py import (  # noqa: E402
    Desearch,
    DesearchAPIError,
    FacebookPost,
    Monitor,
    MonitorDeleted,
    MonitorEstimate,
    MonitorItemList,
    MonitorList,
    MonitorRun,
    MonitorRunList,
    MonitorRunWithItems,
    MonitorSource,
    MonitorWebhookSecret,
    MonitorWebhookTest,
)

QUERY = "Bittensor subnet launches and updates"
WEBHOOK_URL = "https://example.com/desearch-e2e"


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
        # Monitors created and not deleted yet; cleanup() deletes what is left.
        self.created: set[str] = set()

    async def create_monitor(self, *args: Any, **kwargs: Any) -> Monitor:
        monitor = await self.client.create_monitor(*args, **kwargs)
        self.created.add(monitor.monitor_id)
        return monitor

    async def delete_monitor(self, monitor_id: str) -> MonitorDeleted:
        result = await self.client.delete_monitor(monitor_id)
        self.created.discard(monitor_id)
        return result

    async def cleanup(self) -> None:
        """Delete every monitor a check created and did not delete (the account holds 25)."""
        for monitor_id in sorted(self.created):
            await self.call(
                f"cleanup delete_monitor {monitor_id}",
                lambda: self.delete_monitor(monitor_id),
                lambda result: (_expect(result.deleted, "not deleted"), "deleted")[-1],
            )

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
        """Run one call. ``check`` returns a detail or raises."""
        try:
            result = await make_call()
            detail = check(result)
        except Exception as exc:  # noqa: BLE001 - report every failure and go on
            self.report(name, f"{type(exc).__name__}: {exc}")
            return None
        self.report(name, detail=detail)
        return result

    async def expect_status(
        self,
        name: str,
        make_call: Callable[[], Awaitable[Any]],
        status: int,
        detail: Optional[str] = None,
    ) -> None:
        """Expect ``make_call`` to fail with ``status`` (and ``detail`` in the body, if given)."""
        try:
            await make_call()
        except DesearchAPIError as exc:
            if exc.status != status:
                self.report(name, f"HTTP {exc.status}, expected {status}")
            elif detail is not None and detail not in (exc.body or ""):
                self.report(name, f"HTTP {status} without {detail!r}: {exc.body}")
            else:
                self.report(name, detail=f"HTTP {status}")
            return
        except Exception as exc:  # noqa: BLE001
            self.report(name, f"{type(exc).__name__}: {exc}")
            return
        self.report(name, f"no error, expected HTTP {status}")


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


async def run_monitors(run: SmokeRun, with_run: bool) -> None:
    client = run.client

    def check_estimate(result: MonitorEstimate) -> str:
        _expect(isinstance(result, MonitorEstimate), "not a MonitorEstimate")
        _expect(result.max_run_cost_usd > 0, "max_run_cost_usd is 0")
        _expect(result.runs_per_month == 30, f"runs_per_month {result.runs_per_month}")
        return f"max run ${result.max_run_cost_usd}, month ${result.max_monthly_cost_usd}"

    await run.call(
        "estimate_monitor",
        lambda: client.estimate_monitor(sources=["x", "web"], interval="1d"),
        check_estimate,
    )

    def check_created(monitor: Monitor) -> str:
        _expect(isinstance(monitor, Monitor), "not a Monitor")
        _expect(monitor.status == "active", f"status {monitor.status}")
        _expect(bool(monitor.webhook_secret), "no webhook_secret")
        _expect(monitor.webhook_secret.startswith("whsec_"), "secret is not whsec_")
        _expect(monitor.next_run_at is not None, "no next_run_at")
        _expect(monitor.options.get("x", {}).get("count") == 5, f"options {monitor.options}")
        return monitor.monitor_id

    monitor = await run.call(
        "create_monitor",
        lambda: run.create_monitor(
            QUERY,
            name="desearch-py e2e",
            criteria=["Announces a new subnet, release or partnership"],
            sources=["x"],
            interval="7d",
            options={"x": {"count": 5, "lang": "en"}},
            webhook={"url": WEBHOOK_URL},
            metadata={"source": "desearch-py-e2e"},
            run_now=False,
        ),
        check_created,
    )
    if monitor is None:
        return
    monitor_id = monitor.monitor_id
    try:
        await run.call(
            "get_monitor",
            lambda: client.get_monitor(monitor_id),
            lambda m: (
                _expect(m.monitor_id == monitor_id, "wrong monitor"),
                _expect(m.webhook_secret is None, "secret returned again"),
                m.interval,
            )[-1],
        )

        def check_list(page: MonitorList) -> str:
            ids = [m.monitor_id for m in page.monitors]
            _expect(monitor_id in ids, "new monitor not on the first page")
            return f"{len(ids)} monitors, next_cursor={page.next_cursor is not None}"

        await run.call(
            "list_monitors",
            lambda: client.list_monitors(status="active", limit=100),
            check_list,
        )
        first = await run.call(
            "list_monitors page 1",
            lambda: client.list_monitors(limit=1),
            lambda page: _expect(len(page.monitors) == 1, "limit 1") or "1 monitor",
        )
        if first is not None and first.next_cursor:
            await run.call(
                "list_monitors page 2",
                lambda: client.list_monitors(limit=1, cursor=first.next_cursor),
                lambda page: (
                    _expect(
                        page.monitors[0].monitor_id != first.monitors[0].monitor_id,
                        "page 2 repeats page 1",
                    ),
                    "next page differs",
                )[-1],
            )

        await run.call(
            "update_monitor",
            lambda: client.update_monitor(monitor_id, name="desearch-py e2e (renamed)", min_score=70),
            lambda m: (
                _expect(m.name == "desearch-py e2e (renamed)", f"name {m.name}"),
                _expect(m.min_score == 70, f"min_score {m.min_score}"),
                "renamed",
            )[-1],
        )
        await run.call(
            "pause_monitor",
            lambda: client.pause_monitor(monitor_id),
            lambda m: (
                _expect((m.status, m.paused_reason) == ("paused", "user"), f"{m.status} {m.paused_reason}"),
                "paused",
            )[-1],
        )
        await run.call(
            "resume_monitor",
            lambda: client.resume_monitor(monitor_id),
            lambda m: (_expect(m.status == "active", m.status), "active")[-1],
        )
        await run.call(
            "list_monitor_runs",
            lambda: client.list_monitor_runs(monitor_id, limit=5),
            lambda page: (
                _expect(isinstance(page, MonitorRunList), "not a MonitorRunList"),
                f"{len(page.runs)} runs",
            )[-1],
        )
        await run.call(
            "list_monitor_items",
            lambda: client.list_monitor_items(monitor_id, limit=5, source="x"),
            lambda page: (
                _expect(isinstance(page, MonitorItemList), "not a MonitorItemList"),
                f"{len(page.items)} items",
            )[-1],
        )
        await run.call(
            "test_monitor_webhook",
            lambda: client.test_monitor_webhook(monitor_id),
            lambda result: (
                _expect(isinstance(result, MonitorWebhookTest), "not a MonitorWebhookTest"),
                f"delivered={result.delivered} status={result.status_code} {result.duration_ms} ms",
            )[-1],
        )
        await run.call(
            "rotate_monitor_webhook_secret",
            lambda: client.rotate_monitor_webhook_secret(monitor_id),
            lambda result: (
                _expect(isinstance(result, MonitorWebhookSecret), "not a MonitorWebhookSecret"),
                _expect(result.webhook_secret != monitor.webhook_secret, "same secret"),
                "new secret",
            )[-1],
        )
        await run.call(
            "update_monitor remove_webhook",
            lambda: client.update_monitor(monitor_id, remove_webhook=True),
            lambda m: (_expect(m.webhook is None, "webhook kept"), "removed")[-1],
        )
        await run.expect_status(
            "test_monitor_webhook without webhook",
            lambda: client.test_monitor_webhook(monitor_id),
            400,
        )
        await run.expect_status(
            "get_monitor_run unknown",
            lambda: client.get_monitor_run(monitor_id, "00000000-0000-0000-0000-000000000000"),
            404,
        )

        if with_run:
            queued = await run.call(
                "trigger_monitor",
                lambda: client.trigger_monitor(monitor_id),
                lambda r: (
                    _expect(isinstance(r, MonitorRun), "not a MonitorRun"),
                    _expect(r.trigger == "manual", f"trigger {r.trigger}"),
                    r.status,
                )[-1],
            )
            if queued is not None:
                await run.expect_status(
                    "trigger_monitor while running",
                    lambda: client.trigger_monitor(monitor_id),
                    409,
                )
                ended = await run.call(
                    "wait_for_monitor_run",
                    lambda: client.wait_for_monitor_run(
                        monitor_id, queued.run_id, poll_interval=3, timeout=300
                    ),
                    lambda r: (
                        _expect(isinstance(r, MonitorRunWithItems), "not a MonitorRunWithItems"),
                        _expect(r.status == "completed", f"{r.status} {r.fail_reason}"),
                        _expect(r.cost_usd is not None, "not billed"),
                        f"{r.item_count} items, ${r.cost_usd}, screen={r.stats.get('screen')}",
                    )[-1],
                )
                if ended is not None:
                    await run.call(
                        "iter_monitor_items",
                        lambda: _collect(client.iter_monitor_items(monitor_id, page_size=2)),
                        lambda items: (
                            _expect(len(items) == ended.item_count, f"{len(items)} != {ended.item_count}"),
                            f"{len(items)} items",
                        )[-1],
                    )
    finally:
        await run.call(
            "delete_monitor",
            lambda: run.delete_monitor(monitor_id),
            lambda result: (
                _expect(isinstance(result, MonitorDeleted) and result.deleted, "not deleted"),
                "deleted",
            )[-1],
        )
        await run.expect_status(
            "get_monitor after delete", lambda: client.get_monitor(monitor_id), 404
        )


WATCHED = {
    "x": {"accounts": ["@OpenAI", "https://x.com/AnthropicAI"]},
    "reddit": {"subreddits": ["r/LocalLLaMA"]},
    "youtube": {"channels": ["https://www.youtube.com/@OpenAI"]},
    "tiktok": {"count": 10, "accounts": ["@openai"]},
}
CLEANED = {
    "x": ["OpenAI", "AnthropicAI"],
    "reddit": ["LocalLLaMA"],
    "youtube": ["@OpenAI"],
    "tiktok": ["openai"],
}
# X usernames are at most 15 characters; the API refuses longer ones with 422.
X_NAME_TOO_LONG = "a" * 16
assert all(len(name) <= 15 for name in CLEANED["x"])


TIKTOK_FIELDS = ("views", "likes", "comments", "shares", "duration_s", "thumbnail")


async def run_watched_accounts(run: SmokeRun, with_run: bool) -> None:
    client = run.client
    sources = ["x", "reddit", "youtube", "tiktok"]

    await run.call(
        "estimate_monitor watched accounts",
        lambda: client.estimate_monitor(sources=sources, options=WATCHED),
        lambda e: (
            _expect(e.max_run_cost_usd > 0, "max_run_cost_usd is 0"),
            _expect("tiktok" in e.breakdown, f"no tiktok in breakdown {e.breakdown}"),
            f"max run ${e.max_run_cost_usd} {e.breakdown}",
        )[-1],
    )
    await run.expect_status(
        "create_monitor bad account name",
        lambda: run.create_monitor(
            QUERY, sources=["x"], options={"x": {"accounts": ["not a name!"]}}, run_now=False
        ),
        422,
    )
    await run.expect_status(
        "create_monitor X username over 15 characters",
        lambda: run.create_monitor(
            QUERY, sources=["x"], options={"x": {"accounts": [X_NAME_TOO_LONG]}}, run_now=False
        ),
        422,
        "is not an X username",
    )

    def check(monitor: Monitor) -> str:
        _expect(monitor.sources == sources, f"sources {monitor.sources}")
        got = {
            "x": monitor.options["x"]["accounts"],
            "reddit": monitor.options["reddit"]["subreddits"],
            "youtube": monitor.options["youtube"]["channels"],
            "tiktok": monitor.options["tiktok"]["accounts"],
        }
        _expect(got == CLEANED, f"names {got}")
        return "names cleaned"

    monitor = await run.call(
        "create_monitor watched accounts",
        lambda: run.create_monitor(
            "Model and API launches",
            name="desearch-py e2e accounts",
            sources=sources,
            options=WATCHED,
            min_score=0,
            run_now=False,
        ),
        check,
    )
    if monitor is None:
        return
    try:
        if with_run:
            await _run_watched(run, monitor.monitor_id)
    finally:
        await run.call(
            "delete_monitor watched accounts",
            lambda: run.delete_monitor(monitor.monitor_id),
            lambda result: (_expect(result.deleted, "not deleted"), "deleted")[-1],
        )


async def _run_watched(run: SmokeRun, monitor_id: str) -> None:
    client = run.client
    queued = await run.call(
        "trigger_monitor watched accounts",
        lambda: client.trigger_monitor(monitor_id),
        lambda r: r.status,
    )
    if queued is None:
        return

    def check_run(r: MonitorRunWithItems) -> str:
        _expect(r.status == "completed", f"{r.status} {r.fail_reason}")
        sources = r.stats.get("sources") or {}
        for source in CLEANED:
            _expect(source in sources, f"no stats for {source}")
            _expect(not sources[source].get("error"), f"{source}: {sources[source]['error']}")
            _expect(not sources[source].get("accounts_failed"), f"{source}: {sources[source]}")
        return f"{r.item_count} items, ${r.cost_usd}"

    ended = await run.call(
        "wait_for_monitor_run watched accounts",
        lambda: client.wait_for_monitor_run(monitor_id, queued.run_id, poll_interval=5, timeout=480),
        check_run,
    )
    if ended is None:
        return

    def check_items(items: list) -> str:
        _expect(len(items) == ended.item_count, f"{len(items)} != {ended.item_count}")
        for item in items:
            account = item.data.get("account")
            _expect(account in CLEANED[item.source], f"{item.source} item account {account!r}")
            if item.source == "tiktok":
                missing = [field for field in TIKTOK_FIELDS if field not in item.data]
                _expect(not missing, f"TikTok item without {missing}")
        by_source = sorted({item.source for item in items})
        return f"{len(items)} items from {', '.join(by_source) or 'no source'}"

    await run.call(
        "iter_monitor_items watched accounts",
        lambda: _collect(client.iter_monitor_items(monitor_id, page_size=50)),
        check_items,
    )


# desearch-public-api#644. The Ad Library matches keywords, so a meta_ads
# query is a brand or product, not a sentence.
SOCIAL_QUERY = "ChatGPT"
SOCIAL_SOURCES = ["threads", "instagram", "facebook", "meta_ads"]
SOCIAL = {
    "threads": {"accounts": ["@zuck", "https://www.threads.com/@mosseri"]},
    "instagram": {"accounts": ["@openai", "https://www.instagram.com/nasa/"]},
    "facebook": {
        "pages": [
            "https://www.facebook.com/NASA",
            "https://www.facebook.com/profile.php?id=100064869009429",
            "https://www.facebook.com/pages/NASA-Earth/123456789012",
        ]
    },
    "meta_ads": {"count": 20},
}
SOCIAL_CLEANED = {
    "threads": {"accounts": ["zuck", "mosseri"]},
    "instagram": {"accounts": ["openai", "nasa"]},
    "facebook": {"pages": ["NASA", "100064869009429", "123456789012"]},
    "meta_ads": {"count": 20},
}
# Most one run can cost per watched account or ad (docs/monitors.md): a Threads
# profile is one request, an Instagram account 12 posts and a Facebook page 10
# posts at $0.00207 each, and Meta ads meta_ads.count records at $0.00207.
SOCIAL_UNIT_USD = {"threads": 0.00207, "instagram": 0.02484, "facebook": 0.0207, "meta_ads": 0.00207}
SOCIAL_UNITS = {"threads": 2, "instagram": 2, "facebook": 3, "meta_ads": 20}


def _check_breakdown(breakdown: dict, units: dict) -> str:
    for source, count in units.items():
        _expect(source in breakdown, f"no {source} in breakdown {breakdown}")
        want = round(SOCIAL_UNIT_USD[source] * count, 6)
        _expect(abs(breakdown[source] - want) < 1e-6, f"{source} ${breakdown[source]}, expected ${want}")
    return ", ".join(f"{source} ${breakdown[source]}" for source in units)


async def run_social_sources(run: SmokeRun) -> None:
    """Instagram, Facebook, Meta ads and Threads accounts, with no billed run."""
    client = run.client

    await run.call(
        "estimate_monitor social sources",
        lambda: client.estimate_monitor(sources=SOCIAL_SOURCES, options=SOCIAL),
        lambda e: _check_breakdown(e.breakdown, SOCIAL_UNITS),
    )
    # The estimate prices Instagram without accounts as one account instead of refusing it.
    await run.call(
        "estimate_monitor instagram without accounts",
        lambda: client.estimate_monitor(sources=["instagram"]),
        lambda e: _check_breakdown(e.breakdown, {"instagram": 1}),
    )
    await run.expect_status(
        "create_monitor instagram without accounts",
        lambda: run.create_monitor(SOCIAL_QUERY, sources=["instagram"], run_now=False),
        422,
        "options.instagram.accounts",
    )
    await run.expect_status(
        "create_monitor facebook without pages",
        lambda: run.create_monitor(
            SOCIAL_QUERY,
            sources=["meta_ads", "facebook"],
            options={"facebook": {"pages": []}},
            run_now=False,
        ),
        422,
        "options.facebook.pages",
    )

    def check_created(monitor: Monitor) -> str:
        _expect(monitor.sources == SOCIAL_SOURCES, f"sources {monitor.sources}")
        got = {source: monitor.options.get(source) for source in SOCIAL_SOURCES}
        _expect(got == SOCIAL_CLEANED, f"options {got}")
        _expect(bool(monitor.webhook_secret), "no webhook_secret")
        return "names cleaned"

    monitor = await run.call(
        "create_monitor social sources",
        lambda: run.create_monitor(
            SOCIAL_QUERY,
            name="desearch-py e2e social",
            sources=SOCIAL_SOURCES,
            options=SOCIAL,
            webhook={"url": WEBHOOK_URL},
            run_now=False,
        ),
        check_created,
    )
    if monitor is None:
        return
    monitor_id = monitor.monitor_id

    def check_no_delivery(m: Monitor) -> str:
        _expect(m.webhook is not None, "no webhook")
        _expect("last_delivery" in m.webhook.model_fields_set, "no last_delivery in webhook")
        _expect(m.webhook.last_delivery is None, f"last_delivery {m.webhook.last_delivery}")
        return "last_delivery null"

    try:
        await run.call("get_monitor last_delivery", lambda: client.get_monitor(monitor_id), check_no_delivery)
        # A test event is not a delivery, so last_delivery stays null.
        await run.call(
            "test_monitor_webhook social",
            lambda: client.test_monitor_webhook(monitor_id),
            lambda result: f"delivered={result.delivered} status={result.status_code}",
        )
        await run.call(
            "get_monitor last_delivery after webhook test",
            lambda: client.get_monitor(monitor_id),
            check_no_delivery,
        )
        # PATCH checks the monitor as patched. Options replace the current ones as a whole.
        await run.expect_status(
            "update_monitor options without instagram accounts",
            lambda: client.update_monitor(
                monitor_id, options={"facebook": SOCIAL["facebook"], "meta_ads": {"count": 10}}
            ),
            422,
            "options.instagram.accounts",
        )
        await run.expect_status(
            "update_monitor options without facebook pages",
            lambda: client.update_monitor(monitor_id, options={"instagram": SOCIAL["instagram"]}),
            422,
            "options.facebook.pages",
        )
        await run.call(
            "update_monitor drop instagram and facebook",
            lambda: client.update_monitor(
                monitor_id,
                sources=["threads", "meta_ads"],
                options={"threads": SOCIAL["threads"], "meta_ads": {"count": 30}},
            ),
            lambda m: (
                _expect(m.sources == ["threads", "meta_ads"], f"sources {m.sources}"),
                _expect(m.options.get("meta_ads") == {"count": 30}, f"options {m.options}"),
                "threads and meta_ads",
            )[-1],
        )
        # Sources from the patch, options from the monitor, which has no instagram now.
        await run.expect_status(
            "update_monitor add instagram without accounts",
            lambda: client.update_monitor(monitor_id, sources=["threads", "meta_ads", "instagram"]),
            422,
            "options.instagram.accounts",
        )
        for source in (MonitorSource.META_ADS, MonitorSource.INSTAGRAM, MonitorSource.FACEBOOK):
            await run.call(
                f"list_monitor_items source={source.value}",
                lambda: client.list_monitor_items(monitor_id, limit=5, source=source),
                lambda page: (
                    _expect(isinstance(page, MonitorItemList), "not a MonitorItemList"),
                    f"{len(page.items)} items",
                )[-1],
            )
    finally:
        await run.call(
            "delete_monitor social sources",
            lambda: run.delete_monitor(monitor_id),
            lambda result: (_expect(result.deleted, "not deleted"), "deleted")[-1],
        )

    def check_ads(ads: Any) -> str:
        _expect(isinstance(ads, list), f"not a list: {type(ads).__name__}")
        _expect(0 < len(ads) <= 2, f"{len(ads)} ads")
        _expect(all(isinstance(ad, FacebookPost) for ad in ads), "not FacebookPost")
        return f"{len(ads)} ads, first {ads[0].headline or ads[0].text or ads[0].id!r}"

    await run.call(
        "facebook_search sort=recent",
        lambda: client.facebook_search(SOCIAL_QUERY, count=2, sort="recent"),
        check_ads,
    )


async def _collect(iterator: Any) -> list:
    return [item async for item in iterator]


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
    parser.add_argument(
        "--with-run",
        action="store_true",
        help="also trigger one billed run and read its items",
    )
    parser.add_argument(
        "--with-accounts",
        action="store_true",
        help="also check TikTok and watched accounts (needs desearch-public-api#635)",
    )
    parser.add_argument(
        "--with-social",
        action="store_true",
        help=(
            "also check Instagram, Facebook, Meta ads and Threads accounts without a run "
            "(needs desearch-public-api#644; one billed facebook_search of 2 ads)"
        ),
    )
    args = parser.parse_args()

    _load_env_file()
    api_key = os.environ.get(args.key_env, "").strip()
    if not api_key:
        print(f"{args.key_env} is not set", file=sys.stderr)
        return 2

    async with Desearch(api_key=api_key, base_url=args.base_url) as client:
        run = SmokeRun(client)
        try:
            await run_monitors(run, args.with_run)
            if args.with_accounts:
                await run_watched_accounts(run, args.with_run)
            if args.with_social:
                await run_social_sources(run)
        finally:
            await run.cleanup()

    print(f"{run.failures} failure(s) on {args.base_url}", flush=True)
    return 1 if run.failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
