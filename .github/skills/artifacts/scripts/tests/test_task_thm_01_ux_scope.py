"""Contract tests for the TASK-THM-01 UX delivery artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "artifacts").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()


def _require_paths(*paths: Path) -> None:
    missing = [str(path) for path in paths if not path.exists()]
    if missing:
        pytest.skip(f"THM-01 contract artifacts not available in this environment: {', '.join(missing)}")


def test_task_thm_01_scope_contains_required_contract_sections() -> None:
    """THM-01 UX scope artifacts should satisfy the planning contract."""

    scope_path = (
        ROOT
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-24"
        / "project"
        / "UX_SCOPE_THM-01.md"
    )
    spec_path = (
        ROOT
        / ".digital-artifacts"
        / "30-specification"
        / "2026-04-24"
        / "ux-designer"
        / "TASK-THM-01.ux-designer.specification.md"
    )

    _require_paths(scope_path, spec_path)

    scope_text = scope_path.read_text(encoding="utf-8")
    spec_text = spec_path.read_text(encoding="utf-8")

    assert "Target user" in scope_text
    assert "Measurable Usability Target" in scope_text
    assert "WCAG 2.2 AA" in scope_text
    assert "Heuristic review" in scope_text
    assert "recommendation: proceed" in scope_text

    assert "Target User Segment" in spec_text
    assert "Measurable Usability Target" in spec_text
    assert "Human Approval Communication" in spec_text
    assert "Validation Evidence" in spec_text
    assert "project-delivery-execution-thm01-scribble-r1.svg" in spec_text


def test_task_thm_01_scope_references_review_and_scribble() -> None:
    """The stakeholder-facing wiki page should link the THM-01 review evidence and scribble."""

    wiki_path = ROOT / "docs" / "wiki" / "project-delivery-execution-thm01.md"
    _require_paths(wiki_path)
    wiki_text = wiki_path.read_text(encoding="utf-8")

    assert "Outcome: proceed" in wiki_text
    assert "Validation Q/A" in wiki_text
    assert "```mermaid" in wiki_text
    assert "UX_SCOPE_THM-01.md" in wiki_text
    assert "project-delivery-execution-thm01-scribble-r1.svg" in wiki_text