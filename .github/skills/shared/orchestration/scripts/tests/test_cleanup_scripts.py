from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
MAKEFILE_PATH = ROOT / ".github" / "make" / "commands.mk"
CLEANUP_SCRIPT_PATH = (
    ROOT / ".github" / "skills" / "shared" / "orchestration" / "scripts" / "cleanup.sh"
)
CLEANUP_E2E_SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared"
    / "orchestration"
    / "scripts"
    / "cleanup-e2e.sh"
)


def test_makefile_cleanup_defaults_are_destructive() -> None:
    content = MAKEFILE_PATH.read_text(encoding="utf-8")

    assert "cleanup: preflight" in content
    assert '--dry-run "$${DRY_RUN:-0}"' in content
    assert '--confirm "$${CONFIRM:-1}"' in content
    assert "test: preflight layer-venv-sync" in content
    assert "@bash $(_CLEANUP_E2E_SCRIPT)" in content
    assert '--github-test "$${GITHUB_TEST:-0}"' in content
    assert "cleanup-e2e: preflight" not in content
    assert "cleanup                        Cleanup board/sprints/issues/wiki (runs destructive by default)" in content


def test_cleanup_script_supports_non_interactive_confirmation() -> None:
    content = CLEANUP_SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'if [[ "$DRY_RUN" == "0" && "$CONFIRM" != "1" ]]; then' in content
    assert 'die "Non-interactive destructive cleanup requires --confirm 1"' in content
    assert "cleanup_board_refs" in content
    assert "cleanup_local_wiki_docs" in content
    assert "cleanup_generated_artifacts" in content
    assert "cleanup_github" in content
    assert 'script_for_tool="${script_path#"$REPO_ROOT"/}"' in content



def test_cleanup_script_removes_runtime_handoffs_and_stage_artifacts() -> None:
    content = CLEANUP_SCRIPT_PATH.read_text(encoding="utf-8")

    assert '"$REPO_ROOT/.digital-runtime/handoffs"' in content
    assert '"$REPO_ROOT/.digital-artifacts/10-data"' in content
    assert '"$REPO_ROOT/.digital-artifacts/20-done"' in content
    assert '"$REPO_ROOT/.digital-artifacts/30-specification"' in content
    assert '"$REPO_ROOT/.digital-artifacts/40-stage"' in content
    assert '"$REPO_ROOT/.digital-artifacts/50-planning"' in content
    assert '"$REPO_ROOT/.digital-artifacts/60-review"' in content
    assert '"$REPO_ROOT/.digital-artifacts/70-audits"' in content
    assert 'act "mkdir -p \\\"$REPO_ROOT/.digital-runtime/handoffs\\\""' in content


def test_cleanup_e2e_script_covers_temp_clone_and_optional_github_cycle() -> None:
    content = CLEANUP_E2E_SCRIPT_PATH.read_text(encoding="utf-8")

    assert "create_temp_clone" in content
    assert ".digital-runtime/e2e-cleanup" in content
    assert "run_local_e2e" in content
    assert "run_github_temp_cycle" in content
    assert "--github-test" in content
    assert "cleanup-e2e: local temp clone validation passed" in content
