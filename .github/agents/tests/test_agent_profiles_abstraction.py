"""Validate agent profile files avoid concrete artifact path coupling."""

from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    """Resolve repository root by locating the active layer marker."""
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
AGENTS_DIR = ROOT / ".github" / "agents"


def test_agent_profiles_do_not_embed_concrete_artifact_paths() -> None:
    """Ensure agent templates remain path-agnostic for artifact locations."""
    forbidden_tokens = (
        ".digital-artifacts/",
        "10-data/INVENTORY.md",
        "30-specification/INVENTORY.md",
        "40-planning/sprints/",
    )

    for agent_file in AGENTS_DIR.glob("*.agent.md"):
        content = agent_file.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            assert token not in content, (
                f"{agent_file.name} contains forbidden concrete path token: {token}"
            )
