from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


def _run(command: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, check=True, capture_output=True, text=True)


def test_board_ticket_create_works_without_mapfile_support(tmp_path: Path) -> None:
    """TODO: add docstring for test_board_ticket_create_works_without_mapfile_support."""
    repo_root = tmp_path / "repo"
    script_root = repo_root / ".github" / "skills" / "board" / "scripts"
    script_root.mkdir(parents=True)

    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(source_root / "board-ticket.sh", script_root / "board-ticket.sh")
    shutil.copy2(source_root / "board_config.py", script_root / "board_config.py")

    board_yaml = repo_root / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: mvp",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    mvp:",
                "      ref_prefix: refs/board/mvp",
            ]
        ),
        encoding="utf-8",
    )

    _run(["git", "init"], repo_root)
    _run(["git", "config", "user.email", "test@example.com"], repo_root)
    _run(["git", "config", "user.name", "Test User"], repo_root)

    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "create",
            "TASK-001",
            "Portable board ticket",
        ],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    refs = _run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/board/mvp"], repo_root
    )

    assert "Created ticket TASK-001" in result.stdout
    assert "refs/board/mvp/backlog/TASK-001" in refs.stdout


def test_board_ticket_run_tool_uses_repo_relative_helper_path(tmp_path: Path) -> None:
    """Ensure run-tool receives a repo-relative helper path for container safety."""
    repo_root = tmp_path / "repo"
    script_root = repo_root / ".github" / "skills" / "board" / "scripts"
    shared_shell_root = repo_root / ".github" / "skills" / "shared" / "shell" / "scripts"
    script_root.mkdir(parents=True)
    shared_shell_root.mkdir(parents=True)

    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(source_root / "board-ticket.sh", script_root / "board-ticket.sh")
    shutil.copy2(source_root / "board_config.py", script_root / "board_config.py")

    board_yaml = repo_root / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: mvp",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    mvp:",
                "      ref_prefix: refs/board/mvp",
            ]
        ),
        encoding="utf-8",
    )

    run_tool = shared_shell_root / "run-tool.sh"
    run_tool.write_text(
        "#!/usr/bin/env bash\n"
        "set -euo pipefail\n"
        "tool=\"$1\"\n"
        "script_path=\"$2\"\n"
        "shift 2\n"
        "if [[ \"$tool\" != \"python3\" ]]; then\n"
        "  echo \"unexpected tool: $tool\" >&2\n"
        "  exit 1\n"
        "fi\n"
        "if [[ \"$script_path\" == /* ]]; then\n"
        "  echo \"expected relative helper path\" >&2\n"
        "  exit 2\n"
        "fi\n"
        "python3 \"$script_path\" \"$@\"\n",
        encoding="utf-8",
    )
    run_tool.chmod(0o755)

    _run(["git", "init"], repo_root)
    _run(["git", "config", "user.email", "test@example.com"], repo_root)
    _run(["git", "config", "user.name", "Test User"], repo_root)

    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "create",
            "TASK-RT-001",
            "Container-safe helper path",
        ],
        cwd=repo_root,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Created ticket TASK-RT-001" in result.stdout


def _setup_board_repo(tmp_path: Path) -> tuple[Path, Path]:
    """Create a temporary git repo with board scripts and board config."""
    repo_root = tmp_path / "repo"
    script_root = repo_root / ".github" / "skills" / "board" / "scripts"
    script_root.mkdir(parents=True)

    source_root = Path(__file__).resolve().parents[1]
    shutil.copy2(source_root / "board-ticket.sh", script_root / "board-ticket.sh")
    shutil.copy2(source_root / "board_config.py", script_root / "board_config.py")

    board_yaml = repo_root / ".digital-team" / "board.yaml"
    board_yaml.parent.mkdir(parents=True)
    board_yaml.write_text(
        "\n".join(
            [
                "primary_system: github",
                "git_board:",
                "  enabled: true",
                "  ref_prefix: refs/board",
                "  default_board: mvp",
                "  columns:",
                "    - backlog",
                "    - in-progress",
                "    - blocked",
                "    - done",
                "  boards:",
                "    mvp:",
                "      ref_prefix: refs/board/mvp",
            ]
        ),
        encoding="utf-8",
    )

    _run(["git", "init"], repo_root)
    _run(["git", "config", "user.email", "test@example.com"], repo_root)
    _run(["git", "config", "user.name", "Test User"], repo_root)
    return repo_root, script_root


