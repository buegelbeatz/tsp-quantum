#!/usr/bin/env python3
# layer: digital-generic-team
"""
Purpose:
    Build and print a layer-annotated treeview of the .github/ directory,
    grouping files by their origin layer (from layer: frontmatter or comments).
    Detects overrides where the same relative path appears in multiple layers.
    Uses ANSI color codes to highlight the current layer vs. inherited layers.
Security:
    Reads only local files. No network access, no eval, no subprocess.
"""

from __future__ import annotations

import argparse
import os
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# ANSI colors
# ---------------------------------------------------------------------------

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
GREEN = "\033[92m"  # current layer
YELLOW = "\033[93m"  # intermediate layer
BLUE = "\033[94m"  # base layer (L0)
CYAN = "\033[96m"  # section headers
RED = "\033[91m"  # override / conflict marker
MAGENTA = "\033[95m"  # unfamiliar / unknown layer


def color(text: str, *codes: str) -> str:
    """TODO: add docstring for color."""
    return "".join(codes) + text + RESET


# ---------------------------------------------------------------------------
# Layer reading
# ---------------------------------------------------------------------------

LAYER_RE = re.compile(r'layer:\s*([^\s\n>#"\']+)')


def extract_layer(path: Path) -> Optional[str]:
    """Extract the 'layer:' value from any supported file format."""
    try:
        text = path.read_text(errors="replace")
    except (OSError, PermissionError):
        return None

    lines = text.splitlines()

    # Prefer frontmatter blocks first because many files place `layer:`
    # after long metadata sections (for example large tool lists).
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            m = LAYER_RE.search(line)
            if m:
                return m.group(1).strip()

    # Fallback: scan a bounded header window for comment-style metadata.
    for line in lines[:120]:
        m = LAYER_RE.search(line)
        if m:
            return m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Layer chain
# ---------------------------------------------------------------------------


def read_layer_chain(repo_root: Path) -> list[str]:
    """Return ordered list of layers from layers.yaml (oldest ancestor first, current last)."""
    layers_yaml = repo_root / ".digital-team" / "layers.yaml"
    chain: list[str] = []

    if layers_yaml.exists():
        text = layers_yaml.read_text()
        for m in re.finditer(r"- name:\s*(.+)", text):
            chain.append(m.group(1).strip())

    # Derive current layer name from dirname; only trust origin when it does not
    # collide with an inherited parent entry.
    current = repo_root.name
    remote_candidate: str | None = None
    git_config = repo_root / ".git" / "config"
    if git_config.exists():
        for line in git_config.read_text().splitlines():
            if "url" in line and "=" in line:
                url = line.split("=", 1)[1].strip().rstrip(".git")
                remote_candidate = url.split("/")[-1]
                break

    if remote_candidate:
        if remote_candidate == current or remote_candidate not in chain:
            current = remote_candidate

    if current not in chain:
        chain.append(current)

    return chain


# ---------------------------------------------------------------------------
# File scanning
# ---------------------------------------------------------------------------

CATEGORIES = [
    ("agents", ".github/agents", [".agent.md", ".md"]),
    ("skills", ".github/skills", None),  # dirs
    ("instructions", ".github/instructions", [".md"]),
    ("prompts", ".github/prompts", [".prompt.md", ".md"]),
    ("handoffs", ".github/handoffs", [".yaml", ".md"]),
    ("hooks", ".github/hooks", [".sh"]),
    ("make", ".github/make", [".mk"]),
]

SKIP_NAMES = {"README.md", "index.instructions.md"}


class TreeEntry:
    __slots__ = ("rel_path", "abs_path", "layer", "name")

    def __init__(self, rel_path: str, abs_path: Path, layer: Optional[str]):
        self.rel_path = rel_path
        self.abs_path = abs_path
        self.layer = layer or "unknown"
        self.name = abs_path.name


