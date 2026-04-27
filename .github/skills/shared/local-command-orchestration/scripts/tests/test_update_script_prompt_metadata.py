from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "update.sh").exists() and (
            candidate / ".github" / "skills" / "shared/local-command-orchestration"
        ).exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
UPDATE_SCRIPT = ROOT / "update.sh"
UPDATE_RUNTIME_SCRIPT = (
    ROOT / ".github" / "skills" / "shared/runtime" / "scripts" / "update_runtime.py"
)


def test_update_script_preserves_prompt_layer_as_html_comment() -> None:
    """TODO: add docstring for test_update_script_preserves_prompt_layer_as_html_comment."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "HTML_LAYER_RE = re.compile" in content
    assert "normalized_path" in content and "/prompts/" in content
    assert (
        'marker = f"<!-- layer: {layer_name} -->"' in content
        or "marker = f'<!-- layer: {layer_name} -->'" in content
    )
    assert 'r"^layer:[ \\t]*.*\\n?"' in content
    assert "flags=re.MULTILINE" in content
    assert "match.group(1)" in content or "m.group(1)" in content


def test_update_script_detects_prompt_layer_from_html_comment() -> None:
    """TODO: add docstring for test_update_script_detects_prompt_layer_from_html_comment."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "comment_match = HTML_LAYER_RE.search" in content
    assert "return comment_match.group(1).strip() if comment_match else None" in content


def test_update_runtime_contains_built_in_report_command() -> None:
    """TODO: add docstring for test_update_runtime_contains_built_in_report_command."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "def report_update(" in content
    assert 'subparsers.add_parser("report-update")' in content
    assert "[update][report] layer attribution:" in content


def test_update_script_avoids_heredoc_and_uses_runtime_helper() -> None:
    """TODO: add docstring for test_update_script_avoids_heredoc_and_uses_runtime_helper."""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert "UPDATE_RUNTIME_PY=" in content
    assert 'run_python "$UPDATE_RUNTIME_PY"' in content
    assert 'report-update "$REPO_ROOT" "$GITHUB_DIR" "$CLAUDE_DIR"' in content
    assert "<<'PYEOF'" not in content


def test_update_script_keeps_existing_root_makefile_and_enforces_quality_include() -> (
    None
):
    """TODO: add docstring for test_update_script_keeps_existing_root_makefile_and_enforces_quality_include."""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert "ensure_makefile_commands_include" in content
    assert 'if [[ "$rel" == "Makefile" ]] && [[ -f "$dest" ]]; then' in content
    assert "Phase 3: kept existing root Makefile (no overwrite)" in content
    assert "include .github/make/commands.mk" in content


def test_update_script_prunes_stale_claude_commands() -> None:
    """TODO: add docstring for test_update_script_prunes_stale_claude_commands."""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert "generated_commands=()" in content
    assert 'for cmd_file in "$CLAUDE_DIR/commands"/*.md; do' in content
    assert 'rm -f "$cmd_file"' in content


def test_update_runtime_supports_prompt_pruning_from_customizations_index() -> None:
    """TODO: add docstring for test_update_runtime_supports_prompt_pruning_from_customizations_index."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "prompt-governance.yaml" in content
    assert "customizations-index.json" in content
    assert "def prune_prompts(" in content
    assert 'subparsers.add_parser("prune-prompts")' in content


def test_update_runtime_supports_central_stage_catalog() -> None:
    """Stage runtime metadata should be loaded from stages-action catalog."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "STAGE_CATALOG_RELATIVE" in content
    assert "skills/stages-action/stages.yaml" in content
    assert "def _load_stage_catalog(" in content
    assert 'subparsers.add_parser("stage-commands")' in content


def test_update_runtime_enforces_explicit_override_registry() -> None:
    """TODO: add docstring for test_update_runtime_enforces_explicit_override_registry."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "def validate_overrides(" in content
    assert ".digital-team/overrides.yaml" in content
    assert "override drift detected" in content
    assert 'subparsers.add_parser("validate-overrides")' in content


def test_update_runtime_backs_up_only_current_layer_and_rejects_untagged() -> None:
    """TODO: add docstring for test_update_runtime_backs_up_only_current_layer_and_rejects_untagged."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert '"schema": "local_backup_manifest_v1"' in content
    assert "if layer is None:" in content
    assert "Found untagged files under .github/" in content


def test_update_runtime_only_requires_layer_tags_for_supported_file_types() -> None:
    """Only markdown, YAML, and shell files should block update when untagged."""
    content = UPDATE_RUNTIME_SCRIPT.read_text(encoding="utf-8")

    assert "LAYER_METADATA_EXTENSIONS" in content
    assert "def requires_layer_metadata(file_path: Path) -> bool:" in content
    assert "if requires_layer_metadata(file_path):" in content
    assert 'normalized_path.endswith("/index.instructions.md")' in content
    assert '"/.github/workflows/" in normalized_path' in content


def test_update_script_wires_override_validation_gate() -> None:
    """TODO: add docstring for test_update_script_wires_override_validation_gate."""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert 'OVERRIDES_YAML="$REPO_ROOT/.digital-team/overrides.yaml"' in content
    assert "validate_overrides()" in content
    assert "validate-overrides" in content
    assert "kept existing .digital-team/overrides.yaml (no overwrite)" in content


def test_update_script_preserves_existing_container_publish_config() -> None:
    """TODO: add docstring for test_update_script_preserves_existing_container_publish_config."""
    content = UPDATE_SCRIPT.read_text(encoding="utf-8")

    assert ".digital-team/container-publish.yaml" in content
    assert (
        "kept existing .digital-team/container-publish.yaml (no overwrite)" in content
    )


def test_list_stages_emits_three_level_status() -> None:
    """list_stages must resolve available / started / in-progress / active status."""
    import importlib.util
    import sys
    import tempfile

    spec = importlib.util.spec_from_file_location("update_runtime", UPDATE_RUNTIME_SCRIPT)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["update_runtime"] = mod
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        github_dir = tmp_path / ".github"
        stages_dir = github_dir / "instructions" / "stages"
        stages_dir.mkdir(parents=True)
        (stages_dir / "10-foo.instructions.md").write_text(
            "---\nname: foo\ndescription: Foo Stage\ncommand: foo\nlayer: test\n---\n",
            encoding="utf-8",
        )

        artifacts_base = tmp_path / ".digital-artifacts" / "40-stage"
        results: dict[str, str] = {}

        import io
        from contextlib import redirect_stdout

        def _capture_status() -> str:
            buf = io.StringIO()
            with redirect_stdout(buf):
                mod.list_stages(github_dir, tmp_path)
            return buf.getvalue()

        # available: no stage dir
        results["available"] = _capture_status()
        assert "available" in results["available"]

        # started: stage dir exists but no doc
        (artifacts_base / "foo").mkdir(parents=True)
        (artifacts_base / "foo" / "other.md").write_text("x", encoding="utf-8")
        results["started"] = _capture_status()
        assert "started" in results["started"]

        # in-progress: doc exists with status: in-progress
        (artifacts_base / "foo" / "FOO.md").write_text(
            "---\nstatus: in-progress\n---\n", encoding="utf-8"
        )
        results["in-progress"] = _capture_status()
        assert "in-progress" in results["in-progress"]

        # active: doc exists with status: active
        (artifacts_base / "foo" / "FOO.md").write_text(
            "---\nstatus: active\n---\n", encoding="utf-8"
        )
        results["active"] = _capture_status()
        assert "active" in results["active"]
