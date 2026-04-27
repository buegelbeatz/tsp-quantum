from __future__ import annotations

import subprocess
from pathlib import Path

from github_test_support import ROOT, build_env, write_executable


SOURCE_SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "github"
    / "gh-wiki-create.sh"
)


def _prepare_wiki_create_fixture(tmp_path: Path) -> Path:
    """Prepare local script/lib fixture for wiki create idempotency test."""
    script_dir = tmp_path / "github"
    lib_dir = tmp_path / "lib"
    script_dir.mkdir()
    lib_dir.mkdir()

    script_copy = script_dir / "gh-wiki-create.sh"
    write_executable(script_copy, SOURCE_SCRIPT.read_text(encoding="utf-8"))

    common_sh = lib_dir / "common.sh"
    write_executable(
        common_sh,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'die() { echo "[ERROR] $*" >&2; exit 1; }\n',
    )

    github_sh = lib_dir / "github.sh"
    write_executable(
        github_sh,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "github_require_token() { return 0; }\n"
        "github_run_gh() { return 0; }\n",
    )

    page_add = script_dir / "gh-wiki-page-add.sh"
    write_executable(
        page_add,
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "echo '[ERROR] Wiki page already exists: Home.md' >&2\n"
        "exit 1\n",
    )
    return script_copy


def test_wiki_create_succeeds_when_home_page_already_exists(tmp_path: Path) -> None:
    """TODO: add docstring for test_wiki_create_succeeds_when_home_page_already_exists."""
    script_copy = _prepare_wiki_create_fixture(tmp_path)
    env = build_env(gh_token="dummy-token")

    result = subprocess.run(
        ["bash", str(script_copy), "demo-owner", "demo-repo"],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert 'kind: "github_wiki_create_result"' in result.stdout
    assert "home_initialized: true" in result.stdout
    assert "home_created: false" in result.stdout
    assert "home_already_present: true" in result.stdout
