from __future__ import annotations

from pathlib import Path

from board_test_helpers import load_module_from_path


def _load_module():
    script_dir = Path(__file__).resolve().parents[1]
    script_path = script_dir / "board_config.py"
    return load_module_from_path(script_path, "board_config")


def test_load_board_config_supports_multiple_lifecycle_boards(tmp_path: Path) -> None:
    """TODO: add docstring for test_load_board_config_supports_multiple_lifecycle_boards."""
    module = _load_module()
    repo_root = tmp_path
    board_yaml = repo_root / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True, exist_ok=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: pilot",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    mvp:",
                "      label: MVP",
                "      ref_prefix: refs/board/mvp",
                "    pilot:",
                "      label: PILOT",
                "      ref_prefix: refs/board/pilot",
                "      columns:",
                "        - backlog",
                "        - in-progress",
                "        - done",
            ]
        ),
        encoding="utf-8",
    )

    config = module.load_board_config(repo_root)

    assert config["git_board"]["default_board"] == "pilot"
    assert config["git_board"]["boards"]["mvp"]["ref_prefix"] == "refs/board/mvp"
    assert config["git_board"]["boards"]["pilot"]["columns"] == [
        "backlog",
        "in-progress",
        "done",
    ]


def test_load_board_config_keeps_single_board_backward_compatibility(
    tmp_path: Path,
) -> None:
    """TODO: add docstring for test_load_board_config_keeps_single_board_backward_compatibility."""
    module = _load_module()
    repo_root = tmp_path
    board_yaml = repo_root / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True, exist_ok=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: none",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  columns:",
                "    - backlog",
                "    - done",
            ]
        ),
        encoding="utf-8",
    )

    config = module.load_board_config(repo_root)
    board = module.resolve_board(config)

    assert config["git_board"]["default_board"] == "default"
    assert board["ref_prefix"] == "refs/board"
    assert board["columns"] == ["backlog", "done"]
