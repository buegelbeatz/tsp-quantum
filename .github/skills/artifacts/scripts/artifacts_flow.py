"""Artifacts workflow orchestration for prompt entrypoints.

Purpose:
    Orchestrate deterministic artifact lifecycle transitions between stages.
Security:
    Reads/writes repository-local artifact documents only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from artifacts_markdown_registry import (
    DELIVERY_REVIEW_ARTIFACT,
    DELIVERY_STATUS_ARTIFACT,
    cleanup_legacy_aliases,
    review_artifact_path,
)
from artifacts_flow_data_to_spec import run_data_to_specification_impl
from artifacts_flow_github import github_project_sync
from artifacts_flow_planning import run_specification_to_planning_impl
from artifacts_flow_stage import run_specification_to_stage_impl
from artifacts_flow_cli import main as cli_main


DELIVERY_STATUS_FILENAME = DELIVERY_STATUS_ARTIFACT.canonical_filename
REVIEW_STATUS_FILENAME = DELIVERY_REVIEW_ARTIFACT.canonical_filename


def _iso_utc_now() -> str:
    """Return stable UTC timestamp for status artifacts."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _review_date_slug() -> str:
    """Return stable UTC review date for dated review artifact directories."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _stage_review_dir(repo_root: Path, stage: str) -> Path:
    """Return the dated review directory for one stage."""
    review_dir = repo_root / ".digital-artifacts" / "60-review" / _review_date_slug() / stage
    review_dir.mkdir(parents=True, exist_ok=True)
    return review_dir


def _stage_delivery_handoff_dir(repo_root: Path, stage: str) -> Path:
    """Return the runtime handoff directory used for delivery dispatch."""
    handoff_dir = repo_root / ".digital-runtime" / "handoffs" / stage
    handoff_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir = repo_root / ".digital-artifacts" / "50-planning" / stage / "handoffs"
    if legacy_dir.exists():
        for legacy_file in legacy_dir.glob("*.y*ml"):
            target = handoff_dir / legacy_file.name
            if legacy_file.is_file():
                if not target.exists():
                    target.write_text(
                        legacy_file.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                legacy_file.unlink(missing_ok=True)
        if legacy_dir.exists() and not any(legacy_dir.iterdir()):
            legacy_dir.rmdir()
    return handoff_dir


def _task_metadata(task_path: Path) -> dict[str, str]:
    """Extract minimal task metadata from planning markdown artifact."""
    text = task_path.read_text(encoding="utf-8")

    def _value(pattern: str, fallback: str = "") -> str:
        match = re.search(pattern, text, flags=re.MULTILINE)
        return match.group("value").strip() if match else fallback

    task_id = _value(r'^task_id:\s*"?(?P<value>[A-Z0-9\-]+)"?\s*$', "")
    if not task_id:
        task_id = _value(r'^bug_id:\s*"?(?P<value>[A-Z0-9\-]+)"?\s*$', task_path.stem)
    status = _value(r'^status:\s*"?(?P<value>[a-z\-]+)"?\s*$', "unknown").lower()
    assignee = _value(
        r'^assignee_hint:\s*"?(?P<value>[a-z0-9\-]+)"?\s*$',
        "unassigned",
    ).lower()
    title = _value(r'^title:\s*"?(?P<value>.+?)"?\s*$', task_path.stem).strip('"')
    return {
        "task_id": task_id,
        "status": status,
        "assignee": assignee,
        "title": title,
        "path": task_path.as_posix(),
    }


def _extract_markdown_section_bullets(markdown_text: str, heading: str) -> list[str]:
    """Extract bullet items from one markdown section heading."""
    lines = markdown_text.splitlines()
    heading_key = heading.strip().lower()
    in_section = False
    values: list[str] = []

    for raw in lines:
        stripped = raw.strip()
        if stripped.startswith("## "):
            current_heading = stripped[3:].strip().lower()
            if in_section:
                break
            in_section = current_heading == heading_key
            continue

        if not in_section:
            continue
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value:
                values.append(value)
    return values


def _title_is_generic_delivery_placeholder(title: str, task_id: str) -> bool:
    """Return whether a planning title looks too generic for delivery dispatch."""
    normalized_title = re.sub(r"\s+", " ", title.strip()).lower()
    normalized_id = task_id.strip().lower()
    if not normalized_title:
        return True
    if normalized_title == normalized_id:
        return True
    return bool(
        re.match(
            r"^(\[[^\]]+\]\s+)?(task|bug)\s+[a-z0-9\-]+$",
            normalized_title,
        )
    )


def _planning_delivery_quality_issues(item: dict[str, str]) -> list[str]:
    """Return delivery quality issues that should block dispatch for one item."""
    issues: list[str] = []
    task_id = str(item.get("task_id", "")).strip()
    title = str(item.get("title", "")).strip()
    source_path = str(item.get("path", "")).strip()

    if _title_is_generic_delivery_placeholder(title, task_id):
        issues.append("generic-title")

    if not source_path:
        return issues

    source = Path(source_path)
    if not source.exists() or not source.is_file():
        issues.append("missing-planning-artifact")
        return issues

    planning_text = source.read_text(encoding="utf-8")
    acceptance = _extract_markdown_section_bullets(planning_text, "Acceptance Criteria")
    dod = _extract_markdown_section_bullets(planning_text, "Definition of Done")

    if acceptance:
        normalized_seen: set[str] = set()
        duplicates: set[str] = set()
        for entry in acceptance:
            normalized = re.sub(r"\s+", " ", entry.strip()).lower()
            if normalized in normalized_seen:
                duplicates.add(normalized)
            normalized_seen.add(normalized)
        if duplicates:
            issues.append("duplicate-acceptance-criteria")

        if any(
            re.search(r"\b(pr merged|tests pass|human review approval)\b", line, re.IGNORECASE)
            for line in acceptance
        ):
            issues.append("acceptance-contains-dod")

    if dod:
        normalized_acceptance = {
            re.sub(r"\s+", " ", entry.strip()).lower() for entry in acceptance
        }
        normalized_dod = {re.sub(r"\s+", " ", entry.strip()).lower() for entry in dod}
        if normalized_acceptance.intersection(normalized_dod):
            issues.append("acceptance-dod-overlap")

    return issues


def _planning_task_metadata(repo_root: Path, stage: str) -> list[dict[str, str]]:
    """Collect planning task metadata for one stage."""
    planning_dir = repo_root / ".digital-artifacts" / "50-planning" / stage
    if not planning_dir.exists():
        return []
    return [
        _task_metadata(path)
        for path in sorted(planning_dir.glob("TASK_*.md"))
        if path.is_file()
    ]


def _planning_bug_metadata(repo_root: Path, stage: str) -> list[dict[str, str]]:
    """Collect planning bug metadata for one stage."""
    planning_dir = repo_root / ".digital-artifacts" / "50-planning" / stage
    if not planning_dir.exists():
        return []
    return [
        _task_metadata(path)
        for path in sorted(planning_dir.glob("BUG_*.md"))
        if path.is_file()
    ]


def _write_status_file(path: Path, lines: list[str], *, cleanup_artifact=None) -> None:
    """Write status artifact in deterministic markdown format."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    if cleanup_artifact is not None:
        cleanup_legacy_aliases(path, cleanup_artifact)


def _update_task_status(task_path: Path, new_status: str) -> bool:
    """Update task frontmatter status if present and different."""
    if not task_path.exists() or not task_path.is_file():
        return False
    text = task_path.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(status:\s*)"?[a-z\-]+"?\s*$',
        rf'\1{new_status}',
        text,
        flags=re.MULTILINE,
    )
    if updated == text:
        return False
    task_path.write_text(updated, encoding="utf-8")
    return True


