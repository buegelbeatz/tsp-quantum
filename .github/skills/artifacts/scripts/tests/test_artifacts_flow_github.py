"""Unit tests for GitHub project sync token resolution."""

from __future__ import annotations

import json
import subprocess
import sys
from importlib import import_module
from pathlib import Path


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github" / "skills" / "artifacts").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SCRIPT_DIR = ROOT / ".github" / "skills" / "artifacts" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

artifacts_flow_github = import_module("artifacts_flow_github")


def test_run_gh_command_times_out(monkeypatch) -> None:
    """_run_gh_command should fail fast when gh hangs."""

    def _fake_run(*_args, **_kwargs):
        raise subprocess.TimeoutExpired(cmd=["gh", "project", "list"], timeout=30)

    monkeypatch.setattr(subprocess, "run", _fake_run)

    run_gh_command = getattr(artifacts_flow_github, "_run_gh_command")
    ok, output = run_gh_command(
        ["gh", "project", "list"],
        {"GH_TOKEN": "dummy", "GITHUB_TOKEN": "dummy"},
    )

    assert ok is False
    assert "timed out" in output
    assert "classification=timeout" in output


def test_run_gh_command_prefers_local_gh_binary_when_available(monkeypatch) -> None:
    """_run_gh_command should use the local gh binary before the wrapper/container path."""

    captured: dict[str, object] = {}

    def _fake_run(command, **kwargs):
        captured["command"] = command
        captured["env"] = kwargs.get("env", {})
        return subprocess.CompletedProcess(command, 0, stdout="ok", stderr="")

    monkeypatch.setattr(artifacts_flow_github.shutil, "which", lambda tool: "/usr/local/bin/gh" if tool == "gh" else None)
    monkeypatch.setattr(subprocess, "run", _fake_run)

    run_gh_command = getattr(artifacts_flow_github, "_run_gh_command")

    ok, output = run_gh_command(
        ["gh", "project", "list"],
        {"GH_TOKEN": "dummy", "GITHUB_TOKEN": "dummy", "RUN_TOOL_PREFER_CONTAINER": "1"},
    )

    assert ok is True
    assert output == "ok"
    assert captured["command"] == ["gh", "project", "list"]
    assert captured["env"]["GH_TOKEN"] == "dummy"


def test_github_project_sync_uses_gh_token_fallback(monkeypatch) -> None:
    """GH_TOKEN should be accepted when GITHUB_TOKEN is absent."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_example")
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _root: ("owner/repo", "owner", "repo"),
    )

    def _fake_run(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
        assert env.get("GITHUB_TOKEN") == "ghp_example"
        if args[:3] == ["gh", "project", "list"]:
            return True, "[]"
        if args[:3] == ["gh", "project", "create"]:
            return True, '{"title":"Project"}'
        if args[:3] == ["gh", "project", "edit"]:
            return True, "edited"
        return False, "unexpected command"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    status, message = artifacts_flow_github.github_project_sync("project")

    assert status == "created"
    assert "auth=GH_TOKEN" in message


def test_ensure_github_project_reports_token_remediation_guidance(monkeypatch) -> None:
    """Missing token guidance should include explicit env remediation and local fallback."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.setattr(artifacts_flow_github, "_resolve_github_token", lambda: (None, None))
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _root: ("owner/repo", "owner", "repo"),
    )

    result = artifacts_flow_github.ensure_github_project(ROOT, "project")

    assert result["status"] == "manual-required"
    message = str(result["message"])
    assert "GITHUB_TOKEN (preferred) or GH_TOKEN" in message
    assert "Fallback remains default-safe via refs/board/* local board sync" in message


