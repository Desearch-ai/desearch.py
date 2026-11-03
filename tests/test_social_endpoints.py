"""TikTok, Facebook and Instagram methods.

Most tests replace the HTTP session with a fake that records each request.
``LocalServerSocialTests`` runs a local aiohttp server on 127.0.0.1 to check
what aiohttp actually puts on the wire: encoded path segments, cursor query
values, and the ``x-desearch-next-cursor`` header.
"""

import inspect
import unittest
from typing import Any, List, cast

from aiohttp import web

from desearch_py import (
    Desearch,
    DesearchAPIError,
    DesearchCostMetadata,
    DesearchResponse,
    FacebookComment,
    FacebookPost,
    FacebookProfile,
    InstagramComment,
    InstagramMedia,
    InstagramProfile,
    InstagramSearchResult,
    TikTokComment,
    TikTokPost,
    TikTokProfile,
)

KEY = "fake-key-for-social-tests"
CURSOR = "eyJ2IjoxLCJyb3V0ZSI6Ii9kZXNlYXJjaCJ9.c2lnbmF0dXJl-_=="

TIKTOK_POST = {
    "id": "7620891413932166433",
    "providerId": "v12044gd0000",
    "url": "https://www.tiktok.com/@tiktok/video/7620891413932166433",
    "text": "caption #ai",
    "createTime": "2024-01-15T10:30:00Z",
    "author": {"id": "1", "username": "tiktok", "followers": 50000},
    "stats": {"playCount": 120000, "digCount": 5000},
    "music": {"id": "67890", "title": "Song", "authorName": "Artist"},
    "hashtags": ["ai"],
    "mentions": [],
    "videoDuration": 15000,
}
TIKTOK_PROFILE = {
    "id": "1",
    "username": "tiktok",
    "nickname": "TikTok",
    "verified": True,
    "followers": 50000,
    "bio": "bio text",
    "videoCount": 250,
    "digCount": 450000,
}
TIKTOK_COMMENT = {
    "id": "7620891413932166999",
    "videoId": "7620891413932166433",
    "text": "nice",
    "createTime": "2024-01-15T11:00:00Z",
    "author": {"username": "fan"},
    "likes": 42,
    "replies": [],
}
FACEBOOK_PROFILE = {
    "id": "123456789",
    "username": "facebook",
    "name": "Facebook",
    "url": "https://www.facebook.com/facebook",
    "verified": True,
    "followers": 50000,
}
FACEBOOK_POST = {
    "id": "1525856912919657",
    "url": "https://www.facebook.com/ads/library/?id=1525856912919657",
    "text": "Post text",
    "author": FACEBOOK_PROFILE,
    "stats": {"reactionCount": 1200},
    "media": [{"type": "photo", "url": "https://example.com/photo.jpg"}],
    "hashtags": [],
    "linkUrl": "https://example.com/landing",
    "cta": "SHOP_NOW",
    "active": True,
    "platforms": ["FACEBOOK", "INSTAGRAM"],
}
FACEBOOK_COMMENT = {
    "id": "comment-123",
    "postId": "1525856912919657",
    "text": "Comment text",
    "author": {"name": "Someone"},
    "likes": 3,
    "replies": [{"id": "reply-1"}],
}
INSTAGRAM_PROFILE = {
    "id": "12345",
    "username": "instagram",
    "fullName": "Instagram",
    "verified": True,
    "private": False,
    "followers": 50000,
}
INSTAGRAM_MEDIA = {
    "id": "3234567890123456789",
    "shortcode": "DY79rTVS6OK",
    "url": "https://www.instagram.com/p/DY79rTVS6OK/",
    "caption": "caption text",
    "mediaType": "image",
    "author": INSTAGRAM_PROFILE,
    "stats": {"likeCount": 5000, "commentCount": 120},
    "hashtags": ["ai"],
    "mentions": [],
    "children": [],
}
INSTAGRAM_COMMENT = {
    "id": "1789123456789",
    "mediaId": "DY79rTVS6OK",
    "text": "comment text",
    "author": {"username": "fan"},
    "likes": 42,
}
INSTAGRAM_SEARCH_RESULT = {
    "id": "12345",
    "type": "profile",
    "username": "instagram",
    "title": "Instagram",
    "url": "https://www.instagram.com/instagram/",
    "followers": 50000,
}

