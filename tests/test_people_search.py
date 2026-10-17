import json
import unittest

from aiohttp import web
from pydantic import ValidationError

from desearch_py import (
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    PeopleChannel,
    PeopleExportFormat,
    PeoplePlatform,
    PeopleProfileSort,
    PeopleProfilesPage,
    PeopleResultFilters,
    PeopleResultsPage,
    PeopleTask,
    PeopleTaskConflictError,
    PeopleTaskList,
    PeopleTaskStatus,
    PeopleTaskTimeoutError,
    Person,
    TikTokCreatorSearchFilters,
    XProfileSearchFilters,
    YouTubeCreatorSearchFilters,
)

TASK_ID = "6f1c2a8e-3b7d-4c55-9a43-2f6c0e1d9b10"


def _task(status="queued", **extra):
    task = {
        "task_id": TASK_ID,
        "search_type": "tiktok_creator_search",
        "platform": "tiktok",
        "status": status,
        "stage": None,
        "query": "Skincare creators who review sunscreen",
        "count": 25,
        "result_count": 0,
        "interpreted": None,
        "progress": {},
        "errors": [],
        "reserved_cost_usd": 1.25,
        "final_cost_usd": None,
        "refunded_usd": None,
        "created_by": {"user_id": None, "api_key_id": None, "via": "api_key"},
        "created_at": "2026-10-17T10:00:00+00:00",
        "links": {
            "self": f"/desearch/people/tasks/{TASK_ID}",
            "results": f"/desearch/people/tasks/{TASK_ID}/results",
            "export": f"/desearch/people/tasks/{TASK_ID}/export",
        },
    }
    task.update(extra)
    return task


def _person(handle, platform="tiktok", **extra):
    person = {
        "id": f"{platform}:{handle}",
        "platform": platform,
        "handle": handle,
        "url": f"https://www.tiktok.com/@{handle}",
        "name": handle.title(),
        "bio": "Skincare reviews",
        "location": "US",
        "metrics": {"followers": 54000, "likes": 900000},
        "attributes": {"verified": True, "region": "US"},
        "links": [{"type": "instagram", "url": f"https://instagram.com/{handle}"}],
        "contacts": [{"type": "email", "value": f"{handle}@example.com"}],
        "evidence": [
            {
                "type": "video",
                "url": f"https://www.tiktok.com/@{handle}/video/1",
                "text": "SPF 50 review",
                "metrics": {"views": 4200},
            }
        ],
        "score": {
            "value": 81,
            "qualified": True,
            "summary": "Reviews sunscreen weekly",
            "matched_signals": ["reviews sunscreen"],
            "reasons": ["Posts SPF reviews"],
            "concerns": [],
        },
    }
    person.update(extra)
    return person


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


class PeopleSearchCreateTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_each_search_posts_its_route_and_returns_a_task(self):
        cases = (
            ("x_profile_search", "x"),
            ("youtube_creator_search", "youtube"),
            ("linkedin_profile_search", "linkedin"),
            ("tiktok_creator_search", "tiktok"),
        )
        for method_name, platform in cases:
            with self.subTest(method=method_name):
                client = self.make_client(
                    FakeResponse(json_data=_task(platform=platform))
                )
                task = await getattr(client, method_name)(query="who I want")
                self.assertIsInstance(task, PeopleTask)
                self.assertEqual(task.task_id, TASK_ID)
                self.assertEqual(task.status, PeopleTaskStatus.QUEUED)
                self.assertFalse(task.is_finished)
                self.assertEqual(
                    task.links.results, f"/desearch/people/tasks/{TASK_ID}/results"
                )
                method, url, kwargs = client.client.requests[0]
                self.assertEqual(method, "POST")
                self.assertEqual(
                    url, f"https://example.test/desearch/people/search/{platform}"
                )
                self.assertEqual(kwargs["json"], {"query": "who I want"})
                self.assertNotIn("headers", kwargs)

    async def test_search_body_sends_only_given_fields_and_typed_filters(self):
        client = self.make_client(FakeResponse(json_data=_task(platform="x")))
        await client.x_profile_search(
            query="Indie hackers who share their MRR",
            count=30,
            min_score=60,
            exclude=["@already_contacted"],
            filters=XProfileSearchFilters(min_followers=200, countries=["US", "GB"]),
        )
        self.assertEqual(
            client.client.requests[0][2]["json"],
            {
                "query": "Indie hackers who share their MRR",
                "count": 30,
                "min_score": 60,
                "exclude": ["@already_contacted"],
                "filters": {"min_followers": 200, "countries": ["US", "GB"]},
            },
        )

    async def test_search_filters_accept_a_dict(self):
        client = self.make_client(FakeResponse(json_data=_task(platform="youtube")))
        await client.youtube_creator_search(
            query="Home espresso machine reviews",
            filters={"min_subscribers": 10000, "require_contact": True},
        )
        self.assertEqual(
            client.client.requests[0][2]["json"]["filters"],
            {"min_subscribers": 10000, "require_contact": True},
        )

    async def test_tiktok_typed_filters(self):
        client = self.make_client(FakeResponse(json_data=_task()))
        await client.tiktok_creator_search(
            query="Skincare creators who review sunscreen",
            count=25,
            filters=TikTokCreatorSearchFilters(
                min_followers=10000, require_contact=True
            ),
        )
        self.assertEqual(
            client.client.requests[0][2]["json"]["filters"],
            {"min_followers": 10000, "require_contact": True},
        )

    async def test_filters_for_another_platform_are_rejected_before_sending(self):
        client = self.make_client()
        with self.assertRaises(ValidationError):
            await client.x_profile_search(
                query="who I want",
                filters=YouTubeCreatorSearchFilters(min_subscribers=10),
            )
        self.assertEqual(client.client.requests, [])

    async def test_idempotency_key_is_sent_as_a_header(self):
        client = self.make_client(FakeResponse(json_data=_task(), status=200))
        task = await client.tiktok_creator_search(
            query="Skincare creators", idempotency_key="run-42"
        )
        self.assertEqual(task.task_id, TASK_ID)
        self.assertEqual(
            client.client.requests[0][2]["headers"], {"Idempotency-Key": "run-42"}
        )

    async def test_include_metadata_returns_the_reservation_cost(self):
        headers = {
            "X-Desearch-Cost-Usd": "1.25",
            "X-Desearch-Usage-Count": "25",
            "X-Desearch-Currency": "USD",
        }
        client = self.make_client(
            FakeResponse(
                json_data=_task(cost_usd=1.25, usage_count=25),
                headers=headers,
                status=202,
            )
        )
        response = await client.tiktok_creator_search(
            query="Skincare creators", include_metadata=True
        )
        self.assertIsInstance(response, DesearchResponse)
        self.assertIsInstance(response.data, PeopleTask)
        self.assertEqual(response.data.cost_usd, 1.25)
        self.assertEqual(response.data.usage_count, 25)
        self.assertEqual(response.metadata.cost_usd, 1.25)
        self.assertEqual(response.metadata.usage_count, 25)

    async def test_create_errors_raise_desearch_api_error(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "People Search needs account credits."},
                status=402,
                reason="Payment Required",
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.x_profile_search(query="who I want")
        self.assertNotIsInstance(caught.exception, PeopleTaskConflictError)
        self.assertEqual(caught.exception.status, 402)
        self.assertIn("account credits", caught.exception.body)
        self.assertIsNone(caught.exception.__context__)


class PeopleTaskRouteTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_list_tasks_joins_statuses_and_parses_the_page(self):
        client = self.make_client(
            FakeResponse(json_data={"tasks": [_task("running")], "next_cursor": "abc"})
        )
        page = await client.list_people_tasks(
            platform=PeoplePlatform.TIKTOK,
            status=[PeopleTaskStatus.RUNNING, "paused"],
            limit=10,
            cursor="prev",
        )
        self.assertIsInstance(page, PeopleTaskList)
        self.assertEqual(page.tasks[0].status, "running")
        self.assertEqual(page.next_cursor, "abc")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url), ("GET", "https://example.test/desearch/people/tasks")
        )
        self.assertEqual(
            kwargs["params"],
            {
                "platform": "tiktok",
                "status": "running,paused",
                "limit": 10,
                "cursor": "prev",
            },
        )

    async def test_list_tasks_without_arguments_sends_no_params(self):
        client = self.make_client(
            FakeResponse(json_data={"tasks": [], "next_cursor": None})
        )
        page = await client.list_people_tasks(status="running,paused")
        self.assertEqual(page.tasks, [])
        self.assertEqual(
            client.client.requests[0][2]["params"], {"status": "running,paused"}
        )

    async def test_get_task(self):
        client = self.make_client(
            FakeResponse(
                json_data=_task(
                    "completed", result_count=12, final_cost_usd=0.6, refunded_usd=0.65
                )
            )
        )
        task = await client.get_people_task(TASK_ID)
        self.assertTrue(task.is_finished)
        self.assertEqual(task.final_cost_usd, 0.6)
        self.assertEqual(
            client.client.requests[0][0:2],
            ("GET", f"https://example.test/desearch/people/tasks/{TASK_ID}"),
        )

    async def test_task_id_is_quoted_into_the_path(self):
        client = self.make_client(FakeResponse(json_data=_task()))
        await client.get_people_task("../billing?x=1")
        self.assertEqual(
            client.client.requests[0][1],
            "https://example.test/desearch/people/tasks/..%2Fbilling%3Fx%3D1",
        )

    async def test_get_results_page(self):
        client = self.make_client(
            FakeResponse(
                json_data={
                    "task_id": TASK_ID,
                    "status": "running",
                    "results": [_person("glowlab")],
                    "next_cursor": "1",
                    "has_more": False,
                }
            )
        )
        page = await client.get_people_results(TASK_ID, cursor="0", limit=50)
        self.assertIsInstance(page, PeopleResultsPage)
        person = page.results[0]
        self.assertIsInstance(person, Person)
        self.assertEqual(person.handle, "glowlab")
        self.assertEqual(person.score.value, 81)
        self.assertEqual(person.attributes["verified"], True)
        self.assertEqual(person.contacts[0]["value"], "glowlab@example.com")
        self.assertEqual(person.evidence[0].metrics, {"views": 4200})
        self.assertEqual(page.next_cursor, "1")
        self.assertFalse(page.has_more)
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url),
            ("GET", f"https://example.test/desearch/people/tasks/{TASK_ID}/results"),
        )
        self.assertEqual(kwargs["params"], {"cursor": "0", "limit": 50})

    async def test_expired_results_raise_410(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "Results expired"}, status=410, reason="Gone"
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.get_people_results(TASK_ID)
        self.assertEqual(caught.exception.status, 410)

    async def test_pause_resume_cancel_post_their_routes(self):
        for action, status in (
            ("pause", "paused"),
            ("resume", "queued"),
            ("cancel", "cancelled"),
        ):
            with self.subTest(action=action):
                client = self.make_client(FakeResponse(json_data=_task(status)))
                task = await getattr(client, f"{action}_people_task")(TASK_ID)
                self.assertEqual(task.status, status)
                self.assertEqual(
                    client.client.requests[0][0:2],
                    (
                        "POST",
                        f"https://example.test/desearch/people/tasks/{TASK_ID}/{action}",
                    ),
                )

    async def test_conflict_raises_with_the_current_task(self):
        body = {
            "detail": "Only paused searches can be resumed.",
            "task": _task("cancelled"),
        }
        client = self.make_client(
            FakeResponse(json_data=body, status=409, reason="Conflict")
        )
        with self.assertRaises(PeopleTaskConflictError) as caught:
            await client.resume_people_task(TASK_ID)
        error = caught.exception
        self.assertIsInstance(error, DesearchAPIError)
        self.assertEqual(error.status, 409)
        self.assertEqual(error.message, "Conflict")
        self.assertEqual(error.detail, "Only paused searches can be resumed.")
        self.assertIsInstance(error.task, PeopleTask)
        self.assertEqual(error.task.status, "cancelled")
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertIn("409", str(error))

    async def test_conflict_with_an_unreadable_body_keeps_task_none(self):
        client = self.make_client(
            FakeResponse(text_data="not json", status=409, reason="Conflict")
        )
        with self.assertRaises(PeopleTaskConflictError) as caught:
            await client.cancel_people_task(TASK_ID)
        self.assertIsNone(caught.exception.task)
        self.assertEqual(caught.exception.detail, "")
        self.assertEqual(caught.exception.body, "not json")

    async def test_other_control_errors_are_plain_api_errors(self):
        client = self.make_client(
            FakeResponse(
                json_data={"detail": "Task not found"}, status=404, reason="Not Found"
            )
        )
        with self.assertRaises(DesearchAPIError) as caught:
            await client.pause_people_task(TASK_ID)
        self.assertNotIsInstance(caught.exception, PeopleTaskConflictError)
        self.assertEqual(caught.exception.status, 404)


class PeopleExportAndProfileTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_export_results_sends_format_and_keyword_filters(self):
        client = self.make_client(
            FakeResponse(text_data="handle,name\nglowlab,Glowlab\n")
        )
        csv_text = await client.export_people_results(
            TASK_ID,
            has=["email", PeopleChannel.INSTAGRAM],
            min_audience=1000,
            max_audience=500000,
            min_score=70,
            location="united states",
            verified=True,
        )
        self.assertEqual(csv_text, "handle,name\nglowlab,Glowlab\n")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url),
            ("GET", f"https://example.test/desearch/people/tasks/{TASK_ID}/export"),
        )
        self.assertEqual(
            kwargs["params"],
            {
                "format": "csv",
                "has": "email,instagram",
                "min_audience": 1000,
                "max_audience": 500000,
                "min_score": 70,
                "location": "united states",
                "verified": "true",
            },
        )

    async def test_export_results_merges_a_filters_object_with_keywords(self):
        client = self.make_client(FakeResponse(text_data='{"handle": "glowlab"}\n'))
        await client.export_people_results(
            TASK_ID,
            format=PeopleExportFormat.JSONL,
            filters=PeopleResultFilters(has="email,website", min_score=50),
            min_score=80,
        )
        self.assertEqual(
            client.client.requests[0][2]["params"],
            {"format": "jsonl", "has": "email,website", "min_score": 80},
        )

    async def test_export_results_accepts_a_filters_dict_and_metadata(self):
        client = self.make_client(
            FakeResponse(text_data="handle\n", headers={"X-Desearch-Cost-Usd": "0"})
        )
        response = await client.export_people_results(
            TASK_ID,
            filters={"has": ["email"], "verified": False},
            include_metadata=True,
        )
        self.assertIsInstance(response, DesearchResponse)
        self.assertEqual(response.data, "handle\n")
        self.assertEqual(response.metadata.cost_usd, 0.0)
        self.assertEqual(
            client.client.requests[0][2]["params"],
            {"format": "csv", "has": "email", "verified": "false"},
        )

    async def test_list_profiles(self):
        profile = _person(
            "glowlab",
            found_by={
                "task_id": TASK_ID,
                "query": "Skincare creators",
                "found_at": "2026-10-17T10:05:00+00:00",
                "times_found": 2,
            },
        )
        client = self.make_client(
            FakeResponse(
                json_data={"profiles": [profile], "total": 31, "next_cursor": "50"}
            )
        )
        page = await client.list_people_profiles(
            PeoplePlatform.TIKTOK,
            q="sunscreen",
            sort=PeopleProfileSort.AUDIENCE,
            limit=50,
            cursor="0",
            has="email",
            min_audience=10000,
        )
        self.assertIsInstance(page, PeopleProfilesPage)
        self.assertEqual(page.total, 31)
        self.assertEqual(page.next_cursor, "50")
        self.assertEqual(page.profiles[0].found_by.times_found, 2)
        self.assertEqual(page.profiles[0].handle, "glowlab")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url), ("GET", "https://example.test/desearch/people/profiles")
        )
        self.assertEqual(
            kwargs["params"],
            {
                "platform": "tiktok",
                "q": "sunscreen",
                "sort": "audience",
                "limit": 50,
                "cursor": "0",
                "has": "email",
                "min_audience": 10000,
            },
        )

    async def test_export_profiles(self):
        client = self.make_client(FakeResponse(text_data="handle,found_by_search\n"))
        csv_text = await client.export_people_profiles(
            "x", q="founder", sort="score", filters={"verified": True}
        )
        self.assertEqual(csv_text, "handle,found_by_search\n")
        method, url, kwargs = client.client.requests[0]
        self.assertEqual(
            (method, url),
            ("GET", "https://example.test/desearch/people/profiles/export"),
        )
        self.assertEqual(
            kwargs["params"],
            {
                "platform": "x",
                "format": "csv",
                "q": "founder",
                "sort": "score",
                "verified": "true",
            },
        )


class PeopleHelperTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_wait_polls_until_the_task_ends(self):
        client = self.make_client(
            FakeResponse(json_data=_task("queued")),
            FakeResponse(json_data=_task("running", result_count=3)),
            FakeResponse(json_data=_task("partial", result_count=7)),
        )
        task = await client.wait_for_people_task(TASK_ID, poll_interval=0)
        self.assertEqual(task.status, "partial")
        self.assertEqual(task.result_count, 7)
        self.assertEqual(len(client.client.requests), 3)
        for method, url, _ in client.client.requests:
            self.assertEqual(
                (method, url),
                ("GET", f"https://example.test/desearch/people/tasks/{TASK_ID}"),
            )

    async def test_wait_returns_at_once_for_an_ended_task(self):
        client = self.make_client(FakeResponse(json_data=_task("cancelled")))
        task = await client.wait_for_people_task(TASK_ID, timeout=0)
        self.assertEqual(task.status, "cancelled")
        self.assertEqual(len(client.client.requests), 1)

    async def test_wait_raises_on_timeout_with_the_last_task(self):
        client = self.make_client(FakeResponse(json_data=_task("paused")))
        with self.assertRaises(PeopleTaskTimeoutError) as caught:
            await client.wait_for_people_task(TASK_ID, poll_interval=0, timeout=0)
        self.assertIsInstance(caught.exception, TimeoutError)
        self.assertEqual(caught.exception.task.status, "paused")
        self.assertIn(TASK_ID, str(caught.exception))
        self.assertEqual(len(client.client.requests), 1)

    async def test_iter_results_follows_cursors(self):
        def page(people, cursor, has_more):
            return FakeResponse(
                json_data={
                    "task_id": TASK_ID,
                    "status": "completed",
                    "results": people,
                    "next_cursor": cursor,
                    "has_more": has_more,
                }
            )

        client = self.make_client(
            page([_person("a"), _person("b")], "2", True),
            page([_person("c")], "3", False),
        )
        handles = [
            person.handle
            async for person in client.iter_people_results(TASK_ID, page_size=2)
        ]
        self.assertEqual(handles, ["a", "b", "c"])
        self.assertEqual(
            [kwargs["params"] for _, _, kwargs in client.client.requests],
            [{"limit": 2}, {"cursor": "2", "limit": 2}],
        )

    async def test_iter_results_stops_on_an_empty_page(self):
        client = self.make_client(
            FakeResponse(
                json_data={
                    "task_id": TASK_ID,
                    "status": "running",
                    "results": [],
                    "next_cursor": "5",
                    "has_more": True,
                }
            )
        )
        people = [
            person async for person in client.iter_people_results(TASK_ID, cursor="5")
        ]
        self.assertEqual(people, [])
        self.assertEqual(
            client.client.requests[0][2]["params"], {"cursor": "5", "limit": 100}
        )

    def test_result_filters_to_params(self):
        filters = PeopleResultFilters(
            has=[PeopleChannel.EMAIL, "website, x", "email"],
            max_audience=0,
            verified=True,
        )
        self.assertEqual(filters.has, ["email", "website", "x"])
        self.assertEqual(
            filters.to_params(),
            {"has": "email,website,x", "max_audience": 0, "verified": "true"},
        )
        self.assertEqual(PeopleResultFilters(has=[]).to_params(), {})
        self.assertEqual(PeopleResultFilters().to_params(), {})


