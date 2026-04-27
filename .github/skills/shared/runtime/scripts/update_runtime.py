#!/usr/bin/env python3

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import subprocess
from collections import Counter
from pathlib import Path

HTML_LAYER_RE = re.compile(r"<!--\s*layer:\s*([A-Za-z0-9._-]+)\s*-->")
LAYER_METADATA_EXTENSIONS = {".md", ".yaml", ".yml", ".sh"}
STAGE_CATALOG_RELATIVE = Path("skills/stages-action/stages.yaml")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _sha256_file(path: Path) -> str:
    return _sha256_text(path.read_text(encoding="utf-8", errors="replace"))


def _manifest_payload(
    current_repo: str,
    local_files: list[str],
    untagged_files: list[str],
) -> dict[str, object]:
    return {
        "schema": "local_backup_manifest_v1",
        "current_repo": current_repo,
        "local_files": sorted(local_files),
        "untagged_files": sorted(untagged_files),
    }


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def _load_override_registry(overrides_yaml: Path) -> dict[str, dict[str, str]]:
    """Load .digital-team/overrides.yaml as a path-indexed dictionary."""
    if not overrides_yaml.exists():
        return {}

    try:
        import yaml  # type: ignore
    except ImportError as exc:
        raise SystemExit(
            "[update] ERROR: PyYAML is required to parse .digital-team/overrides.yaml"
        ) from exc

    payload = yaml.safe_load(overrides_yaml.read_text(encoding="utf-8")) or {}
    entries = payload.get("overrides", [])
    if not isinstance(entries, list):
        raise SystemExit(
            "[update] ERROR: .digital-team/overrides.yaml must contain a list key 'overrides'"
        )

    registry: dict[str, dict[str, str]] = {}
    for idx, entry in enumerate(entries, start=1):
        if not isinstance(entry, dict):
            raise SystemExit(f"[update] ERROR: overrides[{idx}] must be a mapping")
        path = str(entry.get("path", "")).strip()
        if not path:
            raise SystemExit(
                f"[update] ERROR: overrides[{idx}] is missing required key 'path'"
            )
        registry[path] = {str(k): str(v) for k, v in entry.items() if v is not None}
    return registry


def with_trailing_newline(text: str, original: str) -> str:
    """Return text with a trailing newline if and only if original ended with one."""
    if text.endswith("\n") or not original.endswith("\n"):
        return text
    return text + "\n"


def upsert_prompt_layer(content: str, layer_name: str) -> str:
    """Insert or update the HTML layer comment marker in a prompt markdown file."""
    marker = f"<!-- layer: {layer_name} -->"
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", content, re.DOTALL)
    if match:
        frontmatter = re.sub(
            r"^layer:[ \t]*.*\n?", "", match.group(1), flags=re.MULTILINE
        ).strip("\n")
        rendered_frontmatter = f"---\n{frontmatter}\n---\n" if frontmatter else ""
        body = content[match.end() :]
        lines = body.splitlines()
        for index, line in enumerate(lines[:5]):
            if HTML_LAYER_RE.fullmatch(line.strip()):
                lines[index] = marker
                return with_trailing_newline(
                    rendered_frontmatter + "\n".join(lines), content
                )
        return with_trailing_newline(
            rendered_frontmatter + marker + "\n" + body, content
        )

    lines = content.splitlines()
    for index, line in enumerate(lines[:5]):
        if HTML_LAYER_RE.fullmatch(line.strip()):
            lines[index] = marker
            return with_trailing_newline("\n".join(lines), content)
    return with_trailing_newline(marker + "\n" + content, content)


def inject_layer(target_dir: Path, layer_name: str) -> None:
    """Recursively inject the layer marker into every eligible file under target_dir."""
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [directory for directory in dirs if not directory.startswith(".")]
        for filename in files:
            inject_file(Path(root) / filename, layer_name)


