#!/usr/bin/env python3
"""Run a generic Chrome MCP job from URL + task and save a markdown report."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import mcp_chrome_job_collect as collect_impl  # noqa: E402
import mcp_chrome_job_run as run_impl  # noqa: E402
import mcp_chrome_job_utils as utils  # noqa: E402

read_env = utils.read_env
normalize_host = utils.normalize_host
slugify = utils.slugify
report_path = utils.report_path
summarize_text = utils.summarize_text
build_markdown = utils.build_markdown


async def call_text(session: ClientSession, tool_name: str, args: dict) -> str:
    """Call MCP tool and return concatenated text content entries."""
    tool_result = await session.call_tool(tool_name, args)
    return "\n".join(
        getattr(content, "text", "")
        for content in (tool_result.content or [])
        if getattr(content, "type", None) == "text"
    )


def parse_tool_json(text: str) -> dict:
    """Parse JSON payload returned by chrome-devtools-mcp evaluate_script."""
    return json.loads(text.split("```json", 1)[1].split("```", 1)[0].strip())


async def collect_homepages(
    session: ClientSession,
    source_url: str,
    limit: int,
    wait_timeout_seconds: int,
    poll_seconds: int,
) -> list[str]:
    """Navigate to source URL and collect unique homepage URLs with manual-captcha wait loop."""
    return await collect_impl.collect_homepages_impl(
        session,
        source_url,
        limit,
        wait_timeout_seconds,
        poll_seconds,
        call_text_fn=call_text,
        parse_tool_json_fn=parse_tool_json,
        normalize_host_fn=normalize_host,
        sleep_fn=anyio.sleep,
        print_fn=print,
    )


async def collect_findings(
    session: ClientSession, homepages: list[str]
) -> list[dict[str, str]]:
    """Open each homepage and collect title and compact text excerpt."""
    return await collect_impl.collect_findings_impl(
        session,
        homepages,
        call_text_fn=call_text,
        parse_tool_json_fn=parse_tool_json,
        normalize_host_fn=normalize_host,
        summarize_text_fn=summarize_text,
        sleep_fn=anyio.sleep,
    )


async def run() -> dict[str, str | int | list[str]]:
    """Execute chrome MCP job and write markdown summary report to .specifications."""
    return await run_impl.run_impl(
        read_env_fn=read_env,
        collect_homepages_fn=collect_homepages,
        collect_findings_fn=collect_findings,
        build_markdown_fn=build_markdown,
        report_path_fn=report_path,
        stdio_server_parameters_cls=StdioServerParameters,
        stdio_client_fn=stdio_client,
        client_session_cls=ClientSession,
    )


if __name__ == "__main__":
    result = anyio.run(run)
    print(json.dumps(result, indent=2, ensure_ascii=False))