KEY = "fake-key-for-people-tests"


class PeopleSearchHttpTests(unittest.IsolatedAsyncioTestCase):
    """Runs the client against a local aiohttp server to check real query strings."""

    async def asyncSetUp(self):
        self.seen = []

        async def handler(request):
            self.seen.append(
                {
                    "method": request.method,
                    "path": request.path,
                    "query": request.query_string,
                    "authorization": request.headers.get("Authorization"),
                    "idempotency_key": request.headers.get("Idempotency-Key"),
                    "body": await request.text(),
                }
            )
            path = request.path
            if path.endswith("/export"):
                return web.Response(
                    text="handle,email\nglowlab,glowlab@example.com\n",
                    content_type="text/csv",
                )
            if path.endswith("/resume"):
                body = {
                    "detail": "Only paused searches can be resumed. " + KEY,
                    "task": _task("cancelled"),
                }
                return web.json_response(body, status=409)
            if path.endswith("/forbidden"):
                return web.json_response({"detail": "forbidden " + KEY}, status=403)
            if path.startswith("/desearch/people/search/"):
                return web.json_response(_task(), status=202)
            return web.json_response({"profiles": [], "total": 0, "next_cursor": None})

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

    async def test_search_sends_body_auth_and_idempotency_key(self):
        task = await self.client.tiktok_creator_search(
            query="Skincare creators who review sunscreen",
            count=10,
            filters={"require_contact": True},
            idempotency_key="run-1",
        )
        self.assertEqual(task.task_id, TASK_ID)
        seen = self.seen[0]
        self.assertEqual(
            (seen["method"], seen["path"]), ("POST", "/desearch/people/search/tiktok")
        )
        self.assertEqual(seen["authorization"], KEY)
        self.assertEqual(seen["idempotency_key"], "run-1")
        self.assertEqual(
            json.loads(seen["body"]),
            {
                "query": "Skincare creators who review sunscreen",
                "count": 10,
                "filters": {"require_contact": True},
            },
        )

    async def test_filters_reach_the_server_as_query_params(self):
        csv_text = await self.client.export_people_results(
            TASK_ID, has=["email", "instagram"], verified=True, min_score=60
        )
        self.assertIn("glowlab@example.com", csv_text)
        await self.client.list_people_profiles("tiktok", has="email", verified=False)
        self.assertEqual(
            self.seen[0]["query"],
            "format=csv&has=email,instagram&min_score=60&verified=true",
        )
        self.assertEqual(
            self.seen[1]["query"], "platform=tiktok&has=email&verified=false"
        )
        self.assertIsNone(self.seen[0]["idempotency_key"])

    async def test_conflict_over_http_is_parsed_and_redacted(self):
        with self.assertRaises(PeopleTaskConflictError) as caught:
            await self.client.resume_people_task(TASK_ID)
        error = caught.exception
        self.assertEqual(error.status, 409)
        self.assertEqual(error.task.status, "cancelled")
        self.assertEqual(
            error.detail, "Only paused searches can be resumed. [REDACTED]"
        )
        self.assertNotIn(KEY, error.body)
        self.assertNotIn(KEY, repr(error))
        self.assertIsNone(error.__context__)

    async def test_http_errors_do_not_leak_the_api_key(self):
        with self.assertRaises(DesearchAPIError) as caught:
            await self.client.get_people_task("forbidden")
        error = caught.exception
        self.assertEqual(error.status, 403)
        self.assertNotIn(KEY, str(error))
        self.assertNotIn(KEY, repr(error))
        self.assertIn("[REDACTED]", error.body)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)


if __name__ == "__main__":
    unittest.main()