def inject_file(file_path: Path, layer_name: str) -> None:
    """Inject the layer marker into a single file according to its extension (.md/.yaml/.sh)."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return

    extension = file_path.suffix.lower()
    normalized_path = str(file_path).replace(os.sep, "/")

    if extension == ".md" and "/prompts/" in normalized_path:
        new_content = upsert_prompt_layer(content, layer_name)
    elif extension == ".md":
        match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", content, re.DOTALL)
        if match:
            frontmatter = re.sub(
                r"^layer:[ \t]*.*\n?", "", match.group(1), flags=re.MULTILINE
            )
            frontmatter = frontmatter.rstrip("\n") + "\nlayer: " + layer_name
            new_content = (
                "---\n" + frontmatter.strip("\n") + "\n---\n" + content[match.end() :]
            )
        else:
            new_content = "---\nlayer: " + layer_name + "\n---\n" + content
    elif extension in (".yaml", ".yml"):
        if re.search(r"^layer:", content, re.MULTILINE):
            new_content = re.sub(
                r"^layer:[ \t]*.*", "layer: " + layer_name, content, flags=re.MULTILINE
            )
        else:
            new_content = "layer: " + layer_name + "\n" + content
    elif extension == ".sh":
        lines = content.split("\n")
        if lines and lines[0].startswith("#!"):
            if len(lines) > 1 and lines[1].startswith("# layer:"):
                lines[1] = "# layer: " + layer_name
            else:
                lines.insert(1, "# layer: " + layer_name)
            new_content = "\n".join(lines)
        else:
            new_content = "# layer: " + layer_name + "\n" + content
    else:
        return

    if new_content != content:
        file_path.write_text(new_content, encoding="utf-8")


def get_layer(file_path: Path) -> str | None:
    """Extract the layer name from a markdown, YAML, or shell file's metadata."""
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None

    extension = file_path.suffix.lower()
    if extension == ".md":
        match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", content, re.DOTALL)
        if match:
            layer_match = re.search(r"^layer:[ \t]*(.+)", match.group(1), re.MULTILINE)
            if layer_match:
                return layer_match.group(1).strip()
        comment_match = HTML_LAYER_RE.search("\n".join(content.split("\n")[:8]))
        return comment_match.group(1).strip() if comment_match else None

    if extension in (".yaml", ".yml"):
        layer_match = re.search(r"^layer:[ \t]*(.+)", content, re.MULTILINE)
        return layer_match.group(1).strip() if layer_match else None

    if extension == ".sh":
        for line in content.split("\n")[:4]:
            if line.startswith("# layer:"):
                return line[8:].strip()

    return None


def requires_layer_metadata(file_path: Path) -> bool:
    """Return True when the file type supports repository layer metadata."""
    normalized_path = str(file_path).replace(os.sep, "/")

    if normalized_path.endswith("/index.instructions.md"):
        return False

    if "/.github/workflows/" in normalized_path or normalized_path.startswith(".github/workflows/"):
        return False

    return file_path.suffix.lower() in LAYER_METADATA_EXTENSIONS


def backup_local_files(
    github_dir: Path,
    current_repo: str,
    backup_dir: Path,
    manifest_path: Path,
) -> None:
    """Back up only current-layer files and fail fast on untagged files."""
    count = 0
    local_files: list[str] = []
    untagged_files: list[str] = []

    for root, dirs, files in os.walk(github_dir):
        dirs[:] = [directory for directory in dirs if not directory.startswith(".")]
        for filename in files:
            file_path = Path(root) / filename
            layer = get_layer(file_path)
            relative_path = str(file_path.relative_to(github_dir)).replace(os.sep, "/")
            if layer is None:
                if requires_layer_metadata(file_path):
                    untagged_files.append(relative_path)
                continue
            if layer == current_repo:
                relative_path = file_path.relative_to(github_dir)
                destination = backup_dir / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, destination)
                local_files.append(str(relative_path).replace(os.sep, "/"))
                count += 1

    _write_json(
        manifest_path,
        _manifest_payload(
            current_repo=current_repo,
            local_files=local_files,
            untagged_files=untagged_files,
        ),
    )

    print(f"[update]   backed up {count} local file(s)")
    print(f"[update]   wrote backup manifest: {manifest_path}")

    if untagged_files:
        print(
            "[update] ERROR: Found untagged files under .github/. Add layer metadata first."
        )
        for rel in sorted(untagged_files):
            print(f"[update] ERROR:   untagged -> .github/{rel}")
        raise SystemExit(2)


def validate_overrides(
    merged_github_dir: Path,
    backup_manifest: Path,
    current_repo: str,
    overrides_yaml: Path,
) -> None:
    """Validate that local overrides are explicit and still based on current parent hashes."""
    if not backup_manifest.exists():
        raise SystemExit(
            f"[update] ERROR: backup manifest not found: {backup_manifest}"
        )

    payload = json.loads(backup_manifest.read_text(encoding="utf-8"))
    local_files = {str(path) for path in payload.get("local_files", [])}

    registry = _load_override_registry(overrides_yaml)
    override_candidates = {
        rel for rel in local_files if (merged_github_dir / rel).exists()
    }

    errors: list[str] = []
    warnings: list[str] = []

    for rel in sorted(override_candidates):
        entry = registry.get(rel)
        if not entry:
            errors.append(
                f"override for '.github/{rel}' is missing from {overrides_yaml}"
            )
            continue

        owner_layer = entry.get("owner_layer", "")
        base_layer = entry.get("base_layer", "")
        base_hash = entry.get("base_hash", "")

        if owner_layer != current_repo:
            errors.append(
                f"override '.github/{rel}' has owner_layer='{owner_layer}', expected '{current_repo}'"
            )
        if not base_layer:
            errors.append(f"override '.github/{rel}' is missing base_layer")
        if not base_hash:
            errors.append(f"override '.github/{rel}' is missing base_hash")
            continue

        actual_hash = _sha256_file(merged_github_dir / rel)
        if base_hash != actual_hash:
            errors.append(
                "override drift detected for '.github/{}': base_hash={} actual_parent_hash={}".format(
                    rel,
                    base_hash,
                    actual_hash,
                )
            )

    for rel in sorted(registry):
        if rel not in local_files:
            warnings.append(
                f"registry entry '.github/{rel}' has no local file in current layer"
            )

    print(
        f"[update]   override candidates: {len(override_candidates)}, registry entries: {len(registry)}"
    )
    for warning in warnings:
        print(f"[update] WARNING: {warning}")

    if errors:
        for err in errors:
            print(f"[update] ERROR: {err}")
        raise SystemExit(2)


