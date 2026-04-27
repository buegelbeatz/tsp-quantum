from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()


def test_update_script_uses_canonical_shared_skill_paths() -> None:
    content = (ROOT / "update.sh").read_text(encoding="utf-8")

    assert 'UPDATE_RUNTIME_PY="$GITHUB_DIR/skills/shared/runtime/scripts/update_runtime.py"' in content
    assert '_SHARED_SHELL="$GITHUB_DIR/skills/shared/shell/scripts"' in content
    assert "shared-runtime" not in content
    assert "shared-shell" not in content


def test_gitattributes_exposes_python_and_markdown_to_linguist() -> None:
    content = (ROOT / ".gitattributes").read_text(encoding="utf-8")

    assert "*.py linguist-detectable=true" in content
    assert "*.md linguist-detectable=true" in content
    assert ".github/**/*.py linguist-detectable=true" in content
    assert ".github/**/*.md linguist-detectable=true" in content
    assert "README.md linguist-detectable=true" in content
    assert "linguist-documentation=true" not in content


def test_readme_references_canonical_tool_registry_and_badges() -> None:
    content = (ROOT / "README.md").read_text(encoding="utf-8")

    assert "Python-3.14%2B" in content
    assert "ShellCheck" in content
    assert "GitHub%20CLI" in content
    assert "Mermaid%20CLI" in content
    assert ".github/skills/shared/shell/scripts/metadata/tools.csv" in content
    assert ".github/skills/shared/shell/scripts/run-tool.sh" in content
    assert "shared-shell" not in content