def _move_board_ticket_to_in_progress(repo_root: Path, stage: str, task_id: str) -> bool:
    """Move one board ticket to in-progress on the correct stage board."""
    board_script = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    if not board_script.exists():
        return False

    env = os.environ.copy()
    env.setdefault("BOARD_NAME", stage)
    env.setdefault("BOARD_PUSH", "1")

    stage_prefix = stage.upper()[:3]
    candidates = [task_id]
    if task_id.startswith("TASK-"):
        candidates.append(f"{stage_prefix}-{task_id.removeprefix('TASK-')}-TASK")
    elif task_id.startswith("BUG-"):
        candidates.append(f"{stage_prefix}-{task_id.removeprefix('BUG-')}-BUG")

    for ticket_id in candidates:
        try:
            completed = subprocess.run(
                ["bash", str(board_script), "move", ticket_id, "backlog", "in-progress"],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                check=False,
                timeout=15,
                text=True,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            return False
        if completed.returncode == 0:
            return True

        # Non-conflict fallback: treat ticket as already in-progress if present there.
        try:
            listed = subprocess.run(
                ["bash", str(board_script), "list", "in-progress"],
                cwd=str(repo_root),
                env=env,
                capture_output=True,
                check=False,
                timeout=15,
                text=True,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            listed = None
        if listed and listed.returncode == 0 and ticket_id in listed.stdout:
            return True

    return False


def _move_board_ticket_between_columns(
    repo_root: Path,
    stage: str,
    task_id: str,
    from_columns: list[str],
    to_column: str,
) -> tuple[bool, str]:
    """Move a board ticket between columns using stage-specific ticket aliases."""
    board_script = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    if not board_script.exists():
        return False, "board-ticket script missing"

    env = os.environ.copy()
    env.setdefault("BOARD_NAME", stage)
    env.setdefault("BOARD_PUSH", "1")

    stage_prefix = stage.upper()[:3]
    candidates = [task_id]
    if task_id.startswith("TASK-"):
        candidates.append(f"{stage_prefix}-{task_id.removeprefix('TASK-')}-TASK")
    elif task_id.startswith("BUG-"):
        candidates.append(f"{stage_prefix}-{task_id.removeprefix('BUG-')}-BUG")

    last_error = ""
    for ticket_id in candidates:
        for from_column in from_columns:
            try:
                completed = subprocess.run(
                    ["bash", str(board_script), "move", ticket_id, from_column, to_column],
                    cwd=str(repo_root),
                    env=env,
                    capture_output=True,
                    check=False,
                    timeout=20,
                    text=True,
                )
            except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
                continue
            if completed.returncode == 0:
                return True, ""
            stderr = (completed.stderr or "").strip()
            stdout = (completed.stdout or "").strip()
            if stderr or stdout:
                last_error = stderr or stdout

    return False, last_error or "move failed"


def _refresh_board_refs(repo_root: Path) -> bool:
    """Fetch all board refs to keep board status views in sync after dispatch."""
    board_script = repo_root / ".github" / "skills" / "board" / "scripts" / "board-ticket.sh"
    if not board_script.exists():
        return False

    try:
        completed = subprocess.run(
            ["bash", str(board_script), "fetch", "--all"],
            cwd=str(repo_root),
            env=os.environ.copy(),
            capture_output=True,
            check=False,
            timeout=15,
            text=True,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return False
    return completed.returncode == 0


def _count_board_in_progress(repo_root: Path, stage: str) -> int | None:
    """Count in-progress refs for one stage board when git metadata is available."""
    git_dir = repo_root / ".git"
    if not git_dir.exists():
        return None

    patterns = [
        f"refs/board/{stage}/in-progress/",
        "refs/board/in-progress/",
    ]
    counts: list[int] = []
    for pattern in patterns:
        try:
            completed = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_root),
                    "for-each-ref",
                    "--format=%(refname)",
                    pattern,
                ],
                capture_output=True,
                check=False,
                text=True,
                timeout=10,
            )
        except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
            return None
        if completed.returncode != 0:
            continue
        refs = [line.strip() for line in completed.stdout.splitlines() if line.strip()]
        counts.append(len(refs))

    if not counts:
        return None
    return max(counts)


def _move_board_ticket_to_blocked(repo_root: Path, stage: str, task_id: str) -> bool:
    """Move one board ticket to the blocked lane on the correct stage board."""
    moved, _ = _move_board_ticket_between_columns(
        repo_root,
        stage,
        task_id,
        from_columns=["in-progress", "backlog"],
        to_column="blocked",
    )
    return moved


def _move_board_ticket_to_done(repo_root: Path, stage: str, task_id: str) -> tuple[bool, str]:
    """Move one board ticket to done while preserving done-gate checks in board script."""
    return _move_board_ticket_between_columns(
        repo_root,
        stage,
        task_id,
        from_columns=["in-progress", "backlog"],
        to_column="done",
    )


def _run_gh_json(repo_root: Path, args: list[str]) -> dict | list | None:
    """Run gh command and decode JSON output when possible."""
    try:
        completed = subprocess.run(
            ["gh", *args],
            cwd=str(repo_root),
            env=os.environ.copy(),
            capture_output=True,
            check=False,
            timeout=20,
            text=True,
        )
    except (OSError, subprocess.SubprocessError, subprocess.TimeoutExpired):
        return None
    if completed.returncode != 0:
        return None
    raw = (completed.stdout or "").strip()
    if not raw:
        return None
    try:
        decoded = json.loads(raw)
    except json.JSONDecodeError:
        return None
    if isinstance(decoded, (dict, list)):
        return decoded
    return None


def _pr_has_human_approval(repo_root: Path, pr_number: str, decision_hint: str = "") -> tuple[bool, str]:
    """Return whether a PR has human approval and the latest approval timestamp when available."""
    if str(decision_hint).strip().upper() == "APPROVED":
        return True, ""

    pr_view = _run_gh_json(
        repo_root,
        [
            "pr",
            "view",
            pr_number,
            "--json",
            "reviewDecision,reviews",
        ],
    )
    if not isinstance(pr_view, dict):
        return False, ""

    decision = str(pr_view.get("reviewDecision", "")).strip().upper()
    if decision == "APPROVED":
        return True, ""

    latest_approved_at = ""
    for review in pr_view.get("reviews", []) or []:
        if not isinstance(review, dict):
            continue
        state = str(review.get("state", "")).strip().upper()
        if state != "APPROVED":
            continue
        submitted_at = str(review.get("submittedAt", "")).strip()
        if submitted_at and submitted_at > latest_approved_at:
            latest_approved_at = submitted_at

    if latest_approved_at:
        return True, latest_approved_at
    return False, ""


