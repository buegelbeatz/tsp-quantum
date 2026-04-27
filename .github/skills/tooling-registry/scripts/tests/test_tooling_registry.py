from __future__ import annotations

import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "scripts" / "artifact-register.sh"
VERIFY = ROOT / "scripts" / "artifact-verify.sh"


def _run(script: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [str(script), *args],
        check=False,
        text=True,
        capture_output=True,
    )


def test_artifact_register_success() -> None:
    """TODO: add docstring for test_artifact_register_success."""
    result = _run(
        REGISTER,
        "--name",
        "skill-generic-deliver",
        "--type",
        "shell",
        "--version",
        "1.0.0",
        "--location",
        ".../generic-deliver/scripts",
        "--format",
        "sh",
    )
    assert result.returncode == 0
    assert 'stage: "registered"' in result.stdout
    assert 'status: "ok"' in result.stdout


def test_artifact_register_missing_args() -> None:
    """TODO: add docstring for test_artifact_register_missing_args."""
    result = _run(
        REGISTER,
        "--name",
        "skill-test",
        "--type",
        "shell",
    )
    assert result.returncode != 0
    assert "--version is required" in result.stderr


def test_artifact_verify_success(tmp_path: Path) -> None:
    """TODO: add docstring for test_artifact_verify_success."""
    artifact = tmp_path / "test-artifact.sh"
    artifact.write_text("#!/bin/bash\necho hello\n", encoding="utf-8")
    registry = tmp_path / "registry.csv"
    registry.write_text("artifact_name,version\ntest,1.0.0\n", encoding="utf-8")

    result = _run(
        VERIFY,
        "--artifact",
        str(artifact),
        "--registry",
        str(registry),
    )
    assert result.returncode == 0
    assert 'stage: "verified"' in result.stdout


def test_artifact_verify_missing_artifact(tmp_path: Path) -> None:
    """TODO: add docstring for test_artifact_verify_missing_artifact."""
    missing = tmp_path / "missing.sh"
    registry = tmp_path / "registry.csv"
    registry.write_text("artifact_name,version\n", encoding="utf-8")

    result = _run(
        VERIFY,
        "--artifact",
        str(missing),
        "--registry",
        str(registry),
    )
    assert result.returncode != 0
    assert "Artifact path does not exist" in result.stderr
