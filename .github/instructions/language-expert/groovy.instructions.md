---
name: "Language-expert / Groovys"
description: "Groovy Instructions (Jenkins / General)"
layer: digital-generic-team
---
# Groovy Instructions (Jenkins / General)

These rules apply to all Groovy code in this repository, especially Jenkins Pipelines.

---

## 1. Target & Compatibility

- Prefer Groovy that is compatible with:
  - Jenkins Pipeline Groovy (CPS) where applicable
  - Shared Libraries (`vars/`, `src/`)
- Avoid advanced Groovy features that frequently break under CPS (e.g., heavy metaprogramming).
- Prefer explicit, readable code over clever one-liners.

---

## 2. Project Structure (Jenkins Recommended)

```
(Jenkins Shared Library)
vars/
  myStep.groovy
src/
  org/example/pipeline/Utils.groovy
resources/
  org/example/templates/template.yaml
```

- `vars/` contains pipeline steps (`call(...)` entrypoint).
- `src/` contains classes/helpers (namespaced packages).
- `resources/` contains non-code assets loaded via `libraryResource`.

---

## 3. Naming Conventions

- Classes: `PascalCase`
- Methods/variables: `camelCase`
- Constants: `UPPER_SNAKE_CASE`
- Files:
  - `vars/<stepName>.groovy` must match the exported step name
  - Class file names must match the class name

---

## 4. Code Style

- Use 2-space indentation in Jenkinsfiles and pipeline steps.
- Prefer small, focused methods.
- Avoid deeply nested closures.
- Prefer early returns over nested `if` blocks.
- Keep methods short (~50 lines max where possible).

---

## 4a. Linting (Single Point of Truth for Groovy)

This section is the authoritative linting reference for Groovy in this repository.

Mandatory gates (use the one configured in the project):
- `npm-groovy-lint` (Node-based projects), or
- `gradle codenarcMain codenarcTest` (CodeNarc-based projects)

Recommended static sanity check:
- `gradle classes testClasses` (or equivalent compile check)

Rules:
- Run linting before tests.
- New lint errors are not allowed.
- Store lint outputs and temporary artifacts under `.tests/groovy/`.

---

## 5. Jenkins Pipeline (CPS) Safety Rules

- Do not store non-serializable objects across pipeline steps.
- Avoid capturing large objects in closures.
- Prefer `@NonCPS` only for pure calculations (no Jenkins steps inside).
- Do not call Jenkins steps (e.g. `sh`, `echo`, `checkout`) inside `@NonCPS`.

### @NonCPS Example

```groovy
import groovy.transform.NonCPS

@NonCPS
static List<String> uniqueSorted(List<String> items) {
  return items.findAll { it != null }.unique().sort()
}
```

---

## 6. Error Handling

- Fail fast with clear messages.
- Prefer explicit errors over silent fallbacks.
- Use `error("message")` in pipelines to fail the build.

```groovy
if (!params.VERSION?.trim()) {
  error("VERSION parameter must be set")
}
```

- Wrap critical stages with `try/finally` to ensure cleanup.

```groovy
try {
  stage('Build') {
    sh 'make build'
  }
} finally {
  stage('Cleanup') {
    sh 'make clean || true'
  }
}
```

---

## 7. Logging & Output

- Use `echo` for pipeline logs.
- Include context in messages (stage, component, version).
- Do not print secrets.
- Mask credentials using Jenkins Credentials Binding.

Example:

```groovy
withCredentials([string(credentialsId: 'api-token', variable: 'API_TOKEN')]) {
  sh 'curl -H "Authorization: Bearer $API_TOKEN" https://example/api'
}
```

---

## 8. Strings, Shell, and Quoting

- Prefer single quotes for static strings: `'text'`
- Use GString (`"${var}"`) only when interpolation is required.
- When calling `sh`, prefer triple-single quotes for multi-line scripts:

```groovy
sh '''
  set -euo pipefail
  echo "Hello"
'''
```

- Always quote shell variables inside `sh`.

---

## 9. Dependencies & Reuse

- Prefer shared library functions over duplicated Jenkinsfile logic.
- Centralize repeated logic in `vars/` steps or `src/` helpers.
- Avoid introducing new dependencies/plugins without justification.

---

## 10. Security Rules

- Never hardcode secrets (tokens, passwords, private keys).
- Always use Jenkins credentials (`withCredentials`) for sensitive values.
- Avoid `sh` commands that may echo secrets.
- Validate external input (params, env, file contents) before using it.

---

## 10a. Inline Documentation

- Every Groovy file must start with a short header comment describing purpose and usage.
- Public functions/classes must include inline doc comments (`/** ... */`) with:
  - Purpose
  - Parameters
  - Return behavior
  - Expected errors (when applicable)
- Complex pipeline stages must include brief rationale comments.

---

## 10b. Testing & Coverage

**Test specification (naming, location, output, coverage) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

Specifics for Groovy:
- Use Spock or JUnit-based tests according to repository conventions.
- Keep tests deterministic and runnable in CI.

---

## 11. Prohibited Practices

- No metaprogramming in pipeline code.
- No long-lived non-serializable state in CPS context.
- No swallowing exceptions without logging.
- No printing environment dumps that might include secrets.

---

## 12. PR Requirements

Before merging:

- Pipeline code is CPS-safe (serializable state only)
- Clear error messages (`error(...)`) for invalid input
- No secrets in code or logs
- Shared logic extracted into library steps where appropriate
- Code is readable and consistently formatted
