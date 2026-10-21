import inspect
import json
import unittest
from pathlib import Path

from desearch_py import Desearch, ResponseData, Tool, WebSearchResponse, WebTool


FORBIDDEN = "you" + "tube"


class FakeResponse:
    def __init__(self, *, json_data=None):
        self._json_data = json_data if json_data is not None else {}
        self.headers = {}

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


def _values(enum_cls):
    return {member.value for member in enum_cls}


class AiSearchToolTests(unittest.IsolatedAsyncioTestCase):
    def test_allowed_tool_sets_exclude_youtube(self):
        tool_values = _values(Tool)
        web_tool_values = _values(WebTool)

        self.assertEqual(
            tool_values,
            {"web", "hackernews", "reddit", "wikipedia", "twitter", "arxiv"},
        )
        self.assertEqual(
            web_tool_values,
            {"web", "hackernews", "reddit", "wikipedia", "arxiv"},
        )
        self.assertNotIn(FORBIDDEN, tool_values)
        self.assertNotIn(FORBIDDEN, web_tool_values)
        for name in list(Tool.__members__) + list(WebTool.__members__):
            self.assertNotIn(FORBIDDEN, name.lower())

    def test_response_models_omit_youtube_only_fields(self):
        for model in (ResponseData, WebSearchResponse):
            for field_name in model.model_fields:
                self.assertNotIn(FORBIDDEN, field_name.lower())

    def test_tool_parameters_have_no_youtube_default(self):
        for method_name in ("ai_search", "ai_web_links_search"):
            default = inspect.signature(getattr(Desearch, method_name)).parameters[
                "tools"
            ].default
            if default is inspect.Parameter.empty or default is None:
                continue
            rendered = json.dumps(list(default)).lower()
            self.assertNotIn(FORBIDDEN, rendered)

    async def test_sdk_requests_do_not_send_youtube(self):
        client = Desearch(api_key="test-key", base_url="https://example.test")
        client.client = FakeSession(
            [
                FakeResponse(json_data={"text": "ok"}),
                FakeResponse(json_data={}),
            ]
        )

        await client.ai_search(prompt="q", tools=[member.value for member in Tool])
        await client.ai_web_links_search(
            prompt="q", tools=[member.value for member in WebTool]
        )

        self.assertEqual(
            client.client.requests[0][0:2],
            ("POST", "https://example.test/desearch/ai/search"),
        )
        self.assertEqual(
            client.client.requests[1][0:2],
            ("POST", "https://example.test/desearch/ai/search/links/web"),
        )
        sent_tools = []
        for _method, _url, kwargs in client.client.requests:
            payload = kwargs["json"]
            rendered = json.dumps(payload).lower()
            self.assertNotIn(FORBIDDEN, rendered)
            tools = [tool.lower() for tool in payload["tools"]]
            self.assertNotIn(FORBIDDEN, tools)
            sent_tools.extend(tools)
        self.assertEqual(
            sent_tools,
            [member.value for member in Tool] + [member.value for member in WebTool],
        )

    def test_sdk_and_docs_do_not_mention_youtube(self):
        repo_root = Path(__file__).resolve().parents[1]
        scan_paths = [
            repo_root / "desearch_py",
            repo_root / "README.md",
            repo_root / "docs",
            repo_root / "setup.py",
            repo_root / "pyproject.toml",
        ]
        offenders = []
        for scan_path in scan_paths:
            files = scan_path.rglob("*") if scan_path.is_dir() else [scan_path]
            for path in files:
                if not path.is_file():
                    continue
                if path.suffix.lower() in {".png", ".inv", ".pickle", ".doctree"}:
                    continue
                try:
                    text = path.read_text(encoding="utf-8")
                except (UnicodeDecodeError, OSError):
                    continue
                if FORBIDDEN in text.lower():
                    offenders.append(str(path.relative_to(repo_root)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
