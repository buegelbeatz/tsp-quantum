"""Inventory helpers for managed artifact bundle metadata."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Iterable


ENTRY_HEADING_RE = re.compile(r"^## Entry: (?P<item_id>.+)$", re.MULTILINE)
DEFAULT_INVENTORY_HEADER = "# INVENTORY\n"


@dataclass(frozen=True)
class InventoryEntry:
    """Structured inventory entry rendered as a markdown section."""

    item_id: str
    created_at: str
    fields: dict[str, str | list[str]]


def ensure_inventory_file(
    inventory_path: Path, template_path: Path | None = None
) -> None:
    """Create an inventory file from template if it does not exist yet."""

    if inventory_path.exists():
        return
    inventory_path.parent.mkdir(parents=True, exist_ok=True)
    template_text = ""
    if template_path and template_path.exists():
        template_text = template_path.read_text(encoding="utf-8").strip()
    inventory_path.write_text(
        (template_text or DEFAULT_INVENTORY_HEADER).rstrip() + "\n", encoding="utf-8"
    )


def append_inventory_entry(
    inventory_path: Path, entry: InventoryEntry, template_path: Path | None = None
) -> None:
    """Upsert a markdown inventory entry by item id."""

    ensure_inventory_file(inventory_path, template_path)
    header, entries = split_inventory(inventory_path.read_text(encoding="utf-8"))
    rendered = render_inventory_entry(entry)
    entries_by_id = {item_id: section for item_id, section in entries}
    order = [item_id for item_id, _section in entries if item_id != entry.item_id] + [
        entry.item_id
    ]
    entries_by_id[entry.item_id] = rendered
    write_inventory(
        inventory_path, header, [entries_by_id[item_id] for item_id in order]
    )


def split_inventory(content: str) -> tuple[str, list[tuple[str, str]]]:
    """Split an inventory markdown file into header and entry sections."""

    normalized = content.strip()
    if not normalized:
        return DEFAULT_INVENTORY_HEADER, []
    first_entry = normalized.find("## Entry:")
    if first_entry == -1:
        return normalized + "\n", []

    header = normalized[:first_entry].rstrip() + "\n"
    parsed_entries: list[tuple[str, str]] = []
    for raw_entry in re.split(
        r"(?=^## Entry: )", normalized[first_entry:], flags=re.MULTILINE
    ):
        section = raw_entry.strip()
        if not section:
            continue
        match = ENTRY_HEADING_RE.match(section.splitlines()[0])
        if match:
            parsed_entries.append((match.group("item_id").strip(), section))
    return header, parsed_entries


def render_inventory_entry(entry: InventoryEntry) -> str:
    """Render a markdown inventory section from generic field mappings."""

    lines = [f"## Entry: {entry.item_id}", f"- created_at: {entry.created_at}"]
    for key, value in entry.fields.items():
        if isinstance(value, list):
            lines.append(f"- {key}:")
            lines.extend(f"  - {item}" for item in value)
        else:
            lines.append(f"- {key}: {value}")
    return "\n".join(lines)


def write_inventory(inventory_path: Path, header: str, entries: Iterable[str]) -> None:
    """Write a normalized inventory file."""

    sections = [entry.strip() for entry in entries if entry.strip()]
    content = header.strip() or DEFAULT_INVENTORY_HEADER.strip()
    if sections:
        content = content + "\n\n" + "\n\n".join(sections)
    inventory_path.write_text(content.strip() + "\n", encoding="utf-8")
