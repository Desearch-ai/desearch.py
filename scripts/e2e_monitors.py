#!/usr/bin/env python3
"""Live smoke test for the Monitors methods (desearch-py 1.13.0).

Creates one monitor without running it, calls every free Monitors method on
it, and deletes it. With ``--with-run`` it also triggers one run, waits for
it and reads its items (billed: an X search of 5 posts plus Jev screening,
about $0.002-0.01). Prints one line per call: ``PASS name`` or
``FAIL name: error``. Exits 1 if any call fails, 2 if the API key is not set.

Usage::

    DESEARCH_API_KEY=... python scripts/e2e_monitors.py
    python scripts/e2e_monitors.py --base-url https://api-dev.desearch.ai \\
        --key-env DESEARCH_DEV_API_KEY --with-run

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
    Monitor,
    MonitorDeleted,
    MonitorEstimate,
    MonitorItemList,
    MonitorList,
    MonitorRun,
    MonitorRunList,
    MonitorRunWithItems,
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
        self, name: str, make_call: Callable[[], Awaitable[Any]], status: int
    ) -> None:
        try:
            await make_call()
        except DesearchAPIError as exc:
            if exc.status == status:
                self.report(name, detail=f"HTTP {status}")
            else:
                self.report(name, f"HTTP {exc.status}, expected {status}")
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
        lambda: client.create_monitor(
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
            lambda: client.delete_monitor(monitor_id),
            lambda result: (
                _expect(isinstance(result, MonitorDeleted) and result.deleted, "not deleted"),
                "deleted",
            )[-1],
        )
        await run.expect_status(
            "get_monitor after delete", lambda: client.get_monitor(monitor_id), 404
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
    args = parser.parse_args()

    _load_env_file()
    api_key = os.environ.get(args.key_env, "").strip()
    if not api_key:
        print(f"{args.key_env} is not set", file=sys.stderr)
        return 2

    async with Desearch(api_key=api_key, base_url=args.base_url) as client:
        run = SmokeRun(client)
        await run_monitors(run, args.with_run)

    print(f"{run.failures} failure(s) on {args.base_url}", flush=True)
    return 1 if run.failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
