import hashlib
import hmac
import json
import time
import unittest

from aiohttp import web

from desearch_py import (
    MONITOR_RUN_ENDED_STATUSES,
    SIGNATURE_HEADER,
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    Monitor,
    MonitorDeleted,
    MonitorEstimate,
    MonitorEvent,
    MonitorInterval,
    MonitorItem,
    MonitorItemList,
    MonitorList,
    MonitorRun,
    MonitorRunList,
    MonitorRunStatus,
    MonitorRunTimeoutError,
    MonitorRunWithItems,
    MonitorSource,
    MonitorStatus,
    MonitorOptions,
    MonitorWebhookDelivery,
    MonitorWebhookEvent,
    MonitorWebhookSecret,
    MonitorWebhookTest,
    verify_webhook_signature,
)

MONITOR_ID = "6f1d0c9e-0d55-4b8e-9a3c-3c4d9b8e2a10"
RUN_ID = "0c6a3a52-9f0e-4c41-8f55-2f1c2b7d8e11"
QUERY = "Bittensor subnet launches and updates"
BASE = f"https://example.test/desearch/monitors/{MONITOR_ID}"


class FakeResponse:
    def __init__(
        self, *, json_data=None, text_data="", headers=None, status=None, reason=""
    ):
        self._json_data = json_data
        self._text_data = text_data
        self.headers = headers or {}
        if status is not None:
            self.status = status
            self.reason = reason

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def json(self):
        return self._json_data

    async def text(self):
        if self._text_data == "" and self._json_data is not None:
            return json.dumps(self._json_data)
        return self._text_data


class FakeSession:
    closed = False

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        return self._responses.pop(0)

    async def close(self):
        self.closed = True


# The objects of docs/monitors.md in desearch-public-api.
def _monitor(**extra):
    monitor = {
        "monitor_id": MONITOR_ID,
        "name": "Bittensor subnet news",
        "query": QUERY,
        "criteria": ["Announces a new subnet, release or partnership"],
        "sources": ["web", "x", "reddit", "youtube"],
        "interval": "1d",
        "options": {"x": {"count": 20, "lang": "en", "min_likes": 0}, "web": {"count": 10}},
        "min_score": 60,
        "summary": False,
        "status": "active",
        "paused_reason": None,
        "webhook": {
            "url": "https://example.com/hooks/desearch",
            "events": ["monitor.items.found", "monitor.run.failed"],
            "consecutive_failures": 0,
            "last_delivery": {
                "event": "monitor.items.found",
                "status": "delivered",
                "attempts": 1,
                "status_code": 200,
                "error": None,
                "created_at": "2026-11-03T09:00:41Z",
                "next_attempt_at": None,
                "delivered_at": "2026-11-03T09:00:42Z",
            },
        },
        "metadata": {"team": "growth"},
        "max_run_cost_usd": 0.0098,
        "next_run_at": "2026-11-04T09:00:00Z",
        "last_run": {
            "run_id": RUN_ID,
            "status": "completed",
            "item_count": 3,
            "cost_usd": 0.0041,
            "finished_at": "2026-11-03T09:00:41Z",
        },
        "stats": {"runs": 3, "items": 12, "spent_usd": 0.0213},
        "created_at": "2026-11-03T09:00:00Z",
        "updated_at": "2026-11-03T09:00:41Z",
    }
    monitor.update(extra)
    return monitor


def _run(status="completed", **extra):
    run = {
        "run_id": RUN_ID,
        "monitor_id": MONITOR_ID,
        "trigger": "schedule",
        "status": status,
        "fail_reason": None,
        "window_start": "2026-11-02T09:00:00Z",
        "window_end": "2026-11-03T09:00:00Z",
        "item_count": 3,
        "stats": {
            "sources": {
                "x": {"fetched": 20, "in_window": 18, "new": 7, "passed": 2, "error": None},
                "web": {"fetched": 10, "in_window": 10, "new": 6, "passed": 1, "error": None},
            },
            "screened": 13,
            "passed": 3,
            "screen": "ai",
        },
        "summary": None,
        "reserved_usd": 0.0098,
        "cost_usd": 0.0041,
        "created_at": "2026-11-03T09:00:00Z",
        "started_at": "2026-11-03T09:00:02Z",
        "finished_at": "2026-11-03T09:00:41Z",
    }
    run.update(extra)
    return run


def _item(item_id="1842", **extra):
    item = {
        "item_id": item_id,
        "run_id": RUN_ID,
        "source": "x",
        "url": "https://x.com/opentensor/status/2117",
        "title": None,
        "text": "Subnet 64 is live on mainnet",
        "author": {"name": "Opentensor", "handle": "opentensor", "url": "https://x.com/opentensor"},
        "published_at": "2026-11-03T08:12:00Z",
        "score": 91,
        "signals": {"relevant": 0.91, "new_info": 0.84},
        "found_at": "2026-11-03T09:00:41Z",
        "data": {"likes": 120, "reposts": 14, "replies": 9, "views": 5400},
    }
    item.update(extra)
    return item


