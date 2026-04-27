from __future__ import annotations

import re
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "update.sh").exists() and (
            candidate / ".github" / "prompts"
        ).exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
PROMPT_GOVERNANCE_INSTRUCTIONS = (
    ROOT
    / ".github"
    / "instructions"
    / "governance-layer"
    / "prompt-governance.instructions.md"
)

PROMPT_WORKFLOW_SHELL_ENTRYPOINTS: tuple[Path, ...] = (
    ROOT / "update.sh",
    ROOT / ".github" / "skills" / "shared/delivery" / "scripts" / "prompt-pull.sh",
    ROOT
    / ".github"
    / "skills"
    / "shared/orchestration"
    / "scripts"
    / "layer_quality_fix.sh",
    ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "scripts"
    / "artifacts-testdata-2-input.sh",
    ROOT / ".github" / "skills" / "artifacts" / "scripts" / "artifacts-input-2-data.sh",
    ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "scripts"
    / "artifacts-data-2-specification.sh",
    ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "scripts"
    / "artifacts-specification-2-stage.sh",
    ROOT
    / ".github"
    / "skills"
    / "artifacts"
    / "scripts"
    / "artifacts-specification-2-planning.sh",
)

HEREDOC_PATTERN = re.compile(r"<<-?\s*['\"]?[A-Za-z_][A-Za-z0-9_]*['\"]?")


def _find_heredoc_lines(content: str) -> list[str]:
    offenders: list[str] = []
    for line in content.splitlines():
        if "<<<" in line:
            continue
        if HEREDOC_PATTERN.search(line):
            offenders.append(line.strip())
    return offenders


def test_prompt_governance_documents_no_heredoc_rule() -> None:
    """TODO: add docstring for test_prompt_governance_documents_no_heredoc_rule."""
    content = PROMPT_GOVERNANCE_INSTRUCTIONS.read_text(encoding="utf-8")

    assert "do not use shell heredoc blocks" in content
    assert "Move complex multiline logic into dedicated runtime files" in content


def test_prompt_workflow_shell_entrypoints_do_not_use_heredoc() -> None:
    """TODO: add docstring for test_prompt_workflow_shell_entrypoints_do_not_use_heredoc."""
    for script_path in PROMPT_WORKFLOW_SHELL_ENTRYPOINTS:
        assert script_path.exists(), (
            f"Missing prompt workflow entrypoint: {script_path}"
        )

        content = script_path.read_text(encoding="utf-8")
        offenders = _find_heredoc_lines(content)
        assert not offenders, f"Found heredoc usage in {script_path}: {offenders}"
