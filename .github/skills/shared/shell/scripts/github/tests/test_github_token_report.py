"""Unit tests for gh-token-report.sh GitHub token and account validation."""

from __future__ import annotations

import subprocess
from pathlib import Path

from github_test_support import ROOT, build_env, write_executable


SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "github"
    / "gh-token-report.sh"
)


def test_token_report_fails_without_token() -> None:
    """Test that gh-token-report.sh fails when GH_TOKEN environment variable is not set."""
    env = build_env()
    env.pop("GITHUB_OWNER", None)

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 1
    assert 'kind: "gh_token_report"' in result.stdout
    assert 'status: "error"' in result.stdout
    assert 'message: "GH_TOKEN is not set"' in result.stdout
    assert '  - "repo"' in result.stdout
    assert '  - "project"' in result.stdout
    assert '  - "read:org"' in result.stdout
    assert '  - "read:discussion"' in result.stdout


def test_token_report_handles_missing_scope_header(tmp_path: Path) -> None:
    """TODO: add docstring for test_token_report_handles_missing_scope_header."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    write_executable(
        fake_bin / "gh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${1:-}" == "api" && "${2:-}" == "-i" && "${3:-}" == "/user" ]]; then\n'
        "  printf 'HTTP/1.1 200 OK\\r\\n'\n"
        "  printf 'content-type: application/json\\r\\n'\n"
        "  printf '\\r\\n'\n"
        '  printf \'{"login":"test-user"}\\n\'\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "api" && "${2:-}" == "/user" ]]; then\n'
        "  printf 'test-user\\n'\n"
        "  exit 0\n"
        "fi\n"
        "echo 'unexpected gh call' >&2\n"
        "exit 2\n",
    )
    env = build_env(path_prefix=fake_bin, gh_token="dummy")

    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode in (0, 2)
    assert 'kind: "gh_token_report"' in result.stdout
    assert 'login: "test-user"' in result.stdout
    assert "granted_scopes:" in result.stdout
