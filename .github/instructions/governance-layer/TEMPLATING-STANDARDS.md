---
layer: digital-generic-team
---
# Unified Templating Standards for Assets

Governs consistent structure, quality, and validation across agents, skills, instructions, prompts, and Make targets.

---

## Template Requirements Matrix

| Asset Type | Required Frontmatter | Required Sections | Tests Required | Linting Rules |
|:---|:---|:---|:---:|:---|
| **Instruction** | `name`, `description`, `layer` | Execution, Standards, References | Unit tests per domain | Markdown + Frontmatter validation |
| **Agent** | `name`, `purpose`, `layer`, `role` | Overview, Inputs, Outputs, Handoff contract | Integration tests (if delivery agent) | Frontmatter + Audience match |
| **Skill** | `name`, `purpose`, `layer`, `owner` | Overview, Information Flow, Inputs/Outputs, Testing plan | ≥80% coverage on scripts | Python/Shell linting |
| **Prompt** | `name`, `command`, `layer`, `skill` | Execution contract, Parameters, Output format | Dry-run validation | Markdown + Parameter binding |
| **Make Target** | Comment with `##` | Purpose, Usage, Returns | Shell syntax check | Adherence to naming convention |

---

## Frontmatter Standard

### Instruction (`.instructions.md`)

```yaml
---
name: "Role / Domain / Stage Name"
description: "One-sentence purpose (appears in indexes and catalogs)"
layer: "digital-generic-team"
override-reason: "Only if overriding parent-layer asset; explain why"
---
```

### Agent (`.agent.md`)

```yaml
---
name: "agent-name"
purpose: "One-line purpose"
role: "[agile-coach|generic-plan|generic-deliver|quality-expert|...]"
layer: "digital-generic-team"
override-reason: "Optional; explain if overriding parent asset"
---
```

### Skill (`.skill.md`)

```yaml
---
name: "skill-name"
purpose: "One-line purpose"
layer: "digital-generic-team"
owner: "[role or team]"
---
```

### Prompt (`.prompt.md`)

```yaml
---
name: "prompt-name"
command: "/command-alias"
skill: "skill-name-if-delegating"
layer: "digital-generic-team"
---
```

### Makefile target (in `commands.mk`)

```makefile
target-name: ## One-line purpose (appears in `make help`)
	@echo "Implementation"
```

---

## Content Structure

### Instructions

```markdown
# [Name]

## Purpose / Overview
[What this instruction covers and why]

## Standards
- **Standard 1**: [Rule] — [Rationale]
- **Standard 2**: [Rule] — [Rationale]

## Process / Workflow
1. Step 1
2. Step 2

## References
- [Link to related docs]
- [Link to external standards]

## FAQ / Troubleshooting
- **Q**: ...
- **A**: ...
```

### Agents

```markdown
# [Agent Name]

## Overview
[What this agent does]

## Inputs (Contracts)
- `input_a`: Type, format, constraints
- `input_b`: Type, format, constraints

## Outputs (Contracts)
- `output_x`: Type, format, location
- `output_y`: Type, format, location

## Handoff Integration
[Describe agent-agent handoff protocol]

## Information Flow
**Producer**: [X]  
**Consumer**: [Y]  
**Trigger**: [When triggered]  
**Payload**: [What is exchanged]
```

### Skills

```markdown
# [Skill Name]

## Overview
[What this skill does; its place in the infrastructure]

## Information Flow
**Producer**: [Who generates the output]  
**Consumer**: [Who consumes the output]  
**Trigger**: [When is it called]  
**Payload**: [What is passed/returned]

## Scripts
- `script1.py` — Description
- `script2.sh` — Description

## Scripts + Tests
- `scripts/tests/test_*.py` — Test coverage ≥80%

## Dependencies
- `requirements.txt` — Python packages (optional)
- External tools: [tool list]

## Usage Examples
```bash
# Example 1
bash .github/skills/skill-name/scripts/script.sh arg1 arg2
```
```

### Skill Documentation Policy

- `SKILL.md` is the mandatory and canonical contract file for each skill.
- Skill scaffolding must not auto-generate `.github/skills/<skill>/README.md`.
- If additional documentation is necessary, store it explicitly in `docs/` (or another scoped docs path) instead of generated per-skill README boilerplate.

### Prompts

```markdown
# [/command Prompt Name]

## Overview
[What this prompt does when triggered]

## Execution Contract

**Preconditions**:
- [Input X exists]
- [Configuration Y is set]

**Command**:
```bash
make PROP="value"
```

**Parameters**:
- `--flag`: Description

**Outputs**:
- File at location X
- Config written to Y

**Side Effects**:
- [If any; e.g., creates GitHub PR]

## Information Flow
**Producer**: [Who triggers; e.g., user via /command]  
**Consumer**: [Who consumes output; e.g., delivery agents]  
**Trigger**: [When; e.g., user types /command or scheduled]  
**Payload**: [Exchange format; e.g., JSON, YAML]
```

---

## Validation Rules

### Linting

