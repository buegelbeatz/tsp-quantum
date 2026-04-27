"""Permission and behavior checks for git skill shell wrappers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPTS_DIR = ROOT / ".github" / "skills" / "git" / "scripts"


def _init_git_repo(path: Path) -> None:
    """Initialize a temporary git repository with one baseline commit."""
    subprocess.run(
        ["git", "init"], cwd=path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.org"], cwd=path, check=True
    )
    subprocess.run(["git", "config", "user.name", "Test User"], cwd=path, check=True)
    (path / "README.md").write_text("hello\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path,
        check=True,
        capture_output=True,
        text=True,
    )


def test_git_status_denies_unauthorized_role(tmp_path: Path) -> None:
    """Test that git-status.sh denies access for unauthorized roles."""
    _init_git_repo(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPTS_DIR / "git-status.sh"), "--role", "unknown-role"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 3
    assert 'status: "error"' in result.stdout
    assert "not permitted" in result.stdout


def test_git_status_allows_generic_delivery(tmp_path: Path) -> None:
    """Test that git-status.sh permits generic-deliver role with proper output format."""
    _init_git_repo(tmp_path)
    result = subprocess.run(
        ["bash", str(SCRIPTS_DIR / "git-status.sh"), "--role", "generic-deliver"],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'status: "ok"' in result.stdout
    assert 'operation: "read-status"' in result.stdout


def test_git_branch_create_requires_delivery_permissions(tmp_path: Path) -> None:
    """Test that git-branch-create.sh enforces delivery role permissions."""
    _init_git_repo(tmp_path)
    denied = subprocess.run(
        [
            "bash",
            str(SCRIPTS_DIR / "git-branch-create.sh"),
            "--role",
            "agile-coach",
            "--branch-name",
            "feature/test",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert denied.returncode == 3

    allowed = subprocess.run(
        [
            "bash",
            str(SCRIPTS_DIR / "git-branch-create.sh"),
            "--role",
            "fullstack-engineer",
            "--branch-name",
            "feature/test",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert allowed.returncode == 0, allowed.stderr
    assert 'status: "ok"' in allowed.stdout


def test_git_stage_add_and_commit_create(tmp_path: Path) -> None:
    """Test stage-add + commit-create wrappers succeed for delivery roles."""
    _init_git_repo(tmp_path)
    (tmp_path / "module.py").write_text("print('x')\n", encoding="utf-8")
    paths_file = tmp_path / "paths.txt"
    paths_file.write_text("module.py\n", encoding="utf-8")

    stage = subprocess.run(
        [
            "bash",
            str(SCRIPTS_DIR / "git-stage-add.sh"),
            "--role",
            "fullstack-engineer",
            "--paths-file",
            str(paths_file),
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert stage.returncode == 0, stage.stderr
    assert 'operation: "stage-add"' in stage.stdout

    commit = subprocess.run(
        [
            "bash",
            str(SCRIPTS_DIR / "git-commit-create.sh"),
            "--role",
            "fullstack-engineer",
            "--message",
            "feat(test): add module",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert commit.returncode == 0, commit.stderr
    assert 'operation: "commit-create"' in commit.stdout


def test_git_push_branch_denies_unauthorized_role(tmp_path: Path) -> None:
    """Test push wrapper denies roles without push permission."""
    _init_git_repo(tmp_path)
    denied = subprocess.run(
        [
            "bash",
            str(SCRIPTS_DIR / "git-push-branch.sh"),
            "--role",
            "agile-coach",
            "--remote",
            "origin",
            "--branch",
            "main",
            "--set-upstream",
            "0",
        ],
        cwd=tmp_path,
        text=True,
        capture_output=True,
        check=False,
    )
    assert denied.returncode == 3
    assert 'status: "error"' in denied.stdout
