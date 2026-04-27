from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from board_test_helpers import load_module_from_path


def _load_module():
    script_dir = Path(__file__).resolve().parents[1]
    if str(script_dir) not in sys.path:
        sys.path.insert(0, str(script_dir))
    script_path = script_dir / "board-show.py"
    return load_module_from_path(script_path, "board_show")


def test_parse_ticket_reads_block_style_labels() -> None:
    """TODO: add docstring for test_parse_ticket_reads_block_style_labels."""
    module = _load_module()

    blob = "\n".join(
        [
            "id: TASK-42",
            "title: Important ticket",
            "labels:",
            "  - epic",
            "  - priority/high",
        ]
    )

    ticket = module.parse_ticket(blob)

    assert ticket["id"] == "TASK-42"
    assert ticket["title"] == "Important ticket"
    assert ticket["_labels"] == ["epic", "priority/high"]


def test_parse_ticket_reads_inline_labels() -> None:
    """TODO: add docstring for test_parse_ticket_reads_inline_labels."""
    module = _load_module()

    blob = "\n".join(
        [
            "id: TASK-77",
            "title: Another ticket",
            'labels: [task, docs, "priority/low"]',
        ]
    )

    ticket = module.parse_ticket(blob)

    assert ticket["_labels"] == ["task", "docs", "priority/low"]


def test_parse_ticket_reads_multiline_description_and_checklists() -> None:
    """Parser should keep block descriptions and list-style AC/DoD fields."""
    module = _load_module()

    blob = "\n".join(
        [
            "id: PRO-THM-01-TASK",
            'title: "[project] Task THM-01"',
            "description: |",
            "  First line",
            "  Second line",
            "acceptance_criteria:",
            '  - "Criterion A"',
            '  - "Criterion B"',
            "definition_of_done:",
            "  - PR merged",
            "  - Tests pass",
        ]
    )

    ticket = module.parse_ticket(blob)

    assert ticket["description"] == "First line\nSecond line"
    assert ticket["acceptance_criteria"] == ["Criterion A", "Criterion B"]
    assert ticket["definition_of_done"] == ["PR merged", "Tests pass"]


def test_render_ticket_includes_colored_label_badges(monkeypatch) -> None:
    """TODO: add docstring for test_render_ticket_includes_colored_label_badges."""
    module = _load_module()
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "TASK-99",
        "title": "Label rendering",
        "_labels": ["bug", "priority/high"],
    }

    lines = module.render_ticket(ticket, "backlog")
    joined = "\n".join(lines)

    assert "[bug]" in joined
    assert "[priority/high]" in joined
    assert "\033[" in joined


def test_render_ticket_disables_ansi_with_no_color(monkeypatch) -> None:
    """TODO: add docstring for test_render_ticket_disables_ansi_with_no_color."""
    module = _load_module()
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "TASK-100",
        "title": "No color output",
        "_labels": ["docs"],
    }

    lines = module.render_ticket(ticket, "done")
    joined = "\n".join(lines)

    assert "[docs]" in joined
    assert "\033[" not in joined


def test_render_ticket_strips_stage_prefix_from_title(monkeypatch) -> None:
    """Rendered task titles should not repeat the board stage marker."""
    module = _load_module()
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "PRO-THM-01-TASK",
        "title": "[project] Task THM-01",
    }

    lines = module.render_ticket(ticket, "backlog")
    joined = "\n".join(lines)

    assert "Task THM-01" in joined
    assert "[project] Task THM-01" not in joined


def test_render_ticket_includes_acceptance_criteria_summary(monkeypatch) -> None:
    """Board rendering should show at least one acceptance-criteria summary line."""
    module = _load_module()
    monkeypatch.setenv("NO_COLOR", "1")
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "PRO-THM-01-TASK",
        "title": "[project] Task THM-01",
        "acceptance_criteria": [
            "Implement the approved scope boundary",
            "Keep behavior aligned with stage specification",
        ],
    }

    lines = module.render_ticket(ticket, "backlog")
    joined = "\n".join(lines)

    assert "AC:" in joined
    assert "(+1)" in joined


def test_discover_boards_from_refs_includes_legacy_default_board(
    tmp_path: Path,
) -> None:
    """TODO: add docstring for test_discover_boards_from_refs_includes_legacy_default_board."""
    module = _load_module()

    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    ticket_blob = "id: T1\ntitle: Legacy ticket\n"
    blob_sha = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=tmp_path,
        input=ticket_blob,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/board/backlog/T1", blob_sha],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    configured = [
        {
            "name": "mvp",
            "label": "MVP",
            "ref_prefix": "refs/board/mvp",
            "columns": ["backlog", "in-progress", "blocked", "done"],
        }
    ]

    discovered = module.discover_boards_from_refs(tmp_path, "refs/board", configured)
    names = {board["name"] for board in discovered}

    assert "default" in names