class _ClientTestCase(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    def request(self, client, index=0):
        return client.client.requests[index]


class MonitorCrudTests(_ClientTestCase):
    async def test_create_sends_only_the_query_by_default(self):
        client = self.make_client(FakeResponse(json_data=_monitor(webhook=None), status=201))
        monitor = await client.create_monitor(QUERY)
        self.assertIsInstance(monitor, Monitor)
        self.assertEqual(monitor.monitor_id, MONITOR_ID)
        self.assertIsNone(monitor.webhook_secret)
        self.assertEqual(monitor.last_run.item_count, 3)
        self.assertEqual(monitor.stats.spent_usd, 0.0213)
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("POST", "https://example.test/desearch/monitors"))
        self.assertEqual(kwargs["json"], {"query": QUERY})

    async def test_create_sends_every_given_field_with_enum_values(self):
        body = _monitor(webhook_secret="whsec_abc")
        client = self.make_client(FakeResponse(json_data=body, status=201))
        monitor = await client.create_monitor(
            QUERY,
            name="Bittensor subnet news",
            criteria=["Announces a new subnet"],
            sources=[MonitorSource.WEB, "x", MonitorSource.REDDIT],
            interval=MonitorInterval.SIX_HOURS,
            options={"web": {"count": 15}, "x": {"count": 50, "lang": "en", "min_likes": 5}},
            min_score=70,
            summary=True,
            webhook={
                "url": "https://example.com/hooks/desearch",
                "events": [MonitorEvent.ITEMS_FOUND, "monitor.run.completed"],
            },
            metadata={"team": "growth"},
            run_now=False,
        )
        self.assertEqual(monitor.webhook_secret, "whsec_abc")
        self.assertEqual(monitor.webhook.events, ["monitor.items.found", "monitor.run.failed"])
        self.assertEqual(
            self.request(client)[2]["json"],
            {
                "query": QUERY,
                "name": "Bittensor subnet news",
                "criteria": ["Announces a new subnet"],
                "sources": ["web", "x", "reddit"],
                "interval": "6h",
                "options": {"web": {"count": 15}, "x": {"count": 50, "lang": "en", "min_likes": 5}},
                "min_score": 70,
                "summary": True,
                "webhook": {
                    "url": "https://example.com/hooks/desearch",
                    "events": ["monitor.items.found", "monitor.run.completed"],
                },
                "metadata": {"team": "growth"},
                "run_now": False,
            },
        )

    async def test_create_errors_raise_desearch_api_error(self):
        for status, detail in (
            (402, "Your balance can't cover one run of this monitor."),
            (409, "Too many monitors: you already have 25."),
        ):
            with self.subTest(status=status):
                client = self.make_client(
                    FakeResponse(json_data={"detail": detail}, status=status, reason="Error")
                )
                with self.assertRaises(DesearchAPIError) as caught:
                    await client.create_monitor(QUERY)
                self.assertEqual(caught.exception.status, status)
                self.assertIn(detail, caught.exception.body)

    async def test_create_sends_tiktok_and_watched_accounts(self):
        options = {
            "x": {"accounts": ["@OpenAI", "https://x.com/AnthropicAI"], "min_likes": 10},
            "reddit": {"subreddits": ["r/LocalLLaMA"]},
            "youtube": {"channels": ["@OpenAI", "UCXZCJLdBC09xxGZ6gcdrc6A"]},
            "tiktok": {"count": 20, "accounts": ["@openai"]},
        }
        cleaned = {
            "x": {"count": 20, "lang": None, "min_likes": 10, "accounts": ["OpenAI", "AnthropicAI"]},
            "reddit": {"subreddits": ["LocalLLaMA"]},
            "youtube": {"channels": ["@OpenAI", "UCXZCJLdBC09xxGZ6gcdrc6A"]},
            "tiktok": {"count": 20, "accounts": ["openai"]},
        }
        body = _monitor(sources=["x", "reddit", "youtube", "tiktok"], options=cleaned, min_score=0)
        client = self.make_client(FakeResponse(json_data=body, status=201))
        monitor = await client.create_monitor(
            QUERY,
            sources=[MonitorSource.X, "reddit", "youtube", MonitorSource.TIKTOK],
            options=options,
            min_score=0,
        )
        self.assertEqual(monitor.sources[-1], "tiktok")
        self.assertEqual(monitor.options["x"]["accounts"], ["OpenAI", "AnthropicAI"])
        self.assertEqual(monitor.options["tiktok"], {"count": 20, "accounts": ["openai"]})
        self.assertEqual(
            self.request(client)[2]["json"],
            {
                "query": QUERY,
                "sources": ["x", "reddit", "youtube", "tiktok"],
                "options": options,
                "min_score": 0,
            },
        )

    async def test_create_sends_instagram_facebook_meta_ads_and_threads_accounts(self):
        options = {
            "threads": {"accounts": ["@zuck", "https://www.threads.com/@mosseri"]},
            "instagram": {"accounts": ["@openai", "https://www.instagram.com/nasa/"]},
            "facebook": {
                "pages": [
                    "https://www.facebook.com/NASA",
                    "https://www.facebook.com/profile.php?id=100064869009429",
                ]
            },
            "meta_ads": {"count": 20},
        }
        cleaned = {
            "threads": {"accounts": ["zuck", "mosseri"]},
            "instagram": {"accounts": ["openai", "nasa"]},
            "facebook": {"pages": ["NASA", "100064869009429"]},
            "meta_ads": {"count": 20},
        }
        sources = ["threads", "instagram", "facebook", "meta_ads"]
        body = _monitor(query="ChatGPT", sources=sources, options=cleaned, min_score=0)
        client = self.make_client(FakeResponse(json_data=body, status=201))
        monitor = await client.create_monitor(
            "ChatGPT",
            sources=[
                MonitorSource.THREADS,
                MonitorSource.INSTAGRAM,
                MonitorSource.FACEBOOK,
                MonitorSource.META_ADS,
            ],
            options=options,
            min_score=0,
            run_now=False,
        )
        self.assertEqual(monitor.sources, sources)
        self.assertEqual(monitor.options["facebook"]["pages"], ["NASA", "100064869009429"])
        self.assertEqual(monitor.options["meta_ads"], {"count": 20})
        self.assertEqual(
            self.request(client)[2]["json"],
            {
                "query": "ChatGPT",
                "sources": sources,
                "options": options,
                "min_score": 0,
                "run_now": False,
            },
        )

    async def test_create_sends_tiktok_and_instagram_hashtags(self):
        # Hashtags in any script, with or without #, or as a tag URL; Instagram
        # may watch hashtags without accounts.
        options = {
            "tiktok": {"accounts": ["@openai"], "hashtags": ["#ავერსი", "https://www.tiktok.com/tag/aversi"]},
            "instagram": {"hashtags": ["https://www.instagram.com/explore/tags/aversi/", "ავერსი"]},
        }
        cleaned = {
            "tiktok": {"count": 10, "accounts": ["openai"], "hashtags": ["ავერსი", "aversi"]},
            "instagram": {"hashtags": ["aversi", "ავერსი"]},
        }
        body = _monitor(sources=["tiktok", "instagram"], options=cleaned, min_score=0)
        client = self.make_client(FakeResponse(json_data=body, status=201))
        monitor = await client.create_monitor(
            QUERY,
            sources=[MonitorSource.TIKTOK, MonitorSource.INSTAGRAM],
            options=MonitorOptions.model_validate(options),
            min_score=0,
        )
        self.assertEqual(monitor.options["tiktok"]["hashtags"], ["ავერსი", "aversi"])
        self.assertEqual(monitor.options["instagram"], {"hashtags": ["aversi", "ავერსი"]})
        self.assertEqual(
            self.request(client)[2]["json"],
            {"query": QUERY, "sources": ["tiktok", "instagram"], "options": options, "min_score": 0},
        )

    def test_typed_options_carry_every_source(self):
        options = MonitorOptions.model_validate(
            {
                "x": {"accounts": ["OpenAI"]},
                "reddit": {"subreddits": ["LocalLLaMA"]},
                "youtube": {"channels": ["@OpenAI"]},
                "tiktok": {"count": 30, "accounts": ["openai"], "hashtags": ["aversi"]},
                "threads": {"accounts": ["zuck"]},
                "instagram": {"accounts": ["openai"], "hashtags": ["ავერსი"]},
                "facebook": {"pages": ["NASA", "100064869009429"]},
                "meta_ads": {"count": 10},
            }
        )
        self.assertEqual(options.x.accounts, ["OpenAI"])
        self.assertEqual(options.reddit.subreddits, ["LocalLLaMA"])
        self.assertEqual(options.youtube.channels, ["@OpenAI"])
        self.assertEqual((options.tiktok.count, options.tiktok.accounts), (30, ["openai"]))
        self.assertEqual(options.tiktok.hashtags, ["aversi"])
        self.assertEqual(options.threads.accounts, ["zuck"])
        self.assertEqual((options.instagram.accounts, options.instagram.hashtags), (["openai"], ["ავერსი"]))
        self.assertEqual(options.facebook.pages, ["NASA", "100064869009429"])
        self.assertEqual(options.meta_ads.count, 10)
        self.assertEqual(
            options.model_dump(exclude_none=True),
            {
                "x": {"accounts": ["OpenAI"]},
                "reddit": {"subreddits": ["LocalLLaMA"]},
                "youtube": {"channels": ["@OpenAI"]},
                "threads": {"accounts": ["zuck"]},
                "tiktok": {"count": 30, "accounts": ["openai"], "hashtags": ["aversi"]},
                "instagram": {"accounts": ["openai"], "hashtags": ["ავერსი"]},
                "facebook": {"pages": ["NASA", "100064869009429"]},
                "meta_ads": {"count": 10},
            },
        )
        # An empty source entry stays empty, as before.
        self.assertEqual(
            MonitorOptions.model_validate({"threads": {}, "meta_ads": {}}).model_dump(exclude_none=True),
            {"threads": {}, "meta_ads": {}},
        )

    async def test_instagram_or_facebook_without_accounts_is_the_api_422(self):
        # The SDK leaves this check to the API: create answers with a
        # validation list, update with a plain detail.
        create_body = {
            "detail": [
                {
                    "loc": ["body"],
                    "msg": "Value error, Instagram watches accounts or hashtags: add at least one in options.instagram.accounts or options.instagram.hashtags",
                    "type": "value_error",
                }
            ]
        }
        update_body = {"detail": "Facebook watches pages: add at least one in options.facebook.pages"}
        client = self.make_client(
            FakeResponse(json_data=create_body, status=422, reason="Unprocessable Entity"),
            FakeResponse(json_data=update_body, status=422, reason="Unprocessable Entity"),
        )
        with self.assertRaises(DesearchAPIError) as created:
            await client.create_monitor(QUERY, sources=[MonitorSource.INSTAGRAM], run_now=False)
        self.assertEqual(created.exception.status, 422)
        self.assertIn("options.instagram.accounts or options.instagram.hashtags", created.exception.body)
        with self.assertRaises(DesearchAPIError) as updated:
            await client.update_monitor(MONITOR_ID, options={"instagram": {"accounts": ["openai"]}})
        self.assertEqual(updated.exception.status, 422)
        self.assertIn("options.facebook.pages", updated.exception.body)
        self.assertEqual(
            self.request(client, 0)[2]["json"],
            {"query": QUERY, "sources": ["instagram"], "run_now": False},
        )
        self.assertEqual(
            self.request(client, 1)[2]["json"], {"options": {"instagram": {"accounts": ["openai"]}}}
        )

    async def test_bad_account_names_are_the_api_422(self):
        body = {
            "detail": [
                {
                    "loc": ["body", "options", "x", "accounts"],
                    "msg": "Value error, 'not a name!' is not an X username",
                    "type": "value_error",
                }
            ]
        }
        client = self.make_client(FakeResponse(json_data=body, status=422, reason="Unprocessable Entity"))
        with self.assertRaises(DesearchAPIError) as caught:
            await client.create_monitor(QUERY, options={"x": {"accounts": ["not a name!"]}})
        self.assertEqual(caught.exception.status, 422)
        self.assertIn("is not an X username", caught.exception.body)

    async def test_estimate_posts_its_settings(self):
        estimate = {
            "max_run_cost_usd": 0.0098,
            "runs_per_month": 30,
            "max_monthly_cost_usd": 0.294,
            "breakdown": {"x": 0.006, "web": 0.0025, "screen": 0.0013},
        }
        client = self.make_client(FakeResponse(json_data=estimate))
        result = await client.estimate_monitor(
            sources=["x", MonitorSource.WEB], summary=False, interval="1d"
        )
        self.assertIsInstance(result, MonitorEstimate)
        self.assertEqual(result.runs_per_month, 30)
        self.assertEqual(result.breakdown["x"], 0.006)
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("POST", "https://example.test/desearch/monitors/estimate"))
        self.assertEqual(kwargs["json"], {"sources": ["x", "web"], "summary": False, "interval": "1d"})

    async def test_estimate_breaks_down_the_new_sources(self):
        # docs/monitors.md prices: a Threads profile is one request, an
        # Instagram account 12 posts, a Facebook page 10 posts, Meta ads
        # meta_ads.count records.
        estimate = {
            "max_run_cost_usd": 0.14,
            "runs_per_month": 30,
            "max_monthly_cost_usd": 4.2,
            "breakdown": {
                "threads": 0.00207,
                "instagram": 0.04968,
                "facebook": 0.0207,
                "meta_ads": 0.0621,
                "screening": 0.00505,
            },
        }
        options = {
            "threads": {"accounts": ["zuck"]},
            "instagram": {"accounts": ["openai", "nasa"]},
            "facebook": {"pages": ["NASA"]},
            "meta_ads": {"count": 30},
        }
        client = self.make_client(FakeResponse(json_data=estimate))
        result = await client.estimate_monitor(
            sources=[MonitorSource.THREADS, "instagram", MonitorSource.FACEBOOK, MonitorSource.META_ADS],
            options=options,
        )
        self.assertEqual(result.breakdown["instagram"], 0.04968)
        self.assertEqual(result.breakdown["meta_ads"], 0.0621)
        self.assertEqual(
            self.request(client)[2]["json"],
            {"sources": ["threads", "instagram", "facebook", "meta_ads"], "options": options},
        )

    async def test_list_sends_joined_statuses_limit_and_cursor(self):
        page = {"monitors": [_monitor()], "next_cursor": "abc"}
        client = self.make_client(FakeResponse(json_data=page))
        result = await client.list_monitors(
            status=[MonitorStatus.ACTIVE, "paused"], limit=5, cursor="xyz"
        )
        self.assertIsInstance(result, MonitorList)
        self.assertEqual(result.next_cursor, "abc")
        self.assertEqual(result.monitors[0].monitor_id, MONITOR_ID)
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("GET", "https://example.test/desearch/monitors"))
        self.assertEqual(kwargs["params"], {"status": "active,paused", "limit": 5, "cursor": "xyz"})

    async def test_list_takes_no_arguments(self):
        client = self.make_client(FakeResponse(json_data={"monitors": [], "next_cursor": None}))
        result = await client.list_monitors()
        self.assertEqual(result.monitors, [])
        self.assertIsNone(result.next_cursor)
        self.assertEqual(self.request(client)[2]["params"], {})

    async def test_webhook_last_delivery_is_typed(self):
        pending = {
            "event": "monitor.items.found",
            "status": "pending",
            "attempts": 2,
            "status_code": 503,
            "error": "HTTP 503",
            "created_at": "2026-11-03T09:00:41Z",
            "next_attempt_at": "2026-11-03T09:06:41Z",
            "delivered_at": None,
        }
        fresh = {"url": "https://example.com/hooks/desearch", "events": ["monitor.items.found"], "consecutive_failures": 0, "last_delivery": None}
        older_api = {"url": "https://example.com/hooks/desearch", "events": ["monitor.items.found"]}
        webhook = dict(fresh, last_delivery=pending)
        client = self.make_client(
            FakeResponse(json_data=_monitor()),
            FakeResponse(json_data=_monitor(webhook=webhook)),
            FakeResponse(json_data=_monitor(webhook=fresh)),
            FakeResponse(json_data=_monitor(webhook=older_api)),
        )
        delivered = (await client.get_monitor(MONITOR_ID)).webhook.last_delivery
        self.assertIsInstance(delivered, MonitorWebhookDelivery)
        self.assertEqual(
            (delivered.event, delivered.status, delivered.attempts, delivered.status_code),
            ("monitor.items.found", "delivered", 1, 200),
        )
        self.assertEqual(delivered.delivered_at, "2026-11-03T09:00:42Z")
        retrying = (await client.get_monitor(MONITOR_ID)).webhook.last_delivery
        self.assertEqual((retrying.status, retrying.status_code, retrying.error), ("pending", 503, "HTTP 503"))
        self.assertEqual(retrying.next_attempt_at, "2026-11-03T09:06:41Z")
        self.assertIsNone(retrying.delivered_at)
        new_webhook = (await client.get_monitor(MONITOR_ID)).webhook
        self.assertIsNone(new_webhook.last_delivery)
        self.assertIn("last_delivery", new_webhook.model_fields_set)
        self.assertIsNone((await client.get_monitor(MONITOR_ID)).webhook.last_delivery)

    async def test_get_quotes_the_monitor_id(self):
        client = self.make_client(FakeResponse(json_data=_monitor()))
        await client.get_monitor("a/b c")
        self.assertEqual(
            self.request(client)[0:2],
            ("GET", "https://example.test/desearch/monitors/a%2Fb%20c"),
        )

    async def test_unknown_monitor_is_a_404(self):
        client = self.make_client(
            FakeResponse(json_data={"detail": "Monitor not found"}, status=404, reason="Not Found")
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.get_monitor(MONITOR_ID)
        self.assertEqual(caught.exception.status, 404)

    async def test_update_sends_only_the_given_fields(self):
        client = self.make_client(FakeResponse(json_data=_monitor(name="Renamed", interval="6h")))
        monitor = await client.update_monitor(
            MONITOR_ID, name="Renamed", interval=MonitorInterval.SIX_HOURS, min_score=0
        )
        self.assertEqual(monitor.name, "Renamed")
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("PATCH", BASE))
        self.assertEqual(kwargs["json"], {"name": "Renamed", "interval": "6h", "min_score": 0})

    async def test_update_can_set_or_remove_the_webhook(self):
        client = self.make_client(
            FakeResponse(json_data=_monitor(webhook_secret="whsec_new")),
            FakeResponse(json_data=_monitor(webhook=None)),
        )
        changed = await client.update_monitor(
            MONITOR_ID, webhook={"url": "https://example.com/new"}
        )
        self.assertEqual(changed.webhook_secret, "whsec_new")
        removed = await client.update_monitor(MONITOR_ID, remove_webhook=True)
        self.assertIsNone(removed.webhook)
        self.assertEqual(self.request(client, 0)[2]["json"], {"webhook": {"url": "https://example.com/new"}})
        self.assertEqual(self.request(client, 1)[2]["json"], {"webhook": None})

    async def test_update_refuses_a_webhook_and_its_removal_together(self):
        client = self.make_client()
        with self.assertRaises(ValueError):
            await client.update_monitor(
                MONITOR_ID, webhook={"url": "https://example.com/x"}, remove_webhook=True
            )
        self.assertEqual(client.client.requests, [])

    async def test_pause_and_resume_patch_the_status(self):
        client = self.make_client(
            FakeResponse(json_data=_monitor(status="paused", paused_reason="user")),
            FakeResponse(json_data=_monitor()),
        )
        paused = await client.pause_monitor(MONITOR_ID)
        self.assertEqual((paused.status, paused.paused_reason), ("paused", "user"))
        resumed = await client.resume_monitor(MONITOR_ID)
        self.assertEqual(resumed.status, "active")
        self.assertEqual(self.request(client, 0)[0:2], ("PATCH", BASE))
        self.assertEqual(self.request(client, 0)[2]["json"], {"status": "paused"})
        self.assertEqual(self.request(client, 1)[2]["json"], {"status": "active"})

    async def test_delete_returns_the_deleted_id(self):
        client = self.make_client(FakeResponse(json_data={"monitor_id": MONITOR_ID, "deleted": True}))
        result = await client.delete_monitor(MONITOR_ID)
        self.assertIsInstance(result, MonitorDeleted)
        self.assertTrue(result.deleted)
        self.assertEqual(self.request(client)[0:2], ("DELETE", BASE))

    async def test_include_metadata_wraps_the_result(self):
        client = self.make_client(
            FakeResponse(json_data=_monitor(), headers={"X-Desearch-Service": "monitors"})
        )
        result = await client.get_monitor(MONITOR_ID, include_metadata=True)
        self.assertIsInstance(result, DesearchResponse)
        self.assertIsInstance(result.data, Monitor)
        self.assertEqual(result.metadata.service, "monitors")

    def test_models_keep_fields_a_newer_api_adds(self):
        monitor = Monitor.model_validate(_monitor(new_field="kept"))
        self.assertEqual(monitor.model_extra["new_field"], "kept")
        item = MonitorItem.model_validate(_item(rank=1))
        self.assertEqual(item.model_extra["rank"], 1)

    def test_enums_match_the_api_values(self):
        self.assertEqual(
            [s.value for s in MonitorSource],
            ["web", "x", "reddit", "youtube", "threads", "tiktok", "instagram", "facebook", "meta_ads"],
        )
        self.assertEqual([i.value for i in MonitorInterval], ["1h", "3h", "6h", "12h", "1d", "7d"])
        self.assertEqual(
            [e.value for e in MonitorEvent],
            ["monitor.items.found", "monitor.run.completed", "monitor.run.failed"],
        )
        self.assertEqual([s.value for s in MonitorStatus], ["active", "paused"])
        self.assertEqual(
            [s.value for s in MonitorRunStatus],
            ["queued", "running", "completed", "failed", "cancelled"],
        )
        self.assertEqual(MONITOR_RUN_ENDED_STATUSES, {"completed", "failed", "cancelled"})


