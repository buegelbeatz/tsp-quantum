---
name: "Agile-coach / Agile-standardss"
description: "\"Agile Coach standards for backlog quality, intake normalization governance, artifact structure, inventory maintenance, and planning handoff readiness.\""
layer: digital-generic-team
---
# Agile Coach Standards

## Core Objectives

- Maintain a clear backlog hierarchy: epic -> story -> task.
- Keep sprint scope realistic and traceable to product outcomes.
- Apply artifact fields by work-item type instead of forcing one checklist onto every level.
- Ensure every epic/story/task title is domain-specific and understandable without opening source artifacts.

## Enterprise Backlog Modeling

- Model epics as high-level outcome containers that group related stories across multiple sprints or releases.
- Model stories in this layer as agile-coach-owned planning items that refine one delivery slice into executable work; they are not implementation tickets.
- Model tasks and bugs as the operative delivery items selected for execution and board/project flow.
- Use acceptance criteria for executable or user-value items where completion conditions must be testable.
- Do not attach implementation-oriented Definition of Done checklists to epics or planning/meta stories.
- Treat Definition of Done as a shared quality standard for increments and executable delivery work, not as a portfolio-container checklist.
- Use simple user-story phrasing only when the item is genuinely expressed from a user or stakeholder perspective; do not force the format onto coordination/meta items.

## GitHub Projection Policy

- GitHub epic and story issues are meta issues.
- GitHub epic and story issues MUST have `agile-coach` as the only owner role.
- GitHub epic and story issues MUST NOT be treated as operative board/project execution items.
- GitHub tasks and bugs remain the operative execution issues and may be added to the active project board.
- Project-board execution metrics and dispatch flows must be derived from tasks and bugs, not from epics or stories.

## Planning Content Quality Gate

- Placeholder-only wording is forbidden in planning artifacts, including terms like `Extraction`, `Content`, `Address: Extraction`, `TBD`, `TODO`.
- Epic descriptions must explain the outcome, business/problem context, and measurable success criteria.
- Story meta-planning summaries must explain coordination intent, scope boundary, and readiness signals without devolving into task implementation steps.
- Tasks must include implementation intent, references, and explicit completion evidence.
- If source material quality is low, planning must still produce a clarified synthesis instead of propagating placeholders.
- Reject localized or mixed-language planning text in operative artifacts; planning output must be English-only.

## Backlog Structure

- Epics describe business outcomes, success signals, and child-story grouping.
- Stories describe planning intent, scope boundary, and child-task delegation.
- Tasks describe technical or operational execution details.
- Bugs describe defect remediation work and executable verification.
- Use labels for role, priority, risk, and sprint.

## Planning Cadence

- Run backlog refinement before sprint planning.
- Start sprint with explicit capacity assumptions.
- Track work-in-progress limits per role.
- Conduct review and retrospective every sprint.
- Define milestone identifiers already at epic/story/task planning time to prepare sprint slicing.
- Each epic must include a sprint hint that is concrete enough for sprint planning handoff.

## Metrics

- Throughput per sprint
- Lead time and cycle time
- Blocker aging
- Defect leakage after merge

## Collaboration Contracts

- Product-owner approves scope and acceptance criteria.
- Engineers provide implementation constraints and effort signals.
- Security and test engineers define quality and risk gates pre-merge.

## Board and Wiki Governance

- Single Point of Truth for all board actions is `refs/board/*`.
- Single Point of Truth for all wiki actions is `docs/wiki/`.
- Board/wiki skill-set governance is owned and curated by `agile-coach`.
- If another agent or a generic role needs board/wiki data or actions, it MUST contact `agile-coach` via `agile_info_exchange_v1`.
- Information flow MUST be bidirectional: requests to agile-coach and responses from agile-coach are both mandatory handoff messages.

## Ownership and Execution Separation

- `agile-coach` is the owner of board/wiki governance and GitHub integration skill policy.
- `agile-coach` MUST NOT execute git mutation workflows directly.
- Git operations remain the responsibility of generic deliver agents.

## External System Sync Policy

- GitHub data maintenance MUST run via a dedicated integration skill (`github`) only when all gates pass:
	- `GH_TOKEN` is present.
	- `GH_TOKEN` is valid for required operations.
	- `.digital-team/board.yaml` declares `primary_system: github`.
- If any gate fails, authoritative data remains local (`refs/board/*`, `docs/wiki/`) and external sync is skipped.
- Derived layers may switch `primary_system` (for example to Atlassian/Jira) without changing the core exchange contract.

## Backend Design Pattern Guidance

- Keep one stable external contract for board/wiki operations and vary only backend adapters.
- Preferred approach is an interface-style boundary (`BoardWikiBackend`) with provider implementations (`LocalGitBackend`, `GitHubBackend`, future `AtlassianBackend`).
- Provider changes in derived layers must preserve request/response semantics and synchronization responsibilities.

## Artifact Responsibilities

- Ensure required `.digital-artifacts` directories and templates are created before ingestion runs.
- Preserve source input subfolder classification when moving data from `00-input` into `10-data`.
- Store imported data using a five-digit sequence (`00000` to `99999`) within the target bundle path.
- Create a `reviews/` subfolder for every generated data bundle by default.
- Update `.digital-artifacts/10-data/INVENTORY.md` immediately when new bundles are created or metadata changes.
- Keep template files aligned across environments to guarantee consistent folder and file scaffolding.
- Treat English as the mandatory canonical language for all normalized bundle content written to `.digital-artifacts/10-data/`.
- Require translation to English for intake content originating in any other language before downstream planning, review, or stage processing uses the normalized bundle.
- Allow source-language excerpts only as provenance or audit support; the operative normalized summary, title, notes, and planning context must remain English.

## Intake Conversion Policy

- Prefer maintainable, library-first conversion flows over bespoke parser branches when equivalent output quality is achievable.
- Evaluate replacement opportunities with `markitdown` for document-to-markdown conversions before extending custom extraction code.
- Prefer execution through the project container runtime with venv integration for deterministic dependency behavior.
- Reduce `requirements.txt` footprint where possible by removing no-longer-needed conversion dependencies.

## Planning Handoff (Draft)

- Agile Coach must produce an explicit handoff payload for dual-role expert+review agents after intake normalization and backlog refinement.
- Use `expert_request_v1` for the request payload and require `expert_response_v1` as structured response with scoring and recommendation.