**All `.md` files**:
- ✅ Valid Markdown (no unclosed blocks)
- ✅ Frontmatter is valid YAML
- ✅ No broken internal links
- ✅ Consistent heading hierarchy (#, ##, ###)
- ✅ Code blocks labeled with language (e.g., ` ```bash `)

**`.instructions.md` only**:
- ✅ Frontmatter includes `name`, `description`, `layer`
- ✅ Must include either "Purpose", "Overview", or "Standards" section
- ✅ If `layer != "digital-generic-team"` and asset exists in parent, must include `override-reason`

**`.agent.md` only**:
- ✅ Frontmatter includes `name`, `purpose`, `role`, `layer`
- ✅ Must include "Inputs" and "Outputs" sections (contracts)
- ✅ Delivery agents must include "Handoff Integration"

**`.skill.md` only**:
- ✅ Frontmatter includes `name`, `purpose`, `layer`
- ✅ Must include "Overview" and "Information Flow" sections
- ✅ If skill exports scripts, must include "Scripts + Tests" section

**`.prompt.md` only**:
- ✅ Frontmatter includes `name`, `command`, `layer`
- ✅ Must include "Execution Contract" section
- ✅ If integrating with agents, must include "Information Flow"

**Scripts (`*.py`, `*.sh`)**:
- ✅ All Python: `ruff check` + `mypy` passing
- ✅ All Bash: `shellcheck` passing
- ✅ Layer marker in shebang comment (2nd line for shell, end of imports for Python)

### Testing

**Python skills**:
- ✅ `pytest` coverage ≥80%
- ✅ Tests in `scripts/tests/` with `test_*.py` naming
- ✅ Report: `.tests/coverage/skill-name.xml` (coverage format)

**Bash skills**:
- ✅ Integration tests in `scripts/tests/` with `test-*.sh` naming
- ✅ Syntax check: `bash -n` passing
- ✅ Shellcheck: no errors

**Instructions, Agents, Prompts**:
- ✅ Manual review: Frontmatter valid, links valid, no typos
- ✅ Auto-check: `make quality` linting pass

### Coverage Targets

| Category | Target |
|:---|:---:|
| Python scripts in skills | ≥80% |
| Agent integration tests | ≥1 test per handoff path |
| Instruction examples | ≥1 example per standard |
| Prompt dry-run | ≥1 dry-run config tested |

---

## Scaffolding

Use the built-in scaffold commands to generate templates:

```bash
# Instruction
make scaffold-instruction \
  INSTRUCTION_CATEGORY=stages \
  INSTRUCTION_NAME=10-ideation \
  INSTRUCTION_PURPOSE="Problem ideation and idea validation"

# Agent
make scaffold-agent \
  AGENT_NAME=iot-engineer \
  AGENT_PURPOSE="Research and implement IoT device integrations"

# Skill
make scaffold-skill \
  SKILL_NAME=mqtt \
  SKILL_PURPOSE="MQTT broker automation and device communication"

# Prompt
make scaffold-prompt \
  PROMPT_NAME=ideation \
  PROMPT_PURPOSE="Run the Ideation stage workflow"

# Handoff
make scaffold-handoff \
  HANDOFF_NAME=planning-to-delivery \
  HANDOFF_SCHEMA=work_handoff_v1
```

All scaffolds include:
- ✅ Correct frontmatter (layer auto-filled as current repo)
- ✅ Required sections with placeholders
- ✅ Inline comments guiding customization
- ✅ Layer-aware override detection

---

## Quality Workflow

```bash
# 1. Scaffold new asset
make scaffold-{instruction|agent|skill|prompt}

# 2. Customize content

# 3. Run linting
make quality            # Full quality report (tests, linting, coverage)

# 4. Fix issues
make quality-fix        # Auto-remediate linting issues

# 5. Commit
git add .github/...
git commit -m "feat: add [asset-type]: [name]"
```

---

## Examples

| Asset | Path | Template |
|:---|:---|:---|
| Instruction | `.github/instructions/stages/10-ideation.instructions.md` | See `scaffold-instruction` output |
| Agent | `.github/agents/iot-engineer.agent.md` | See `scaffold-agent` output |
| Skill | `.github/skills/mqtt/SKILL.md` | See `scaffold-skill` output |
| Prompt | `.github/prompts/ideation.prompt.md` | See `scaffold-prompt` output |
| Make target | `.github/make/commands.mk` | Standard line per target |

---

## Enforcement

**Pre-commit hooks** (optional, via `.githooks/`):
- ✅ Validate frontmatter in new/modified `.md` files
- ✅ Enforce `## Purpose` / `## Overview` presence
- ✅ Check layer marker in `.sh` and `.py` files

**CI/CD** (`make quality`):
- ✅ All linting and coverage checks run automatically
- ✅ Reports in `.tests/` for visibility

**Manual review** (pull requests):
- ✅ Ensure "Information Flow" contract is clear
- ✅ Validate contract consistency (inputs/outputs match caller expectations)
- ✅ Spot-check examples for correctness

---

## Migration Path

**Existing assets** (inherited, no frontmatter or incomplete):
1. Run `make update` → Re-sync from parent layers
2. Check for assets with missing `layer:` frontmatter
3. Add `layer: [repo-name]` during `/update` execution (auto-injected)
4. If custom, add `override-reason: <why>` explanations

**New assets** (your layer):
1. Always use `make scaffold-*` to create
2. Frontmatter auto-populated with current layer
3. Follow content structure above
4. Pass `make quality` before committing
