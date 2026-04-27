from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (
            candidate / ".github" / "skills" / "layers" / "scripts" / "layers-tree.py"
        ).exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
LAYERS_TREE_SCRIPT = (
    ROOT / ".github" / "skills" / "layers" / "scripts" / "layers-tree.py"
)


def test_layers_tree_reads_override_registry() -> None:
    """TODO: add docstring for test_layers_tree_reads_override_registry."""
    content = LAYERS_TREE_SCRIPT.read_text(encoding="utf-8")

    assert ".digital-team" in content
    assert "overrides.yaml" in content
    assert "def load_override_paths(" in content


def test_layers_tree_renders_visual_status_markers() -> None:
    """TODO: add docstring for test_layers_tree_renders_visual_status_markers."""
    content = LAYERS_TREE_SCRIPT.read_text(encoding="utf-8")

    assert "⛭ override-registered" in content
    assert "✦ local-layer" in content
    assert "◌ overridden-by-child" in content


def test_layers_tree_groups_generic_agents_under_roles() -> None:
    """TODO: add docstring for test_layers_tree_groups_generic_agents_under_roles."""
    content = LAYERS_TREE_SCRIPT.read_text(encoding="utf-8")

    assert 'cat_name == "agents"' in content
    assert "roles/" in content
    assert 'startswith("generic-")' in content
