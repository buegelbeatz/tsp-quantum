#!/usr/bin/env python3
# layer: digital-generic-team
"""Track workflow-code-debt KPI and enforce a monotonic non-increasing trend."""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

TRACKED_GLOBS = (
    ".github/hooks/prompt-invoke*.sh",
    ".github/skills/artifacts/scripts/artifacts_flow*.py",
    ".github/skills/**/scripts/*orchestrat*.py",
    ".github/skills/**/scripts/*orchestrat*.sh",
    ".github/skills/**/scripts/*flow*.py",
    ".github/skills/**/scripts/stages-action.sh",
    ".github/skills/**/scripts/board-ticket.sh",
    ".github/skills/shared/task-orchestration/scripts/task-audit-log.sh",
)

DEFAULT_HISTORY = Path(".digital-artifacts/70-audits/workflow-code-debt/history.csv")
DEFAULT_REPORT = Path(".digital-artifacts/70-audits/workflow-code-debt/latest.md")


@dataclass(frozen=True)
class DebtSnapshot:
    file_count: int
    total_decision_lines: int


def _is_tracked_file(path: Path) -> bool:
    text = path.as_posix()
    if "/tests/" in text or path.name.startswith("test_"):
        return False
    if text.startswith(".digital-runtime/") or text.startswith(".tests/"):
        return False
    return True


def _collect_tracked_files(repo_root: Path) -> list[Path]:
    files: dict[str, Path] = {}
    for pattern in TRACKED_GLOBS:
        for candidate in repo_root.glob(pattern):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(repo_root)
            if not _is_tracked_file(rel):
                continue
            files[rel.as_posix()] = rel
    return [files[key] for key in sorted(files)]


def _count_net_lines(path: Path) -> int:
    count = 0
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#"):
            continue
        count += 1
    return count


def _scan_snapshot(repo_root: Path) -> DebtSnapshot:
    tracked = _collect_tracked_files(repo_root)
    total = sum(_count_net_lines(repo_root / rel) for rel in tracked)
    return DebtSnapshot(file_count=len(tracked), total_decision_lines=total)


def scan_snapshot(repo_root: Path) -> DebtSnapshot:
    """Return workflow-code-debt snapshot for the repository root."""
    return _scan_snapshot(repo_root)


def _read_previous_total(history_path: Path) -> int | None:
    if not history_path.exists():
        return None
    rows = history_path.read_text(encoding="utf-8").splitlines()
    if len(rows) <= 1:
        return None
    try:
        return int(rows[-1].split(",")[2])
    except (IndexError, ValueError):
        return None


def read_previous_total(history_path: Path) -> int | None:
    """Return previous total_decision_lines from history, if available."""
    return _read_previous_total(history_path)


def _append_history(history_path: Path, snapshot: DebtSnapshot, repo_root: Path) -> None:
    history_path.parent.mkdir(parents=True, exist_ok=True)
    exists = history_path.exists()
    with history_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        if not exists:
            writer.writerow(["timestamp", "file_count", "total_decision_lines", "repo_root"])
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                snapshot.file_count,
                snapshot.total_decision_lines,
                repo_root.as_posix(),
            ]
        )


def _write_report(report_path: Path, snapshot: DebtSnapshot, previous_total: int | None) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    delta = "n/a" if previous_total is None else str(snapshot.total_decision_lines - previous_total)
    trend = "stable"
    if previous_total is not None:
        if snapshot.total_decision_lines < previous_total:
            trend = "improving"
        elif snapshot.total_decision_lines > previous_total:
            trend = "regression"

    report_path.write_text(
        "\n".join(
            [
                "# Workflow Code Debt KPI",
                "",
                f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
                f"- tracked_files: {snapshot.file_count}",
                f"- total_decision_lines: {snapshot.total_decision_lines}",
                f"- previous_total_decision_lines: {previous_total if previous_total is not None else 'n/a'}",
                f"- delta: {delta}",
                f"- trend: {trend}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root to scan")
    parser.add_argument("--history-path", default=str(DEFAULT_HISTORY), help="CSV history path")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT), help="Markdown report path")
    parser.add_argument("--record", action="store_true", help="Append current snapshot to history")
    parser.add_argument(
        "--check-monotonic",
        action="store_true",
        help="Fail when total_decision_lines increased compared with previous history row",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    history_path = (repo_root / args.history_path).resolve()
    report_path = (repo_root / args.report_path).resolve()

    snapshot = _scan_snapshot(repo_root)
    previous_total = _read_previous_total(history_path)

    if args.check_monotonic and previous_total is not None and snapshot.total_decision_lines > previous_total:
        _write_report(report_path, snapshot, previous_total)
        print(
            f"workflow-code-debt regression: current={snapshot.total_decision_lines} previous={previous_total}",
        )
        return 2

    if args.record:
        _append_history(history_path, snapshot, repo_root)
    _write_report(report_path, snapshot, previous_total)

    print(f"tracked_files={snapshot.file_count}")
    print(f"total_decision_lines={snapshot.total_decision_lines}")
    if previous_total is not None:
        print(f"previous_total_decision_lines={previous_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
