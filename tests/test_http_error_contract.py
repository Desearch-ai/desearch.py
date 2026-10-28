import traceback
import unittest
from typing import Any, List, Optional, cast

from aiohttp import web

from desearch_py import (
    Desearch,
    DesearchAPIError,
    ResponseData,
    WebSearchResponse,
    XTrendsResponse,
)


KEY = "fake-key-for-422-contract-test"
WOEID = 23424977

TREND_VALIDATION_BODY = (
    '{"detail":[{"loc":["query","count"],'
    '"msg":"Input should be greater than or equal to 30",'
    '"type":"greater_than_equal"}]}'
)
AI_SEARCH_VALIDATION_BODY = (
    '{"detail":"Unsupported tool. Supported tools are Twitter Search and Web Search."}'
)
WEB_LINKS_VALIDATION_BODY = (
    '{"detail":"Unsupported tool. Supported tools are Web Search."}'
)


def _exception_dump(exc: BaseException) -> str:
    chunks = []
    pending: List[Optional[BaseException]] = [exc]
    seen = set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        chunks.extend(
            (
                str(current),
                repr(current),
                repr(current.args),
                repr(getattr(current, "__dict__", {})),
                "".join(
                    traceback.format_exception(
                        type(current), current, current.__traceback__
                    )
                ),
            )
        )
        pending.append(current.__cause__)
        pending.append(current.__context__)
    return "\n".join(chunks)


class HttpErrorContractTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []

        async def ai_search(request):
            payload = await request.json()
            self.requests.append(
                (request.method, request.path, payload, request.headers.get("Authorization"))
            )
            prompt = payload["prompt"]
            if prompt == "success":
                return web.json_response({"text": "ok"})
            if prompt == "redact":
                return web.Response(
                    status=422,
                    reason=f"Invalid request for {KEY}",
                    text='{"detail":"invalid ' + KEY + '"}',
                    content_type="application/json",
                )
            if prompt == "text-error":
                return web.Response(
                    status=422,
                    text="validation failed before JSON parsing",
                    content_type="text/plain",
                )
            return web.Response(
                status=422,
                text=AI_SEARCH_VALIDATION_BODY,
                content_type="application/json",
            )

        async def ai_web_links_search(request):
            payload = await request.json()
            self.requests.append(
                (request.method, request.path, payload, request.headers.get("Authorization"))
            )
            prompt = payload["prompt"]
            if prompt == "success":
                return web.json_response(
                    {
                        "search_results": [
                            {
                                "title": "Desearch",
                                "snippet": "Search for AI applications",
                                "link": "https://desearch.ai",
                            }
                        ]
                    }
                )
            if prompt == "empty-error":
                return web.Response(status=422)
            return web.Response(
                status=422,
                text=WEB_LINKS_VALIDATION_BODY,
                content_type="application/json",
            )

        async def x_trends(request):
            self.requests.append(
                (
                    request.method,
                    request.path,
                    dict(request.query),
                    request.headers.get("Authorization"),
                )
            )
            if request.query.get("count") == "30":
                return web.json_response(
                    {
                        "trends": [
                            {"name": "#Desearch", "query": "%23Desearch", "rank": 1}
                        ],
                        "woeid": {"name": "United States", "id": WOEID},
                    }
                )
            return web.Response(
                status=422,
                text=TREND_VALIDATION_BODY,
                content_type="application/json",
            )

        app = web.Application()
        app.router.add_post("/desearch/ai/search", ai_search)
        app.router.add_post("/desearch/ai/search/links/web", ai_web_links_search)
        app.router.add_get("/twitter/trends", x_trends)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        server = site._server
        self.assertIsNotNone(server)
        sockets = getattr(server, "sockets", None)
        self.assertTrue(sockets)
        sockets = cast(List[Any], sockets)
        self.base_url = f"http://127.0.0.1:{sockets[0].getsockname()[1]}"

    async def asyncTearDown(self):
        await self.runner.cleanup()

    def assert_error_surface(self, error, expected_body):
        self.assertIsInstance(error, DesearchAPIError)
        self.assertEqual(error.status, 422)
        self.assertEqual(error.message, "Unprocessable Entity")
        self.assertEqual(error.body, expected_body)
        self.assertEqual(error.args, (422, "Unprocessable Entity", expected_body))
        self.assertIn("422", str(error))
        self.assertIn(expected_body, str(error))
        self.assertIn("422", repr(error))
        self.assertIn(expected_body, repr(error))
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    async def test_public_methods_preserve_422_status_and_diagnostic_body(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        calls = (
            (
                client.x_trends(woeid=WOEID, count=29),
                TREND_VALIDATION_BODY,
            ),
            (
                client.ai_search(prompt="unsupported", tools=["youtube"]),
                AI_SEARCH_VALIDATION_BODY,
            ),
            (
                client.ai_web_links_search(
                    prompt="unsupported", tools=["youtube"]
                ),
                WEB_LINKS_VALIDATION_BODY,
            ),
        )
        try:
            for call, expected_body in calls:
                with self.assertRaises(DesearchAPIError) as caught:
                    await call
                self.assert_error_surface(caught.exception, expected_body)
        finally:
            await client.close()

    async def test_422_redacts_key_from_exception_and_logs(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        try:
            with self.assertLogs("desearch_py.api", level="ERROR") as logs:
                with self.assertRaises(DesearchAPIError) as caught:
                    await client.ai_search(prompt="redact", tools=["web"])
        finally:
            await client.close()

        error = caught.exception
        self.assertEqual(error.status, 422)
        self.assertEqual(error.message, "Invalid request for [REDACTED]")
        self.assertEqual(error.body, '{"detail":"invalid [REDACTED]"}')
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(KEY, _exception_dump(error))
        self.assertNotIn(KEY, "\n".join(logs.output))

    async def test_non_json_and_empty_422_bodies_fall_back_to_text_and_empty_string(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        try:
            with self.assertRaises(DesearchAPIError) as text_caught:
                await client.ai_search(prompt="text-error", tools=["web"])
            with self.assertRaises(DesearchAPIError) as empty_caught:
                await client.ai_web_links_search(
                    prompt="empty-error", tools=["web"]
                )
        finally:
            await client.close()

        self.assertEqual(text_caught.exception.status, 422)
        self.assertEqual(
            text_caught.exception.body, "validation failed before JSON parsing"
        )
        self.assertEqual(empty_caught.exception.status, 422)
        self.assertEqual(empty_caught.exception.body, "")
        self.assertEqual(
            empty_caught.exception.args, (422, "Unprocessable Entity", "")
        )

    async def test_affected_public_methods_keep_successful_response_shapes(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        try:
            ai_result = await client.ai_search(
                prompt="success", tools=["web"], count=10
            )
            web_result = await client.ai_web_links_search(
                prompt="success", tools=["web"], count=10
            )
            trends_result = await client.x_trends(woeid=WOEID, count=30)
        finally:
            await client.close()

        self.assertIsInstance(ai_result, ResponseData)
        ai_data = cast(ResponseData, ai_result)
        self.assertEqual(ai_data.text, "ok")
        self.assertIsInstance(web_result, WebSearchResponse)
        web_data = cast(WebSearchResponse, web_result)
        self.assertIsNotNone(web_data.search_results)
        search_results = cast(List[Any], web_data.search_results)
        self.assertEqual(search_results[0].link, "https://desearch.ai")
        self.assertIsInstance(trends_result, XTrendsResponse)
        trends_data = cast(XTrendsResponse, trends_result)
        self.assertEqual(trends_data.trends[0].name, "#Desearch")
        self.assertIsNotNone(trends_data.woeid)
        self.assertEqual(cast(Any, trends_data.woeid).id, WOEID)
        self.assertEqual(
            self.requests,
            [
                (
                    "POST",
                    "/desearch/ai/search",
                    {
                        "prompt": "success",
                        "tools": ["web"],
                        "streaming": False,
                        "result_type": "LINKS_WITH_FINAL_SUMMARY",
                        "count": 10,
                    },
                    KEY,
                ),
                (
                    "POST",
                    "/desearch/ai/search/links/web",
                    {"prompt": "success", "tools": ["web"], "count": 10},
                    KEY,
                ),
                (
                    "GET",
                    "/twitter/trends",
                    {"woeid": str(WOEID), "count": "30"},
                    KEY,
                ),
            ],
        )


if __name__ == "__main__":
    unittest.main()
