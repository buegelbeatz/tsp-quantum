"""Tests for runtime layer virtualenv synchronization script behavior."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "runtime"
    / "layer-venv-sync.sh"
)


def _runtime_env(
    runtime_root: Path, *, repo_root: Path | None = None
) -> dict[str, str]:
    env = os.environ.copy()
    env["DIGITAL_TEAM_RUNTIME_ROOT"] = str(runtime_root)
    env["DIGITAL_TEAM_SKIP_PIP_INSTALL"] = "1"
    env["DIGITAL_TEAM_ALLOW_VENV_CREATE"] = "1"
    if repo_root is not None:
        env["DIGITAL_TEAM_REPO_ROOT"] = str(repo_root)
    return env


def _run_sync(
    layer_dir: Path, *, cwd: Path, env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["bash", str(SCRIPT), str(layer_dir)],
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_layer_venv_sync_merges_unique_sorted_requirements(tmp_path: Path) -> None:
    """TODO: add docstring for test_layer_venv_sync_merges_unique_sorted_requirements."""
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text(
        "PyYAML==6.0.2\nopenpyxl==3.1.5\n", encoding="utf-8"
    )
    nested = layer_dir / "nested"
    nested.mkdir()
    (nested / "requirements-extra.txt").write_text(
        "openpyxl==3.1.5\nlangdetect==1.0.9\n", encoding="utf-8"
    )

    runtime_root = tmp_path / "runtime"

    result = _run_sync(layer_dir, cwd=ROOT, env=_runtime_env(runtime_root))

    assert result.returncode == 0, result.stderr
    merged = runtime_root / "layers" / "layer" / "requirements.merged.txt"
    assert merged.exists()
    assert merged.read_text(encoding="utf-8").splitlines() == [
        "langdetect==1.0.9",
        "openpyxl==3.1.5",
        "PyYAML==6.0.2",
    ]


def test_layer_venv_sync_reports_unchanged_hash_on_second_run(tmp_path: Path) -> None:
    """TODO: add docstring for test_layer_venv_sync_reports_unchanged_hash_on_second_run."""
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    env = _runtime_env(runtime_root)
    first = _run_sync(layer_dir, cwd=ROOT, env=env)
    second = _run_sync(layer_dir, cwd=ROOT, env=env)

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert "requirements_changed: false" in second.stdout


def test_layer_venv_sync_uses_shared_python_runtime_venv_by_default(
    tmp_path: Path,
) -> None:
    """The default sync target should be the shared python-runtime venv."""
    layer_dir = tmp_path / "artifacts"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"

    result = _run_sync(layer_dir, cwd=ROOT, env=_runtime_env(runtime_root))

    assert result.returncode == 0, result.stderr
    assert (runtime_root / "layers" / "python-runtime" / "venv").exists()
    assert not (runtime_root / "layers" / "artifacts" / "venv").exists()


def test_layer_venv_sync_removes_stray_layer_venvs(tmp_path: Path) -> None:
    """Unexpected layer-local venvs should be removed in favor of python-runtime."""
    layer_dir = tmp_path / "artifacts"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    stray_python = runtime_root / "layers" / "artifacts" / "venv" / "bin" / "python"
    stray_python.parent.mkdir(parents=True, exist_ok=True)
    stray_python.write_text("#!/bin/false\n", encoding="utf-8")

    result = _run_sync(layer_dir, cwd=ROOT, env=_runtime_env(runtime_root))

    assert result.returncode == 0, result.stderr
    assert not (runtime_root / "layers" / "artifacts" / "venv").exists()
    assert (runtime_root / "layers" / "python-runtime" / "venv").exists()


def test_layer_venv_sync_fails_when_root_venv_exists_in_layer_repo(
    tmp_path: Path,
) -> None:
    """Layer repos must fail when a forbidden root-level .venv exists."""
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()
    unexpected_root_venv = fake_repo_root / ".venv"
    (unexpected_root_venv / "bin").mkdir(parents=True, exist_ok=True)
    (unexpected_root_venv / "bin" / "python").write_text(
        "#!/bin/false\n", encoding="utf-8"
    )

    env = _runtime_env(runtime_root, repo_root=fake_repo_root)
    result = _run_sync(layer_dir, cwd=fake_repo_root, env=env)

    assert result.returncode != 0
    assert "Forbidden root virtual environment detected" in result.stderr
    assert unexpected_root_venv.exists()


def test_layer_venv_sync_keeps_root_venv_for_app_repo(tmp_path: Path) -> None:
    """App repositories may keep their root .venv."""
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    fake_repo_root = tmp_path / "app-repo"
    (fake_repo_root / ".github").mkdir(parents=True)
    (fake_repo_root / "src").mkdir(parents=True)
    (fake_repo_root / "src" / "main.py").write_text("print('ok')\n", encoding="utf-8")
    root_python = fake_repo_root / ".venv" / "bin" / "python"
    root_python.parent.mkdir(parents=True, exist_ok=True)
    root_python.write_text("#!/bin/false\n", encoding="utf-8")

    env = _runtime_env(runtime_root, repo_root=fake_repo_root)
    result = _run_sync(layer_dir, cwd=fake_repo_root, env=env)

    assert result.returncode == 0, result.stderr
    assert root_python.exists()
    assert (runtime_root / "layers" / "python-runtime" / "venv").exists()


def test_layer_venv_sync_rejects_root_shared_venv_override_in_layer_repo(
    tmp_path: Path,
) -> None:
    """Layer repos must reject DIGITAL_TEAM_SHARED_VENV_PATH pointing to root .venv."""
    layer_dir = tmp_path / "layer"
    layer_dir.mkdir()
    (layer_dir / "requirements.txt").write_text("PyYAML==6.0.2\n", encoding="utf-8")

    runtime_root = tmp_path / "runtime"
    fake_repo_root = tmp_path / "repo"
    fake_repo_root.mkdir()

    env = _runtime_env(runtime_root, repo_root=fake_repo_root)
    env["DIGITAL_TEAM_SHARED_VENV_PATH"] = str(fake_repo_root / ".venv")

    result = _run_sync(layer_dir, cwd=fake_repo_root, env=env)

    assert result.returncode != 0
    assert "Invalid DIGITAL_TEAM_SHARED_VENV_PATH for layer repo" in result.stderr
