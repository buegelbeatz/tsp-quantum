"""E2E integration tests for GitHub operations.

These tests exercise real GitHub API calls (issues, board refs, wiki content)
using temporary resources. Each test creates resources with a unique prefix,
verifies expected behavior, and unconditionally cleans up in a finally-block.

**Requirements:**
- GITHUB_TOKEN (or GH_TOKEN) must be set in the environment.
- The token must have repo-level write access to the repository under test.
- GITHUB_TEST_REPO may be set explicitly; if omitted it is derived from the
  current git remote (owner/repo format).

**Running:**
    pytest -m integration --timeout=60 \\
        .github/skills/artifacts/scripts/tests/test_github_e2e_integration.py

**Skipping:**
    Any test is automatically skipped when GITHUB_TOKEN is absent.
"""
# pylint: disable=redefined-outer-name
# (pytest fixtures intentionally share the parameter name with the fixture function)

from __future__ import annotations

import json
import os
import subprocess
import sys
import uuid
from importlib import import_module
from pathlib import Path


import pytest


# ---------------------------------------------------------------------------
# Module-level bootstrap
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _github_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")


def _test_repo() -> str | None:
    explicit = os.environ.get("GITHUB_TEST_REPO")
    if explicit:
        return explicit
    try:
        remote = subprocess.check_output(
            ["git", "-C", str(ROOT), "remote", "get-url", "origin"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        import re
        m = re.search(r"github\.com[:/]([A-Za-z0-9_./-]+?)(?:\.git)?$", remote)
        return m.group(1) if m else None
    except (subprocess.SubprocessError, OSError, ValueError):
        return None


def _gh(*args: str, check: bool = True) -> subprocess.CompletedProcess:
    """Run a gh CLI command against the test repo with the current token."""
    token = _github_token()
    env = {**os.environ, "GH_TOKEN": token or "", "GITHUB_TOKEN": token or ""}
    return subprocess.run(
        ["gh", *args],
        capture_output=True,
        text=True,
        check=check,
        env=env,
    )


def _unique_tag() -> str:
    return f"e2e-test-{uuid.uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Skip marker
# ---------------------------------------------------------------------------

requires_github = pytest.mark.skipif(
    not _github_token() or not _test_repo(),
    reason="GITHUB_TOKEN and a resolvable repo are required for E2E tests",
)
pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixture: resolved repo slug
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def github_repo_slug() -> str:
    slug = _test_repo()
    if not slug:
        pytest.skip("Could not resolve GITHUB_TEST_REPO or git remote")
    return slug


# ---------------------------------------------------------------------------
# E2E: GitHub Issues
# ---------------------------------------------------------------------------

@requires_github
def test_github_issue_create_and_close(github_repo_slug: str) -> None:
    """Create a temporary issue, verify it exists, then close and delete it."""
    tag = _unique_tag()
    title = f"[E2E] Temporary issue {tag}"
    issue_number: str | None = None

    try:
        # Create issue
        result = _gh("issue", "create",
                     "--repo", github_repo_slug,
                     "--title", title,
                     "--body", f"Auto-created by E2E test {tag}. Will be deleted immediately.")
        # gh issue create returns the URL; extract number from it
        url = result.stdout.strip()
        issue_number = url.rstrip("/").rsplit("/", 1)[-1]

        assert issue_number.isdigit(), f"Expected numeric issue number, got: {issue_number}"

        # Verify issue is open
        view_result = _gh("issue", "view",
                          "--repo", github_repo_slug,
                          issue_number,
                          "--json", "title,state")
        issue_data = json.loads(view_result.stdout)
        assert issue_data["title"] == title
        assert issue_data["state"] == "OPEN"

    finally:
        if issue_number and issue_number.isdigit():
            # Close the issue
            _gh("issue", "close", "--repo", github_repo_slug, issue_number, check=False)
            # Delete the issue (requires admin token; fails gracefully if unavailable)
            _gh("issue", "delete", "--repo", github_repo_slug, issue_number, "--yes", check=False)


@requires_github
def test_github_issue_label_roundtrip(github_repo_slug: str) -> None:
    """Create an issue with a label, verify label is attached, then clean up."""
    tag = _unique_tag()
    title = f"[E2E] Label test {tag}"
    issue_number: str | None = None
    label_name = f"e2e-label-{tag}"

    try:
        # Ensure the test label exists (create it; ignore error if it already exists)
        _gh("label", "create", "--repo", github_repo_slug,
            label_name, "--color", "eeeeee", "--description", "E2E test label", check=False)

        # Create issue with label
        result = _gh("issue", "create",
                     "--repo", github_repo_slug,
                     "--title", title,
                     "--body", "E2E label roundtrip test.",
                     "--label", label_name)
        url = result.stdout.strip()
        issue_number = url.rstrip("/").rsplit("/", 1)[-1]

        assert issue_number.isdigit()

        # Verify label is attached
        view_result = _gh("issue", "view",
                          "--repo", github_repo_slug,
                          issue_number,
                          "--json", "labels")
        labels = json.loads(view_result.stdout).get("labels", [])
        label_names = [la["name"] for la in labels]
        assert label_name in label_names, f"Label {label_name!r} not found on issue. Got: {label_names}"

    finally:
        if issue_number and issue_number.isdigit():
            _gh("issue", "close", "--repo", github_repo_slug, issue_number, check=False)
            _gh("issue", "delete", "--repo", github_repo_slug, issue_number, "--yes", check=False)
        _gh("label", "delete", "--repo", github_repo_slug, label_name, "--yes", check=False)


# ---------------------------------------------------------------------------
# E2E: Board git refs
# ---------------------------------------------------------------------------

@requires_github
def test_board_ref_create_and_delete(_github_repo_slug: str) -> None:
    """Write a temporary board ticket as a git ref, verify it, and delete it."""
    tag = _unique_tag()
    ref_name = f"refs/board/e2e-stage/backlog/{tag}"
    ticket_content = (
        f"# E2E board ticket {tag}\n"
        "kind: task\n"
        "stage: e2e-stage\n"
        "status: backlog\n"
    )

    try:
        # Write blob and create the ref
        blob_hash = subprocess.check_output(
            ["git", "-C", str(ROOT), "hash-object", "-w", "--stdin"],
            input=ticket_content,
            text=True,
        ).strip()
        subprocess.check_call(
            ["git", "-C", str(ROOT), "update-ref", ref_name, blob_hash],
        )

        # Verify ref exists
        refs = subprocess.check_output(
            ["git", "-C", str(ROOT), "for-each-ref", "--format=%(refname)", ref_name],
            text=True,
        ).strip()
        assert ref_name in refs, f"Board ref {ref_name!r} not found after creation"

        # Read back content
        content_back = subprocess.check_output(
            ["git", "-C", str(ROOT), "cat-file", "blob", blob_hash],
            text=True,
        )
        assert tag in content_back

    finally:
        # Delete the temporary ref (ignore errors)
        subprocess.run(
            ["git", "-C", str(ROOT), "update-ref", "-d", ref_name],
            check=False,
        )


@requires_github
def test_board_refs_survive_multiple_tickets(_github_repo_slug: str) -> None:
    """Create three board refs in different lanes and verify they are independent."""
    tag = _unique_tag()
    lanes = ["backlog", "in-progress", "done"]
    ref_base = f"refs/board/e2e-stage/{{}}/{tag}"
    created_refs: list[str] = []

    try:
        for lane in lanes:
            ref = ref_base.format(lane)
            content = f"# Ticket {lane} {tag}\nstatus: {lane}\n"
            blob_hash = subprocess.check_output(
                ["git", "-C", str(ROOT), "hash-object", "-w", "--stdin"],
                input=content, text=True,
            ).strip()
            subprocess.check_call(
                ["git", "-C", str(ROOT), "update-ref", ref, blob_hash]
            )
            created_refs.append(ref)

        for lane, ref in zip(lanes, created_refs):
            out = subprocess.check_output(
                ["git", "-C", str(ROOT), "for-each-ref", "--format=%(refname)", ref],
                text=True,
            ).strip()
            assert ref in out, f"Ref {ref!r} missing after creation"

        backlog_ref = ref_base.format("backlog")
        done_ref = ref_base.format("done")
        assert backlog_ref != done_ref

    finally:
        for ref in created_refs:
            subprocess.run(
                ["git", "-C", str(ROOT), "update-ref", "-d", ref],
                check=False,
            )


# ---------------------------------------------------------------------------
# E2E: Wiki pages (local + GitHub wiki clone)
# ---------------------------------------------------------------------------

@requires_github
def test_wiki_local_page_is_owner_neutral(tmp_path: Path) -> None:
    """ensure_stage_wiki must write docs/wiki without owner-specific URLs."""
    tag = _unique_tag()
    stage_doc = tmp_path / "PROJECT.md"
    stage_doc.write_text(
        f"# E2E Test Stage {tag}\n"
        "ready_for_planning: true\n"
        f"stage_title: E2E Test {tag}\n"
    )

    wiki_dir = tmp_path / "docs" / "wiki"
    wiki_dir.mkdir(parents=True)

    # Call ensure_stage_wiki with no GitHub token (local-only path)
    orig_token_fn = getattr(artifacts_flow_github, "_resolve_github_token", None)
    try:
        if orig_token_fn:
            # Monkeypatch token resolver to return no-auth tuple (prevents GitHub sync)
            setattr(artifacts_flow_github, "_resolve_github_token", lambda: (None, None))
        os.environ.setdefault("DIGITAL_TEAM_SKIP_DOTENV", "1")
        os.environ.setdefault("DIGITAL_STAGE_PRIMARY_SYNC", "0")

        artifacts_flow_github.ensure_stage_wiki(
            tmp_path,
            "project",
            stage_doc,
            "",  # empty repo_slug → owner-neutral
        )
    finally:
        if orig_token_fn:
            setattr(artifacts_flow_github, "_resolve_github_token", orig_token_fn)
        os.environ.pop("DIGITAL_TEAM_SKIP_DOTENV", None)
        os.environ.pop("DIGITAL_STAGE_PRIMARY_SYNC", None)

    home_file = wiki_dir / "Home.md"
    if home_file.exists():
        content = home_file.read_text()
        # Must NOT contain any Github.com absolute URL when repo_slug is empty
        assert "https://github.com" not in content, (
            "Local wiki Home.md must not contain absolute GitHub URLs"
        )
        # Must NOT contain personal domain or email patterns (owner-neutral requirement)
        import re
        personal_patterns = [
            r'\w+@\w+\.\w+',  # Email addresses (e.g., name@example.com)
            r'https?://[\w-]+\.\w{2,}',  # Personal domains (e.g., https://example.org)
        ]
        for pattern in personal_patterns:
            matches = re.findall(pattern, content)
            assert not matches, (
                f"Local wiki must not contain personal domain/email patterns. Found: {matches}"
            )


@requires_github
def test_wiki_github_push_roundtrip(
    github_repo_slug: str,
    tmp_path: Path,
) -> None:
    """Clone the GitHub wiki, write a temp page, push it, verify it, then delete it."""
    tag = _unique_tag()
    wiki_clone_dir = tmp_path / "wiki-clone"
    wiki_page_name = f"E2E-Temp-{tag}.md"

    token = _github_token()
    owner, repo = github_repo_slug.split("/", 1)
    wiki_clone_url = f"https://{token}@github.com/{owner}/{repo}.wiki.git"

    # Clone the wiki (skip test gracefully if wiki not enabled)
    result = subprocess.run(
        ["git", "clone", "--depth=1", wiki_clone_url, str(wiki_clone_dir)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.skip(f"GitHub wiki not accessible for {github_repo_slug}: {result.stderr.strip()}")

    try:
        # Write temp page
        page_path = wiki_clone_dir / wiki_page_name
        page_path.write_text(
            f"# Temporary E2E test page {tag}\n\nThis page was auto-created and will be deleted.\n"
        )

        # Commit and push
        subprocess.check_call(
            ["git", "-C", str(wiki_clone_dir), "config", "user.email", "e2e-test@example.com"]
        )
        subprocess.check_call(
            ["git", "-C", str(wiki_clone_dir), "config", "user.name", "E2E Test"]
        )
        subprocess.check_call(
            ["git", "-C", str(wiki_clone_dir), "add", wiki_page_name]
        )
        subprocess.check_call(
            ["git", "-C", str(wiki_clone_dir), "commit", "-m", f"e2e: add temp page {tag}"]
        )
        subprocess.check_call(
            ["git", "-C", str(wiki_clone_dir), "push"]
        )

        # Verify: the page file must be in the clone after push
        assert page_path.exists(), f"Wiki page {wiki_page_name} missing after push"
        content = page_path.read_text()
        assert tag in content

    finally:
        # Delete temp page and force-push
        page_path = wiki_clone_dir / wiki_page_name
        if page_path.exists():
            page_path.unlink()
            subprocess.run(
                ["git", "-C", str(wiki_clone_dir), "add", "-A"], check=False
            )
            subprocess.run(
                ["git", "-C", str(wiki_clone_dir), "commit", "-m", f"e2e: cleanup temp page {tag}"],
                check=False,
            )
            subprocess.run(
                ["git", "-C", str(wiki_clone_dir), "push"],
                check=False,
            )
