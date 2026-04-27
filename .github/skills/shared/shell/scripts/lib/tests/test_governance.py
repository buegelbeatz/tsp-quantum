from __future__ import annotations

import subprocess
from pathlib import Path


LIB_DIR = Path(__file__).resolve().parents[1]
GOVERNANCE = LIB_DIR / "governance.sh"


def _run_bash(script: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", "-lc", script],
        check=False,
        text=True,
        capture_output=True,
    )


def test_check_permission_allows(tmp_path: Path) -> None:
    """TODO: add docstring for test_check_permission_allows."""
    permissions = tmp_path / "PERMISSIONS.csv"
    permissions.write_text(
        "operation;developer;reviewer\nread;1;1\nwrite;1;0\n",
        encoding="utf-8",
    )

    result = _run_bash(
        f'source "{GOVERNANCE}" && check_permission "{permissions}" developer write'
    )
    assert result.returncode == 0


def test_check_permission_denies(tmp_path: Path) -> None:
    """TODO: add docstring for test_check_permission_denies."""
    permissions = tmp_path / "PERMISSIONS.csv"
    permissions.write_text(
        "operation;developer;reviewer\nread;1;1\nwrite;1;0\n",
        encoding="utf-8",
    )

    result = _run_bash(
        f'source "{GOVERNANCE}" && check_permission "{permissions}" reviewer write'
    )
    assert result.returncode != 0
    assert "Permission denied" in result.stderr


def test_validate_handoff_success(tmp_path: Path) -> None:
    """TODO: add docstring for test_validate_handoff_success."""
    schema = tmp_path / "schema.yaml"
    payload = tmp_path / "payload.yaml"

    schema.write_text(
        "required:\n  - ticket_id\n  - summary\n",
        encoding="utf-8",
    )
    payload.write_text(
        "ticket_id: DT-99\nsummary: done\n",
        encoding="utf-8",
    )

    result = _run_bash(
        f'source "{GOVERNANCE}" && validate_handoff "{payload}" "{schema}"'
    )
    assert result.returncode == 0


def test_validate_handoff_missing_field(tmp_path: Path) -> None:
    """TODO: add docstring for test_validate_handoff_missing_field."""
    schema = tmp_path / "schema.yaml"
    payload = tmp_path / "payload.yaml"

    schema.write_text(
        "required:\n  - ticket_id\n  - summary\n",
        encoding="utf-8",
    )
    payload.write_text("ticket_id: DT-99\n", encoding="utf-8")

    result = _run_bash(
        f'source "{GOVERNANCE}" && validate_handoff "{payload}" "{schema}"'
    )
    assert result.returncode != 0
    assert "Missing required handoff" in result.stderr


def test_resolve_script_path_primary_github(tmp_path: Path) -> None:
    """TODO: add docstring for test_resolve_script_path_primary_github."""
    github_dir = tmp_path / ".github" / "hooks"
    github_dir.mkdir(parents=True)
    script = github_dir / "test-hook.sh"
    script.write_text("#!/bin/bash\necho 'primary'\n", encoding="utf-8")

    digital_team_dir = tmp_path / ".digital-team" / "00-test" / "hooks"
    digital_team_dir.mkdir(parents=True)
    fallback_script = digital_team_dir / "test-hook.sh"
    fallback_script.write_text("#!/bin/bash\necho 'fallback'\n", encoding="utf-8")

    result = _run_bash(
        f'source "{GOVERNANCE}" && resolve_script_path "test-hook.sh" "{tmp_path}"'
    )
    assert result.returncode == 0
    assert str(script) in result.stdout


def test_resolve_script_path_fallback_digital_team(tmp_path: Path) -> None:
    """TODO: add docstring for test_resolve_script_path_fallback_digital_team."""
    digital_team_dir = tmp_path / ".digital-team" / "00-test" / "hooks"
    digital_team_dir.mkdir(parents=True)
    script = digital_team_dir / "fallback-hook.sh"
    script.write_text("#!/bin/bash\necho 'fallback'\n", encoding="utf-8")

    result = _run_bash(
        f'source "{GOVERNANCE}" && resolve_script_path "fallback-hook.sh" "{tmp_path}"'
    )
    assert result.returncode == 0
    assert str(script) in result.stdout


def test_resolve_script_path_not_found(tmp_path: Path) -> None:
    """TODO: add docstring for test_resolve_script_path_not_found."""
    result = _run_bash(
        f'source "{GOVERNANCE}" && resolve_script_path "nonexistent.sh" "{tmp_path}"'
    )
    assert result.returncode != 0
    assert "Script not found" in result.stderr
