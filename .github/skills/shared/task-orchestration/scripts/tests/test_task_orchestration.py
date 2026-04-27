"""Unit tests for task orchestration shell scripts (assign, validate, approve)."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
LAYER_ROOT = Path(__file__).resolve().parents[4]
ASSIGN = ROOT / "scripts" / "task-assign.sh"
VALIDATE = ROOT / "scripts" / "task-validate-handoff.sh"
APPROVE = ROOT / "scripts" / "task-approve-gate.sh"
AUDIT = ROOT / "scripts" / "task-audit-log.sh"
HOOKS_INSTALL = ROOT / "scripts" / "task-hooks-install.sh"
HOOKS_RUN = ROOT / "scripts" / "task-hooks-run.sh"
AUDIT_TOGGLE = ROOT / "scripts" / "task-audit-toggle.sh"
PROMPT_INVOKE = LAYER_ROOT / "hooks" / "prompt-invoke.sh"
GOVERNANCE = (
    LAYER_ROOT / "skills" / "shared/shell" / "scripts" / "lib" / "governance.sh"
)
COMMON = LAYER_ROOT / "skills" / "shared/shell" / "scripts" / "lib" / "common.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run a task orchestration script with given arguments.

    Args:
        script: Path to the script to run.
        *args: Command-line arguments for the script.

    Returns:
        subprocess.CompletedProcess[str]: Result of script execution.
    """
    env = os.environ.copy()
    env.setdefault("DIGITAL_AUDIT_ENABLED", "1")
    return subprocess.run(
        ["/bin/bash", str(script), *args],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def test_task_assign_success() -> None:
    """Test that task-assign.sh successfully assigns task with valid arguments."""
    result = _run(
        ASSIGN,
        "--role",
        "fullstack-engineer",
        "--task-id",
        "TASK-100",
        "--owner-agent",
        "agile-coach",
    )
    assert result.returncode == 0
    assert 'stage: "assigned"' in result.stdout
    assert 'task_id: "TASK-100"' in result.stdout


def test_task_assign_missing_required() -> None:
    """Test that task-assign.sh validates required arguments."""
    result = _run(ASSIGN, "--role", "fullstack-engineer")
    assert result.returncode != 0
    assert "--task-id is required" in result.stderr


def test_task_validate_handoff_success(tmp_path: Path) -> None:
    """TODO: add docstring for test_task_validate_handoff_success."""
    payload = tmp_path / "handoff.yaml"
    schema = tmp_path / "schema.yaml"

    payload.write_text("task_id: TASK-100\n", encoding="utf-8")
    schema.write_text("required:\n  - task_id\n", encoding="utf-8")

    result = _run(
        VALIDATE,
        "--task-id",
        "TASK-100",
        "--handoff",
        str(payload),
        "--schema",
        str(schema),
    )
    assert result.returncode == 0
    assert 'stage: "validating"' in result.stdout
    assert 'status: "ok"' in result.stdout


def test_task_validate_handoff_missing_file(tmp_path: Path) -> None:
    """TODO: add docstring for test_task_validate_handoff_missing_file."""
    missing = tmp_path / "missing.yaml"
    schema = tmp_path / "schema.yaml"
    schema.write_text("required:\n  - task_id\n", encoding="utf-8")

    result = _run(
        VALIDATE,
        "--task-id",
        "TASK-100",
        "--handoff",
        str(missing),
        "--schema",
        str(schema),
    )
    assert result.returncode != 0
    assert "Handoff payload not found" in result.stdout


def test_task_approve_gate_requires_approval() -> None:
    """Test that task-approve-gate.sh enforces approval requirement."""
    result = _run(
        APPROVE,
        "--task-id",
        "TASK-100",
        "--role",
        "fullstack-engineer",
        "--approvers",
        "maintainers",
    )
    assert result.returncode == 0
    assert 'stage: "approval_gate"' in result.stdout
    assert 'status: "requires_approval"' in result.stdout


def test_task_audit_log_full_generates_required_structure(tmp_path: Path) -> None:
    """TODO: add docstring for test_task_audit_log_full_generates_required_structure."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-401",
        "--role",
        "developer",
        "--action",
        "handoff",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--handoff-file",
        "handoff.yaml",
        "--assumptions",
        "none",
        "--open-questions",
        "none",
        "--artifacts",
        "a.md,b.md",
    )

    assert result.returncode == 0
    assert 'kind: "task_audit_log"' in result.stdout
    expected = audits_root / "2026-03-27" / "00000.audit.md"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "## Event: handoff (handoff)" in content
    assert "### Handoff Status" in content
    assert "- status: present" in content
    assert "- handoff_file: handoff.yaml" in content
    assert "- a.md" in content


def test_task_audit_log_marks_missing_required_handoff(tmp_path: Path) -> None:
    """Test that full audit marks missing handoff when multiple agents are involved."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-499",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--handoff-expected",
        "yes",
        "--agents-trace",
        "copilot, quality-expert",
        "--communication-flow",
        "copilot -> quality-expert;quality-expert -> task-audit-log",
        "--timing-total-ms",
        "230",
        "--timing-command-ms",
        "180",
    )

    assert result.returncode == 0
    expected = audits_root / "2026-03-27" / "00000.audit.md"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "## Session Result" in content
    assert "- required: yes" in content
    assert "- status: missing_required_handoff" in content
    assert "- Runtime: 230 ms" in content
    assert "### Flow Visualization" in content
    assert "![Communication flow](./00000/sequence-flow.svg)" in content

    flow_svg = audits_root / "2026-03-27" / "00000" / "sequence-flow.svg"
    assert flow_svg.exists()
    flow_svg_content = flow_svg.read_text(encoding="utf-8")
    assert "<svg" in flow_svg_content
    assert "Sequence Diagram" in flow_svg_content
    assert 'x1="282,143"' not in flow_svg_content


