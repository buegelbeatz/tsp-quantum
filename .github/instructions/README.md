---
layer: digital-generic-team
---
# instructions

## Purpose

**Instructions** define role-specific standards, workflows, and best practices. They embody organizational knowledge about how to work well in specific domains and roles.

## Hierarchy

Instructions are organized in layers:

1. **Role Instructions** (top-level)
   - Focus: A specific professional role or expertise area.
   - Scope: Person/team perspective; values, principles, process.
   - Examples: `language-expert/`, `fullstack-engineer/`, `security-expert/`.
   - Content: Standards, conventions, decision frameworks.

2. **Domain Instructions** (functional groups)
   - Focus: A technology, framework, or system category.
   - Scope: How to work effectively with that domain.
   - Examples: `api-rest/`, `docker/`, `postgres/`, `kubernetes/`.
   - Content: Best practices, configuration patterns, troubleshooting.

3. **Stage Instructions** (project lifecycle — digital-generic-team scope)
   - Focus: What work to prioritize at each project phase.
   - Scope: Early exploration and project setup (Layer 0 scope).
   - Examples: `00-exploration/`, `05-project/`.
   - Content: Acceptance criteria, deliverables, gate checks.
   - Note: Extended stages (Ideation–Pilot) are managed in downstream layers (digital-iot-team, digital-home-app, etc.).

## Structure

Each instruction lives in `instructions/{role-or-domain}/` and includes:

```
instructions/language-expert/
├── README.md                    # Overview (this file, optional)
├── python.instructions.md       # Python language standards
├── java.instructions.md         # Java language standards
└── rust.instructions.md         # Rust language standards
```

### Anatomy of an Instruction File

Every instruction file (`*.instructions.md`) uses this frontmatter and structure:

```yaml
---
name: "Role / Domain"
description: "One-line summary"
layer: {layer-name}
---

# Title

## Scope
- Who uses this instruction? (e.g., all developers, security team)
- What contexts apply? (e.g., all projects, Python projects only)

## Principles
2-3 foundational beliefs that guide the instruction.

## Standards
### Rule 1: ...
Details and rationale.

### Rule 2: ...
Details and rationale.

## Process
Step-by-step workflows or checklists.

## References
Links to related instructions, external docs, examples.
```

## Role Categories

### Technical Roles

