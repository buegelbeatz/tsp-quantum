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
    / "gh-board-create.sh"
)


def _write_fake_gh(fake_bin: Path, log_file: Path) -> None:
    """Create fake gh executable that simulates project create/list/link calls."""
    write_executable(
        fake_bin / "gh",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        f"log_file='{log_file}'\n"
        'printf \'%s\n\' "$*" >> "$log_file"\n'
        'if [[ "${1:-}" == "project" && "${2:-}" == "create" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "project" && "${2:-}" == "list" ]]; then\n'
        '  printf \'{"projects":[{"number":7,"title":"demo","owner":{"login":"demo-user","type":"User"},"closed":false,"fields":{"totalCount":0},"items":{"totalCount":0},"public":false,"readme":"","shortDescription":"","url":"https://example.test/project/7","id":"PVT_demo"}]}\'\n'
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "api" && "${2:-}" == "/user" ]]; then\n'
        "  printf 'demo-user\n'\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${1:-}" == "project" && "${2:-}" == "link" ]]; then\n'
        "  exit 0\n"
        "fi\n"
        "echo 'unexpected gh call' >&2\n"
        "exit 2\n",
    )


def test_board_create_links_repository_when_requested(tmp_path: Path) -> None:
    """TODO: add docstring for test_board_create_links_repository_when_requested."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    log_file = tmp_path / "gh.log"
    _write_fake_gh(fake_bin, log_file)
    env = build_env(path_prefix=fake_bin, gh_token="dummy-token")

    result = subprocess.run(
        ["bash", str(SCRIPT), "@me", "demo", "demo-user/demo-repo"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'linked_repository: "demo-user/demo-repo"' in result.stdout
    log_content = log_file.read_text(encoding="utf-8")
    assert "project link 7 --owner demo-user --repo demo-user/demo-repo" in log_content