def test_board_ticket_move_to_done_requires_human_approval(tmp_path: Path) -> None:
    """Move to done must fail when no approved review decision exists."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(
        ["bash", str(script_root / "board-ticket.sh"), "create", "TASK-002", "Gate test"],
        repo_root,
    )
    _run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-002",
            "backlog",
            "in-progress",
        ],
        repo_root,
    )

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"list\" ]]; then\n"
        "  echo \"101\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"view\" ]]; then\n"
        "  echo \"REVIEW_REQUIRED\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = {"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}

    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-002",
            "in-progress",
            "done",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "no human approval detected" in result.stderr.lower()


def test_board_ticket_move_to_done_accepts_approved_review(tmp_path: Path) -> None:
    """Move to done should pass when a merged PR has APPROVED review decision."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(
        ["bash", str(script_root / "board-ticket.sh"), "create", "TASK-003", "Gate pass"],
        repo_root,
    )
    _run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-003",
            "backlog",
            "in-progress",
        ],
        repo_root,
    )

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"list\" ]]; then\n"
        "  echo \"202\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"view\" && \"$*\" == *\"reviewDecision\"* ]]; then\n"
        "  echo \"APPROVED\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"view\" && \"$*\" == *\"body,comments\"* ]]; then\n"
        "  echo \"Review completed. Quality checks passed. Test coverage: 92%.\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = {"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}

    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-003",
            "in-progress",
            "done",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    refs = _run(
        ["git", "for-each-ref", "--format=%(refname)", "refs/board/mvp/done"],
        repo_root,
    )
    assert "refs/board/mvp/done/TASK-003" in refs.stdout


def test_sprint_list_shows_synthetic_open_sprint_for_in_progress_work(
    tmp_path: Path, monkeypatch
) -> None:
    """Sprint list should show a derived open sprint when no sprint refs exist."""
    monkeypatch.setenv("BOARD_SYNC_GITHUB_STATUS", "0")
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(
        ["bash", str(script_root / "board-ticket.sh"), "create", "TASK-010", "Synthetic sprint title"],
        repo_root,
    )
    _run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-010",
            "backlog",
            "in-progress",
        ],
        repo_root,
    )

    result = subprocess.run(
        ["bash", str(script_root / "board-ticket.sh"), "sprint-list"],
        cwd=repo_root,
        check=True,
        capture_output=True,
        text=True,
    )

    assert "auto-mvp-current" in result.stdout
    assert "Synthetic sprint title" in result.stdout


def test_board_ticket_move_to_done_requires_visible_review_evidence(tmp_path: Path) -> None:
    """Move to done must fail when APPROVED review exists but no evidence text is present."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(
        ["bash", str(script_root / "board-ticket.sh"), "create", "TASK-006", "Evidence gate"],
        repo_root,
    )
    _run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-006",
            "backlog",
            "in-progress",
        ],
        repo_root,
    )

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_gh = fake_bin / "gh"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"list\" ]]; then\n"
        "  echo \"303\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"view\" && \"$*\" == *\"reviewDecision\"* ]]; then\n"
        "  echo \"APPROVED\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"pr\" && \"$2\" == \"view\" && \"$*\" == *\"body,comments\"* ]]; then\n"
        "  echo \"Merged successfully.\"\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = {"PATH": f"{fake_bin}:{os.environ.get('PATH', '')}"}

    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-006",
            "in-progress",
            "done",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "review evidence is missing" in result.stderr.lower()


def test_board_ticket_move_backlog_to_done_is_blocked(tmp_path: Path) -> None:
    """Backlog to done must be rejected to enforce lifecycle order."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(
        ["bash", str(script_root / "board-ticket.sh"), "create", "TASK-005", "Order gate"],
        repo_root,
    )

    env = {**os.environ, "BOARD_SKIP_PR_GATE": "1"}
    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "move",
            "TASK-005",
            "backlog",
            "done",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert "move ticket to in-progress first" in result.stderr.lower()


