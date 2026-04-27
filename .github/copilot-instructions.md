---
name: "Copilot-instructions"
description: "Generic Copilot Instructions"
layer: digital-generic-team
---
# Generic Copilot Instructions

Use English for naming, code comments, documentation, and markdown files.

## Scope

This file defines global behavior for all agents, instructions, prompts, and skills.
Role-specific quality gates, engineering standards, and testing details are defined in role instructions and skills.

## Working Model

- Prefer autonomous execution with sensible defaults.
- Ask follow-up questions only when blocked by missing critical input or security constraints.
- Keep outputs deterministic, traceable, and reproducible.
- Reference capabilities by stable IDs from agent, instruction, and skill catalogs.
- Do not ask optional confirmation questions such as "Should I continue?" or "Do you want me to do X?" when a safe default exists.
- Continue end-to-end by default and only stop for explicit human approval gates, destructive actions, or missing mandatory data.

## Required Runtime Behavior

- Prefer registry-backed container-first execution for external CLI tooling. Use local execution only for explicit bootstrap flows or when the shared wrapper intentionally falls back.
- Use container fallback if required tooling is missing.
- All external CLI tools invoked by repository code MUST go through the shared/shell tool registry (`.github/skills/shared/shell/scripts/run-tool.sh`) or an equivalent registry-backed wrapper. Do not call non-standard host tools directly via `subprocess` when a registry-backed path is possible.
- For containerized tool execution, prefer multi-architecture images. When architecture-specific images or emulation are required, the tool registry and wrapper must honor an explicit platform selector such as `CONTAINER_PLATFORM`.
- Never hardcode secrets, tokens, local file paths or sensitive information; load from environment variables.
- Keep `.env` local and provide all keys in `.env.example`.
- Assume environment configuration is loaded from `.env` and referenced via environment variables.
- Always add a leading comment to every entry in `.env.example` to explain the expected value and usage.

## Directory Structure and Storage Governance

**CRITICAL:** This rule applies to ALL layers (Layer 0, Layer 1, and derived layers).

### Runtime and Caching Storage

- **NEVER** store runtime data, cache, temporary files, or working directories under `.digital-team/`.
- **NEVER** create directories or write artifacts outside the repository root.
- **REQUIRED:** ad-hoc experiments and temporary workspaces must be created only under `.digital-runtime/`.
- **REQUIRED** location for all runtime data: `.digital-runtime/layers/<current-layer>/`
  - Example: `.digital-runtime/layers/generic/cache/`, `.digital-runtime/layers/generic/.venv`
  - Subdirectories under `.digital-runtime/layers/<layer>/` are free to organize as needed.
- **FORBIDDEN:** creating or using a repository-root `.venv` directory.
- **REQUIRED:** Python virtual environments must be located only under `.digital-runtime/layers/...`.

### Test and Coverage Storage

- **NEVER** store test outputs, coverage files, or test reports under `.digital-team/`.
- **REQUIRED** location for all test outputs: `.tests/` (at repository root)
  - Includes: `*.xml`, coverage data, pytest logs, lint reports, temporary test files.

### Layer Python Requirements

- Each skill declares its Python dependencies in a `requirements.txt` within its own skill directory.
- The layer venv sync (`make layer-venv-sync`) auto-discovers and merges all skill-level `requirements.txt` files.
- **Do NOT** maintain a manual root-level `requirements.txt`; use skill-scoped files instead.

## Mandatory Delivery Gates

- Every code change must include corresponding unit tests.
- Coverage must be measured and reported (target >= 80% unless explicitly waived).
- Documentation must be updated in the same change when behavior, interfaces, or operations are affected.
- Documentation MUST always be done on a standardized enterprise level.
- Security review and test review outputs must be included in review artifacts.
- Generate review artifacts only at the final review gate, not during preparation or mid-implementation.

## Branch Policy

- MUST NOT commit or push directly to `master` or `main`.
- All changes MUST be made on a dedicated feature or fix branch.
- Branch naming convention: `<type>/<short-description>` — for example `feat/add-login`, `fix/null-pointer`, `chore/update-deps`.
- Changes reach `master`/`main` only via a reviewed and approved pull request.
- Pull requests MUST include a human approval before merge.

## Prompt Execution Contract

- Every slash prompt that triggers multi-step work MUST provide visible progress updates.
- Progress output format MUST use stable markers: `[progress][<prompt-or-command>] step=<x/y> action=<name>`.
- Long-running script calls in prompts MUST print at least: start, current step, and completion.
- Prompt text should document expected progress behavior so chat users can trace execution state.

## Information Flow Contract

- New or updated tooling assets in `.github/prompts/`, `.github/skills/`, and `.github/agents/` MUST include explicit information flow documentation.
- Required section title for prompts: `## Information flow`.
- Required section title for skills and agents: `## Information Flow`.
- Each information flow section MUST document at least:
  - producer (who sends information),
  - consumer (who receives information),
  - trigger (when the exchange happens),
  - payload summary (what is exchanged).
- Tooling scaffolds and templates must preserve this contract by default so new generated assets include it automatically.

## Specification Locations

- Agent definitions: `.github/agents/`
- Shared and role instructions: `.github/instructions/`
- Task capabilities: `.github/skills/`
- Reusable prompt templates: `.github/prompts/`
- Handoff templates: `.github/handoffs/`
- Artifacts: `.digital-artifacts/`
- MCP connections are specified in `.vscode/mcp.json`

## Layer Override Policy

When working in a Layer N or App repo, **always check for name collisions with parent-layer assets before creating new agents, instructions, skills, or prompts.**

- If a collision exists and the override is **not intended**: choose a different name.
- If a collision exists and the override **is intended**: add `override-reason: <why>` to the file's frontmatter.
- When creating assets automatically via chat or agent workflows: stop and inform the user explicitly before proceeding with any override.

Full rules: `.github/instructions/governance-layer/layer-override.instructions.md`

## Delivery Expectations

- Produce actionable artifacts in predictable locations.
- Include concise rationale for non-obvious decisions.
- Keep role boundaries clear and coordinate across agents through defined interfaces.
- In progress and final reports, state completed actions and next mandatory step directly instead of asking for optional permission.

## Mandatory Coding Guidance Integration

- For every code generation or code modification task, agents MUST apply both:
  - `.github/instructions/quality-expert/cleancode.instructions.md`
  - `.github/instructions/quality-expert/designpatterns.instructions.md`
- This requirement applies during initial generation and subsequent adjustments/refactors.
- If either guidance source cannot be resolved, agents MUST stop and report a blocked state instead of continuing with partial guidance.