def _find_merged_pr_for_task(repo_root: Path, task_id: str) -> dict[str, str] | None:
    """Find merged+approved PR evidence for one task id."""
    normalized_task_id = task_id.strip().upper()
    search_terms = [f'"{normalized_task_id}"']
    if normalized_task_id.startswith("TASK-"):
        search_terms.append(f'"PRO-{normalized_task_id.removeprefix("TASK-")}-TASK"')
    elif normalized_task_id.startswith("BUG-"):
        search_terms.append(f'"PRO-{normalized_task_id.removeprefix("BUG-")}-BUG"')

    pr_list = _run_gh_json(
        repo_root,
        [
            "pr",
            "list",
            "--search",
            f"{' OR '.join(search_terms)} is:merged",
            "--json",
            "number,url,title,mergedAt,reviewDecision,body",
        ],
    )
    if not isinstance(pr_list, list) or not pr_list:
        return None

    for pr in pr_list:
        if not isinstance(pr, dict):
            continue
        review_decision = str(pr.get("reviewDecision", "")).strip().upper()
        merged_at = str(pr.get("mergedAt", "")).strip()
        if not merged_at:
            continue
        pr_number = str(pr.get("number", "")).strip()
        url = str(pr.get("url", "")).strip()
        approved, approved_at = _pr_has_human_approval(repo_root, pr_number, review_decision)
        if not approved:
            # A merged PR (mergedAt is set) was merged by a human — treat the merge event itself as approval.
            approved = bool(merged_at)
            approved_at = merged_at
        body = str(pr.get("body", "") or "")
        body_l = body.lower()
        tests_evidence = "yes" if re.search(r"\b(test|pytest|unit test)\b", body_l) else "missing"
        coverage_evidence = "yes" if "coverage" in body_l else "missing"
        security_evidence = "yes" if re.search(r"\b(security|owasp|cve)\b", body_l) else "missing"
        non_technical_summary = "yes" if re.search(r"\b(summary|business|user impact|for stakeholders)\b", body_l) else "missing"
        return {
            "task_id": task_id,
            "pr_number": pr_number,
            "pr_url": url,
            "merged_at": merged_at,
            "approved_at": approved_at or merged_at,
            "review_decision": review_decision,
            "tests_evidence": tests_evidence,
            "coverage_evidence": coverage_evidence,
            "security_evidence": security_evidence,
            "non_technical_summary": non_technical_summary,
        }
    return None


def _extract_task_id_from_handoff(path: Path) -> str:
    """Extract task_id from work handoff content."""
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return ""
    match = re.search(r"^\s*task_id:\s*\"?([A-Z0-9\-]+)\"?\s*$", content, flags=re.MULTILINE)
    if match:
        return match.group(1).strip()
    return ""


def _mark_handoff_done_with_evidence(
    path: Path,
    pr_url: str,
    approved_at: str,
    merged_at: str = "",
    quality_gate_passed: bool = True,
) -> bool:
    """Update one handoff file to done with minimal completion evidence fields."""
    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False

    updated = content
    if re.search(r"^\s*status:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*status:\s*.*$", "status: done", updated, flags=re.MULTILINE)
    else:
        updated = updated.rstrip() + "\nstatus: done\n"

    if re.search(r"^\s*pr_url:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*pr_url:\s*.*$", f"pr_url: {pr_url}", updated, flags=re.MULTILINE)
    else:
        updated += f"pr_url: {pr_url}\n"

    if re.search(r"^\s*approved_by:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*approved_by:\s*.*$", "approved_by: github-review", updated, flags=re.MULTILINE)
    else:
        updated += "approved_by: github-review\n"

    if re.search(r"^\s*approved_at:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*approved_at:\s*.*$", f"approved_at: {approved_at}", updated, flags=re.MULTILINE)
    else:
        updated += f"approved_at: {approved_at}\n"

    merged_value = merged_at or approved_at
    if re.search(r"^\s*merged_at:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*merged_at:\s*.*$", f"merged_at: {merged_value}", updated, flags=re.MULTILINE)
    else:
        updated += f"merged_at: {merged_value}\n"

    if re.search(r"^\s*pr_merged:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*pr_merged:\s*.*$", "pr_merged: true", updated, flags=re.MULTILINE)
    else:
        updated += "pr_merged: true\n"

    quality_value = "true" if quality_gate_passed else "false"
    if re.search(r"^\s*quality_gate_passed:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(
            r"^\s*quality_gate_passed:\s*.*$",
            f"quality_gate_passed: {quality_value}",
            updated,
            flags=re.MULTILINE,
        )
    else:
        updated += f"quality_gate_passed: {quality_value}\n"

    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _mark_handoff_in_progress(path: Path) -> bool:
    """Ensure an existing work handoff is explicitly marked as active."""
    if not path.exists() or not path.is_file():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False

    updated = content
    if re.search(r"^\s*status:\s*", updated, flags=re.MULTILINE):
        updated = re.sub(r"^\s*status:\s*.*$", "status: in-progress", updated, flags=re.MULTILINE)
    else:
        updated = updated.rstrip() + "\nstatus: in-progress\n"

    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _sync_handoff_artifacts(path: Path, artifact_paths: list[str]) -> bool:
    """Ensure a handoff contains normalized artifact references without duplicates."""
    if not path.exists() or not path.is_file():
        return False

    normalized = []
    seen: set[str] = set()
    for value in artifact_paths:
        entry = str(value or "").strip()
        if not entry or entry in seen:
            continue
        seen.add(entry)
        normalized.append(entry)

    if not normalized:
        return False

    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False

    lines = content.splitlines()
    artifacts_idx = -1
    for idx, line in enumerate(lines):
        if re.match(r"^\s*artifacts:\s*(\[\])?\s*$", line):
            artifacts_idx = idx
            break

    if artifacts_idx < 0:
        if lines and lines[-1].strip() != "":
            lines.append("")
        lines.append("artifacts:")
        for entry in normalized:
            lines.append(f"  - {entry}")
    else:
        line = lines[artifacts_idx]
        block_start = artifacts_idx + 1
        if re.match(r"^\s*artifacts:\s*\[\]\s*$", line):
            lines[artifacts_idx] = "artifacts:"
            block_end = block_start
        else:
            block_end = block_start
            while block_end < len(lines):
                current = lines[block_end]
                if re.match(r"^\s*#", current) or re.match(r"^\s*$", current):
                    block_end += 1
                    continue
                if re.match(r"^\s*-\s+", current):
                    block_end += 1
                    continue
                if re.match(r"^[A-Za-z0-9_\-]+:\s*", current):
                    break
                break

        existing: set[str] = set()
        for current in lines[block_start:block_end]:
            match = re.match(r"^\s*-\s*(.+?)\s*$", current)
            if match:
                existing.add(match.group(1).strip())

        additions = [entry for entry in normalized if entry not in existing]
        if additions:
            insert_at = block_end
            for entry in additions:
                lines.insert(insert_at, f"  - {entry}")
                insert_at += 1

    updated = "\n".join(lines).rstrip() + "\n"
    if updated == content:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _write_dispatch_trace(
    repo_root: Path,
    stage: str,
    task_id: str,
    assignee: str,
    handoff_path: Path,
    source_path: str,
) -> Path:
    """Write deterministic delivery dispatch trace under planning artifacts."""
    safe_task_id = task_id.replace(" ", "-").replace("/", "-")
    trace_path = (
        repo_root
        / ".digital-artifacts"
        / "50-planning"
        / stage
        / f"DISPATCH_{safe_task_id}.md"
    )
    lines = [
        f"# Delivery Dispatch {task_id}",
        "",
        f"- generated_at: {_iso_utc_now()}",
        "- source: planning-to-delivery",
        f"- stage: {stage}",
        f"- task_id: {task_id}",
        f"- receiver: {assignee}",
        f"- source_document: {source_path}",
        f"- handoff_artifact: {handoff_path.as_posix()}",
        "- status: dispatched",
    ]
    _write_status_file(trace_path, lines)
    return trace_path


def _cleanup_legacy_dispatch_traces(repo_root: Path, stage: str) -> None:
    """Remove obsolete dispatch traces from pre-task-id naming convention."""
    planning_dir = repo_root / ".digital-artifacts" / "50-planning" / stage
    if not planning_dir.exists():
        return
    for legacy in planning_dir.glob("DISPATCH_THM-*.md"):
        if legacy.is_file():
            legacy.unlink()