class MonitorRunTests(_ClientTestCase):
    async def test_trigger_posts_and_returns_the_queued_run(self):
        queued = _run("queued", trigger="manual", cost_usd=None, started_at=None, finished_at=None)
        client = self.make_client(FakeResponse(json_data=queued, status=202))
        run = await client.trigger_monitor(MONITOR_ID)
        self.assertIsInstance(run, MonitorRun)
        self.assertEqual((run.status, run.trigger), ("queued", "manual"))
        self.assertIsNone(run.cost_usd)
        self.assertFalse(run.is_finished)
        self.assertEqual(self.request(client)[0:2], ("POST", f"{BASE}/trigger"))

    async def test_trigger_while_running_is_a_409(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "This monitor is already running."},
                status=409,
                reason="Conflict",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.trigger_monitor(MONITOR_ID)
        self.assertEqual(caught.exception.status, 409)

    async def test_list_runs_sends_limit_and_cursor(self):
        page = {"runs": [_run()], "next_cursor": "c2"}
        client = self.make_client(FakeResponse(json_data=page))
        result = await client.list_monitor_runs(MONITOR_ID, limit=10, cursor="c1")
        self.assertIsInstance(result, MonitorRunList)
        self.assertEqual(result.runs[0].stats["screen"], "ai")
        self.assertTrue(result.runs[0].is_finished)
        self.assertEqual(result.next_cursor, "c2")
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("GET", f"{BASE}/runs"))
        self.assertEqual(kwargs["params"], {"limit": 10, "cursor": "c1"})

    async def test_get_run_returns_its_items(self):
        client = self.make_client(FakeResponse(json_data=_run(items=[_item(), _item("1841")])))
        run = await client.get_monitor_run(MONITOR_ID, RUN_ID)
        self.assertIsInstance(run, MonitorRunWithItems)
        self.assertEqual([item.item_id for item in run.items], ["1842", "1841"])
        self.assertEqual(run.items[0].data["likes"], 120)
        self.assertEqual(self.request(client)[0:2], ("GET", f"{BASE}/runs/{RUN_ID}"))

    async def test_run_stats_list_accounts_that_failed(self):
        stats = {
            "sources": {
                "x": {"fetched": 40, "in_window": 12, "new": 12, "passed": 3, "error": None, "accounts_failed": ["gone_account"]},
                "tiktok": {"fetched": 0, "in_window": 0, "new": 0, "passed": 0, "error": "all accounts failed", "accounts_failed": ["private1"]},
                "instagram": {"fetched": 12, "in_window": 4, "new": 4, "passed": 1, "error": None, "hashtags_failed": ["gone_tag"]},
            },
            "screened": 12,
            "passed": 3,
            "screen": "ai",
        }
        client = self.make_client(FakeResponse(json_data=_run(stats=stats, items=[])))
        run = await client.get_monitor_run(MONITOR_ID, RUN_ID)
        self.assertEqual(run.stats["sources"]["x"]["accounts_failed"], ["gone_account"])
        self.assertEqual(run.stats["sources"]["tiktok"]["error"], "all accounts failed")
        self.assertEqual(run.stats["sources"]["instagram"]["hashtags_failed"], ["gone_tag"])

    async def test_wait_polls_until_the_run_ends(self):
        client = self.make_client(
            FakeResponse(json_data=_run("queued", items=[])),
            FakeResponse(json_data=_run("running", items=[])),
            FakeResponse(json_data=_run("completed", items=[_item()])),
        )
        run = await client.wait_for_monitor_run(MONITOR_ID, RUN_ID, poll_interval=0)
        self.assertEqual(run.status, "completed")
        self.assertEqual(len(run.items), 1)
        self.assertEqual(len(client.client.requests), 3)

    async def test_wait_raises_on_timeout_with_the_last_run(self):
        client = self.make_client(FakeResponse(json_data=_run("running", items=[])))
        with self.assertRaises(MonitorRunTimeoutError) as caught:
            await client.wait_for_monitor_run(MONITOR_ID, RUN_ID, timeout=0)
        self.assertEqual(caught.exception.run.status, "running")
        self.assertIsInstance(caught.exception, TimeoutError)
        self.assertIn(RUN_ID, str(caught.exception))


