"""Query string encoding tests that send real aiohttp requests.

The other suites replace the HTTP session with a fake, so aiohttp and yarl
never encode the query string there. These tests run a local aiohttp server on
127.0.0.1 and check the query each SDK method actually sends.
"""

import unittest

from aiohttp import test_utils, web

from desearch_py import Desearch
from desearch_py.api import _encode_query_params


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
USER = {"id": "2", "username": "desearch"}

JSON_RESPONSES = {
    "/twitter": [TWEET],
    "/twitter/urls": [TWEET],
    "/twitter/post": TWEET,
    "/twitter/post/user": [TWEET],
    "/twitter/post/retweeters": {"users": [USER]},
    "/twitter/user/posts": {"user": USER, "tweets": [TWEET]},
    "/twitter/replies": [TWEET],
    "/twitter/replies/post": [TWEET],
    "/twitter/trends": {"trends": [{"name": "#desearch"}]},
    "/web": {"data": []},
}
TEXT_RESPONSES = {
    "/web/extract": "extracted",
    "/web/crawl": "crawled",
}


class LocalServerQueryParamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.received = []

        async def handler(request):
            self.received.append((request.path, list(request.query.items())))
            if request.path in TEXT_RESPONSES:
                return web.Response(text=TEXT_RESPONSES[request.path])
            return web.json_response(JSON_RESPONSES[request.path])

        app = web.Application()
        app.router.add_get("/{tail:.*}", handler)
        self.server = test_utils.TestServer(app, host="127.0.0.1")
        await self.server.start_server()
        self.client = Desearch(
            api_key="test-key", base_url=str(self.server.make_url("/"))
        )

    async def asyncTearDown(self):
        await self.client.close()
        await self.server.close()

    async def test_x_search_sends_boolean_filters_as_lowercase_strings(self):
        tweets = await self.client.x_search(
            query="desearch",
            verified=True,
            blue_verified=False,
            is_quote=True,
            is_video=False,
            is_image=True,
            min_likes=5,
            count=3,
        )

        self.assertEqual([tweet.id for tweet in tweets], ["1"])
        self.assertEqual(
            self.received,
            [
                (
                    "/twitter",
                    [
                        ("query", "desearch"),
                        ("sort", "Top"),
                        ("verified", "true"),
                        ("blue_verified", "false"),
                        ("is_quote", "true"),
                        ("is_video", "false"),
                        ("is_image", "true"),
                        ("min_likes", "5"),
                        ("count", "3"),
                    ],
                )
            ],
        )

    async def test_every_query_param_method_sends_a_real_request(self):
        first = "https://x.com/desearch/status/1"
        second = "https://x.com/desearch/status/2"
        await self.client.x_posts_by_urls(urls=[first, second])
        await self.client.x_post_by_id(id="1")
        await self.client.x_posts_by_user(user="desearch", count=2)
        await self.client.x_post_retweeters(id="1")
        await self.client.x_user_posts(username="desearch")
        await self.client.x_user_replies(user="desearch", query="sdk")
        await self.client.x_post_replies(post_id="1", count=2)
        await self.client.x_trends(woeid=23424977)
        await self.client.web_search(query="desearch")
        extracted = await self.client.extract(url="https://desearch.ai", js=True)
        crawled = await self.client.web_crawl(url="https://desearch.ai")

        self.assertEqual(extracted, "extracted")
        self.assertEqual(crawled, "crawled")
        self.assertEqual(
            self.received,
            [
                ("/twitter/urls", [("urls", first), ("urls", second)]),
                ("/twitter/post", [("id", "1")]),
                ("/twitter/post/user", [("user", "desearch"), ("count", "2")]),
                ("/twitter/post/retweeters", [("id", "1")]),
                ("/twitter/user/posts", [("username", "desearch")]),
                ("/twitter/replies", [("user", "desearch"), ("query", "sdk")]),
                ("/twitter/replies/post", [("post_id", "1"), ("count", "2")]),
                ("/twitter/trends", [("woeid", "23424977")]),
                ("/web", [("query", "desearch"), ("start", "0")]),
                (
                    "/web/extract",
                    [
                        ("url", "https://desearch.ai"),
                        ("format", "text"),
                        ("js", "true"),
                    ],
                ),
                (
                    "/web/crawl",
                    [("url", "https://desearch.ai"), ("format", "text")],
                ),
            ],
        )


class EncodeQueryParamsTests(unittest.TestCase):
    def test_mapping_converts_booleans_and_drops_none(self):
        self.assertEqual(
            _encode_query_params(
                {"on": True, "off": False, "unset": None, "zero": 0, "text": "x"}
            ),
            {"on": "true", "off": "false", "zero": 0, "text": "x"},
        )

    def test_pairs_keep_repeated_keys_in_order(self):
        self.assertEqual(
            _encode_query_params([("tag", True), ("tag", None), ("tag", "x")]),
            [("tag", "true"), ("tag", "x")],
        )

    def test_other_values_pass_through(self):
        self.assertEqual(_encode_query_params("a=1"), "a=1")
        self.assertIsNone(_encode_query_params(None))


if __name__ == "__main__":
    unittest.main()
