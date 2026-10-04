import traceback
import unittest

from aiohttp import ClientResponseError, web
from aiohttp.client_reqrep import RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from desearch_py import Desearch, DesearchAPIError


KEY = "fake-key-for-leak-test"


def _exception_dump(exc: BaseException) -> str:
    chunks = []
    pending = [exc]
    seen = set()
    while pending:
        current = pending.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        chunks.append(str(current))
        chunks.append(repr(current))
        chunks.append(repr(current.args))
        chunks.append(repr(getattr(current, "__dict__", {})))
        notes = getattr(current, "__notes__", None)
        if notes:
            chunks.append(repr(notes))
        chunks.append(
            "".join(
                traceback.format_exception(type(current), current, current.__traceback__)
            )
        )
        pending.append(current.__cause__)
        pending.append(current.__context__)
    return "\n".join(chunks)


class _LeakResponse:
    """Response double with no status, so the client calls raise_for_status()."""

    def __init__(self, error: ClientResponseError) -> None:
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        raise self._error


class _LeakSession:
    closed = False

    def request(self, method, url, **kwargs):
        return _LeakResponse(_client_response_error())

    async def close(self):
        self.closed = True


def _client_response_error() -> ClientResponseError:
    headers = CIMultiDictProxy(CIMultiDict({"Authorization": KEY}))
    info = RequestInfo(
        url=URL("http://example.test/web"),
        method="GET",
        headers=headers,
        real_url=URL("http://example.test/web"),
    )
    return ClientResponseError(
        info,
        (),
        status=403,
        message="Forbidden",
        headers=headers,
    )


class ApiKeyRedactionTests(unittest.IsolatedAsyncioTestCase):
    def assert_key_absent(self, exc: BaseException) -> None:
        self.assertIsInstance(exc, DesearchAPIError)
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)
        self.assertFalse(hasattr(exc, "request_info"))
        self.assertFalse(hasattr(exc, "headers"))
        self.assertFalse(hasattr(exc, "history"))
        dump = _exception_dump(exc)
        self.assertNotIn(KEY, dump)
        self.assertNotIn(KEY, str(exc))
        self.assertNotIn(KEY, repr(exc))
        self.assertNotIn(KEY, repr(exc.args))

    async def asyncSetUp(self):
        self.authorizations = []
        self.include_key_in_body = False

        async def handler(request):
            self.authorizations.append(request.headers.get("Authorization"))
            if self.include_key_in_body:
                body = '{"detail":"forbidden ' + KEY + '"}'
            else:
                body = '{"detail":"forbidden"}'
            return web.Response(status=403, text=body, content_type="application/json")

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        sockets = site._server.sockets
        self.assertTrue(sockets)
        port = sockets[0].getsockname()[1]
        self.base_url = f"http://127.0.0.1:{port}"

    async def asyncTearDown(self):
        await self.runner.cleanup()

    async def test_http_403_omits_api_key_on_every_request_path(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        calls = (
            client.web_search(query="q"),
            client.x_posts_by_urls(urls=["https://x.com/desearch/status/1"]),
            client.extract(url="https://example.com"),
            client.web_crawl(url="https://example.com"),
        )
        try:
            for call in calls:
                with self.assertRaises(DesearchAPIError) as caught:
                    await call
                error = caught.exception
                self.assert_key_absent(error)
                self.assertEqual(error.status, 403)
                self.assertEqual(error.message, "Forbidden")
                self.assertEqual(error.body, '{"detail":"forbidden"}')
                self.assertIn("403", str(error))
                self.assertIn('{"detail":"forbidden"}', str(error))
                self.assertIn("403", repr(error))
        finally:
            await client.close()

        self.assertEqual(self.authorizations, [KEY, KEY, KEY, KEY])

    async def test_response_body_that_echoes_the_key_is_redacted(self):
        self.include_key_in_body = True
        client = Desearch(api_key=KEY, base_url=self.base_url)
        try:
            with self.assertRaises(DesearchAPIError) as caught:
                await client.ai_search(prompt="q", tools=["web"])
            with self.assertRaises(DesearchAPIError) as extract_caught:
                await client.extract(url="https://example.com")
        finally:
            await client.close()

        error = caught.exception
        self.assert_key_absent(error)
        self.assertEqual(error.status, 403)
        self.assertEqual(error.body, '{"detail":"forbidden [REDACTED]"}')
        self.assertIn("[REDACTED]", str(error))

        extract_error = extract_caught.exception
        self.assert_key_absent(extract_error)
        self.assertEqual(extract_error.status, 403)
        self.assertEqual(extract_error.body, '{"detail":"forbidden [REDACTED]"}')
        self.assertEqual(self.authorizations, [KEY, KEY])

    async def test_client_response_error_is_not_chained(self):
        leaked = _client_response_error()
        self.assertIn(KEY, repr(leaked))
        client = Desearch(api_key=KEY, base_url="https://example.test")
        client.client = _LeakSession()
        calls = (
            client.web_search(query="q"),
            client.x_posts_by_urls(urls=["https://x.com/desearch/status/1"]),
            client.extract(url="https://example.com"),
            client.web_crawl(url="https://example.com"),
        )
        try:
            for call in calls:
                with self.assertRaises(DesearchAPIError) as caught:
                    await call
                error = caught.exception
                self.assert_key_absent(error)
                self.assertEqual(error.status, 403)
                self.assertEqual(error.message, "Forbidden")
                self.assertEqual(error.body, "")
        finally:
            await client.close()


if __name__ == "__main__":
    unittest.main()
