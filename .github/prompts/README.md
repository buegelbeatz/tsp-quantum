<!-- layer: digital-generic-team -->
# prompts

## Purpose

**Prompts** are user-invocable slash-command workflows that expose layer capabilities through a simple, consistent interface. They map human intent (e.g., `/quality`) to automated implementations (skills, agents, orchestration).

## What Is a Prompt?

A prompt is:
- **User-facing:** Invoked by slash commands (e.g., `/quality`, `/quality-fix`, `/update`).
- **Intent-based:** Describes what the user wants, not how to do it.
- **Backed by skills:** Delegates to skills, agents, and orchestration logic.
- **Documented:** Clear help text, examples, expected output.

## Prompt Categories

### Quality & Validation

**`/quality`** — Audits layer contracts and code quality.
- Scope: Validates all layer assets (agents, instructions, skills, prompts).
- Validates: Metadata, naming conventions, markdown formatting, references.
- Output: Structured report with findings, severity, and remediation hints.
- Powered by: `prompt-quality` skill.

**`/quality-fix`** — Applies automated fixes; reports escalations.
- Scope: Remediates structural and deterministic quality issues.
- Fixes: Docstrings, headers, file naming, metadata fields.
- Escalates: Oversized modules, refactoring needs, domain conflicts.
- Output: Applied fixes log + escalation report.
- Powered by: `prompt-quality-fix` skill.

### Maintenance & Updates

**`/update`** — Refreshes inherited layer content from parent layers.
- Scope: Syncs instructions, agents, skills from parent layer.
- Behavior: Overwrites local copies with parent versions (unless overridden).
- Output: Summary of updates applied.
- Powered by: `shared/runtime` skill + `shared/shell` utilities.

**`/help`** — Lists all available layer prompts and their usage.
- Scope: Dynamic help from integrated help registry.
- Output: Formatted list of prompts, one-liners, example invocations.
- Powered by: `prompt-help` skill.

### Specialized Workflows

**`/discover`** — Analyzes codebase and recommends improvements.
- Scope: Code exploration, dependency analysis, pattern detection.
- Output: Findings report with recommended actions.
- Powered by: `prompt-discovery` skill.

**`/input-2-data`** — Transforms unstructured user input into structured data models.
- Scope: Parsing, validation, schema mapping.
- Output: JSON/YAML data files in standard formats.
- Powered by: `prompt-input-2-data` skill.

## Prompt Metadata (PROMPT.md)

Every prompt **must** have a `{name}.prompt.md` file documenting:

```yaml
---
name: "Prompt Name"
command: "/command-name"
description: "One-line summary displayed in help."
layer: {layer-name}
---

# Prompt: {Name}

## Purpose
Multi-paragraph explanation of what this prompt does and when to use it.

## Usage
```
/{command-name} [OPTIONS]
```

**Options:**
- `--flag` — Description (optional|required).
- `--repo-root PATH` — Path to repository root (default: current dir).

## Examples

### Example 1: Basic Usage
```
/{command-name}
```
Expected output: ... description ...

### Example 2: With Options
```
/{command-name} --flag value
```
Expected output: ... description ...

## Output Format
Describe what the user sees:
- Success: Exit code 0, structured report (Markdown, JSON, etc.).
- Failure: Exit code 1, error message with next steps.

## Execution contract
- Delegates to: `.github/skills/quality-expert/SKILL.md`
- Invokes agent: `agent: generic-deliver`

## See Also
- Related prompt: `/quality-fix`
- Related skill: `skills/quality-expert`
- Related instruction: `quality-expert/documentation.instructions.md`
```

## Prompt Contract Sections

### Purpose
Why does this prompt exist? What user problem does it solve?

### Usage
Command syntax, available options, expected inputs.

### Examples
2–3 real-world use cases with invocation and output.

### Output Format
What the user sees (structure, format, success/failure indicators).

### Dependencies
- Skills this prompt invokes.
- Agents it delegates to.
- External tools (git, docker, python3, etc.).

