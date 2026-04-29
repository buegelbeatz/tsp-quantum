"""Contract tests for the canonical /stages-action state-machine documentation."""

from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "stages-action").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


def test_canonical_state_machine_actions_match_runtime_script() -> None:
    """Canonical action names must stay aligned between YAML contract and shell runtime."""
    repo_root = _repo_root()
    state_machine = (
        repo_root / ".github" / "skills" / "stages-action" / "state-machine.yaml"
    ).read_text(encoding="utf-8")
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    canonical_actions = re.findall(r'^\s*action:\s*"([^"]+)"\s*$', state_machine, flags=re.MULTILINE)
    runtime_actions = set(re.findall(r"action=([a-z0-9\-]+)", script_text))

    assert canonical_actions
    for action in canonical_actions:
        assert action in runtime_actions


def test_state_machine_contract_enforces_review_flow_visibility() -> None:
    """Prompt, skill, and runtime script must consistently declare ExistingProjectFlow review follow-up."""
    repo_root = _repo_root()
    prompt_text = (
        repo_root / ".github" / "prompts" / "stages-action.prompt.md"
    ).read_text(encoding="utf-8")
    skill_text = (
        repo_root / ".github" / "skills" / "stages-action" / "SKILL.md"
    ).read_text(encoding="utf-8")
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "ExistingProjectFlow" in prompt_text
    assert "follow-up" in prompt_text.lower()
    assert "ExistingProjectFlow" in skill_text
    assert "follow-up" in skill_text.lower()
    assert "delivery review status" in script_text.lower()
    assert "why-not-progressing.md" in script_text
    assert "stage-handoff.md" in script_text
    assert "OBSERVABILITY ready_for_planning" in script_text


def test_stage_runtime_blocks_on_workflow_code_debt_regression() -> None:
    """Runtime must enforce workflow code debt monotonicity as a hard completion gate."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "_enforce_workflow_code_debt_gate" in script_text
    assert "workflow_code_debt_monotonic_status" in script_text
    assert "regression-detected" in script_text
    assert "blocking stage completion" in script_text


def test_stage_runtime_enforces_mandatory_github_sync_gate() -> None:
    """Runtime must hard-fail when board/wiki/powerpoint GitHub sync is incomplete."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "_enforce_mandatory_primary_sync_gate" in script_text
    assert "mandatory GitHub sync gate failed" in script_text
    assert "refs/board/${STAGE}" in script_text
    assert "wiki cache repository missing" in script_text
    assert "Project-Summary.pptx" in script_text
    assert 'git ls-remote origin "refs/board/${STAGE}/*"' in script_text
    assert 'git ls-remote --heads origin "refs/board/${STAGE}/*"' not in script_text


def test_stage_runtime_allows_project_noop_runs_to_skip_sync_gate() -> None:
    """Project runs with no selected bundles must not fail the GitHub sync gate for missing dispatch traces."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "mandatory GitHub sync gate skipped for no-op stage" in script_text
    assert "_is_noop_stage_run()" in script_text
    assert '"$(_latest_delivery_status)" == "no_ready_tasks"' in script_text
    assert '"${selected_count:-0}" == "0"' in script_text
    assert '"${blocked_count:-0}" == "0"' in script_text


def test_stage_runtime_emits_completion_brief_sections() -> None:
    """Runtime must print dedicated completion brief sections after /project execution."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")
    template_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "templates"
        / "completion-brief.txt"
    ).read_text(encoding="utf-8")

    assert "_print_stage_completion_brief" in script_text
    assert "completion-brief.txt" in script_text
    assert "[stages-action][brief] where-we-stand:" in template_text
    assert "[stages-action][brief] github-sync:" in template_text
    assert "[stages-action][brief] pull-requests:" in script_text
    assert "[stages-action][brief] completed:" in script_text
    assert "[stages-action][brief] approval-links:" in script_text
    assert "[stages-action][brief] not-completed:" in script_text
    assert "[stages-action][brief] recommendations:" in script_text
    assert "_board_ticket_reason_lines" in script_text
    assert "why-${state}" in script_text
    assert "_handoff_state_for_board_ticket" in script_text
    assert ".digital-runtime/handoffs/${STAGE}" in script_text
    assert "Delivery handoffs were generated and checked." in script_text
    assert "_planning_artifact_path_for_board_ticket" not in script_text
    assert "## Completed Successfully" in script_text
    assert "## Approval Links Requiring Re-run" in script_text
    assert "## Not Completed and Why" in script_text
    assert "## Recommendations" in script_text
    assert "# Stage Handoff" in script_text


def test_stage_runtime_marks_internal_artifact_ingest_calls() -> None:
    """Internal-only artifact prompts must be invoked through the runtime bypass inside /project."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert 'PROMPT_INTERNAL_CALL=1 bash "$ARTIFACTS_SCRIPTS_DIR/artifacts-input-2-data.sh"' in script_text


def test_stage_runtime_avoids_nested_make_invocations() -> None:
    """Stage runtime should avoid nested make orchestration and call scoped scripts directly."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert 'make -C "$REPO_ROOT"' not in script_text
    assert 'bash "$BOARD_CLEANUP_SCRIPT" --board "$STAGE" --remote --yes' in script_text


def test_stage_runtime_project_post_gate_uses_project_briefing_file() -> None:
    """Project post-gate must publish the freshly generated project briefing, not the stale 40-stage deck."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "digital-generic-team_project.pptx" in script_text
    assert "_sync_project_wiki_post_gate" in script_text
    assert 'ppt_source_path="$REPO_ROOT/$(_project_powerpoint_source_relpath)"' in script_text
    assert "digital-generic-team_40-stage.pptx" not in script_text


def test_validates_stage_skill_dependencies_before_execution() -> None:
    """Stage frontdoor targets must enforce preflight dependency checks before execution."""
    repo_root = _repo_root()
    commands_text = (repo_root / ".github" / "make" / "commands.mk").read_text(encoding="utf-8")

    assert "stages-action: preflight" in commands_text
    assert "project: preflight" in commands_text
    assert "exploration: preflight" in commands_text


def test_exports_dependency_validation_evidence_in_completion_report() -> None:
    """Runtime completion evidence must include observability lines for stage gate outcomes."""
    repo_root = _repo_root()
    script_text = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "scripts"
        / "stages-action.sh"
    ).read_text(encoding="utf-8")

    assert "OBSERVABILITY ready_for_planning" in script_text
    assert "workflow_code_debt_monotonic_status" in script_text
    assert "mandatory GitHub sync gate failed" in script_text


def test_commands_frontdoor_runs_dependency_validation_for_stage_targets() -> None:
    """Canonical stage frontdoors must route through preflight before stage runtime."""
    repo_root = _repo_root()
    commands_text = (repo_root / ".github" / "make" / "commands.mk").read_text(encoding="utf-8")

    assert "check-delivery-work: preflight" in commands_text
    assert "project-e2e: preflight" in commands_text
    assert "bash $(_STAGES_ACTION_SCRIPT)" in commands_text