def test_task_audit_log_decodes_html_summary_entities(tmp_path: Path) -> None:
    """Summary text should decode HTML entities before markdown and SVG rendering."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-500",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--notes",
        "event=post-message summary=/quality -&gt; quality-expert-orchestrator",
        "--communication-flow",
        "user -> copilot: /quality;copilot -> audit-log: persist",
    )

    assert result.returncode == 0
    expected = audits_root / "2026-03-27" / "00000.audit.md"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "- Executed command: /quality -> quality-expert-orchestrator" in content
    assert "-&gt;" not in content

    flow_svg = audits_root / "2026-03-27" / "00000" / "sequence-flow.svg"
    assert flow_svg.exists()
    flow_svg_content = flow_svg.read_text(encoding="utf-8")
    assert "/quality -&gt; quality-expert-orchestrator" in flow_svg_content
    assert "-&amp;gt;" not in flow_svg_content
    assert "->gt;" not in flow_svg_content


def test_task_audit_log_uses_explicit_status_summary_and_next_step(tmp_path: Path) -> None:
    """Explicit stage status details should override the generic audit fallback text."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-510",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--status-summary",
        "board=project; backlog=2; in_progress=0; blocked=0; done=0; ready_tasks=2; triggered_tasks=2; delivery=triggered",
        "--next-step",
        "Await delivery execution results for the triggered board tickets and collect follow-up review artifacts.",
    )

    assert result.returncode == 0
    expected = audits_root / "2026-03-27" / "00000.audit.md"
    assert expected.exists()
    content = expected.read_text(encoding="utf-8")
    assert "- Status signal: board=project; backlog=2; in_progress=0; blocked=0; done=0; ready_tasks=2; triggered_tasks=2; delivery=triggered" in content
    assert "- Recommended next step: Await delivery execution results for the triggered board tickets and collect follow-up review artifacts." in content