### Error Handling
What happens when the prompt fails.
What the user should do next.

### See Also
Links to related prompts, skills, instructions, documentation.

## How to Create a New Prompt

### 1. Plan the User Experience
- **Command name:** `/quality`, `/fix`, `/discover` (verb-noun pattern).
- **Purpose:** What user intent does it serve? (e.g., "validate code quality").
- **Input:** What options/arguments does the user provide?
- **Output:** What should the user see? (report, changes, log messages).

### 2. Design the Skill Mapping
- **Which canonical skill implements this?** Reference existing skills (e.g., `skills/quality-expert/SKILL.md`).
- **No prompt-wrapper skills:** Do NOT create `skills/prompt-{name}/SKILL.md` wrappers — reference canonical skills directly from the prompt's `## Execution contract`.
- **Skill entry point:** Which function/script does the prompt invoke?
- **Delegation:** Will the prompt invoke an agent? (e.g., `/quality-fix` → quality-expert agent).

### 3. Write the Metadata File
Start with:

```bash
make scaffold-prompt PROMPT_NAME=<name> PROMPT_PURPOSE="one-line purpose"
```

Then refine `prompts/{name}.prompt.md` with contract sections.

### 4. Implement or Delegate to Skill
- Wire up the `## Execution contract` to reference the canonical skill path.
- Expose the prompt through the canonical target `make <name>`.

### 5. Document with Examples
- Write 2–3 realistic use cases showing command, output, and user interpretation.
- Show both success and failure scenarios if applicable.

### 6. Register in Help
Add an entry to `prompts/help.prompt.md`:
```md
- `/command-name` — One-line summary.
```

### 7. Validate
```bash
make quality        # Checks prompt metadata, skill references
make test           # Tests prompt invocation and skill delegation
```

## Prompt Naming Conventions

- **Verb-noun pattern:** `/quality`, `/update`, `/discover` (not `/quality-audit` or `/validate-quality`).
- **Single-word preferred:** `/quality` better than `/code-quality`.
- **Lowercase:** `/quality`, not `/Quality`.
- **No dashes unless unavoidable:** `/input-2-data` (exception for compound concepts).

## Quality Audits

### What `/quality` Checks for Prompts
- Frontmatter metadata completeness (name, command, description, layer).
- File naming consistency (`{name}.prompt.md`, not `prompt.md`).
- Command name appears in file path (e.g., `/quality` → `quality.prompt.md`).
- Contract sections present and prompt-bound skill exists.
- Shell examples invoke the prompt through `make <name>`, not `make prompt-<name>`.
- No hardcoded secrets, credentials, or paths.
- Skill references are valid (skill must exist in `skills/prompt-{name}/`).

### What `/quality-fix` Does for Prompts
**Autofix:**
- Adds missing frontmatter fields.
- Normalizes file naming.
- Ensures required sections exist.
- Syncs `help.prompt.md` with registered prompts.

**Escalation (manual):**
- Missing examples or unclear documentation.
- Unimplemented skill or broken skill binding.
- Conflicting command names across layers.

## Examples

### Simple Prompt: /quality

**File:** `prompts/quality.prompt.md`

```yaml
---
name: "Quality Audit"
command: "/quality"
description: "Audit layer contracts and code quality."
layer: digital-generic-team
---

# Prompt: /quality

## Purpose
Validates all layer assets (agents, instructions, skills, prompts) against quality standards.
Reports findings by severity level.

## Usage
```
/quality [--format=json|markdown]
```

## Examples

### Example 1: Quick Audit
```
/quality
```
Output: Markdown report with findings grouped by severity.

### Example 2: JSON Output for Tooling
```
/quality --format=json
```
Output: Structured JSON for integration with IDEs or CI/CD.

## Output Format
- **Success:** Exit 0, report with findings (0 or more).
- **Failure:** Exit 1, error message (e.g., "No layer detected").

## Dependencies
- Skill: `prompt-quality`
- Invokes: `lq_runtime_collect.py`, `lq_validate_*.py` modules.

## Error Handling
Common failures:
- "Working directory is not a layer root" → Must be in `.github/` or at layer root.
- "No agents found" → Layer may be new or misconfigured.

## See Also
- `/quality-fix` — Apply automated fixes.
- `prompt-quality-fix` skill documentation.
```

