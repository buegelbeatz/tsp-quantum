from __future__ import annotations

import shutil
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
    / "gh-wiki-list-pages.sh"
)


def _write_fake_git(fake_bin: Path) -> None:
    """Create fake git executable with deterministic sync failure."""
    write_executable(
        fake_bin / "git",
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        'if [[ "${*}" == *"rev-parse --show-toplevel"* ]]; then\n'
        f"  echo '{ROOT}'\n"
        "  exit 0\n"
        "fi\n"
        'if [[ "${*}" == *" pull --rebase"* ]]; then\n'
        "  echo 'simulated pull failure' >&2\n"
        "  exit 1\n"
        "fi\n"
        "exit 0\n",
    )


def _prepare_cached_wiki_repo(repo_slug: str) -> Path:
    """Create cached wiki directory with stale content for sync failure path."""
    owner_repo = repo_slug.replace("/", "__")
    wiki_dir = (
        ROOT / ".digital-runtime" / "github" / "wiki-cache" / f"{owner_repo}.wiki"
    )
    wiki_git_dir = wiki_dir / ".git"
    wiki_dir.mkdir(parents=True, exist_ok=True)
    wiki_git_dir.mkdir(exist_ok=True)
    (wiki_dir / "Home.md").write_text("# stale cache\n", encoding="utf-8")
    return wiki_dir


def test_wiki_list_fails_when_cached_repo_cannot_sync(tmp_path: Path) -> None:
    """TODO: add docstring for test_wiki_list_fails_when_cached_repo_cannot_sync."""
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    _write_fake_git(fake_bin)

    repo_slug = "sync-test-owner/sync-test-repo"
    wiki_dir = _prepare_cached_wiki_repo(repo_slug)

    env = build_env(path_prefix=fake_bin, gh_token="dummy-token")

    result = subprocess.run(
        ["bash", str(SCRIPT), repo_slug],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert "Wiki sync failed from remote" in result.stderr

    shutil.rmtree(wiki_dir, ignore_errors=True)
