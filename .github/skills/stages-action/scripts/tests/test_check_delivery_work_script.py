from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "stages-action").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


def test_check_delivery_work_reports_pending_and_returns_nonzero(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "check-delivery-work.sh"

    handoff_dir = repo / ".digital-runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    pending_handoff = handoff_dir / "task-thm-01-handoff.yaml"
    pending_handoff.write_text(
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-01",
                "receiver: fullstack-engineer",
                "status: pending",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project"],
        cwd=repo,
        text=True,
        capture_output=True,
        env={"DIGITAL_REPO_ROOT": str(repo)},
        check=False,
    )

    assert result.returncode == 3
    assert "status=pending" in result.stdout

    report = repo / ".digital-artifacts" / "60-review"
    report_files = list(report.glob("*/project/CHECK_DELIVERY_WORK_STATUS.md"))
    assert report_files
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "- status: pending" in report_text
    assert "TASK-THM-01" in report_text


def test_check_delivery_work_reports_clear_when_all_done(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "check-delivery-work.sh"

    handoff_dir = repo / ".digital-runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    done_handoff = handoff_dir / "task-thm-02-handoff.yaml"
    done_handoff.write_text(
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-02",
                "receiver: fullstack-engineer",
                "status: done",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project"],
        cwd=repo,
        text=True,
        capture_output=True,
        env={"DIGITAL_REPO_ROOT": str(repo)},
        check=False,
    )

    assert result.returncode == 0
    assert "status=clear" in result.stdout

    report = repo / ".digital-artifacts" / "60-review"
    report_files = list(report.glob("*/project/CHECK_DELIVERY_WORK_STATUS.md"))
    assert report_files
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "- status: clear" in report_text
    assert "- pending_work_handoffs: 0" in report_text


def test_check_delivery_work_can_return_success_with_pending_override(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "check-delivery-work.sh"

    handoff_dir = repo / ".digital-runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    pending_handoff = handoff_dir / "task-thm-03-handoff.yaml"
    pending_handoff.write_text(
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-03",
                "receiver: fullstack-engineer",
                "status: pending",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project"],
        cwd=repo,
        text=True,
        capture_output=True,
        env={
            "DIGITAL_REPO_ROOT": str(repo),
            "CHECK_DELIVERY_WORK_EXIT_PENDING": "0",
        },
        check=False,
    )

    assert result.returncode == 0
    assert "status=pending" in result.stdout


def test_check_delivery_work_marks_missing_source_handoffs_as_stale(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "check-delivery-work.sh"

    handoff_dir = repo / ".digital-runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    stale_handoff = handoff_dir / "task-thm-99-handoff.yaml"
    stale_handoff.write_text(
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-99",
                "receiver: fullstack-engineer",
                f"source_document: {repo / '.digital-artifacts' / '50-planning' / 'project' / 'TASK_THM-99.md'}",
                "status: pending",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project"],
        cwd=repo,
        text=True,
        capture_output=True,
        env={"DIGITAL_REPO_ROOT": str(repo)},
        check=False,
    )

    assert result.returncode == 0
    assert "stale=1" in result.stdout

    report = repo / ".digital-artifacts" / "60-review"
    report_files = list(report.glob("*/project/CHECK_DELIVERY_WORK_STATUS.md"))
    assert report_files
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "- pending_work_handoffs: 0" in report_text
    assert "- stale_work_handoffs: 1" in report_text
    assert "TASK-THM-99" in report_text
    assert "status=stale" in report_text


def test_check_delivery_work_reports_review_lane_and_quality_details(tmp_path: Path) -> None:
    repo = tmp_path
    script = _repo_root() / ".github" / "skills" / "stages-action" / "scripts" / "check-delivery-work.sh"

    handoff_dir = repo / ".digital-runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    active_blocked = handoff_dir / "task-thm-01-handoff.yaml"
    active_blocked.write_text(
        "\n".join(
            [
                "schema: work_handoff_v1",
                "task_id: TASK-THM-01",
                "receiver: fullstack-engineer",
                "status: in-progress",
                "pr_url: https://github.com/example/repo/pull/101",
                "quality_gate_passed: false",
                "make_test_status: fail",
                "make_quality_status: fail",
                "blocker: failing quality gate",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        ["bash", str(script), "project"],
        cwd=repo,
        text=True,
        capture_output=True,
        env={"DIGITAL_REPO_ROOT": str(repo)},
        check=False,
    )

    assert result.returncode == 0
    assert "active_blocked_for_review=1" in result.stdout

    report = repo / ".digital-artifacts" / "60-review"
    report_files = list(report.glob("*/project/CHECK_DELIVERY_WORK_STATUS.md"))
    assert report_files
    report_text = report_files[0].read_text(encoding="utf-8")
    assert "- active_ready_for_review: 0" in report_text
    assert "- active_blocked_for_review: 1" in report_text
    assert "## Active Blocked For Review" in report_text
    assert "lane=blocked:quality-gate" in report_text
    assert "make_test=fail" in report_text
    assert "make_quality=fail" in report_text