def generate_instruction_indexes(instructions_dir: Path) -> None:
    """Generate an index.instructions.md file for each instruction category directory."""
    for category in sorted(
        entry.name for entry in instructions_dir.iterdir() if entry.is_dir()
    ):
        category_dir = instructions_dir / category
        files = sorted(
            filename
            for filename in os.listdir(category_dir)
            if filename.endswith(".md") and filename != "index.instructions.md"
        )
        if not files:
            continue

        lines = [
            "---",
            f'name: "{category} index"',
            f'description: "Auto-generated index for {category} instructions"',
            "---",
            "",
            f"# {category}",
            "",
        ]
        lines.extend(f"- [{filename}]({filename})" for filename in files)
        lines.append("")

        index_path = category_dir / "index.instructions.md"
        index_path.write_text("\n".join(lines), encoding="utf-8")


def transform_agents(source_dir: Path, destination_dir: Path) -> None:
    """Transform *.agent.md files from source_dir into cleaned copies in destination_dir."""
    destination_dir.mkdir(parents=True, exist_ok=True)
    count = 0

    for filename in sorted(os.listdir(source_dir)):
        if not filename.endswith(".agent.md"):
            continue

        source_path = source_dir / filename
        content = source_path.read_text(encoding="utf-8", errors="replace")
        transformed = transform_agent_frontmatter(content)

        destination_name = filename.replace(".agent.md", ".md")
        (destination_dir / destination_name).write_text(transformed, encoding="utf-8")
        count += 1

    print(count)


def transform_agent_frontmatter(content: str) -> str:
    """Strip deployment-specific frontmatter fields (user-invocable, agents) from agent markdown."""
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", content, re.DOTALL)
    if not match:
        return content

    frontmatter = match.group(1)
    frontmatter = re.sub(
        r"^user-invocable:[ \t]*.*\n?", "", frontmatter, flags=re.MULTILINE
    )
    frontmatter = re.sub(
        r"^agents:[ \t]*.*\n([ \t]+-[ \t]+.*\n)*", "", frontmatter, flags=re.MULTILINE
    )
    frontmatter = re.sub(r"\n{3,}", "\n\n", frontmatter)
    return "---\n" + frontmatter.strip("\n") + "\n---\n" + content[match.end() :]


def generate_hook_adapters(
    hooks_dir: Path, claude_hooks_dir: Path, settings_path: Path
) -> None:
    """Create Claude hook adapter scripts and register them in the Claude settings.json."""
    hook_map: dict[str, tuple[str, str | None]] = {
        "session-start.sh": ("SessionStart", None),
        "pre-message.sh": ("UserPromptSubmit", None),
        "post-message.sh": ("Stop", None),
    }

    adapter_template = (
        "#!/usr/bin/env bash\n"
        "# Auto-generated by update.sh — do not edit manually.\n"
        "# Bridges Claude Code JSON stdin → .github/hooks/{name} env-var convention.\n"
        "set -euo pipefail\n\n"
        '_json="$(cat)"\n'
        '_session_id="$(printf \'%s\\n\' "$_json" \\\n'
        "    | python3 -c \"import sys,json; print(json.load(sys.stdin).get('session_id',''))\" \\\n"
        '    2>/dev/null || true)"\n\n'
        'export DIGITAL_SESSION_ID="${{_session_id:-}}"\n'
        'bash "$(git rev-parse --show-toplevel 2>/dev/null || pwd)/.github/hooks/{name}" 2>/dev/null || true\n'
    )

    claude_hooks_dir.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[str, str | None, str]] = []

    for filename, (event, matcher) in hook_map.items():
        source = hooks_dir / filename
        if not source.is_file():
            continue

        adapter_path = claude_hooks_dir / filename
        adapter_path.write_text(
            adapter_template.format(name=filename), encoding="utf-8"
        )
        adapter_path.chmod(adapter_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP)
        generated.append((event, matcher, filename))

    existing: dict[str, object] = {}
    if settings_path.exists():
        try:
            existing = json.loads(settings_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}

    hooks_config = existing.get("hooks", {})
    if not isinstance(hooks_config, dict):
        hooks_config = {}

    for event, matcher, filename in generated:
        command = f"bash .claude/hooks/{filename}"
        entry: dict[str, object] = {"hooks": [{"type": "command", "command": command}]}
        if matcher:
            entry["matcher"] = matcher

        previous = hooks_config.get(event, [])
        if not isinstance(previous, list):
            previous = []
        user_added = [
            item
            for item in previous
            if not any(
                str(hook.get("command", "")).startswith("bash .claude/hooks/")
                for hook in item.get("hooks", [])
                if isinstance(hook, dict)
            )
            if isinstance(item, dict)
        ]
        hooks_config[event] = user_added + [entry]

    existing["hooks"] = hooks_config
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(len(generated))