def test_task_audit_log_marks_not_required_handoffs_cleanly(tmp_path: Path) -> None:
    """Non-handoff runs should not claim inline evidence for handoff data."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-511",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--assumptions",
        "Stage pipeline executed with curated runtime signals.",
    )

    assert result.returncode == 0
    content = (audits_root / "2026-03-27" / "00000.audit.md").read_text(
        encoding="utf-8"
    )
    assert "- status: not_applicable" in content
    assert "- evidence: not_required" in content
    assert "inline_fields_or_protocol" not in content


def test_task_audit_log_summarizes_large_artifact_sets(tmp_path: Path) -> None:
    """Large artifact lists should be summarized instead of dumped in full."""
    audits_root = tmp_path / "audits"
    artifacts = ", ".join(
        [f".digital-artifacts/30-specification/2026-03-27/{index:05d}.md" for index in range(14)]
    )
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-512",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--artifacts",
        artifacts,
    )

    assert result.returncode == 0
    content = (audits_root / "2026-03-27" / "00000.audit.md").read_text(
        encoding="utf-8"
    )
    assert "- Artifact signal: 14 curated artifact(s) captured for this run." in content
    assert "#### Artifact Overview" in content
    assert "- total: 14" in content
    assert "  - .digital-artifacts/30-specification: 14" in content
    assert "#### Key Artifacts" in content
    assert "- ... 2 more omitted from the detailed list" in content


def test_task_audit_log_embeds_collapsible_handoff_snippets(tmp_path: Path) -> None:
    """Audit markdown should include collapsible snippets for runtime handoff payloads."""
    audits_root = tmp_path / "audits"
    handoff_dir = tmp_path / "runtime" / "handoffs" / "project"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    request_file = handoff_dir / "sample-request.yaml"
    request_file.write_text(
        "\n".join(
            [
                "schema: expert_request_v1",
                "requester: agile-coach",
                "receiver: quality-expert",
                "intent: Validate delivery quality risks",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    response_file = handoff_dir / "sample-response.yaml"
    response_file.write_text(
        "\n".join(
            [
                "schema: expert_response_v1",
                "responder: quality-expert",
                "recommendation: proceed_with_guardrails",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    artifacts = f"{request_file}, {response_file}"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-513",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--artifacts",
        artifacts,
    )

    assert result.returncode == 0
    content = (audits_root / "2026-03-27" / "00000.audit.md").read_text(
        encoding="utf-8"
    )
    assert "### Handoff Snippets" in content
    assert "<summary>expert_request_v1:" in content
    assert "<summary>expert_response_v1:" in content
    assert "```yaml" in content
    assert "schema: expert_request_v1" in content
    assert "schema: expert_response_v1" in content


def test_task_audit_log_wraps_long_actor_labels(tmp_path: Path) -> None:
    """Long actor labels should wrap into multiple SVG tspans instead of overflowing."""
    audits_root = tmp_path / "audits"
    result = _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-777",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-03-27",
        "--communication-flow",
        "user -> artifacts-specification-2-planning(project);artifacts-specification-2-planning(project) -> generic-deliver sub-agents",
    )

    assert result.returncode == 0
    flow_svg = audits_root / "2026-03-27" / "00000" / "sequence-flow.svg"
    assert flow_svg.exists()
    flow_svg_content = flow_svg.read_text(encoding="utf-8")
    assert "artifacts-specification" in flow_svg_content
    assert "<tspan" in flow_svg_content
    assert "dy=\"13\"" in flow_svg_content
    assert "sub-agents</tspan>" in flow_svg_content


def test_task_hooks_install_and_run_short_audit(tmp_path: Path) -> None:
    """TODO: add docstring for test_task_hooks_install_and_run_short_audit."""
    repo_dir = tmp_path / "repo"
    git_dir = repo_dir / ".git" / "hooks"
    repo_dir.mkdir(parents=True)
    git_dir.mkdir(parents=True)

    install_result = subprocess.run(
        ["/bin/bash", str(HOOKS_INSTALL)],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )
    assert install_result.returncode == 0
    assert 'kind: "task_hooks_install"' in install_result.stdout
    assert (git_dir / "pre-commit").exists()
    assert (git_dir / "post-commit").exists()

    audits_root = repo_dir / ".digital-artifacts" / "70-audits"
    run_result = _run(
        HOOKS_RUN,
        "--hook",
        "custom-workflow",
        "--task-id",
        "TASK-402",
        "--mode",
        "short",
        "--audits-root",
        str(audits_root),
    )
    assert run_result.returncode == 0
    assert 'kind: "task_audit_log"' in run_result.stdout
    generated = list(audits_root.glob("**/*.audit.md"))
    assert generated


def test_task_audit_toggle_on_off_status(tmp_path: Path) -> None:
    """Test that audit toggle persists state and reports deterministic status."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)

    on_result = _run(AUDIT_TOGGLE, "--repo-root", str(repo_dir), "--state", "on")
    assert on_result.returncode == 0
    assert 'enabled: "1"' in on_result.stdout

    status_on = _run(AUDIT_TOGGLE, "--repo-root", str(repo_dir), "--state", "status")
    assert status_on.returncode == 0
    assert 'enabled: "1"' in status_on.stdout

    off_result = _run(AUDIT_TOGGLE, "--repo-root", str(repo_dir), "--state", "off")
    assert off_result.returncode == 0
    assert 'enabled: "0"' in off_result.stdout

    status_off = _run(AUDIT_TOGGLE, "--repo-root", str(repo_dir), "--state", "status")
    assert status_off.returncode == 0
    assert 'enabled: "0"' in status_off.stdout


