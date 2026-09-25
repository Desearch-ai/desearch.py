import unittest

import aiohttp

from desearch_py import Desearch, DesearchResponse, __version__


class FakeResponse:
    def __init__(self, *, text_data="", headers=None, status=200, message="OK"):
        self._text_data = text_data
        self.headers = headers or {}
        self.status = status
        self.message = message

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self):
        if self.status >= 400:
            raise aiohttp.ClientResponseError(
                None,
                (),
                status=self.status,
                message=self.message,
            )

    async def text(self):
        return self._text_data


class FakeSession:
    closed = False

    def __init__(self, responses):
        self._responses = list(responses)
        self.requests = []

    def request(self, method, url, **kwargs):
        self.requests.append((method, url, kwargs))
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def close(self):
        self.closed = True


class ExtractTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    def test_package_version_is_1_3_0(self):
        self.assertEqual(__version__, "1.3.0")

    async def test_extract_defaults_match_public_api(self):
        client = self.make_client(FakeResponse(text_data="page text"))

        result = await client.extract(url="https://desearch.ai")

        self.assertEqual(result, "page text")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(method, "GET")
        self.assertEqual(url, "https://example.test/web/extract")
        self.assertEqual(
            kwargs["params"],
            {
                "url": "https://desearch.ai",
                "format": "text",
                "js": "false",
            },
        )
        self.assertNotIn("wait", kwargs["params"])

    async def test_extract_sends_canonical_query_params(self):
        client = self.make_client(FakeResponse(text_data="rendered"))

        result = await client.extract(
            url="https://desearch.ai",
            format="html",
            js=True,
            wait=250,
        )

        self.assertEqual(result, "rendered")
        self.assertEqual(
            client.client.requests[0][2]["params"],
            {
                "url": "https://desearch.ai",
                "format": "html",
                "js": "true",
                "wait": 250,
            },
        )

    async def test_extract_omits_null_format_and_keeps_zero_wait(self):
        client = self.make_client(FakeResponse(text_data="ok"))

        await client.extract(url="https://desearch.ai", format=None, js=False, wait=0)

        self.assertEqual(
            client.client.requests[0][2]["params"],
            {
                "url": "https://desearch.ai",
                "js": "false",
                "wait": 0,
            },
        )

    async def test_extract_include_metadata_wraps_text(self):
        headers = {
            "X-Desearch-Cost-Usd": "0.00015",
            "X-Desearch-Usage-Count": "10",
            "X-Desearch-Service": "web-extract",
            "X-Desearch-Currency": "USD",
        }
        client = self.make_client(FakeResponse(text_data="content", headers=headers))

        result = await client.extract(
            url="https://desearch.ai", include_metadata=True
        )

        self.assertIsInstance(result, DesearchResponse)
        self.assertEqual(result.data, "content")
        self.assertEqual(result.metadata.cost_usd, 0.00015)
        self.assertEqual(result.metadata.usage_count, 10)
        self.assertEqual(result.metadata.service, "web-extract")
        self.assertEqual(result.metadata.currency, "USD")

    async def test_extract_http_error_is_reraised(self):
        client = self.make_client(
            FakeResponse(status=422, message="Validation Error", text_data="nope")
        )

        with self.assertRaises(aiohttp.ClientResponseError) as caught:
            await client.extract(url="https://desearch.ai")

        self.assertEqual(caught.exception.status, 422)
        self.assertEqual(caught.exception.message, "Validation Error")

    async def test_extract_connection_error_is_reraised(self):
        client = self.make_client(aiohttp.ClientConnectionError("connection failed"))

        with self.assertRaises(aiohttp.ClientConnectionError):
            await client.extract(url="https://desearch.ai", js=True, wait=250)


if __name__ == "__main__":
    unittest.main()
