---
name: readme-standard
description: Generates and validates enterprise README.md files including badge governance, QuickStart patterns derived from .git/config and .digital-team/layers.yaml, and mandatory section structure.
user-invocable: false
layer: digital-generic-team
---

# Skill: README Standard

Provides tooling and rules for generating and validating `README.md` files across all `digital-*` repositories.

## Capabilities

- Generate QuickStart clone commands from real `.git/config` `origin` URLs.
- Detect parent layer chain from `.digital-team/layers.yaml`.
- Emit both public and private (GH_TOKEN) clone variants.
- Validate badge coverage against actual repository capabilities (detected tool config files).
- Enforce mandatory section order and content rules.
- Enforce stable-process-only README content: include durable workflow guidance, exclude volatile planning runtime outputs.
- Enforce stage concept coverage for `exploration` and `project` when stage workflows are part of the repository.
- Enforce explanatory text between diagram blocks (no raw diagram dumping).

## Content Boundary (Mandatory)

- README is the stable entry document for humans and must remain durable across runs.
- Dynamic planning/runtime artifacts MUST NOT be embedded into README content.
	- Examples of excluded sources: `.digital-artifacts/50-planning/**`, `.digital-artifacts/**/project-assessment.md`, transient checklist scores, current open-question queues.
- Dynamic state belongs in `.digital-artifacts/`, board refs (`refs/board/*`), and wiki/project artifacts.
- README may reference process commands (for example `/project`, `make project`) but should not inline the generated planning payload.

## Stage Documentation Contract

- README generation must include a stable stage-concept explanation when stage assets exist.
- At minimum, the generated content must explain:
	- `exploration` stage
	- `project` stage
- For each stage, reference canonical implementation sources instead of duplicating runtime outputs.
- Diagram-heavy sections must include short interpretation text between images to keep the documentation readable for humans.

## Script

- `scripts/readme-quickstart.sh` — emits the correct QuickStart block for a given repo directory.

## Usage

```bash
# Print QuickStart block for current repo
bash .github/skills/readme-standard/scripts/readme-quickstart.sh .

# Print QuickStart block for a target app directory (install pattern)
bash .github/skills/readme-standard/scripts/readme-quickstart.sh /path/to/my-app
```

## Information Flow

| Field    | Value |
|----------|-------|
| Producer | Agent or developer invoking the skill |
| Consumer | README.md of the target repository |
| Trigger  | `/update`, `/quality`, or manual invocation |
| Payload  | QuickStart block (Markdown fenced code blocks with correct clone URLs) |

## Dependencies

- `.git/config` — source of `origin` URL
- `.digital-team/layers.yaml` — source of parent layer chain
- `.github/skills/shared/shell/` — tool registry for container fallback

## Related Instructions

- `.github/instructions/quality-expert/readme-template.instructions.md`
- `.github/instructions/quality-expert/documentation.instructions.md`