def test_merge_configured_and_discovered_keeps_order_and_adds_new_board() -> None:
    """TODO: add docstring for test_merge_configured_and_discovered_keeps_order_and_adds_new_board."""
    module = _load_module()

    configured = [
        {
            "name": "project",
            "label": "PROJECT",
            "ref_prefix": "refs/board/project",
            "columns": ["backlog", "done"],
        }
    ]
    discovered = [
        {
            "name": "default",
            "label": "DEFAULT",
            "ref_prefix": "refs/board",
            "columns": ["backlog", "done"],
        },
        {
            "name": "project",
            "label": "PROJECT",
            "ref_prefix": "refs/board/project",
            "columns": ["blocked"],
        },
    ]

    merged = module.merge_configured_and_discovered_boards(configured, discovered)

    assert merged[0]["name"] == "project"
    assert "blocked" in merged[0]["columns"]
    assert merged[1]["name"] == "default"


def test_discover_boards_ignores_sprint_refs_as_columns(tmp_path: Path) -> None:
    """Sprint refs must not be rendered as Kanban columns in board view."""
    module = _load_module()

    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    ticket_blob = "id: T1\ntitle: Ticket\n"
    blob_sha = subprocess.run(
        ["git", "hash-object", "-w", "--stdin"],
        cwd=tmp_path,
        input=ticket_blob,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    subprocess.run(
        ["git", "update-ref", "refs/board/project/backlog/T1", blob_sha],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "update-ref", "refs/board/project/sprints/SPRINT-01", blob_sha],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    configured = [
        {
            "name": "project",
            "label": "PROJECT",
            "ref_prefix": "refs/board/project",
            "columns": ["backlog", "in-progress", "blocked", "done"],
        }
    ]

    discovered = module.discover_boards_from_refs(tmp_path, "refs/board", configured)
    project_board = next(board for board in discovered if board["name"] == "project")

    assert "sprints" not in project_board["columns"]


def test_render_labels_infers_type_and_project_from_ticket_fields(monkeypatch) -> None:
    """TODO: add docstring for test_render_labels_infers_type_and_project_from_ticket_fields."""
    module = _load_module()
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "PRO-00000-EPIC",
        "title": "[project] Example Epic",
    }

    rendered = module.render_labels(ticket)
    joined = " ".join(rendered)

    assert "[epic]" in joined
    assert "[project]" not in joined


def test_render_labels_infers_parent_hierarchy_for_task_tickets(monkeypatch) -> None:
    """Task tickets should show parent story/epic context instead of repeating the stage tag."""
    module = _load_module()
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setattr(module.sys.stdout, "isatty", lambda: True)

    ticket = {
        "id": "PRO-THM-01-TASK",
        "title": "[project] Task THM-01",
    }

    rendered = module.render_labels(ticket)
    joined = " ".join(rendered)

    assert "[task]" in joined
    assert "[story:STORY-THM-01]" in joined
    assert "[epic:EPIC-THM-01]" in joined
    assert "[project]" not in joined


def test_render_single_board_hides_empty_columns_in_compact_mode(
    monkeypatch, tmp_path: Path
) -> None:
    """Compact mode should hide empty columns and keep only populated ones."""
    module = _load_module()
    monkeypatch.delenv("BOARD_FULL", raising=False)
    monkeypatch.setenv("BOARD_COMPACT_MODE", "1")

    monkeypatch.setattr(
        module,
        "load_column",
        lambda _repo_root, _ref_prefix, column: (
            [{"id": "TASK-1", "title": "Only backlog", "_labels": ["task"]}]
            if column == "backlog"
            else []
        ),
    )

    board = {
        "name": "project",
        "label": "PROJECT",
        "ref_prefix": "refs/board/project",
        "columns": ["backlog", "in-progress", "blocked", "done"],
    }

    has_tickets, rendered = module.render_single_board(tmp_path, board)

    assert has_tickets is True
    assert "BACKLOG (1)" in rendered
    assert "IN PROGRESS (0)" not in rendered
    assert "BLOCKED (0)" not in rendered
    assert "DONE (0)" not in rendered


def test_unknown_board_prints_hint_and_exits_cleanly(tmp_path: Path) -> None:
    """Unknown stage/board names should produce a hint instead of a traceback."""
    script_dir = Path(__file__).resolve().parents[1]
    board_show = script_dir / "board-show.py"

    subprocess.run(
        ["git", "init"], cwd=tmp_path, check=True, capture_output=True, text=True
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=tmp_path,
        check=True,
        capture_output=True,
        text=True,
    )

    board_yaml = tmp_path / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True, exist_ok=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: project",
                "  boards:",
                "    project:",
                "      ref_prefix: refs/board/project",
                "      columns:",
                "        - backlog",
                "        - in-progress",
                "        - blocked",
                "        - done",
            ]
        ),
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(board_show), str(tmp_path), "--board", "pilot"],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    combined = (result.stdout or "") + (result.stderr or "")
    assert result.returncode == 0
    assert "Stage/board 'pilot' is not configured" in combined
    assert "Available boards: project" in combined
    assert "Traceback" not in combined