class MonitorItemTests(_ClientTestCase):
    async def test_list_items_sends_source_limit_and_cursor(self):
        page = {"items": [_item()], "next_cursor": "1842"}
        client = self.make_client(FakeResponse(json_data=page))
        result = await client.list_monitor_items(
            MONITOR_ID, limit=1, cursor="1900", source=MonitorSource.X
        )
        self.assertIsInstance(result, MonitorItemList)
        self.assertEqual(result.items[0].signals["relevant"], 0.91)
        self.assertEqual(result.next_cursor, "1842")
        method, url, kwargs = self.request(client)
        self.assertEqual((method, url), ("GET", f"{BASE}/items"))
        self.assertEqual(kwargs["params"], {"limit": 1, "cursor": "1900", "source": "x"})

    async def test_items_from_watched_accounts_and_tiktok_keep_their_data(self):
        tiktok = _item(
            "1900",
            source="tiktok",
            url="https://www.tiktok.com/@openai/video/7570000000000000000",
            data={
                "account": "openai",
                "views": 12000,
                "likes": 800,
                "comments": 31,
                "shares": 12,
                "duration_s": 42,
                "thumbnail": "https://p16-sign.tiktokcdn.com/thumb.jpeg",
            },
        )
        reddit = _item("1899", source="reddit", data={"account": "LocalLLaMA", "subreddit": "LocalLLaMA", "score": 50, "comments": 7})
        client = self.make_client(FakeResponse(json_data={"items": [tiktok, reddit], "next_cursor": None}))
        page = await client.list_monitor_items(MONITOR_ID, source=MonitorSource.TIKTOK)
        self.assertEqual(page.items[0].data["account"], "openai")
        self.assertEqual(page.items[0].data["duration_s"], 42)
        self.assertEqual(page.items[1].data["account"], "LocalLLaMA")
        self.assertEqual(self.request(client)[2]["params"], {"source": "tiktok"})

    async def test_items_from_hashtags_keep_the_post_fields(self):
        tiktok = _item(
            "2101",
            source="tiktok",
            url="https://www.tiktok.com/@someone/video/7570000000000000001",
            data={
                "hashtag": "aversi",
                "post_id": "7570000000000000001",
                "type": "video",
                "views": 3400,
                "likes": 210,
                "comments": 8,
                "shares": 3,
                "saves": 14,
                "duration_s": 21,
                "hashtags": ["aversi", "pharmacy"],
                "mentions": ["aversipharma"],
                "media": ["https://v16.tiktokcdn.com/video.mp4"],
                "thumbnail": "https://p16-sign.tiktokcdn.com/thumb.jpeg",
            },
        )
        instagram = _item(
            "2100",
            source="instagram",
            data={"hashtag": "ავერსი", "post_id": "DfPq1x2ABcd", "type": "carousel", "media_type": "carousel",
                  "media": ["https://scontent.cdninstagram.com/1.jpg", "https://scontent.cdninstagram.com/2.jpg"]},
        )
        facebook = _item("2099", source="facebook", data={"account": "NASA", "post_id": "1234567890", "type": "video", "views": 52000})
        client = self.make_client(FakeResponse(json_data={"items": [tiktok, instagram, facebook], "next_cursor": None}))
        page = await client.list_monitor_items(MONITOR_ID)
        by_source = {item.source: item for item in page.items}
        self.assertEqual(by_source["tiktok"].data["hashtag"], "aversi")
        self.assertEqual(by_source["tiktok"].data["saves"], 14)
        self.assertEqual(by_source["tiktok"].data["mentions"], ["aversipharma"])
        self.assertEqual(by_source["instagram"].data["post_id"], "DfPq1x2ABcd")
        self.assertEqual(len(by_source["instagram"].data["media"]), 2)
        self.assertEqual(by_source["facebook"].data["views"], 52000)
        self.assertNotIn("hashtag", by_source["facebook"].data)

    async def test_items_from_the_social_sources_and_meta_ads_keep_their_data(self):
        # Meta ads: the headline is the title, url the Ad Library record and
        # data.link the landing page; ads are screened without new_info.
        ad = _item(
            "2004",
            source="meta_ads",
            url="https://www.facebook.com/ads/library/?id=1234567890",
            title="Try ChatGPT Plus",
            text="Get faster answers.",
            signals={"relevant": 0.96, "criteria": 0.9},
            data={
                "page": "OpenAI",
                "active": True,
                "cta": "Learn more",
                "link": "https://chatgpt.com/",
                "platforms": ["facebook", "instagram"],
                "thumbnail": "https://scontent.xx.fbcdn.net/ad.jpg",
            },
        )
        instagram = _item(
            "2003",
            source="instagram",
            data={
                "account": "openai",
                "likes": 5400,
                "comments": 120,
                "views": 90000,
                "media_type": "video",
                "thumbnail": "https://scontent.cdninstagram.com/cover.jpg",
            },
        )
        facebook = _item("2002", source="facebook", data={"account": "NASA", "reactions": 3100, "comments": 210, "shares": 95})
        threads = _item(
            "2001",
            source="threads",
            signals={"relevant": 0.8, "new_info": 0.7, "criteria": 0.75},
            data={"account": "zuck", "likes": 4200},
        )
        page = {"items": [ad, instagram, facebook, threads], "next_cursor": None}
        client = self.make_client(FakeResponse(json_data=page))
        result = await client.list_monitor_items(MONITOR_ID, source=MonitorSource.META_ADS)
        by_source = {item.source: item for item in result.items}
        self.assertEqual(by_source["meta_ads"].title, "Try ChatGPT Plus")
        self.assertEqual(by_source["meta_ads"].data["link"], "https://chatgpt.com/")
        self.assertEqual(by_source["meta_ads"].data["platforms"], ["facebook", "instagram"])
        self.assertNotIn("new_info", by_source["meta_ads"].signals)
        self.assertEqual(by_source["meta_ads"].signals["criteria"], 0.9)
        self.assertEqual(by_source["instagram"].data["media_type"], "video")
        self.assertEqual(by_source["facebook"].data["reactions"], 3100)
        self.assertEqual(by_source["threads"].data["likes"], 4200)
        self.assertEqual(by_source["threads"].signals["criteria"], 0.75)
        self.assertEqual(self.request(client)[2]["params"], {"source": "meta_ads"})
        for source in (MonitorSource.INSTAGRAM, MonitorSource.FACEBOOK, "threads"):
            with self.subTest(source=source):
                client = self.make_client(FakeResponse(json_data={"items": [], "next_cursor": None}))
                await client.list_monitor_items(MONITOR_ID, source=source)
                self.assertEqual(
                    self.request(client)[2]["params"],
                    {"source": source.value if isinstance(source, MonitorSource) else source},
                )

    async def test_iter_items_follows_cursors_until_the_last_page(self):
        client = self.make_client(
            FakeResponse(json_data={"items": [_item("3"), _item("2")], "next_cursor": "2"}),
            FakeResponse(json_data={"items": [_item("1")], "next_cursor": None}),
        )
        items = [item async for item in client.iter_monitor_items(MONITOR_ID, page_size=2)]
        self.assertEqual([item.item_id for item in items], ["3", "2", "1"])
        self.assertEqual(self.request(client, 0)[2]["params"], {"limit": 2})
        self.assertEqual(self.request(client, 1)[2]["params"], {"limit": 2, "cursor": "2"})

    async def test_iter_items_stops_on_an_empty_page(self):
        client = self.make_client(FakeResponse(json_data={"items": [], "next_cursor": "9"}))
        items = [item async for item in client.iter_monitor_items(MONITOR_ID, source="web")]
        self.assertEqual(items, [])
        self.assertEqual(
            self.request(client)[2]["params"], {"limit": 50, "source": "web"}
        )


