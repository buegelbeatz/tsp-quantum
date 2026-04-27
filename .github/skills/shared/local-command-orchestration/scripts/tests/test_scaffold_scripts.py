from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPTS_DIR = (
    ROOT / ".github" / "skills" / "shared/local-command-orchestration" / "scripts"
)


def test_agent_scaffold_contains_governed_contract_sections() -> None:
    """Test that agent scaffold creates required agent governance sections."""
    content = (SCRIPTS_DIR / "agent-scaffold.sh").read_text(encoding="utf-8")

    assert 'AGENT_NAME="${AGENT_NAME:-}"' in content
    assert "## Mission" in content
    assert "## Responsibilities" in content
    assert "## Handoff Rules" in content
    assert "## Preferred Skills" in content
    assert "## Not Responsible For" in content
    assert "work_handoff_v1" in content


def test_instruction_scaffold_supports_stage_and_domain_instructions() -> None:
    """Test that instruction scaffold enforces category/name inputs and structure."""
    content = (SCRIPTS_DIR / "instruction-scaffold.sh").read_text(encoding="utf-8")

    assert 'INSTRUCTION_CATEGORY="${INSTRUCTION_CATEGORY:-}"' in content
    assert 'INSTRUCTION_NAME="${INSTRUCTION_NAME:-}"' in content
    assert "## Scope" in content
    assert "## Standards" in content
    assert "## Process" in content
    assert "## References" in content


def test_skill_scaffold_creates_dependencies_and_information_flow() -> None:
    """Test that skill scaffold creates the canonical SKILL.md sections."""
    content = (SCRIPTS_DIR / "skill-scaffold.sh").read_text(encoding="utf-8")

    assert 'SKILL_NAME="${SKILL_NAME:-}"' in content
    assert 'touch "$SKILL_DIR/requirements.txt"' in content
    assert "## Purpose" in content
    assert "## Outputs" in content
    assert "## Dependencies" in content
    assert "## Information Flow" in content
    assert ".github/skills/shared/shell/SKILL.md" in content
    assert "README.md" not in content


def test_handoff_scaffold_enforces_uppercase_name_and_schema() -> None:
    """Test that handoff scaffold creates canonical schema files."""
    content = (SCRIPTS_DIR / "handoff-scaffold.sh").read_text(encoding="utf-8")

    assert 'HANDOFF_NAME="${HANDOFF_NAME:-}"' in content
    assert 'HANDOFF_SCHEMA="${HANDOFF_SCHEMA:-}"' in content
    assert "^[A-Z_]+$" in content
    assert "schema: $HANDOFF_SCHEMA" in content
    assert "required:" in content
    assert "artifacts" in content