def test_board_ticket_create_persists_ac_and_dod_from_env(tmp_path: Path) -> None:
    """Create should persist acceptance criteria and DoD entries from env vars."""
    repo_root, script_root = _setup_board_repo(tmp_path)

    env = {
        **os.environ,
        "BOARD_ACCEPTANCE_CRITERIA": "criterion one\ncriterion two",
        "BOARD_DEFINITION_OF_DONE": "merged PR\nhuman approved",
    }
    subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "create",
            "TASK-004",
            "Rich ticket",
            "Line one\nLine two",
        ],
        cwd=repo_root,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )

    blob = _run(["git", "cat-file", "-p", "refs/board/mvp/backlog/TASK-004"], repo_root)
    content = blob.stdout

    assert "description: |" in content
    assert "  Line one" in content
    assert "  Line two" in content
    assert "acceptance_criteria:" in content
    assert "criterion one" in content
    assert "criterion two" in content
    assert "definition_of_done:" in content
    assert "merged PR" in content
    assert "human approved" in content


def test_sprint_create_syncs_github_milestone(tmp_path: Path) -> None:
    """Sprint creation should create a matching GitHub milestone when enabled."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], repo_root)

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_gh = fake_bin / "gh"
    gh_log = repo_root / "gh.log"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "echo \"$*\" >> \"$GH_LOG\"\n"
        "if [[ \"$1\" == \"api\" && \"$2\" == \"repos/org/repo/milestones?state=all&per_page=100\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"api\" && \"$2\" == \"-X\" && \"$3\" == \"POST\" && \"$4\" == \"repos/org/repo/milestones\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
        "GH_LOG": str(gh_log),
    }
    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "sprint-create",
            "PRO-SPRINT-10",
            "Goal text",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    log = gh_log.read_text(encoding="utf-8")
    assert "repos/org/repo/milestones?state=all&per_page=100" in log
    assert "-X POST repos/org/repo/milestones" in log


def test_sprint_close_syncs_github_milestone(tmp_path: Path) -> None:
    """Sprint close should close the matching GitHub milestone when present."""
    repo_root, script_root = _setup_board_repo(tmp_path)
    _run(["git", "remote", "add", "origin", "https://github.com/org/repo.git"], repo_root)
    subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "sprint-create",
            "PRO-SPRINT-11",
            "Goal text",
        ],
        cwd=repo_root,
        env={**os.environ, "BOARD_SYNC_MILESTONES": "0"},
        check=True,
        capture_output=True,
        text=True,
    )

    fake_bin = repo_root / "fake-bin"
    fake_bin.mkdir(parents=True)
    fake_gh = fake_bin / "gh"
    gh_log = repo_root / "gh.log"
    fake_gh.write_text(
        "#!/usr/bin/env bash\n"
        "echo \"$*\" >> \"$GH_LOG\"\n"
        "if [[ \"$1\" == \"api\" && \"$2\" == \"repos/org/repo/milestones?state=all&per_page=100\" ]]; then\n"
        "  echo -e \"7\\tPRO-SPRINT-11\"\n"
        "  exit 0\n"
        "fi\n"
        "if [[ \"$1\" == \"api\" && \"$2\" == \"-X\" && \"$3\" == \"PATCH\" && \"$4\" == \"repos/org/repo/milestones/7\" ]]; then\n"
        "  exit 0\n"
        "fi\n"
        "exit 1\n",
        encoding="utf-8",
    )
    fake_gh.chmod(0o755)

    env = {
        **os.environ,
        "PATH": f"{fake_bin}:{os.environ.get('PATH', '')}",
        "GH_LOG": str(gh_log),
    }
    result = subprocess.run(
        [
            "bash",
            str(script_root / "board-ticket.sh"),
            "sprint-close",
            "PRO-SPRINT-11",
        ],
        cwd=repo_root,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    log = gh_log.read_text(encoding="utf-8")
    assert "repos/org/repo/milestones?state=all&per_page=100" in log
    assert "-X PATCH repos/org/repo/milestones/7" in log
