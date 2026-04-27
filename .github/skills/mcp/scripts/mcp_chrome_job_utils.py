"""Utility helpers for Chrome MCP job report generation."""

from __future__ import annotations

import datetime as dt
import os
import re
from pathlib import Path
from urllib.parse import urlparse


def read_env(name: str, *, required: bool = False, default: str = "") -> str:
    """Read environment variable and enforce required fields when configured."""
    value = os.getenv(name, default).strip()
    if required and not value:
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def normalize_host(url: str) -> str:
    """Return lowercase host without leading www prefix."""
    host = urlparse(url).hostname or ""
    host = host.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def slugify(text: str) -> str:
    """Create filesystem-safe slug from free text."""
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text).strip("-").lower()
    return slug or "chrome-job"


def report_path(job: str, output_dir: Path, now: dt.datetime | None = None) -> Path:
    """Build deterministic output path for markdown report."""
    current = now or dt.datetime.now(dt.timezone.utc)
    stamp = current.strftime("%Y%m%d-%H%M%S")
    return output_dir / f"chrome-{stamp}-{slugify(job)}.md"


def summarize_text(text: str, max_chars: int = 900) -> str:
    """Return condensed single-paragraph summary snippet from page text."""
    normalized = " ".join((text or "").split())
    if len(normalized) <= max_chars:
        return normalized
    return normalized[: max_chars - 1].rstrip() + "…"


def _render_findings(findings: list[dict[str, str]]) -> list[str]:
    """Render finding entries for the markdown report."""
    if not findings:
        return ["No homepage content could be collected."]
    lines: list[str] = []
    for finding in findings:
        lines.extend(
            [
                f"### {finding['host']}",
                "",
                f"- url: {finding['url']}",
                f"- title: {finding['title'] or '(empty title)'}",
                "- extracted_text:",
                "",
                "```text",
                finding["summary"] or "(no text extracted)",
                "```",
                "",
            ]
        )
    return lines


def build_markdown(
    job: str, source_url: str, homepages: list[str], findings: list[dict[str, str]]
) -> str:
    """Render markdown report for collected homepage findings."""
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat()
    lines = [
        "# Chrome Job Report",
        "",
        f"- generated_at: {generated_at}",
        f"- job: {job}",
        f"- source_url: {source_url}",
        f"- homepage_count: {len(homepages)}",
        "",
        "## Found Homepages",
        "",
    ]
    if not homepages:
        lines.append("- none")
    else:
        for index, homepage in enumerate(homepages, start=1):
            lines.append(f"{index}. {homepage}")
    lines.extend(["", "## Findings", ""])
    lines.extend(_render_findings(findings))
    return "\n".join(lines).rstrip() + "\n"
