from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


DIRECT_TOOL_PATTERN = re.compile(
    r"(?:^|[;(]|&&|\|\|)\s*(?:[A-Z_][A-Z0-9_]*=(?:\"[^\"]*\"|'[^']*'|[^\s]+)\s+)*(?P<tool>python3|pytest|ruff|jq|gh|mmdc|pip3|docker|podman|shellcheck)(?=\s|$)"
)


@dataclass(frozen=True)
class AllowEntry:
    path: str
    tool: str
    reason: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Guard direct tool invocations under .github shell scripts.")
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--allowlist", required=True)
    return parser.parse_args()


def read_allowlist(path: Path) -> set[tuple[str, str]]:
    allowed: set[tuple[str, str]] = set()
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) != 3:
            raise ValueError(f"Invalid allowlist entry: {raw_line}")
        allowed.add((parts[0], parts[1]))
    return allowed


def tracked_shell_files(repo_root: Path) -> list[Path]:
    result = subprocess.run(
        ["git", "-C", str(repo_root), "ls-files"],
        text=True,
        capture_output=True,
        check=True,
    )
    files: list[Path] = []
    for line in result.stdout.splitlines():
        if line.startswith(".github/") and line.endswith(".sh"):
            files.append(repo_root / line)
    return files


def find_violations(repo_root: Path, allowlist: set[tuple[str, str]]) -> list[str]:
    violations: list[str] = []
    for file_path in tracked_shell_files(repo_root):
        relative_path = file_path.relative_to(repo_root).as_posix()
        for line_number, line in enumerate(file_path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if "run-tool.sh" in line:
                continue
            match = DIRECT_TOOL_PATTERN.search(line)
            if not match:
                continue
            tool = match.group("tool")
            if (relative_path, tool) in allowlist:
                continue
            violations.append(f"{relative_path}:{line_number}: direct {tool} invocation")
    return violations


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    allowlist_path = Path(args.allowlist).resolve()

    allowlist = read_allowlist(allowlist_path)
    violations = find_violations(repo_root, allowlist)
    if violations:
        print("Direct tool invocation guard failed:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print("Direct tool invocation guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())