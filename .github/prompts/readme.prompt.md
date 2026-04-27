<!-- layer: digital-generic-team -->
---
name: readme
description: Generate or update the enterprise README.md for the current repository following the digital-* template standard.
---

# /readme — Enterprise README Generator

Generates or updates the `README.md` for the current repository following the digital-* Enterprise README Template Standard.

## Information flow

| Field   | Value |
|---------|-------|
| Producer | This prompt (agent-invoked) |
| Consumer | `README.md` in the target repository |
| Trigger  | User invokes `/readme` in chat |
| Payload  | Full or updated README.md content adhering to the template standard |

## Pre-flight: Context Collection

Before generating, collect the following from disk (never guess or hardcode):

1. **Origin URL** — read `.git/config`, extract `[remote "origin"].url`
2. **Parent layer chain** — read `.digital-team/layers.yaml`, extract `layers[].name` and `layers[].source`
3. **Capability detection** — scan the repo root for:
   - `LICENSE` → emit license badge
   - `ruff.toml` or `[tool.ruff]` in `pyproject.toml` → emit ruff badge
   - `mypy.ini` or `[mypy]` section → emit mypy badge
   - `.coveragerc` or `[coverage:run]` in `setup.cfg` → emit coverage badge
   - `.github/workflows/*.yml` → emit CI badge (only if file exists)
   - `pyproject.toml` or `setup.cfg` with `python_requires` → emit Python version badge
4. **QuickStart block** — run `.github/skills/readme-standard/scripts/readme-quickstart.sh .` and embed its output verbatim.

## Output: README.md Structure

Generate the README in this exact section order:

```markdown
# <repo-name-as-title>

> <one-line description — derive from existing README or role in layer hierarchy>

<badges — only for detected capabilities, style=flat-square>

---

## Overview

## Prerequisites

## QuickStart

<output of readme-quickstart.sh verbatim>

## Repository Structure

## Development

## Testing

## License
```

### Stage Concept Coverage (Mandatory)

When stage flows are part of the repository, README generation must include a stable "Stage Concepts" explanation section that covers at least:

- `exploration` stage (purpose, gate criteria, and operational flow references)
- `project` stage (purpose, gate criteria, and operational flow references)

This section must reference the canonical policy/runtime files (instructions + prompt + runtime script) and must not copy dynamic planning outputs.

### Diagram Narrative Rule (Mandatory)

- Do not stack stage diagrams without context text.
- Add concise explanatory narrative between diagrams (what the view shows, why it matters, and how it relates to stage decisions).
- Maintain deterministic wording style so regenerated README output is stable across runs.

## Badge Rules (Strict)

- Only include a badge if the corresponding config file exists in the repo root (see pre-flight check).
- Use `flat-square` style for all badges.
- Do NOT generate fake CI badges for workflows that do not exist.
- Do NOT include coverage percentage values unless a coverage report file is present under `.tests/`.

### Allowed badge templates

```markdown
![Python](https://img.shields.io/badge/python-3.11+-blue?style=flat-square)
![Ruff](https://img.shields.io/badge/linter-ruff-blue?style=flat-square)
![Mypy](https://img.shields.io/badge/types-mypy-informational?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-green?style=flat-square)
![Tests](https://img.shields.io/badge/tests-pytest-orange?style=flat-square)
```

## QuickStart Section

Use the output of the `readme-quickstart.sh` script without modification.  
QuickStart snippets must target the current working directory (`"$PWD"`) after a pre-run workspace setup command.

## Stable Process Documentation Rule

- README content must document the general, stable way of working (process, commands, prerequisites, lifecycle).
- Do not copy dynamic planning outputs into README (for example: `.digital-artifacts/50-planning/**`, `project-assessment.md`, live checklist scores, transient open-question lists, generated feature proposals).
- If planning context is relevant, reference the process only (for example: "run `/project` to generate current planning artifacts") instead of embedding current planning content.
- Keep README deterministic across runs; volatile state belongs in `.digital-artifacts/` and board/wiki artifacts.

## Progress Markers

```
[progress][readme] step=1/5 action=collect-git-context
[progress][readme] step=2/5 action=detect-capabilities
[progress][readme] step=3/5 action=run-quickstart-script
[progress][readme] step=4/5 action=generate-readme
[progress][readme] step=5/5 action=write-readme-md
```

## Related Instructions

- `.github/instructions/quality-expert/readme-template.instructions.md` — full badge and section policy
- `.github/skills/readme-standard/SKILL.md` — QuickStart script documentation
