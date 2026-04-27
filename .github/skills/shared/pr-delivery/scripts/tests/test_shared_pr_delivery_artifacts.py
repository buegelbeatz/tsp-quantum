"""Tests for the shared/pr-delivery skill static artifacts.

Validates that the SKILL.md and PR review report template are structurally
complete and contain all required fields.
"""

from __future__ import annotations

from pathlib import Path


def _skill_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        skills = candidate / ".github" / "skills" / "shared/pr-delivery"
        if skills.exists():
            return skills
    raise RuntimeError("Could not locate shared/pr-delivery skill root")


SKILL_ROOT = _skill_root()
SKILL_MD = SKILL_ROOT / "SKILL.md"
TEMPLATE = SKILL_ROOT / "templates" / "pr_review_report.template.md"

REQUIRED_TEMPLATE_PLACEHOLDERS = (
    "{{pr_title}}",
    "{{branch_name}}",
    "{{scope}}",
    "{{summary}}",
    "{{tests_status}}",
    "{{lint_status}}",
    "{{typing_status}}",
    "{{risks}}",
)

REQUIRED_SKILL_SECTIONS = (
    "## Purpose",
    "## When to Use",
    "## Features",
)


class TestSkillMetadata:
    def test_skill_md_exists(self) -> None:
        """TODO: add docstring for test_skill_md_exists."""
        assert SKILL_MD.exists(), f"SKILL.md not found at {SKILL_MD}"

    def test_skill_md_has_name_in_frontmatter(self) -> None:
        """TODO: add docstring for test_skill_md_has_name_in_frontmatter."""
        content = SKILL_MD.read_text(encoding="utf-8")
        assert 'name: "shared/pr-delivery"' in content

    def test_skill_md_has_description_in_frontmatter(self) -> None:
        """TODO: add docstring for test_skill_md_has_description_in_frontmatter."""
        content = SKILL_MD.read_text(encoding="utf-8")
        assert "description:" in content

    def test_skill_md_has_required_sections(self) -> None:
        """TODO: add docstring for test_skill_md_has_required_sections."""
        content = SKILL_MD.read_text(encoding="utf-8")
        for section in REQUIRED_SKILL_SECTIONS:
            assert section in content, f"Missing section: {section}"

    def test_skill_md_mentions_approval_gate(self) -> None:
        """TODO: add docstring for test_skill_md_mentions_approval_gate."""
        content = SKILL_MD.read_text(encoding="utf-8")
        assert "Approval" in content or "approval" in content


class TestPrReviewTemplate:
    def test_template_exists(self) -> None:
        """TODO: add docstring for test_template_exists."""
        assert TEMPLATE.exists(), f"Template not found at {TEMPLATE}"

    def test_template_contains_all_required_placeholders(self) -> None:
        """TODO: add docstring for test_template_contains_all_required_placeholders."""
        content = TEMPLATE.read_text(encoding="utf-8")
        for placeholder in REQUIRED_TEMPLATE_PLACEHOLDERS:
            assert placeholder in content, f"Missing placeholder: {placeholder}"

    def test_template_has_checks_section(self) -> None:
        """TODO: add docstring for test_template_has_checks_section."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "## Checks" in content

    def test_template_has_risks_section(self) -> None:
        """TODO: add docstring for test_template_has_risks_section."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "## Risks" in content

    def test_template_has_summary_section(self) -> None:
        """TODO: add docstring for test_template_has_summary_section."""
        content = TEMPLATE.read_text(encoding="utf-8")
        assert "## Summary" in content