def test_task_audit_toggle_status_defaults_enabled(tmp_path: Path) -> None:
    """Test that audit status defaults to enabled when no state file exists."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir(parents=True)

    status_default = _run(
        AUDIT_TOGGLE, "--repo-root", str(repo_dir), "--state", "status"
    )
    assert status_default.returncode == 0
    assert 'enabled: "1"' in status_default.stdout


def test_prompt_invoke_calls_primary_github_hooks(tmp_path: Path) -> None:
    """TODO: add docstring for test_prompt_invoke_calls_primary_github_hooks."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    github_hooks = repo_dir / ".github" / "hooks"
    github_hooks.mkdir(parents=True)
    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)

    (github_hooks / "pre-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\n' \"$*\" > pre.log\n",
        encoding="utf-8",
    )
    (github_hooks / "post-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\n' \"$*\" > post.log\n",
        encoding="utf-8",
    )
    (digital_team_lib / "governance.sh").write_text(
        GOVERNANCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        COMMON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = subprocess.run(
        [
            "/bin/bash",
            str(PROMPT_INVOKE),
            "--prompt-name",
            "update",
            "--message-id",
            "msg-123",
            "--summary",
            "Run update",
            "--",
            "/bin/sh",
            "-c",
            "exit 0",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 0
    assert (repo_dir / "pre.log").exists()
    assert (repo_dir / "post.log").exists()
    assert "--message-id msg-123 --summary Run update" in (
        repo_dir / "pre.log"
    ).read_text(encoding="utf-8")
    assert "--message-id msg-123 --summary Run update --status ok" in (
        repo_dir / "post.log"
    ).read_text(encoding="utf-8")


def test_prompt_invoke_skips_hooks_when_audit_disabled(tmp_path: Path) -> None:
    """Test that prompt-invoke bypasses hook execution when audit is disabled."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    github_hooks = repo_dir / ".github" / "hooks"
    github_hooks.mkdir(parents=True)
    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)

    (github_hooks / "pre-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n: > pre.log\n",
        encoding="utf-8",
    )
    (github_hooks / "post-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n: > post.log\n",
        encoding="utf-8",
    )
    (digital_team_lib / "governance.sh").write_text(
        GOVERNANCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        COMMON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    state_dir = repo_dir / ".digital-runtime" / "layers" / repo_dir.name / "audit"
    state_dir.mkdir(parents=True)
    (state_dir / "state.env").write_text("DIGITAL_AUDIT_ENABLED=0\n", encoding="utf-8")

    # Remove DIGITAL_AUDIT_ENABLED from env so the state.env file drives the check
    env_without_flag = {
        k: v for k, v in os.environ.items() if k != "DIGITAL_AUDIT_ENABLED"
    }
    result = subprocess.run(
        [
            "/bin/bash",
            str(PROMPT_INVOKE),
            "--prompt-name",
            "quality-fix",
            "--",
            "/bin/sh",
            "-c",
            "exit 0",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
        env=env_without_flag,
    )

    assert result.returncode == 0
    assert not (repo_dir / "pre.log").exists()
    assert not (repo_dir / "post.log").exists()


def test_prompt_invoke_prints_failure_guidance(tmp_path: Path) -> None:
    """Prompt wrapper should emit actionable guidance when wrapped command fails."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    github_hooks = repo_dir / ".github" / "hooks"
    github_hooks.mkdir(parents=True)
    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)

    (github_hooks / "pre-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n",
        encoding="utf-8",
    )
    (github_hooks / "post-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n",
        encoding="utf-8",
    )
    (digital_team_lib / "governance.sh").write_text(
        GOVERNANCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        COMMON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = subprocess.run(
        [
            "/bin/bash",
            str(PROMPT_INVOKE),
            "--prompt-name",
            "exploration",
            "--",
            "/bin/sh",
            "-c",
            "exit 7",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 7
    assert "[prompt-invoke] ERROR: /exploration failed" in result.stderr
    assert "[prompt-invoke] NEXT: check command output above" in result.stderr


def test_prompt_invoke_blocks_internal_only_prompts_for_user_calls(
    tmp_path: Path,
) -> None:
    """Prompt invoke should reject internal-only prompts unless explicitly bypassed."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    prompt_invoke = Path(__file__).resolve().parents[6] / ".github" / "hooks" / "prompt-invoke.sh"
    result = subprocess.run(
        [
            "/bin/bash",
            str(prompt_invoke),
            "--prompt-name",
            "powerpoint",
            "--",
            "/bin/sh",
            "-c",
            "exit 0",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 2
    assert "is internal-only and not user-invocable" in result.stderr


def test_prompt_invoke_allows_internal_only_prompts_with_internal_flag(
    tmp_path: Path,
) -> None:
    """Prompt invoke should allow internal-only prompts when orchestration sets bypass."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    env = os.environ.copy()
    env["PROMPT_INTERNAL_CALL"] = "1"
    prompt_invoke = Path(__file__).resolve().parents[6] / ".github" / "hooks" / "prompt-invoke.sh"
    result = subprocess.run(
        [
            "/bin/bash",
            str(prompt_invoke),
            "--prompt-name",
            "powerpoint",
            "--",
            "/bin/sh",
            "-c",
            "exit 0",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
        env=env,
    )

    assert result.returncode == 0


def test_post_message_hook_handles_empty_optional_args(tmp_path: Path) -> None:
    """TODO: add docstring for test_post_message_hook_handles_empty_optional_args."""
    repo_dir = tmp_path / "repo"
    github_hooks = repo_dir / ".github" / "hooks"
    github_scripts = (
        repo_dir / ".github" / "skills" / "shared/task-orchestration" / "scripts"
    )
    repo_dir.mkdir(parents=True)
    github_hooks.mkdir(parents=True)
    github_scripts.mkdir(parents=True)

    (repo_dir / ".github" / "hooks" / "post-message.sh").write_text(
        (LAYER_ROOT / "hooks" / "post-message.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (github_scripts / "task-audit-log.sh").write_text(
        AUDIT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "/bin/bash",
            str(repo_dir / ".github" / "hooks" / "post-message.sh"),
            "--message-id",
            "msg-1",
            "--status",
            "ok",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 0, result.stderr
    generated = list(
        (repo_dir / ".digital-artifacts" / "70-audits").glob("**/*.audit.md")
    )
    assert generated


def test_prompt_invoke_groups_pre_post_into_single_audit_file(tmp_path: Path) -> None:
    """Test that prompt wrapper writes one audit file per message and includes trace details."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    github_hooks = repo_dir / ".github" / "hooks"
    github_hooks.mkdir(parents=True)
    github_scripts = (
        repo_dir / ".github" / "skills" / "shared/task-orchestration" / "scripts"
    )
    github_scripts.mkdir(parents=True)
    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)

    (github_hooks / "pre-message.sh").write_text(
        (LAYER_ROOT / "hooks" / "pre-message.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (github_hooks / "post-message.sh").write_text(
        (LAYER_ROOT / "hooks" / "post-message.sh").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (github_scripts / "task-audit-log.sh").write_text(
        AUDIT.read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    (digital_team_lib / "governance.sh").write_text(
        GOVERNANCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        COMMON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    result = subprocess.run(
        [
            "/bin/bash",
            str(PROMPT_INVOKE),
            "--prompt-name",
            "quality",
            "--message-id",
            "msg-grouped-1",
            "--summary",
            "/quality -> quality-expert-orchestrator",
            "--",
            "/bin/sh",
            "-c",
            "exit 0",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 0
    audit_files = sorted(
        (repo_dir / ".digital-artifacts" / "70-audits").glob("**/*.audit.md")
    )
    assert len(audit_files) == 1
    content = audit_files[0].read_text(encoding="utf-8")
    assert "## Session Result" in content
    assert "request_received (pre-message)" not in content
    assert "response_completed (post-message)" not in content
    assert "### Summary" in content
    assert "- Runtime:" in content
    assert "<summary>Technical details (for maintainers)</summary>" in content
    assert "#### Execution Stack" in content
    assert "```text" in content
    assert "-> wrapper=prompt-invoke" in content
    assert "#### Resolution Trace" in content
    assert "### Handoff Status" in content
    assert "- expectation: yes" in content
    assert "- required: yes" in content
    assert "Handoff check: A handoff was expected" in content
    assert "### Communication Flow" not in content

    flow_svgs = sorted(
        (repo_dir / ".digital-artifacts" / "70-audits").glob("**/*-flow.svg")
    )
    assert len(flow_svgs) == 1
    flow_svg_content = flow_svgs[0].read_text(encoding="utf-8")
    assert "Sequence Diagram" in flow_svg_content
    assert "copilot" in flow_svg_content
    assert "-&amp;gt;" not in flow_svg_content


def test_prompt_invoke_emits_mcp_and_nested_expert_trace(tmp_path: Path) -> None:
    """Prompt invoke should pass MCP endpoint trace and nested expert flow to post hook."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    github_hooks = repo_dir / ".github" / "hooks"
    github_hooks.mkdir(parents=True)
    prompt_dir = repo_dir / ".github" / "prompts"
    prompt_dir.mkdir(parents=True)
    prompt_skill_dir = repo_dir / ".github" / "skills" / "prompt-quality"
    prompt_skill_dir.mkdir(parents=True)
    agent_dir = repo_dir / ".github" / "agents"
    agent_dir.mkdir(parents=True)
    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)

    (github_hooks / "pre-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" > pre.log\n",
        encoding="utf-8",
    )
    (github_hooks / "post-message.sh").write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf '%s\\n' \"$*\" > post.log\n",
        encoding="utf-8",
    )
    (digital_team_lib / "governance.sh").write_text(
        GOVERNANCE.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        COMMON.read_text(encoding="utf-8"), encoding="utf-8"
    )

    (prompt_dir / "quality.prompt.md").write_text(
        "# Prompt\nUse quality-expert and security-expert for review.\n",
        encoding="utf-8",
    )
    (prompt_skill_dir / "SKILL.md").write_text(
        "## Dependencies\n- quality-expert\n- mcp\n",
        encoding="utf-8",
    )
    (agent_dir / "quality-expert.agent.md").write_text(
        "---\nname: quality-expert\n---\n",
        encoding="utf-8",
    )
    (agent_dir / "security-expert.agent.md").write_text(
        "---\nname: security-expert\n---\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [
            "/bin/bash",
            str(PROMPT_INVOKE),
            "--prompt-name",
            "quality",
            "--message-id",
            "msg-nested-1",
            "--summary",
            "quality with nested experts",
            "--",
            "/bin/echo",
            "--server-id",
            "azure-quantum",
            "--tool",
            "jobs.list",
            "https://mcp.example/api",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
    )

    assert result.returncode == 0
    post_log = (repo_dir / "post.log").read_text(encoding="utf-8")
    assert "--mcp-endpoints-trace" in post_log
    assert "server:azure-quantum" in post_log
    assert "tool:jobs.list" in post_log
    assert "https://mcp.example/api" in post_log
    assert "quality-expert -> security-expert: expert_request_v1" in post_log
    assert "security-expert --> quality-expert: expert_response_v1" in post_log


def test_task_audit_log_amend_appends_handoff_block(tmp_path: Path) -> None:
    """Test that --mode amend appends a Handoff Update block to an existing audit entry."""
    audits_root = tmp_path / "audits"
    # Step 1: create initial full audit
    _run(
        AUDIT,
        "--mode",
        "full",
        "--task-id",
        "TASK-600",
        "--role",
        "copilot",
        "--action",
        "post-message",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-04-02",
        "--message-id",
        "amend-test",
        "--handoff-expected",
        "yes",
    )
    initial_file = audits_root / "2026-04-02" / "00000.audit.md"
    assert initial_file.exists()

    # Step 2: write a handoff YAML somewhere
    handoff_dir = tmp_path / "handoffs"
    handoff_dir.mkdir()
    handoff_yaml = handoff_dir / "amend-test-handoff.yaml"
    handoff_yaml.write_text(
        "kind: work_handoff_v1\nfrom: quality-expert\nto: copilot\nsummary: done\n",
        encoding="utf-8",
    )

    # Step 3: amend with handoff details and updated communication flow
    result = _run(
        AUDIT,
        "--mode",
        "amend",
        "--message-id",
        "amend-test",
        "--audits-root",
        str(audits_root),
        "--date",
        "2026-04-02",
        "--handoff-file",
        str(handoff_yaml),
        "--communication-flow",
        "user -> copilot: /quality; copilot -> quality-expert: invoke; quality-expert --> copilot: work_handoff_v1; copilot -> audit-log: amend",
    )
    assert result.returncode == 0, result.stderr
    assert 'mode: "amend"' in result.stdout

    content = initial_file.read_text(encoding="utf-8")
    assert "## Handoff Update" in content
    assert "- protocol: work_handoff_v1" in content
    assert "- evidence: handoff_file" in content
    assert ".digital-runtime/handoffs/audit/2026-04-02/00000/amend-test-handoff.yaml" in content

    runtime_handoff = (
        audits_root.parent
        / ".digital-runtime"
        / "handoffs"
        / "audit"
        / "2026-04-02"
        / "00000"
        / "amend-test-handoff.yaml"
    )
    assert runtime_handoff.exists()

    legacy_handoff_dir = audits_root / "2026-04-02" / "00000" / "handoffs"
    assert not legacy_handoff_dir.exists()

    flow_svg = audits_root / "2026-04-02" / "00000" / "sequence-flow.svg"
    assert flow_svg.exists()
    svg_content = flow_svg.read_text(encoding="utf-8")
    assert "Sequence Diagram" in svg_content
    assert "quality-expert" in svg_content
    assert "work_handoff_v1" in svg_content


def test_task_audit_log_basename_adds_numeric_prefix(tmp_path: Path) -> None:
    """Basename-based audits should stay unique via numeric prefix."""
    audits_root = tmp_path / "audits"
    env = os.environ.copy()
    env.setdefault("DIGITAL_AUDIT_ENABLED", "1")
    env["DIGITAL_AUDIT_BASENAME"] = "project"

    first = subprocess.run(
        [
            "/bin/bash",
            str(AUDIT),
            "--mode",
            "full",
            "--task-id",
            "TASK-700",
            "--role",
            "copilot",
            "--action",
            "post-message",
            "--audits-root",
            str(audits_root),
            "--date",
            "2026-04-13",
            "--message-id",
            "project-msg-1",
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    second = subprocess.run(
        [
            "/bin/bash",
            str(AUDIT),
            "--mode",
            "full",
            "--task-id",
            "TASK-701",
            "--role",
            "copilot",
            "--action",
            "post-message",
            "--audits-root",
            str(audits_root),
            "--date",
            "2026-04-13",
            "--message-id",
            "project-msg-2",
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    first_file = audits_root / "2026-04-13" / "00000-project.audit.md"
    second_file = audits_root / "2026-04-13" / "00001-project.audit.md"
    assert first_file.exists()
    assert second_file.exists()


def test_task_audit_log_reuses_latest_basename_when_enabled(tmp_path: Path) -> None:
    """Basename reuse flag should append reruns into the latest matching audit file."""
    audits_root = tmp_path / "audits"
    env = os.environ.copy()
    env.setdefault("DIGITAL_AUDIT_ENABLED", "1")
    env["DIGITAL_AUDIT_BASENAME"] = "project"
    env["DIGITAL_AUDIT_REUSE_LATEST_FOR_BASENAME"] = "1"

    first = subprocess.run(
        [
            "/bin/bash",
            str(AUDIT),
            "--mode",
            "full",
            "--task-id",
            "TASK-710",
            "--role",
            "copilot",
            "--action",
            "post-message",
            "--audits-root",
            str(audits_root),
            "--date",
            "2026-04-13",
            "--message-id",
            "project-msg-1",
            "--notes",
            "summary=/project",
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )
    second = subprocess.run(
        [
            "/bin/bash",
            str(AUDIT),
            "--mode",
            "short",
            "--task-id",
            "TASK-711",
            "--role",
            "copilot",
            "--action",
            "pre-message",
            "--audits-root",
            str(audits_root),
            "--date",
            "2026-04-13",
            "--message-id",
            "project-msg-2",
            "--notes",
            "summary=/project rerun",
        ],
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr

    files = sorted((audits_root / "2026-04-13").glob("*.audit.md"))
    assert len(files) == 1
    assert files[0].name == "00000-project.audit.md"

    content = files[0].read_text(encoding="utf-8")
    assert "## Rerun Start" in content
    assert "- message_id: project-msg-2" in content
    assert "- summary: /project rerun" in content


def test_prompt_invoke_project_exports_master_audit_context(tmp_path: Path) -> None:
    """/project prompt should export master audit context for nested prompt wrappers."""
    repo_dir = tmp_path / "repo"
    subprocess.run(
        ["git", "init", str(repo_dir)], check=True, capture_output=True, text=True
    )

    digital_team_lib = (
        repo_dir / ".github" / "skills" / "shared/shell" / "scripts" / "lib"
    )
    digital_team_lib.mkdir(parents=True)
    governance_src = LAYER_ROOT / "shared" / "shell" / "scripts" / "lib" / "governance.sh"
    common_src = LAYER_ROOT / "shared" / "shell" / "scripts" / "lib" / "common.sh"
    (digital_team_lib / "governance.sh").write_text(
        governance_src.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (digital_team_lib / "common.sh").write_text(
        common_src.read_text(encoding="utf-8"), encoding="utf-8"
    )

    env = os.environ.copy()
    env["DIGITAL_AUDIT_ENABLED"] = "0"
    prompt_invoke_src = Path(__file__).resolve().parents[5] / "hooks" / "prompt-invoke.sh"
    result = subprocess.run(
        [
            "/bin/bash",
            str(prompt_invoke_src),
            "--prompt-name",
            "project",
            "--message-id",
            "project-msg-ctx",
            "--",
            "/bin/sh",
            "-c",
            "printf '%s|%s|%s' \"${DIGITAL_AUDIT_MASTER_MESSAGE_ID:-}\" \"${DIGITAL_AUDIT_MASTER_BASENAME:-}\" \"${DIGITAL_AUDIT_REUSE_LATEST_FOR_BASENAME:-}\"",
        ],
        check=False,
        text=True,
        capture_output=True,
        cwd=repo_dir,
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert result.stdout == "project-msg-ctx|project|1"