class MonitorWebhookRouteTests(_ClientTestCase):
    async def test_webhook_test_reports_the_delivery(self):
        result_body = {"delivered": False, "status_code": 405, "error": None, "duration_ms": 212}
        client = self.make_client(FakeResponse(json_data=result_body))
        result = await client.test_monitor_webhook(MONITOR_ID)
        self.assertIsInstance(result, MonitorWebhookTest)
        self.assertFalse(result.delivered)
        self.assertEqual(result.status_code, 405)
        self.assertEqual(self.request(client)[0:2], ("POST", f"{BASE}/webhook/test"))

    async def test_rotate_returns_the_new_secret(self):
        client = self.make_client(FakeResponse(json_data={"webhook_secret": "whsec_rotated"}))
        result = await client.rotate_monitor_webhook_secret(MONITOR_ID)
        self.assertIsInstance(result, MonitorWebhookSecret)
        self.assertEqual(result.webhook_secret, "whsec_rotated")
        self.assertEqual(
            self.request(client)[0:2], ("POST", f"{BASE}/webhook/rotate-secret")
        )

    async def test_a_monitor_without_webhook_is_a_400(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "This monitor has no webhook. Add one first."},
                status=400,
                reason="Bad Request",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.test_monitor_webhook(MONITOR_ID)
        self.assertEqual(caught.exception.status, 400)


