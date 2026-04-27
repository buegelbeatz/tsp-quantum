#!/usr/bin/env python3
# layer: digital-generic-team
"""Render one or multiple git-backed kanban boards from configured ref namespaces."""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from board_config import list_boards, load_board_config, resolve_board

# ---------------------------------------------------------------------------
# ANSI
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[91m"
YELLOW = "\033[93m"
GREEN = "\033[92m"
BLUE = "\033[94m"
CYAN = "\033[96m"
WHITE = "\033[97m"


def c(*codes: str) -> str:
    """TODO: add docstring for c."""
    return "".join(codes)


# ---------------------------------------------------------------------------
# Ticket parsing
# ---------------------------------------------------------------------------


def parse_ticket(blob: str) -> dict[str, Any]:
    """TODO: add docstring for parse_ticket."""
    ticket: dict[str, str] = {}

    def _inline_list(value: str) -> list[str]:
        stripped = value.strip()
        if not (stripped.startswith("[") and stripped.endswith("]")):
            return []
        content = stripped[1:-1].strip()
        if not content:
            return []
        row = next(csv.reader([content], skipinitialspace=True), [])
        return [item.strip().strip('"').strip("'") for item in row if item.strip()]

    lines = blob.splitlines()
    idx = 0
    while idx < len(lines):
        line = lines[idx].rstrip("\n")
        stripped = line.strip()

        if not stripped or stripped.startswith("#"):
            idx += 1
            continue
        if line.startswith(" ") or ":" not in line:
            idx += 1
            continue

        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()

        if value == "|":
            block: list[str] = []
            j = idx + 1
            while j < len(lines):
                tail = lines[j]
                if re.match(r"^[^\s].*:\s*", tail):
                    break
                if tail.startswith("  "):
                    block.append(tail[2:])
                j += 1
            ticket[key] = "\n".join(block).strip()
            idx = j
            continue

        if key in {"labels", "acceptance_criteria", "definition_of_done"}:
            values: list[str] = []
            if value.startswith("[") and value.endswith("]"):
                values = _inline_list(value)
                idx += 1
            elif not value:
                j = idx + 1
                while j < len(lines):
                    tail = lines[j]
                    if re.match(r"^[^\s].*:\s*", tail):
                        break
                    stripped_tail = tail.strip()
                    if stripped_tail.startswith("-"):
                        values.append(
                            stripped_tail[1:].strip().strip('"').strip("'")
                        )
                    j += 1
                idx = j
            else:
                values = [value.strip('"').strip("'")]
                idx += 1

            if key == "labels" and values:
                ticket["_labels"] = values  # type: ignore[assignment]
            elif key != "labels":
                ticket[key] = values  # type: ignore[assignment]
            continue

        ticket[key] = value.strip('"').strip("'")
        idx += 1

    return ticket


# ---------------------------------------------------------------------------
# Git refs reading
# ---------------------------------------------------------------------------


def git(repo_root: Path, *args: str) -> str:
    """TODO: add docstring for git."""
    result = subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip()


def list_board_refs(repo_root: Path, ref_prefix: str) -> list[str]:
    """TODO: add docstring for list_board_refs."""
    out = git(repo_root, "for-each-ref", "--format=%(refname)", ref_prefix + "/")
    return [line.strip() for line in out.splitlines() if line.strip()]


def discover_boards_from_refs(
    repo_root: Path,
    root_prefix: str,
    configured_boards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """TODO: add docstring for discover_boards_from_refs."""
    refs = list_board_refs(repo_root, root_prefix.rstrip("/"))
    if not refs:
        return []

    known_columns: list[str] = []
    for board in configured_boards:
        for column in board.get("columns", []):
            if column not in known_columns:
                known_columns.append(column)
    if not known_columns:
        known_columns = ["backlog", "in-progress", "blocked", "done"]

    discovered: dict[str, dict[str, Any]] = {}
    root = root_prefix.rstrip("/")

    def ensure_board(name: str, ref_prefix: str) -> dict[str, Any]:
        """TODO: add docstring for ensure_board."""
        if name not in discovered:
            discovered[name] = {
                "name": name,
                "label": name.upper(),
                "ref_prefix": ref_prefix,
                "columns": list(known_columns),
                "description": "",
            }
        return discovered[name]

    for ref in refs:
        if not ref.startswith(root + "/"):
            continue
        rel = ref[len(root) + 1 :]
        parts = rel.split("/")
        if len(parts) < 2:
            continue

        if parts[0] in known_columns:
            board = ensure_board("default", root)
            if parts[0] not in board["columns"]:
                board["columns"].append(parts[0])
            continue

        if len(parts) >= 3:
            board_name = parts[0]
            col = parts[1]
            # Sprint refs live under refs/board/<board>/sprints/<id> and are
            # metadata, not Kanban columns. Rendering them as a board column is
            # confusing in make board output.
            if col == "sprints":
                continue
            board = ensure_board(board_name, f"{root}/{board_name}")
            if col not in board["columns"]:
                board["columns"].append(col)

    return list(discovered.values())


def merge_configured_and_discovered_boards(
    configured_boards: list[dict[str, Any]],
    discovered_boards: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """TODO: add docstring for merge_configured_and_discovered_boards."""
    by_name: dict[str, dict[str, Any]] = {
        board["name"]: board for board in configured_boards
    }

    for discovered in discovered_boards:
        name = discovered["name"]
        if name not in by_name:
            by_name[name] = discovered
            continue

        existing_cols = by_name[name].get("columns", [])
        for col in discovered.get("columns", []):
            if col not in existing_cols:
                existing_cols.append(col)

    ordered: list[dict[str, Any]] = []
    for board in configured_boards:
        ordered.append(by_name[board["name"]])

    for board in discovered_boards:
        if board["name"] not in {b["name"] for b in configured_boards}:
            ordered.append(by_name[board["name"]])

    return ordered


def read_blob(repo_root: Path, ref: str) -> str:
    """TODO: add docstring for read_blob."""
    return git(repo_root, "cat-file", "blob", ref)


def load_column(repo_root: Path, ref_prefix: str, column: str) -> list[dict[str, str]]:
    """TODO: add docstring for load_column."""
    col_prefix = f"{ref_prefix}/{column}/"
    refs = list_board_refs(repo_root, col_prefix.rstrip("/"))
    tickets = []
    for ref in refs:
        blob = read_blob(repo_root, ref)
        if blob:
            t = parse_ticket(blob)
            if "id" not in t:
                t["id"] = ref.split("/")[-1]
            t["_column"] = column
            tickets.append(t)
    return tickets


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------

COL_WIDTH = 24
DEFAULT_COLUMNS_PER_ROW = 4

COLUMN_COLORS = {
    "backlog": (BLUE, "□", "BACKLOG"),
    "in-progress": (CYAN, "◎", "IN PROGRESS"),
    "blocked": (RED, "⚠", "BLOCKED"),
    "done": (GREEN, "✓", "DONE"),
}

LABEL_COLORS = {
    "epic": YELLOW,
    "story": BLUE,
    "task": CYAN,
    "bug": RED,
    "blocked": RED,
    "hotfix": RED,
    "risk": RED,
    "security": RED,
    "infra": WHITE,
    "ops": WHITE,
    "docs": GREEN,
    "feature": GREEN,
    "enhancement": GREEN,
    "priority/high": RED,
    "priority/medium": YELLOW,
    "priority/low": BLUE,
}

STAGE_LABELS = {
    "exploration",
    "discovery",
    "ideation",
    "paperfit",
    "project",
    "mvp",
    "pilot",
    "production",
}


def truncate(s: str, n: int) -> str:
    """TODO: add docstring for truncate."""
    return s if len(s) <= n else s[: n - 1] + "…"


def _ansi_enabled() -> bool:
    if os.getenv("NO_COLOR") is not None:
        return False
    return sys.stdout.isatty()


def _style(text: str, *codes: str) -> str:
    if not _ansi_enabled():
        return text
    return c(*codes) + text + RESET


def _compact_mode_enabled() -> bool:
    """Return True when empty board columns should be hidden."""
    if os.getenv("BOARD_FULL", "").strip().lower() in {"1", "true", "yes", "on"}:
        return False
    raw = os.getenv("BOARD_COMPACT_MODE", "0").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def render_labels(ticket: dict[str, str]) -> list[str]:
    """TODO: add docstring for render_labels."""
    raw_labels: list[str] | str = ticket.get("_labels", [])  # type: ignore[assignment]
    if not raw_labels:
        raw_labels = infer_labels(ticket)
    if not isinstance(raw_labels, list):
        return []

    rendered: list[str] = []
    for label in raw_labels:
        label_text = str(label).strip()
        if not label_text:
            continue
        label_key = label_text.lower()
        label_color = LABEL_COLORS.get(label_key)
        if label_color is None and ":" in label_key:
            label_color = LABEL_COLORS.get(label_key.split(":", 1)[0], WHITE)
        if label_color is None:
            label_color = WHITE
        rendered.append(_style(f"[{truncate(label_text, 18)}]", BOLD, label_color))
    return rendered


def _bundle_code_from_ticket_id(ticket_id: str) -> str:
    """Extract the planning bundle code from a deterministic board ticket id."""
    parts = [part.strip() for part in ticket_id.split("-") if part.strip()]
    if len(parts) < 3:
        return ""
    return "-".join(parts[1:-1])


def _display_title(title: str) -> str:
    """Remove redundant stage prefixes from ticket titles for board rendering."""
    match = re.match(r"^\[(?P<label>[^\]]+)\]\s*(?P<rest>.+)$", title.strip())
    if not match:
        return title
    label = match.group("label").strip().lower()
    if label in STAGE_LABELS:
        return match.group("rest").strip()
    return title


def infer_labels(ticket: dict[str, str]) -> list[str]:
    """TODO: add docstring for infer_labels."""
    inferred: list[str] = []

    ticket_id = str(ticket.get("id", "")).strip()
    title = str(ticket.get("title", "")).strip()

    if ticket_id:
        suffix = ticket_id.split("-")[-1].lower()
        if suffix in {"epic", "story", "task", "bug"}:
            inferred.append(suffix)
        if suffix == "task":
            bundle_code = _bundle_code_from_ticket_id(ticket_id)
            if bundle_code:
                inferred.extend(
                    [
                        f"story:STORY-{bundle_code}",
                        f"epic:EPIC-{bundle_code}",
                    ]
                )

    bracket_match = re.match(r"\[(?P<label>[^\]]+)\]", title)
    if bracket_match:
        label = bracket_match.group("label").strip().lower()
        if label and label not in STAGE_LABELS:
            inferred.append(label)

    return inferred


def render_ticket(ticket: dict[str, str], column: str) -> list[str]:
    """TODO: add docstring for render_ticket."""
    col_color, icon, _ = COLUMN_COLORS.get(column, (WHITE, "·", column.upper()))
    ticket_id = ticket.get("id", "???")
    title = _display_title(ticket.get("title", "(no title)"))
    locked_by = ticket.get("locked_by", "null")
    blocked = ticket.get("blocked_by", "")
    labels = render_labels(ticket)

    lines = [
        f"  {_style(icon, BOLD, col_color)} {_style(truncate(ticket_id, COL_WIDTH - 4), BOLD)}",
        f"    {truncate(title, COL_WIDTH - 4)}",
    ]
    acceptance_criteria = ticket.get("acceptance_criteria", [])
    if isinstance(acceptance_criteria, list) and acceptance_criteria:
        first_ac = str(acceptance_criteria[0]).strip()
        if first_ac:
            remaining = len(acceptance_criteria) - 1
            suffix = f" (+{remaining})" if remaining > 0 else ""
            if suffix:
                prefix = "AC: "
                max_content = max(8, (COL_WIDTH - 4) - len(prefix) - len(suffix))
                compact_first = truncate(first_ac, max_content)
                ac_line = f"{prefix}{compact_first}{suffix}"
            else:
                ac_line = truncate(f"AC: {first_ac}", COL_WIDTH - 4)
            lines.append(f"    {ac_line}")
    if labels:
        for label_line in wrap_labels_for_column(labels, COL_WIDTH - 4):
            lines.append(f"    {label_line}")
    if locked_by and locked_by not in ("null", ""):
        lines.append(f"    {_style(f'→ {locked_by}', DIM)}")
    if blocked and blocked not in ("null", ""):
        lines.append(
            f"    {_style(f'⛔ needs: {truncate(blocked, COL_WIDTH - 12)}', RED)}"
        )
    lines.append("")
    return lines


def pad_line(line: str, width: int) -> str:
    """Pad a line to `width` visible characters (ignoring ANSI escape codes)."""
    visible = re.sub(r"\033\[[0-9;]*m", "", line)
    pad = width - len(visible)
    return line + " " * max(pad, 0)


def _visible_len(line: str) -> int:
    return len(re.sub(r"\033\[[0-9;]*m", "", line))


def wrap_labels_for_column(labels: list[str], width: int) -> list[str]:
    """TODO: add docstring for wrap_labels_for_column."""
    if not labels:
        return []

    wrapped: list[str] = []
    current = ""

    for label in labels:
        sep = " " if current else ""
        candidate = f"{current}{sep}{label}" if current else label

        if _visible_len(candidate) <= width:
            current = candidate
            continue

        if current:
            wrapped.append(current)
            current = label
        else:
            wrapped.append(label)
            current = ""

    if current:
        wrapped.append(current)

    return wrapped


def _chunk_columns(columns: list[str], size: int) -> list[list[str]]:
    return [columns[i : i + size] for i in range(0, len(columns), size)]


def _max_columns_per_row(total_columns: int) -> int:
    """Choose the maximum columns-per-row that still fits the current terminal."""
    terminal_width = shutil.get_terminal_size((120, 30)).columns
    max_supported = min(DEFAULT_COLUMNS_PER_ROW, max(1, total_columns))

    for candidate in range(max_supported, 0, -1):
        needed = COL_WIDTH * candidate + (candidate + 1)
        if needed <= terminal_width:
            return candidate

    return 1


def render_board(columns_data: dict[str, list[dict]], board: dict[str, str]) -> str:
    """TODO: add docstring for render_board."""
    columns = board["columns"]
    board_label = board["label"]
    board_name = board["name"]

    # Build per-column line lists
    col_lines: dict[str, list[str]] = {}
    for col in columns:
        col_color, _, label = COLUMN_COLORS.get(col, (WHITE, "·", col.upper()))
        tickets = columns_data.get(col, [])
        header = _style(f" {label} ({len(tickets)})", BOLD, col_color)
        lines: list[str] = [header, ""]
        for t in tickets:
            lines.extend(render_ticket(t, col))
        if not tickets:
            lines.append(f"  {_style('(empty)', DIM)}")
            lines.append("")
        col_lines[col] = lines

    result_lines: list[str] = []
    columns_per_row = _max_columns_per_row(len(columns))

    # Title bar
    total_width = COL_WIDTH * columns_per_row + (columns_per_row + 1)
    title = f"  BOARD: {board_label} [{board_name}]"
    left = _style("╔", BOLD, CYAN)
    mid_h = _style("═" * (total_width - 2), BOLD, CYAN)
    right = _style("╗", BOLD, CYAN)
    result_lines.append(left + mid_h + right)
    result_lines.append(
        _style("║", BOLD, CYAN)
        + _style(title.center(total_width - 2), BOLD, WHITE)
        + _style("║", BOLD, CYAN)
    )
    result_lines.append(
        _style("╠", BOLD, CYAN)
        + _style("═" * (total_width - 2), BOLD, CYAN)
        + _style("╣", BOLD, CYAN)
    )

    col_rows = _chunk_columns(columns, columns_per_row)

    for row_idx, row_columns in enumerate(col_rows):
        row_line_sets = [col_lines[col] for col in row_columns]
        row_height = max(len(lines) for lines in row_line_sets)

        for i in range(row_height):
            rendered_cells: list[str] = []
            for lines in row_line_sets:
                line = lines[i] if i < len(lines) else ""
                rendered_cells.append(pad_line(line, COL_WIDTH))

            result_lines.append(
                _style("║", BOLD, CYAN)
                + _style("│", BOLD, CYAN).join(rendered_cells)
                + _style("║", BOLD, CYAN)
            )

        if row_idx < len(col_rows) - 1:
            result_lines.append(
                _style("╠", BOLD, CYAN)
                + _style(("═" * COL_WIDTH + "╪") * (columns_per_row - 1), BOLD, CYAN)
                + _style("═" * COL_WIDTH, BOLD, CYAN)
                + _style("╣", BOLD, CYAN)
            )

    result_lines.append(
        _style("╚", BOLD, CYAN)
        + _style(("═" * COL_WIDTH + "╧") * (columns_per_row - 1), BOLD, CYAN)
        + _style("═" * COL_WIDTH, BOLD, CYAN)
        + _style("╝", BOLD, CYAN)
    )
    return "\n".join(result_lines)


def parse_args() -> argparse.Namespace:
    """TODO: add docstring for parse_args."""
    parser = argparse.ArgumentParser(description="Render configured board refs.")
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument("--board", dest="board")
    parser.add_argument("--all", dest="show_all", action="store_true")
    parser.add_argument("--list-boards", action="store_true")
    parser.add_argument("--issues", dest="show_issues", action="store_true",
                        help="Show full ticket details (AC, DoD, sprint) instead of board layout.")
    return parser.parse_args()


def render_issue(ticket: dict) -> str:
    """Render a full-detail ticket block for the --issues view."""
    col = ticket.get("_column", "backlog")
    col_color, icon, col_label = COLUMN_COLORS.get(col, (WHITE, "·", col.upper()))
    tid = ticket.get("id", "???")
    lines: list[str] = [
        _style(f"{icon} {tid}  [{col_label}]", BOLD, col_color),
        f"  Title:               {ticket.get('title', '(no title)')}",
        "  Description:",
    ]
    for desc_line in ticket.get("description", "No description provided.").splitlines():
        lines.append(f"    {desc_line}")
    ac = ticket.get("acceptance_criteria", [])
    lines.append("  Acceptance Criteria:")
    if ac and ac not in ([], "[]", None):
        items = ac if isinstance(ac, list) else [ac]
        for item in items:
            lines.append(f"    - {item}")
    else:
        lines.append("    (none)")
    dod = ticket.get("definition_of_done", [])
    lines.append("  Definition of Done:")
    if dod and dod not in ([], "[]", None):
        items = dod if isinstance(dod, list) else [dod]
        for item in items:
            lines.append(f"    - {item}")
    else:
        lines.append("    (none)")
    lines.append(f"  Sprint:              {ticket.get('sprint', 'null')}")
    lines.append(f"  Assigned:            {ticket.get('assigned', 'null')}")
    rendered_labels = render_labels(ticket)
    lines.append(f"  Labels:              {' '.join(rendered_labels) if rendered_labels else '(none)'}")
    lines.append("")
    return "\n".join(lines)


def render_single_board(repo_root: Path, board: dict[str, str]) -> tuple[bool, str]:
    """TODO: add docstring for render_single_board."""
    columns_data: dict[str, list[dict]] = {}
    has_tickets = False
    for col in board["columns"]:
        tickets = load_column(repo_root, board["ref_prefix"], col)
        columns_data[col] = tickets
        if tickets:
            has_tickets = True

    render_board_config = dict(board)
    if _compact_mode_enabled():
        visible_columns = [col for col in board["columns"] if columns_data.get(col)]
        if visible_columns:
            render_board_config["columns"] = visible_columns

    body = render_board(columns_data, render_board_config)
    total = sum(len(v) for v in columns_data.values())
    done_count = len(columns_data.get("done", []))
    summary = _style(
        f"Total: {total} tickets  ·  {done_count} done  ·  Source: {board['ref_prefix']}/*",
        DIM,
    )
    return has_tickets, body + "\n\n" + summary


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """TODO: add docstring for main."""
    args = parse_args()
    repo_root = Path(args.repo_root).resolve()
    config = load_board_config(repo_root)

    if args.list_boards:
        default_board = config["git_board"]["default_board"]
        for board in list_boards(config):
            marker = "*" if board["name"] == default_board else "-"
            print(f"{marker} {board['name']} ({board['ref_prefix']})")
        return

    configured_boards = list_boards(config)
    discovered_boards = discover_boards_from_refs(
        repo_root,
        config["git_board"]["ref_prefix"],
        configured_boards,
    )

    if args.show_all:
        boards = merge_configured_and_discovered_boards(
            configured_boards, discovered_boards
        )
    else:
        try:
            boards = [resolve_board(config, args.board)]
        except KeyError:
            discovered_map = {board["name"]: board for board in discovered_boards}
            if args.board and args.board in discovered_map:
                boards = [discovered_map[args.board]]
            else:
                available = sorted(
                    {
                        board["name"]
                        for board in merge_configured_and_discovered_boards(
                            configured_boards,
                            discovered_boards,
                        )
                    }
                )
                available_text = ", ".join(available) if available else "none"
                selected = args.board or config["git_board"].get("default_board", "")
                print(
                    _style(
                        f"Stage/board '{selected}' is not configured for this repository.",
                        YELLOW,
                        BOLD,
                    )
                )
                print(_style(f"Available boards: {available_text}", DIM))
                print(
                    _style(
                        "Hint: run 'make stages' to list supported stages and use '<stage>-board' only for available stage boards.",
                        DIM,
                    )
                )
                sys.exit(0)

    if args.show_issues:
        for board in boards:
            print(_style(f"  ISSUES: {board.get('label', board['name'])} [{board['name']}]", BOLD, CYAN))
            print()
            any_found = False
            for col in board["columns"]:
                tickets = load_column(repo_root, board["ref_prefix"], col)
                for ticket in tickets:
                    print(render_issue(ticket))
                    any_found = True
            if not any_found:
                print(_style("  (no tickets found)", DIM))
        return

    rendered_sections: list[str] = []
    has_any_tickets = False
    for board in boards:
        has_tickets, rendered = render_single_board(repo_root, board)
        if has_tickets:
            has_any_tickets = True
            rendered_sections.append(rendered)

    if not has_any_tickets:
        namespaces = ", ".join(board["ref_prefix"] for board in boards)
        board_names = ", ".join(board["name"] for board in boards)
        print(
            _style(
                f"No board tickets found in configured namespaces: {namespaces}",
                YELLOW,
                BOLD,
            )
        )
        print(_style(f"Boards: {board_names}", DIM))
        print(
            _style(
                "Use BOARD_NAME=<board> bash .github/skills/board/scripts/board-ticket.sh create <id> <title> to add tickets.",
                DIM,
            )
        )
        print(
            _style("Use board-ticket.sh fetch --all to pull tickets from remote.", DIM)
        )
        sys.exit(0)

    print("\n\n".join(rendered_sections))


if __name__ == "__main__":
    main()
