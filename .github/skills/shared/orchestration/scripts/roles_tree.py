#!/usr/bin/env python3
"""Render generic role assignments from .github/agents/roles/*.agent.md."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "agents" / "roles").exists():
            return candidate
    raise RuntimeError("Could not resolve repository root")


def _parse_role_agents(role_file: Path) -> tuple[str, list[str]]:
    text = role_file.read_text(encoding="utf-8")
    role_name_match = re.search(r"^name:\s*([^\n]+)$", text, flags=re.MULTILINE)
    role_name = role_name_match.group(1).strip().strip('"') if role_name_match else role_file.stem

    agents: list[str] = []
    in_agents = False
    for raw in text.splitlines():
        line = raw.rstrip()
        if re.match(r"^agents:\s*$", line):
            in_agents = True
            continue
        if in_agents and re.match(r"^[A-Za-z0-9_-]+:\s*", line):
            break
        if in_agents:
            match = re.match(r"^\s*-\s*([A-Za-z0-9_-]+)\s*$", line)
            if match:
                agents.append(match.group(1))
    return role_name, sorted(set(agents))


def _supports_color() -> bool:
    if os.getenv("NO_COLOR"):
        return False
    return sys.stdout.isatty() and os.getenv("TERM", "") != "dumb"


def _style(text: str, *, color: str = "", bold: bool = False) -> str:
    if not _supports_color():
        return text
    codes: list[str] = []
    if bold:
        codes.append("1")
    if color:
        codes.append(color)
    if not codes:
        return text
    return f"\033[{';'.join(codes)}m{text}\033[0m"


def main() -> None:
    repo_root = _repo_root()
    roles_dir = repo_root / ".github" / "agents" / "roles"

    role_files = sorted(roles_dir.glob("*.agent.md"))
    if not role_files:
        print("No role definitions found.")
        return

    print(_style("Role assignments", color="36", bold=True))
    print(_style("================", color="36"))
    for role_file in role_files:
        role_name, agents = _parse_role_agents(role_file)
        print(_style(f"🧭 {role_name}", color="34", bold=True))
        if agents:
            for agent in agents:
                print(_style(f"  ✅ {agent}", color="32"))
        else:
            print(_style("  ⚪ (no agents assigned)", color="33"))


if __name__ == "__main__":
    main()
