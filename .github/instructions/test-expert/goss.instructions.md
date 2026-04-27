---
name: "Test-expert / Gosss"
description: "Goss Instructions (Container / Image Validation)"
layer: digital-generic-team
---
# Goss Instructions (Container / Image Validation)


These rules apply to all **Goss** tests in this repository.
Goss is used to validate container images and running containers (smoke/integration checks).

---

## 1. Purpose & Scope

Use Goss to verify:
- container starts correctly
- required files and directories exist
- expected users/permissions are present
- ports are listening
- processes are running (if applicable)
- HTTP endpoints respond correctly
- basic runtime dependencies exist

Do NOT use Goss for:
- multi-service business flows (use Tavern/StepCI)
- full UI/end-to-end journeys
- deep functional validation that requires complex logic

---

## 2. Repository Structure

Recommended layout:

```
tests/
  goss/
    <image-name>/
      goss.yaml
      goss_vars.yaml (optional)
      README.md (optional)
```

Rules:
- One `goss.yaml` per image or per container role.
- Keep checks minimal, deterministic, and fast.

---

## 3. Test File Naming

**Test specification (naming, location, output) is defined in `.github/instructions/testing/testing.instructions.md`.**  
**If this section conflicts with that file, the testing.instructions.md takes priority.**

Goss-specific:
- Default file name: `goss.yaml`
- Optional variables file: `goss_vars.yaml`

---

## 4. Test Design Rules

- Prefer small, stable checks that indicate container correctness.
- Avoid flakey checks (timing-sensitive, external network dependencies).
- Do not assert dynamic timestamps or volatile log output.
- Use HTTP checks for `/health`, `/ready`, `/version` where available.

---

## 5. Example `goss.yaml` (Minimal)

```yaml
file:
  /app:
    exists: true
    mode: "0755"

port:
  tcp:8080:
    listening: true

http:
  http://localhost:8080/health:
    status: 200
    timeout: 2000

user:
  app:
    exists: true
```

---

## 6. Running Tests (Local & CI)

Recommended patterns:

- Against a running container:
  - mount `goss.yaml` into container or run goss in a test container
- Against an image (preferred via `dgoss` if available):
  - run the image
  - execute goss inside or alongside it

Rules:
- Tests must be runnable locally and in CI with the same command path (via `make` target).
- Do not hardcode environment-specific hostnames; parameterize via variables where needed.

---

## 7. CI Requirements

- Goss must run on every image build (PR or main branch) where images are produced.
- CI must fail if any Goss test fails.
- Keep runtime small (target: seconds, not minutes).

---

## 8. Anti-Patterns (Prohibited)

- ❌ calling external production services
- ❌ relying on timing without retry/backoff strategy
- ❌ validating full business flows
- ❌ embedding secrets into test specs