# (method, kwargs, HTTP method, path, query params or None, JSON body or None,
#  response body, model, returns a list)
CASES = (
    (
        "tiktok_search",
        {"query": "bittensor", "count": 3, "cursor": CURSOR, "sort": "latest"},
        "POST",
        "/desearch/tiktok/search",
        None,
        {"query": "bittensor", "count": 3, "cursor": CURSOR, "sort": "latest"},
        [TIKTOK_POST],
        TikTokPost,
        True,
    ),
    (
        "tiktok_post_by_id",
        {"id": "7620891413932166433"},
        "GET",
        "/desearch/tiktok/post/7620891413932166433",
        None,
        None,
        TIKTOK_POST,
        TikTokPost,
        False,
    ),
    (
        "tiktok_profile",
        {"username": "tiktok"},
        "GET",
        "/desearch/tiktok/profile/tiktok",
        None,
        None,
        TIKTOK_PROFILE,
        TikTokProfile,
        False,
    ),
    (
        "tiktok_profile_posts",
        {"username": "tiktok", "count": 2, "cursor": CURSOR},
        "GET",
        "/desearch/tiktok/profile/tiktok/posts",
        {"count": 2, "cursor": CURSOR},
        None,
        [TIKTOK_POST],
        TikTokPost,
        True,
    ),
    (
        "tiktok_comments",
        {"video_id": "7620891413932166433", "count": 2, "cursor": CURSOR},
        "GET",
        "/desearch/tiktok/comments/7620891413932166433",
        {"count": 2, "cursor": CURSOR},
        None,
        [TIKTOK_COMMENT],
        TikTokComment,
        True,
    ),
    (
        "tiktok_hashtag",
        {"tag": "ai", "count": 2, "cursor": CURSOR},
        "GET",
        "/desearch/tiktok/hashtag/ai",
        {"count": 2, "cursor": CURSOR},
        None,
        [TIKTOK_POST],
        TikTokPost,
        True,
    ),
    (
        "tiktok_trending",
        {"region": "GB", "count": 2},
        "GET",
        "/desearch/tiktok/trending",
        {"region": "GB", "count": 2},
        None,
        [TIKTOK_POST],
        TikTokPost,
        True,
    ),
    (
        "facebook_search",
        {"query": "running", "count": 3, "cursor": CURSOR},
        "POST",
        "/desearch/facebook/search",
        None,
        {"query": "running", "count": 3, "cursor": CURSOR},
        [FACEBOOK_POST],
        FacebookPost,
        True,
    ),
    (
        "facebook_post_by_id",
        {"id": "1525856912919657"},
        "GET",
        "/desearch/facebook/post/1525856912919657",
        None,
        None,
        FACEBOOK_POST,
        FacebookPost,
        False,
    ),
    (
        "facebook_profile",
        {"profile_id": "facebook"},
        "GET",
        "/desearch/facebook/profile/facebook",
        None,
        None,
        FACEBOOK_PROFILE,
        FacebookProfile,
        False,
    ),
    (
        "facebook_profile_posts",
        {"profile_id": "facebook", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/facebook/profile/facebook/posts",
        {"count": 3, "cursor": CURSOR},
        None,
        [FACEBOOK_POST],
        FacebookPost,
        True,
    ),
    (
        "facebook_comments",
        {"post_id": "1525856912919657", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/facebook/comments/1525856912919657",
        {"count": 3, "cursor": CURSOR},
        None,
        [FACEBOOK_COMMENT],
        FacebookComment,
        True,
    ),
    (
        "facebook_hashtag",
        {"tag": "running", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/facebook/hashtag/running",
        {"count": 3, "cursor": CURSOR},
        None,
        [FACEBOOK_POST],
        FacebookPost,
        True,
    ),
    (
        "instagram_search",
        {"query": "desearch", "count": 3},
        "POST",
        "/desearch/instagram/search",
        None,
        {"query": "desearch", "count": 3},
        [INSTAGRAM_SEARCH_RESULT],
        InstagramSearchResult,
        True,
    ),
    (
        "instagram_media",
        {"id": "DY79rTVS6OK"},
        "GET",
        "/desearch/instagram/media/DY79rTVS6OK",
        None,
        None,
        INSTAGRAM_MEDIA,
        InstagramMedia,
        False,
    ),
    (
        "instagram_profile",
        {"username": "instagram"},
        "GET",
        "/desearch/instagram/profile/instagram",
        None,
        None,
        INSTAGRAM_PROFILE,
        InstagramProfile,
        False,
    ),
    (
        "instagram_profile_posts",
        {"username": "instagram", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/instagram/profile/instagram/posts",
        {"count": 3, "cursor": CURSOR},
        None,
        [INSTAGRAM_MEDIA],
        InstagramMedia,
        True,
    ),
    (
        "instagram_comments",
        {"shortcode": "DY79rTVS6OK", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/instagram/comments/DY79rTVS6OK",
        {"count": 3, "cursor": CURSOR},
        None,
        [INSTAGRAM_COMMENT],
        InstagramComment,
        True,
    ),
    (
        "instagram_hashtag",
        {"tag": "ai", "count": 3, "cursor": CURSOR},
        "GET",
        "/desearch/instagram/hashtag/ai",
        {"count": 3, "cursor": CURSOR},
        None,
        [INSTAGRAM_MEDIA],
        InstagramMedia,
        True,
    ),
)

# Methods whose route takes a path parameter: (method, parameter, route prefix,
# route suffix).
PATH_CASES = (
    ("tiktok_post_by_id", "id", "/desearch/tiktok/post/", ""),
    ("tiktok_profile", "username", "/desearch/tiktok/profile/", ""),
    ("tiktok_profile_posts", "username", "/desearch/tiktok/profile/", "/posts"),
    ("tiktok_comments", "video_id", "/desearch/tiktok/comments/", ""),
    ("tiktok_hashtag", "tag", "/desearch/tiktok/hashtag/", ""),
    ("facebook_post_by_id", "id", "/desearch/facebook/post/", ""),
    ("facebook_profile", "profile_id", "/desearch/facebook/profile/", ""),
    ("facebook_profile_posts", "profile_id", "/desearch/facebook/profile/", "/posts"),
    ("facebook_comments", "post_id", "/desearch/facebook/comments/", ""),
    ("facebook_hashtag", "tag", "/desearch/facebook/hashtag/", ""),
    ("instagram_media", "id", "/desearch/instagram/media/", ""),
    ("instagram_profile", "username", "/desearch/instagram/profile/", ""),
    ("instagram_profile_posts", "username", "/desearch/instagram/profile/", "/posts"),
    ("instagram_comments", "shortcode", "/desearch/instagram/comments/", ""),
    ("instagram_hashtag", "tag", "/desearch/instagram/hashtag/", ""),
)
OBJECT_METHODS = {
    "tiktok_post_by_id",
    "tiktok_profile",
    "facebook_post_by_id",
    "facebook_profile",
    "instagram_media",
    "instagram_profile",
}
PAGINATED_METHODS = [
    case[0] for case in CASES if "cursor" in case[1]
]


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


def _body_for(method_name):
    return [] if method_name not in OBJECT_METHODS else {}


class SocialRequestTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_each_method_builds_its_request_and_parses_the_body(self):
        for name, kwargs, http, path, params, body, response, model, is_list in CASES:
            with self.subTest(method=name):
                client = self.make_client(FakeResponse(json_data=response))
                result = await getattr(client, name)(**kwargs)

                method, url, sent = client.client.requests[0]
                self.assertEqual(method, http)
                self.assertEqual(url, f"https://example.test{path}")
                if params is None:
                    self.assertNotIn("params", sent)
                else:
                    self.assertEqual(sent["params"], params)
                if body is None:
                    self.assertNotIn("json", sent)
                else:
                    self.assertEqual(sent["json"], body)

                self.assertNotIsInstance(result, DesearchResponse)
                if is_list:
                    self.assertIsInstance(result, list)
                    self.assertEqual(len(result), 1)
                    self.assertIsInstance(result[0], model)
                    self.assertEqual(
                        result[0].model_dump(exclude_unset=True), response[0]
                    )
                else:
                    self.assertIsInstance(result, model)
                    self.assertEqual(
                        result.model_dump(exclude_unset=True), response
                    )

    async def test_unset_optional_arguments_are_not_sent(self):
        minimal = {
            "tiktok_search": ({"query": "ai"}, {"json": {"query": "ai"}}),
            "tiktok_profile_posts": ({"username": "tiktok"}, {"params": {}}),
            "tiktok_comments": ({"video_id": "1"}, {"params": {}}),
            "tiktok_hashtag": ({"tag": "ai"}, {"params": {}}),
            "tiktok_trending": ({}, {"params": {}}),
            "facebook_search": ({"query": "ai"}, {"json": {"query": "ai"}}),
            "facebook_profile_posts": ({"profile_id": "facebook"}, {"params": {}}),
            "facebook_comments": ({"post_id": "1"}, {"params": {}}),
            "facebook_hashtag": ({"tag": "ai"}, {"params": {}}),
            "instagram_search": ({"query": "ai"}, {"json": {"query": "ai"}}),
            "instagram_profile_posts": ({"username": "instagram"}, {"params": {}}),
            "instagram_comments": ({"shortcode": "X"}, {"params": {}}),
            "instagram_hashtag": ({"tag": "ai"}, {"params": {}}),
        }
        for name, (kwargs, expected) in minimal.items():
            with self.subTest(method=name):
                client = self.make_client(FakeResponse(json_data=[]))
                result = await getattr(client, name)(**kwargs)
                self.assertEqual(result, [])
                sent = client.client.requests[0][2]
                for key, value in expected.items():
                    self.assertEqual(sent[key], value)

    async def test_path_parameters_are_percent_encoded_as_one_segment(self):
        raw = "https://www.instagram.com/p/DeuOR-CjKE9/?a=b#c d@e"
        encoded = (
            "https%3A%2F%2Fwww.instagram.com%2Fp%2FDeuOR-CjKE9%2F%3Fa%3Db%23c%20d%40e"
        )
        for name, param, prefix, suffix in PATH_CASES:
            with self.subTest(method=name):
                client = self.make_client(FakeResponse(json_data=_body_for(name)))
                await getattr(client, name)(**{param: raw})
                url = client.client.requests[0][1]
                self.assertEqual(
                    url, f"https://example.test{prefix}{encoded}{suffix}"
                )

    async def test_include_metadata_returns_next_cursor_and_cost(self):
        headers = {
            "X-Desearch-Cost-Usd": "0.003",
            "X-Desearch-Usage-Count": "3",
            "X-Desearch-Service": "tiktok",
            "X-Desearch-Currency": "USD",
            "x-desearch-next-cursor": CURSOR,
        }
        for name, kwargs, _http, _path, _p, _b, response, model, is_list in CASES:
            with self.subTest(method=name):
                client = self.make_client(
                    FakeResponse(json_data=response, headers=headers)
                )
                result = await getattr(client, name)(
                    **kwargs, include_metadata=True
                )
                self.assertIsInstance(result, DesearchResponse)
                self.assertIsInstance(result.metadata, DesearchCostMetadata)
                self.assertEqual(result.metadata.next_cursor, CURSOR)
                self.assertEqual(result.metadata.cost_usd, 0.003)
                self.assertEqual(result.metadata.usage_count, 3)
                self.assertEqual(result.metadata.service, "tiktok")
                self.assertEqual(result.metadata.currency, "USD")
                if is_list:
                    self.assertIsInstance(result.data[0], model)
                else:
                    self.assertIsInstance(result.data, model)

    async def test_last_page_has_no_next_cursor(self):
        for headers in ({}, {"x-desearch-next-cursor": ""}):
            with self.subTest(headers=headers):
                client = self.make_client(
                    FakeResponse(json_data=[TIKTOK_POST], headers=headers)
                )
                result = await client.tiktok_hashtag(
                    tag="ai", cursor=CURSOR, include_metadata=True
                )
                self.assertIsNone(result.metadata.next_cursor)
                self.assertIsInstance(result.data[0], TikTokPost)

    async def test_pagination_loop_sends_the_cursor_back_unchanged(self):
        client = self.make_client(
            FakeResponse(
                json_data=[TIKTOK_POST],
                headers={"x-desearch-next-cursor": CURSOR},
            ),
            FakeResponse(json_data=[dict(TIKTOK_POST, id="2")]),
        )
        posts = []
        cursor = None
        while True:
            page = await client.tiktok_profile_posts(
                "tiktok", count=1, cursor=cursor, include_metadata=True
            )
            posts.extend(page.data)
            cursor = page.metadata.next_cursor
            if cursor is None:
                break

        self.assertEqual([post.id for post in posts], [TIKTOK_POST["id"], "2"])
        sent = [request[2]["params"] for request in client.client.requests]
        self.assertEqual(sent, [{"count": 1}, {"count": 1, "cursor": CURSOR}])

    async def test_list_route_returns_a_non_list_body_unchanged(self):
        for name in PAGINATED_METHODS + ["tiktok_trending", "instagram_search"]:
            kwargs = next(case[1] for case in CASES if case[0] == name)
            with self.subTest(method=name):
                client = self.make_client(
                    FakeResponse(json_data={"detail": "provider page unavailable"})
                )
                result = await getattr(client, name)(**kwargs)
                self.assertEqual(result, {"detail": "provider page unavailable"})

    async def test_models_keep_extra_fields_and_default_lists(self):
        client = self.make_client(
            FakeResponse(json_data={"id": "1", "cost_usd": 0.001, "newField": 7})
        )
        post = cast(TikTokPost, await client.tiktok_post_by_id("1"))
        self.assertEqual(post.hashtags, [])
        self.assertEqual(post.mentions, [])
        self.assertIsNone(post.music)
        self.assertEqual(getattr(post, "cost_usd"), 0.001)
        self.assertEqual(getattr(post, "newField"), 7)

    def test_signatures_match_the_routes(self):
        for name in PAGINATED_METHODS:
            with self.subTest(method=name):
                parameters = inspect.signature(getattr(Desearch, name)).parameters
                self.assertIn("cursor", parameters)
                self.assertIsNone(parameters["cursor"].default)
                self.assertIsNone(parameters["count"].default)
                self.assertEqual(
                    parameters["include_metadata"].kind,
                    inspect.Parameter.KEYWORD_ONLY,
                )
        # Instagram search does not paginate (any cursor is a 422) and TikTok
        # trending has no cursor parameter.
        for name in ("instagram_search", "tiktok_trending"):
            with self.subTest(method=name):
                parameters = inspect.signature(getattr(Desearch, name)).parameters
                self.assertNotIn("cursor", parameters)
        self.assertEqual(
            sorted(PAGINATED_METHODS),
            sorted(
                [
                    "tiktok_search",
                    "tiktok_profile_posts",
                    "tiktok_comments",
                    "tiktok_hashtag",
                    "facebook_search",
                    "facebook_profile_posts",
                    "facebook_comments",
                    "facebook_hashtag",
                    "instagram_profile_posts",
                    "instagram_comments",
                    "instagram_hashtag",
                ]
            ),
        )


class LocalServerSocialTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.received: List[Any] = []
        self.next_cursor = None
        self.error = None

        async def handler(request):
            body = None
            if request.method == "POST":
                body = await request.json()
            self.received.append(
                {
                    "method": request.method,
                    "raw_path": request.raw_path.split("?")[0],
                    "path": request.path,
                    "query": list(request.query.items()),
                    "json": body,
                    "authorization": request.headers.get("Authorization"),
                }
            )
            if self.error is not None:
                status, text = self.error
                return web.Response(
                    status=status, text=text, content_type="application/json"
                )
            headers = {}
            if self.next_cursor is not None:
                headers["x-desearch-next-cursor"] = self.next_cursor
            # /desearch/{platform}/{kind}/...: post, media and profile (not
            # profile posts) return one object; every other route a list.
            kind = request.path.split("/")[3]
            if kind in ("post", "media") or (
                kind == "profile" and not request.path.endswith("/posts")
            ):
                return web.json_response({"id": "1"}, headers=headers)
            return web.json_response([{"id": "1", "type": "profile"}], headers=headers)

        app = web.Application()
        app.router.add_route("*", "/{tail:.*}", handler)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        sockets = cast(Any, site._server).sockets
        self.client = Desearch(
            api_key=KEY,
            base_url=f"http://127.0.0.1:{sockets[0].getsockname()[1]}",
        )

    async def asyncTearDown(self):
        await self.client.close()
        await self.runner.cleanup()

    async def test_ids_with_slashes_reach_the_server_as_one_encoded_segment(self):
        media_url = "https://www.instagram.com/p/DeuOR-CjKE9/"
        await self.client.instagram_media(media_url)
        await self.client.tiktok_post_by_id("a/b c")
        await self.client.facebook_comments("123_456/789", count=1)

        self.assertEqual(
            [(r["raw_path"], r["path"]) for r in self.received],
            [
                (
                    "/desearch/instagram/media/"
                    "https:%2F%2Fwww.instagram.com%2Fp%2FDeuOR-CjKE9%2F",
                    f"/desearch/instagram/media/{media_url}",
                ),
                ("/desearch/tiktok/post/a%2Fb%20c", "/desearch/tiktok/post/a/b c"),
                (
                    "/desearch/facebook/comments/123_456%2F789",
                    "/desearch/facebook/comments/123_456/789",
                ),
            ],
        )

    async def test_cursor_and_count_query_values_arrive_unchanged(self):
        cursor = "a+b/c=d&e?f%g"
        self.next_cursor = "next+page/=="
        page = await self.client.instagram_hashtag(
            "ai", count=2, cursor=cursor, include_metadata=True
        )
        self.assertEqual(
            self.received[0]["query"], [("count", "2"), ("cursor", cursor)]
        )
        self.assertEqual(self.received[0]["authorization"], KEY)
        page = cast(DesearchResponse, page)
        self.assertEqual(page.metadata.next_cursor, "next+page/==")
        self.assertIsInstance(page.data[0], InstagramMedia)

    async def test_post_routes_send_the_cursor_in_the_json_body(self):
        await self.client.tiktok_search("bittensor", count=1, cursor=CURSOR)
        await self.client.facebook_search("running", count=1, cursor=CURSOR)
        await self.client.instagram_search("desearch", count=1)
        self.assertEqual(
            [(r["method"], r["path"], r["json"], r["query"]) for r in self.received],
            [
                (
                    "POST",
                    "/desearch/tiktok/search",
                    {"query": "bittensor", "count": 1, "cursor": CURSOR},
                    [],
                ),
                (
                    "POST",
                    "/desearch/facebook/search",
                    {"query": "running", "count": 1, "cursor": CURSOR},
                    [],
                ),
                (
                    "POST",
                    "/desearch/instagram/search",
                    {"query": "desearch", "count": 1},
                    [],
                ),
            ],
        )

    async def test_real_headers_are_read_case_insensitively(self):
        self.next_cursor = CURSOR
        page = cast(
            DesearchResponse,
            await self.client.tiktok_comments("1", include_metadata=True),
        )
        self.assertEqual(page.metadata.next_cursor, CURSOR)

        self.next_cursor = None
        last = cast(
            DesearchResponse,
            await self.client.tiktok_comments(
                "1", cursor=CURSOR, include_metadata=True
            ),
        )
        self.assertIsNone(last.metadata.next_cursor)

    async def test_invalid_cursor_422_raises_desearch_api_error(self):
        body = '{"detail":"Invalid request parameters"}'
        self.error = (422, body)
        with self.assertLogs("desearch_py.api", level="ERROR"):
            with self.assertRaises(DesearchAPIError) as caught:
                await self.client.facebook_hashtag("running", cursor="10")
        error = caught.exception
        self.assertEqual(error.status, 422)
        self.assertEqual(error.body, body)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)

    async def test_http_errors_keep_status_and_redact_the_key(self):
        cases = (
            (404, '{"detail":"Resource not found"}', "instagram_comments", ("123",)),
            (401, '{"detail":"bad key ' + KEY + '"}', "tiktok_profile", ("tiktok",)),
            (500, '{"detail":"Error fetching"}', "facebook_profile", ("facebook",)),
        )
        for status, body, name, args in cases:
            with self.subTest(method=name):
                self.error = (status, body)
                with self.assertLogs("desearch_py.api", level="ERROR") as logs:
                    with self.assertRaises(DesearchAPIError) as caught:
                        await getattr(self.client, name)(*args)
                self.assertNotIn(KEY, "\n".join(logs.output))
                error = caught.exception
                self.assertEqual(error.status, status)
                self.assertEqual(error.body, body.replace(KEY, "[REDACTED]"))
                self.assertNotIn(KEY, str(error))
                self.assertNotIn(KEY, repr(error))
                self.assertIsNone(error.__cause__)


if __name__ == "__main__":
    unittest.main()
