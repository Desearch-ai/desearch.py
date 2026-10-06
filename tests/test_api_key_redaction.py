import inspect
import traceback
import types
import unittest

from aiohttp import ClientResponseError, web
from aiohttp.client_reqrep import RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from desearch_py import Desearch, DesearchAPIError


KEY = "fake-key-for-leak-test"

_SKIP_TYPES = (
    types.ModuleType,
    types.FunctionType,
    types.MethodType,
    types.BuiltinFunctionType,
    types.BuiltinMethodType,
    types.TracebackType,
    types.FrameType,
    type,
)


def _request_info(url: URL, method: str, headers: CIMultiDictProxy) -> RequestInfo:
    """Construct ``RequestInfo`` whether or not this aiohttp requires ``real_url``."""
    try:
        parameters = inspect.signature(RequestInfo).parameters
    except (TypeError, ValueError):
        parameters = {}
    kwargs = {"url": url, "method": method, "headers": headers}
    if "real_url" in parameters:
        kwargs["real_url"] = url
    try:
        return RequestInfo(**kwargs)
    except TypeError:
        if "real_url" in kwargs:
            kwargs.pop("real_url")
        else:
            kwargs["real_url"] = url
        return RequestInfo(**kwargs)


def _recursive_dump(obj: object) -> str:
    """Stringify an exception chain and the attributes stored on it.

    Traceback frames are not walked into ``f_locals``. The formatted traceback
    is included separately; frame locals are live caller state, not values the
    exception stores.
    """
    chunks = []
    seen = set()

    def walk(value: object) -> None:
        if value is None or isinstance(value, (int, float, bool)):
            chunks.append(repr(value))
            return
        if isinstance(value, (str, bytes)):
            chunks.append(repr(value))
            return
        if isinstance(value, _SKIP_TYPES):
            return
        identity = id(value)
        if identity in seen:
            return
        seen.add(identity)
        try:
            chunks.append(repr(value))
        except Exception:
            chunks.append(f"<unrepr {type(value).__name__}>")

        if isinstance(value, BaseException):
            chunks.append(str(value))
            chunks.append(
                "".join(
                    traceback.format_exception(type(value), value, value.__traceback__)
                )
            )
            walk(value.args)
            walk(getattr(value, "__dict__", {}))
            notes = getattr(value, "__notes__", None)
            if notes:
                walk(notes)
            walk(value.__cause__)
            walk(value.__context__)
            for name in ("request_info", "headers", "history", "status", "message", "body"):
                if name in getattr(value, "__dict__", {}):
                    walk(value.__dict__[name])
            return

        if isinstance(value, dict):
            for key, item in value.items():
                walk(key)
                walk(item)
            return

        if isinstance(value, (list, tuple, set, frozenset)):
            for item in value:
                walk(item)
            return

        items = getattr(value, "items", None)
        if callable(items):
            try:
                pairs = list(items())
            except Exception:
                pairs = None
            if pairs is not None:
                for key, item in pairs:
                    walk(key)
                    walk(item)

        raw = getattr(value, "__dict__", None)
        if isinstance(raw, dict) and raw:
            walk(raw)

        slots = getattr(type(value), "__slots__", ())
        if isinstance(slots, str):
            slots = (slots,)
        for name in slots or ():
            if not isinstance(name, str) or name.startswith("__"):
                continue
            try:
                walk(getattr(value, name))
            except Exception:
                continue

        fields = getattr(value, "_fields", None)
        if isinstance(fields, tuple):
            for name in fields:
                try:
                    walk(getattr(value, name))
                except Exception:
                    continue

    walk(obj)
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
    info = _request_info(URL(f"http://example.test/web?token={KEY}"), "GET", headers)
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
        self.assertIsInstance(exc, ClientResponseError)
        self.assertIsNone(exc.__cause__)
        self.assertIsNone(exc.__context__)

        info = exc.request_info
        self.assertEqual(list(info.headers.items()), [])
        self.assertNotIn("Authorization", info.headers)
        self.assertEqual(exc.history, ())
        self.assertIsNone(exc.headers)
        self.assertNotIn(KEY, repr(info))
        for url in (info.url, info.real_url):
            self.assertNotIn(KEY, str(url))
            self.assertNotIn(KEY, repr(url))
            self.assertEqual(url.query_string, "")
            for value in url.query.values():
                self.assertNotIn(KEY, str(value))

        formatted = "".join(
            traceback.format_exception(type(exc), exc, exc.__traceback__)
        )
        dump = _recursive_dump(exc)
        self.assertNotIn(KEY, dump)
        self.assertNotIn(KEY, formatted)
        self.assertNotIn(KEY, str(exc))
        self.assertNotIn(KEY, repr(exc))
        self.assertNotIn(KEY, repr(exc.args))
        self.assertNotIn(KEY, repr(exc.__dict__))

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

    async def _assert_http_error(self, call):
        try:
            await call
        except ClientResponseError as error:
            self.assertIsInstance(error, DesearchAPIError)
            return error
        self.fail("except aiohttp.ClientResponseError did not catch the error")

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
                error = await self._assert_http_error(call)
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
            error = await self._assert_http_error(client.ai_search(prompt="q", tools=["web"]))
            extract_error = await self._assert_http_error(
                client.extract(url="https://example.com")
            )
        finally:
            await client.close()

        self.assert_key_absent(error)
        self.assertEqual(error.status, 403)
        self.assertEqual(error.body, '{"detail":"forbidden [REDACTED]"}')
        self.assertIn("[REDACTED]", str(error))

        self.assert_key_absent(extract_error)
        self.assertEqual(extract_error.status, 403)
        self.assertEqual(extract_error.body, '{"detail":"forbidden [REDACTED]"}')
        self.assertEqual(self.authorizations, [KEY, KEY])

    async def test_client_response_error_is_not_chained(self):
        leaked = _client_response_error()
        self.assertIn(KEY, repr(leaked))
        client = Desearch(api_key=KEY, base_url=f"https://example.test/{KEY}?token={KEY}")
        client.client = _LeakSession()
        calls = (
            client.web_search(query="q"),
            client.x_posts_by_urls(urls=["https://x.com/desearch/status/1"]),
            client.extract(url="https://example.com"),
            client.web_crawl(url="https://example.com"),
        )
        try:
            for call in calls:
                error = await self._assert_http_error(call)
                self.assert_key_absent(error)
                self.assertEqual(error.status, 403)
                self.assertEqual(error.message, "Forbidden")
                self.assertEqual(error.body, "")
                rendered = str(error.request_info.url)
                self.assertNotIn(KEY, rendered)
                self.assertTrue(
                    "[REDACTED]" in rendered or "%5BREDACTED%5D" in rendered,
                    rendered,
                )
        finally:
            await client.close()

    async def test_query_value_that_carries_the_key_is_not_stored(self):
        client = Desearch(api_key=KEY, base_url=self.base_url)
        error = client._make_api_error(
            403,
            "Forbidden " + KEY,
            "see " + KEY,
            "GET",
            f"{self.base_url}/{KEY}/web?token={KEY}&q=1#frag-{KEY}",
        )
        try:
            raise error
        except ClientResponseError as caught:
            self.assertIs(caught, error)
        self.assert_key_absent(error)
        self.assertEqual(error.status, 403)
        self.assertIn("[REDACTED]", error.message)
        self.assertIn("[REDACTED]", error.body)
        self.assertNotIn("token=", str(error.request_info.url))
        self.assertNotIn("token=", str(error.request_info.real_url))
        await client.close()


if __name__ == "__main__":
    unittest.main()