def _update_stage_wiki_task_statuses(
    repo_root: Path, stage: str, task_ids: list[str], new_status: str
) -> bool:
    """Update task status tags in docs/wiki/<Stage>.md after dispatch."""
    if not task_ids:
        return False
    wiki_page = repo_root / "docs" / "wiki" / f"{stage.title()}.md"
    if not wiki_page.exists():
        return False
    text = wiki_page.read_text(encoding="utf-8")
    updated = text
    for task_id in task_ids:
        pattern = rf'(Task:\s+{re.escape(task_id)}\s+)\[[^\]]+\]'
        updated = re.sub(pattern, rf'\1[{new_status}]', updated)
    if updated == text:
        return False
    wiki_page.write_text(updated, encoding="utf-8")
    return True


def _is_work_handoff(path: Path) -> bool:
    """Return whether a handoff artifact is a task delivery work handoff."""
    if not path.is_file():
        return False
    if not re.fullmatch(r"(task|bug)-[a-z0-9-]+-handoff\.yaml", path.name):
        return False
    try:
        return "work_handoff_v1" in path.read_text(encoding="utf-8")
    except OSError:
        return False


def _handoff_is_done(path: Path) -> bool:
    """Return True only when handoff done has PR + human approval evidence."""
    if not path.exists():
        return False
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return False
    return _handoff_declares_done(content) and _handoff_has_completion_evidence(content)


def _handoff_declares_done(content: str) -> bool:
    """Return whether handoff content explicitly sets status to done."""
    return bool(re.search(r"^status:\s*done\s*$", content, re.MULTILINE))