def test_github_project_sync_uses_dotenv_gh_token_fallback(monkeypatch) -> None:
    """If env vars are missing, _resolve_github_token should read from a .env file."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.delenv("GH_TOKEN", raising=False)

    # Stub token resolution to simulate reading the token from a .env file on disk.
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_from_env_file", "GH_TOKEN"),
    )
    # Stub repo context so no git subprocess is invoked.
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _root: ("acme/demo", "acme", "demo"),
    )

    def _fake_run(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
        assert env.get("GITHUB_TOKEN") == "ghp_from_env_file"
        if args[:3] == ["gh", "project", "list"]:
            return True, "[]"
        if args[:3] == ["gh", "project", "create"]:
            return (
                True,
                '{"title":"Project","number":1,"url":"https://github.com/orgs/acme/projects/1"}',
            )
        if args[:3] == ["gh", "project", "edit"]:
            return True, "edited"
        if args[:3] == ["gh", "project", "view"]:
            return True, '{"url":"https://github.com/orgs/acme/projects/1"}'
        if args[:3] == ["gh", "project", "link"]:
            return True, "linked"
        return False, "unexpected command"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    status, message = artifacts_flow_github.github_project_sync("project")

    assert status == "created"
    assert "auth=GH_TOKEN" in message


def test_github_project_sync_handles_dict_list_response(monkeypatch) -> None:
    """github_project_sync should not crash when gh list returns dict payload."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_example")
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _root: ("owner/repo", "owner", "repo"),
    )

    def _fake_run(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
        assert env.get("GITHUB_TOKEN") == "ghp_example"
        if args[:3] == ["gh", "project", "list"]:
            return True, '{"projects": [{"title": "Project"}]}'
        if args[:3] == ["gh", "project", "edit"]:
            return True, "edited"
        return False, "unexpected command"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    status, message = artifacts_flow_github.github_project_sync("project")

    assert status == "found"
    assert "auth=GH_TOKEN" in message


def test_github_project_sync_reuses_legacy_project_title(monkeypatch) -> None:
    """Legacy stage project titles should be reused instead of creating duplicates."""
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setenv("GH_TOKEN", "ghp_example")
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _root: ("owner/repo", "owner", "repo"),
    )

    calls: list[list[str]] = []

    def _fake_run(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
        assert env.get("GITHUB_TOKEN") == "ghp_example"
        calls.append(args)
        if args[:3] == ["gh", "project", "list"]:
            return (
                True,
                '{"projects": [{"title": "Project Delivery Board", "number": 7, "url": "https://github.com/orgs/owner/projects/7"}]}'
            )
        if args[:3] == ["gh", "project", "view"]:
            return True, '{"url":"https://github.com/orgs/owner/projects/7"}'
        if args[:3] == ["gh", "project", "edit"]:
            return True, "edited"
        if args[:3] == ["gh", "project", "link"]:
            return True, "linked"
        if args[:3] == ["gh", "project", "close"]:
            return True, "closed"
        if args[:3] == ["gh", "project", "create"]:
            return False, "must not create duplicate"
        return False, f"unexpected command: {args}"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    status, _message = artifacts_flow_github.github_project_sync("project")

    assert status == "found"
    assert not any(call[:3] == ["gh", "project", "create"] for call in calls)


def test_ensure_stage_primary_assets_updates_stage_metadata(
    monkeypatch, tmp_path: Path
) -> None:
    """Stage primary asset sync should persist board and wiki URLs into stage frontmatter."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text(
        "\n".join(
            [
                "---",
                'stage: "project"',
                'board_id: ""',
                'board_url: ""',
                'wiki_url: ""',
                "---",
                "",
                "# Project",
                "",
                "## Vision",
                "Ship the project stage.",
                "",
                "## Goals",
                "- Goal one",
                "",
                "## Constraints",
                "- Constraint one",
                "",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        artifacts_flow_github,
        "ensure_github_project",
        lambda repo_root, stage: {
            "status": "found",
            "message": "ok",
            "owner": "acme",
            "repo_slug": "acme/demo",
            "number": "7",
            "url": "https://github.com/orgs/acme/projects/7",
            "title": "Project",
            "auth_source": "GH_TOKEN",
        },
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "ensure_stage_wiki",
        lambda repo_root, stage, stage_path_arg, board_url: {
            "status": "updated",
            "message": "wiki updated",
            "url": "https://github.com/acme/demo/wiki/Project",
            "auth_source": "GH_TOKEN",
        },
    )

    result = artifacts_flow_github.ensure_stage_primary_assets(
        tmp_path, "project", stage_path
    )

    stage_text = stage_path.read_text(encoding="utf-8")
    assert result["project"]["url"] == "https://github.com/orgs/acme/projects/7"
    assert result["wiki"]["url"] == "https://github.com/acme/demo/wiki/Project"
    assert 'board_id: "7"' in stage_text
    assert 'board_url: "https://github.com/orgs/acme/projects/7"' in stage_text
    assert 'wiki_url: "https://github.com/acme/demo/wiki/Project"' in stage_text


def test_cleanup_stage_primary_assets_removes_project_issues_and_wiki(
    monkeypatch, tmp_path: Path
) -> None:
    """DRY_RUN=2 cleanup should remove stage-scoped GitHub assets before regeneration."""
    wiki_cache = (
        tmp_path
        / ".digital-runtime"
        / "github"
        / "wiki-cache"
        / "acme_demo"
    )
    wiki_cache.mkdir(parents=True, exist_ok=True)
    (wiki_cache / ".git").mkdir()
    (wiki_cache / "Home.md").write_text("old wiki", encoding="utf-8")

    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_example", "GH_TOKEN"),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _repo_root: ("acme/demo", "acme", "demo"),
    )

    commands: list[list[str]] = []

    def _fake_run(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
        commands.append(args)
        assert env.get("GITHUB_TOKEN") == "ghp_example"
        if args[:3] == ["gh", "issue", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "issues": [
                            {
                                "number": 11,
                                "title": "Project | PRO-THM-01-EPIC: Legacy",
                                "url": "https://github.com/acme/demo/issues/11",
                                "body": "<!-- artifact-sync: stage=project; bundle=2026-04-15/THM-01; kind=epic; board_ticket=PRO-THM-01-EPIC -->",
                            }
                        ]
                    }
                ),
            )
        if args[:3] == ["gh", "project", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "projects": [
                            {
                                "id": "PVT_kwDOA",
                                "number": 7,
                                "title": "Project",
                            }
                        ]
                    }
                ),
            )
        if args[:3] == ["gh", "api", "graphql"]:
            return True, '{"data":{"deleteProjectV2":{"clientMutationId":null}}}'
        if args[:5] == ["gh", "api", "-X", "DELETE", "repos/acme/demo/issues/11"]:
            return True, ""
        if args[:5] == ["gh", "api", "-X", "PATCH", "repos/acme/demo"]:
            return True, '{"has_wiki":false}'
        return False, f"unexpected command: {args}"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.cleanup_stage_primary_assets(tmp_path, "project")

    assert result["status"] == "cleaned"
    assert result["project"] == "deleted"
    assert result["wiki"] == "deleted"
    assert result["issues"]["Project | PRO-THM-01-EPIC: Legacy"] == "deleted"
    assert not wiki_cache.exists()


def test_sync_ux_review_assets_copies_latest_stage_artifacts(tmp_path: Path) -> None:
    """UX review markdown artifacts should be mirrored into docs/wiki/ux-reviews."""
    old_scope = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-22"
        / "project"
        / "UX_SCOPE_THM-03.md"
    )
    new_scope = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-23"
        / "project"
        / "UX_SCOPE_THM-03.md"
    )
    user_review = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-23"
        / "project"
        / "USER_STANDARD_REVIEW_REQUEST_THM-03.md"
    )
    old_scope.parent.mkdir(parents=True, exist_ok=True)
    new_scope.parent.mkdir(parents=True, exist_ok=True)
    old_scope.write_text("old", encoding="utf-8")
    new_scope.write_text("new", encoding="utf-8")
    user_review.write_text("request", encoding="utf-8")

    local_wiki_dir = tmp_path / "docs" / "wiki"
    local_wiki_dir.mkdir(parents=True, exist_ok=True)

    sync_ux_reviews = getattr(artifacts_flow_github, "_sync_ux_review_assets")
    entries, assets, changed = sync_ux_reviews(
        tmp_path,
        local_wiki_dir,
        "project",
    )

    assert changed is True
    assert "ux-reviews/UX_SCOPE_THM-03.md" in assets
    assert "ux-reviews/USER_STANDARD_REVIEW_REQUEST_THM-03.md" in assets
    assert (local_wiki_dir / "ux-reviews" / "UX_SCOPE_THM-03.md").read_text(encoding="utf-8") == "new"
    assert len(entries) == 2


def test_sync_ux_scribble_assets_copies_svg_files(tmp_path: Path) -> None:
    """UX scribble SVG files should be mirrored into docs/wiki/ux-scribbles."""
    source_dir = tmp_path / "docs" / "ux" / "scribbles"
    source_dir.mkdir(parents=True, exist_ok=True)
    scribble_file = source_dir / "team-operating-model-thm03-scribble-r1.svg"
    scribble_file.write_text("<svg><!-- scribble --></svg>", encoding="utf-8")

    local_wiki_dir = tmp_path / "docs" / "wiki"
    local_wiki_dir.mkdir(parents=True, exist_ok=True)

    sync_ux_scribbles = getattr(artifacts_flow_github, "_sync_ux_scribble_assets")
    entries, assets, changed = sync_ux_scribbles(tmp_path, local_wiki_dir)

    assert changed is True
    assert "ux-scribbles/team-operating-model-thm03-scribble-r1.svg" in assets
    assert (
        local_wiki_dir / "ux-scribbles" / "team-operating-model-thm03-scribble-r1.svg"
    ).read_text(encoding="utf-8") == "<svg><!-- scribble --></svg>"
    assert len(entries) == 1


def test_sync_ux_review_assets_includes_lowercase_user_review_files(tmp_path: Path) -> None:
    """Lowercase user-review files should be mirrored into docs/wiki/ux-reviews."""
    user_review = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-24"
        / "project"
        / "user-review-20260424-chat-flow-r1.md"
    )
    user_review.parent.mkdir(parents=True, exist_ok=True)
    user_review.write_text("review", encoding="utf-8")

    local_wiki_dir = tmp_path / "docs" / "wiki"
    local_wiki_dir.mkdir(parents=True, exist_ok=True)

    sync_ux_reviews = getattr(artifacts_flow_github, "_sync_ux_review_assets")
    entries, assets, changed = sync_ux_reviews(tmp_path, local_wiki_dir, "project")

    assert changed is True
    assert "ux-reviews/user-review-20260424-chat-flow-r1.md" in assets
    assert any(title == "User Review 20260424 Chat Flow R1" for title, _, _ in entries)


def test_sync_ux_review_loop_pages_generates_wiki_loop_summary(tmp_path: Path) -> None:
    """Second-round revise outcomes should stop the loop and emit a report."""
    user_review = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-24"
        / "project"
        / "user-review-20260424-chat-flow-r2.md"
    )
    user_review.parent.mkdir(parents=True, exist_ok=True)
    user_review.write_text(
        "\n".join(
            [
                "---",
                "schema: user_review_v1",
                'design_artifact: "docs/ux/scribbles/chat-flow-r2.svg"',
                "iteration: 2",
                'task_performed: "Complete onboarding"',
                "composite_score: 3.2",
                'recommendation: "revise"',
                "---",
                "",
                "# User Review",
                "",
                "## Interview Questionnaire",
                "",
                "| Question | Answer |",
                "|---|---|",
                "| What is the first thing you would tap and why? | Start button |",
            ]
        ),
        encoding="utf-8",
    )

    local_wiki_dir = tmp_path / "docs" / "wiki"
    (local_wiki_dir / "ux-scribbles").mkdir(parents=True, exist_ok=True)
    (local_wiki_dir / "ux-scribbles" / "chat-flow-r2.svg").write_text("<svg/>", encoding="utf-8")

    sync_loops = getattr(artifacts_flow_github, "_sync_ux_review_loop_pages")
    entries, assets, changed = sync_loops(tmp_path, local_wiki_dir, "project")

    assert changed is True
    assert "ux-review-loops/chat-flow-loop.md" in assets
    loop_page = local_wiki_dir / "ux-review-loops" / "chat-flow-loop.md"
    assert loop_page.exists()
    content = loop_page.read_text(encoding="utf-8")
    assert "Recommendation: revise" in content
    assert "Loop status: aborted after iteration limit." in content
    assert "Suggested task status: done" in content
    assert "Reporting reason:" in content
    assert "Suggested intake bug artifact" in content
    assert "## Questionnaire Q/A" in content
    assert "## Validation Scope" in content
    followup_bug = (
        tmp_path
        / ".digital-artifacts"
        / "00-input"
        / "bugs"
        / "ux-chat-flow-bug-followup.md"
    )
    followup_feature = (
        tmp_path
        / ".digital-artifacts"
        / "00-input"
        / "features"
        / "ux-chat-flow-feat-followup.md"
    )
    assert followup_bug.exists()
    assert followup_feature.exists()
    assert any(title == "Chat Flow" for title, _, _ in entries)


def test_sync_ux_review_loop_pages_blocks_after_second_round_with_blockers(tmp_path: Path) -> None:
    """Second-round redesign or blocking outcomes should recommend blocked."""
    user_review = (
        tmp_path
        / ".digital-artifacts"
        / "60-review"
        / "2026-04-24"
        / "project"
        / "user-review-20260424-voice-flow-r2.md"
    )
    user_review.parent.mkdir(parents=True, exist_ok=True)
    user_review.write_text(
        "\n".join(
            [
                "---",
                "schema: user_review_v1",
                'design_artifact: "docs/ux/scribbles/voice-flow-r2.svg"',
                "iteration: 2",
                'task_performed: "Start voice setup"',
                "composite_score: 1.8",
                'blocking_issues: ["The prompt does not explain when the microphone is active"]',
                'recommendation: "redesign"',
                "---",
                "",
                "# User Review",
                "",
                "## Interview Questionnaire",
                "",
                "| Question | Answer |",
                "|---|---|",
                "| What confused you most? | I do not know when the assistant is listening. |",
            ]
        ),
        encoding="utf-8",
    )

    local_wiki_dir = tmp_path / "docs" / "wiki"
    (local_wiki_dir / "ux-scribbles").mkdir(parents=True, exist_ok=True)
    (local_wiki_dir / "ux-scribbles" / "voice-flow-r2.svg").write_text("<svg/>", encoding="utf-8")

    sync_loops = getattr(artifacts_flow_github, "_sync_ux_review_loop_pages")
    _entries, assets, changed = sync_loops(tmp_path, local_wiki_dir, "project")

    assert changed is True
    assert "ux-review-loops/voice-flow-loop.md" in assets
    content = (local_wiki_dir / "ux-review-loops" / "voice-flow-loop.md").read_text(encoding="utf-8")
    assert "Loop status: aborted after iteration limit." in content
    assert "Suggested task status: blocked" in content
    assert "Further iteration needs clearer product or medium-specific guidance." in content


def test_cleanup_stage_primary_assets_closes_when_delete_is_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    """Issue/project cleanup should fall back to close operations when hard delete is unavailable."""
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_example", "GH_TOKEN"),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _repo_root: ("acme/demo", "acme", "demo"),
    )

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        if args[:3] == ["gh", "issue", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "issues": [
                            {
                                "number": 12,
                                "title": "Project | PRO-THM-01-TASK: Legacy",
                                "url": "https://github.com/acme/demo/issues/12",
                                "body": "<!-- artifact-sync: stage=project; bundle=2026-04-15/THM-01; kind=task; board_ticket=PRO-THM-01-TASK -->",
                            }
                        ]
                    }
                ),
            )
        if args[:3] == ["gh", "project", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "projects": [
                            {
                                "number": 8,
                                "title": "Project",
                            }
                        ]
                    }
                ),
            )
        if args[:5] == ["gh", "api", "-X", "DELETE", "repos/acme/demo/issues/12"]:
            return False, "delete unsupported"
        if args[:4] == ["gh", "issue", "close", "12"]:
            return True, "closed"
        if args[:4] == ["gh", "project", "close", "8"]:
            return True, "closed"
        if args[:5] == ["gh", "api", "-X", "PATCH", "repos/acme/demo"]:
            return False, "cannot disable wiki"
        if args[:3] == ["gh", "api", "graphql"]:
            return False, "delete unsupported"
        return False, f"unexpected command: {args}"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.cleanup_stage_primary_assets(tmp_path, "project")

    assert result["status"] == "partial"
    assert result["project"] == "closed"
    assert result["issues"]["Project | PRO-THM-01-TASK: Legacy"] == "closed"
    assert result["wiki"].startswith("manual-required:")


def test_render_wiki_home_content_is_landing_page_with_navigation() -> None:
    """Home wiki page should act as a landing page and not duplicate the stage page."""
    render_home = getattr(artifacts_flow_github, "_render_wiki_home_content")
    content = render_home(
        repo_slug="acme/demo",
        stage_title="Project",
        stage_page_url="https://github.com/acme/demo/wiki/Project",
        board_url="https://github.com/orgs/acme/projects/7",
        vision="Ship a better project workflow.",
        goals="- Goal one",
        constraints="- Constraint one",
        presentation_link="Project-Stakeholder-Briefing.pptx",
        visualization_entries=[
            (
                "Process Sequence",
                "assets/visualizations/sequence.svg",
                "Shows the orchestration flow.",
            )
        ],
    )

    assert "## Start Here" in content
    assert "# acme/demo Wiki" in content
    assert "Ship a better project workflow." in content
    assert "- Current focus: Goal one" in content
    assert "## Key Assets" in content
    assert "Project-Stakeholder-Briefing.pptx" in content
    assert "## Visual Guide" in content
    assert "[Process Sequence](assets/visualizations/sequence.svg)" in content


def test_render_wiki_home_content_supports_owner_neutral_local_links() -> None:
    """Local committed wiki pages should be renderable without owner-specific GitHub URLs."""
    render_home = getattr(artifacts_flow_github, "_render_wiki_home_content")

    content = render_home(
        repo_slug="",
        stage_title="Project",
        stage_page_url="Project.md",
        board_url="See [.digital-artifacts/40-stage/PROJECT.md](../../.digital-artifacts/40-stage/PROJECT.md).",
        vision="Ship a better project workflow.",
        goals="- Goal one",
        constraints="- Constraint one",
        presentation_link="Project-Stakeholder-Briefing.pptx",
    )

    assert "# Project Wiki" in content
    assert "[Project](Project.md)" in content
    assert "../../.digital-artifacts/40-stage/PROJECT.md" in content
    assert "github.com" not in content


def test_ensure_stage_scribble_rewrites_with_hand_drawn_style(tmp_path: Path) -> None:
    """Stage scribble should be visibly rough and rewrite stale machine-clean output."""
    scribble_dir = tmp_path / "docs" / "wiki" / "assets" / "scribbles"
    scribble_dir.mkdir(parents=True, exist_ok=True)
    scribble_path = scribble_dir / "project-workflow-scribble.svg"
    scribble_path.write_text("<svg><rect/></svg>", encoding="utf-8")

    ensure_scribble = getattr(artifacts_flow_github, "_ensure_stage_scribble")
    result = ensure_scribble(tmp_path, "project")
    content = result.read_text(encoding="utf-8")

    assert result == scribble_path
    assert "rough-paper" in content
    assert "stroke-linecap=\"round\"" in content
    assert "Project Workflow Sketch" in content
    assert "<path" in content


def test_ensure_stage_stakeholder_presentation_writes_handoffs_and_deck(
    monkeypatch, tmp_path: Path
) -> None:
    """Stakeholder deck generation should create request/response handoffs and a pptx artifact."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text("# Project\n\n## Vision\nShip stage.\n", encoding="utf-8")
    build_script = (
        tmp_path
        / ".github"
        / "skills"
        / "powerpoint"
        / "scripts"
        / "build_from_source.py"
    )
    build_script.parent.mkdir(parents=True, exist_ok=True)
    build_script.write_text("# test stub\n", encoding="utf-8")

    def _fake_run_local_command(
        _args: list[str], _cwd: Path, _env: dict[str, str]
    ) -> tuple[bool, str]:
        output_path = (
            tmp_path
            / "docs"
            / "wiki"
            / "assets"
            / "powerpoint"
            / "Project-Stakeholder-Briefing.pptx"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(b"pptx")
        return True, json.dumps({"status": "ok", "output": str(output_path)})

    monkeypatch.setattr(
        artifacts_flow_github, "_run_local_command", _fake_run_local_command
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_python_executable",
        lambda _repo_root: "python3",
    )

    ensure_presentation = getattr(
        artifacts_flow_github, "_ensure_stage_stakeholder_presentation"
    )
    result = ensure_presentation(
        tmp_path,
        "project",
        stage_path,
        "Project",
        "https://github.com/orgs/acme/projects/7",
        "https://github.com/acme/demo/wiki/Project",
    )

    request_path = Path(str(result["request_handoff"]))
    response_path = Path(str(result["response_handoff"]))
    output_path = Path(str(result["output_path"]))
    assert result["status"] == "created"
    assert request_path.exists()
    assert response_path.exists()
    assert output_path.exists()
    assert "expected_outputs:" in request_path.read_text(encoding="utf-8")
    assert "completion_criteria:" in response_path.read_text(encoding="utf-8")


def test_ensure_stage_wiki_initializes_home_when_wiki_repo_missing(
    monkeypatch, tmp_path: Path
) -> None:
    """Missing wiki clone should still initialize Home.md and the stage page."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text(
        "\n".join(
            [
                "---",
                'stage: "project"',
                "---",
                "",
                "# Project",
                "",
                "## Vision",
                "Ship the project stage.",
                "",
                "## Goals",
                "- Goal one",
                "",
                "## Constraints",
                "- Constraint one",
            ]
        ),
        encoding="utf-8",
    )
    wiki_template = (
        tmp_path
        / ".github"
        / "skills"
        / "stages-action"
        / "templates"
        / "wiki-stage-page.md"
    )
    wiki_template.parent.mkdir(parents=True, exist_ok=True)
    wiki_template.write_text(
        "\n".join(
            [
                "# {{ stage_title }}",
                "",
                "## Vision",
                "{{ vision }}",
                "",
                "## Goals",
                "{{ goals }}",
                "",
                "## Constraints",
                "{{ constraints }}",
                "",
                "Board: {{ board_url }}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    deck_path = (
        tmp_path
        / "docs"
        / "wiki"
        / "assets"
        / "powerpoint"
        / "Project-Stakeholder-Briefing.pptx"
    )
    deck_path.parent.mkdir(parents=True, exist_ok=True)
    deck_path.write_bytes(b"pptx")

    mermaid_dir = tmp_path / "docs" / "images" / "mermaid"
    mermaid_dir.mkdir(parents=True, exist_ok=True)
    (mermaid_dir / "sequence_project_prompt_agents.svg").write_text(
        "<svg>sequence</svg>",
        encoding="utf-8",
    )
    (mermaid_dir / "layer_model.svg").write_text(
        "<svg>layer</svg>",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_example", "GH_TOKEN"),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_repo_context",
        lambda _repo_root: ("acme/demo", "acme", "demo"),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_ensure_stage_stakeholder_presentation",
        lambda *_args, **_kwargs: {
            "status": "created",
            "output_path": str(deck_path),
            "attachment_name": "Project-Stakeholder-Briefing.pptx",
        },
    )

    run_git_calls: list[list[str]] = []

    clone_attempts = 0

    def _fake_run_git(
        args: list[str], _cwd: Path, _env: dict[str, str]
    ) -> tuple[bool, str]:
        nonlocal clone_attempts
        run_git_calls.append(args)
        if args[:1] == ["clone"]:
            clone_attempts += 1
            if clone_attempts == 1:
                return False, "missing wiki repo"
            (Path(args[-1]) / ".git").mkdir(parents=True, exist_ok=True)
            return True, "ok"
        return True, "ok"

    monkeypatch.setattr(artifacts_flow_github, "_run_git", _fake_run_git)
    monkeypatch.setattr(
        artifacts_flow_github,
        "_run_gh_command",
        lambda *_args, **_kwargs: (True, "ok"),
    )

    result = artifacts_flow_github.ensure_stage_wiki(
        tmp_path,
        "project",
        stage_path,
        "https://github.com/orgs/acme/projects/7",
    )

    wiki_dir = tmp_path / ".digital-runtime" / "github" / "wiki-cache" / "acme_demo"
    local_wiki_dir = tmp_path / "docs" / "wiki"
    home_text = (wiki_dir / "Home.md").read_text(encoding="utf-8")
    page_text = (wiki_dir / "Project.md").read_text(encoding="utf-8")
    local_home_text = (local_wiki_dir / "Home.md").read_text(encoding="utf-8")
    local_page_text = (local_wiki_dir / "Project.md").read_text(encoding="utf-8")
    assert result["status"] == "created"
    assert "## Start Here" in home_text
    assert "https://github.com/acme/demo/wiki/Project" in home_text
    assert "Project-Stakeholder-Briefing.pptx" in home_text
    assert "assets/visualizations/sequence_project_prompt_agents.svg" in home_text
    assert "assets/visualizations/layer_model.svg" in home_text
    assert "assets/scribbles/project-workflow-scribble.svg" in home_text
    assert "## Stakeholder Briefing" in page_text
    assert "## Visual Walkthrough" in page_text
    assert "assets/visualizations/sequence_project_prompt_agents.svg" in page_text
    assert "## Start Here" in local_home_text
    assert "[Project](Project.md)" in local_home_text
    assert "../../.digital-artifacts/40-stage/PROJECT.md" in local_home_text
    assert "https://github.com/acme/demo/wiki/Project" not in local_home_text
    assert "## Stakeholder Briefing" in local_page_text
    assert (wiki_dir / "assets" / "visualizations" / "sequence_project_prompt_agents.svg").exists()
    assert (wiki_dir / "assets" / "visualizations" / "layer_model.svg").exists()
    assert (wiki_dir / "assets" / "scribbles" / "project-workflow-scribble.svg").exists()
    assert sum(1 for call in run_git_calls if call[:1] == ["clone"]) == 2


def test_ensure_stage_stakeholder_presentation_reuses_project_runtime_deck(
    tmp_path: Path,
) -> None:
    """Project wiki publishing must reuse the canonical /project deck instead of building a divergent PPTX."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text("# Project\n", encoding="utf-8")

    canonical_project_deck = (
        tmp_path / "docs" / "powerpoints" / f"{tmp_path.name}_project.pptx"
    )
    canonical_project_deck.parent.mkdir(parents=True, exist_ok=True)
    canonical_project_deck.write_bytes(b"canonical-project-deck")

    ensure_presentation = getattr(
        artifacts_flow_github, "_ensure_stage_stakeholder_presentation"
    )
    result = ensure_presentation(
        tmp_path,
        "project",
        stage_path,
        "Project",
        "",
        "https://github.com/acme/demo/wiki/Project",
    )

    output_path = Path(str(result["output_path"]))
    assert result["status"] == "created"
    assert result["message"] == "stakeholder deck reused from canonical /project output"
    assert output_path.read_bytes() == b"canonical-project-deck"
    assert result["attachment_name"] == "Project-Stakeholder-Briefing.pptx"


def test_ensure_stage_primary_assets_skips_wiki_when_primary_sync_disabled(
    monkeypatch, tmp_path: Path
) -> None:
    """Primary sync disabled must not create or push wiki assets."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text(
        "\n".join(
            [
                "---",
                'stage: "project"',
                'board_id: ""',
                'board_url: ""',
                'wiki_url: ""',
                "---",
                "",
                "# Project",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(artifacts_flow_github, "_is_primary_sync_enabled", lambda: False)

    called = {"wiki": 0}

    def _unexpected(*_args, **_kwargs):
        called["wiki"] += 1
        raise AssertionError("ensure_stage_wiki must not be called when sync is disabled")

    monkeypatch.setattr(artifacts_flow_github, "ensure_stage_wiki", _unexpected)

    result = artifacts_flow_github.ensure_stage_primary_assets(tmp_path, "project", stage_path)

    assert result["project"]["status"] == "skipped"
    assert result["wiki"]["status"] == "skipped"
    assert called["wiki"] == 0


def test_ensure_planning_issue_assets_reopens_closed_issue(monkeypatch, tmp_path: Path) -> None:
    """Existing artifact-synced closed issues should be reopened during regeneration."""
    planning_dir = tmp_path / ".digital-artifacts" / "50-planning" / "project"
    planning_dir.mkdir(parents=True, exist_ok=True)
    task_path = planning_dir / "TASK_THM-01.md"
    task_path.write_text(
        "\n".join(
            [
                "---",
                'kind: task',
                'task_id: "TASK-THM-01"',
                'title: "Operationalize scope"',
                'assignee_hint: "fullstack-engineer"',
                "---",
                "",
                "# Task: Operationalize scope",
                "",
                "## Description",
                "- Execute deterministic delivery",
            ]
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_example", "GH_TOKEN"),
    )

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        if args[:3] == ["gh", "issue", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "issues": [
                            {
                                "number": 40,
                                "title": "Project | PRO-THM-01-TASK: Legacy",
                                "url": "https://github.com/acme/demo/issues/40",
                                "state": "CLOSED",
                                "body": "<!-- artifact-sync: stage=project; bundle=2026-04-15/THM-01; kind=task; board_ticket=PRO-THM-01-TASK -->",
                            }
                        ]
                    }
                ),
            )
        if args[:4] == ["gh", "issue", "reopen", "40"]:
            return True, "reopened"
        if args[:4] == ["gh", "issue", "edit", "40"]:
            return True, "edited"
        if args[:3] == ["gh", "label", "create"]:
            return True, "ok"
        if args[:3] == ["gh", "issue", "view"]:
            return True, json.dumps({"labels": []})
        if args[:3] == ["gh", "project", "item-list"]:
            return True, json.dumps({"items": []})
        if args[:3] == ["gh", "project", "item-add"]:
            return True, json.dumps({"id": "PVTI_lAH"})
        if args[:3] == ["gh", "api", "repos/acme/demo/milestones"]:
            return True, "[]"
        return True, "ok"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.ensure_planning_issue_assets(
        tmp_path,
        "project",
        "2026-04-15/THM-01",
        {"task": task_path},
        {"task": "PRO-THM-01-TASK"},
        {
            "repo_slug": "acme/demo",
            "project": {"owner": "acme", "number": "7"},
        },
    )

    assert result["status"] == "synced"
    assert result["issues"]["task"]["status"] in {
        "reopened+updated",
        "updated+reopened",
    }


def test_ensure_planning_issue_assets_creates_and_links_issues(
    monkeypatch, tmp_path: Path
) -> None:
    """Planning issue sync should create missing issues and add them to the project."""
    planning_root = tmp_path / ".digital-artifacts" / "50-planning" / "project"
    planning_root.mkdir(parents=True, exist_ok=True)
    task_path = planning_root / "TASK_00000.md"
    task_path.write_text(
        "---\nassignee_hint: \"fullstack-engineer\"\ntitle: \"Implement approved scope\"\n---\n\n## Description\nHuman-readable task scope\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("GH_TOKEN", "ghp_example")

    def _fake_repo_context(_repo_root: Path) -> tuple[str, str, str]:
        return "acme/demo", "acme", "demo"

    issue_list_calls = {"count": 0}

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        if args[:3] == ["gh", "api", "repos/acme/demo/milestones"]:
            method = "GET"
            if "--method" in args:
                method = args[args.index("--method") + 1]
            if method == "GET":
                return True, "[]"
            return True, '{"number": 1, "title": "Project-00000 Delivery"}'
        if args[:3] == ["gh", "issue", "list"]:
            issue_list_calls["count"] += 1
            return True, "[]"
        if args[:3] == ["gh", "issue", "create"]:
            return True, "https://github.com/acme/demo/issues/12"
        if args[:3] == ["gh", "issue", "view"]:
            return True, '{"labels": []}'
        if args[:3] == ["gh", "project", "item-list"]:
            return True, json.dumps({"items": []})
        if args[:3] == ["gh", "project", "item-add"]:
            return True, '{"id":"item-1"}'
        if args[:3] == ["gh", "label", "create"]:
            return True, "ok"
        if args[:3] == ["gh", "issue", "edit"]:
            return True, "ok"
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(
        artifacts_flow_github, "_resolve_repo_context", _fake_repo_context
    )
    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.ensure_planning_issue_assets(
        tmp_path,
        "project",
        "2026-03-31/00000",
        {"task": task_path},
        {"task": "PRO-00000-TASK"},
        {
            "repo_slug": "acme/demo",
            "project": {"owner": "acme", "number": "7"},
        },
    )

    assert issue_list_calls["count"] == 1
    assert result["status"] == "synced"
    assert result["issues"]["task"]["status"] == "created"
    assert result["issues"]["task"]["project_item_status"] == "added"
    assert result["issues"]["task"]["milestone"] == "Project-00000 Delivery"


def test_ensure_planning_issue_assets_syncs_meta_issues_but_skips_project_items(
    monkeypatch, tmp_path: Path
) -> None:
    """Epic and story issues are synced as agile-coach-owned meta issues without project-item placement."""
    planning_root = tmp_path / ".digital-artifacts" / "50-planning" / "project"
    planning_root.mkdir(parents=True, exist_ok=True)
    epic_path = planning_root / "EPIC_00000.md"
    story_path = planning_root / "STORY_00000.md"
    task_path = planning_root / "TASK_00000.md"
    epic_path.write_text(
        "---\nassignee_hint: \"agile-coach\"\ntitle: \"Project Team Operating Model\"\n---\n\n## Outcome\nMeta planning scope\n\n## Success Signals\n- Clear delivery boundary\n",
        encoding="utf-8",
    )
    story_path.write_text(
        "---\nassignee_hint: \"agile-coach\"\ntitle: \"Plan delivery for Project Team Operating Model\"\n---\n\n## Outcome\nPlanning coordination scope\n\n## Readiness Signals\n- Linked delivery task exists\n",
        encoding="utf-8",
    )
    task_path.write_text(
        "---\nassignee_hint: \"fullstack-engineer\"\ntitle: \"Implement approved scope\"\n---\n\n## Description\nHuman-readable task scope\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("GH_TOKEN", "ghp_example")

    added_urls: list[str] = []
    edited_commands: list[list[str]] = []

    def _fake_repo_context(_repo_root: Path) -> tuple[str, str, str]:
        return "acme/demo", "acme", "demo"

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        if args[:3] == ["gh", "api", "repos/acme/demo/milestones"]:
            method = "GET"
            if "--method" in args:
                method = args[args.index("--method") + 1]
            if method == "GET":
                return True, "[]"
            return True, '{"number": 1, "title": "Project-00000 Delivery"}'
        if args[:3] == ["gh", "issue", "list"]:
            return True, "[]"
        if args[:3] == ["gh", "issue", "create"]:
            issue_number = 10 + len(added_urls)
            return True, f"https://github.com/acme/demo/issues/{issue_number}"
        if args[:3] == ["gh", "issue", "view"]:
            return True, '{"labels": []}'
        if args[:3] == ["gh", "project", "item-list"]:
            return True, json.dumps({"items": []})
        if args[:3] == ["gh", "project", "item-add"]:
            added_urls.append(args[args.index("--url") + 1])
            return True, '{"id":"item-1"}'
        if args[:3] == ["gh", "label", "create"]:
            return True, "ok"
        if args[:3] == ["gh", "issue", "edit"]:
            edited_commands.append(args)
            return True, "ok"
        raise AssertionError(f"unexpected command: {args}")

    monkeypatch.setattr(
        artifacts_flow_github, "_resolve_repo_context", _fake_repo_context
    )
    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.ensure_planning_issue_assets(
        tmp_path,
        "project",
        "2026-03-31/00000",
        {"epic": epic_path, "story": story_path, "task": task_path},
        {"task": "PRO-00000-TASK"},
        {
            "repo_slug": "acme/demo",
            "project": {"owner": "acme", "number": "7"},
        },
    )

    assert result["issues"]["epic"]["status"] == "created"
    assert result["issues"]["story"]["status"] == "created"
    assert result["issues"]["task"]["status"] == "created"
    assert result["issues"]["epic"]["project_item_status"] == "skipped"
    assert result["issues"]["story"]["project_item_status"] == "skipped"
    assert result["issues"]["task"]["project_item_status"] == "added"
    assert added_urls == ["https://github.com/acme/demo/issues/10"]
    owner_labels = [args[args.index("--add-label") + 1] for args in edited_commands if "--add-label" in args]
    assert any("owner:agile-coach" in labels and "kind:epic" in labels for labels in owner_labels)
    assert any("owner:agile-coach" in labels and "kind:story" in labels for labels in owner_labels)
    assert any("owner:fullstack-engineer" in labels and "kind:task" in labels for labels in owner_labels)


def test_ensure_issue_labels_replaces_stale_owner_kind_stage_labels(monkeypatch) -> None:
    """Issue label sync should remove stale owner/kind/stage labels before adding deterministic labels."""
    edited_calls: list[list[str]] = []

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        if args[:3] == ["gh", "label", "create"]:
            return True, "ok"
        if args[:3] == ["gh", "issue", "view"]:
            return True, '{"labels": [{"name": "owner:fullstack-engineer"}, {"name": "kind:task"}, {"name": "stage:mvp"}]}'
        if args[:3] == ["gh", "issue", "edit"]:
            edited_calls.append(args)
            return True, "ok"
        return False, f"unexpected command: {args}"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    ensure_labels = getattr(artifacts_flow_github, "_ensure_issue_labels")
    ensure_labels(
        "acme/demo",
        "12",
        stage="project",
        kind="story",
        assignee_hint="fullstack-engineer",
        env={},
    )

    remove_calls = [call for call in edited_calls if "--remove-label" in call]
    add_calls = [call for call in edited_calls if "--add-label" in call]
    assert remove_calls
    remove_call_text = " ".join(remove_calls[0])
    assert "owner:fullstack-engineer" in remove_call_text
    assert "kind:task" in remove_call_text
    assert "stage:mvp" in remove_call_text
    assert add_calls


def test_artifact_issue_title_uses_frontmatter_title() -> None:
    """Issue titles should be human-readable and derived from artifact frontmatter."""
    text = "\n".join(
        [
            "---",
            'title: "Implement Specification 00003"',
            "---",
            "",
            "# Task: Implement Specification 00003",
        ]
    )
    issue_title = getattr(artifacts_flow_github, "_artifact_issue_title")
    title = issue_title(
        "task", text, "2026-04-13/00003", "project", "PRO-00003-TASK"
    )
    assert title.startswith("Project | PRO-00003-TASK")
    assert "---" not in title


def test_issue_body_omits_raw_frontmatter_and_absolute_paths() -> None:
    """Issue bodies should present cleaned artifact content and concise metadata."""
    artifact_text = "\n".join(
        [
            "---",
            "kind: task",
            'title: "Implement Specification 00003"',
            "---",
            "",
            "# Task: Implement Specification 00003",
            "",
            "## Description",
            "Human-readable description",
        ]
    )
    issue_body = getattr(artifacts_flow_github, "_issue_body")
    body = issue_body(
        marker="<!-- artifact-sync -->",
        artifact_text=artifact_text,
        board_ticket_id="PRO-00003-TASK",
        stage="project",
        kind="task",
        bundle_key="2026-04-13/00003",
    )
    assert "Execution Brief" in body
    assert "kind: task" not in body
    assert "/Users/" not in body


def test_issue_body_marks_checklist_items_done_for_completed_artifacts() -> None:
    """Completed artifacts should render checked checklist items in issue bodies."""
    artifact_text = "\n".join(
        [
            "---",
            'kind: task',
            'title: "Finalize delivery evidence"',
            "---",
            "",
            "## Acceptance Criteria",
            "- [ ] Human approval recorded",
            "- [ ] Tests attached",
        ]
    )

    issue_body = getattr(artifacts_flow_github, "_issue_body")
    body = issue_body(
        marker="<!-- artifact-sync -->",
        artifact_text=artifact_text,
        board_ticket_id="PRO-77777-TASK",
        stage="project",
        kind="task",
        bundle_key="2026-04-27/77777",
        artifact_status="done",
    )

    assert "## Progress Checklist" in body
    assert "- [x] Human approval recorded" in body
    assert "- [x] Tests attached" in body


def test_ensure_stage_wiki_keeps_ux_sections_off_home_page(monkeypatch, tmp_path: Path) -> None:
    """UX investigation and loop links belong on Project page, not Home page."""
    stage_path = tmp_path / ".digital-artifacts" / "40-stage" / "PROJECT.md"
    stage_path.parent.mkdir(parents=True, exist_ok=True)
    stage_path.write_text(
        "\n".join(
            [
                "---",
                'stage: "project"',
                "---",
                "",
                "# Project",
                "",
                "## Vision",
                "Ship deterministic delivery.",
                "",
                "## Goals",
                "- Goal one",
                "",
                "## Constraints",
                "- Constraint one",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    wiki_template = (
        tmp_path
        / ".github"
        / "skills"
        / "stages-action"
        / "templates"
        / "wiki-stage-page.md"
    )
    wiki_template.parent.mkdir(parents=True, exist_ok=True)
    wiki_template.write_text("# {{ stage_title }}\n\n{{ vision }}\n", encoding="utf-8")

    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: (None, None),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_sync_ux_review_assets",
        lambda *_args, **_kwargs: (
            [("UX Review A", "ux-reviews/UX_A.md", "Synced UX review")],
            ["ux-reviews/UX_A.md"],
            False,
        ),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_sync_ux_review_loop_pages",
        lambda *_args, **_kwargs: (
            [("Flow Alpha", "ux-review-loops/flow-alpha-loop.md", "Loop summary")],
            ["ux-review-loops/flow-alpha-loop.md"],
            False,
        ),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_sync_ux_scribble_assets",
        lambda *_args, **_kwargs: ([], [], False),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_sync_visualization_assets",
        lambda *_args, **_kwargs: ([], [], False),
    )
    monkeypatch.setattr(
        artifacts_flow_github,
        "_ensure_stage_stakeholder_presentation",
        lambda *_args, **_kwargs: {
            "status": "created",
            "output_path": "",
            "attachment_name": "",
        },
    )

    result = artifacts_flow_github.ensure_stage_wiki(
        tmp_path,
        "project",
        stage_path,
        "",
    )

    assert result["status"] in {"updated", "unchanged"}
    home_content = (tmp_path / "docs" / "wiki" / "Home.md").read_text(encoding="utf-8")
    stage_content = (tmp_path / "docs" / "wiki" / "Project.md").read_text(encoding="utf-8")
    assert "## UX Investigations" not in home_content
    assert "## UX Review Loops" not in home_content
    assert "## UX Investigations" in stage_content
    assert "## UX Review Loops" in stage_content


def test_ensure_planning_issue_assets_closes_issue_for_done_status(monkeypatch, tmp_path: Path) -> None:
    """Task artifacts marked done should close existing open synced issues."""
    planning_dir = tmp_path / ".digital-artifacts" / "50-planning" / "project"
    planning_dir.mkdir(parents=True, exist_ok=True)
    task_path = planning_dir / "TASK_DONE.md"
    task_path.write_text(
        "\n".join(
            [
                "---",
                'kind: task',
                'status: "done"',
                'task_id: "TASK-DONE-01"',
                'title: "Close loop after approval"',
                'assignee_hint: "fullstack-engineer"',
                "---",
                "",
                "## Description",
                "- Final reconciliation run",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        artifacts_flow_github,
        "_resolve_github_token",
        lambda: ("ghp_example", "GH_TOKEN"),
    )

    calls: list[list[str]] = []

    def _fake_run(args: list[str], _env: dict[str, str]) -> tuple[bool, str]:
        calls.append(args)
        if args[:3] == ["gh", "issue", "list"]:
            return (
                True,
                json.dumps(
                    {
                        "issues": [
                            {
                                "number": 41,
                                "title": "Project | PRO-DONE-TASK: Legacy",
                                "url": "https://github.com/acme/demo/issues/41",
                                "state": "OPEN",
                                "body": "<!-- artifact-sync: stage=project; bundle=2026-04-27/DONE; kind=task; board_ticket=PRO-DONE-TASK -->",
                            }
                        ]
                    }
                ),
            )
        if args[:4] == ["gh", "issue", "close", "41"]:
            return True, "closed"
        if args[:3] == ["gh", "label", "create"]:
            return True, "ok"
        if args[:3] == ["gh", "issue", "view"]:
            return True, json.dumps({"labels": []})
        if args[:3] == ["gh", "project", "item-list"]:
            return True, json.dumps({"items": []})
        if args[:3] == ["gh", "project", "item-add"]:
            return True, json.dumps({"id": "PVTI_done"})
        if args[:3] == ["gh", "api", "repos/acme/demo/milestones"]:
            return True, "[]"
        if args[:3] == ["gh", "issue", "edit"]:
            return True, "ok"
        return True, "ok"

    monkeypatch.setattr(artifacts_flow_github, "_run_gh_command", _fake_run)

    result = artifacts_flow_github.ensure_planning_issue_assets(
        tmp_path,
        "project",
        "2026-04-27/DONE",
        {"task": task_path},
        {"task": "PRO-DONE-TASK"},
        {
            "repo_slug": "acme/demo",
            "project": {"owner": "acme", "number": "7"},
        },
    )

    assert result["status"] == "synced"
    assert result["issues"]["task"]["status"] == "updated+closed"
    assert any(call[:4] == ["gh", "issue", "close", "41"] for call in calls)
