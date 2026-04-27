---
name: quality-expert
description: Central quality gate runner and report source shared by layer-quality, engineering sessions, and reviewer workflows.
layer: digital-generic-team
---

# Skill: Quality Expert

This skill provides one shared quality gate execution and report contract.

## Capabilities

- Run the canonical quality session for tests, coverage, linting, typing, and security checks.
- Publish a normalized report to `.tests/python/reports/quality-expert-session.md`.
- Keep compatibility with legacy fullstack quality reporting.

## Script

- `scripts/quality-expert-session.sh`
- `scripts/quality-expert-orchestrator.sh`

## Shared Consumption

- `/quality` and `/quality-fix` are routed through `quality-expert-orchestrator.sh` as the single quality orchestration entrypoint.
- `/quality` produces the read-only overview and tabular worklist of current quality findings.
- `/quality-fix` consumes that worklist and works through the reported points; if a finding requires an extensive refactor, it may escalate through expert consultation before proceeding.
- `/layer-quality` reads and reports runtime quality status from the canonical report.
- `/layer-quality` emits `expert_request_v1` blocks to `quality-expert` with focus on:
  - Clean code (parameter count, strict mode, naming conventions)
  - Design patterns (multi-class modules, explicit patterns)
  - Enterprise documentation (module docstrings, public function docstrings, script headers)
  - Documentation structure (skill-level README.md presence)
  - Module-size limits (`<= 100` lines per module)
  - All delivery agents (via `generic-deliver` skill) consume the same source via `make quality`, `make quality-fix`, or `make quality-expert` / `make fullstack-quality`.
- Reviewer workflows consume the same report as the quality source of truth.
  - Expert consultation handoffs must use `expert_request_v1` / `expert_response_v1`.
  - Delivery-to-review handoffs must use `work_handoff_v1`.
