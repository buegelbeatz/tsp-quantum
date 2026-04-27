"""Run orchestration helper for Chrome MCP jobs."""

from __future__ import annotations

from pathlib import Path


def _read_job_params(read_env_fn) -> dict:
    """Read and validate job execution parameters from environment."""
    return {
        "source_url": read_env_fn("URL", required=True),
        "job": read_env_fn("JOB", required=True),
        "limit": int(read_env_fn("LIMIT", default="5") or "5"),
        "browser_url": read_env_fn("MCP_BROWSER_URL", default="http://[::1]:9222"),
        "wait_timeout_seconds": int(
            read_env_fn("WAIT_TIMEOUT_SECONDS", default="240") or "240"
        ),
        "poll_seconds": int(read_env_fn("POLL_SECONDS", default="5") or "5"),
    }


def _build_chrome_server(browser_url: str, stdio_server_parameters_cls):
    """Build and return a StdioServerParameters for the chrome-devtools MCP proxy."""
    return stdio_server_parameters_cls(
        command="./.github/skills/mcp/scripts/mcp-proxy-wrapper.sh",
        args=[
            "chrome-devtools",
            "npx",
            "chrome-devtools-mcp@latest",
            "--browserUrl",
            browser_url,
            "--no-usage-statistics",
        ],
    )


def _make_result(homepages: list, destination: Path) -> dict[str, str | int | list]:
    """Build the standardised job-result dict."""
    return {
        "status": "ok",
        "report": str(destination),
        "homepage_count": len(homepages),
        "homepages": homepages,
    }


async def run_impl(
    *,
    read_env_fn,
    collect_homepages_fn,
    collect_findings_fn,
    build_markdown_fn,
    report_path_fn,
    stdio_server_parameters_cls,
    stdio_client_fn,
    client_session_cls,
) -> dict[str, str | int | list[str]]:
    """Execute chrome MCP job and write markdown summary report."""
    params = _read_job_params(read_env_fn)
    output_dir = Path(".specifications")
    output_dir.mkdir(parents=True, exist_ok=True)
    server = _build_chrome_server(params["browser_url"], stdio_server_parameters_cls)

    async with stdio_client_fn(server) as (read_stream, write_stream):
        async with client_session_cls(read_stream, write_stream) as session:
            await session.initialize()
            homepages = await collect_homepages_fn(
                session,
                source_url=params["source_url"],
                limit=params["limit"],
                wait_timeout_seconds=params["wait_timeout_seconds"],
                poll_seconds=params["poll_seconds"],
            )
            findings = await collect_findings_fn(session, homepages)

    markdown = build_markdown_fn(
        job=params["job"],
        source_url=params["source_url"],
        homepages=homepages,
        findings=findings,
    )
    destination = report_path_fn(job=params["job"], output_dir=output_dir)
    destination.write_text(markdown, encoding="utf-8")
    return _make_result(homepages, destination)
