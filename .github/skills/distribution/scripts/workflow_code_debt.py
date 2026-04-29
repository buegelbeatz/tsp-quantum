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
DEFAULT_TARGETS = Path(".github/skills/distribution/config/workflow_code_debt_targets.csv")


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


def summarize_top_tracked_files(repo_root: Path, limit: int = 10) -> list[tuple[str, int]]:
    """Return tracked workflow files sorted by net decision-line count descending."""
    scored = [(rel.as_posix(), _count_net_lines(repo_root / rel)) for rel in _collect_tracked_files(repo_root)]
    return sorted(scored, key=lambda item: item[1], reverse=True)[: max(0, limit)]


def load_targets(targets_path: Path) -> dict[str, tuple[int, str]]:
    """Load optional target plan as {path: (target_lines, due)} from CSV."""
    if not targets_path.exists():
        return {}

    targets: dict[str, tuple[int, str]] = {}
    with targets_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            rel_path = str(row.get("path", "")).strip()
            raw_target = str(row.get("target_lines", "")).strip()
            if not raw_target.isdigit():
                continue
            if rel_path:
                targets[rel_path] = (int(raw_target), str(row.get("due", "")).strip() or "n/a")
    return targets


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


def _write_report(
    report_path: Path,
    snapshot: DebtSnapshot,
    previous_total: int | None,
    top_files: list[tuple[str, int]],
    targets: dict[str, tuple[int, str]],
) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    delta = "n/a" if previous_total is None else str(snapshot.total_decision_lines - previous_total)
    trend = "stable"
    if previous_total is not None:
        if snapshot.total_decision_lines < previous_total:
            trend = "improving"
        elif snapshot.total_decision_lines > previous_total:
            trend = "regression"

    targeted_files = sum(1 for rel_path, _ in top_files if targets.get(rel_path, (0, "n/a"))[0] > 0)
    over_target_files = sum(
        1
        for rel_path, net_lines in top_files
        if (target_lines := targets.get(rel_path, (0, "n/a"))[0]) > 0 and net_lines > target_lines
    )

    lines = [
        "# Workflow Code Debt KPI",
        "",
        f"- generated_at: {datetime.now(timezone.utc).isoformat()}",
        f"- tracked_files: {snapshot.file_count}",
        f"- total_decision_lines: {snapshot.total_decision_lines}",
        f"- previous_total_decision_lines: {previous_total if previous_total is not None else 'n/a'}",
        f"- delta: {delta}",
        f"- trend: {trend}",
        f"- targeted_top_files: {targeted_files}",
        f"- over_target_top_files: {over_target_files}",
        "",
        "## Top Tracked Workflow Files",
        "",
        "| file | net_lines | target_lines | remaining_to_target | due |",
        "| --- | ---: | ---: | ---: | --- |",
    ]
    for rel_path, net_lines in top_files:
        target_lines, due = targets.get(rel_path, (0, "n/a"))
        remaining = max(0, net_lines - target_lines) if target_lines > 0 else "n/a"
        target_cell = str(target_lines) if target_lines > 0 else "n/a"
        lines.append(f"| {rel_path} | {net_lines} | {target_cell} | {remaining} | {due} |")

    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=".", help="Repository root to scan")
    parser.add_argument("--history-path", default=str(DEFAULT_HISTORY), help="CSV history path")
    parser.add_argument("--report-path", default=str(DEFAULT_REPORT), help="Markdown report path")
    parser.add_argument("--targets-path", default=str(DEFAULT_TARGETS), help="CSV target plan path")
    parser.add_argument("--record", action="store_true", help="Append current snapshot to history")
    parser.add_argument("--check-monotonic", action="store_true", help="Fail when total_decision_lines increased compared with previous history row")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(args.repo_root).resolve()
    history_path = (repo_root / args.history_path).resolve()
    report_path = (repo_root / args.report_path).resolve()
    targets_path = (repo_root / args.targets_path).resolve()

    snapshot = _scan_snapshot(repo_root)
    previous_total = _read_previous_total(history_path)
    top_files = summarize_top_tracked_files(repo_root, limit=10)
    targets = load_targets(targets_path)

    if args.check_monotonic and previous_total is not None and snapshot.total_decision_lines > previous_total:
        _write_report(report_path, snapshot, previous_total, top_files, targets)
        print(
            f"workflow-code-debt regression: current={snapshot.total_decision_lines} previous={previous_total}",
        )
        return 2

    if args.record:
        _append_history(history_path, snapshot, repo_root)
    _write_report(report_path, snapshot, previous_total, top_files, targets)

    print(f"tracked_files={snapshot.file_count}")
    print(f"total_decision_lines={snapshot.total_decision_lines}")
    if previous_total is not None:
        print(f"previous_total_decision_lines={previous_total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
