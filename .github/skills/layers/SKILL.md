---
name: layers
description: Builds a color-annotated treeview of the .github/ directory grouped by origin layer, based on the layer frontmatter keyword. Detects overrides where the same file appears in multiple layers.
user-invocable: false
layer: digital-generic-team
---

# Skill: Layers

Renders a treeview of `.github/` assets annotated with the layer that owns each file.

Default rendering mode is compact (cumulative counts + latest markdown updates).
Use `LAYERS_MODE=full` to render the full detailed tree.

## Script

- `scripts/layers-tree.py` — scans `.github/`, reads layer annotations, renders tree

## Usage

```bash
source .digital-runtime/layers/python-runtime/venv/bin/activate
python3 .github/skills/layers/scripts/layers-tree.py [repo-root]
```

## Covered Categories

| Category | Path |
|----------|------|
| agents | `.github/agents/` |
| skills | `.github/skills/` |
| instructions | `.github/instructions/` (incl. subdirs like `stages/`) |
| prompts | `.github/prompts/` |
| handoffs | `.github/handoffs/` |
| hooks | `.github/hooks/` |
| make | `.github/make/` |

Special grouping:
- In `agents/`, generic agents (`generic-*`) are grouped under `roles/`.

## Layer Detection

Layer ownership is extracted from:
- YAML frontmatter `layer: <name>` in `.md` files
- `# layer: <name>` comment in `.sh` and `.mk` files
- `<!-- layer: <name> -->` HTML comment in `.md` prompt files
- Top-level `layer: <name>` in `.yaml` files

Override ownership is read from `.digital-team/overrides.yaml` (`overrides[].path`).

## Color Coding

| Color | Meaning |
|-------|---------|
| Green bold | Current layer (the repo being viewed) |
| Yellow | Intermediate parent layer |
| Blue | Base layer (L0) |
| Dim | No layer annotation found |
| Red bold | Registered override (`⛭ override-registered`) |
| Green | Local layer file (`✦ local-layer`) |
| Dim | Parent path marked as overridden (`◌ overridden-by-child`) |

## Information Flow

| Field    | Value |
|----------|-------|
| Producer | Agent or developer invoking `/layers` |
| Consumer | Chat output / terminal |
| Trigger  | User invokes `/layers` |
| Payload  | Tree with ANSI color annotations and override markers |

## Dependencies

- Python 3.11+ (standard library only)
- `.digital-team/layers.yaml` — must exist for chain detection