def generate_claude_md(
    instructions_dir: Path, claude_md_path: Path, current_repo: str
) -> None:
    """Generate the .claude/CLAUDE.md file with auto-discovered instruction imports."""
    imports: list[str] = []
    for category in sorted(
        entry.name for entry in instructions_dir.iterdir() if entry.is_dir()
    ):
        category_dir = instructions_dir / category
        for filename in sorted(os.listdir(category_dir)):
            if not filename.endswith(".md") or filename == "index.instructions.md":
                continue
            relative_path = Path(".github") / "instructions" / category / filename
            imports.append(f"@{relative_path}")

    header = (
        f"# Project Instructions — {current_repo}\n\n"
        "<!-- Auto-generated by update.sh — do not edit manually. -->\n"
        "<!-- Edit source files in .github/instructions/ instead.  -->\n\n"
    )
    claude_md_path.write_text(header + "\n".join(imports) + "\n", encoding="utf-8")
    print(len(imports))


STAGE_PROMPT_TEMPLATE = """\
<!-- layer: {current_repo} -->
# /{command} — {stage_title}

Alias for `/stages-action stage="{command}"`. Runs the full stage workflow for the **{stage_title}** stage.

Default command:

```bash
make {command}
```

Source layer: `{source_layer}`

See `/stages-action` for the full execution contract.
"""

STAGE_HELP_ENTRY = (
    "- `/{command}` — run the **{stage_title}** stage workflow"
    ' (alias for `/stages-action stage="{command}"`, source: `{source_layer}`).'
)

STAGE_BOARD_PROMPT_TEMPLATE = """\
<!-- layer: {current_repo} -->
# /{command}-board — {stage_title} Board

Alias for `/board --board {command}`. Shows the lifecycle board for the **{stage_title}** stage in terminal/chat output.

Default command:

```bash
make board BOARD={command}
```

Source layer: `{source_layer}`

See `/board` for board rendering, ref sync, and checkout workflow details.
"""

STAGE_BOARD_HELP_ENTRY = (
    "- `/{command}-board` — show the **{stage_title}** lifecycle board"
    " (alias for `/board --board {command}`, source: `{source_layer}`)."
)


def _normalize_prompt_name(name: str) -> str:
    """Normalize prompt names from config values to bare command names."""
    value = name.strip()
    if value.startswith("/"):
        value = value[1:]
    if value.endswith(".prompt.md"):
        value = value[: -len(".prompt.md")]
    if value.endswith(".md"):
        value = value[: -len(".md")]
    return value


