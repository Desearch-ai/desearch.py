"""Network stats methods and the Server-Sent Events decoder behind the stream."""

import asyncio
import json
import unittest
from contextlib import aclosing
from typing import Any, List, cast

import aiohttp
from aiohttp import ClientResponseError, web
from aiohttp.client_reqrep import RequestInfo
from multidict import CIMultiDict, CIMultiDictProxy
from yarl import URL

from desearch_py import (
    Desearch,
    DesearchAPIError,
    DesearchResponse,
    NetworkStatsEvent,
    NetworkStatsHistoryPoint,
    NetworkStatsHistoryResponse,
    NetworkStatsResponse,
)
from desearch_py.api import _ServerSentEventDecoder

KEY = "fake-key-for-network-stats"


def _stats(second: int) -> dict:
    return {
        "total_searchable_pages": 1_024_383_856 + 184 * second,
        "searches_completed_today": 512_895 + 6 * second,
        "urls_crawled_today": 25_484_231 + 296 * second,
        "rates_per_second": {
            "total_searchable_pages": 184,
            "searches_completed_today": 6,
            "urls_crawled_today": 296,
        },
        "started_at": "2026-09-16T07:04:12Z",
        "updated_at": f"2026-10-28T12:00:{second:02d}Z",
        "telemetry_kind": "estimated",
        "methodology": "fixed_rate_projection",
    }


def _sse(event_id: int, data: Any, event: str = "stats") -> str:
    payload = data if isinstance(data, str) else json.dumps(data)
    return f"id: {event_id}\nevent: {event}\ndata: {payload}\n\n"


HISTORY = {
    "window_seconds": 1200,
    "interval_seconds": 1,
    "window_started_at": "2026-10-28T11:40:00Z",
    "window_ended_at": "2026-10-28T12:00:00Z",
    "points": [
        {
            "total_searchable_pages": 1,
            "searches_completed_today": 2,
            "urls_crawled_today": 3,
            "observed_at": "2026-10-28T11:40:00Z",
            "telemetry_kind": "estimated",
            "methodology": "fixed_rate_projection",
        },
        {
            "total_searchable_pages": 4,
            "searches_completed_today": 5,
            "urls_crawled_today": 6,
            "observed_at": "2026-10-28T11:40:01Z",
        },
    ],
}


def _decode(*chunks: bytes) -> List[Any]:
    decoder = _ServerSentEventDecoder()
    events: List[Any] = []
    for chunk in chunks:
        events.extend(decoder.feed(chunk))
    events.extend(decoder.close())
    return [(e.event, e.data, e.id) for e in events]


class ServerSentEventDecoderTests(unittest.TestCase):
    def test_parses_id_event_and_data(self):
        self.assertEqual(
            _decode(b'id: 7\nevent: stats\ndata: {"a": 1}\n\n'),
            [("stats", '{"a": 1}', "7")],
        )

    def test_joins_multiple_data_lines_and_defaults_the_event_type(self):
        self.assertEqual(
            _decode(b"data: first\ndata:second\ndata\n\n"),
            [("message", "first\nsecond\n", None)],
        )

    def test_ignores_comments_retry_and_unknown_fields(self):
        self.assertEqual(
            _decode(b": keepalive\nretry: 1000\nfoo: bar\ndata: x\n\n:\n\n"),
            [("message", "x", None)],
        )

    def test_accepts_crlf_and_cr_line_endings(self):
        self.assertEqual(
            _decode(b"data: a\r\n\r\ndata: b\r\rdata: c\n\n"),
            [("message", "a", None), ("message", "b", None), ("message", "c", None)],
        )

    def test_handles_a_crlf_split_across_chunks(self):
        self.assertEqual(
            _decode(b"data: a\r", b"\n\r", b"\ndata: b\r", b"\r"),
            [("message", "a", None), ("message", "b", None)],
        )

    def test_handles_any_chunking_of_the_same_stream(self):
        stream = (
            "\ufeffid: 1\r\nevent: stats\r\ndata: caf\u00e9\r\n\r\n"
            ": ping\n\nid: 2\nevent: stats\ndata: two\n\n"
        ).encode("utf-8")
        expected = [("stats", "caf\u00e9", "1"), ("stats", "two", "2")]
        for size in range(1, len(stream) + 1):
            with self.subTest(chunk_size=size):
                chunks = [stream[i : i + size] for i in range(0, len(stream), size)]
                self.assertEqual(_decode(*chunks), expected)

    def test_drops_events_without_data_and_keeps_the_last_id(self):
        self.assertEqual(
            _decode(b"id: 5\nevent: stats\n\nevent: stats\ndata: x\n\n"),
            [("stats", "x", "5")],
        )

    def test_ignores_an_id_containing_nul(self):
        self.assertEqual(
            _decode(b"id: 1\ndata: a\n\nid: 2\x00\ndata: b\n\n"),
            [("message", "a", "1"), ("message", "b", "1")],
        )

    def test_keeps_only_one_leading_space_and_colons_in_the_value(self):
        self.assertEqual(
            _decode(b"data:  two spaces: and a colon\n\n"),
            [("message", " two spaces: and a colon", None)],
        )

    def test_discards_an_unfinished_event_at_end_of_stream(self):
        self.assertEqual(_decode(b"data: done\n\ndata: partial\n"), [
            ("message", "done", None)
        ])
        self.assertEqual(_decode(b"data: no newline"), [])

    def test_event_type_resets_after_each_event(self):
        self.assertEqual(
            _decode(b"event: other\ndata: a\n\ndata: b\n\n"),
            [("other", "a", None), ("message", "b", None)],
        )


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