# A delivery signed by the API's own signer (src/utils/webhooks.py signature()).
SECRET = "whsec_test_secret"
TIMESTAMP = 1793700041
BODY = b'{"id":"5521","type":"monitor.items.found","items":[]}'
HEADER = "t=1793700041,v1=f4d11312444751f4482c48e61ee3534472e3db1e5a6767e374b25846f95508e1"


def _sign(secret, timestamp, body):
    digest = hmac.new(secret.encode(), f"{timestamp}.".encode() + body, hashlib.sha256)
    return f"t={timestamp},v1={digest.hexdigest()}"


class VerifyWebhookSignatureTests(unittest.TestCase):
    def test_accepts_the_api_signature(self):
        self.assertEqual(SIGNATURE_HEADER, "Desearch-Signature")
        self.assertEqual(_sign(SECRET, TIMESTAMP, BODY), HEADER)
        self.assertTrue(verify_webhook_signature(SECRET, HEADER, BODY, now=TIMESTAMP))

    def test_accepts_str_and_bytearray_bodies(self):
        self.assertTrue(verify_webhook_signature(SECRET, HEADER, BODY.decode(), now=TIMESTAMP))
        self.assertTrue(verify_webhook_signature(SECRET, HEADER, bytearray(BODY), now=TIMESTAMP))

    def test_accepts_within_five_minutes_either_way(self):
        for now in (TIMESTAMP + 300, TIMESTAMP - 300):
            with self.subTest(now=now):
                self.assertTrue(verify_webhook_signature(SECRET, HEADER, BODY, now=now))

    def test_rejects_older_or_newer_than_the_tolerance(self):
        for now in (TIMESTAMP + 301, TIMESTAMP - 301):
            with self.subTest(now=now):
                self.assertFalse(verify_webhook_signature(SECRET, HEADER, BODY, now=now))
        self.assertTrue(
            verify_webhook_signature(SECRET, HEADER, BODY, tolerance=600, now=TIMESTAMP + 500)
        )
        self.assertTrue(
            verify_webhook_signature(SECRET, HEADER, BODY, tolerance=None, now=TIMESTAMP + 10**6)
        )

    def test_uses_the_clock_by_default(self):
        self.assertFalse(verify_webhook_signature(SECRET, HEADER, BODY))
        fresh = int(time.time())
        self.assertTrue(verify_webhook_signature(SECRET, _sign(SECRET, fresh, BODY), BODY))

    def test_rejects_a_changed_body_secret_or_timestamp(self):
        self.assertFalse(verify_webhook_signature(SECRET, HEADER, BODY + b" ", now=TIMESTAMP))
        self.assertFalse(verify_webhook_signature("whsec_other", HEADER, BODY, now=TIMESTAMP))
        moved = HEADER.replace("t=1793700041", "t=1793700042")
        self.assertFalse(verify_webhook_signature(SECRET, moved, BODY, now=TIMESTAMP))
        # The prefix is part of the key: the bare token does not verify.
        self.assertFalse(verify_webhook_signature("test_secret", HEADER, BODY, now=TIMESTAMP))

    def test_rejects_malformed_headers(self):
        digest = HEADER.split("v1=")[1]
        for header in (
            None,
            "",
            "garbage",
            f"v1={digest}",
            "t=1793700041",
            "t=1793700041,v1=",
            f"t=abc,v1={digest}",
            f"t=-1793700041,v1={digest}",
            f"t=１７９３７０００４１,v1={digest}",
            f"t=1793700041,v0={digest}",
            f"t=1793700041,v1={digest.upper()}",
            f"t=1793700041,v1=ü{digest[1:]}",
        ):
            with self.subTest(header=header):
                self.assertFalse(verify_webhook_signature(SECRET, header, BODY, now=TIMESTAMP))
        self.assertFalse(verify_webhook_signature("", HEADER, BODY, now=TIMESTAMP))

    def test_accepts_any_matching_v1_and_spaces(self):
        digest = HEADER.split("v1=")[1]
        header = f"t=1793700041, v1={'0' * 64}, v1={digest}"
        self.assertTrue(verify_webhook_signature(SECRET, header, BODY, now=TIMESTAMP))

    def test_a_verified_body_parses_as_a_webhook_event(self):
        payload = {
            "id": "5521",
            "type": "monitor.items.found",
            "created_at": "2026-11-03T09:00:41Z",
            "monitor": {"monitor_id": MONITOR_ID, "name": "Bittensor subnet news", "metadata": {}},
            "run": _run(),
            "items": [_item()],
        }
        body = json.dumps(payload, separators=(",", ":")).encode()
        header = _sign(SECRET, TIMESTAMP, body)
        self.assertTrue(verify_webhook_signature(SECRET, header, body, now=TIMESTAMP))
        event = MonitorWebhookEvent.model_validate_json(body)
        self.assertEqual(event.type, MonitorEvent.ITEMS_FOUND.value)
        self.assertEqual(event.run.run_id, RUN_ID)
        self.assertEqual(event.items[0].score, 91)
        test_event = MonitorWebhookEvent.model_validate(
            {**payload, "type": "monitor.test", "run": None}
        )
        self.assertIsNone(test_event.run)


