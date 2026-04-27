"""Unit tests for mcp-chrome-job.py helper behavior."""

from __future__ import annotations

import asyncio
import datetime as dt
import importlib.util
import json
import sys
import types
from contextlib import asynccontextmanager
from pathlib import Path

import pytest


def _install_dependency_stubs() -> None:
    """Install lightweight stubs for optional runtime dependencies."""

    if "anyio" not in sys.modules:
        anyio_module = types.ModuleType("anyio")

        async def sleep(_seconds: float) -> None:
            """TODO: add docstring for sleep."""
            return None

        anyio_module.sleep = sleep  # type: ignore[attr-defined]
        sys.modules["anyio"] = anyio_module

    if "mcp" not in sys.modules:
        mcp_module = types.ModuleType("mcp")
        client_module = types.ModuleType("mcp.client")
        stdio_module = types.ModuleType("mcp.client.stdio")

        class ClientSession:
            def __init__(self, _read, _write) -> None:
                return None

            async def __aenter__(self):
                return self

            async def __aexit__(self, _exc_type, _exc, _tb) -> None:
                return None

            async def initialize(self) -> None:
                """TODO: add docstring for initialize."""
                return None

            async def call_tool(self, _tool_name: str, _args: dict):
                """TODO: add docstring for call_tool."""
                return None

        class StdioServerParameters:
            def __init__(self, **_kwargs) -> None:
                return None

        @asynccontextmanager
        async def stdio_client(_server):
            """TODO: add docstring for stdio_client."""
            yield object(), object()

        mcp_module.ClientSession = ClientSession  # type: ignore[attr-defined]
        stdio_module.stdio_client = stdio_client  # type: ignore[attr-defined]
        stdio_module.StdioServerParameters = StdioServerParameters  # type: ignore[attr-defined]

        sys.modules["mcp"] = mcp_module
        sys.modules["mcp.client"] = client_module
        sys.modules["mcp.client.stdio"] = stdio_module


def _load_module():
    _install_dependency_stubs()
    root = Path(__file__).resolve().parents[1]
    module_path = root / "mcp-chrome-job.py"
    spec = importlib.util.spec_from_file_location("mcp_chrome_job", module_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


MODULE = _load_module()


def test_normalize_host_strips_www() -> None:
    """TODO: add docstring for test_normalize_host_strips_www."""
    assert MODULE.normalize_host("https://www.example.com/x") == "example.com"


def test_slugify_creates_safe_token() -> None:
    """TODO: add docstring for test_slugify_creates_safe_token."""
    assert MODULE.slugify("Find top 5 links!") == "find-top-5-links"


def test_report_path_uses_timestamp_and_slug(tmp_path: Path) -> None:
    """TODO: add docstring for test_report_path_uses_timestamp_and_slug."""
    now = dt.datetime(2026, 3, 27, 15, 30, 45, tzinfo=dt.timezone.utc)
    target = MODULE.report_path("My Job", tmp_path, now)
    assert target.name == "chrome-20260327-153045-my-job.md"


def test_summarize_text_truncates_with_ellipsis() -> None:
    """TODO: add docstring for test_summarize_text_truncates_with_ellipsis."""
    text = "a" * 1200
    summary = MODULE.summarize_text(text, max_chars=100)
    assert len(summary) == 100
    assert summary.endswith("…")


def test_build_markdown_contains_sections() -> None:
    """TODO: add docstring for test_build_markdown_contains_sections."""
    markdown = MODULE.build_markdown(
        job="Find links",
        source_url="https://google.com/search?q=test",
        homepages=["https://example.com/"],
        findings=[
            {
                "host": "example.com",
                "url": "https://example.com/",
                "title": "Example",
                "summary": "Sample text",
            }
        ],
    )
    assert "# Chrome Job Report" in markdown
    assert "## Found Homepages" in markdown
    assert "## Findings" in markdown
    assert "### example.com" in markdown


def test_read_env_required_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """TODO: add docstring for test_read_env_required_raises."""
    monkeypatch.delenv("URL", raising=False)
    with pytest.raises(ValueError, match="Missing required environment variable: URL"):
        MODULE.read_env("URL", required=True)


def test_parse_tool_json_extracts_payload() -> None:
    """TODO: add docstring for test_parse_tool_json_extracts_payload."""
    payload = {"homepages": ["https://example.com/"]}
    text = f"noise\n```json\n{json.dumps(payload)}\n```\n"
    parsed = MODULE.parse_tool_json(text)
    assert parsed == payload


class _FakeSession:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict]] = []

    async def call_tool(self, tool_name: str, args: dict):
        """TODO: add docstring for call_tool."""
        self.calls.append((tool_name, args))
        return None


def _tool_json(payload: dict) -> str:
    return f"```json\n{json.dumps(payload)}\n```"