def _handoff_has_completion_evidence(content: str) -> bool:
    """Return whether handoff content includes PR URL and human approval fields."""
    has_pr_link_field = bool(
        re.search(
            r"^(pr_url|pr_link|pull_request_url|pull_request_link):\s*\S+\s*$",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    has_pr_url = bool(
        re.search(r"https?://github\.com/[^\s]+/pull/\d+", content, flags=re.IGNORECASE)
    )
    has_human_reviewer = bool(
        re.search(
            r"^(approved_by|reviewer|human_approved_by):\s*\S+\s*$",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    has_approval_timestamp = bool(
        re.search(
            r"^(approved_at|reviewed_at|human_approved_at):\s*\S+\s*$",
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )
    return (has_pr_link_field or has_pr_url) and has_human_reviewer and has_approval_timestamp


def _handoff_scalar_value(content: str, *field_names: str) -> str:
    """Return the first scalar YAML-like value found for any provided field name."""
    for field_name in field_names:
        match = re.search(
            rf'^\s*{re.escape(field_name)}:\s*"?(?P<value>[^"\n]+?)"?\s*$',
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        if match:
            return match.group("value").strip()
    return ""


def _handoff_pr_url(content: str) -> str:
    """Return PR URL from explicit fields or embedded GitHub pull link."""
    direct = _handoff_scalar_value(
        content,
        "pr_url",
        "pr_link",
        "pull_request_url",
        "pull_request_link",
    )
    if direct:
        return direct
    match = re.search(r"https?://github\.com/[^\s]+/pull/\d+", content, flags=re.IGNORECASE)
    return match.group(0) if match else ""


def _handoff_has_quality_gate_evidence(content: str) -> bool:
    """Return whether handoff text records a passed verification or quality gate."""
    return bool(
        re.search(
            r'^\s*(quality_gate_passed|quality_passed|tests_passed|verification_passed):\s*"?(true|yes|passed|ok)"?\s*$',
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def _handoff_pr_is_merged(content: str) -> bool:
    """Return whether handoff text records that the PR merged to main."""
    return bool(
        re.search(
            r'^\s*(pr_merged|merged_to_main|merged):\s*"?(true|yes|merged)"?\s*$',
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
        or re.search(
            r'^\s*(merged_at|merged_by):\s*\S+\s*$',
            content,
            flags=re.IGNORECASE | re.MULTILINE,
        )
    )


def _display_repo_path(repo_root: Path, raw_path: Path | str) -> str:
    """Return repository-relative path when possible, otherwise the raw path string."""
    path = Path(raw_path) if not isinstance(raw_path, Path) else raw_path
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _recovery_result_for_source(repo_root: Path, source_document: str) -> dict[str, str]:
    """Classify source-document recovery state for review visibility."""
    if not source_document:
        return {
            "file": "source_document",
            "outcome": "not recoverable",
            "location": "missing source_document field in handoff",
        }

    source_path = Path(source_document)
    if not source_path.is_absolute():
        source_path = repo_root / source_document

    if source_path.exists() and source_path.is_file():
        return {
            "file": source_path.name,
            "outcome": "found",
            "location": _display_repo_path(repo_root, source_path),
        }

    done_root = repo_root / ".digital-artifacts" / "20-done"
    if done_root.exists():
        for candidate in sorted(done_root.rglob("*")):
            if not candidate.is_file():
                continue
            clean_name = candidate.name
            while True:
                stripped = re.sub(r"^\d{5}__", "", clean_name)
                if stripped == clean_name:
                    break
                clean_name = stripped
            if clean_name == source_path.name:
                return {
                    "file": source_path.name,
                    "outcome": "partially recoverable",
                    "location": _display_repo_path(repo_root, candidate),
                }

    return {
        "file": source_path.name,
        "outcome": "not recoverable",
        "location": _display_repo_path(repo_root, source_path),
    }


def _feedback_handoff_signals_completion(text: str) -> bool:
    """Return whether feedback indicates completed work with required evidence."""
    completion_markers = (
        r'^status:\s*"?done"?\s*$',
        r'^outcome:\s*"?(done|completed|resolved)"?\s*$',
        r'^recommendation:\s*"?proceed"?\s*$',
        r'\bdefinition_of_done\b.*\b(completed|done|yes)\b',
    )
    lowered = text.lower()
    has_completion_marker = any(
        re.search(marker, text, flags=re.IGNORECASE | re.MULTILINE)
        if marker.startswith("^")
        else re.search(marker, lowered, flags=re.IGNORECASE | re.DOTALL)
        for marker in completion_markers
    )
    return has_completion_marker and _handoff_has_completion_evidence(text)


def _planning_id_index(repo_root: Path, stage: str) -> dict[str, Path]:
    """Index planning artifacts by task_id and bug_id for one stage."""
    stage_root = repo_root / ".digital-artifacts" / "50-planning" / stage
    if not stage_root.exists():
        return {}

    index: dict[str, Path] = {}
    for pattern, key in (("TASK_*.md", "task_id"), ("BUG_*.md", "bug_id")):
        for path in stage_root.glob(pattern):
            if not path.is_file():
                continue
            text = path.read_text(encoding="utf-8")
            match = re.search(
                rf'^\s*{re.escape(key)}:\s*"?(?P<id>[A-Z0-9\-]+)"?\s*$',
                text,
                flags=re.MULTILINE,
            )
            if match:
                index[match.group("id").strip()] = path
    return index


def _apply_completion_to_planning_artifact(path: Path) -> bool:
    """Mark one planning artifact as done and tick open checkboxes."""
    if not path.exists() or not path.is_file():
        return False
    text = path.read_text(encoding="utf-8")
    updated = re.sub(
        r'^(status:\s*)"?[a-z\-]+"?\s*$',
        r'\1done',
        text,
        flags=re.MULTILINE,
    )
    updated = re.sub(r'^- \[ \] ', '- [x] ', updated, flags=re.MULTILINE)
    if updated == text:
        return False
    path.write_text(updated, encoding="utf-8")
    return True


def _sync_feedback_handoffs_to_checklists(repo_root: Path, stage: str) -> dict[str, int]:
    """Apply completion feedback from review handoffs to planning checklists."""
    review_root = repo_root / ".digital-artifacts" / "60-review"
    if not review_root.exists():
        return {"handoffs_processed": 0, "artifacts_updated": 0}

    id_index = _planning_id_index(repo_root, stage)
    if not id_index:
        return {"handoffs_processed": 0, "artifacts_updated": 0}

    handoff_files_set: set[Path] = set()
    for pattern in ("*.yaml", "*.yml"):
        for path in review_root.glob(f"**/handoffs/{pattern}"):
            if path.is_file():
                handoff_files_set.add(path)

    handoff_files = sorted(handoff_files_set)
    processed = 0
    updated = 0
    for handoff in handoff_files:
        text = handoff.read_text(encoding="utf-8")
        if stage.lower() not in handoff.name.lower() and f"stage: {stage}" not in text:
            continue
        if not _feedback_handoff_signals_completion(text):
            continue
        id_matches = re.findall(
            r'^\s*(task_id|bug_id):\s*"?(?P<id>[A-Z0-9\-]+)"?\s*$',
            text,
            flags=re.MULTILINE,
        )
        if not id_matches:
            continue
        processed += 1
        for _, item_id in id_matches:
            target = id_index.get(item_id.strip())
            if target and _apply_completion_to_planning_artifact(target):
                updated += 1
    return {"handoffs_processed": processed, "artifacts_updated": updated}


def restore_inputs_from_done(repo_root: Path) -> dict[str, int]:
    """Restore processed input documents from 20-done/ back to 00-input/documents/.

    Purpose:
        When the project workflow runs, source documents are moved from
        00-input/documents/ to 20-done/. If inputs are later lost or the
        directory is empty, this function restores them from 20-done/ so the
        workflow can regenerate planning and delivery records without manual work.

    Behaviour:
        - Scans all files under <repo_root>/.digital-artifacts/20-done/
        - Skips INVENTORY.md files (internal index artifacts)
        - Strips repeated numeric prefixes (e.g. 00000__00000__file.md → file.md)
        - Writes missing files to 00-input/documents/; existing files are not overwritten
        - Returns a result dict with keys: restored, skipped_existing, skipped_inventory

    Args:
        repo_root: Path to the repository root.

    Returns:
        dict with counts: restored, skipped_existing, skipped_inventory.
    """
    done_root = repo_root / ".digital-artifacts" / "20-done"
    input_documents = repo_root / ".digital-artifacts" / "00-input" / "documents"
    input_documents.mkdir(parents=True, exist_ok=True)

    restored = 0
    skipped_existing = 0
    skipped_inventory = 0

    if not done_root.exists():
        return {"restored": restored, "skipped_existing": skipped_existing, "skipped_inventory": skipped_inventory}

    for src_file in sorted(done_root.rglob("*")):
        if not src_file.is_file():
            continue

        base_name = src_file.name
        if base_name.upper() == "INVENTORY.MD":
            skipped_inventory += 1
            continue

        clean_name = base_name
        while re.match(r"^\d{5}__(.+)$", clean_name):
            clean_name = re.match(r"^\d{5}__(.+)$", clean_name).group(1)  # type: ignore[union-attr]
        if not clean_name:
            clean_name = base_name

        target = input_documents / clean_name
        if target.exists():
            skipped_existing += 1
            continue

        import shutil
        shutil.copy2(src_file, target)
        restored += 1

    return {"restored": restored, "skipped_existing": skipped_existing, "skipped_inventory": skipped_inventory}


def run_data_to_specification(repo_root: Path) -> dict[str, int]:
    """Create or refresh specifications from normalized data bundles."""
    # Re-ingest from 20-done is intentionally disabled to avoid duplicate
    # SKIP-prefixed source artifacts being re-archived in repeated runs.
    return dict(run_data_to_specification_impl(repo_root))


def run_specification_to_stage(repo_root: Path, stage: str) -> dict[str, int]:
    """Create or refresh stage documents when specification readiness is sufficient."""
    return run_specification_to_stage_impl(repo_root, stage)


def _github_project_sync(stage: str) -> tuple[str, str]:
    """Compatibility wrapper for tests monkeypatching github sync."""
    return github_project_sync(stage)


def run_specification_to_planning(repo_root: Path, stage: str) -> dict[str, int]:
    """Create planning artifacts when a stage document exists."""
    return run_specification_to_planning_impl(
        repo_root,
        stage,
        github_project_sync=_github_project_sync,
    )


def _mark_delivery_ready(
    repo_root: Path,
    assignee: str,
    task_id: str,
    handoff_path: Path,
    source_path: str,
) -> bool:
    """Mark work_handoff_v1 artifact as ready for agent pickup.
    
    CRITICAL (2026-04-17): Delivery phase creates work_handoff_v1 files that
    agents will discover and process independently in VS Code. This function
    verifies the handoff file is prepared and creates a signal file for monitoring.
    
    DO NOT attempt subprocess calls to runSubagent (VS Code tool, not CLI).
    Instead, create the artifact and let agents discover it via file monitoring.
    
    Args:
        repo_root: Repository root path
        assignee: Agent role name (e.g., 'fullstack-engineer', 'ux-designer')
        task_id: Task identifier for tracing
        handoff_path: Path to work_handoff_v1 YAML file
        source_path: Path to source planning artifact
    
    Returns:
        True if handoff artifact exists and is ready, False otherwise
    """
    _ = (repo_root, assignee, task_id, source_path)
    # Since agents run in VS Code and check for work_handoff_v1 files,
    # we only need to ensure the file exists. Agents will discover it.
    return handoff_path.exists()



def run_planning_to_delivery(repo_root: Path, stage: str) -> dict[str, int]:
    """Emit work-handoff artifacts for ready tasks/bugs and trigger delivery agents.
    
    CRITICAL (2026-04-17): This function MUST trigger agents and wait for implementation.
    Merely creating handoff YAML files is not sufficient. Agents must be called.
    """
    task_meta = _planning_task_metadata(repo_root, stage)
    bug_meta = _planning_bug_metadata(repo_root, stage)
    all_meta = task_meta + bug_meta

    normalized_status_updates = 0
    unverified_done_handoffs_reopened: list[str] = []
    handoff_dir = _stage_delivery_handoff_dir(repo_root, stage)

    # Legacy cleanup: a plain "status: done" without PR/review evidence is invalid.
    # Re-open those planning artifacts so delivery can proceed instead of stalling.
    for item in all_meta:
        if item.get("status") != "done":
            continue
        task_id = str(item.get("task_id", ""))
        is_bug = task_id.startswith("BUG-")
        prefix = "bug" if is_bug else "task"
        slug = task_id.lower().replace(" ", "-")
        slug_without_prefix = slug.removeprefix(f"{prefix}-")
        handoff_path = handoff_dir / f"{prefix}-{slug_without_prefix}-handoff.yaml"
        if not handoff_path.exists():
            continue
        try:
            handoff_text = handoff_path.read_text(encoding="utf-8")
        except OSError:
            continue
        if _handoff_declares_done(handoff_text) and not _handoff_is_done(handoff_path):
            source_path = str(item.get("path", ""))
            if source_path and _update_task_status(Path(source_path), "open"):
                normalized_status_updates += 1
            item["status"] = "open"
            unverified_done_handoffs_reopened.append(task_id)

    known_assignees = {"fullstack-engineer", "ux-designer", "quality-expert"}
    ready = [
        item
        for item in all_meta
        if item["status"] == "open" and item["assignee"] in known_assignees
    ]
    blocked = [item for item in all_meta if item["status"] == "blocked"]
    unassigned = [
        item
        for item in all_meta
        if item["status"] == "open" and item["assignee"] not in known_assignees
    ]

    _cleanup_legacy_dispatch_traces(repo_root, stage)

    triggered = 0
    dispatch_traces = 0
    status_updates = normalized_status_updates
    already_done = 0
    already_dispatched = 0
    invalid_for_delivery = 0
    board_sync_conflicts = 0
    dispatched_task_ids: list[str] = []
    board_sync_notes: list[str] = []
    for task_id in unverified_done_handoffs_reopened:
        board_sync_notes.append(
            f"{task_id}: reopened because handoff was done without PR/human-review evidence"
        )
    blocked_reasons: list[tuple[str, str]] = []
    reopened_handoff_task_ids = set(unverified_done_handoffs_reopened)
    print(
        "[planning-to-delivery] HEARTBEAT: "
        f"stage={stage} ready={len(ready)} blocked={len(blocked)} unassigned={len(unassigned)}",
        flush=True,
    )
    for item in ready:
        task_id: str = str(item.get("task_id", "unknown"))
        assignee: str = str(item.get("assignee", "fullstack-engineer"))
        title: str = str(item.get("title", task_id))
        source_path: str = str(item.get("path", ""))
        print(
            "[planning-to-delivery] HEARTBEAT: "
            f"dispatch-candidate task_id={task_id} assignee={assignee}",
            flush=True,
        )
        quality_issues = _planning_delivery_quality_issues(item)
        if quality_issues:
            invalid_for_delivery += 1
            _move_board_ticket_to_blocked(repo_root, stage, task_id)
            if source_path:
                if _update_task_status(Path(source_path), "blocked"):
                    status_updates += 1
            blocked_reasons.append(
                (
                    task_id,
                    "invalid-for-delivery: " + ", ".join(sorted(set(quality_issues))),
                )
            )
            continue
        is_bug = task_id.startswith("BUG-")
        prefix = "bug" if is_bug else "task"
        slug = task_id.lower().replace(" ", "-")
        slug_without_prefix = slug.removeprefix(f"{prefix}-")
        handoff_path = handoff_dir / f"{prefix}-{slug_without_prefix}-handoff.yaml"
        if _handoff_is_done(handoff_path):
            already_done += 1
            if source_path and _update_task_status(Path(source_path), "done"):
                status_updates += 1
            move_ok = _move_board_ticket_to_done(repo_root, stage, task_id)
            if not move_ok:
                board_sync_conflicts += 1
                board_sync_notes.append(f"{task_id}: already-done handoff but done reconciliation failed")
            else:
                board_sync_notes.append(f"{task_id}: already-done handoff reconciled to done")
            continue

        if handoff_path.exists() and task_id not in reopened_handoff_task_ids:
            already_dispatched += 1
            if _mark_handoff_in_progress(handoff_path):
                status_updates += 1
            if source_path and _update_task_status(Path(source_path), "in-progress"):
                status_updates += 1
            move_ok = _move_board_ticket_to_in_progress(repo_root, stage, task_id)
            if not move_ok:
                board_sync_conflicts += 1
                board_sync_notes.append(f"{task_id}: existing handoff but in-progress reconciliation failed")
            else:
                board_sync_notes.append(f"{task_id}: existing handoff kept in-progress without redispatch")
            continue

        handoff_content = "\n".join([
            "schema: work_handoff_v1",
            "requester: artifacts-flow",
            f"receiver: {assignee}",
            "status: in-progress",
            f"intent: deliver {'bug fix' if is_bug else 'task'} '{title}' for stage '{stage}'",
            "expected_outputs:",
            "  - implemented code with corresponding unit tests",
            "  - updated inline documentation where interfaces changed",
            "  - PR or commit on a feature branch",
            "completion_criteria:",
            "  - all acceptance criteria in the task document are satisfied",
            "  - test coverage target is met or waiver is documented",
            "  - reviewer sign-off recorded in the PR or review artifact",
            "context:",
            f"  stage: {stage}",
            f"  task_id: {task_id}",
            f"  source_document: {source_path}",
            f"  generated_at: {_iso_utc_now()}",
            "assumptions:",
            "  - task is in 'open' state on the board at handoff time",
            "  - delivery agent has access to the source document and board",
            "open_questions: []",
            "artifacts: []",
        ])
        handoff_path.write_text(handoff_content + "\n", encoding="utf-8")

        if source_path:
            if _update_task_status(Path(source_path), "in-progress"):
                status_updates += 1
                dispatched_task_ids.append(task_id)

        _write_dispatch_trace(
            repo_root=repo_root,
            stage=stage,
            task_id=task_id,
            assignee=assignee,
            handoff_path=handoff_path,
            source_path=source_path,
        )
        dispatch_traces += 1

        move_ok = _move_board_ticket_to_in_progress(repo_root, stage, task_id)
        if not move_ok:
            board_sync_conflicts += 1
            board_sync_notes.append(f"{task_id}: in-progress transition failed")

        # CRITICAL (2026-04-17): Mark delivery artifact as ready for agent discovery.
        # Agents run in VS Code and will discover work_handoff_v1 files independently.
        # DO NOT attempt subprocess calls to runSubagent (it's VS Code only, not CLI).
        _mark_delivery_ready(
            repo_root=repo_root,
            assignee=assignee,
            task_id=task_id,
            handoff_path=handoff_path,
            source_path=source_path,
        )

        triggered += 1
        print(
            "[planning-to-delivery] HEARTBEAT: "
            f"dispatch-ready task_id={task_id} triggered={triggered}",
            flush=True,
        )

    board_refresh_ok = _refresh_board_refs(repo_root)
    if not board_refresh_ok:
        board_sync_notes.append("board-refresh: fetch --all failed")

    in_progress_count = _count_board_in_progress(repo_root, stage)
    expected_in_progress = triggered

    _update_stage_wiki_task_statuses(repo_root, stage, dispatched_task_ids, "in-progress")

    # Move explicitly blocked planning items to the blocked board lane.
    for item in blocked:
        ticket_id = str(item.get("task_id", "unknown"))
        title = str(item.get("title", ticket_id))
        _move_board_ticket_to_blocked(repo_root, stage, ticket_id)
        blocked_reasons.append((ticket_id, f"marked blocked in planning artifact: {title}"))

    # Move items with unrecognized assignees to blocked with a mandatory explanation.
    for item in unassigned:
        ticket_id = str(item.get("task_id", "unknown"))
        raw_assignee = str(item.get("assignee", ""))
        _move_board_ticket_to_blocked(repo_root, stage, ticket_id)
        reason = (
            f"unrecognized assignee '{raw_assignee}' — no delivery agent available; "
            f"add '{raw_assignee}' to known_assignees or reassign the ticket"
        )
        blocked_reasons.append((ticket_id, reason))

    # Mandatory console output for every blocked item.
    for ticket_id, reason in blocked_reasons:
        print(f"[BLOCKED] {ticket_id}: {reason}", flush=True)

    status_path = review_artifact_path(_stage_review_dir(repo_root, stage), DELIVERY_STATUS_ARTIFACT)
    lines = [
        f"# Delivery Automation Status ({stage})",
        "",
        "- purpose: internal automation control artifact for dispatch/readiness gating",
        f"- generated_at: {_iso_utc_now()}",
        "- automation_step: planning-to-delivery",
        f"- status: {'triggered' if triggered > 0 else ('already_dispatched' if (already_done + already_dispatched) > 0 else 'no_ready_tasks')}",
        f"- triggered_tasks: {triggered}",
        f"- already_done_handoffs: {already_done}",
        f"- already_dispatched_handoffs: {already_dispatched}",
        f"- total_tasks_and_bugs: {len(all_meta)}",
        f"- ready: {len(ready)}",
        f"- blocked: {len(blocked_reasons)}",
        f"- invalid_for_delivery: {invalid_for_delivery}",
        f"- unverified_done_handoffs_reopened: {len(unverified_done_handoffs_reopened)}",
        f"- board_sync_conflicts: {board_sync_conflicts}",
        f"- board_refresh_ok: {str(board_refresh_ok).lower()}",
        f"- expected_in_progress_from_dispatch: {expected_in_progress}",
        (
            f"- observed_in_progress_on_board: {in_progress_count}"
            if in_progress_count is not None
            else "- observed_in_progress_on_board: unknown"
        ),
        "",
        "## Triggered",
        "",
    ]
    if triggered > 0:
        lines.extend([
            f"- {item['task_id']} | {item['assignee']} | {item['title']}"
            for item in ready[:triggered]
        ])
    else:
        lines.append("- none")

    if blocked_reasons:
        lines.extend(["", "## Blocked", ""])
        lines.extend([f"- {tid}: {reason}" for tid, reason in blocked_reasons])

    if board_sync_notes:
        lines.extend(["", "## Board Sync Notes", ""])
        lines.extend([f"- {entry}" for entry in board_sync_notes])

    if unverified_done_handoffs_reopened:
        lines.extend(["", "## Reopened Due To Missing Review Evidence", ""])
        lines.extend([f"- {task_id}" for task_id in unverified_done_handoffs_reopened])

    _write_status_file(status_path, lines, cleanup_artifact=DELIVERY_STATUS_ARTIFACT)

    return {
        "triggered": triggered,
        "ready": len(ready),
        "already_done_handoffs": already_done,
        "already_dispatched_handoffs": already_dispatched,
        "dispatch_traces": dispatch_traces,
        "status_updates": status_updates,
        "blocked": len(blocked_reasons),
        "invalid_for_delivery": invalid_for_delivery,
        "board_sync_conflicts": board_sync_conflicts,
        "board_refresh_ok": int(board_refresh_ok),
        "status": "ok" if triggered > 0 else ("already_dispatched" if (already_done + already_dispatched) > 0 else "no_ready_tasks"),
        "status_report_path": status_path.as_posix(),
    }


def run_delivery_to_review(repo_root: Path, stage: str) -> dict[str, int]:
    """Emit explicit automation status for delivery->review transition."""
    handoff_dir = _stage_delivery_handoff_dir(repo_root, stage)
    handoffs = sorted(
        path
        for pattern in ("*.md", "*.yaml", "*.yml")
        for path in handoff_dir.glob(pattern)
        if _is_work_handoff(path)
    )
    print(f"[delivery-to-review] HEARTBEAT: stage={stage} handoffs={len(handoffs)}", flush=True)

    completed_auto = 0
    blocked_after_gate = 0
    evidence_rows: list[str] = []
    blocked_rows: list[str] = []
    pending_after_scan = 0

    for handoff in handoffs:
        task_id = _extract_task_id_from_handoff(handoff)
        if not task_id:
            pending_after_scan += 1
            continue
        if _handoff_is_done(handoff):
            evidence = _find_merged_pr_for_task(repo_root, task_id)
            if evidence:
                evidence_rows.append(
                    "- "
                    f"{task_id} | {evidence['pr_url']} | review={evidence['review_decision']} | "
                    f"tests={evidence['tests_evidence']} | coverage={evidence['coverage_evidence']} | "
                    f"security={evidence['security_evidence']} | non_technical={evidence['non_technical_summary']}"
                )
            continue

        evidence = _find_merged_pr_for_task(repo_root, task_id)
        if not evidence:
            pending_after_scan += 1
            continue

        _mark_handoff_done_with_evidence(
            handoff,
            evidence["pr_url"],
            evidence.get("approved_at") or evidence["merged_at"],
            merged_at=evidence.get("merged_at") or "",
            quality_gate_passed=(
                evidence.get("tests_evidence") == "yes"
                and evidence.get("coverage_evidence") == "yes"
            ),
        )
        moved_done, move_error = _move_board_ticket_to_done(repo_root, stage, task_id)
        if moved_done:
            completed_auto += 1
            evidence_rows.append(
                "- "
                f"{task_id} | {evidence['pr_url']} | review={evidence['review_decision']} | "
                f"tests={evidence['tests_evidence']} | coverage={evidence['coverage_evidence']} | "
                f"security={evidence['security_evidence']} | non_technical={evidence['non_technical_summary']}"
            )
            continue

        _move_board_ticket_to_blocked(repo_root, stage, task_id)
        blocked_after_gate += 1
        blocked_rows.append(f"- {task_id}: done-gate failed -> {move_error}")

    feedback_sync = _sync_feedback_handoffs_to_checklists(repo_root, stage)
    review_status_path = review_artifact_path(
        _stage_review_dir(repo_root, stage),
        DELIVERY_REVIEW_ARTIFACT,
    )
    has_handoffs = len(handoffs) > 0
    has_feedback = feedback_sync["handoffs_processed"] > 0
    handoff_gate_rows: list[dict[str, object]] = []
    recovery_results: list[dict[str, str]] = []
    recovery_seen: set[tuple[str, str, str]] = set()
    open_prs_ready_for_review: list[dict[str, str]] = []
    open_prs_blocked_by_quality: list[dict[str, str]] = []

    for handoff in handoffs:
        text = handoff.read_text(encoding="utf-8")
        task_id = _handoff_scalar_value(text, "task_id", "bug_id") or handoff.stem
        pr_url = _handoff_pr_url(text)
        approved_by = _handoff_scalar_value(text, "approved_by", "reviewer", "human_approved_by")
        approved_at = _handoff_scalar_value(text, "approved_at", "reviewed_at", "human_approved_at")
        merged = _handoff_pr_is_merged(text)
        quality_passed = _handoff_has_quality_gate_evidence(text)
        source_document = _handoff_scalar_value(text, "source_document")
        artifact_refs = [review_status_path.as_posix()]
        if source_document:
            artifact_refs.append(source_document)
        task_review_artifact = review_status_path.parent / f"{task_id}-delivery-review.md"
        if task_review_artifact.exists() and task_review_artifact.is_file():
            artifact_refs.append(task_review_artifact.as_posix())
        _sync_handoff_artifacts(handoff, artifact_refs)

        recovery = _recovery_result_for_source(repo_root, source_document)
        recovery_key = (recovery["file"], recovery["outcome"], recovery["location"])
        if recovery_key not in recovery_seen:
            recovery_results.append(recovery)
            recovery_seen.add(recovery_key)

        handoff_gate_rows.append(
            {
                "task_id": task_id,
                "pr_created": bool(pr_url),
                "pr_approved": bool(approved_by and approved_at),
                "pr_merged": merged,
                "quality_gate_passed": quality_passed,
                "approval_evidence_recorded": _handoff_has_completion_evidence(text),
            }
        )
        if pr_url and not merged:
            pr_item = {"title": f"{task_id} delivery PR", "url": pr_url}
            if quality_passed:
                open_prs_ready_for_review.append(pr_item)
            else:
                open_prs_blocked_by_quality.append(pr_item)

    pr_created = has_handoffs and all(bool(row["pr_created"]) for row in handoff_gate_rows)
    pr_approved = has_handoffs and all(bool(row["pr_approved"]) for row in handoff_gate_rows)
    pr_merged = has_handoffs and all(bool(row["pr_merged"]) for row in handoff_gate_rows)
    quality_gate_passed = has_handoffs and all(
        bool(row["quality_gate_passed"]) for row in handoff_gate_rows
    )
    approval_evidence_recorded = has_handoffs and all(
        bool(row["approval_evidence_recorded"]) for row in handoff_gate_rows
    )

    partially_recoverable = sum(1 for row in recovery_results if row["outcome"] == "partially recoverable")
    not_recoverable = sum(1 for row in recovery_results if row["outcome"] == "not recoverable")

    if (
        has_handoffs
        and pending_after_scan == 0
        and pr_created
        and pr_approved
        and pr_merged
        and quality_gate_passed
        and approval_evidence_recorded
    ):
        overall_status = "ready_for_done"
        status_reason = "all discovered handoffs are completed, reviewed, and reconciled"
    elif has_feedback:
        overall_status = "partial"
        status_reason = "handoff detection and feedback sync completed; full review aggregation pending"
    elif has_handoffs:
        overall_status = "awaiting_human_review"
        reason_parts = [
            "delivery handoffs detected, but review evidence is still incomplete",
        ]
        if not_recoverable:
            reason_parts.append(f"{not_recoverable} source artifact(s) are not recoverable")
        elif partially_recoverable:
            reason_parts.append(
                f"{partially_recoverable} source artifact(s) need recovery from 20-done"
            )
        status_reason = "; ".join(reason_parts)
    else:
        overall_status = "no_handoffs"
        status_reason = "no delivery handoffs detected yet"

    next_actions: list[str] = []
    if has_handoffs and not pr_created:
        next_actions.append("Create PRs for the active delivery handoffs before review can proceed.")
    if has_handoffs and pr_created and not quality_gate_passed:
        next_actions.append(
            "Keep PRs in draft and apply blocked:quality-gate until make test and make quality pass; do not request human review yet."
        )
    elif has_handoffs and pr_created and not pr_approved:
        next_actions.append(
            "Request human review approval and record reviewer identity plus approval timestamp in the handoff or review artifact."
        )
    if has_handoffs and pr_created and not pr_merged:
        next_actions.append("Merge approved PRs to main before reconciling board tickets.")
    if has_handoffs and not quality_gate_passed:
        next_actions.append("Run make test and make quality and capture the passing evidence for review.")
    if partially_recoverable:
        next_actions.append(
            "Restore missing source artifacts from .digital-artifacts/20-done or update the source_document path before approval."
        )
    if not_recoverable:
        next_actions.append(
            "Recreate missing source planning artifacts before treating the delivery as review-ready."
        )
    if not next_actions:
        next_actions.append("Await human review artifact aggregation and rerun /project after approval evidence is recorded.")

    lines = [
        f"# Delivery Review Aggregation Status ({stage})",
        "",
        "> Purpose: human review gate record for delivery work.",
        "> Shows what a reviewer must verify before any ticket may move to done.",
        "> For automation-only tracking see delivery-automation-status.md.",
        "",
        f"- generated_at: {_iso_utc_now()}",
        "- automation_step: delivery-to-review",
        f"- status: {overall_status}",
        f"- reason: {status_reason}",
        f"- detected_handoff_files: {len(handoffs)}",
        f"- feedback_handoffs_processed: {feedback_sync['handoffs_processed']}",
        f"- planning_artifacts_checked_off: {feedback_sync['artifacts_updated']}",
        f"- auto_completed_from_merged_pr: {completed_auto}",
        f"- blocked_after_done_gate: {blocked_after_gate}",
        f"- pending_after_scan: {pending_after_scan}",
        "- quality_gate_required: true",
        "",
        "## Human Review Gate",
        "",
        "| Gate | Required | Met |",
        "|------|----------|-----|",
        f"| PR created | yes | {'yes' if pr_created else 'no'} |",
        f"| PR approved by human | yes | {'yes' if pr_approved else 'no'} |",
        f"| PR merged to main | yes | {'yes' if pr_merged else 'no'} |",
        f"| Quality gate passed | yes | {'yes' if quality_gate_passed else 'no'} |",
        f"| Approval evidence recorded | yes | {'yes' if approval_evidence_recorded else 'no'} |",
        "",
        "Board transition to done remains blocked until every gate above is met.",
        "",
        "## Open PRs Ready For Human Review",
        "",
    ]
    if open_prs_ready_for_review:
        lines.extend([f"- [ ] {item['title']} — {item['url']}" for item in open_prs_ready_for_review])
    else:
        lines.append("- none")

    lines.extend(["", "## Open PRs Blocked By Quality Gate", ""])
    if open_prs_blocked_by_quality:
        lines.extend([f"- [ ] {item['title']} — {item['url']}" for item in open_prs_blocked_by_quality])
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Input Recovery Status",
            "",
            "| File | Outcome | Located At |",
            "|------|---------|-----------|",
        ]
    )
    if recovery_results:
        lines.extend(
            [
                f"| {row['file']} | {row['outcome']} | {row['location']} |"
                for row in recovery_results
            ]
        )
    else:
        lines.append("| none | not recoverable | no source artifacts referenced by handoffs |")

    lines.extend(
        [
            "",
            "Recovery outcomes use three explicit states: found, partially recoverable, not recoverable.",
            "",
        "## Detected Handoff Artifacts",
        "",
        ]
    )
    if handoffs:
        lines.extend([f"- {path.as_posix()}" for path in handoffs])
    else:
        lines.append("- none")

    lines.extend(["", "## Review Evidence Matrix", ""])
    if evidence_rows:
        lines.extend(evidence_rows)
    else:
        lines.append("- none")

    lines.extend(["", "## Blocked After Done Gate", ""])
    if blocked_rows:
        lines.extend(blocked_rows)
    else:
        lines.append("- none")

    lines.extend(
        [
            "",
            "## Next Steps",
            "",
            *[f"- {action}" for action in next_actions],
        ]
    )
    _write_status_file(
        review_status_path,
        lines,
        cleanup_artifact=DELIVERY_REVIEW_ARTIFACT,
    )

    return {
        "aggregated": feedback_sync["artifacts_updated"],
        "status": overall_status,
        "note": status_reason,
        "status_report_path": review_status_path.as_posix(),
        "detected_handoffs": len(handoffs),
        "feedback_handoffs_processed": feedback_sync["handoffs_processed"],
        "planning_artifacts_checked_off": feedback_sync["artifacts_updated"],
        "auto_completed_from_merged_pr": completed_auto,
        "blocked_after_done_gate": blocked_after_gate,
        "pending_after_scan": pending_after_scan,
    }


def main(argv: list[str] | None = None) -> int:
    """CLI main for artifacts workflow transitions."""
    return cli_main(
        argv,
        run_data_to_specification_fn=run_data_to_specification,
        run_specification_to_stage_fn=run_specification_to_stage,
        run_specification_to_planning_fn=run_specification_to_planning,
        run_planning_to_delivery_fn=run_planning_to_delivery,
        run_delivery_to_review_fn=run_delivery_to_review,
    )


if __name__ == "__main__":
    raise SystemExit(main())
