from __future__ import annotations

import subprocess

from github_test_support import ROOT


SCRIPT = (
    ROOT
    / ".github"
    / "skills"
    / "shared/shell"
    / "scripts"
    / "github"
    / "gh-board-items-add.sh"
)


def test_board_item_add_requires_arguments() -> None:
    """TODO: add docstring for test_board_item_add_requires_arguments."""
    result = subprocess.run(
        ["bash", str(SCRIPT)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    # Script validates required args; at least one required-arg error must appear
    assert any(msg in result.stderr for msg in ("required", "Usage:"))