def test_collect_homepages_wait_loop_then_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TODO: add docstring for test_collect_homepages_wait_loop_then_success."""
    session = _FakeSession()
    responses = iter(
        [
            _tool_json({"homepages": []}),
            _tool_json({"homepages": ["https://example.com/", "https://other.com/"]}),
        ]
    )

    async def fake_call_text(*_args, **_kwargs) -> str:
        """TODO: add docstring for fake_call_text."""
        return next(responses)

    async def fake_sleep(_seconds: float) -> None:
        """TODO: add docstring for fake_sleep."""
        return None

    monkeypatch.setattr(MODULE, "call_text", fake_call_text)
    monkeypatch.setattr(MODULE.anyio, "sleep", fake_sleep)

    result = asyncio.run(
        MODULE.collect_homepages(session, "https://example.com/search?q=test", 1, 10, 5)
    )

    assert result == ["https://example.com/"]
    assert session.calls[0][0] == "navigate_page"


def test_collect_homepages_google_fallback_to_ddg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TODO: add docstring for test_collect_homepages_google_fallback_to_ddg."""
    session = _FakeSession()
    responses = iter(
        [
            _tool_json({"homepages": []}),
            _tool_json({"homepages": []}),
            _tool_json({"homepages": ["https://fallback.example/"]}),
        ]
    )

    async def fake_call_text(*_args, **_kwargs) -> str:
        """TODO: add docstring for fake_call_text."""
        return next(responses)

    async def fake_sleep(_seconds: float) -> None:
        """TODO: add docstring for fake_sleep."""
        return None

    monkeypatch.setattr(MODULE, "call_text", fake_call_text)
    monkeypatch.setattr(MODULE.anyio, "sleep", fake_sleep)

    result = asyncio.run(
        MODULE.collect_homepages(
            session, "https://www.google.com/search?q=skoda+elroq", 3, 10, 5
        )
    )

    assert result == ["https://fallback.example/"]
    assert len(session.calls) == 2
    assert session.calls[1][1]["url"].startswith("https://duckduckgo.com/?q=")


def test_collect_findings_extracts_title_and_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TODO: add docstring for test_collect_findings_extracts_title_and_summary."""
    session = _FakeSession()
    responses = iter(
        [
            _tool_json({"title": "Example", "text": "Alpha text"}),
            _tool_json({"title": "Other", "text": "Beta text"}),
        ]
    )

    async def fake_call_text(*_args, **_kwargs) -> str:
        """TODO: add docstring for fake_call_text."""
        return next(responses)

    async def fake_sleep(_seconds: float) -> None:
        """TODO: add docstring for fake_sleep."""
        return None

    monkeypatch.setattr(MODULE, "call_text", fake_call_text)
    monkeypatch.setattr(MODULE.anyio, "sleep", fake_sleep)

    findings = asyncio.run(
        MODULE.collect_findings(
            session, ["https://www.example.com/", "https://other.com/"]
        )
    )

    assert len(findings) == 2
    assert findings[0]["host"] == "example.com"
    assert findings[1]["title"] == "Other"


def test_run_writes_report(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """TODO: add docstring for test_run_writes_report."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("URL", "https://example.com/search?q=test")
    monkeypatch.setenv("JOB", "run flow")
    monkeypatch.setenv("LIMIT", "2")
    monkeypatch.setenv("MCP_BROWSER_URL", "http://[::1]:9222")
    monkeypatch.setenv("WAIT_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("POLL_SECONDS", "5")

    async def fake_collect_homepages(*_args, **_kwargs):
        """TODO: add docstring for fake_collect_homepages."""
        return ["https://example.com/"]

    async def fake_collect_findings(*_args, **_kwargs):
        """TODO: add docstring for fake_collect_findings."""
        return [
            {
                "host": "example.com",
                "url": "https://example.com/",
                "title": "Example",
                "summary": "Summary",
            }
        ]

    class _FakeClientSession:
        def __init__(self, _read, _write) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, _exc_type, _exc, _tb) -> None:
            return None

        async def initialize(self) -> None:
            """TODO: add docstring for initialize."""
            return None

    @asynccontextmanager
    async def fake_stdio_client(_server):
        """TODO: add docstring for fake_stdio_client."""
        yield object(), object()

    monkeypatch.setattr(MODULE, "collect_homepages", fake_collect_homepages)
    monkeypatch.setattr(MODULE, "collect_findings", fake_collect_findings)
    monkeypatch.setattr(MODULE, "ClientSession", _FakeClientSession)
    monkeypatch.setattr(MODULE, "stdio_client", fake_stdio_client)
    monkeypatch.setattr(MODULE, "StdioServerParameters", lambda **_kwargs: object())

    result = asyncio.run(MODULE.run())

    assert result["status"] == "ok"
    report_path = tmp_path / result["report"]
    assert report_path.exists()
    assert "Chrome Job Report" in report_path.read_text(encoding="utf-8")
