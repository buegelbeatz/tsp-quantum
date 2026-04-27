---
layer: digital-generic-team
---
# skills

## Purpose

**Skills** are executable capability packages that implement specific features or workflows. They provide:
- Reusable building blocks for agents and prompts.
- Clear contracts (dependencies, inputs, outputs, error handling).
- Testable implementations with minimal side effects.
- Documentation and examples for consistent usage.

## Structure

Each skill lives in `skills/{name}/` and follows this layout:

```
skills/prompt-quality/
├── SKILL.md                    # Canonical contract: metadata, dependencies, entry points
├── scripts/
│   ├── quality_script.py       # Main implementation
│   ├── quality_helpers.py      # Supporting utilities
│   └── tests/
│       └── test_quality.py     # Unit & integration tests (≥80% coverage)
├── templates/ (optional)       # Templated outputs (markdown, yaml, etc.)
└── requirements.txt            # Python dependencies (auto-merged by layer-venv-sync)
```

## Skill Categories

### Prompt Skills
**Purpose:** Power slash-command workflows invoked directly by users.

**Naming:** `prompt-{name}` (e.g., `prompt-quality`, `prompt-discovery`, `prompt-help`)  
**Mapping:** Maps to `{name}.prompt.md` in `/prompts/`  
**Registration:** Listed in `/prompts/help.prompt.md`

**Examples:**
- `prompt-quality` → `/quality` command → verifies layer contracts
- `prompt-quality-fix` → `/quality-fix` command → applies remediations
- `shared/runtime` → `/update` command runtime helper + environment/tool wrappers

### Generic Skills
**Purpose:** Framework/toolkit capabilities used across multiple projects.

**Naming:** `generic-{name}` (e.g., `generic-deliver`, `generic-input-2-data`)  
**Scope:** Cross-layer, reusable by any project type.

### Shared Skills
**Purpose:** Reusable shell utilities, library functions, shared logic.

**Canonical naming:** `shared/{name}` (for example `shared/runtime`, `shared/shell`)  
**Transitional aliases:** top-level `shared-*` directories remain temporarily valid until migration is complete.  
**Usage:** Sourced by other scripts; provides functions/utilities.

#### Canonical Shared Facades

To reduce naming ambiguity, new integrations should prefer these canonical facades:

- `shared/runtime` -> runtime/tool/bootstrap concerns
- `shared/orchestration` -> tests/audits/role orchestration concerns
- `shared/delivery` -> review/publication/PR delivery concerns

Backend shared wrappers remain valid during migration (for example `shared/shell`, `shared/task-orchestration`, `shared/local-command-orchestration`, `shared/pr-delivery`) and are tracked through `.github/skills/DEPRECATION_MAP.md`.

### Domain Expert Skills
**Purpose:** Specialized knowledge and capabilities by domain.

**Naming:** `{domain}-{function}` (e.g., `k8s-expert`, `quality-expert`)  
**Scope:** Deep expertise in a specific domain (Kubernetes, quality, testing, security, etc.).

## SKILL.md Contract

Every skill **must** have a `SKILL.md` that documents:

```yaml
---
name: {skill-name}
description: "One-line purpose statement"
layer: {layer-name}
---

# Skill: {Name}

## Purpose
Multi-line explanation of what this skill does and when to use it.

## Dependencies
- Other skills: `shared/shell`, `prompt-quality`
- External tools: `python3 ≥3.10`, `bash ≥4.0`
- Python packages: Listed in `requirements.txt`

## Entry Points
- CLI: How to invoke from command line or scripts.
- Function: If providing shell functions or Python modules.
- Handoff: What handoff types this skill accepts (if any).

## Failure Modes
- Error handling and recovery strategies.
- Edge cases and limitations.

## Examples
```bash
# Example shell invocation
bash scripts/quality-script.sh --repo-root /path --layer-name digital-team
```
"""

## References
- Related skills: `shared/orchestration`
- Documentation: `.github/instructions/quality-expert/`
```

## Quality Audits

### What `/quality` Checks for Skills
- `SKILL.md` metadata completeness (name, description, dependencies).
- Skill naming follows convention (`prompt-*`, `generic-*`, `shared-*`).
- Script structure: clear entry points, no global state.
- Python files: syntax, typing, docstring coverage.
- Shell files: `set -euo pipefail`, Purpose/Security headers.
- Test coverage: Minimum 80% for production code.

