from __future__ import annotations

from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_PATH = (
    ROOT
    / ".github"
    / "skills"
    / "shared/local-command-orchestration"
    / "scripts"
    / "prompt-scaffold.sh"
)


def test_prompt_scaffold_enforces_valid_name_and_help_sync() -> None:
    """TODO: add docstring for test_prompt_scaffold_enforces_valid_name_and_help_sync."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'PROMPT_NAME="${PROMPT_NAME:-}"' in content
    assert 'PROMPT_PURPOSE="${PROMPT_PURPOSE:-describe the command purpose}"' in content
    assert "^[[a-z0-9]+(-[a-z0-9]+)*$" not in content
    assert "^[a-z0-9]+(-[a-z0-9]+)*$" in content
    assert "prompts/help.prompt.md" in content
    assert "make $PROMPT_NAME" in content
    assert (
        "Use only \\`make ...\\` invocations for tool/script execution examples."
        in content
    )
    assert "[progress][prompt-scaffold]" in content


def test_prompt_scaffold_creates_prompt_and_skill_templates() -> None:
    """TODO: add docstring for test_prompt_scaffold_creates_prompt_and_skill_templates."""
    content = SCRIPT_PATH.read_text(encoding="utf-8")

    assert 'PROMPT_FILE="$PROMPTS_DIR/$PROMPT_NAME.prompt.md"' in content
    assert 'SKILL_DIR="$SKILLS_DIR/prompt-$PROMPT_NAME"' in content
    assert 'SKILL_FILE="$SKILL_DIR/SKILL.md"' in content
    assert "name: prompt-$PROMPT_NAME" in content
    assert "## Execution contract" in content
    assert "## Information flow" in content
    assert "## Documentation contract" in content
    assert "## Information Flow" in content
    assert "## Dependencies" in content
