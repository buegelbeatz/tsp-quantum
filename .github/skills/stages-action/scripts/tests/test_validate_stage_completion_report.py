from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
REPORT_FILENAME = "stage-completion-status.md"


def _load_module():
    import importlib.util
    import sys

    script_path = ROOT / "scripts" / "validate_stage_completion_report.py"
    spec = importlib.util.spec_from_file_location("validate_stage_completion_report", script_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["validate_stage_completion_report"] = module
    spec.loader.exec_module(module)
    return module


def _report_content(stage: str, generated_at: datetime) -> str:
    is_project = stage == "project"
    ppt_bool = "true" if is_project else "false"
    return "\n".join(
        [
            f"# Stage Completion Status ({stage})",
            "",
            f"- generated_at: {generated_at.isoformat().replace('+00:00', 'Z')}",
            f"- stage: {stage}",
            "- dry_run_mode: false",
            "- agile_coach_first: true",
            "- progress_steps: \"1/6 ..., 6/6 ...\"",
            "- pr_open_total: 0",
            "- pr_merged_total: 0",
            "- pr_approved_merged_total: 0",
            f"- powerpoint_required: {ppt_bool}",
            f"- powerpoint_post_gate_executed: {ppt_bool}",
            f"- powerpoint_regenerated: {ppt_bool}",
            "- powerpoint_generated_at: 2026-04-21T12:00:00Z",
            "- powerpoint_wiki_exists: true",
            "- powerpoint_source_exists: true",
            "- powerpoint_hash_match: true",
            "",
            "## PR Status by Ticket",
            "",
            "- TASK-THM-01: open_prs=1 [#123 https://github.com/example/repo/pull/123 | Example open PR] | merged_prs=0 [none] | approved_merged=no",
            "",
            "## Completed Successfully",
            "",
            "- PRO-THM-01-TASK: completed and reconciled on board=done | merged_prs=[#122 https://github.com/example/repo/pull/122 | Example merged PR] | human_approval=recorded",
            "",
            "## Approval Links Requiring Re-run",
            "",
            "- PRO-THM-02-TASK: #124 https://github.com/example/repo/pull/124 | Approved follow-up PR | rerun_required=/project to reconcile approval and fully close the ticket",
            "",
            "## Not Completed and Why",
            "",
            "- PRO-THM-03-TASK -> handoff is in-progress for fullstack-engineer (.digital-runtime/handoffs/project/task-thm-03-handoff.yaml); waiting for implementation and review",
            "",
            "## Recommendations",
            "",
            "- Review why-not-progressing.md and unblock remaining board items before the next /project run",
            "",
        ]
    )


def test_validate_report_accepts_fresh_report(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    report = tmp_path / REPORT_FILENAME
    report.write_text(_report_content(stage, datetime.now(timezone.utc)), encoding="utf-8")

    module.validate_report(report, stage, max_age_hours=24)


def test_validate_report_rejects_stale_report(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    report = tmp_path / REPORT_FILENAME
    stale = datetime.now(timezone.utc) - timedelta(hours=30)
    report.write_text(_report_content(stage, stale), encoding="utf-8")

    with pytest.raises(ValueError, match="stale"):
        module.validate_report(report, stage, max_age_hours=24)


def test_latest_report_path_resolves_latest_day(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    old_report = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-19"
        / stage
        / REPORT_FILENAME
    )
    new_report = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-20"
        / stage
        / REPORT_FILENAME
    )
    old_report.parent.mkdir(parents=True, exist_ok=True)
    new_report.parent.mkdir(parents=True, exist_ok=True)
    old_report.write_text("x", encoding="utf-8")
    new_report.write_text("y", encoding="utf-8")

    resolved = module.latest_report_path(tmp_path, stage)
    assert resolved == new_report


def test_validate_report_rejects_project_without_powerpoint_post_gate(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    report = tmp_path / REPORT_FILENAME
    content = _report_content(stage, datetime.now(timezone.utc)).replace(
        "- powerpoint_post_gate_executed: true",
        "- powerpoint_post_gate_executed: false",
    )
    report.write_text(content, encoding="utf-8")

    with pytest.raises(ValueError, match="PowerPoint post-gate"):
        module.validate_report(report, stage, max_age_hours=24)


def test_validate_report_allows_dry_run_without_powerpoint_post_gate(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    report = tmp_path / REPORT_FILENAME
    content = _report_content(stage, datetime.now(timezone.utc))
    content = content.replace("- dry_run_mode: false", "- dry_run_mode: true")
    content = content.replace(
        "- powerpoint_post_gate_executed: true",
        "- powerpoint_post_gate_executed: false",
    )
    content = content.replace("- powerpoint_wiki_exists: true", "- powerpoint_wiki_exists: false")
    content = content.replace("- powerpoint_source_exists: true", "- powerpoint_source_exists: false")
    content = content.replace("- powerpoint_hash_match: true", "- powerpoint_hash_match: false")
    report.write_text(content, encoding="utf-8")

    module.validate_report(report, stage, max_age_hours=24)


def test_validate_report_allows_project_noop_without_powerpoint_post_gate(tmp_path: Path) -> None:
    module = _load_module()
    stage = "project"
    report = tmp_path / REPORT_FILENAME
    content = _report_content(stage, datetime.now(timezone.utc))
    content = content.replace("- powerpoint_required: true", "- powerpoint_required: false")
    content = content.replace(
        "- powerpoint_post_gate_executed: true",
        "- powerpoint_post_gate_executed: false",
    )
    content = content.replace("- powerpoint_wiki_exists: true", "- powerpoint_wiki_exists: false")
    content = content.replace("- powerpoint_source_exists: true", "- powerpoint_source_exists: false")
    content = content.replace("- powerpoint_hash_match: true", "- powerpoint_hash_match: false")
    report.write_text(content, encoding="utf-8")

    module.validate_report(report, stage, max_age_hours=24)
