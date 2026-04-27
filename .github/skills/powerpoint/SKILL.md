---
name: "powerpoint"
description: "Build deterministic PowerPoint decks from repository sources and layer templates."
layer: digital-generic-team
---

# Skill: PowerPoint

## Purpose
Generate reusable layer-scoped PowerPoint templates and build decks from a source file or folder.

Stakeholder-facing decks must optimize for comprehension by non-technical audiences through simplified visuals, clear narrative flow, and restrained text density.

Templates include:
- Title slide with futuristic SVG background
- Agenda slide (dark mode, 3 default sections)
- Chapter Title slide
- Slide/Content page
- **Our Team slide with all non-generic agents** (polaroid-style portraits + role titles)
- Thank You slide
- Schema slide (brand colours + typography specification)

## Features

### Team Portraits
The template now includes a dedicated team member slide with all non-generic agents:

- **Portrait Extraction**: Uses the `portraits.png` sprite sheet (1254x1254, 5x5 grid of 25 diverse portraits)
- **Deterministic Selection**: Each portrait is selected based on a deterministic seed, ensuring reproducible team slides
- **Polaroid Card Rendering**: Rounded-corner portrait frames with one thin white border and role labels below the frame
- **Agent-Driven Titles**: Agent titles are loaded from `.github/agents/*.agent.md` and generic agents are excluded
- **Adaptive Layout**: Grid scales to fit all non-generic agents on one slide

**Example portrait slide generation:**
```python
from template_factory import create_template
from pathlib import Path

template_path = Path("my_template.pptx")
create_template(Path("."), "my-layer", template_path)
# Template now includes: title, agenda, chapter title, slide, team, thank you, schema
```

### Portrait Sprite Sheet
The `templates/portraits.png` file contains a 5x5 grid of 25 unique portraits:
- Each portrait: 250x250 pixels
- Total image: 1254x1254 pixels
- Stored as 8-bit RGB PNG

Portraits are extracted programmatically based on deterministic indices/seeds.

## Inputs
- `source`: File or folder that provides text content for slides.
- `template`: `.github/skills/powerpoint/templates/<layer>_template.pptx`.
- Preferred source material for stakeholder decks includes `docs/wiki/`, approved UX scribbles, Mermaid SVG exports, and simplified architecture visuals.

## Outputs
- Template `.pptx` under `templates/` when missing:
  - Title slide (deterministic SVG background)
  - Agenda slide (dark mode)
  - Chapter Title slide
  - Slide/Content page
  - Our Team slide (all non-generic agents with polaroid-style portraits)
  - Thank You slide
  - Schema slide (colours and typography)
- Generated deck under `docs/powerpoints/`.

## Entry Points
- `scripts/create_standard_template.py` — Create layer template with team portraits
- `scripts/build_from_source.py` — Build presentations from source content
- `scripts/review_generated_deck.py` — Score generated decks against template and stakeholder quality heuristics
- `scripts/powerpoint.sh` — CLI entrypoint

## Built-in Reviewer Gate

`powerpoint.sh` now runs a mandatory reviewer pass directly after generation.

- Reviewer input: generated deck + active template (`<layer>_template.pptx`)
- Reviewer output artifacts:
  - `.digital-artifacts/60-review/powerpoint/<date>/<deck-slug>-quality-review.json`
  - `.digital-artifacts/60-review/powerpoint/<date>/<deck-slug>-quality-review.md`
- Reviewer dimensions (1-5 each):
  - Template Compliance
  - Narrative Structure
  - Text Density
  - Content Hygiene
  - User Lens

Default gate behavior:

- `POWERPOINT_QUALITY_GATE=1` (enabled)
- `POWERPOINT_QUALITY_STRICT=1` (fail generation when below threshold)
- `POWERPOINT_QUALITY_MIN_SCORE=4.0`

When strict mode is active, generation exits non-zero unless recommendation is `proceed` and score threshold is met.

## New Modules

### `powerpoint_portraits.py`
Handles portrait extraction and sprite sheet management:
- `get_portrait_by_index(index)` — Extract portrait by position (0-24)
- `get_portrait_by_seed(seed)` — Extract portrait deterministically using seed
- `portrait_to_png_file(portrait)` — Convert portrait to temporary PNG for embedding
- `get_portrait_png_file_by_seed(seed)` — Convenience wrapper

### `template_factory.py` (Enhanced)
Now includes:
- `_add_agenda_slide(slide)` — Add dark-mode agenda with 3 standard sections
- `_add_team_slide(slide, seed, repo_root)` — Add all non-generic agents with polaroid-style portraits and titles
- `_add_color_schema_slide(slide)` — Add schema page with colour swatches and typography specs
- `create_template()` — Creates 7-slide template in standardized order

## Dependencies
- `.github/skills/shared/shell/SKILL.md`
- `.github/skills/ui-scribble/SKILL.md`
- `PIL/Pillow` — Image manipulation
- `python-pptx` — PowerPoint generation
- `cairosvg` — SVG to PNG rendering

## Information Flow
- **producer**: `/powerpoint` prompt or UX Designer runtime command
- **consumer**: `powerpoint` skill scripts (template generation, presentation building)
- **trigger**: explicit slide generation request or template creation
- **payload summary**: source path, layer id, deterministic seed context, portrait selection, and target output path

## Stakeholder Deck Rules

- Prefer one strong visual with a short takeaway over dense bullet-heavy slides.
- Reuse approved `docs/wiki/` diagrams and `docs/ux/scribbles/` artifacts where possible.
- When showing architecture, reduce it to stakeholder-relevant actors, flows, and decisions.
- When showing UX, prefer scribbles, annotated flows, and before/after concepts to raw requirement prose.

## Granular Assembly Workflow

Use this deterministic workflow for stakeholder-facing generation:

1. Resolve `SOURCE` and layer context.
2. Ensure template exists (create if missing).
3. Clone a working copy from the template and keep the base template immutable.
4. Insert a first-slide `BACKUP` separator marker.
5. Identify style source slide (schema/style page) and extract typography, color palette, and spacing heuristics.
6. Analyze `SOURCE` and derive a temporary markdown structure with 3-level decomposition:
  - chapter/theme,
  - section/subtopic,
  - statement/evidence/action.
7. For each heading/subheading, select and adapt candidate slides from the region behind `BACKUP`.
8. For visualizations, use approved visualization skills or agent consultation when needed.
9. Compose final slides and remove unused placeholders.
10. Emit deterministic output metadata (template path, output path, source trace).

## Slide Quality Gates (Mandatory)

Every assembled slide must pass:

- No text overlaps with visuals or shape regions.
- Foreground/background contrast is readable for human audiences.
- Text density remains concise (prefer keywords and statements over dense prose).
- Visuals support the narrative instead of duplicating long text blocks.

## Visualization Extension

- Visualization support may be requested from other approved agents or visualization-focused skills.
- Generated or imported visuals must align with the UX Stakeholder Visualization Contract in `.github/agents/ux-designer.agent.md`.

## Testing
```bash
pytest scripts/tests/test_powerpoint_portraits.py -v
pytest scripts/tests/test_template_factory.py -v
```

Available tests for portraits:
- Index-based extraction and wrapping
- Deterministic seed-based selection
- PNG file generation
- Different seeds produce different portraits
