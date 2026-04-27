"""GitHub project sync helpers for artifacts planning flow."""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from github_auth import build_github_env, resolve_github_token


_GH_COMMAND_TIMEOUT_SECONDS = 30
_GH_COMMAND_MAX_ATTEMPTS = 3
_LOCAL_COMMAND_TIMEOUT_SECONDS = 30
_MAX_UX_REVIEW_ITERATIONS = 2


def _shared_run_tool_path() -> Path:
    """Return path to shared run-tool wrapper."""
    return _repo_root() / ".github" / "skills" / "shared" / "shell" / "scripts" / "run-tool.sh"


def _classify_subprocess_failure(output: str) -> str:
    """Return deterministic failure class for subprocess output."""
    lowered = output.lower()
    if "timed out" in lowered:
        return "timeout"
    if "could not resolve host" in lowered or "connection reset" in lowered:
        return "network"
    if "authentication" in lowered or "token" in lowered or "forbidden" in lowered:
        return "auth"
    if "not found" in lowered:
        return "missing-resource"
    return "command-error"


def _resolve_github_token() -> tuple[str | None, str | None]:
    """Return available GitHub token and its source env var name."""
    return resolve_github_token(Path(__file__).resolve().parents[4])


def _run_gh_command(args: list[str], env: dict[str, str]) -> tuple[bool, str]:
    """Execute one gh command and return success plus output."""
    started = time.monotonic()
    last_output = ""
    run_tool = _shared_run_tool_path()
    use_local_gh = bool(args and args[0] == "gh" and shutil.which("gh"))
    command = args if use_local_gh or not run_tool.exists() else ["bash", str(run_tool), *args]
    for attempt in range(1, _GH_COMMAND_MAX_ATTEMPTS + 1):
        try:
            completed = subprocess.run(
                command,
                check=False,
                text=True,
                capture_output=True,
                env=env,
                timeout=_GH_COMMAND_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            last_output = (
                f"gh command timed out after {_GH_COMMAND_TIMEOUT_SECONDS}s: {' '.join(args)}"
            )
            if attempt < _GH_COMMAND_MAX_ATTEMPTS:
                continue
            elapsed = int(time.monotonic() - started)
            return False, (
                f"[operation=gh attempt={attempt}/{_GH_COMMAND_MAX_ATTEMPTS} "
                f"elapsed={elapsed}s classification=timeout] {last_output}"
            )
        except OSError as exc:
            elapsed = int(time.monotonic() - started)
            output = str(exc)
            return False, (
                f"[operation=gh attempt={attempt}/{_GH_COMMAND_MAX_ATTEMPTS} "
                f"elapsed={elapsed}s classification={_classify_subprocess_failure(output)}] {output}"
            )

        output = ((completed.stdout or "") + (completed.stderr or "")).strip()
        if completed.returncode == 0:
            return True, output

        last_output = output or f"gh command failed: {' '.join(command)}"
        if attempt < _GH_COMMAND_MAX_ATTEMPTS:
            continue
        elapsed = int(time.monotonic() - started)
        return False, (
            f"[operation=gh attempt={attempt}/{_GH_COMMAND_MAX_ATTEMPTS} "
            f"elapsed={elapsed}s classification={_classify_subprocess_failure(last_output)}] {last_output}"
        )

    return False, last_output


def _run_local_command(
    args: list[str], cwd: Path, env: dict[str, str]
) -> tuple[bool, str]:
    """Execute a local helper command and return success plus combined output."""
    started = time.monotonic()
    try:
        completed = subprocess.run(
            args,
            check=False,
            text=True,
            capture_output=True,
            env=env,
            cwd=cwd,
            timeout=_LOCAL_COMMAND_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        elapsed = int(time.monotonic() - started)
        output = (
            f"local command timed out after {_LOCAL_COMMAND_TIMEOUT_SECONDS}s: {' '.join(args)}"
        )
        return False, (
            f"[operation=local-command elapsed={elapsed}s classification=timeout] {output}"
        )
    except OSError as exc:
        elapsed = int(time.monotonic() - started)
        output = str(exc)
        return False, (
            f"[operation=local-command elapsed={elapsed}s classification={_classify_subprocess_failure(output)}] {output}"
        )
    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode == 0:
        return True, output.strip()
    elapsed = int(time.monotonic() - started)
    clean_output = output.strip()
    return False, (
        f"[operation=local-command elapsed={elapsed}s "
        f"classification={_classify_subprocess_failure(clean_output)}] {clean_output}"
    )


def _repo_root() -> Path:
    """Return repository root derived from this module path."""
    return Path(__file__).resolve().parents[4]


def _build_gh_env(token: str) -> dict[str, str]:
    """Build environment for gh and shared GitHub shell scripts."""
    env = build_github_env(token)
    # Prevent interactive login/device prompts in non-interactive pipeline runs.
    env["GH_PROMPT_DISABLED"] = "1"
    return env


def _wiki_cache_dir(repo_root: Path, repo_slug: str) -> Path:
    """Return local cache directory used for GitHub wiki clones."""
    return (
        repo_root
        / ".digital-runtime"
        / "github"
        / "wiki-cache"
        / repo_slug.replace("/", "_")
    )


def _resolve_repo_slug(repo_root: Path) -> str:
    """Resolve owner/repo slug from env or git remote."""
    repo_slug = os.getenv("GITHUB_REPO", "").strip()
    if repo_slug:
        return repo_slug

    try:
        completed = subprocess.run(
            ["git", "-C", str(repo_root), "remote", "get-url", "origin"],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        return ""

    remote_url = (completed.stdout or "").strip()
    match = re.search(r"github\.com[:/]([^/]+/[^/.]+)(?:\.git)?$", remote_url)
    return match.group(1) if match else ""


def _resolve_repo_context(repo_root: Path) -> tuple[str, str, str]:
    """Return (repo_slug, owner, repo_name)."""
    repo_slug = _resolve_repo_slug(repo_root)
    if not repo_slug or "/" not in repo_slug:
        return "", "", ""
    owner, repo_name = repo_slug.split("/", 1)
    return repo_slug, owner, repo_name


def _is_primary_sync_enabled() -> bool:
    """Return True when primary-system synchronization is enabled."""
    raw = os.getenv("DIGITAL_STAGE_PRIMARY_SYNC", "1").strip().lower()
    return raw not in {"0", "false", "off", "no"}


def _filter_dict_items(values: object) -> list[dict[str, object]]:
    """Return only dictionary entries from a list-like value."""
    if not isinstance(values, list):
        return []
    return [item for item in values if isinstance(item, dict)]


def _extract_container_values(payload: object, key: str) -> object:
    """Extract container payload by key when payload is dict; else passthrough."""
    if isinstance(payload, dict):
        return payload.get(key)
    return payload


def _extract_dict_list(payload: object, key: str) -> list[dict[str, object]]:
    """Normalize payload to a list of dictionaries for a given top-level key."""
    values = _extract_container_values(payload, key)
    return _filter_dict_items(values)


def _extract_project_items(payload: object) -> list[dict[str, object]]:
    """Normalize gh project item-list payload to a list of items."""
    return _extract_dict_list(payload, "items")


def _extract_projects(payload: object) -> list[dict[str, object]]:
    """Normalize gh project list payload to a list of project dicts."""
    return _extract_dict_list(payload, "projects")


def _extract_issues(payload: object) -> list[dict[str, object]]:
    """Normalize gh issue list payload to a list of issues."""
    return _extract_dict_list(payload, "issues")


def _find_stage_project(
    owner: str, stage: str, repo_name: str, env: dict[str, str]
) -> dict[str, object] | None:
    """Return matching GitHub project metadata for one stage, if present."""
    ok, output = _run_gh_command(
        [
            "gh",
            "project",
            "list",
            "--owner",
            owner,
            "--limit",
            "100",
            "--format",
            "json",
        ],
        env,
    )
    if not ok:
        return None
    try:
        projects = _extract_projects(json.loads(output))
    except json.JSONDecodeError:
        return None

    aliases = set(_project_title_aliases(stage, repo_name))
    for project in projects:
        if str(project.get("title", "")).strip() in aliases:
            return project
    return None


def _project_title(stage: str, repo_name: str) -> str:
    """Return deterministic GitHub project title for a stage."""
    return f"{repo_name} - {stage}"


def _project_title_aliases(stage: str, repo_name: str) -> list[str]:
    """Return accepted canonical and legacy titles for one stage project."""
    canonical = _project_title(stage, repo_name)
    legacy = stage.title()
    return [
        canonical,
        legacy,
        f"{legacy} Delivery Board",
        f"{legacy} Board",
    ]


def _project_description(stage: str, repo_slug: str) -> str:
    """Return default short description for a stage project board."""
    return (
        f"Stage board for '{stage}' in {repo_slug}. "
        "Source workflow is generated from the stage artifacts pipeline."
    )


def _parse_frontmatter(artifact_text: str) -> dict[str, str]:
    """Parse simple YAML frontmatter key/value pairs from a markdown artifact."""
    lines = artifact_text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}
    metadata: dict[str, str] = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"').strip("'")
    return metadata


def _frontmatter_list_has_items(artifact_text: str, key: str) -> bool:
    """Return True when a YAML frontmatter list key contains at least one item."""
    lines = artifact_text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return False

    in_target_list = False
    key_prefix = f"{key}:"
    for line in lines[1:]:
        stripped = line.strip()
        if stripped == "---":
            break
        if not stripped:
            continue
        if line.startswith(" ") or line.startswith("\t"):
            if in_target_list and stripped.startswith("- "):
                return True
            continue
        if stripped.startswith(key_prefix):
            remainder = stripped[len(key_prefix) :].strip()
            if remainder.startswith("[") and remainder.endswith("]"):
                inner = remainder[1:-1].strip()
                return bool(inner)
            in_target_list = True
            continue
        if in_target_list:
            return False
    return False


def _strip_frontmatter(artifact_text: str) -> str:
    """Return markdown content without YAML frontmatter."""
    lines = artifact_text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return artifact_text
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            return "\n".join(lines[index + 1 :]).strip()
    return artifact_text


def ensure_github_project(repo_root: Path, stage: str) -> dict[str, object]:
    """Ensure the GitHub project exists and return resolved metadata."""
    token, source = _resolve_github_token()
    repo_slug, owner, repo_name = _resolve_repo_context(repo_root)
    if not token:
        return {
            "status": "manual-required",
            "message": (
                "GITHUB_TOKEN/GH_TOKEN not set. "
                "Set GITHUB_TOKEN (preferred) or GH_TOKEN, or define one of them in repository .env. "
                "Fallback remains default-safe via refs/board/* local board sync."
            ),
            "owner": owner,
            "repo_slug": repo_slug,
            "number": "",
            "url": "",
            "title": _project_title(stage, repo_name),
            "auth_source": "",
        }
    if not owner:
        return {
            "status": "manual-required",
            "message": "repository owner could not be resolved",
            "owner": "",
            "repo_slug": repo_slug,
            "number": "",
            "url": "",
            "title": _project_title(stage, repo_name),
            "auth_source": source or "",
        }

    env = _build_gh_env(token)
    title = _project_title(stage, repo_name)
    ok, list_output = _run_gh_command(
        [
            "gh",
            "project",
            "list",
            "--owner",
            owner,
            "--limit",
            "100",
            "--format",
            "json",
        ],
        env,
    )
    if not ok:
        return {
            "status": "manual-required",
            "message": list_output or "unable to list github projects",
            "owner": owner,
            "repo_slug": repo_slug,
            "number": "",
            "url": "",
            "title": title,
            "auth_source": source or "",
        }

    try:
        projects = _extract_projects(json.loads(list_output))
    except json.JSONDecodeError:
        projects = []

    title_aliases = [candidate.lower() for candidate in _project_title_aliases(stage, repo_name)]
    canonical_title_lc = title.lower()
    canonical_project = next(
        (
            item
            for item in projects
            if str(item.get("title", "")).strip().lower() == canonical_title_lc
        ),
        None,
    )
    project = canonical_project
    if project is None:
        project = next(
            (
                item
                for item in projects
                if str(item.get("title", "")).strip().lower() in title_aliases
            ),
            None,
        )
    status = "found"
    if project is None:
        ok, create_output = _run_gh_command(
            [
                "gh",
                "project",
                "create",
                "--owner",
                owner,
                "--title",
                title,
                "--format",
                "json",
            ],
            env,
        )
        if not ok:
            return {
                "status": "manual-required",
                "message": create_output or "unable to create github project",
                "owner": owner,
                "repo_slug": repo_slug,
                "number": "",
                "url": "",
                "title": title,
                "auth_source": source or "",
            }
        status = "created"
        try:
            created_payload = json.loads(create_output)
            project = created_payload if isinstance(created_payload, dict) else None
        except json.JSONDecodeError:
            project = None
        if project is None:
            ok, relist_output = _run_gh_command(
                [
                    "gh",
                    "project",
                    "list",
                    "--owner",
                    owner,
                    "--limit",
                    "100",
                    "--format",
                    "json",
                ],
                env,
            )
            if ok:
                try:
                    projects = _extract_projects(json.loads(relist_output))
                except json.JSONDecodeError:
                    projects = []
                project = next(
                    (
                        item
                        for item in projects
                        if str(item.get("title", "")).strip().lower() == title.lower()
                    ),
                    None,
                )

    number = str(project.get("number", "")) if isinstance(project, dict) else ""
    url = str(project.get("url", "")) if isinstance(project, dict) else ""
    resolved_title = str(project.get("title", "")).strip() if isinstance(project, dict) else title

    if number:
        ok, view_output = _run_gh_command(
            ["gh", "project", "view", number, "--owner", owner, "--format", "json"], env
        )
        if ok:
            try:
                view_payload = json.loads(view_output)
            except json.JSONDecodeError:
                view_payload = {}
            if isinstance(view_payload, dict):
                url = str(view_payload.get("url", url))

    if repo_slug and number:
        if resolved_title and resolved_title.lower() != title.lower():
            _run_gh_command(
                [
                    "gh",
                    "project",
                    "edit",
                    number,
                    "--owner",
                    owner,
                    "--title",
                    title,
                ],
                env,
            )
            resolved_title = title

        _run_gh_command(
            ["gh", "project", "link", number, "--owner", owner, "--repo", repo_slug],
            env,
        )
        _run_gh_command(
            [
                "gh",
                "project",
                "edit",
                number,
                "--owner",
                owner,
                "--description",
                _project_description(stage, repo_slug),
            ],
            env,
        )

        # Best-effort cleanup: close legacy duplicates when canonical exists.
        if canonical_project is not None:
            for candidate in projects:
                candidate_number = str(candidate.get("number", "")).strip()
                candidate_title = str(candidate.get("title", "")).strip()
                if not candidate_number or candidate_number == number:
                    continue
                if candidate_title.lower() not in title_aliases:
                    continue
                _run_gh_command(
                    ["gh", "project", "close", candidate_number, "--owner", owner],
                    env,
                )

    message_prefix = "existing project" if status == "found" else "created project"
    return {
        "status": status,
        "message": f"{message_prefix}: {resolved_title or title} (auth={source})",
        "owner": owner,
        "repo_slug": repo_slug,
        "number": number,
        "url": url,
        "title": resolved_title or title,
        "auth_source": source or "",
    }


def github_project_sync(stage: str) -> tuple[str, str]:
    """Try to find or create a stage-scoped GitHub project with gh CLI."""
    if not _is_primary_sync_enabled():
        return "skipped", "primary sync disabled by DIGITAL_STAGE_PRIMARY_SYNC"
    project = ensure_github_project(_repo_root(), stage)
    return str(project.get("status", "manual-required")), str(
        project.get("message", "manual-required")
    )


def _first_heading(markdown_text: str) -> str:
    """Return first H1 heading from markdown text."""
    for line in markdown_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return ""


def _extract_section(markdown_text: str, heading: str) -> str:
    """Extract markdown section body without the heading line."""
    lines = markdown_text.splitlines()
    expected = heading.strip().lower()
    in_section = False
    collected: list[str] = []
    for line in lines:
        if line.startswith("## "):
            current = line[3:].strip().lower()
            if in_section:
                break
            if current == expected:
                in_section = True
                continue
        if in_section:
            collected.append(line)
    return "\n".join(collected).strip()


def _render_template(template_text: str, replacements: dict[str, str]) -> str:
    """Render simple handlebars-style template."""
    rendered = template_text
    for key, value in replacements.items():
        rendered = rendered.replace(f"{{{{{key}}}}}", value)
    return rendered


def _wiki_page_slug(title: str) -> str:
    """Convert page title to GitHub wiki slug."""
    return "".join(
        ch for ch in title.replace(" ", "-") if ch.isalnum() or ch in {"-", "_"}
    )


def _wiki_page_url(repo_slug: str, page_title: str) -> str:
    """Return canonical GitHub wiki page URL."""
    return f"https://github.com/{repo_slug}/wiki/{_wiki_page_slug(page_title)}"


def _clean_stage_summary_lines(text: str) -> str:
    """Return a concise, English-oriented stage summary block for wiki rendering."""
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        line = re.sub(r"^[\-*]+\s*", "", line).strip()
        line = re.sub(r"^(primary finding:|secondary finding:|core problem:|supporting evidence:|address:|focus on:)\s*", "", line, flags=re.IGNORECASE)
        line = line.replace("**", "").strip()
        if any(token in line.lower() for token in ("interne entwickler", "der primäre zugang", "der nutzer gibt", "`state_", "stakeholder map", "self-managed virtual team")):
            continue
        if line.lower().startswith("holistic synthesis from all relevant expert"):
            continue
        if "|" in line and line.count("|") >= 2:
            continue
        lines.append(line)
    return "\n".join(lines[:3])


def _planning_hierarchy_lines(repo_root: Path, stage: str) -> list[str]:
    """Return concise planning hierarchy bullets for the stage wiki page."""
    planning_dir = repo_root / ".digital-artifacts" / "50-planning" / stage
    if not planning_dir.exists():
        return []

    entries: list[str] = []
    for kind, pattern, id_key in (
        ("Epic", "EPIC_*.md", "epic_id"),
        ("Story", "STORY_*.md", "story_id"),
        ("Task", "TASK_*.md", "task_id"),
        ("Bug", "BUG_*.md", "bug_id"),
    ):
        for artifact in sorted(planning_dir.glob(pattern)):
            artifact_text = artifact.read_text(encoding="utf-8")
            metadata = _parse_frontmatter(artifact_text)
            item_id = metadata.get(id_key, "").strip() or artifact.stem
            item_title = metadata.get("title", "").strip() or _first_heading(artifact_text)
            item_status = metadata.get("status", "").strip() or "unknown"
            if item_title:
                entries.append(f"- {kind}: {item_id} [{item_status}] - {item_title}")
            else:
                entries.append(f"- {kind}: {item_id} [{item_status}]")
    return entries


def _visualization_catalog(repo_root: Path, stage: str) -> list[tuple[str, Path, str]]:
    """Return visualization sources together with reader-oriented descriptions.

    Dynamically discovers all SVG files under docs/images/mermaid/ so any
    committed diagram is included in the wiki without manual catalog updates.
    """
    stage_label = stage.replace("-", " ").title()
    mermaid_dir = repo_root / "docs" / "images" / "mermaid"
    if not mermaid_dir.exists():
        return []
    entries: list[tuple[str, Path, str]] = []
    for svg_file in sorted(mermaid_dir.glob("*.svg")):
        label = svg_file.stem.replace("_", " ").replace("-", " ").title()
        description = f"{stage_label} stage diagram: {label}."
        entries.append((label, svg_file, description))
    return entries


def _build_stage_visualization_lines(
    visualization_entries: list[tuple[str, str, str]]
) -> list[str]:
    """Build a top-down visualization walkthrough under a Visual Walkthrough heading.

    All entries are rendered as sub-sections beneath a "## Visual Walkthrough"
    heading so readers can navigate from high-level understanding to precise
    implementation detail without being overwhelmed.
    """
    if not visualization_entries:
        return []

    lines: list[str] = ["## Visual Walkthrough", ""]
    for title, relative_target, description in visualization_entries:
        image_markup = f"![{title}]({relative_target})"
        # Keep the three-layer model compact in wiki pages.
        if title.strip().lower() == "layer model":
            image_markup = (
                f'<img src="{relative_target}" alt="{title}" '
                'style="max-width: 520px; width: 100%; height: auto;" />'
            )
        lines.extend(
            [
                f"### {title}",
                "",
                description,
                "",
                image_markup,
                f"[Open SVG file]({relative_target})",
                "",
            ]
        )
    return lines


def _build_home_visual_guide_lines(
    visualization_entries: list[tuple[str, str, str]]
) -> list[str]:
    """Build compact visualization navigation for the wiki landing page."""
    if not visualization_entries:
        return []

    lines = [
        "## Visual Guide",
        "",
        "Open these assets when you need detail. The landing page stays compact on purpose.",
        "",
    ]
    for title, relative_target, description in visualization_entries:
        lines.append(f"- [{title}]({relative_target}) - {description}")
    lines.append("")
    return lines


def _ensure_stage_scribble(repo_root: Path, stage: str) -> Path:
    """Create a hand-drawn style workflow sketch SVG for stakeholder wiki pages."""
    scribble_dir = repo_root / "docs" / "wiki" / "assets" / "scribbles"
    scribble_dir.mkdir(parents=True, exist_ok=True)
    scribble_path = scribble_dir / f"{stage}-workflow-scribble.svg"
    stage_label = stage.replace("-", " ").title()
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="560" viewBox="0 0 1280 560">
    <defs>
        <filter id="rough-paper">
            <feTurbulence type="fractalNoise" baseFrequency="0.04" numOctaves="5" result="noise"/>
            <feDisplacementMap in="SourceGraphic" in2="noise" scale="3" xChannelSelector="R" yChannelSelector="G"/>
        </filter>
        <marker id="arrow" markerWidth="12" markerHeight="8" refX="10" refY="4" orient="auto" markerUnits="strokeWidth">
            <path d="M0,0 L12,4 L0,8 z" fill="#555" stroke-linecap="round"/>
        </marker>
    </defs>
    <rect x="0" y="0" width="1280" height="560" fill="#faf9f6" filter="url(#rough-paper)"/>
    <text x="72" y="84" font-family="'Segoe UI', Arial, sans-serif" font-size="40" fill="#1a1a1a" font-weight="700">{stage_label} Workflow Sketch</text>
    <text x="72" y="124" font-family="'Segoe UI', Arial, sans-serif" font-size="20" fill="#555">Intake to delivery — one controlled feedback loop.</text>

    <path d="M80,186 C82,183 388,190 390,186 C392,182 394,298 390,302 C386,306 82,310 78,306 C74,302 76,190 80,186 Z" fill="#fff" stroke="#333" stroke-width="2" stroke-linecap="round" filter="url(#rough-paper)"/>
    <text x="160" y="236" font-family="'Segoe UI', Arial, sans-serif" font-size="28" fill="#111" font-weight="600">Input &amp; Intake</text>
    <text x="100" y="274" font-family="'Segoe UI', Arial, sans-serif" font-size="18" fill="#4b5563">Evidence, notes, open questions</text>

    <path d="M488,186 C490,183 796,190 798,186 C800,182 802,298 798,302 C794,306 490,310 486,306 C482,302 484,190 488,186 Z" fill="#fff" stroke="#333" stroke-width="2" stroke-linecap="round" filter="url(#rough-paper)"/>
    <text x="576" y="236" font-family="'Segoe UI', Arial, sans-serif" font-size="28" fill="#111" font-weight="600">Planning</text>
    <text x="510" y="274" font-family="'Segoe UI', Arial, sans-serif" font-size="18" fill="#4b5563">Scope, owners, quality gates</text>

    <path d="M896,186 C898,183 1196,190 1198,186 C1200,182 1202,298 1198,302 C1194,306 898,310 894,306 C890,302 892,190 896,186 Z" fill="#fff" stroke="#333" stroke-width="2" stroke-linecap="round" filter="url(#rough-paper)"/>
    <text x="986" y="236" font-family="'Segoe UI', Arial, sans-serif" font-size="28" fill="#111" font-weight="600">Delivery</text>
    <text x="940" y="274" font-family="'Segoe UI', Arial, sans-serif" font-size="18" fill="#4b5563">Tickets, PRs, review loops</text>

    <path d="M393,250 C420,248 462,250 484,250" fill="none" stroke="#555" stroke-width="3" stroke-linecap="round" marker-end="url(#arrow)" filter="url(#rough-paper)"/>
    <path d="M800,250 C828,248 868,250 892,250" fill="none" stroke="#555" stroke-width="3" stroke-linecap="round" marker-end="url(#arrow)" filter="url(#rough-paper)"/>
    <path d="M1048,320 C980,430 528,440 420,352" fill="none" stroke="#d97706" stroke-width="3" stroke-dasharray="9 7" stroke-linecap="round" marker-end="url(#arrow)" filter="url(#rough-paper)"/>
    <text x="526" y="500" font-family="'Segoe UI', Arial, sans-serif" font-size="20" fill="#9a3412" font-weight="600">Feedback and clarification loop</text>
</svg>
"""
    existing_svg = scribble_path.read_text(encoding="utf-8") if scribble_path.exists() else None
    if existing_svg != svg:
        scribble_path.write_text(svg, encoding="utf-8")
    return scribble_path


def _resolve_default_branch(repo_root: Path) -> str:
    """Best-effort detection of repository default branch for stable raw links."""
    try:
        symbolic = subprocess.run(
            ["git", "-C", str(repo_root), "symbolic-ref", "refs/remotes/origin/HEAD"],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        symbolic = None
    if symbolic and symbolic.returncode == 0:
        ref = (symbolic.stdout or "").strip()
        if "/" in ref:
            candidate = ref.rsplit("/", 1)[-1].strip()
            if candidate:
                return candidate

    try:
        current = subprocess.run(
            ["git", "-C", str(repo_root), "rev-parse", "--abbrev-ref", "HEAD"],
            check=False,
            text=True,
            capture_output=True,
        )
    except OSError:
        current = None
    if current and current.returncode == 0:
        candidate = (current.stdout or "").strip()
        if candidate and candidate != "HEAD":
            return candidate

    return "main"


def _sync_visualization_assets(
    repo_root: Path,
    local_wiki_dir: Path,
    stage: str,
) -> tuple[list[tuple[str, str, str]], list[str], bool]:
    """Copy visualization assets into wiki-managed folders and return their metadata."""
    entries: list[tuple[str, str, str]] = []
    asset_paths: list[str] = []
    changed = False

    wiki_asset_root = local_wiki_dir / "assets"
    visualization_dir = wiki_asset_root / "visualizations"
    visualization_dir.mkdir(parents=True, exist_ok=True)
    scribble_dir = wiki_asset_root / "scribbles"
    scribble_dir.mkdir(parents=True, exist_ok=True)

    for label, source_path, description in _visualization_catalog(repo_root, stage):
        if not source_path.exists():
            continue
        target_path = visualization_dir / source_path.name
        source_bytes = source_path.read_bytes()
        existing_bytes = target_path.read_bytes() if target_path.exists() else None
        if existing_bytes != source_bytes:
            target_path.write_bytes(source_bytes)
            changed = True
        relative_target = target_path.relative_to(local_wiki_dir).as_posix()
        asset_paths.append(relative_target)
        entries.append((label, relative_target, description))

    scribble_source = _ensure_stage_scribble(repo_root, stage)
    scribble_target = scribble_dir / scribble_source.name
    scribble_bytes = scribble_source.read_bytes()
    existing_scribble_bytes = scribble_target.read_bytes() if scribble_target.exists() else None
    if existing_scribble_bytes != scribble_bytes:
        scribble_target.write_bytes(scribble_bytes)
        changed = True
    scribble_relative = scribble_target.relative_to(local_wiki_dir).as_posix()
    asset_paths.append(scribble_relative)
    entries.append(
        (
            "Simplified Workflow",
            scribble_relative,
            "Executive-level workflow view with clean structure and one explicit feedback loop.",
        )
    )
    return entries, asset_paths, changed


def _sync_ux_review_assets(
    repo_root: Path,
    local_wiki_dir: Path,
    stage: str,
) -> tuple[list[tuple[str, str, str]], list[str], bool]:
    """Copy UX review markdown artifacts into docs/wiki and return metadata."""
    stage_review_root = repo_root / ".digital-artifacts" / "60-review"
    target_dir = local_wiki_dir / "ux-reviews"
    target_dir.mkdir(parents=True, exist_ok=True)

    if not stage_review_root.exists():
        return [], [], False

    patterns = (
        "UX_*.md",
        "USER_STANDARD_REVIEW*.md",
        "USER_REVIEW*.md",
        "user-review-*.md",
    )

    latest_by_name: dict[str, Path] = {}
    for stage_dir in stage_review_root.glob(f"*/{stage}"):
        if not stage_dir.is_dir():
            continue
        for pattern in patterns:
            for candidate in stage_dir.glob(pattern):
                name = candidate.name
                current = latest_by_name.get(name)
                if current is None or candidate.stat().st_mtime >= current.stat().st_mtime:
                    latest_by_name[name] = candidate

    entries: list[tuple[str, str, str]] = []
    asset_paths: list[str] = []
    changed = False

    for name, source in sorted(latest_by_name.items()):
        target = target_dir / name
        source_text = source.read_text(encoding="utf-8")
        existing_text = target.read_text(encoding="utf-8") if target.exists() else None
        if existing_text != source_text:
            target.write_text(source_text, encoding="utf-8")
            changed = True

        rel_path = target.relative_to(local_wiki_dir).as_posix()
        title = name.removesuffix(".md").replace("_", " ").replace("-", " ").title()
        entries.append(
            (
                title,
                rel_path,
                "Synced UX investigation artifact from the review pipeline.",
            )
        )
        asset_paths.append(rel_path)

    return entries, asset_paths, changed


def _infer_feature_slug_from_review_filename(filename: str) -> str:
    """Infer feature slug from user-review filename convention."""
    name = filename.removesuffix(".md")
    match = re.match(r"^user-review-\d{8}-(.+)-r\d+$", name)
    if match:
        return match.group(1).strip().lower()
    return re.sub(r"[^a-z0-9._-]+", "-", name.strip().lower()).strip("-") or "ux-feature"


def _sync_ux_review_loop_pages(
    repo_root: Path,
    local_wiki_dir: Path,
    stage: str,
) -> tuple[list[tuple[str, str, str]], list[str], bool]:
    """Generate per-feature UX loop pages from latest user-review artifacts."""
    stage_review_root = repo_root / ".digital-artifacts" / "60-review"
    target_dir = local_wiki_dir / "ux-review-loops"
    target_dir.mkdir(parents=True, exist_ok=True)

    if not stage_review_root.exists():
        return [], [], False

    latest_by_slug: dict[str, Path] = {}
    for stage_dir in stage_review_root.glob(f"*/{stage}"):
        if not stage_dir.is_dir():
            continue
        for candidate in stage_dir.glob("user-review-*.md"):
            slug = _infer_feature_slug_from_review_filename(candidate.name)
            current = latest_by_slug.get(slug)
            if current is None or candidate.stat().st_mtime >= current.stat().st_mtime:
                latest_by_slug[slug] = candidate

    entries: list[tuple[str, str, str]] = []
    asset_paths: list[str] = []
    changed = False

    for slug, source in sorted(latest_by_slug.items()):
        source_text = source.read_text(encoding="utf-8")
        metadata = _parse_frontmatter(source_text)
        composite = metadata.get("composite_score", "n/a")
        recommendation = metadata.get("recommendation", "revise").strip().lower() or "revise"
        iteration = metadata.get("iteration", "n/a")
        try:
            iteration_number = int(str(iteration).strip())
        except ValueError:
            iteration_number = 0
        task_performed = metadata.get("task_performed", "Task not provided")
        design_artifact = metadata.get("design_artifact", "")
        blocking_issues_present = _frontmatter_list_has_items(source_text, "blocking_issues")
        loop_limit_reached = iteration_number >= _MAX_UX_REVIEW_ITERATIONS
        design_name = Path(design_artifact).name if design_artifact else ""
        review_rel_path = f"ux-reviews/{source.name}"
        scribble_rel_path = f"ux-scribbles/{design_name}" if design_name else ""
        has_scribble = bool(design_name and (local_wiki_dir / scribble_rel_path).exists())

        questionnaire_section = _extract_section(source_text, "Interview Questionnaire")
        if not questionnaire_section:
            questionnaire_section = (
                "| Question | Answer |\n"
                "|---|---|\n"
                "| What confused you most? | not provided |\n"
                "| What felt easiest? | not provided |\n"
                "| What should change before next review? | not provided |"
            )

        task_status_recommendation = "done"
        reporting_reason = ""

        if recommendation == "proceed":
            decision_block = "\n".join(
                [
                    "- Decision: proceed",
                    "- Loop status: closed for current feature iteration.",
                    "- Suggested task status: done",
                ]
            )
        elif recommendation == "redesign":
            bug_artifact = repo_root / ".digital-artifacts" / "00-input" / "bugs" / f"ux-{slug}-bug-redesign.md"
            feature_artifact = repo_root / ".digital-artifacts" / "00-input" / "features" / f"ux-{slug}-feat-redesign.md"
            bug_artifact.parent.mkdir(parents=True, exist_ok=True)
            feature_artifact.parent.mkdir(parents=True, exist_ok=True)
            if not bug_artifact.exists():
                bug_artifact.write_text(
                    "\n".join(
                        [
                            f"# UX Redesign Bug: {slug}",
                            "",
                            f"- source_review: .digital-artifacts/60-review/{source.parent.parent.name}/{stage}/{source.name}",
                            f"- recommendation: {recommendation}",
                            f"- composite_score: {composite}",
                            "- action: redesign the current UX approach before next validation round",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            if not feature_artifact.exists():
                feature_artifact.write_text(
                    "\n".join(
                        [
                            f"# UX Redesign Feature: {slug}",
                            "",
                            f"- source_review: .digital-artifacts/60-review/{source.parent.parent.name}/{stage}/{source.name}",
                            f"- recommendation: {recommendation}",
                            "- action: introduce redesigned user flow based on questionnaire findings",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            if loop_limit_reached:
                task_status_recommendation = "blocked"
                reporting_reason = (
                    "Maximal two technical review rounds reached without a validation-ready design. "
                    "Further iteration needs clearer product or medium-specific guidance."
                )
                decision_block = "\n".join(
                    [
                        "- Decision: redesign",
                        "- Loop status: aborted after iteration limit.",
                        "- Suggested task status: blocked",
                        f"- Reporting reason: {reporting_reason}",
                        f"- Suggested intake bug artifact: .digital-artifacts/00-input/bugs/ux-{slug}-bug-redesign.md",
                        f"- Suggested intake feature artifact: .digital-artifacts/00-input/features/ux-{slug}-feat-redesign.md",
                    ]
                )
            else:
                decision_block = "\n".join(
                    [
                        "- Decision: redesign",
                        "- Loop status: continue with a new scribble baseline.",
                        "- Suggested task status: in-progress",
                        f"- Suggested intake bug artifact: .digital-artifacts/00-input/bugs/ux-{slug}-bug-redesign.md",
                        f"- Suggested intake feature artifact: .digital-artifacts/00-input/features/ux-{slug}-feat-redesign.md",
                    ]
                )
        else:
            bug_artifact = repo_root / ".digital-artifacts" / "00-input" / "bugs" / f"ux-{slug}-bug-followup.md"
            feature_artifact = repo_root / ".digital-artifacts" / "00-input" / "features" / f"ux-{slug}-feat-followup.md"
            bug_artifact.parent.mkdir(parents=True, exist_ok=True)
            feature_artifact.parent.mkdir(parents=True, exist_ok=True)
            if not bug_artifact.exists():
                bug_artifact.write_text(
                    "\n".join(
                        [
                            f"# UX Follow-up Bug: {slug}",
                            "",
                            f"- source_review: .digital-artifacts/60-review/{source.parent.parent.name}/{stage}/{source.name}",
                            f"- recommendation: {recommendation}",
                            f"- composite_score: {composite}",
                            "- action: resolve confusion/blocking findings before next UX validation round",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            if not feature_artifact.exists():
                feature_artifact.write_text(
                    "\n".join(
                        [
                            f"# UX Follow-up Feature: {slug}",
                            "",
                            f"- source_review: .digital-artifacts/60-review/{source.parent.parent.name}/{stage}/{source.name}",
                            f"- recommendation: {recommendation}",
                            "- action: deliver UX enhancements raised by user questionnaire answers",
                        ]
                    )
                    + "\n",
                    encoding="utf-8",
                )
            if loop_limit_reached:
                if blocking_issues_present:
                    task_status_recommendation = "blocked"
                    reporting_reason = (
                        "Maximal two technical review rounds reached and blocking issues are still present. "
                        "Further iteration needs clearer product or medium-specific guidance."
                    )
                else:
                    task_status_recommendation = "done"
                    reporting_reason = (
                        "Maximal two technical review rounds reached. Stop the loop, keep the findings, "
                        "and convert remaining UX questions into follow-up backlog items."
                    )
                decision_block = "\n".join(
                    [
                        "- Decision: revise",
                        "- Loop status: aborted after iteration limit.",
                        f"- Suggested task status: {task_status_recommendation}",
                        f"- Reporting reason: {reporting_reason}",
                        f"- Suggested intake bug artifact: .digital-artifacts/00-input/bugs/ux-{slug}-bug-followup.md",
                        f"- Suggested intake feature artifact: .digital-artifacts/00-input/features/ux-{slug}-feat-followup.md",
                    ]
                )
            else:
                decision_block = "\n".join(
                    [
                        "- Decision: revise",
                        "- Loop status: continue with incremental scribble revision.",
                        "- Suggested task status: in-progress",
                        f"- Suggested intake bug artifact: .digital-artifacts/00-input/bugs/ux-{slug}-bug-followup.md",
                        f"- Suggested intake feature artifact: .digital-artifacts/00-input/features/ux-{slug}-feat-followup.md",
                    ]
                )

        loop_content_lines = [
            f"# UX Review Loop: {slug}",
            "",
            "## Current Iteration",
            "",
            f"- Stage: {stage}",
            f"- Iteration: {iteration}",
            f"- Composite score: {composite}",
            f"- Recommendation: {recommendation}",
            f"- User task: {task_performed}",
            f"- Source review: [{source.name}]({review_rel_path})",
        ]
        if has_scribble:
            loop_content_lines.append(f"- Scribble: [{design_name}]({scribble_rel_path})")
        elif design_name:
            loop_content_lines.append(f"- Scribble: {design_name} (not synced to wiki yet)")
        if has_scribble:
            loop_content_lines.extend(
                [
                    "",
                    "## Scribble Snapshot",
                    "",
                    f"<img src=\"{scribble_rel_path}\" alt=\"{design_name}\" style=\"max-width: 820px; width: 100%; height: auto;\" />",
                ]
            )
        loop_content_lines.extend(
            [
                "",
                "## Questionnaire Q/A",
                "",
                questionnaire_section.strip(),
                "",
                "## Loop Decision",
                "",
                decision_block,
                "",
                "## Validation Scope",
                "",
                "- Current layer reviewer: generic `user-standard` persona for early technical UX discovery.",
                "- Purpose: capture likely questions, confusion points, and missing context for a real human UX process.",
                "- Medium-specific expert user agents for web, mobile, voice, or CLI validation belong to later layers.",
            ]
        )
        loop_content = "\n".join(loop_content_lines).rstrip() + "\n"

        loop_filename = f"{slug}-loop.md"
        target = target_dir / loop_filename
        existing_text = target.read_text(encoding="utf-8") if target.exists() else None
        if existing_text != loop_content:
            target.write_text(loop_content, encoding="utf-8")
            changed = True

        rel_path = target.relative_to(local_wiki_dir).as_posix()
        entries.append(
            (
                slug.replace("-", " ").title(),
                rel_path,
                "Loop summary with questionnaire Q/A and rating-based next action.",
            )
        )
        asset_paths.append(rel_path)

    return entries, asset_paths, changed


def _sync_ux_scribble_assets(
    repo_root: Path,
    local_wiki_dir: Path,
) -> tuple[list[tuple[str, str, str]], list[str], bool]:
    """Copy UX scribble SVG assets into docs/wiki and return metadata."""
    source_dir = repo_root / "docs" / "ux" / "scribbles"
    target_dir = local_wiki_dir / "ux-scribbles"
    target_dir.mkdir(parents=True, exist_ok=True)

    if not source_dir.exists():
        return [], [], False

    entries: list[tuple[str, str, str]] = []
    asset_paths: list[str] = []
    changed = False

    for source in sorted(source_dir.glob("*.svg")):
        target = target_dir / source.name
        source_bytes = source.read_bytes()
        existing_bytes = target.read_bytes() if target.exists() else None
        if existing_bytes != source_bytes:
            target.write_bytes(source_bytes)
            changed = True

        rel_path = target.relative_to(local_wiki_dir).as_posix()
        title = source.stem.replace("_", " ").replace("-", " ").title()
        entries.append(
            (
                title,
                rel_path,
                "Scribble used for UX walkthroughs and user-standard review sessions.",
            )
        )
        asset_paths.append(rel_path)

    return entries, asset_paths, changed


def _render_wiki_home_content(
    repo_slug: str,
    stage_title: str,
    stage_page_url: str,
    board_url: str,
    vision: str,
    goals: str,
    constraints: str,
    presentation_link: str = "",
    visualization_entries: list[tuple[str, str, str]] | None = None,
) -> str:
    """Render the wiki Home page as a concise project entry page."""
    def _clean_lines(text: str) -> list[str]:
        blocked_tokens = (
            "define the explicitly included outcomes",
            "define explicit exclusions",
            "criterion 1",
            "criterion 2",
            "criterion 3",
            "todo",
            "no vision available",
            "no goals available",
            "no constraints available",
        )
        seen: set[str] = set()
        cleaned: list[str] = []
        for raw in text.splitlines():
            line = raw.strip()
            if not line:
                continue
            normalized = line.lower()
            if any(token in normalized for token in blocked_tokens):
                continue
            if normalized in {"in scope", "out of scope"}:
                continue
            line = re.sub(r"^(primary finding:|secondary finding:|address:)\s*", "", line, flags=re.IGNORECASE)
            if normalized in seen:
                continue
            seen.add(normalized)
            cleaned.append(line)
        return cleaned

    clean_vision = _clean_lines(vision)
    clean_goals = _clean_lines(goals)
    clean_constraints = _clean_lines(constraints)

    summary_line = (
        clean_vision[0]
        if clean_vision
        else "Project summary is pending completion in the canonical stage page."
    )
    focus_line = clean_goals[0].lstrip("- ").strip() if clean_goals else "Delivery scope is being refined in the stage page."
    guardrail_line = clean_constraints[0].lstrip("- ").strip() if clean_constraints else "Constraints are being maintained in the stage page."
    title = f"{repo_slug} Wiki" if repo_slug else f"{stage_title} Wiki"

    lines = [
        f"# {title}",
        "",
        "This wiki is the entry point for project orientation. Use it to understand where the work stands and where deeper detail lives.",
        "",
        "## Start Here",
        "",
        f"- Active stage: [{stage_title}]({stage_page_url})",
        f"- Board: {board_url or 'Not available'}",
        "",
        "## Stage Snapshot",
        "",
        f"- Summary: {summary_line}",
        f"- Current focus: {focus_line}",
        f"- Guardrail: {guardrail_line}",
        "",
        "## Key Assets",
        "",
        (
            f"- [Download stakeholder presentation]({presentation_link})"
            if presentation_link
            else "- Stakeholder presentation not available yet."
        ),
        "",
        "## Navigation",
        "",
        f"- [{stage_title}]({stage_page_url})",
        "",
    ]
    if visualization_entries:
        lines.extend(["## Visual Guide", ""])
        for title, path, _caption in visualization_entries:
            lines.append(f"- [{title}]({path})")
        lines.append("")
    return "\n".join(lines)


def _local_stage_page_reference(page_slug: str) -> str:
    """Return the relative stage page link used in committed local wiki files."""
    return f"{page_slug}.md"


def _local_board_reference(stage: str) -> str:
    """Return an owner-neutral local board reference for committed wiki files."""
    stage_doc_name = stage.upper()
    return (
        "See the synchronized board metadata in "
        f"[.digital-artifacts/40-stage/{stage_doc_name}.md](../../.digital-artifacts/40-stage/{stage_doc_name}.md)."
    )


def _yaml_quote(value: str) -> str:
    """Return a JSON-style quoted scalar suitable for YAML string values."""
    return json.dumps(value, ensure_ascii=True)


def _append_yaml_list(lines: list[str], key: str, values: list[str]) -> None:
    """Append a simple YAML list field."""
    lines.append(f"{key}:")
    for value in values:
        lines.append(f"  - {_yaml_quote(value)}")


def _build_work_handoff_payload(
    *,
    handoff_id: str,
    from_role: str,
    to_role: str,
    goal: str,
    current_state: dict[str, str],
    assumptions: list[str],
    open_questions: list[str],
    artifacts: list[str],
    expected_outputs: list[str],
    completion_criteria: list[str],
    completed_items: list[str] | None = None,
    remaining_items: list[str] | None = None,
    definition_of_done: list[str] | None = None,
) -> str:
    """Build a work_handoff_v1 YAML payload with trigger-specific fields."""
    lines = [
        "schema: work_handoff_v1",
        f"handoff_id: {_yaml_quote(handoff_id)}",
        f"from_role: {_yaml_quote(from_role)}",
        f"to_role: {_yaml_quote(to_role)}",
        f"goal: {_yaml_quote(goal)}",
        "current_state:",
    ]
    for key, value in current_state.items():
        lines.append(f"  {key}: {_yaml_quote(value)}")
    _append_yaml_list(lines, "expected_outputs", expected_outputs)
    _append_yaml_list(lines, "completion_criteria", completion_criteria)
    if completed_items:
        _append_yaml_list(lines, "completed_items", completed_items)
    if remaining_items:
        _append_yaml_list(lines, "remaining_items", remaining_items)
    _append_yaml_list(lines, "assumptions", assumptions)
    _append_yaml_list(lines, "open_questions", open_questions)
    _append_yaml_list(lines, "artifacts", artifacts)
    if definition_of_done:
        _append_yaml_list(lines, "definition_of_done", definition_of_done)
    return "\n".join(lines) + "\n"


def _resolve_python_executable(repo_root: Path) -> str:
    """Resolve the preferred Python executable for local repository tooling."""
    candidates = [
        repo_root
        / ".digital-runtime"
        / "layers"
        / "python-runtime"
        / "venv"
        / "bin"
        / "python3",
        repo_root / ".digital-runtime" / "layers" / repo_root.name / "bin" / "python3",
    ]
    for candidate in candidates:
        if candidate.exists() and os.access(candidate, os.X_OK):
            return str(candidate)
    return "python3"


def _presentation_handoff_dir(repo_root: Path, stage: str) -> Path:
    """Return the canonical handoff directory for stage presentation work."""
    handoff_dir = repo_root / ".digital-runtime" / "handoffs" / stage
    handoff_dir.mkdir(parents=True, exist_ok=True)
    legacy_dir = repo_root / ".digital-artifacts" / "50-planning" / stage / "handoffs"
    if legacy_dir.exists():
        for legacy_file in legacy_dir.glob("*.y*ml"):
            target = handoff_dir / legacy_file.name
            if legacy_file.is_file():
                if not target.exists():
                    target.write_text(
                        legacy_file.read_text(encoding="utf-8"),
                        encoding="utf-8",
                    )
                legacy_file.unlink(missing_ok=True)
        if legacy_dir.exists() and not any(legacy_dir.iterdir()):
            legacy_dir.rmdir()
    return handoff_dir


def _stakeholder_deck_filename(stage_title: str) -> str:
    """Return canonical stakeholder deck filename for wiki and local storage."""
    return f"{_wiki_page_slug_fs(stage_title)}-Stakeholder-Briefing.pptx"


def _legacy_stakeholder_deck_output_path(repo_root: Path, stage: str) -> Path:
    """Return the legacy deck path used before canonical wiki attachment naming."""
    output_dir = repo_root / "docs" / "wiki" / "assets" / "powerpoint"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / f"{stage}_stakeholder_briefing.pptx"


def _stakeholder_deck_output_path(repo_root: Path, stage_title: str) -> Path:
    """Return canonical output path for the stakeholder presentation deck."""
    output_dir = repo_root / "docs" / "wiki" / "assets" / "powerpoint"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / _stakeholder_deck_filename(stage_title)


def _project_stage_generated_deck_path(repo_root: Path) -> Path:
    """Return the canonical /project-generated deck path used for stakeholder publishing."""
    return repo_root / "docs" / "powerpoints" / f"{repo_root.name}_project.pptx"


def _ensure_stage_stakeholder_presentation(
    repo_root: Path,
    stage: str,
    stage_path: Path,
    stage_title: str,
    board_url: str,
    wiki_url: str,
) -> dict[str, object]:
    """Create handoff artifacts and build a stakeholder deck from the stage doc."""
    handoff_dir = _presentation_handoff_dir(repo_root, stage)
    request_path = handoff_dir / "UX_STAKEHOLDER_DECK_REQUEST.yaml"
    response_path = handoff_dir / "UX_STAKEHOLDER_DECK_RESPONSE.yaml"
    output_path = _stakeholder_deck_output_path(repo_root, stage_title)
    build_script = (
        repo_root
        / ".github"
        / "skills"
        / "powerpoint"
        / "scripts"
        / "build_from_source.py"
    )
    attachment_name = _stakeholder_deck_filename(stage_title)
    legacy_output_path = _legacy_stakeholder_deck_output_path(repo_root, stage)
    canonical_project_deck = _project_stage_generated_deck_path(repo_root)

    request_payload = _build_work_handoff_payload(
        handoff_id=f"{stage}-ux-stakeholder-deck-request",
        from_role="agile-coach",
        to_role="ux-designer",
        goal=(
            "Create a stakeholder-ready PowerPoint presentation from the canonical "
            f"{stage} stage description using the /powerpoint templates. The UX Designer "
            "may add diagrams, flows, and visual scribbles where they improve clarity."
        ),
        current_state={
            "stage": stage,
            "stage_title": stage_title,
            "stage_document": stage_path.as_posix(),
            "board_url": board_url or "not-available",
            "wiki_url": wiki_url or "not-available",
        },
        expected_outputs=[
            "A .pptx stakeholder briefing generated from the canonical stage document.",
            "A UX response handoff that returns the generated deck artifact to agile-coach.",
        ],
        completion_criteria=[
            "The presentation exists as a .pptx artifact in the repository.",
            "The deck is suitable for stakeholder review and summarizes the project in a few slides.",
            "Agile-coach can attach the deck from the response artifact into the wiki Home page.",
        ],
        completed_items=[
            "Canonical stage document exists.",
            "GitHub board/wiki synchronization has been evaluated for the stage.",
        ],
        remaining_items=[
            "Generate the stakeholder deck from the current project description.",
            "Return the deck artifact to agile-coach for wiki embedding.",
        ],
        assumptions=[
            "The canonical stage document is the authoritative project summary.",
            "The PowerPoint skill templates are available in this repository.",
        ],
        open_questions=["none"],
        artifacts=[stage_path.as_posix(), output_path.as_posix()],
        definition_of_done=[
            "Deck file exists and is readable.",
            "Deck can be linked from the wiki Home page and stage page.",
        ],
    )
    request_path.write_text(request_payload, encoding="utf-8")

    if stage == "project" and canonical_project_deck.exists():
        existed_before = output_path.exists()
        source_bytes = canonical_project_deck.read_bytes()
        existing_bytes = output_path.read_bytes() if output_path.exists() else None
        if existing_bytes != source_bytes:
            output_path.write_bytes(source_bytes)
        if legacy_output_path != output_path and legacy_output_path.exists():
            legacy_output_path.unlink()

        response_payload = _build_work_handoff_payload(
            handoff_id=f"{stage}-ux-stakeholder-deck-response",
            from_role="ux-designer",
            to_role="agile-coach",
            goal=(
                "Return the stakeholder-ready PowerPoint deck so agile-coach can attach "
                "it to the wiki Home page and project stage page."
            ),
            current_state={
                "stage": stage,
                "stage_title": stage_title,
                "stage_document": stage_path.as_posix(),
                "presentation_output": output_path.as_posix(),
                "attachment_name": attachment_name,
            },
            expected_outputs=[
                "A repository-local .pptx artifact for stakeholder presentation.",
                "A stable attachment name for the wiki.",
            ],
            completion_criteria=[
                "Agile-coach can copy the deck into the wiki repository and link it from Home.md.",
                "The returned artifact path is deterministic.",
            ],
            completed_items=[
                "Stakeholder deck reused from the canonical /project output.",
                "Deck kept aligned with the /project-generated briefing.",
            ],
            remaining_items=["Attach the deck in the wiki and link it from Home.md."],
            assumptions=[
                "Agile-coach will keep Home.md as the canonical wiki entry point.",
                "Wiki attachment links may reference committed binary files in the wiki repository.",
            ],
            open_questions=["none"],
            artifacts=[request_path.as_posix(), output_path.as_posix()],
            definition_of_done=[
                "Deck is committed or ready to commit as a wiki attachment.",
                "Home.md can link to the attachment by deterministic file name.",
            ],
        )
        response_path.write_text(response_payload, encoding="utf-8")

        return {
            "status": "updated" if existed_before else "created",
            "message": "stakeholder deck reused from canonical /project output",
            "request_handoff": request_path.as_posix(),
            "response_handoff": response_path.as_posix(),
            "output_path": output_path.as_posix(),
            "attachment_name": attachment_name,
        }

    if not build_script.exists():
        return {
            "status": "manual-required",
            "message": "powerpoint build script not found",
            "request_handoff": request_path.as_posix(),
            "response_handoff": response_path.as_posix(),
            "output_path": output_path.as_posix(),
            "attachment_name": attachment_name,
        }

    existed_before = output_path.exists()
    python_exec = _resolve_python_executable(repo_root)
    ok, command_output = _run_local_command(
        [
            python_exec,
            str(build_script),
            "--repo-root",
            str(repo_root),
            "--layer",
            repo_root.name,
            "--source",
            str(stage_path),
            "--output",
            str(output_path),
        ],
        repo_root,
        os.environ.copy(),
    )
    if not ok or not output_path.exists():
        return {
            "status": "manual-required",
            "message": command_output or "powerpoint build failed",
            "request_handoff": request_path.as_posix(),
            "response_handoff": response_path.as_posix(),
            "output_path": output_path.as_posix(),
            "attachment_name": attachment_name,
        }

    if legacy_output_path != output_path and legacy_output_path.exists():
        legacy_output_path.unlink()

    response_payload = _build_work_handoff_payload(
        handoff_id=f"{stage}-ux-stakeholder-deck-response",
        from_role="ux-designer",
        to_role="agile-coach",
        goal=(
            "Return the stakeholder-ready PowerPoint deck so agile-coach can attach "
            "it to the wiki Home page and project stage page."
        ),
        current_state={
            "stage": stage,
            "stage_title": stage_title,
            "stage_document": stage_path.as_posix(),
            "presentation_output": output_path.as_posix(),
            "attachment_name": attachment_name,
        },
        expected_outputs=[
            "A repository-local .pptx artifact for stakeholder presentation.",
            "A stable attachment name for the wiki.",
        ],
        completion_criteria=[
            "Agile-coach can copy the deck into the wiki repository and link it from Home.md.",
            "The returned artifact path is deterministic.",
        ],
        completed_items=[
            "Stakeholder deck generated with the PowerPoint skill.",
            "Deck kept suitable for stakeholder presentation in a few slides.",
        ],
        remaining_items=["Attach the deck in the wiki and link it from Home.md."],
        assumptions=[
            "Agile-coach will keep Home.md as the canonical wiki entry point.",
            "Wiki attachment links may reference committed binary files in the wiki repository.",
        ],
        open_questions=["none"],
        artifacts=[request_path.as_posix(), output_path.as_posix()],
        definition_of_done=[
            "Deck is committed or ready to commit as a wiki attachment.",
            "Home.md can link to the attachment by deterministic file name.",
        ],
    )
    response_path.write_text(response_payload, encoding="utf-8")

    return {
        "status": "updated" if existed_before else "created",
        "message": "stakeholder deck generated",
        "request_handoff": request_path.as_posix(),
        "response_handoff": response_path.as_posix(),
        "output_path": output_path.as_posix(),
        "attachment_name": attachment_name,
    }


def _update_stage_doc_metadata(stage_path: Path, updates: dict[str, str]) -> None:
    """Update selected frontmatter scalar values in the stage document."""
    text = stage_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return
    lines = text.splitlines()
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            break
        key, _, _value = line.partition(":")
        normalized_key = key.strip()
        if normalized_key in updates:
            lines[index] = f'{normalized_key}: "{updates[normalized_key]}"'
    stage_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _render_stage_wiki_content(
    repo_root: Path, stage: str, stage_path: Path, board_url: str
) -> tuple[str, str]:
    """Render wiki page title and content from stage document and template."""
    stage_text = stage_path.read_text(encoding="utf-8")
    stage_title = _first_heading(stage_text) or stage.title()
    updated = datetime.fromtimestamp(
        stage_path.stat().st_mtime, tz=timezone.utc
    ).strftime("%Y-%m-%d")
    template_path = (
        repo_root
        / ".github"
        / "skills"
        / "stages-action"
        / "templates"
        / "wiki-stage-page.md"
    )
    template_text = template_path.read_text(encoding="utf-8")
    vision = _clean_stage_summary_lines(_extract_section(stage_text, "Vision")) or "Project summary is being refined."
    goals = _clean_stage_summary_lines(_extract_section(stage_text, "Goals")) or "- Delivery focus is being refined."
    constraints = (
        _clean_stage_summary_lines(_extract_section(stage_text, "Constraints")) or "- Constraints are being maintained."
    )
    content = _render_template(
        template_text,
        {
            "stage_title": stage_title,
            "stage": stage,
            "status": "active",
            "date": updated,
            "vision": vision,
            "goals": goals,
            "constraints": constraints,
            "board_url": board_url or "Not available",
            "updated": updated,
        },
    )
    return stage_title, content


def _git_credentials_env(token: str) -> dict[str, str]:
    """Build env suitable for authenticated git operations without persisting credentials."""
    env = os.environ.copy()
    env["GIT_ASKPASS"] = "echo"
    env["GIT_TERMINAL_PROMPT"] = "0"
    env["GH_TOKEN"] = token
    env["GITHUB_TOKEN"] = token
    return env


def _run_git(args: list[str], cwd: Path, env: dict[str, str]) -> tuple[bool, str]:
    """Execute git with token-based HTTP authentication injected as a header."""
    import base64 as _base64

    auth_value = _base64.b64encode(
        f"x-access-token:{env['GH_TOKEN']}".encode()
    ).decode()
    full_args = [
        "git",
        "-c",
        f"http.extraHeader=Authorization: Basic {auth_value}",
        *args,
    ]
    try:
        completed = subprocess.run(
            full_args, check=False, text=True, capture_output=True, cwd=cwd, env=env
        )
    except OSError as exc:
        return False, str(exc)
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    return completed.returncode == 0, output


def _wiki_page_slug_fs(title: str) -> str:
    """Convert page title to filesystem-safe wiki filename slug."""
    return "".join(
        ch if ch.isalnum() or ch in {"-", "_"} else "-" for ch in title
    ).strip("-")


def ensure_stage_wiki(
    repo_root: Path, stage: str, stage_path: Path, board_url: str = ""
) -> dict[str, object]:
    """Ensure repository wiki exists and sync the stage page from the canonical stage doc."""
    repo_slug, owner, repo_name = _resolve_repo_context(repo_root)
    page_title, page_content = _render_stage_wiki_content(
        repo_root, stage, stage_path, board_url
    )
    page_slug = _wiki_page_slug_fs(page_title)
    local_wiki_dir = repo_root / "docs" / "wiki"
    local_wiki_dir.mkdir(parents=True, exist_ok=True)
    local_stage_file = local_wiki_dir / f"{page_slug}.md"
    local_home_file = local_wiki_dir / "Home.md"
    remote_stage_page_url = (
        _wiki_page_url(repo_slug, page_title)
        if repo_slug
        else f"docs/wiki/{page_slug}.md"
    )
    local_stage_page_url = _local_stage_page_reference(page_slug)
    planning_hierarchy_lines = _planning_hierarchy_lines(repo_root, stage)
    visualization_entries, visualization_assets, local_visualization_changed = _sync_visualization_assets(
        repo_root,
        local_wiki_dir,
        stage,
    )
    ux_review_entries, ux_review_assets, local_ux_reviews_changed = _sync_ux_review_assets(
        repo_root,
        local_wiki_dir,
        stage,
    )
    ux_loop_entries, ux_loop_assets, local_ux_loops_changed = _sync_ux_review_loop_pages(
        repo_root,
        local_wiki_dir,
        stage,
    )
    _ux_scribble_entries, ux_scribble_assets, local_ux_scribbles_changed = _sync_ux_scribble_assets(
        repo_root,
        local_wiki_dir,
    )

    presentation = _ensure_stage_stakeholder_presentation(
        repo_root,
        stage,
        stage_path,
        page_title,
        board_url,
        remote_stage_page_url,
    )

    stage_text = stage_path.read_text(encoding="utf-8")
    presentation_link = str(presentation.get("attachment_name", ""))
    remote_home_content = _render_wiki_home_content(
        repo_slug=repo_slug,
        stage_title=page_title,
        stage_page_url=remote_stage_page_url,
        board_url=board_url,
        vision=_clean_stage_summary_lines(_extract_section(stage_text, "Vision")) or "Project summary is being refined.",
        goals=_clean_stage_summary_lines(_extract_section(stage_text, "Goals")) or "- Delivery focus is being refined.",
        constraints=_clean_stage_summary_lines(_extract_section(stage_text, "Constraints"))
        or "- Constraints are being maintained.",
        presentation_link=presentation_link,
        visualization_entries=visualization_entries,
    )
    local_home_content = _render_wiki_home_content(
        repo_slug="",
        stage_title=page_title,
        stage_page_url=local_stage_page_url,
        board_url=_local_board_reference(stage),
        vision=_clean_stage_summary_lines(_extract_section(stage_text, "Vision")) or "Project summary is being refined.",
        goals=_clean_stage_summary_lines(_extract_section(stage_text, "Goals")) or "- Delivery focus is being refined.",
        constraints=_clean_stage_summary_lines(_extract_section(stage_text, "Constraints"))
        or "- Constraints are being maintained.",
        presentation_link=presentation_link,
        visualization_entries=visualization_entries,
    )

    remote_page_content = page_content
    local_page_content = _render_stage_wiki_content(
        repo_root,
        stage,
        stage_path,
        _local_board_reference(stage),
    )[1]

    if planning_hierarchy_lines:
        remote_page_content = (
            remote_page_content.rstrip()
            + "\n\n## Planning Snapshot\n\n"
            + "\n".join(planning_hierarchy_lines)
        )
        local_page_content = (
            local_page_content.rstrip()
            + "\n\n## Planning Snapshot\n\n"
            + "\n".join(planning_hierarchy_lines)
        )

    stage_visualization_lines = _build_stage_visualization_lines(visualization_entries)
    if stage_visualization_lines:
        remote_page_content = (
            remote_page_content.rstrip()
            + "\n\n"
            + "\n".join(stage_visualization_lines)
        )
        local_page_content = (
            local_page_content.rstrip()
            + "\n\n"
            + "\n".join(stage_visualization_lines)
        )

    if ux_review_entries:
        ux_lines = ["## UX Investigations", ""]
        ux_lines.extend(
            [f"- [{title}]({path}) - {description}" for title, path, description in ux_review_entries]
        )
        remote_page_content = remote_page_content.rstrip() + "\n\n" + "\n".join(ux_lines) + "\n"
        local_page_content = local_page_content.rstrip() + "\n\n" + "\n".join(ux_lines) + "\n"

    if ux_loop_entries:
        loop_lines = ["## UX Review Loops", ""]
        loop_lines.extend(
            [f"- [{title}]({path}) - {description}" for title, path, description in ux_loop_entries]
        )
        remote_page_content = remote_page_content.rstrip() + "\n\n" + "\n".join(loop_lines) + "\n"
        local_page_content = local_page_content.rstrip() + "\n\n" + "\n".join(loop_lines) + "\n"

    if presentation_link:
        remote_page_content = (
            remote_page_content.rstrip()
            + "\n\n## Stakeholder Briefing\n\n"
            + f"- [Download stakeholder presentation]({presentation_link})\n"
        )
        local_page_content = (
            local_page_content.rstrip()
            + "\n\n## Stakeholder Briefing\n\n"
            + f"- [Download stakeholder presentation]({presentation_link})\n"
        )

    local_attachment_changed = False
    if presentation_link and str(presentation.get("output_path", "")):
        source_attachment = Path(str(presentation.get("output_path", "")))
        target_attachment = local_wiki_dir / "assets" / "powerpoint" / presentation_link
        target_attachment.parent.mkdir(parents=True, exist_ok=True)
        if source_attachment.exists():
            source_bytes = source_attachment.read_bytes()
            existing_bytes = (
                target_attachment.read_bytes() if target_attachment.exists() else None
            )
            if existing_bytes != source_bytes:
                target_attachment.write_bytes(source_bytes)
                local_attachment_changed = True
        legacy_attachment = local_wiki_dir / "assets" / "powerpoint" / f"{stage}_stakeholder_briefing.pptx"
        if legacy_attachment != target_attachment and legacy_attachment.exists():
            legacy_attachment.unlink()
            local_attachment_changed = True

    existing_local_content = (
        local_stage_file.read_text(encoding="utf-8")
        if local_stage_file.exists()
        else None
    )
    existing_local_home_content = (
        local_home_file.read_text(encoding="utf-8") if local_home_file.exists() else None
    )
    local_stage_changed = existing_local_content != local_page_content
    local_home_changed = existing_local_home_content != local_home_content

    if local_stage_changed:
        local_stage_file.write_text(local_page_content, encoding="utf-8")
    if local_home_changed:
        local_home_file.write_text(local_home_content, encoding="utf-8")

    token, source = _resolve_github_token()
    if not token or not repo_slug or not owner or not repo_name:
        local_changed = (
            local_stage_changed
            or local_home_changed
            or local_attachment_changed
            or local_visualization_changed
            or local_ux_reviews_changed
            or local_ux_loops_changed
            or local_ux_scribbles_changed
        )
        return {
            "status": "updated" if local_changed else "unchanged",
            "message": "local wiki updated; github wiki sync skipped",
            "url": remote_stage_page_url,
            "auth_source": source or "",
            "presentation": presentation,
        }

    repo_env = _build_gh_env(token)
    repo_ok, repo_output = _run_gh_command(
        ["gh", "api", f"repos/{repo_slug}"],
        repo_env,
    )
    if repo_ok:
        try:
            repo_payload = json.loads(repo_output)
        except json.JSONDecodeError:
            repo_payload = {}
        has_wiki = bool(repo_payload.get("has_wiki", False)) if isinstance(repo_payload, dict) else False
        if not has_wiki:
            ok_enable, enable_out = _run_gh_command(
                [
                    "gh",
                    "api",
                    f"repos/{repo_slug}",
                    "--field",
                    "has_wiki=true",
                    "--method",
                    "PATCH",
                ],
                repo_env,
            )
            if not ok_enable:
                return {
                    "status": "manual-required",
                    "message": enable_out or "unable to enable repository wiki",
                    "url": remote_stage_page_url,
                    "auth_source": source or "",
                    "presentation": presentation,
                }

    wiki_remote = f"https://github.com/{repo_slug}.wiki.git"
    wiki_cache_root = repo_root / ".digital-runtime" / "github" / "wiki-cache"
    wiki_cache_root.mkdir(parents=True, exist_ok=True)
    wiki_dir = wiki_cache_root / repo_slug.replace("/", "_")
    git_env = _git_credentials_env(token)

    if not (wiki_dir / ".git").exists():
        ok, clone_out = _run_git(
            ["clone", wiki_remote, str(wiki_dir)], wiki_cache_root, git_env
        )
        if not ok:
            ok_enable, enable_out = _run_gh_command(
                [
                    "gh",
                    "api",
                    f"repos/{repo_slug}",
                    "--field",
                    "has_wiki=true",
                    "--method",
                    "PATCH",
                ],
                repo_env,
            )
            if not ok_enable:
                return {
                    "status": "manual-required",
                    "message": enable_out or "unable to enable repository wiki",
                    "url": remote_stage_page_url,
                    "auth_source": source or "",
                    "presentation": presentation,
                }

            ok, clone_out = _run_git(
                ["clone", wiki_remote, str(wiki_dir)], wiki_cache_root, git_env
            )
            if not ok:
                return {
                    "status": "manual-required",
                    "message": clone_out or "wiki clone failed",
                    "url": remote_stage_page_url,
                    "auth_source": source or "",
                    "presentation": presentation,
                }
    else:
        _run_git(["-C", str(wiki_dir), "pull", "--rebase"], wiki_cache_root, git_env)

    page_file = wiki_dir / f"{page_slug}.md"
    home_file = wiki_dir / "Home.md"

    attachment_changed = False
    if presentation_link:
        source_attachment = local_wiki_dir / "assets" / "powerpoint" / presentation_link
        target_attachment = wiki_dir / presentation_link
        if source_attachment.exists():
            source_bytes = source_attachment.read_bytes()
            existing_bytes = (
                target_attachment.read_bytes() if target_attachment.exists() else None
            )
            if existing_bytes != source_bytes:
                target_attachment.write_bytes(source_bytes)
                attachment_changed = True
        legacy_attachment = wiki_dir / f"{stage}_stakeholder_briefing.pptx"
        if legacy_attachment != target_attachment and legacy_attachment.exists():
            legacy_attachment.unlink()
            attachment_changed = True

    visualization_changed = False
    for relative_asset in visualization_assets:
        source_asset = local_wiki_dir / relative_asset
        target_asset = wiki_dir / relative_asset
        target_asset.parent.mkdir(parents=True, exist_ok=True)
        if not source_asset.exists():
            continue
        source_bytes = source_asset.read_bytes()
        existing_bytes = target_asset.read_bytes() if target_asset.exists() else None
        if existing_bytes != source_bytes:
            target_asset.write_bytes(source_bytes)
            visualization_changed = True

    ux_reviews_changed = False
    for relative_asset in ux_review_assets:
        source_asset = local_wiki_dir / relative_asset
        target_asset = wiki_dir / relative_asset
        target_asset.parent.mkdir(parents=True, exist_ok=True)
        if not source_asset.exists():
            continue
        source_text = source_asset.read_text(encoding="utf-8")
        existing_text = target_asset.read_text(encoding="utf-8") if target_asset.exists() else None
        if existing_text != source_text:
            target_asset.write_text(source_text, encoding="utf-8")
            ux_reviews_changed = True

    ux_loops_changed = False
    for relative_asset in ux_loop_assets:
        source_asset = local_wiki_dir / relative_asset
        target_asset = wiki_dir / relative_asset
        target_asset.parent.mkdir(parents=True, exist_ok=True)
        if not source_asset.exists():
            continue
        source_text = source_asset.read_text(encoding="utf-8")
        existing_text = target_asset.read_text(encoding="utf-8") if target_asset.exists() else None
        if existing_text != source_text:
            target_asset.write_text(source_text, encoding="utf-8")
            ux_loops_changed = True

    ux_scribbles_changed = False
    for relative_asset in ux_scribble_assets:
        source_asset = local_wiki_dir / relative_asset
        target_asset = wiki_dir / relative_asset
        target_asset.parent.mkdir(parents=True, exist_ok=True)
        if not source_asset.exists():
            continue
        source_bytes = source_asset.read_bytes()
        existing_bytes = target_asset.read_bytes() if target_asset.exists() else None
        if existing_bytes != source_bytes:
            target_asset.write_bytes(source_bytes)
            ux_scribbles_changed = True

    existing_content = (
        page_file.read_text(encoding="utf-8") if page_file.exists() else None
    )
    existing_home_content = (
        home_file.read_text(encoding="utf-8") if home_file.exists() else None
    )

    stage_changed = existing_content != remote_page_content
    home_changed = existing_home_content != remote_home_content
    if (
        not stage_changed
        and not home_changed
        and not attachment_changed
        and not visualization_changed
        and not ux_reviews_changed
        and not ux_loops_changed
        and not ux_scribbles_changed
    ):
        return {
            "status": "unchanged",
            "message": "wiki pages already up to date",
            "url": _wiki_page_url(repo_slug, page_title),
            "auth_source": source or "",
            "presentation": presentation,
        }

    action = "created" if (existing_content is None and stage_changed) else "updated"
    page_file.write_text(remote_page_content, encoding="utf-8")
    home_file.write_text(remote_home_content, encoding="utf-8")

    _run_git(
        ["-C", str(wiki_dir), "config", "user.name", "agile-coach-bot"],
        wiki_cache_root,
        git_env,
    )
    _run_git(
        [
            "-C",
            str(wiki_dir),
            "config",
            "user.email",
            "agile-coach-bot@users.noreply.github.com",
        ],
        wiki_cache_root,
        git_env,
    )
    add_args = ["-C", str(wiki_dir), "add", f"{page_slug}.md", "Home.md"]
    if presentation_link:
        add_args.append(presentation_link)
    add_args.extend(visualization_assets)
    add_args.extend(ux_review_assets)
    add_args.extend(ux_loop_assets)
    add_args.extend(ux_scribble_assets)
    _run_git(add_args, wiki_cache_root, git_env)
    ok_commit, commit_out = _run_git(
        [
            "-C",
            str(wiki_dir),
            "commit",
            "-m",
            f"{action.title()} wiki pages: {page_title} + Home",
        ],
        wiki_cache_root,
        git_env,
    )
    if not ok_commit:
        return {
            "status": "manual-required",
            "message": commit_out or "git commit failed",
            "url": _wiki_page_url(repo_slug, page_title),
            "auth_source": source or "",
            "presentation": presentation,
        }

    ok_push, push_out = _run_git(
        ["-C", str(wiki_dir), "push", "--set-upstream", "origin", "main"],
        wiki_cache_root,
        git_env,
    )
    if not ok_push:
        ok_push, push_out = _run_git(
            ["-C", str(wiki_dir), "push", "--set-upstream", "origin", "master"],
            wiki_cache_root,
            git_env,
        )
    if not ok_push:
        ok_push, push_out = _run_git(
            ["-C", str(wiki_dir), "push"], wiki_cache_root, git_env
        )
    if not ok_push:
        return {
            "status": "manual-required",
            "message": push_out or "wiki push failed",
            "url": _wiki_page_url(repo_slug, page_title),
            "auth_source": source or "",
            "presentation": presentation,
        }

    return {
        "status": action,
        "message": f"wiki page {action}",
        "url": _wiki_page_url(repo_slug, page_title),
        "auth_source": source or "",
        "presentation": presentation,
    }


def ensure_stage_primary_assets(
    repo_root: Path, stage: str, stage_path: Path
) -> dict[str, object]:
    """Ensure primary-system project and wiki assets exist for a stage."""
    if not _is_primary_sync_enabled():
        updates = {
            "board_id": "",
            "board_url": "",
            "wiki_url": "",
        }
        _update_stage_doc_metadata(stage_path, updates)
        return {
            "project": {
                "status": "skipped",
                "message": "primary sync disabled by DIGITAL_STAGE_PRIMARY_SYNC",
                "owner": "",
                "repo_slug": "",
                "number": "",
                "url": "",
                "title": "",
                "auth_source": "",
            },
            "wiki": {
                "status": "skipped",
                "message": "primary sync disabled by DIGITAL_STAGE_PRIMARY_SYNC",
                "url": "",
                "auth_source": "",
            },
            "presentation": {},
            "repo_slug": "",
            "owner": "",
        }

    project = ensure_github_project(repo_root, stage)
    wiki = ensure_stage_wiki(repo_root, stage, stage_path, str(project.get("url", "")))

    updates = {
        "board_id": str(project.get("number", "")),
        "board_url": str(project.get("url", "")),
        "wiki_url": str(wiki.get("url", "")),
    }
    _update_stage_doc_metadata(stage_path, updates)

    return {
        "project": project,
        "wiki": wiki,
        "presentation": wiki.get("presentation", {}),
        "repo_slug": str(project.get("repo_slug", "")),
        "owner": str(project.get("owner", "")),
    }


def _artifact_marker(
    stage: str, bundle_key: str, kind: str, board_ticket_id: str
) -> str:
    """Build stable hidden marker for primary-system issue reconciliation."""
    return f"<!-- artifact-sync: stage={stage}; bundle={bundle_key}; kind={kind}; board_ticket={board_ticket_id} -->"


def _artifact_issue_title(
    kind: str,
    artifact_text: str,
    bundle_key: str,
    stage: str,
    board_ticket_id: str,
) -> str:
    """Derive deterministic issue title from artifact content."""
    metadata = _parse_frontmatter(artifact_text)
    summary = metadata.get("title", "").strip()
    if summary:
        return f"{stage.title()} | {board_ticket_id}: {summary}"[:120]

    for raw_line in artifact_text.splitlines():
        line = raw_line.strip().lstrip("#").strip()
        if not line:
            continue
        if line in {"---", "```yaml", "```"}:
            continue
        lower = line.lower()
        prefixes = ("epic ", "story ", "task ", "bug ")
        if lower.startswith(prefixes):
            parts = line.split(" ", 1)
            if len(parts) == 2 and parts[1].strip():
                summary = parts[1].strip()
                break
        summary = line
        break
    if not summary:
        summary = f"{kind.title()} {bundle_key}"
    return f"{stage.title()} | {board_ticket_id}: {summary}"[:120]


def _issue_parent_hint(kind: str, stage: str, bundle_key: str, artifact_text: str) -> str:
    """Return readable hierarchy hint for issue descriptions."""
    metadata = _parse_frontmatter(artifact_text)
    parent_epic = metadata.get("parent_epic", "").strip()
    parent_story = metadata.get("parent_story", "").strip()
    prefix = (stage.strip()[:3] or "stg").upper()
    item_code = bundle_key.split("/")[-1]
    epic = f"{prefix}-{item_code}-EPIC"
    story = f"{prefix}-{item_code}-STORY"
    if kind == "epic":
        return "Hierarchy: Epic (top-level planning container)"
    if kind == "story":
        return f"Hierarchy: Story under Epic {parent_epic or epic}"
    if kind == "task":
        return f"Hierarchy: Task under Story {parent_story or story}"
    if kind == "bug":
        if parent_story:
            return f"Hierarchy: Bug linked to Story {parent_story} (Epic {parent_epic or epic})"
        return f"Hierarchy: Bug linked to Epic {parent_epic or epic}"
    return "Hierarchy: Planning item"


def _issue_body(
    marker: str,
    artifact_text: str,
    board_ticket_id: str,
    *,
    stage: str,
    kind: str,
    bundle_key: str,
    assignee_hint: str = "",
    artifact_status: str = "",
) -> str:
    """Build issue body containing stable marker and artifact content."""
    cleaned_content = _strip_frontmatter(artifact_text)
    hierarchy = _issue_parent_hint(kind, stage, bundle_key, artifact_text)
    effective_owner = "agile-coach" if kind in {"epic", "story"} else (assignee_hint or "fullstack-engineer")

    def _section_lines(*headings: str) -> list[str]:
        collected: list[str] = []
        for heading in headings:
            section = _extract_section(cleaned_content, heading)
            if not section:
                continue
            for raw in section.splitlines():
                line = raw.strip().lstrip("-* ").strip()
                if not line:
                    continue
                lower = line.lower()
                if any(
                    token in lower
                    for token in (
                        "references:",
                        ".digital-artifacts/",
                        "interne entwickler",
                        "der primäre zugang",
                        "source specifications",
                        "stakeholder map",
                    )
                ):
                    continue
                line = line.replace("**", "").replace("`", "").strip()
                if line:
                    collected.append(line)
        return collected

    def _section_checklist(*headings: str) -> list[str]:
        checklist: list[str] = []
        for heading in headings:
            section = _extract_section(cleaned_content, heading)
            if not section:
                continue
            for raw in section.splitlines():
                line = raw.strip()
                if re.match(r"^- \[[ xX]\] ", line):
                    checklist.append(line)
        deduped: list[str] = []
        seen: set[str] = set()
        for item in checklist:
            key = item.lower()
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        return deduped

    summary_lines = (
        _section_lines("Description", "Outcome", "User Story")[:4]
        or ["Approved implementation scope ready for execution."]
    )
    deduped_summary: list[str] = []
    seen_summary: set[str] = set()
    for line in summary_lines:
        normalized = line.strip().rstrip(".").lower()
        if normalized in seen_summary:
            continue
        seen_summary.add(normalized)
        deduped_summary.append(line)
    summary_lines = deduped_summary
    readiness_lines = _section_lines("Success Signals", "Readiness Signals", "Acceptance Criteria")[:4]
    checklist_lines = _section_checklist(
        "Acceptance Criteria",
        "Execution plan",
        "Verification plan",
        "Definition of Done",
    )
    normalized_status = artifact_status.strip().lower()
    if normalized_status in {"done", "complete", "completed", "closed"}:
        checklist_lines = [
            re.sub(r"^- \[[ xX]\] ", "- [x] ", item) for item in checklist_lines
        ]
    meta_block = "\n".join(
        [
            "```yaml",
            f'bundle: "{bundle_key}"',
            f'board_ticket: "{board_ticket_id}"',
            'source_of_truth: "project wiki + task board ticket"',
            "```",
        ]
    )
    blocks = [
        marker,
        "## Delivery Metadata",
        meta_block,
        f"- Board ticket: {board_ticket_id or 'meta-item'}",
        f"- {hierarchy}",
        f"- Suggested owner role: {effective_owner}",
        f"- Artifact status: {artifact_status or 'unknown'}",
    ]
    if kind in {"epic", "story"}:
        blocks.extend(
            [
                "## Planning Summary",
                "\n".join(f"- {line}" for line in summary_lines),
            ]
        )
        if readiness_lines:
            blocks.extend(
                [
                    "## Readiness Signals",
                    "\n".join(f"- {line}" for line in readiness_lines),
                ]
            )
        blocks.append("Meta issue: governance and planning only; execution is delegated to child delivery items.")
    else:
        execution_lines = summary_lines[:2] if kind == "bug" else summary_lines
        blocks.extend(
            [
                "## Execution Brief",
                "\n".join(f"- {line}" for line in execution_lines),
                "Definition of done: deliver the approved task scope with tests and review-ready evidence.",
            ]
        )
        if checklist_lines:
            blocks.extend(
                [
                    "## Progress Checklist",
                    "\n".join(checklist_lines[:8]),
                ]
            )
    return "\n\n".join(blocks) + "\n"


def _is_done_like_status(status: str) -> bool:
    """Return True when a planning artifact status represents completed work."""
    return status.strip().lower() in {"done", "complete", "completed", "closed"}


def _sync_issue_state_with_artifact_status(
    repo_slug: str,
    issue_number: str,
    artifact_status: str,
    current_issue_state: str,
    env: dict[str, str],
) -> str:
    """Keep GitHub issue open/closed state aligned with planning artifact status."""
    state = current_issue_state.strip().lower()
    target_closed = _is_done_like_status(artifact_status)

    if target_closed and state != "closed":
        ok, output = _run_gh_command(
            [
                "gh",
                "issue",
                "close",
                issue_number,
                "--repo",
                repo_slug,
                "--comment",
                "Closed automatically because planning artifact status is done.",
            ],
            env,
        )
        return "closed" if ok else f"manual-required:{output or 'unable to close issue'}"

    if (not target_closed) and state == "closed":
        ok, output = _run_gh_command(
            ["gh", "issue", "reopen", issue_number, "--repo", repo_slug],
            env,
        )
        return "reopened" if ok else f"manual-required:{output or 'unable to reopen issue'}"

    return "unchanged"


def _list_github_issues(repo_slug: str, env: dict[str, str]) -> list[dict[str, object]]:
    """Return all relevant issues for matching markers."""
    ok, output = _run_gh_command(
        [
            "gh",
            "issue",
            "list",
            "--repo",
            repo_slug,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,url,body,state",
        ],
        env,
    )
    if not ok:
        return []
    try:
        return _extract_issues(json.loads(output))
    except json.JSONDecodeError:
        return []


def _list_stage_sync_issues(
    repo_slug: str, stage: str, env: dict[str, str]
) -> list[dict[str, object]]:
    """Return artifact-synced issues belonging to one stage."""
    marker_prefix = f"<!-- artifact-sync: stage={stage};"
    return [
        issue
        for issue in _list_github_issues(repo_slug, env)
        if marker_prefix in str(issue.get("body", ""))
    ]


def _delete_or_close_issue(
    repo_slug: str, issue_number: str, env: dict[str, str]
) -> str:
    """Delete a GitHub issue when possible, otherwise close it as fallback."""
    ok, output = _run_gh_command(
        [
            "gh",
            "api",
            "-X",
            "DELETE",
            f"repos/{repo_slug}/issues/{issue_number}",
        ],
        env,
    )
    if ok:
        return "deleted"

    close_ok, close_output = _run_gh_command(
        [
            "gh",
            "issue",
            "close",
            issue_number,
            "--repo",
            repo_slug,
            "--comment",
            "Closed by DRY_RUN=2 stage cleanup before deterministic regeneration.",
        ],
        env,
    )
    if close_ok:
        return "closed"
    return f"manual-required:{close_output or output or 'unable to delete or close issue'}"


def _delete_or_close_stage_project(
    owner: str, project: dict[str, object], env: dict[str, str]
) -> str:
    """Delete a GitHub project when possible, otherwise close it as fallback."""
    project_id = str(project.get("id", "")).strip()
    project_number = str(project.get("number", "")).strip()

    if project_id:
        ok, output = _run_gh_command(
            [
                "gh",
                "api",
                "graphql",
                "-f",
                "query=mutation($projectId:ID!){deleteProjectV2(input:{projectId:$projectId}){clientMutationId}}",
                "-F",
                f"projectId={project_id}",
            ],
            env,
        )
        if ok:
            return "deleted"
    else:
        output = ""

    if project_number:
        close_ok, close_output = _run_gh_command(
            [
                "gh",
                "project",
                "close",
                project_number,
                "--owner",
                owner,
            ],
            env,
        )
        if close_ok:
            return "closed"
        output = close_output or output

    return f"manual-required:{output or 'unable to delete or close project'}"


def cleanup_stage_primary_assets(repo_root: Path, stage: str) -> dict[str, object]:
    """Remove GitHub stage assets so DRY_RUN=2 can regenerate from a clean slate."""
    token, source = _resolve_github_token()
    repo_slug, owner, repo_name = _resolve_repo_context(repo_root)
    if not token or not repo_slug or not owner:
        return {
            "status": "manual-required",
            "message": "github cleanup unavailable",
            "project": "manual-required",
            "wiki": "manual-required",
            "issues": {},
            "auth_source": source or "",
        }

    env = _build_gh_env(token)
    issue_statuses: dict[str, str] = {}
    for issue in _list_stage_sync_issues(repo_slug, stage, env):
        issue_number = str(issue.get("number", "")).strip()
        issue_title = str(issue.get("title", "")).strip() or issue_number
        if not issue_number:
            continue
        issue_statuses[issue_title] = _delete_or_close_issue(repo_slug, issue_number, env)

    project = _find_stage_project(owner, stage, repo_name, env)
    project_status = (
        _delete_or_close_stage_project(owner, project, env)
        if project is not None
        else "not-found"
    )

    wiki_ok, wiki_output = _run_gh_command(
        [
            "gh",
            "api",
            "-X",
            "PATCH",
            f"repos/{repo_slug}",
            "-f",
            "has_wiki=false",
        ],
        env,
    )
    wiki_status = "deleted" if wiki_ok else f"manual-required:{wiki_output or 'unable to disable wiki'}"

    wiki_cache_dir = _wiki_cache_dir(repo_root, repo_slug)
    if wiki_cache_dir.exists():
        for path in sorted(wiki_cache_dir.rglob("*"), reverse=True):
            if path.is_file() or path.is_symlink():
                path.unlink(missing_ok=True)
            elif path.is_dir():
                path.rmdir()
        wiki_cache_dir.rmdir()

    overall_status = "cleaned"
    if project_status.startswith("manual-required") or wiki_status.startswith("manual-required"):
        overall_status = "partial"
    elif any(status.startswith("manual-required") for status in issue_statuses.values()):
        overall_status = "partial"

    return {
        "status": overall_status,
        "message": "github stage assets cleaned before regeneration",
        "project": project_status,
        "wiki": wiki_status,
        "issues": issue_statuses,
        "auth_source": source or "",
    }


def _find_issue_by_marker(
    repo_slug: str, marker: str, env: dict[str, str]
) -> dict[str, object] | None:
    """Find existing issue by hidden artifact-sync marker."""
    for issue in _list_github_issues(repo_slug, env):
        if marker in str(issue.get("body", "")):
            return issue
    return None


def _extract_issue_number_from_url(issue_url: str) -> str:
    """Extract issue number from issue URL."""
    return issue_url.rstrip("/").split("/")[-1]


def _write_temp_body(content: str) -> str:
    """Persist markdown body into a temporary file for gh issue commands."""
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", delete=False, suffix=".md"
    )
    handle.write(content)
    handle.flush()
    handle.close()
    return handle.name


def _ensure_issue_on_project(
    owner: str, project_number: str, issue_url: str, env: dict[str, str]
) -> str:
    """Ensure GitHub issue is present in the target project exactly once."""
    if not owner or not project_number or not issue_url:
        return "skipped"

    ok, output = _run_gh_command(
        [
            "gh",
            "project",
            "item-list",
            project_number,
            "--owner",
            owner,
            "--format",
            "json",
        ],
        env,
    )
    if ok:
        try:
            items = _extract_project_items(json.loads(output))
        except json.JSONDecodeError:
            items = []
        for item in items:
            content = item.get("content")
            if isinstance(content, dict) and str(content.get("url", "")) == issue_url:
                return "existing"

    ok, add_output = _run_gh_command(
        [
            "gh",
            "project",
            "item-add",
            project_number,
            "--owner",
            owner,
            "--url",
            issue_url,
            "--format",
            "json",
        ],
        env,
    )
    return (
        "added"
        if ok
        else f"manual-required:{add_output or 'unable to add issue to project'}"
    )


def _ensure_bundle_milestone(
    repo_slug: str,
    *,
    stage: str,
    bundle_key: str,
    env: dict[str, str],
) -> str:
    """Ensure one milestone exists for the planning bundle and return its title."""
    item_code = bundle_key.split("/")[-1]
    milestone_title = f"{stage.title()}-{item_code} Delivery"
    ok, output = _run_gh_command(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/milestones",
            "--method",
            "GET",
            "--field",
            "state=all",
        ],
        env,
    )
    if ok:
        try:
            payload = json.loads(output)
        except json.JSONDecodeError:
            payload = []
        if isinstance(payload, list):
            for entry in payload:
                if (
                    isinstance(entry, dict)
                    and str(entry.get("title", "")).strip() == milestone_title
                ):
                    return milestone_title

    _run_gh_command(
        [
            "gh",
            "api",
            f"repos/{repo_slug}/milestones",
            "--method",
            "POST",
            "--field",
            f"title={milestone_title}",
            "--field",
            "description=Planning hierarchy container generated from stage artifacts.",
        ],
        env,
    )
    return milestone_title


def _assign_issue_milestone(
    repo_slug: str,
    issue_number: str,
    milestone_title: str,
    env: dict[str, str],
) -> None:
    """Assign a milestone to an issue (best effort)."""
    if not issue_number:
        return
    _run_gh_command(
        [
            "gh",
            "issue",
            "edit",
            issue_number,
            "--repo",
            repo_slug,
            "--milestone",
            milestone_title,
        ],
        env,
    )


def _ensure_issue_labels(
    repo_slug: str,
    issue_number: str,
    *,
    stage: str,
    kind: str,
    assignee_hint: str,
    env: dict[str, str],
) -> None:
    """Ensure deterministic labels exist and are attached to the issue."""
    effective_owner = "agile-coach" if kind in {"epic", "story"} else (assignee_hint or "fullstack-engineer")
    owner_label = f"owner:{effective_owner}"
    label_specs = [
        (f"kind:{kind}", "1f6feb"),
        (f"stage:{stage}", "a371f7"),
        (owner_label, "0e8a16"),
        ("source:artifacts", "fbca04"),
    ]
    for label_name, color in label_specs:
        _run_gh_command(
            [
                "gh",
                "label",
                "create",
                label_name,
                "--repo",
                repo_slug,
                "--color",
                color,
                "--force",
            ],
            env,
        )

    ok, view_output = _run_gh_command(
        [
            "gh",
            "issue",
            "view",
            issue_number,
            "--repo",
            repo_slug,
            "--json",
            "labels",
        ],
        env,
    )
    if ok:
        try:
            payload = json.loads(view_output)
        except json.JSONDecodeError:
            payload = {}
        existing_labels: list[str] = []
        if isinstance(payload, dict):
            raw_labels = payload.get("labels", [])
            if isinstance(raw_labels, list):
                for item in raw_labels:
                    if isinstance(item, dict):
                        name = str(item.get("name", "")).strip()
                    else:
                        name = str(item).strip()
                    if name:
                        existing_labels.append(name)

        stale_labels = [
            label
            for label in existing_labels
            if label.startswith(("owner:", "kind:", "stage:"))
        ]
        if stale_labels:
            _run_gh_command(
                [
                    "gh",
                    "issue",
                    "edit",
                    issue_number,
                    "--repo",
                    repo_slug,
                    "--remove-label",
                    ",".join(stale_labels),
                ],
                env,
            )

    _run_gh_command(
        [
            "gh",
            "issue",
            "edit",
            issue_number,
            "--repo",
            repo_slug,
            "--add-label",
            ",".join(label for label, _ in label_specs),
        ],
        env,
    )


def ensure_planning_issue_assets(
    repo_root: Path,
    stage: str,
    bundle_key: str,
    planning_paths: dict[str, Path],
    board_ticket_ids: dict[str, str],
    primary_assets: dict[str, object],
) -> dict[str, object]:
    """Ensure GitHub issues exist for planning artifacts and are linked to the project."""
    if not _is_primary_sync_enabled():
        return {
            "status": "skipped",
            "issues": {},
            "message": "primary sync disabled by DIGITAL_STAGE_PRIMARY_SYNC",
            "auth_source": "",
        }

    token, source = _resolve_github_token()
    repo_slug = str(primary_assets.get("repo_slug", ""))
    if not repo_slug:
        repo_slug, _, _ = _resolve_repo_context(repo_root)
    _project_raw = primary_assets.get("project")
    project: dict[str, object] = _project_raw if isinstance(_project_raw, dict) else {}
    owner = str(project.get("owner", ""))
    project_number = str(project.get("number", ""))
    if not token or not repo_slug:
        return {
            "status": "manual-required",
            "issues": {},
            "message": "github issue sync unavailable",
            "auth_source": source or "",
        }

    env = _build_gh_env(token)
    issue_results: dict[str, dict[str, str]] = {}
    statuses: set[str] = set()
    milestone_title = _ensure_bundle_milestone(
        repo_slug,
        stage=stage,
        bundle_key=bundle_key,
        env=env,
    )

    kind_order = ["epic", "story", "task", "bug"]
    ordered_items = [
        (kind, planning_paths[kind]) for kind in kind_order if kind in planning_paths
    ]

    for kind, artifact_path in ordered_items:
        artifact_text = artifact_path.read_text(encoding="utf-8")
        metadata = _parse_frontmatter(artifact_text)
        artifact_status = metadata.get("status", "").strip()
        assignee_hint = metadata.get("assignee_hint", "fullstack-engineer")
        if kind in {"epic", "story"}:
            assignee_hint = "agile-coach"
        elif kind in {"task", "bug"} and assignee_hint == "agile-coach":
            assignee_hint = "fullstack-engineer"
        board_ticket_id = board_ticket_ids.get(kind, "")
        marker = _artifact_marker(stage, bundle_key, kind, board_ticket_id)
        title = _artifact_issue_title(
            kind,
            artifact_text,
            bundle_key,
            stage,
            board_ticket_id,
        )
        body = _issue_body(
            marker,
            artifact_text,
            board_ticket_id,
            stage=stage,
            kind=kind,
            bundle_key=bundle_key,
            assignee_hint=assignee_hint,
            artifact_status=artifact_status,
        )
        existing_issue = _find_issue_by_marker(repo_slug, marker, env)

        issue_status = "existing"
        issue_url = ""
        issue_number = ""
        temp_path = _write_temp_body(body)
        try:
            if existing_issue is not None:
                issue_url = str(existing_issue.get("url", ""))
                issue_number = str(existing_issue.get("number", ""))
                if (
                    str(existing_issue.get("title", "")) != title
                    or str(existing_issue.get("body", "")) != body
                ):
                    ok, edit_output = _run_gh_command(
                        [
                            "gh",
                            "issue",
                            "edit",
                            issue_number,
                            "--repo",
                            repo_slug,
                            "--title",
                            title,
                            "--body-file",
                            temp_path,
                        ],
                        env,
                    )
                    if ok:
                        issue_status = (
                            "reopened+updated"
                            if issue_status == "reopened"
                            else "updated"
                        )
                    else:
                        issue_status = f"manual-required:{edit_output or 'unable to update issue'}"
            else:
                ok, create_output = _run_gh_command(
                    [
                        "gh",
                        "issue",
                        "create",
                        "--repo",
                        repo_slug,
                        "--title",
                        title,
                        "--body-file",
                        temp_path,
                    ],
                    env,
                )
                if ok:
                    issue_url = create_output.strip().splitlines()[-1]
                    issue_number = _extract_issue_number_from_url(issue_url)
                    issue_status = "created"
                else:
                    issue_status = (
                        f"manual-required:{create_output or 'unable to create issue'}"
                    )
        finally:
            try:
                os.unlink(temp_path)
            except OSError:
                pass

        if issue_number:
            current_issue_state = str(existing_issue.get("state", "")) if existing_issue else "open"
            state_sync_status = _sync_issue_state_with_artifact_status(
                repo_slug,
                issue_number,
                artifact_status,
                current_issue_state,
                env,
            )
            if state_sync_status in {"closed", "reopened"} and not issue_status.startswith("manual-required"):
                issue_status = f"{issue_status}+{state_sync_status}"
            elif state_sync_status.startswith("manual-required"):
                issue_status = state_sync_status

        if issue_number:
            _ensure_issue_labels(
                repo_slug,
                issue_number,
                stage=stage,
                kind=kind,
                assignee_hint=assignee_hint,
                env=env,
            )
            if kind in {"epic", "story", "task", "bug"}:
                _assign_issue_milestone(
                    repo_slug,
                    issue_number,
                    milestone_title,
                    env,
                )

        project_item_status = (
            _ensure_issue_on_project(owner, project_number, issue_url, env)
            if issue_url and kind in {"task", "bug"}
            else "skipped"
        )
        issue_results[kind] = {
            "status": issue_status,
            "url": issue_url,
            "number": issue_number,
            "project_item_status": project_item_status,
            "board_ticket_id": board_ticket_id,
            "milestone": milestone_title,
        }
        statuses.add(issue_status)

    overall_status = "synced"
    if any(status.startswith("manual-required") for status in statuses):
        overall_status = "partial"

    return {
        "status": overall_status,
        "issues": issue_results,
        "message": f"issue-sync:{overall_status}",
        "auth_source": source or "",
    }
