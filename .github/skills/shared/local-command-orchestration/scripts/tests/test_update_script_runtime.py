from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


def test_update_script_forces_local_python_for_repo_runtime_helpers() -> None:
    """Test that update.sh disables container preference for repo-local Python helpers."""
    content = (_repo_root() / "update.sh").read_text(encoding="utf-8")

    assert "RUN_TOOL_PREFER_CONTAINER=0" in content
    assert 'bash "$_SHARED_SHELL/run-tool.sh" python3 "$@"' in content


def test_update_script_bootstrap_manifest_is_valid_json() -> None:
    """Ensure bootstrap fallback writes a valid JSON manifest for override validation."""
    content = (_repo_root() / "update.sh").read_text(encoding="utf-8")

    assert "write_empty_backup_manifest()" in content
    assert '"schema": "local_backup_manifest_v1"' in content
    assert 'touch "$manifest_path"' not in content


def test_update_script_prunes_generated_stage_prompts_before_backup() -> None:
    """Ensure generated stage prompts are pruned before backup so they are never treated as overrides."""
    content = (_repo_root() / "update.sh").read_text(encoding="utf-8")

    assert "_prune_generated_stage_prompts()" in content
    # Must be called before backup_local_files in the Phase 1 block
    prune_pos = content.find("_prune_generated_stage_prompts\n")
    backup_pos = content.find("backup_local_files ")
    assert prune_pos != -1, "_prune_generated_stage_prompts call not found"
    assert prune_pos < backup_pos, "_prune_generated_stage_prompts must be called before backup_local_files"
    assert "grep -m1 '^command:[[:space:]]*' \"$stage_file\" 2>/dev/null || true" in content