class _ChunkReader:
    def __init__(self, chunks):
        self._chunks = list(chunks)

    async def iter_any(self):
        for chunk in self._chunks:
            yield chunk


class FakeStreamResponse(FakeResponse):
    def __init__(self, chunks):
        super().__init__()
        self.content = _ChunkReader(chunks)


class _LeakResponse(FakeResponse):
    """Response with no status, so the client calls raise_for_status()."""

    def raise_for_status(self):
        headers = CIMultiDictProxy(CIMultiDict({"Authorization": KEY}))
        info = RequestInfo(
            url=URL("http://example.test/network/stats/stream"),
            method="GET",
            headers=headers,
            real_url=URL("http://example.test/network/stats/stream"),
        )
        raise ClientResponseError(
            info, (), status=403, message="Forbidden", headers=headers
        )


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


class NetworkStatsTests(unittest.IsolatedAsyncioTestCase):
    def make_client(self, *responses):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(responses)
        return client

    async def test_network_stats_returns_the_current_counters(self):
        client = self.make_client(FakeResponse(json_data=_stats(0)))

        stats = await client.network_stats()

        self.assertEqual(
            client.client.requests[0][0:2],
            ("GET", "https://example.test/network/stats"),
        )
        self.assertNotIn("params", client.client.requests[0][2])
        self.assertIsInstance(stats, NetworkStatsResponse)
        stats = cast(NetworkStatsResponse, stats)
        self.assertEqual(stats.total_searchable_pages, 1_024_383_856)
        self.assertEqual(stats.rates_per_second.urls_crawled_today, 296)
        self.assertEqual(stats.telemetry_kind, "estimated")
        self.assertEqual(stats.methodology, "fixed_rate_projection")

    async def test_network_stats_history_returns_the_timeline(self):
        client = self.make_client(FakeResponse(json_data=HISTORY))

        history = await client.network_stats_history()

        self.assertEqual(
            client.client.requests[0][0:2],
            ("GET", "https://example.test/network/stats/history"),
        )
        self.assertIsInstance(history, NetworkStatsHistoryResponse)
        history = cast(NetworkStatsHistoryResponse, history)
        self.assertEqual(history.window_seconds, 1200)
        self.assertEqual(len(history.points), 2)
        self.assertIsInstance(history.points[1], NetworkStatsHistoryPoint)
        self.assertEqual(history.points[1].telemetry_kind, "estimated")

    async def test_network_stats_support_include_metadata(self):
        client = self.make_client(
            FakeResponse(json_data=_stats(0)), FakeResponse(json_data=HISTORY)
        )
        stats = await client.network_stats(include_metadata=True)
        history = await client.network_stats_history(include_metadata=True)
        self.assertIsInstance(stats, DesearchResponse)
        self.assertIsInstance(cast(DesearchResponse, stats).data, NetworkStatsResponse)
        self.assertIsNone(cast(DesearchResponse, stats).metadata.cost_usd)
        self.assertIsInstance(
            cast(DesearchResponse, history).data, NetworkStatsHistoryResponse
        )

    async def test_stream_sends_sse_headers_and_a_long_lived_timeout(self):
        client = self.make_client(
            FakeStreamResponse([_sse(1, _stats(1)).encode()]),
            FakeStreamResponse([]),
        )

        events = [event async for event in client.stream_network_stats()]
        resumed = [
            event async for event in client.stream_network_stats(last_event_id=1)
        ]

        self.assertEqual(len(events), 1)
        self.assertEqual(resumed, [])
        method, url, kwargs = client.client.requests[0]
        self.assertEqual((method, url), ("GET", "https://example.test/network/stats/stream"))
        self.assertEqual(
            kwargs["headers"],
            {"Accept": "text/event-stream", "Cache-Control": "no-cache"},
        )
        timeout = kwargs["timeout"]
        self.assertIsInstance(timeout, aiohttp.ClientTimeout)
        self.assertIsNone(timeout.total)
        self.assertEqual(timeout.sock_read, 60)
        self.assertEqual(
            client.client.requests[1][2]["headers"]["Last-Event-ID"], "1"
        )

    async def test_stream_yields_parsed_stats_events_only(self):
        body = (
            ": connected\n\n"
            + _sse(100, _stats(0))
            + _sse(101, {"unexpected": True}, event="notice")
            + _sse(102, "not json")
            + _sse(103, _stats(3))
        ).encode()
        # Split the body at awkward places, including inside a JSON payload.
        chunks = [body[:7], body[7:150], body[150:151], body[151:]]
        client = self.make_client(FakeStreamResponse(chunks))

        with self.assertLogs("desearch_py.api", level="WARNING") as logs:
            events = [event async for event in client.stream_network_stats()]

        self.assertEqual([event.id for event in events], ["100", "103"])
        for event in events:
            self.assertIsInstance(event, NetworkStatsEvent)
            self.assertEqual(event.event, "stats")
            self.assertIsInstance(event.data, NetworkStatsResponse)
        self.assertEqual(events[1].data.updated_at, "2026-10-28T12:00:03Z")
        self.assertIn("102", "\n".join(logs.output))

    async def test_stream_client_response_error_is_not_chained(self):
        client = Desearch(api_key=KEY, base_url="https://example.test")
        client.client = FakeSession([_LeakResponse()])

        with self.assertLogs("desearch_py.api", level="ERROR"):
            with self.assertRaises(DesearchAPIError) as caught:
                async for _event in client.stream_network_stats():
                    pass

        error = caught.exception
        self.assertEqual(error.status, 403)
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(KEY, repr(error))


class LocalServerStreamTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests: List[Any] = []
        self.stream_error = None

        async def stats(request):
            self.requests.append((request.path, dict(request.headers)))
            return web.json_response(_stats(0))

        async def history(request):
            self.requests.append((request.path, dict(request.headers)))
            return web.json_response(HISTORY)

        async def stream(request):
            self.requests.append((request.path, dict(request.headers)))
            if self.stream_error is not None:
                status, text = self.stream_error
                return web.Response(
                    status=status, text=text, content_type="application/json"
                )
            response = web.StreamResponse(
                headers={"Content-Type": "text/event-stream", "Cache-Control": "no-cache"}
            )
            await response.prepare(request)
            start = int(request.headers.get("Last-Event-ID", "0")) + 1
            try:
                for event_id in range(start, start + 5):
                    payload = _sse(event_id, _stats(event_id % 60)).encode()
                    # Two writes per event so the client sees partial events.
                    await response.write(payload[:20])
                    await asyncio.sleep(0)
                    await response.write(payload[20:])
                await response.write_eof()
            except ConnectionResetError:
                # The client stopped reading early (test_aclosing_...).
                pass
            return response

        app = web.Application()
        app.router.add_get("/network/stats", stats)
        app.router.add_get("/network/stats/history", history)
        app.router.add_get("/network/stats/stream", stream)
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

    async def test_stream_reads_every_event_until_the_server_closes(self):
        events = [event async for event in self.client.stream_network_stats()]

        self.assertEqual([event.id for event in events], ["1", "2", "3", "4", "5"])
        self.assertEqual(events[0].data.total_searchable_pages, 1_024_383_856 + 184)
        path, headers = self.requests[0]
        self.assertEqual(path, "/network/stats/stream")
        self.assertEqual(headers["Accept"], "text/event-stream")
        self.assertNotIn("Last-Event-ID", headers)

    async def test_resume_sends_last_event_id(self):
        events = [
            event async for event in self.client.stream_network_stats(last_event_id=41)
        ]
        self.assertEqual(events[0].id, "42")
        self.assertEqual(self.requests[0][1]["Last-Event-ID"], "41")

    async def test_aclosing_stops_the_stream_early(self):
        received = []
        async with aclosing(self.client.stream_network_stats()) as events:
            async for event in events:
                received.append(event.id)
                if len(received) == 2:
                    break
        self.assertEqual(received, ["1", "2"])
        with self.assertRaises(StopAsyncIteration):
            await events.__anext__()

    async def test_stream_http_error_raises_desearch_api_error(self):
        self.stream_error = (503, '{"detail":"unavailable ' + KEY + '"}')
        with self.assertLogs("desearch_py.api", level="ERROR") as logs:
            with self.assertRaises(DesearchAPIError) as caught:
                async for _event in self.client.stream_network_stats():
                    pass
        error = caught.exception
        self.assertEqual(error.status, 503)
        self.assertEqual(error.body, '{"detail":"unavailable [REDACTED]"}')
        self.assertIsNone(error.__cause__)
        self.assertIsNone(error.__context__)
        self.assertNotIn(KEY, "\n".join(logs.output))

    async def test_json_routes_send_real_requests(self):
        stats = await self.client.network_stats()
        history = await self.client.network_stats_history()
        self.assertIsInstance(stats, NetworkStatsResponse)
        self.assertIsInstance(history, NetworkStatsHistoryResponse)
        self.assertEqual(
            [path for path, _headers in self.requests],
            ["/network/stats", "/network/stats/history"],
        )

    async def test_public_routes_work_without_an_api_key(self):
        client = Desearch(api_key="", base_url=self.client.base_url)
        try:
            stats = await client.network_stats()
            events = [event async for event in client.stream_network_stats()]
        finally:
            await client.close()
        self.assertIsInstance(stats, NetworkStatsResponse)
        self.assertEqual(len(events), 5)


if __name__ == "__main__":
    unittest.main()
