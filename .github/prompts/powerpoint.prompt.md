<!-- layer: digital-generic-team -->
# /powerpoint Prompt

Generate a stakeholder-ready presentation from a source file or folder.

The canonical behavior contract is skill-first and defined by:
- `.github/skills/powerpoint/SKILL.md`
- `.github/agents/ux-designer.agent.md` (Stakeholder Visualization Contract)
- `presentation.instructions.md` (Enterprise Presentation Standard)

## Context

**Layer vs. App context matters:**
- When visualizing a layer itself (tooling, agent catalog, governance), favour the layer's own template and include team/architecture slides.
- When inside an app repository, focus on the app's domain: features, user flows, technical decisions, and roadmap.

The template name encodes the layer (`<layer>_template.pptx`) but the content strategy must match the repository context.

## Template Slides and Their Purpose

The standard 7-slide template contains distinct slide types. Select and populate them deliberately:

| Slide | Type | When to Use |
|-------|------|-------------|
| 1 | Title | Always — deck title, date, author |
| 2 | Agenda | When deck has ≥ 3 topics — list the 3 main themes |
| 3 | Chapter Title | Introduce each major section break |
| 4 | Content | One key message per slide — use for findings, decisions, concepts |
| 5 | Our Team | Include when audience is unfamiliar with the team |
| 6 | Thank You | Always — close with a clear next step or call to action |
| 7 | Schema (BACKUP) | Reference only — never shown to the audience |

Unused template slides move behind the `BACKUP` divider automatically.

## The Rule of Three

A presentation is experienced live by an audience. Human attention and short-term memory work in threes:
- Limit each slide to **at most 3 key points**.
- Limit the agenda to **at most 3 main themes** (or 3 clusters of themes).
- State the **3 most important decisions or takeaways** in the closing slide.

This is not a structural hierarchy — it is a perceptual principle. A slide with 7 bullets is a document, not a slide.

## Execution Contract

1. Require `SOURCE` as input path (file or folder of markdown/text artifacts).
2. Detect context: is this a layer visualization or an app/product deck?
3. Select the correct template for the layer. If missing, create it via `create_standard_template.py`.
4. Clone a working copy — never mutate the base template.
5. Parse `SOURCE` into slide-ready sections using heading structure:
   - Each `##` heading becomes a slide (or chapter-title slide for major breaks).
   - Body content is distilled to 3 or fewer key points per slide.
   - Raw prose is reduced to keywords, statements, or annotated visuals.
6. Map sections to the appropriate template slide type (Content, Chapter Title, etc.).
7. Discover and embed visual assets (mermaid exports, architecture diagrams, scribbles) where available.
8. Apply readability checks:
   - No text/visual overlap.
   - Sufficient contrast between foreground text and background.
   - Each slide communicates a single, clear message.
9. Place team slide at visible position when audience is unfamiliar with the team.
10. Append BACKUP divider followed by unused template slides for reviewer reference.
11. Write output to `docs/wiki/assets/` (for wiki-published decks) or `docs/powerpoints/` (for delivery artifacts).
12. Return deterministic JSON output with template path, output path, and source trace metadata.

## Information Flow

- producer: user invoking `/powerpoint` or UX Designer workflow
- consumer: `prompt-powerpoint` skill via agent runtime
- trigger: explicit presentation request with a `SOURCE` path
- payload summary: `SOURCE`, layer context, template path, discovered visuals, and generated deck path

## Documentation Contract

- Keep prompt behavior skill-first and deterministic.
- Keep this command listed exactly once in `/help`.
- Keep matching skill metadata in `skills/prompt-powerpoint/SKILL.md`.
- Presentation quality rules live in `presentation.instructions.md`, not in this prompt.
