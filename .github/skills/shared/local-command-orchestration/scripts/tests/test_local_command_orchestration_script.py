from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "run-local-update.sh"
)
HELPER_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "lib"
    / "run-local-update-lib.sh"
)
README_MERGE_CHECK_SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "check-readme-merge.sh"
)


def test_run_local_update_executes_update_and_optional_verification() -> None:
    """TODO: add docstring for test_run_local_update_executes_update_and_optional_verification."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")
    helper_content = HELPER_PATH.read_text(encoding="utf-8")

    assert 'DRY_RUN="${DIGITAL_TEAM_DRY_RUN:-0}"' in content
    assert 'RUN_VERIFY="${DIGITAL_TEAM_RUN_VERIFY:-1}"' in content
    assert 'VERIFY_IF_NO_CHANGES="${DIGITAL_TEAM_VERIFY_IF_NO_CHANGES:-0}"' in content
    assert "TEST_RUNNER_SH=" in content
    assert 'source "$RUN_LOCAL_UPDATE_LIB"' in content
    assert "detect_bootstrap_mode()" in helper_content
    assert "verification_expr_for_mode()" in helper_content
    assert "collect_update_scope_status()" in helper_content
    assert "status_entry_count()" in helper_content
    assert "print_summary_table()" in helper_content
    assert "compact_file_delta()" in helper_content
    assert "$REPO_ROOT/.digital-team/scripts/update.sh" in content
    assert (
        "DIGITAL_TEAM_TEST_TARGET=.digital-team/scripts/tests/test_root_bootstrap_scripts.py"
        in content
    )
    assert "DIGITAL_TEAM_TEST_EXPR=" in content
    assert "step=2/3 action=skip-verification" in content
    assert "[info][update] verification skipped" in content
    assert ".vscode/mcp.json" in content
    assert "| 2/3 |" in helper_content
    assert "| 3/3 |" in helper_content
    assert "no update-scope changes introduced by this run" in content
    assert (
        "verification skipped: this run produced no new update-scope changes" in content
    )
    assert "| Step | Action | Status | Detail | Files |" in helper_content
    assert "    env" in content
    assert 'eval "' not in content
    assert "[progress][update]" in helper_content
    assert "[dry-run]" in helper_content


def test_check_readme_merge_script_executes_focused_bootstrap_tests() -> None:
    """TODO: add docstring for test_check_readme_merge_script_executes_focused_bootstrap_tests."""
    content = README_MERGE_CHECK_SCRIPT_PATH.read_text(encoding="utf-8")

    assert (
        'TEST_EXPR="${DIGITAL_TEAM_README_MERGE_TEST_EXPR:-merges_layer_readmes_into_github_targets or backup_excludes_root_readme}"'
        in content
    )
    assert "TEST_RUNNER_SH=" in content
    assert (
        'for candidate in "$REPO_ROOT"/.digital-runtime/layers/*/venv/bin/python'
        in content
    )
    assert ".digital-team/scripts/tests/test_root_bootstrap_scripts.py" in content
    assert "[progress][check-readme-merge]" in content
