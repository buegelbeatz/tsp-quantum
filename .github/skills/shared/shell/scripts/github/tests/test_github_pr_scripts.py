"""Tests for GitHub PR create/comment wrappers with fake gh executable."""

from __future__ import annotations

import subprocess
from pathlib import Path

from github_test_support import ROOT, build_env, write_executable


CREATE_SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "github"
    / "gh-pr-create.sh"
)
COMMENT_SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "github"
    / "gh-pr-comment.sh"
)


def _create_fake_gh(tmp_path: Path) -> Path:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "gh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${1:-}" == "pr" && "${2:-}" == "create" ]]; then\n'
        "  printf 'https://github.com/org/repo/pull/42\\n'\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "pr" && "${2:-}" == "comment" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        "echo 'unexpected gh call' >&2\n"
        "exit 2\n",
    )
    return fake_bin


def test_gh_pr_create_outputs_yaml(tmp_path: Path) -> None:
    """TODO: add docstring for test_gh_pr_create_outputs_yaml."""
    fake_bin = _create_fake_gh(tmp_path)
    env = build_env(path_prefix=fake_bin, gh_token="dummy")

    result = subprocess.run(
        [
            "bash",
            str(CREATE_SCRIPT),
            "org/repo",
            "main",
            "feature/test",
            "My PR",
            "Body",
        ],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'kind: "github_pr_create"' in result.stdout
    assert 'status: "ok"' in result.stdout
    assert 'pr_url: "https://github.com/org/repo/pull/42"' in result.stdout


def test_gh_pr_comment_outputs_yaml(tmp_path: Path) -> None:
    """TODO: add docstring for test_gh_pr_comment_outputs_yaml."""
    fake_bin = _create_fake_gh(tmp_path)
    env = build_env(path_prefix=fake_bin, gh_token="dummy")

    result = subprocess.run(
        ["bash", str(COMMENT_SCRIPT), "org/repo", "42", "Looks good"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert 'kind: "github_pr_comment"' in result.stdout
    assert 'status: "ok"' in result.stdout
