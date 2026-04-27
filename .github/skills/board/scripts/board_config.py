#!/usr/bin/env python3
# layer: digital-generic-team
"""Board configuration helpers for single-board and multi-board layouts."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any


DEFAULT_COLUMNS = ["backlog", "in-progress", "blocked", "done"]


def _strip_comment(line: str) -> str:
    if "#" not in line:
        return line.rstrip("\n")
    return line.split("#", 1)[0].rstrip("\n")


def _parse_scalar(value: str) -> Any:
    stripped = value.strip()
    if stripped in {"true", "True"}:
        return True
    if stripped in {"false", "False"}:
        return False
    if stripped in {"null", "None", ""}:
        return None
    return stripped.strip('"').strip("'")


def _parse_board_yaml(text: str) -> dict[str, Any]:
    config: dict[str, Any] = {
        "primary_system": "github",
        "git_board": {
            "enabled": True,
            "ref_prefix": "refs/board",
            "columns": list(DEFAULT_COLUMNS),
            "default_board": None,
            "boards": {},
        },
    }
    current_top: str | None = None
    current_board: str | None = None
    board_section: str | None = None

    for raw_line in text.splitlines():
        line = _strip_comment(raw_line)
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()

        if indent == 0:
            current_board = None
            board_section = None
            if stripped.endswith(":"):
                current_top = stripped[:-1]
                config.setdefault(current_top, {})
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                config[key.strip()] = _parse_scalar(value)
                current_top = None
            continue

        if current_top != "git_board":
            continue

        git_board = config.setdefault("git_board", {})

        if indent == 2:
            current_board = None
            if stripped == "columns:":
                board_section = "root-columns"
                git_board["columns"] = []
                continue
            if stripped == "boards:":
                board_section = "boards"
                git_board.setdefault("boards", {})
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                git_board[key.strip()] = _parse_scalar(value)
                board_section = None
            continue

        if (
            indent == 4
            and board_section == "root-columns"
            and stripped.startswith("- ")
        ):
            git_board.setdefault("columns", []).append(stripped[2:].strip())
            continue

        if (
            indent == 4
            and stripped.endswith(":")
            and git_board.get("boards") is not None
        ):
            current_board = stripped[:-1]
            git_board.setdefault("boards", {}).setdefault(current_board, {})
            board_section = "board"
            continue

        if current_board is None:
            continue

        board_config = git_board.setdefault("boards", {}).setdefault(current_board, {})
        if indent == 6:
            if stripped == "columns:":
                board_config["columns"] = []
                board_section = "board-columns"
                continue
            if ":" in stripped:
                key, _, value = stripped.partition(":")
                board_config[key.strip()] = _parse_scalar(value)
                board_section = "board"
            continue

        if (
            indent == 8
            and board_section == "board-columns"
            and stripped.startswith("- ")
        ):
            board_config.setdefault("columns", []).append(stripped[2:].strip())

    return config


def load_board_config(repo_root: Path) -> dict[str, Any]:
    """TODO: add docstring for load_board_config."""
    board_yaml = repo_root / ".digital-team" / "board.yaml"
    if not board_yaml.exists():
        raw = _parse_board_yaml("")
    else:
        raw = _parse_board_yaml(board_yaml.read_text(encoding="utf-8"))

    git_board = raw.setdefault("git_board", {})
    git_board.setdefault("enabled", True)
    git_board.setdefault("ref_prefix", "refs/board")
    git_board.setdefault("columns", list(DEFAULT_COLUMNS))
    git_board.setdefault("boards", {})

    board_entries = git_board.get("boards") or {}
    default_board = git_board.get("default_board") or git_board.get("active_board")

    normalized_boards: dict[str, dict[str, Any]] = {}
    if board_entries:
        for board_name, board_values in board_entries.items():
            board_values = dict(board_values or {})
            normalized_boards[board_name] = {
                "name": board_name,
                "label": board_values.get("label") or board_name.upper(),
                "ref_prefix": board_values.get("ref_prefix")
                or f"{git_board['ref_prefix'].rstrip('/')}/{board_name}",
                "columns": list(board_values.get("columns") or git_board["columns"]),
                "description": board_values.get("description") or "",
            }
        if default_board is None:
            default_board = next(iter(normalized_boards))
    else:
        default_board = default_board or "default"
        normalized_boards[default_board] = {
            "name": default_board,
            "label": default_board.upper(),
            "ref_prefix": git_board["ref_prefix"],
            "columns": list(git_board["columns"]),
            "description": "",
        }

    raw["git_board"] = {
        **git_board,
        "default_board": default_board,
        "boards": normalized_boards,
    }
    return raw


def list_boards(config: dict[str, Any]) -> list[dict[str, Any]]:
    """TODO: add docstring for list_boards."""
    return list(config["git_board"]["boards"].values())


def resolve_board(
    config: dict[str, Any], board_name: str | None = None
) -> dict[str, Any]:
    """TODO: add docstring for resolve_board."""
    boards = config["git_board"]["boards"]
    selected_name = board_name or config["git_board"]["default_board"]
    if selected_name not in boards:
        available = ", ".join(sorted(boards))
        raise KeyError(
            f"Unknown board '{selected_name}'. Available boards: {available}"
        )
    return boards[selected_name]


def _cli() -> int:
    parser = argparse.ArgumentParser(description="Resolve board configuration.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    shell_parser = subparsers.add_parser(
        "shell", help="Print shell-friendly board settings"
    )
    shell_parser.add_argument("repo_root")
    shell_parser.add_argument("board", nargs="?")

    list_parser = subparsers.add_parser("list", help="List configured boards")
    list_parser.add_argument("repo_root")

    default_parser = subparsers.add_parser("default", help="Print default board name")
    default_parser.add_argument("repo_root")

    args = parser.parse_args()
    repo_root = Path(args.repo_root).resolve()
    config = load_board_config(repo_root)

    if args.command == "shell":
        board = resolve_board(config, args.board)
        print(f"BOARD_NAME={board['name']}")
        print(f"BOARD_LABEL={board['label']}")
        print(f"REF_PREFIX={board['ref_prefix']}")
        print(f"COLUMNS={','.join(board['columns'])}")
        return 0

    if args.command == "list":
        default_board = config["git_board"]["default_board"]
        for board in list_boards(config):
            marker = "*" if board["name"] == default_board else "-"
            print(
                f"{marker} {board['name']}|{board['ref_prefix']}|{','.join(board['columns'])}|{board['label']}"
            )
        return 0

    if args.command == "default":
        print(config["git_board"]["default_board"])
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(_cli())