**language-expert/** — Programming language standards & conventions
- `python.instructions.md` — Type hints, testing, style
- `java.instructions.md` — OOP patterns, build, dependency management
- `typescript.instructions.md` — Module systems, async, tooling
- `bash.instructions.md` — Shell scripting safety and clarity

**fullstack-engineer/** — Application architecture & integration
- `backend.instructions.md` — Server design, API contracts, database
- `frontend.instructions.md` — UI frameworks, state, accessibility
- `react.instructions.md` — Component patterns, hooks, testing
- `mobile.instructions.md` — Platform conventions, distribution

**data-scientist/** — Analytics, ML, research workflows
- `jupyter.instructions.md` — Notebook best practices, reproducibility
- `science-standards.instructions.md` — Experiment tracking, publish standards
- `machine-learning.instructions.md` — Model development, validation, deployment

**container-expert/** — Containerization & orchestration
- `docker.instructions.md` — Dockerfile patterns, image optimization
- `kubernetes.instructions.md` — Cluster architecture, resource management
- `podman.instructions.md` — Rootless containers, security

**database-expert/** — Data storage & query optimization
- `postgres.instructions.md` — Schema design, indexing, tuning
- `relational.instructions.md` — Normalization, transactions, integrity
- `triplestore.instructions.md` — RDF, SPARQL, semantic queries

**network-expert/** — Communication protocols & connectivity
- `api-rest.instructions.md` — REST design, HTTP conventions
- `api-graphql.instructions.md` — Schema, resolvers, federation
- `app-mqtt.instructions.md` — MQTT patterns, QoS, broker setup
- `connectivity-wifi.instructions.md` — Network provisioning, security

**security-expert/** — Application & infrastructure security
- `security-standards.instructions.md` — Threat modeling, defense layers
- `owasp.instructions.md` — Top 10 vulnerabilities and mitigations
- `penetration-testing.instructions.md` — Red team methodology

**test-expert/** — Quality assurance & verification
- `testing.instructions.md` — Unit, integration, E2E test strategy
- `e2e-tests.instructions.md` — Test automation frameworks & patterns
- `test-standards.instructions.md` — Coverage targets, reporting

**quality-expert/** — Code quality & architecture
- `cleancode.instructions.md` — Naming, functions, error handling
- `designpatterns.instructions.md` — Creational, structural, behavioral
- `linting.instructions.md` — Style checkers, static analysis
- `documentation.instructions.md` — Docstrings, README, changelog

### Leadership Roles

**agile-coach/** — Project execution & team coordination
- `agile-standards.instructions.md` — Sprint rhythm, ceremonies
- `project-management.instructions.md` — Tracking, stakeholders, risks

**platform-architect/** — System architecture & visualization
- `architecture.instructions.md` — C4 diagrams, decision records
- `mermaid.instructions.md` — Diagram syntax and when to use
- `uml.instructions.md` — Class diagrams, sequence, deployment

**ai-expert/** — Machine learning & NLP
- `llm.instructions.md` — Large language model usage, prompt design
- `machine-learning.instructions.md` — Model selection, training loops
- `huggingface.instructions.md` — Dataset hub, model zoo, inference

### Specialized Roles

**paper-expert/** — Research & academic publication
- `paper.instructions.md` — Writing structure, peer review process
- `jupyter-paper.instructions.md` — Notebook-based papers

**quantum-expert/** — Quantum computing
- `quantum-computing.instructions.md` — Q# language, qubit management
- `quantum-mapping.instructions.md` — Algorithm-to-circuit compilation

## Quality Audits

### What `/quality` Checks for Instructions
- Frontmatter metadata completeness (name, description, layer).
- File naming consistency (`*.instructions.md`, not `.md` alone).
- Structure headers present (Purpose, Standards, Process, References).
- No hardcoded secrets, tokens, or internal paths.
- Markdown formatting valid (no broken links, proper headers).

### What `/quality-fix` Does for Instructions
**Autofix:**
- Adds/fixes frontmatter headers.
- Normalizes file naming to `*.instructions.md`.
- Corrects Markdown syntax.
- Ensures required section headers exist.

**Escalation (manual):**
- Outdated standards (requires domain expert review).
- Conflicting instructions across roles (inheritance/override).
- Missing processes or workflow documentation.

## How to Create an Instruction

### 1. Identify the Role or Domain
- **Role-based:** `language-expert/python.instructions.md` (programming language).
- **Domain-based:** `api-rest.instructions.md` (architectural pattern).
- **Stage-based:** `05-project.instructions.md` (project phase in digital-generic-team scope).

### 2. Determine Scope
- Who is this for? (e.g., "all Python developers" vs. "backend team")
- What projects/codebases apply? (e.g., "all projects" vs. "microservices only")

### 3. Define Principles
- 2–3 core beliefs that drive the instruction.
- Example: "Python code should be explicit over implicit, readable over clever."

### 4. Write Standards
- Organize into logical groups (e.g., "Naming", "Error Handling", "Testing").
- Each standard includes:
  - **Rule:** What to do.
  - **Rationale:** Why (links to external docs, examples).
  - **Example:** Good and bad code samples (if applicable).

### 5. Document Processes
- Step-by-step checklists for common workflows.
- Who is responsible at each step.
- Success criteria (how do you know you're done).

### 6. Add References
- Links to related instructions.
- External documentation (PEP 8, MDN, etc.).
- Tool setup guides (linters, type checkers).

### 7. Layer Governance
- Check if parent layers already define this instruction.
- If overriding: add `override-reason: <why>` to frontmatter.
- If new: ensure no naming collision with parent layers.

### 8. Validate
```bash
make quality        # Checks metadata, formatting, references
make test           # If tests ingest instructions (e.g., linting rules)
```

### Scaffold First

```bash
make scaffold-instruction INSTRUCTION_CATEGORY=<domain> INSTRUCTION_NAME=<topic> INSTRUCTION_PURPOSE="one-line purpose"
make scaffold-instruction INSTRUCTION_CATEGORY=stages INSTRUCTION_NAME=05-project INSTRUCTION_PURPOSE="stage guidance"
```

## Examples

### Language Instruction (language-expert/python.instructions.md)
- Scope: All Python developers, all projects using Python.
- Principles: Explicit over implicit, readable, testable, type-safe.
- Standards: Naming (snake_case), typing (PEP 484), testing (pytest).
- Process: How to set up a new Python module, enable mypy, configure ruff.

### Domain Instruction (api-rest.instructions.md)
- Scope: Teams building REST APIs (backend, fullstack).
- Principles: Stateless, resource-centered, content-negotiation.
- Standards: URI design, HTTP methods, status codes, versioning.
- Process: How to design a new REST endpoint, deprecate old ones.

### Stage Instruction (05-project.instructions.md)
- Scope: Projects in initial Project phase (project-registered, team-established).
- Principles: Establish charter, define scope, activate downstream stages.
- Standards: Project structure, ownership, initial planning.
- Process: Go/no-go checklist, kickoff, downstream stage delegation (via digital-iot-team inheritance).

## Inheritance & Overrides

### Layer Inheritance
Parent-layer instructions apply to all child layers **unless explicitly overridden**.

```yaml
---
name: "Python Standards"
layer: digital-generic-team
override-reason: "More restrictive type checking for critical paths"
---
```

### When to Override
- **New organization requirement:** Child layer adds stricter rules.
- **Different toolchain:** Child layer uses different linter/formatter.
- **Domain-specific:** Example: Data science team uses different Jupyter conventions.

## Best Practices

### Writing Clear Instructions
- **Be specific:** "Use `raise ValueError(...)`" not "handle errors well".
- **Provide examples:** Show both good and bad code.
- **Link to tools:** Include setup commands, configuration snippets.
- **Version external references:** "PEP 8 (as of 2023)" not just "PEP 8".

### Maintaining Instructions
- Review annually (or when new major tooling versions release).
- Mark as updated: `last-reviewed: YYYY-MM-DD` in frontmatter (optional).
- When deprecated: Add deprecation notice at top, link to replacement.

### Collaboration
- Instructions are team decisions, not individuals' opinions.
- Propose changes as PRs with justification.
- Merge only after consensus (especially for foundational standards).

## References
- [Governance: Layer Override](./governance-layer/layer-override.instructions.md) — Inheritance rules.
- [Quality Standards](./quality-expert/documentation.instructions.md) — Instruction documentation quality.
- [Testing Standards](./test-expert/testing.instructions.md) — How to test instruction compliance.
- [Agile Standards](./agile-coach/agile-standards.instructions.md) — Sprint and workflow ceremonies.

## Quality Workflows

- `/quality` validates instruction naming, metadata, and cross-reference consistency.
- `/quality-fix` normalizes deterministic instruction defects when safe.