def scan_category(
    repo_root: Path,
    rel_dir: str,
    exts: Optional[list[str]],
    default_layer: str,
) -> list[TreeEntry]:
    """TODO: add docstring for scan_category."""
    base = repo_root / rel_dir
    if not base.exists():
        return []

    entries: list[TreeEntry] = []

    if exts is None:
        # skills: list subdirectories (each skill is a dir)
        for item in sorted(base.iterdir()):
            if item.is_dir() and item.name != "README.md":
                skill_md = item / "SKILL.md"
                layer = extract_layer(skill_md) if skill_md.exists() else None
                # fallback: check any file in the dir
                if not layer:
                    for f in item.iterdir():
                        layer = extract_layer(f)
                        if layer:
                            break
                entries.append(
                    TreeEntry(f"{rel_dir}/{item.name}", item, layer or default_layer)
                )
        return entries

    # Walk recursively for file-based categories
    for dirpath, dirnames, filenames in os.walk(base):
        # Sort for stable output
        dirnames.sort()
        for fname in sorted(filenames):
            if fname in SKIP_NAMES:
                continue
            fpath = Path(dirpath) / fname
            suffix = "".join(fpath.suffixes)
            if any(fname.endswith(e) or suffix.endswith(e) for e in exts):
                rel = str(fpath.relative_to(repo_root))
                entries.append(
                    TreeEntry(rel, fpath, extract_layer(fpath) or default_layer)
                )

    return entries


# ---------------------------------------------------------------------------
# Tree rendering
# ---------------------------------------------------------------------------


def layer_badge(layer: str, chain: list[str], current: str) -> str:
    """TODO: add docstring for layer_badge."""
    if layer == current:
        idx = len(chain) - 1
        label = f"L{idx}" if idx > 0 else "L0"
        return color(f"[{label}]", BOLD, GREEN)
    elif layer in chain:
        idx = chain.index(layer)
        label = f"L{idx}"
        return color(f"[{label}]", YELLOW)
    elif layer == "unknown":
        return color("[??]", DIM)
    else:
        return color("[ext]", MAGENTA)


def load_override_paths(repo_root: Path) -> set[str]:
    """Load override paths from .digital-team/overrides.yaml.

    Returns normalized paths relative to .github/, e.g. prompts/help.prompt.md.
    """
    overrides_file = repo_root / ".digital-team" / "overrides.yaml"
    if not overrides_file.exists():
        return set()

    text = overrides_file.read_text(encoding="utf-8", errors="replace")

    # Prefer YAML parser when available for strict parsing.
    try:
        import yaml  # type: ignore
    except ImportError:
        yaml = None  # type: ignore

    if yaml is not None:
        yaml_error = getattr(yaml, "YAMLError", ValueError)
        try:
            payload = yaml.safe_load(text) or {}
            entries = payload.get("overrides", [])
            paths = {
                str(entry.get("path", "")).strip().lstrip("/")
                for entry in entries
                if isinstance(entry, dict) and str(entry.get("path", "")).strip()
            }
            return {path for path in paths if path}
        except (yaml_error, AttributeError, TypeError, ValueError):
            pass

    # Graceful fallback: scan for list items containing path: values.
    matches = re.finditer(r"^\s*-\s*path:\s*(.+)\s*$", text, re.MULTILINE)
    return {m.group(1).strip().strip("\"'").lstrip("/") for m in matches}


def to_registry_path(rel_path: str) -> str:
    """TODO: add docstring for to_registry_path."""
    normalized = rel_path.replace("\\", "/")
    if normalized.startswith(".github/"):
        return normalized[len(".github/") :]
    return normalized


def _layer_counts(entries: list[TreeEntry]) -> Counter[str]:
    counts: Counter[str] = Counter()
    for entry in entries:
        counts[entry.layer] += 1
    return counts


def _format_layer_summary(counts: Counter[str], chain: list[str]) -> str:
    parts: list[str] = []
    current = chain[-1]
    for layer, value in sorted(counts.items(), key=lambda item: item[0]):
        parts.append(f"{layer_badge(layer, chain, current)}={value}")
    return ", ".join(parts)


