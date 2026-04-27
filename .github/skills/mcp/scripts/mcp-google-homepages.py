"""Run a Google query through chrome-devtools MCP and print unique homepage domains.

Purpose:
    Query Google results using MCP chrome integration and extract unique organization domains.
    Provides URL enumeration for research and testing workflows.

Security:
    Executes queries through configured MCP endpoint only. Results are public domain data.
    No credentials stored in output.
"""

from __future__ import annotations

import argparse
import json
import os
from urllib.parse import quote_plus

import anyio
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("query", help="Google search query")
    parser.add_argument(
        "--limit", type=int, default=10, help="Maximum homepage URLs in output"
    )
    parser.add_argument(
        "--browser-url",
        default=os.getenv("MCP_BROWSER_URL", "http://[::1]:9222"),
        help="Chrome DevTools endpoint URL",
    )
    return parser


async def _call_text(session: ClientSession, tool: str, args: dict) -> str:
    result = await session.call_tool(tool, args)
    return "\n".join(
        getattr(content, "text", "")
        for content in (result.content or [])
        if getattr(content, "type", None) == "text"
    )


# Browser JS that collects unique homepage URLs from a Google results page.
_GOOGLE_SEARCH_SCRIPT = """async () => {
              const out = {
                title: document.title,
                url: location.href,
                homepages: [],
              };

              const ignored = new Set([
                'google.com', 'www.google.com', 'support.google.com',
                'policies.google.com', 'accounts.google.com', 'maps.google.com',
              ]);

              const seen = new Set();
              const anchors = Array.from(document.querySelectorAll('a[href]'));
              for (const a of anchors) {
                const href = a.getAttribute('href') || '';
                if (!href.startsWith('http')) { continue; }
                try {
                  const url = new URL(href);
                  const host = url.hostname.toLowerCase();
                  if (ignored.has(host)) { continue; }
                  const homepage = `${url.protocol}//${host}/`;
                  if (!seen.has(homepage)) {
                    seen.add(homepage);
                    out.homepages.push(homepage);
                  }
                } catch (_) {
                  // ignore malformed links
                }
              }
              return out;
            }"""


async def run(query: str, limit: int, browser_url: str) -> dict:
    """Run a Google search through chrome-devtools MCP and collect unique homepage URLs."""
    search_url = f"https://www.google.com/search?q={quote_plus(query)}"
    server = StdioServerParameters(
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

    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            await session.call_tool(
                "navigate_page",
                {
                    "type": "url",
                    "url": search_url,
                    "timeout": 30000,
                },
            )
            await anyio.sleep(2)
            text = await _call_text(
                session, "evaluate_script", {"function": _GOOGLE_SEARCH_SCRIPT}
            )
            data = json.loads(text.split("```json", 1)[1].split("```", 1)[0].strip())
            data["query"] = query
            data["homepages"] = data.get("homepages", [])[: max(limit, 1)]
            data["count"] = len(data["homepages"])
            return data


async def _main() -> None:
    args = _parser().parse_args()
    result = await run(args.query, args.limit, args.browser_url)
    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    anyio.run(_main)
