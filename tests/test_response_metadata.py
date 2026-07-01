import unittest

from desearch_py import Desearch, DesearchResponse, ResponseData, TwitterScraperTweet


TWEET = {
    "id": "1",
    "text": "hello",
    "reply_count": 0,
    "retweet_count": 0,
    "like_count": 1,
    "quote_count": 0,
    "bookmark_count": 0,
    "created_at": "2026-05-07T00:00:00Z",
}


class FakeResponse:
    def __init__(self, *, json_data=None, text_data="", headers=None):
        self._json_data = json_data
        self._text_data = text_data
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


class ResponseMetadataTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_default_calls_keep_original_json_object_list_and_text_shapes(self):
        ai_client = self.make_client(
            FakeResponse(
                json_data={"text": "answer"},
                headers={"X-Desearch-Cost-Usd": "0.00015"},
            )
        )
        ai_result = await ai_client.ai_search(prompt="q", tools=["web"])
        self.assertIsInstance(ai_result, ResponseData)
        self.assertNotIsInstance(ai_result, DesearchResponse)
        self.assertEqual(ai_result.text, "answer")

        x_client = self.make_client(
            FakeResponse(
                json_data=[TWEET],
                headers={"X-Desearch-Cost-Usd": "0.00015"},
            )
        )
        x_result = await x_client.x_search(query="desearch")
        self.assertIsInstance(x_result, list)
        self.assertIsInstance(x_result[0], TwitterScraperTweet)

        crawl_client = self.make_client(
            FakeResponse(
                text_data="plain crawl text",
                headers={"X-Desearch-Cost-Usd": "0.00015"},
            )
        )
        crawl_result = await crawl_client.web_crawl(url="https://desearch.ai")
        self.assertEqual(crawl_result, "plain crawl text")

    async def test_include_metadata_wraps_data_and_parsed_response_headers(self):
        headers = {
            "X-Desearch-Cost-Usd": "0.00025",
            "X-Desearch-Usage-Count": "7",
            "X-Desearch-Service": "twitter",
            "X-Desearch-Currency": "USD",
        }
        client = self.make_client(FakeResponse(json_data=[TWEET], headers=headers))

        result = await client.x_search(query="desearch", include_metadata=True)

        self.assertIsInstance(result, DesearchResponse)
        self.assertIsInstance(result.data, list)
        self.assertIsInstance(result.data[0], TwitterScraperTweet)
        self.assertEqual(result.metadata.cost_usd, 0.00025)
        self.assertEqual(result.metadata.usage_count, 7)
        self.assertEqual(result.metadata.service, "twitter")
        self.assertEqual(result.metadata.currency, "USD")

    async def test_custom_json_and_text_paths_support_include_metadata(self):
        headers = {
            "X-Desearch-Cost-Usd": "0.00005",
            "X-Desearch-Usage-Count": "1",
            "X-Desearch-Service": "crawl",
            "X-Desearch-Currency": "USD",
        }
        urls_client = self.make_client(FakeResponse(json_data=[TWEET], headers=headers))
        urls_result = await urls_client.x_posts_by_urls(
            urls=["https://x.com/desearch/status/1"], include_metadata=True
        )
        self.assertIsInstance(urls_result, DesearchResponse)
        self.assertIsInstance(urls_result.data[0], TwitterScraperTweet)
        self.assertEqual(urls_result.metadata.cost_usd, 0.00005)

        crawl_client = self.make_client(FakeResponse(text_data="content", headers=headers))
        crawl_result = await crawl_client.web_crawl(
            url="https://desearch.ai", include_metadata=True
        )
        self.assertIsInstance(crawl_result, DesearchResponse)
        self.assertEqual(crawl_result.data, "content")
        self.assertEqual(crawl_result.metadata.service, "crawl")

    async def test_legacy_cents_header_is_not_treated_as_canonical_usd_metadata(self):
        client = self.make_client(
            FakeResponse(
                json_data={"text": "ok"},
                headers={"X-Desearch-Cost-Cents": "0.15"},
            )
        )

        result = await client.ai_search(
            prompt="q", tools=["web"], include_metadata=True
        )

        self.assertIsInstance(result, DesearchResponse)
        self.assertIsNone(result.metadata.cost_usd)

    async def test_missing_or_malformed_metadata_headers_do_not_break_successful_calls(self):
        client = self.make_client(
            FakeResponse(
                json_data={"text": "ok"},
                headers={
                    "X-Desearch-Cost-Usd": "NaN",
                    "X-Desearch-Usage-Count": "also-bad",
                },
            )
        )

        result = await client.ai_search(
            prompt="q", tools=["web"], include_metadata=True
        )

        self.assertIsInstance(result, DesearchResponse)
        self.assertEqual(result.data.text, "ok")
        self.assertIsNone(result.metadata.cost_usd)
        self.assertIsNone(result.metadata.usage_count)
        self.assertIsNone(result.metadata.service)
        self.assertIsNone(result.metadata.currency)


if __name__ == "__main__":
    unittest.main()
