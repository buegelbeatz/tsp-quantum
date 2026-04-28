# PR delivery artifact tests
# This module tests the shared-pr-delivery skill integration

import pytest
import tempfile
import os
from pathlib import Path


class TestPRDeliveryArtifacts:
    """Test PR delivery workflow artifact generation."""

    def test_pr_review_template_renders(self):
        """Verify pr_review_report.template.md is valid markdown template."""
        template_dir = Path(__file__).parent.parent.parent / "templates"
        template_file = template_dir / "pr_review_report.template.md"
        assert template_file.exists(), f"Template not found: {template_file}"
        
        content = template_file.read_text()
        # Verify required template variables are present
        required_vars = [
            "{{pr_title}}", "{{branch_name}}", "{{recommendation}}",
            "{{confidence_score}}", "{{score_correctness}}", "{{score_risk}}"
        ]
        for var in required_vars:
            assert var in content, f"Missing template variable: {var}"

    def test_skill_metadata_valid(self):
        """Verify SKILL.md layer metadata is set correctly."""
        skill_file = Path(__file__).parent.parent.parent / "SKILL.md"
        content = skill_file.read_text()
        # Verify layer is set to digital-generic-team
        assert "layer: digital-generic-team" in content, "Layer metadata incorrect"
        assert "shared-pr-delivery" in content, "Skill name not found"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
