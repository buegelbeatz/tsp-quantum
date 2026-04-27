---
name: "Quality-expert / Presentation"
description: "Enterprise Presentation Standard — how to build and deliver stakeholder-ready presentations"
applyTo: "**"
layer: digital-generic-team
---

# Enterprise Presentation Standard

Presentations are experienced live by a human audience. A PowerPoint is not a document — it is a stage prop. These rules govern how decks are structured and how each slide is written.

---

## Audience First

Before generating any slide, answer three questions:

1. **Who is in the room?** (technical team, sponsor, board, client)
2. **What decision or response is needed after this presentation?**
3. **How much time is available?**

Every structural and content choice follows from these answers.

---

## The Rule of Three

Human short-term memory reliably holds three items. This is not a hierarchy — it is a perceptual limit.

- **Agenda:** Maximum 3 main themes. If more topics exist, cluster them into 3 groups.
- **Slide content:** Maximum 3 key points per slide. If a slide needs more, split it.
- **Closing takeaway:** State exactly 3 things the audience must remember after leaving.

A slide with more than 3 bullets is a document fragment, not a slide.

---

## Slide Types and Their Rules

Each slide type in the standard template has a distinct purpose and usage rule:

### Title Slide
- Purpose: Name the presentation, anchor the context, and date it.
- Rules: Include the title, the occasion or meeting name, and the date. Nothing else.
- Anti-pattern: Subtitles that already summarize the full agenda.

### Agenda Slide
- Purpose: Signal the structure so the audience can orient themselves.
- Rules: Show 3 items (or 3 clusters). No detail — just the theme labels.
- When to include: When the deck has 3 or more distinct topics.
- When to skip: For short, single-topic briefings.

### Chapter Title Slide
- Purpose: Separate major sections visually and mentally.
- Rules: One line — the chapter name. Optionally a one-sentence framing question.
- Anti-pattern: Putting content on a chapter title slide.

### Content Slide
- Purpose: Communicate one idea, finding, decision, or argument.
- Rules:
  - One key message per slide (stated in the slide title, not the body).
  - Body: at most 3 bullet points or one strong visual.
  - Every bullet must be a complete statement, not a keyword fragment.
  - Use visuals (diagrams, charts, scribbles) when they replace explanation better than text.
- Anti-pattern: Dense paragraphs, 6+ bullets, no conclusion in the title.

### Our Team Slide
- Purpose: Make the team visible and credible to unfamiliar audiences.
- Rules: Show role title and portrait. No CVs, no long bios.
- When to include: Sponsor briefings, client meetings, kickoffs. Omit for internal team stand-ups.

### Thank-You / Closing Slide
- Purpose: Signal the end and drive the next action.
- Rules: End with a concrete next step or call to action. Must be one sentence.
- Anti-pattern: "Thank you" with nothing else — missed opportunity to drive action.

### BACKUP Section (behind divider)
- Purpose: Reserve slides for Q&A, deeper reference, or reviewer access.
- Rules: Never shown during the main presentation. Contains template reference slides and detail slides that were cut for time.

---

## Content Quality Rules

### Titles are headlines, not labels
- Bad: "Architecture"
- Good: "The three-layer architecture reduces deployment risk"

### One message per slide
Split a slide whenever it contains more than one independent idea, not when it is "too long".

### Visuals replace text
If a diagram or chart makes the point better than bullets, use it instead — not in addition to.

### No jargon without definition
Technical terms that the audience may not know must be defined on first use or delegated to a BACKUP slide.

### Consistent tense and voice
Use present tense for current state, future tense for planned actions. Avoid passive voice.

---

## Deck Structure for Common Scenarios

### Sponsor Briefing (5–7 slides)
1. Title
2. Executive Summary (status + 1 key risk)
3. Delivery Focus (goals and current scope)
4. Constraints and Risks
5. Decision and Next Step
6. Thank You + call to action
7. BACKUP: detailed plan, open items

### Project Kickoff (8–10 slides)
1. Title
2. Agenda
3. Chapter: Context — Vision + Goal
4. Chapter: Scope — In / Out of Scope
5. Chapter: Plan — Milestones + Owners
6. Our Team
7. Open Questions
8. Thank You + immediate next step
9. BACKUP: technical details, risk register

### Layer / Tooling Overview (6–8 slides)
1. Title
2. Agenda
3. What the layer provides (3 capabilities)
4. How it is structured (architecture / agent map)
5. Our Team (roles and agents)
6. How to get started (3 steps)
7. Thank You
8. BACKUP: full skill catalog, instruction index

---

## Relationship to Other Standards

- PowerPoint generation behavior: `.github/skills/powerpoint/SKILL.md`
- Prompt contract: `.github/prompts/powerpoint.prompt.md`
- UX Stakeholder Visualization Contract: `.github/agents/ux-designer.agent.md`
- Stage-specific context: `.github/instructions/stages/`

When a stage instruction (e.g., `05-project.instructions.md`) calls for a presentation artifact, the structure for that stage governs which scenario template above applies.