def _load_disabled_prompts(repo_root: Path) -> set[str]:
    """Load disabled prompt names from governance config.

    Preferred source: .digital-team/prompt-governance.yaml
    Legacy fallback: .digital-team/customizations-index.json
    """
    governance_path = repo_root / ".digital-team" / "prompt-governance.yaml"
    if governance_path.exists():
        try:
            import yaml  # type: ignore
        except ImportError:
            yaml = None  # type: ignore

        if yaml is not None:
            try:
                payload = (
                    yaml.safe_load(governance_path.read_text(encoding="utf-8")) or {}
                )
            except (OSError, yaml.YAMLError):
                payload = {}
            values = payload.get("disabled_prompts", [])
            if isinstance(values, list):
                return {
                    normalized
                    for normalized in (
                        _normalize_prompt_name(str(value)) for value in values
                    )
                    if normalized
                }

    index_path = repo_root / ".digital-team" / "customizations-index.json"
    if not index_path.exists():
        return set()

    try:
        payload = json.loads(index_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()

    disabled_values: list[str] = []
    for key in ("disabled_prompts", "hidden_prompts", "exclude_prompts"):
        values = payload.get(key, [])
        if isinstance(values, list):
            disabled_values.extend(str(value) for value in values)

    return {
        normalized
        for normalized in (_normalize_prompt_name(value) for value in disabled_values)
        if normalized
    }


def prune_prompts(github_dir: Path, repo_root: Path) -> None:
    """Remove disabled prompts and stale help entries based on repo customizations."""
    prompts_dir = github_dir / "prompts"
    help_path = prompts_dir / "help.prompt.md"
    if not prompts_dir.is_dir():
        return

    disabled_prompts = _load_disabled_prompts(repo_root)
    removed_files = 0

    for prompt_name in sorted(disabled_prompts):
        prompt_path = prompts_dir / f"{prompt_name}.prompt.md"
        if prompt_path.exists():
            prompt_path.unlink()
            removed_files += 1

    active_prompts = {
        path.name[: -len(".prompt.md")]
        for path in prompts_dir.glob("*.prompt.md")
        if path.name.endswith(".prompt.md")
    }

    if help_path.exists():
        command_pattern = re.compile(r"^- `/(?P<cmd>[a-zA-Z0-9_-]+)`")
        kept_lines: list[str] = []
        removed_help_entries = 0
        for line in help_path.read_text(encoding="utf-8").splitlines():
            command_match = command_pattern.match(line.strip())
            if command_match:
                command_name = command_match.group("cmd")
                if (
                    command_name in disabled_prompts
                    or command_name not in active_prompts
                ):
                    removed_help_entries += 1
                    continue
            kept_lines.append(line)
        help_path.write_text("\n".join(kept_lines).rstrip() + "\n", encoding="utf-8")
    else:
        removed_help_entries = 0

    print(
        f"[update_runtime] pruned {removed_files} disabled prompt file(s), removed {removed_help_entries} stale help entries"
    )


def _read_frontmatter(path: Path) -> dict[str, str]:
    """Return frontmatter key/value dict from a markdown file."""
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    match = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n", content, re.DOTALL)
    if not match:
        return {}
    fm: dict[str, str] = {}
    for line in match.group(1).splitlines():
        kv = re.match(r'^([\w-]+):\s*"?([^"]*)"?\s*$', line)
        if kv:
            fm[kv.group(1)] = kv.group(2).strip()
    return fm


def _is_local_prompt_override(path: Path, current_repo: str) -> bool:
    """Return true when an existing prompt file belongs to the current layer."""
    if not path.exists():
        return False

    frontmatter = _read_frontmatter(path)
    if frontmatter.get("layer", "") == current_repo:
        return True

    detected_layer = get_layer(path)
    return detected_layer == current_repo


def _load_stage_catalog(github_dir: Path, current_repo: str) -> list[dict[str, str]]:
    """Load stage metadata from skills catalog, with instruction frontmatter fallback."""
    catalog_path = github_dir / STAGE_CATALOG_RELATIVE

    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None  # type: ignore

    if yaml is not None and catalog_path.exists():
        try:
            payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            payload = {}

        rows = payload.get("stages", [])
        if isinstance(rows, list):
            stages: list[dict[str, str]] = []
            for row in rows:
                if not isinstance(row, dict):
                    continue

                command = str(row.get("command", "")).strip()
                if not command:
                    continue

                title = str(row.get("title", "")).strip() or command.capitalize()
                stages.append(
                    {
                        "command": command,
                        "stage_id": str(row.get("stage_id", "")).strip(),
                        "description": str(row.get("description", "")).strip()
                        or command,
                        "source_layer": str(row.get("source_layer", "")).strip()
                        or current_repo,
                        "stage_title": title,
                    }
                )
            if stages:
                return stages

    stages_dir = github_dir / "instructions" / "stages"
    if not stages_dir.is_dir():
        return []

    stages: list[dict[str, str]] = []
    for fname in sorted(os.listdir(stages_dir)):
        if not fname.endswith(".instructions.md") or fname == "index.instructions.md":
            continue
        fm = _read_frontmatter(stages_dir / fname)
        command = fm.get("command", "").strip()
        if not command:
            continue
        stages.append(
            {
                "command": command,
                "stage_id": fm.get("stage-id", ""),
                "description": fm.get("description", command),
                "source_layer": fm.get("layer", current_repo),
                "stage_title": command.capitalize(),
            }
        )

    return stages


def stage_commands(github_dir: Path, current_repo: str) -> None:
    """Print one stage command per line from the central stage catalog."""
    for stage in _load_stage_catalog(github_dir, current_repo):
        print(stage["command"])


def generate_stage_prompts(github_dir: Path, current_repo: str) -> None:
    """Auto-generate stage prompt and board alias prompt files from stage metadata."""
    prompts_dir = github_dir / "prompts"
    help_path = prompts_dir / "help.prompt.md"

    stages = _load_stage_catalog(github_dir, current_repo)
    if not stages:
        print("[update_runtime] no stage metadata found")
        return

    generated = 0
    generated_board_aliases = 0
    for stage in stages:
        prompt_path = prompts_dir / f"{stage['command']}.prompt.md"
        if not _is_local_prompt_override(prompt_path, current_repo):
            content = STAGE_PROMPT_TEMPLATE.format(
                command=stage["command"],
                stage_title=stage["stage_title"],
                source_layer=stage["source_layer"],
                current_repo=current_repo,
            )
            prompt_path.write_text(content, encoding="utf-8")
            generated += 1

        board_prompt_path = prompts_dir / f"{stage['command']}-board.prompt.md"
        if _is_local_prompt_override(board_prompt_path, current_repo):
            continue
        if (
            not board_prompt_path.exists()
            or get_layer(board_prompt_path) != current_repo
        ):
            board_content = STAGE_BOARD_PROMPT_TEMPLATE.format(
                command=stage["command"],
                stage_title=stage["stage_title"],
                source_layer=stage["source_layer"],
                current_repo=current_repo,
            )
            board_prompt_path.write_text(board_content, encoding="utf-8")
            generated_board_aliases += 1

    # Update help.prompt.md — replace managed stage block
    if help_path.exists():
        help_content = help_path.read_text(encoding="utf-8")

        stage_entries = "\n".join(STAGE_HELP_ENTRY.format(**s) for s in stages)
        stage_board_entries = "\n".join(
            STAGE_BOARD_HELP_ENTRY.format(**s) for s in stages
        )

        managed_start = "<!-- stages:start -->"
        managed_end = "<!-- stages:end -->"
        block = f"{managed_start}\n{stage_entries}\n{managed_end}"

        managed_board_start = "<!-- stages-board:start -->"
        managed_board_end = "<!-- stages-board:end -->"
        board_block = (
            f"{managed_board_start}\n{stage_board_entries}\n{managed_board_end}"
        )

        if managed_start in help_content:
            help_content = re.sub(
                re.escape(managed_start) + r".*?" + re.escape(managed_end),
                block,
                help_content,
                flags=re.DOTALL,
            )
        elif "## Output style" in help_content:
            help_content = help_content.replace(
                "## Output style",
                block + "\n\n## Output style",
            )
        else:
            help_content = help_content.rstrip() + "\n\n" + block + "\n"

        if managed_board_start in help_content:
            help_content = re.sub(
                re.escape(managed_board_start) + r".*?" + re.escape(managed_board_end),
                board_block,
                help_content,
                flags=re.DOTALL,
            )
        elif managed_end in help_content:
            help_content = help_content.replace(
                managed_end,
                managed_end + "\n" + board_block,
            )
        elif "## Output style" in help_content:
            help_content = help_content.replace(
                "## Output style",
                board_block + "\n\n## Output style",
            )
        else:
            help_content = help_content.rstrip() + "\n\n" + board_block + "\n"

        help_path.write_text(help_content, encoding="utf-8")

    print(
        f"[update_runtime] generated {generated} stage prompt(s), generated {generated_board_aliases} stage-board prompt(s), updated help.prompt.md"
    )  # noqa: E501


def list_stages(github_dir: Path, repo_root: Path) -> None:
    """Print a status table of all available stages."""
    stages = _load_stage_catalog(github_dir, "")
    if not stages:
        print("No stages directory found.")
        return

    resolved_stages: list[dict[str, str]] = []
    for stage in stages:
        command = stage["command"]
        stage_dir = repo_root / ".digital-artifacts" / "40-stage" / command
        stage_doc = stage_dir / f"{command.upper()}.md"
        if not stage_dir.exists() or not any(stage_dir.iterdir()):
            status = "available"
        elif not stage_doc.exists():
            status = "started"
        else:
            doc_fm = _read_frontmatter(stage_doc)
            status = "active" if doc_fm.get("status", "") == "active" else "in-progress"
        resolved_stages.append(
            {
                "command": command,
                "description": stage.get("description", command),
                "source_layer": stage.get("source_layer", ""),
                "status": status,
            }
        )

    # Find active and in-progress stage(s)
    active = [s for s in resolved_stages if s["status"] == "active"]
    in_prog = [s for s in resolved_stages if s["status"] == "in-progress"]
    if active:
        print(f"\nActive stage: {', '.join('/' + s['command'] for s in active)}\n")
    if in_prog:
        print(f"In progress: {', '.join('/' + s['command'] for s in in_prog)}\n")

    col_w = [
        max(len(s[k]) for s in resolved_stages)
        for k in ("command", "description", "status", "source_layer")
    ]
    col_w = [max(w, h) for w, h in zip(col_w, [7, 11, 6, 5])]
    header = (
        f"{'Command':<{col_w[0] + 2}}  {'Description':<{col_w[1]}}  "
        f"{'Status':<{col_w[2]}}  {'Layer':<{col_w[3]}}"
    )
    sep = "  ".join("-" * (w + (2 if i == 0 else 0)) for i, w in enumerate(col_w))
    print(header)
    print(sep)
    for s in resolved_stages:
        cmd = f"/{s['command']}"
        print(
            f"{cmd:<{col_w[0] + 2}}  {s['description']:<{col_w[1]}}  "
            f"{s['status']:<{col_w[2]}}  {s['source_layer']:<{col_w[3]}}"
        )


def _read_git_name_status(repo_root: Path) -> list[tuple[str, str]]:
    result = subprocess.run(
        [
            "git",
            "-C",
            str(repo_root),
            "diff",
            "--name-status",
            "--",
            ".github",
            ".claude",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return []

    rows: list[tuple[str, str]] = []
    for raw_line in result.stdout.splitlines():
        if not raw_line.strip():
            continue
        columns = raw_line.split("\t")
        status = columns[0]
        if status.startswith(("R", "C")) and len(columns) >= 3:
            rows.append((status[0], columns[2]))
        elif len(columns) >= 2:
            rows.append((status[0], columns[1]))
    return rows


def _github_group(path: str) -> str:
    if path.startswith(".github/agents/"):
        return "agents"
    if path.startswith(".github/instructions/"):
        return "instructions"
    if path.startswith(".github/skills/"):
        return "skills"
    if path.startswith(".github/prompts/"):
        return "prompts"
    if path.startswith(".github/hooks/"):
        return "hooks"
    return "other"


def _claude_group(path: str) -> str:
    if path.startswith(".claude/commands/"):
        return "commands"
    if path.startswith(".claude/agents/"):
        return "agents"
    if path.startswith(".claude/hooks/"):
        return "hooks"
    if path == ".claude/CLAUDE.md":
        return "claude-md"
    if path == ".claude/settings.json":
        return "settings"
    return "other"


def _layer_attribution_summary(github_dir: Path) -> Counter[str]:
    counts: Counter[str] = Counter()
    for root, dirs, files in os.walk(github_dir):
        dirs[:] = [directory for directory in dirs if not directory.startswith(".")]
        for filename in files:
            file_path = Path(root) / filename
            if file_path.suffix.lower() not in {".md", ".yaml", ".yml", ".sh"}:
                continue
            layer = get_layer(file_path)
            if layer:
                counts[layer] += 1
            else:
                counts["<missing>"] += 1
    return counts


def report_update(repo_root: Path, github_dir: Path, claude_dir: Path) -> None:
    """Print a summary of git-changed .github and .claude files grouped by type and layer."""
    rows = _read_git_name_status(repo_root)

    if not claude_dir.is_dir():
        print(f"[update][report] note: {claude_dir} does not exist")

    github_counts: dict[str, Counter[str]] = {
        "A": Counter(),
        "M": Counter(),
        "D": Counter(),
    }
    claude_counts: dict[str, Counter[str]] = {
        "A": Counter(),
        "M": Counter(),
        "D": Counter(),
    }

    for status, path in rows:
        normalized_status = status if status in {"A", "M", "D"} else "M"
        if path.startswith(".github/"):
            github_counts[normalized_status][_github_group(path)] += 1
        elif path.startswith(".claude/"):
            claude_counts[normalized_status][_claude_group(path)] += 1

    layer_counts = (
        _layer_attribution_summary(github_dir) if github_dir.is_dir() else Counter()
    )

    print("[update][report] changed files in .github by type")
    for status in ("A", "M", "D"):
        payload = dict(sorted(github_counts[status].items()))
        print(
            f"[update][report] .github {status}: {json.dumps(payload, sort_keys=True)}"
        )

    print("[update][report] changed files in .claude by type")
    for status in ("A", "M", "D"):
        payload = dict(sorted(claude_counts[status].items()))
        print(
            f"[update][report] .claude {status}: {json.dumps(payload, sort_keys=True)}"
        )

    print(
        f"[update][report] layer attribution: {json.dumps(dict(sorted(layer_counts.items())), sort_keys=True)}"
    )
    print(
        "[update][report] warnings/errors: see '[update] WARNING:' and '[update] ERROR:' lines above"
    )


def get_layers(layers_yaml: Path) -> None:
    """Read layers.yaml and print each layer's name and source separated by a pipe."""
    try:
        import yaml  # type: ignore
    except ImportError:
        return

    data = yaml.safe_load(layers_yaml.read_text(encoding="utf-8")) or {}
    for layer in data.get("layers", []):
        print(f"{layer['name']}|{layer['source']}")


def main() -> None:
    """Entry point for the update-runtime CLI dispatcher."""
    parser = argparse.ArgumentParser(
        description="Runtime helpers for update.sh without heredoc usage"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_get_layers = subparsers.add_parser("get-layers")
    parser_get_layers.add_argument("layers_yaml", type=Path)

    parser_inject_layer = subparsers.add_parser("inject-layer")
    parser_inject_layer.add_argument("target_dir", type=Path)
    parser_inject_layer.add_argument("layer_name")

    parser_backup = subparsers.add_parser("backup-local")
    parser_backup.add_argument("github_dir", type=Path)
    parser_backup.add_argument("current_repo")
    parser_backup.add_argument("backup_dir", type=Path)
    parser_backup.add_argument("manifest_path", type=Path)

    parser_validate_overrides = subparsers.add_parser("validate-overrides")
    parser_validate_overrides.add_argument("merged_github_dir", type=Path)
    parser_validate_overrides.add_argument("backup_manifest", type=Path)
    parser_validate_overrides.add_argument("current_repo")
    parser_validate_overrides.add_argument("overrides_yaml", type=Path)

    parser_indexes = subparsers.add_parser("generate-indexes")
    parser_indexes.add_argument("instructions_dir", type=Path)

    parser_agents = subparsers.add_parser("transform-agents")
    parser_agents.add_argument("source_dir", type=Path)
    parser_agents.add_argument("destination_dir", type=Path)

    parser_hooks = subparsers.add_parser("generate-hooks")
    parser_hooks.add_argument("hooks_dir", type=Path)
    parser_hooks.add_argument("claude_hooks_dir", type=Path)
    parser_hooks.add_argument("settings_path", type=Path)

    parser_claude_md = subparsers.add_parser("generate-claude-md")
    parser_claude_md.add_argument("instructions_dir", type=Path)
    parser_claude_md.add_argument("claude_md_path", type=Path)
    parser_claude_md.add_argument("current_repo")

    parser_stage_prompts = subparsers.add_parser("generate-stage-prompts")
    parser_stage_prompts.add_argument("github_dir", type=Path)
    parser_stage_prompts.add_argument("current_repo")

    parser_prune_prompts = subparsers.add_parser("prune-prompts")
    parser_prune_prompts.add_argument("github_dir", type=Path)
    parser_prune_prompts.add_argument("repo_root", type=Path)

    parser_report_update = subparsers.add_parser("report-update")
    parser_report_update.add_argument("repo_root", type=Path)
    parser_report_update.add_argument("github_dir", type=Path)
    parser_report_update.add_argument("claude_dir", type=Path)

    parser_list_stages = subparsers.add_parser("list-stages")
    parser_list_stages.add_argument("github_dir", type=Path)
    parser_list_stages.add_argument("repo_root", type=Path)

    parser_stage_commands = subparsers.add_parser("stage-commands")
    parser_stage_commands.add_argument("github_dir", type=Path)
    parser_stage_commands.add_argument("current_repo")

    args = parser.parse_args()

    if args.command == "get-layers":
        get_layers(args.layers_yaml)
    elif args.command == "inject-layer":
        inject_layer(args.target_dir, args.layer_name)
    elif args.command == "backup-local":
        backup_local_files(
            args.github_dir,
            args.current_repo,
            args.backup_dir,
            args.manifest_path,
        )
    elif args.command == "validate-overrides":
        validate_overrides(
            args.merged_github_dir,
            args.backup_manifest,
            args.current_repo,
            args.overrides_yaml,
        )
    elif args.command == "generate-indexes":
        generate_instruction_indexes(args.instructions_dir)
    elif args.command == "transform-agents":
        transform_agents(args.source_dir, args.destination_dir)
    elif args.command == "generate-hooks":
        generate_hook_adapters(
            args.hooks_dir, args.claude_hooks_dir, args.settings_path
        )
    elif args.command == "generate-claude-md":
        generate_claude_md(
            args.instructions_dir, args.claude_md_path, args.current_repo
        )
    elif args.command == "generate-stage-prompts":
        generate_stage_prompts(args.github_dir, args.current_repo)
    elif args.command == "prune-prompts":
        prune_prompts(args.github_dir, args.repo_root)
    elif args.command == "report-update":
        report_update(args.repo_root, args.github_dir, args.claude_dir)
    elif args.command == "list-stages":
        list_stages(args.github_dir, args.repo_root)
    elif args.command == "stage-commands":
        stage_commands(args.github_dir, args.current_repo)


if __name__ == "__main__":
    main()
