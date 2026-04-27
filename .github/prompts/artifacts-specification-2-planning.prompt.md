<!-- layer: digital-generic-team -->
# /artifacts-specification-2-planning Prompt

Create or update GitHub project, generate epics/stories, and trigger generic delivery agents.

## Skill

- **Skill**: `artifacts`
- **Owner**: `agile-coach`

## Parameters

- `stage=<stage>` — Target stage code (e.g., `00-exploration`, `05-project`). Extended stages (10+) are managed in downstream layers.

## Execution contract

**Precondition**: The canonical stage document must exist at `.digital-artifacts/40-stage/<STAGE>.md`

If no stage document exists, this prompt does nothing.

1. **GitHub Project Check**:
  - Search for existing linked GitHub project for this stage/item
   - If project exists: verify it's current; update if needed
   - If no project: create new project with name `<item_code>-<stage>` in repository

2. **Work Structure Generation**:
   - Create Epics (high-level work groupings) with:
     - Theme name and description synthesized from validated source specifications
     - Outcome summary and measurable success signals
     - Explicit milestone metadata (`milestone_id`, `sprint_hint`)
   - Create Stories (meta-planning items in this layer) with:
     - Coordination intent and planning boundary grounded in the synthesized problem/scope
     - Readiness signals and linked execution tasks
     - Linked epic
     - `agile-coach` as owner
   - Create Tasks (technical work items) with:
     - Definition of Done checklist
     - Acceptance criteria for executable completion
     - Owner role label
     - Linked story
     - Explicit milestone metadata (`milestone_id`, `sprint_hint`)
   - Create parallel transparency documentation in `docs/wiki/` with:
     - One dedicated explainer page per major epic/theme or tightly related story cluster
     - Plain-language summaries for domain outsiders and stakeholders
     - Supporting visual artifacts such as Mermaid diagrams, exported Mermaid SVGs, UX scribbles, or other simplified visual explainers

3. **Labeling Strategy**:
   - `type:epic`, `type:story`, `type:task`
   - `role:<agent-name>` for delivery agent identification
   - `stage:<stage-code>` for filtering
   - `status:ready`, `status:in-progress`, `status:blocked`
   - Custom labels based on specification metadata

4. **Detailed Descriptions**:
   - Epic and story issues include:
     - Problem statement / context
     - Meta-planning summary appropriate for backlog hierarchy
     - Links to child items and source specification bundle
     - Milestone planning hints for later sprint planning
     - Links to corresponding `docs/wiki/` explanation pages and visualization artifacts when available
   - Task and bug issues include:
     - Problem statement / context
     - Acceptance criteria
     - Definition of Done
     - Links to source specification and bundle
     - Milestone planning hints for later sprint planning
  - Templates applied from `.github/skills/stages-action/templates/`

5. **Enterprise Quality Gate (mandatory)**:
  - Reject generic placeholders such as `Extraction`, `Content`, `Address: Extraction`, `TODO`, and similar noise.
  - Reject output where epic/story/task title does not communicate domain intent.
  - Reject forced user-story phrasing for meta-planning items when the item is not a real end-user story.
  - Ensure each generated artifact can answer: what is delivered, for whom, why now, and how success is measured.

6. **Delivery Agent Dispatch**:
   - Once project is ready, scan all issues labeled with agent roles
   - Trigger all generic delivery agents in parallel:
     - Each agent pulls issues matching their role from the project
     - Agents work autonomously to implement their assigned work
     - Agents report completion back to project
  - Where stakeholder understanding is important, agile-coach may additionally hand off to `ux-designer` for explainers, diagrams, scribbles, and presentation-ready assets
   - Agents continue polling for new issues until project is marked as complete

## Default command

```bash
make artifacts-specification-2-planning stage=<stage>
```

## Documentation contract

- Reads from `.digital-artifacts/40-stage/`
- Writes to GitHub: project, issues, labels
- Writes locally: `.digital-artifacts/50-planning/<stage>/` with epic/story/task/bug specs and dispatch traces
- Writes locally: `docs/wiki/` with stakeholder-oriented explainers and linked visuals for major epic/story themes
- Maintains traceability back to original bundle
- Keeps epic/story issues as agile-coach-owned meta issues; adds only executable task/bug issues to the active project board

## Verification

- GitHub project created/updated: repository projects tab
- All issues labeled correctly and linked to epic/story
- Audit: `.digital-artifacts/50-planning/<stage>/DISPATCH_<item_code>.md`
- Agents active: delivery agents begin polling for work