### What `/quality-fix` Does for Skills
**Autofix:**
- Adds/fixes Purpose and Security headers in shell scripts.
- Generates missing docstrings in Python files.
- Normalizes file permissions and shebang lines.
- Ensures `SKILL.md` has required metadata fields.

**Escalation (manual):**
- Module size > 100 lines (split into smaller functions).
- Missing test coverage (write tests).
- Complex logic refactoring (depends on intent).

## How to Create a New Skill

### 1. Plan
- **Name:** Choose `prompt-*`, `generic-*`, `shared-*`, or `{domain}-*`.
- **Purpose:** One sentence + expanded description.
- **Domain:** What agent(s) or workflow(s) depend on this?
- **Entry:** CLI command, function name, handoff schema?

### 2. Create Structure
```bash
make scaffold-skill SKILL_NAME=<name> SKILL_PURPOSE="use when ..."
```

### 3. Write SKILL.md
Document purpose, outputs, dependencies, information flow, entry points, and failure modes.

### 4. Implement
- Keep modules ≤100 lines net code.
- Use clear, focused functions (≤40 lines body).
- Add docstrings for all public functions.
- Handle errors gracefully (exit codes, log messages).

### 5. Test
- Write tests in `scripts/tests/`.
- Target ≥80% coverage.
- Test failure modes and edge cases.

### 6. Document
- Keep `SKILL.md` as the single canonical skill contract.
- Add extra documentation only when explicitly requested and place it under `docs/`.
- Include examples and usage.

### 7. Validate
```bash
make quality        # Run layer quality checks
make test           # Run tests (including this skill's tests)
```

## Dependencies & Merging

### Python Requirements
- Each skill declares dependencies in `requirements.txt`.
- `make layer-venv-sync` **auto-merges** all skill `requirements.txt` into the layer venv.
- **Do NOT** maintain a root-level `requirements.txt` — use skill-scoped files.

### Shell Dependencies
- Document required commands and versions in `SKILL.md` (e.g., `bash ≥4.0`, `grep`, `sed`).
- Use `command -v` checks in scripts to verify availability.

## Best Practices

### Code Style
- **Python:** PEP 8, type hints where possible, docstrings for all public functions.
- **Shell:** `set -euo pipefail`, clear variable naming, avoid global state.
- **Naming:** Functions/variables use `snake_case`, constants use `UPPER_CASE`.

### Error Handling
- Exit with non-zero code on failure.
- Log errors to stderr with context (file, line, action).
- Provide recovery hints where possible.

### Documentation
- Include PURPOSE and SECURITY headers in shell scripts.
- Docstrings: function purpose, arguments, return value, raises.
- Examples: at least one documented invocation.

### Testing
- Mock external dependencies (subprocess, file I/O).
- Test success and failure paths.
- Use fixtures for common setup.
- Target ≥80% coverage; document exceptions.

## Examples

### Prompt Skill (prompt-quality)
- Implements `/quality` workflow.
- Entry: `layer-quality.py` (parses CLI, delegates to `lq_runtime_collect.py`).
- Dependencies: Other quality scripts, Python packages.
- Tests: Validation cases, report rendering, findings classification.

### Shared Skill (shared/shell)
- Provides reusable shell utilities.
- Entry: `run-tool.sh` (sourced by other scripts).
- Functions: Container detection, environment setup, tool registry.
- No prompt mapping (not user-facing directly).

### Domain Skill (k8s-expert)
- Kubernetes/K3S cluster analysis and diagnostics.
- Entry: Shell functions for cluster connection, resource inspection.
- Dependencies: `kubectl`, optional SSH tunnel setup.
- Used by: `kubernetes-expert` agent for expert consultation.

## References
- [SKILL.md Template](../prompts/help.prompt.md) — See skill metadata format.
- [Testing Standards](../instructions/test-expert/testing.instructions.md) — Coverage, best practices.
- [Python Instructions](../instructions/language-expert/python.instructions.md) — Language-specific standards.
- [Quality Workflow](./quality-expert/) — Main quality orchestration.