KEY = "fake-key-for-monitor-tests"


class MonitorHttpTests(unittest.IsolatedAsyncioTestCase):
    """Runs the client against a local aiohttp server to check real requests."""

    async def asyncSetUp(self):
        self.seen = []

        async def handler(request):
            raw = await request.text()
            self.seen.append(
                {
                    "method": request.method,
                    "path": request.path,
                    "query": request.query_string,
                    "authorization": request.headers.get("Authorization"),
                    "body": raw,
                }
            )
            path = request.path
            if path.endswith("/items"):
                return web.json_response({"items": [_item()], "next_cursor": None})
            if path.endswith("/trigger"):
                return web.json_response(_run("queued", trigger="manual"), status=202)
            if path == "/desearch/monitors" and request.method == "GET":
                return web.json_response({"monitors": [], "next_cursor": None})
            return web.json_response(_monitor(), status=201 if request.method == "POST" else 200)

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = site._server.sockets[0].getsockname()[1]
        self.client = Desearch(api_key=KEY, base_url=f"http://127.0.0.1:{port}")

    async def asyncTearDown(self):
        await self.client.close()
        await self.runner.cleanup()

    async def test_requests_reach_the_server_with_auth_bodies_and_params(self):
        await self.client.create_monitor(QUERY, sources=["x"], run_now=False)
        await self.client.update_monitor(MONITOR_ID, remove_webhook=True)
        await self.client.list_monitors(status="paused", limit=3)
        await self.client.trigger_monitor(MONITOR_ID)
        items = [i async for i in self.client.iter_monitor_items(MONITOR_ID, source="x")]
        self.assertEqual(len(items), 1)
        create, update, listing, trigger, item_page = self.seen
        self.assertEqual((create["method"], create["path"]), ("POST", "/desearch/monitors"))
        self.assertEqual(create["authorization"], KEY)
        self.assertEqual(
            json.loads(create["body"]), {"query": QUERY, "sources": ["x"], "run_now": False}
        )
        self.assertEqual((update["method"], update["path"]), ("PATCH", f"/desearch/monitors/{MONITOR_ID}"))
        self.assertEqual(update["body"], '{"webhook": null}')
        self.assertEqual(listing["query"], "status=paused&limit=3")
        self.assertEqual(trigger["path"], f"/desearch/monitors/{MONITOR_ID}/trigger")
        self.assertEqual(item_page["query"], "limit=50&source=x")


if __name__ == "__main__":
    unittest.main()
