---
name: "Test-expert / Taverns"
description: "Tavern Instructions (YAML API Integration Tests via pytest)"
layer: digital-generic-team
---
# Tavern Instructions (YAML API Integration Tests via pytest)


These rules apply to all **Tavern** tests in this repository.
Tavern is used for **HTTP API integration tests** using YAML specs executed by `pytest`.

---

## 1. Purpose & Scope

Use Tavern to validate:
- request/response correctness (status, headers, JSON schema/values)
- multi-step API flows (auth, sessions, redirects, token exchanges)
- negative cases (invalid input, expired tokens, permission errors)
- integration behavior against a running environment (local cluster or deployed)

Do NOT use Tavern for:
- UI/browser-level tests (use Playwright/Selenium)
- heavy load/performance testing (use k6/locust)
- tests requiring complex loops/data generation inside YAML (use Python tests)

---

## 2. Repository Structure

Recommended layout:

```
tests/
  tavern/
    conftest.py
    stages/
      auth_login.tavern.yaml
      webauthn_flow.tavern.yaml
      qr_redirect.tavern.yaml
```

Rules:
- Group tests by feature or flow.
- Keep YAML files small and focused (one flow per file).

---

## 3. Naming Conventions

**Test specification (naming, location, output) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

Tavern-specific:
- Test files: `*.tavern.yaml` (recommended), or `test_*.yaml` if repo convention requires it.
- Use descriptive names:
  - `webauthn_register.tavern.yaml`
  - `qr_redirect.tavern.yaml`

---

## 4. Environment Configuration (Mandatory)

Tests must be environment-agnostic.
Use a base URL provided by environment variables:

- `BASE_URL`
- optional: `API_TOKEN`, `CLIENT_ID`, etc.

Rules:
- Never hardcode hostnames in test specs.
- Never store secrets in YAML files.
- Use CI secret injection and local `.env` for developer runs.

---

## 5. Example Tavern Test (Multi-Step Flow)

```yaml
test_name: "QR endpoint returns redirect"

stages:
  - name: "Call QR endpoint"
    request:
      url: "{env:BASE_URL}/api/qr"
      method: GET
    response:
      status_code: 302
      headers:
        location: !re_fullmatch "https://.*"
```

Example JSON assertion:

```yaml
test_name: "Health endpoint"
stages:
  - name: "Health"
    request:
      url: "{env:BASE_URL}/health"
      method: GET
    response:
      status_code: 200
      json:
        status: "ok"
```

---

## 6. Test Design Rules

- Prefer explicit assertions over loose matching.
- Include negative tests for security-critical endpoints.
- Avoid time-dependent assertions.
- Keep payloads minimal; use fixtures for larger payloads.

---

## 7. Running Tests (Local & CI)

- Must run via pytest, typically:

```
pytest -q tests/tavern
```

Rules:
- Tests must run against local deployments (e.g., kind/k3d) and deployed environments.
- Provide a `make itest-api` (or equivalent) to run Tavern consistently.

---

## 8. CI Requirements

- Run Tavern tests after deployment to a test environment.
- CI must fail on any test failure.
- Keep tests deterministic; avoid flakey external dependencies.

---

## 9. Anti-Patterns (Prohibited)

- ❌ hardcoded secrets or tokens in YAML
- ❌ tests depending on external internet services
- ❌ overly broad regex assertions that hide failures
- ❌ using Tavern for load testing
