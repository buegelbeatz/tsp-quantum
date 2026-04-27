---
name: "Language-expert / Bashs"
description: "Bash/Shell Script Instructions"
layer: digital-generic-team
---
# Bash/Shell Script Instructions


## Environment Variables

- **CRITICAL**: Never hardcode values that are defined in `.env`
- Always use environment variable references: `$VAR_NAME` or `${VAR_NAME}`
- Provide validation for required environment variables:
  ```bash
  if [[ -z "$REQUIRED_VAR" ]]; then
    echo "Error: REQUIRED_VAR must be set"
    return 1
  fi
  ```
- Document environment variable usage in function headers

## Error Handling

- Use `set -euo pipefail` for strict error handling in scripts
- Always check exit codes for critical operations
- Provide meaningful error messages to users

## Quoting and Safety

- Quote all variable expansions: `"$VAR"` not `$VAR`
- Use `[[ ]]` for conditionals instead of `[ ]`
- Initialize numeric variables with defaults: `local count=0`
- Use `2>/dev/null || echo 0` pattern for commands that may fail

## Code Style

- Use 2-space indentation
- Add explanatory comments for complex logic
- Keep functions focused and single-purpose
- Color-code output using predefined color variables

## Linting (Single Point of Truth for Bash)

This section is the authoritative linting reference for Bash in this repository.

Mandatory gates:
- `shellcheck $(git ls-files '*.sh')`
- `bash -n $(git ls-files '*.sh')`

Rules:
- Run linting before tests.
- New lint/syntax errors are not allowed.
- Store lint outputs and temporary artifacts under `.tests/bash/`.

## Inline Documentation

- Provide a brief header comment for each script describing purpose and usage.
- Document functions with a short doc block including:
  - Purpose (one sentence)
  - Required environment variables (if any)
  - Parameters and return behavior
- Prefer examples only when behavior is non-obvious.

## Testing and Coverage

**Test specification (naming, location, output) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

Key points:
- **Naming:** Test files must start with `test_` prefix (e.g., `test_deploy.bats`).
- **Location:** Store tests as close as possible to the code they test (colocated).
- **Output:** All test artifacts (cache, reports, temp files) must go to `.tests/bash/`.

---

Specifics for Bash:
- Use **Bats** for unit/integration tests of shell scripts.
- Prefer **ShellSpec** only when BDD-style tests are explicitly required.
- For coverage, use **kcov** when available; otherwise fall back to **bashcov**.
- Document test execution in README or CI config when adding new tests.