def _recent_markdown(repo_root: Path, limit: int) -> list[tuple[str, float]]:
    if limit <= 0:
        return []

    base = repo_root / ".github"
    if not base.exists():
        return []

    items: list[tuple[str, float]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = [
            directory for directory in dirnames if not directory.startswith(".")
        ]
        for filename in filenames:
            if not filename.endswith(".md"):
                continue
            path = Path(dirpath) / filename
            try:
                mtime = path.stat().st_mtime
            except OSError:
                continue
            rel = str(path.relative_to(repo_root)).replace(os.sep, "/")
            items.append((rel, mtime))

    items.sort(key=lambda item: item[1], reverse=True)
    return items[:limit]


def _cap_items(items: list, max_items: Optional[int]) -> tuple[list, int]:
    """Return capped items and remaining count."""
    if max_items is None or max_items <= 0 or len(items) <= max_items:
        return items, 0
    return items[:max_items], len(items) - max_items


def render_tree(repo_root: Path, chain: list[str], mode: str, recent_md: int) -> str:
    """Render layer tree either in full or compact cumulative mode."""
    current = chain[-1]
    lines: list[str] = []

    # Header: layer stack
    lines.append(color("Layer Stack", BOLD, CYAN))
    for i, layer in enumerate(chain):
        marker = "●" if layer == current else "○"
        badge = color(
            f"[L{i}]", BOLD, GREEN if layer == current else (BLUE if i == 0 else YELLOW)
        )
        suffix = color("  ← current", BOLD, GREEN) if layer == current else ""
        lines.append(f"  {marker} {badge}  {layer}{suffix}")

    lines.append("")
    lines.append(color(".github/", BOLD, CYAN))

    override_paths = load_override_paths(repo_root)

    # First pass: collect all
    category_data: list[tuple[str, list[TreeEntry]]] = []
    for cat_name, rel_dir, exts in CATEGORIES:
        entries = scan_category(repo_root, rel_dir, exts, current)
        category_data.append((cat_name, entries))

    tree_level_cap: Optional[int] = None

    if mode == "auto":
        if len(chain) > 1:
            mode = "full"
            category_data = [
                (cat_name, [entry for entry in entries if entry.layer == current])
                for cat_name, entries in category_data
            ]
            category_data = [
                (cat_name, entries) for cat_name, entries in category_data if entries
            ]
        else:
            mode = "full"
            tree_level_cap = 3

    if mode == "compact":
        lines.append(color(".github/ (compact summary)", BOLD, CYAN))
        for category, entries in category_data:
            counts = _layer_counts(entries)
            if category == "agents":
                role_count = sum(
                    1
                    for entry in entries
                    if Path(entry.rel_path).name.startswith("generic-")
                )
                core_count = len(entries) - role_count
                lines.append(
                    f"- {category}: total={len(entries)} core={core_count} roles={role_count} | {_format_layer_summary(counts, chain)}"
                )
            else:
                lines.append(
                    f"- {category}: total={len(entries)} | {_format_layer_summary(counts, chain)}"
                )

        recent = _recent_markdown(repo_root, recent_md)
        lines.append("")
        lines.append(color(f"Latest Markdown Changes (top {len(recent)})", BOLD, CYAN))
        if not recent:
            lines.append("- none")
        else:
            for rel, mtime in recent:
                stamp = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M")
                lines.append(f"- {stamp}  {rel}")

        lines.append("")
        lines.append(
            color(
                f"Summary: {len(override_paths)} registered override path(s)",
                CYAN,
            )
        )
        return "\n".join(lines)

    if not category_data:
        lines.append(color("└── (no assets owned by current layer)", DIM))
        lines.append("")
        lines.append(
            color(
                f"Summary: {len(override_paths)} registered override path(s)",
                CYAN,
            )
        )
        return "\n".join(lines)

    # Second pass: render
    category_data, category_remaining = _cap_items(category_data, tree_level_cap)
    last_cat = category_data[-1][0] if category_data else ""
    for cat_name, entries in category_data:
        is_last_cat = cat_name == last_cat and category_remaining == 0
        branch = "└── " if is_last_cat else "├── "
        sub_branch = "    " if is_last_cat else "│   "

        cat_label = color(f"{cat_name}/", BOLD, CYAN)
        lines.append(f"{branch}{cat_label}  [{len(entries)} items]")

        # Group by subdirectory for instructions
        if cat_name == "instructions":
            subgroups: dict[str, list[TreeEntry]] = {}
            for e in entries:
                rel = Path(e.rel_path)
                # rel = .github/instructions/<subgroup>/<file>
                parts = rel.parts
                if len(parts) >= 4:
                    subgroup = parts[2]  # e.g. "stages", "agile-coach"
                else:
                    subgroup = "_root"
                subgroups.setdefault(subgroup, []).append(e)

            subgroup_names = sorted(subgroups.keys())
            subgroup_names, subgroup_remaining = _cap_items(
                subgroup_names, tree_level_cap
            )
            for sg_idx, sg_name in enumerate(subgroup_names):
                sg_entries = subgroups[sg_name]
                is_last_sg = (
                    sg_idx == len(subgroup_names) - 1 and subgroup_remaining == 0
                )
                sg_branch = f"{sub_branch}{'└── ' if is_last_sg else '├── '}"
                sg_sub = f"{sub_branch}{'    ' if is_last_sg else '│   '}"
                lines.append(f"{sg_branch}{color(sg_name + '/', CYAN)}")
                sg_entries, sg_entry_remaining = _cap_items(sg_entries, tree_level_cap)
                for e_idx, e in enumerate(sg_entries):
                    is_last_e = (
                        e_idx == len(sg_entries) - 1 and sg_entry_remaining == 0
                    )
                    e_branch = f"{sg_sub}{'└── ' if is_last_e else '├── '}"
                    lines.append(
                        _render_entry(e, e_branch, chain, current, override_paths)
                    )
                if sg_entry_remaining:
                    lines.append(
                        f"{sg_sub}└── {color(f'... (+{sg_entry_remaining} more entries)', DIM)}"
                    )

            if subgroup_remaining:
                lines.append(
                    f"{sub_branch}└── {color(f'... (+{subgroup_remaining} more groups)', DIM)}"
                )
        elif cat_name == "agents":
            role_entries = [
                e for e in entries if Path(e.rel_path).name.startswith("generic-")
            ]
            core_entries = [e for e in entries if e not in role_entries]

            if role_entries:
                lines.append(f"{sub_branch}├── {color('core/', CYAN)}")
                core_sub = f"{sub_branch}│   "
                core_entries, core_remaining = _cap_items(core_entries, tree_level_cap)
                for idx, e in enumerate(core_entries):
                    is_last = idx == len(core_entries) - 1 and core_remaining == 0
                    e_branch = f"{core_sub}{'└── ' if is_last else '├── '}"
                    lines.append(
                        _render_entry(e, e_branch, chain, current, override_paths)
                    )
                if core_remaining:
                    lines.append(
                        f"{core_sub}└── {color(f'... (+{core_remaining} more entries)', DIM)}"
                    )

                lines.append(f"{sub_branch}└── {color('roles/', CYAN)}")
                roles_sub = f"{sub_branch}    "
                role_entries, roles_remaining = _cap_items(role_entries, tree_level_cap)
                for idx, e in enumerate(role_entries):
                    is_last = idx == len(role_entries) - 1 and roles_remaining == 0
                    e_branch = f"{roles_sub}{'└── ' if is_last else '├── '}"
                    lines.append(
                        _render_entry(e, e_branch, chain, current, override_paths)
                    )
                if roles_remaining:
                    lines.append(
                        f"{roles_sub}└── {color(f'... (+{roles_remaining} more entries)', DIM)}"
                    )
            else:
                entries, entry_remaining = _cap_items(entries, tree_level_cap)
                for idx, e in enumerate(entries):
                    is_last = idx == len(entries) - 1 and entry_remaining == 0
                    e_branch = f"{sub_branch}{'└── ' if is_last else '├── '}"
                    lines.append(
                        _render_entry(e, e_branch, chain, current, override_paths)
                    )
                if entry_remaining:
                    lines.append(
                        f"{sub_branch}└── {color(f'... (+{entry_remaining} more entries)', DIM)}"
                    )
        else:
            entries, entry_remaining = _cap_items(entries, tree_level_cap)
            for idx, e in enumerate(entries):
                is_last = idx == len(entries) - 1 and entry_remaining == 0
                e_branch = f"{sub_branch}{'└── ' if is_last else '├── '}"
                lines.append(_render_entry(e, e_branch, chain, current, override_paths))
            if entry_remaining:
                lines.append(
                    f"{sub_branch}└── {color(f'... (+{entry_remaining} more entries)', DIM)}"
                )

    if category_remaining:
        lines.append(
            f"└── {color(f'... (+{category_remaining} more categories)', DIM)}"
        )

    lines.append("")
    lines.append(
        color(
            f"Summary: {len(override_paths)} registered override path(s)",
            CYAN,
        )
    )

    return "\n".join(lines)


def _render_entry(
    e: TreeEntry,
    prefix: str,
    chain: list[str],
    current: str,
    override_paths: set[str],
) -> str:
    badge = layer_badge(e.layer, chain, current)
    short = Path(e.rel_path).name
    registry_path = to_registry_path(e.rel_path)

    status = ""
    if e.layer == current and registry_path in override_paths:
        status = color("  ⛭ override-registered", BOLD, RED)
    elif e.layer == current:
        status = color("  ✦ local-layer", GREEN)
    elif registry_path in override_paths:
        status = color("  ◌ overridden-by-child", DIM)

    # Dim inherited files
    if e.layer == current:
        name_str = color(short, BOLD)
    elif e.layer in chain:
        name_str = color(short, DIM)
    else:
        name_str = short

    return f"{prefix}{badge} {name_str}{status}"


# ---------------------------------------------------------------------------
# Legend
# ---------------------------------------------------------------------------


def render_legend(chain: list[str]) -> str:
    """TODO: add docstring for render_legend."""
    current = chain[-1]
    lines = ["", color("Legend", BOLD, CYAN)]
    lines.append(f"  {color('[L0]', BLUE)}   Base layer (oldest ancestor)")
    for i in range(1, len(chain) - 1):
        lines.append(f"  {color(f'[L{i}]', YELLOW)}   Intermediate layer: {chain[i]}")
    lines.append(
        f"  {color(f'[L{len(chain) - 1}]', BOLD, GREEN)}   Current layer: {current}"
    )
    lines.append(f"  {color('[??]', DIM)}   No layer annotation found")
    lines.append(
        f"  {color('✦ local-layer', GREEN)}  Local file owned by current layer"
    )
    lines.append(
        f"  {color('⛭ override-registered', BOLD, RED)}  Explicit override from .digital-team/overrides.yaml"
    )
    lines.append(
        f"  {color('◌ overridden-by-child', DIM)}  Parent-layer file path registered as child override"
    )
    lines.append(
        "  Status markers use colour + symbols for accessibility in dense trees"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """TODO: add docstring for main."""
    parser = argparse.ArgumentParser(description="Render layered .github asset tree")
    parser.add_argument("repo_root", nargs="?", default=".")
    parser.add_argument(
        "--mode",
        choices=["auto", "full", "compact"],
        default="auto",
        help="auto shows only current layer for Layer>0, and capped full-tree for Layer0",
    )
    parser.add_argument(
        "--recent-md",
        type=int,
        default=20,
        help="number of recently modified markdown files to list in compact mode",
    )
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    chain = read_layer_chain(repo_root)

    print(render_tree(repo_root, chain, mode=args.mode, recent_md=args.recent_md))
    print(render_legend(chain))
    print()


if __name__ == "__main__":
    main()
