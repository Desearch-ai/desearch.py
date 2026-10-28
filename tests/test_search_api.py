import unittest
from typing import Any, List, cast

from aiohttp import web

from desearch_py import (
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    SearchApiMode,
    SearchApiResponse,
    SearchApiResult,
)

SEARCH_BODY = {
    "results": [
        {
            "url": "https://example.com/nobel",
            "title": "Nobel Prize in Physics 2024",
            "published_date": "2024-10-08",
            "highlights": ["Hopfield and Hinton won the 2024 prize."],
        },
        {"url": "https://example.com/other", "title": "Other"},
    ],
    "cost_usd": 0.005,
    "usage_count": 1,
    "service": "search",
    "currency": "USD",
}


class FakeResponse:
    def __init__(self, *, json_data=None, headers=None):
        self._json_data = json_data
        self.headers = headers or {}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        return None

    async def json(self):
        return self._json_data

    async def text(self):
        return ""


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


class SearchApiTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_posts_only_the_query_by_default(self):
        client = self.make_client(FakeResponse(json_data=SEARCH_BODY))

        result = await client.search_api("Who won the 2024 Nobel Prize in Physics?")

        method, url, kwargs = client.client.requests[0]
        self.assertEqual((method, url), ("POST", "https://example.test/search"))
        self.assertEqual(
            kwargs["json"], {"query": "Who won the 2024 Nobel Prize in Physics?"}
        )
        self.assertIsInstance(result, SearchApiResponse)
        result = cast(SearchApiResponse, result)
        self.assertEqual(len(result.results), 2)
        self.assertIsInstance(result.results[0], SearchApiResult)
        self.assertEqual(
            result.results[0].highlights, ["Hopfield and Hinton won the 2024 prize."]
        )
        self.assertIsNone(result.results[1].published_date)
        self.assertIsNone(result.results[1].page_text)
        self.assertEqual(result.cost_usd, 0.005)
        self.assertEqual(result.service, "search")

    async def test_sends_every_option(self):
        client = self.make_client(
            FakeResponse(json_data={"results": []}),
            FakeResponse(json_data={"results": []}),
        )
        await client.search_api(
            "bittensor",
            mode=SearchApiMode.FAST,
            count=20,
            start_date="2026-01-01",
            end_date="2026-09-17",
            highlights=False,
            page_text=True,
        )
        await client.search_api("bittensor", mode="balanced", count=15)

        self.assertEqual(
            client.client.requests[0][2]["json"],
            {
                "query": "bittensor",
                "mode": "fast",
                "count": 20,
                "start_date": "2026-01-01",
                "end_date": "2026-09-17",
                "highlights": False,
                "page_text": True,
            },
        )
        self.assertEqual(
            client.client.requests[1][2]["json"],
            {"query": "bittensor", "mode": "balanced", "count": 15},
        )

    async def test_include_metadata_wraps_the_response(self):
        headers = {
            "X-Desearch-Cost-Usd": "0.005",
            "X-Desearch-Usage-Count": "1",
            "X-Desearch-Service": "search",
            "X-Desearch-Currency": "USD",
        }
        client = self.make_client(FakeResponse(json_data=SEARCH_BODY, headers=headers))

        result = await client.search_api("q", include_metadata=True)

        self.assertIsInstance(result, DesearchResponse)
        result = cast(DesearchResponse, result)
        self.assertIsInstance(result.data, SearchApiResponse)
        self.assertEqual(result.metadata.cost_usd, 0.005)
        self.assertEqual(result.metadata.service, "search")
        self.assertIsNone(result.metadata.next_cursor)

    async def test_cost_fields_are_optional_in_the_body(self):
        client = self.make_client(
            FakeResponse(json_data={"results": [{"url": "u", "title": "t"}]})
        )
        result = cast(SearchApiResponse, await client.search_api("q"))
        self.assertIsNone(result.cost_usd)
        self.assertEqual(result.results[0].url, "u")

    def test_no_method_is_named_plain_search(self):
        # llama-index-desearch 0.0.2 still calls a legacy client.search(...).
        # Reusing that name with new semantics would hide the breakage.
        self.assertFalse(hasattr(Desearch, "search"))


class SearchApiErrorTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests: List[Any] = []

        async def handler(request):
            payload = await request.json()
            self.requests.append(payload)
            if payload["query"] == "unavailable":
                return web.Response(
                    status=503,
                    text='{"detail":"Search unavailable."}',
                    content_type="application/json",
                )
            return web.Response(
                status=422,
                text='{"detail":[{"loc":["body","count"],"msg":"Input should be a multiple of 5","type":"multiple_of"}]}',
                content_type="application/json",
            )

        app = web.Application()
        app.router.add_post("/search", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        sockets = cast(Any, site._server).sockets
        self.client = Desearch(
            api_key="test-key",
            base_url=f"http://127.0.0.1:{sockets[0].getsockname()[1]}",
        )

    async def asyncTearDown(self):
        await self.client.close()
        await self.runner.cleanup()

    async def test_http_errors_raise_desearch_api_error(self):
        with self.assertLogs("desearch_py.api", level="ERROR"):
            with self.assertRaises(DesearchAPIError) as unavailable:
                await self.client.search_api("unavailable")
            with self.assertRaises(DesearchAPIError) as invalid:
                await self.client.search_api("q", count=12)

        self.assertEqual(unavailable.exception.status, 503)
        self.assertEqual(unavailable.exception.body, '{"detail":"Search unavailable."}')
        self.assertIsNone(unavailable.exception.__cause__)
        self.assertEqual(invalid.exception.status, 422)
        self.assertIn("multiple_of", invalid.exception.body)
        self.assertEqual(
            self.requests, [{"query": "unavailable"}, {"query": "q", "count": 12}]
        )


if __name__ == "__main__":
    unittest.main()