### Complex Prompt: /quality-fix

**File:** `prompts/quality-fix.prompt.md`

```yaml
---
name: "Quality Fix"
command: "/quality-fix"
description: "Apply automated quality fixes; report escalations."
layer: digital-generic-team
---

# Prompt: /quality-fix

## Purpose
Automatically remediates deterministic quality issues.
Reports escalation findings (manual refactoring required).

## Usage
```
/quality-fix [--dry-run] [--auto-commit]
```

**Options:**
- `--dry-run` — Show what would be fixed without modifying files.
- `--auto-commit` — Automatically commit fixes with conventional message.

## Examples

### Example 1: Preview Fixes
```
/quality-fix --dry-run
```
Output: Files to modify, changes proposed.

### Example 2: Apply & Commit
```
/quality-fix --auto-commit
```
Output: Applied fixes log, Git commit hash, escalation report.

## Dependencies
- Skill: `prompt-quality-fix`
- Invokes: `lq_fix.py` (autofix engine).
- Delegates: Escalations to `quality-expert` agent for recommendations.

## Escalation Examples
- Module > 100 lines → Manual split into smaller units.
- Missing tests → Write new tests (automated suggestions TBD).
- Code duplication → Refactoring (manual analysis needed).

## See Also
- `/quality` — Audit without fixes.
- [Quality Expert Agent](../agents/quality-expert.agent.md) — Escalation consultations.
```

## Prompt Registry (help.prompt.md)

Central registry of all available prompts:

```yaml
---
name: "Help"
description: "List available layer prompts and their usage."
layer: digital-generic-team
---

# Prompt: Help

## Purpose
Dynamic, current list of all available prompts with usage summary.

## Available Prompts

| Command | Description | Skill |
|---------|-------------|-------|
| `/quality` | Audit layer contracts and code quality | `prompt-quality` |
| `/quality-fix` | Apply automated fixes; report escalations | `prompt-quality-fix` |
| `/update` | Refresh inherited content from parent layer | `shared/runtime` |
| `/help` | Show this list | (built-in) |
| `/discover` | Analyze codebase and recommend improvements | `prompt-discovery` |
| `/input-2-data` | Transform input into structured data | `prompt-input-2-data` |

### Quick Help
```
/{command} --help
```

All prompts support `--help` flag for detailed usage.
```

## Best Practices

### Command Design
- **Short:** Most prompts are single word (e.g., `/quality`, `/help`).
- **Verb-based:** Describe the action (e.g., `/quality`, `/update`, `/discover`).
- **Discoverable:** Available in `/help` registry.

### Input Validation
- Validate all user-provided options.
- Suggest alternatives if command is mistyped or unknown.
- Provide clear error messages with recovery hints.

### Output Consistency
- Success always exits 0.
- Failure always exits 1.
- Key output clearly marked (headers, colors, bold text).
- Provide actionable next steps in error messages.

### Documentation
- One-liner in prompt metadata (to appear in `/help`).
- Full purpose section (what, why, when to use).
- At least 2 examples (common case, advanced case).
- Reference related prompts, skills, agents.

## References
- [Skill Contracts](../skills/README.md) — How prompts map to skills.
- [Agent Contracts](../agents/README.md) — How prompts delegate to agents.
- [Help Prompt](./help.prompt.md) — Prompt registry and reference.
- [Quality Instruction](../instructions/quality-expert/documentation.instructions.md) — Quality standards for prompts.

## Quality Workflows

- `/quality` validates prompt naming, command policy, and prompt-to-skill binding integrity.
- `/quality-fix` applies deterministic prompt normalization fixes.
