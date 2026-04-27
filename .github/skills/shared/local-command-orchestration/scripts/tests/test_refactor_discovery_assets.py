from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
DISCOVERY_SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "refactor-discovery.sh"
)
REFACTOR_TEMPLATE = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "templates"
    / "refactor-review-template.md"
)


def test_refactor_discovery_script_uses_git_tracked_discovery_and_stable_sections() -> (
    None
):
    """TODO: add docstring for test_refactor_discovery_script_uses_git_tracked_discovery_and_stable_sections."""
    content = DISCOVERY_SCRIPT.read_text(encoding="utf-8")

    assert "set -euo pipefail" in content
    assert 'git -C "$REPO_ROOT" ls-files' in content
    assert "===RELEVANT_FILES===" in content
    assert "===OVER_THRESHOLD===" in content
    assert "===LINE_COUNTS===" in content
    assert "tracked_count" in content
    assert "remaining_count" in content


def test_refactor_template_exists_and_contains_compact_sections() -> None:
    """TODO: add docstring for test_refactor_template_exists_and_contains_compact_sections."""
    content = REFACTOR_TEMPLATE.read_text(encoding="utf-8")

    assert "## Tracked files" in content
    assert "Relevant files reviewed in detail" in content
    assert "Remaining tracked files reviewed and summarized" in content
    assert "## Findings" in content
    assert "## Refactor candidates" in content
    assert "## Security review" in content
    assert "## Documentation review" in content
