---
name: "Test-expert / Testings"
description: "Testing Strategy Guidelines"
layer: digital-generic-team
---
# Testing Strategy Guidelines  
(Test Types, When to Use Them, and When They Don’t Make Sense)


This document provides a structured overview of common testing types,
when they are appropriate, for which project types they are recommended,
and when they may not provide sufficient value.

Testing should be risk-driven, proportional, and cost-aware.

Per-language linting gates are defined directly in the corresponding language
instruction files under `.github/instructions/languages/`.

---
# ⚠️ CRITICAL: Test Specification (Single Point of Truth)

**This section supersedes any conflicting guidance in language-specific or framework instructions.**
If a language instruction conflicts, this section takes priority.

## Test Naming
- **Mandatory:** All test files must be prefixed with `test_` (e.g., `test_auth.py`, `test_login.sh`)
- **Mandatory:** All test functions/methods must start with `test_` (e.g., `test_user_login_succeeds`)
- **Mandatory:** Test names must be descriptive: `test_<subject>_<scenario>`  
  Example: `test_admin_login_with_invalid_token_returns_401`

## Test Location
- **Mandatory:** Test files must reside **as close as possible** to the code they test.
  - Colocate: `src/auth.py` → `src/test_auth.py` or `src/tests/test_auth.py`
  - Avoid: Centralizing all tests in a distant `tests/` directory
- **Rationale:** Proximity reduces test maintenance burden and keeps related logic together.

## Test Output (Artifacts, Caches, Temporary Files)
- **Mandatory:** All test artifacts, caches, temporary files, and logs must be written to `.tests/<language>/` directory at the repository root.
- **Mandatory:** No other directory may contain test artifacts. 
  - Example: `.tests/python/`, `.tests/bash/`, `.tests/nextflow/`, `.tests/terraform/`, etc.
- **Mandatory:** Add `.tests/` to `.gitignore` to prevent accidental commits.
- **Rationale:** Centralizing outputs makes cleanup simple (e.g., `rm -rf .tests/`), prevents repo bloat, and keeps working directories clean.

### Output Subdirectory Structure (Recommended)
```
.tests/
├── python/
│   ├── pytest-cache/
│   ├── coverage/
│   ├── .coverage.json
│   └── test-reports/
├── bash/
│   ├── bats-output/
│   └── test-reports/
├── nextflow/
│   ├── work/
│   └── test-reports/
└── general/
    ├── temp/
    └── logs/
```

## Code Coverage

**Mandatory Minimum:**
- **Minimum threshold:** ≥ 80% code coverage for all production code.
- **Exceptions** (Waiver Allowed):
  - Thin wrappers around third-party libraries (no logic to cover).
  - Highly language-/framework-specific boilerplate (e.g., `__init__.py`, config registration).
  - Short-lived prototypes or PoCs (explicitly documented as such).
  - Infrastructure-as-code (IaC) validation tests replace coverage metrics; use schema/policy tests instead.
  - Disposable experimental branches (clearly marked; do not merge without addressing).
- **Measurement:** Coverage thresholds apply to:
  - Source code `/src/`, `/lib/`, `/provider/`, `/sidecar/` (project-specific).
  - Exclude test files, vendor, generated code, and `.venv/`.
- **Reporting:**
  - CI must fail if coverage drops below 80% (unless waived).
  - Generate and archive coverage reports in `.tests/<language>/coverage/`.
  - Track coverage trends over time (optional but recommended for long-running projects).

---
# 1. Core Testing Layers

## 1.1 Unit Tests

**Purpose**
- Validate isolated functions, classes, and domain logic.
- No external dependencies.

**Mandatory Environment Isolation**
- Unit tests must not read secrets or operational values from `.env`.
- Unit tests must not source `.env` directly or indirectly (Bash and Python).
- Unit tests must use explicit test fixtures/mocks/dummy environment values (e.g. `POSTGRES_PASSWORD=test`).
- Any test requiring real secrets, real infrastructure credentials, or user-local environment state is not a unit test and must be moved to integration/e2e scope.

**Use When**
- Business logic exists.
- Algorithms, parsing, validation, transformations are present.
- Building libraries, SDKs, backend services, pipelines.

**Recommended For**
- Libraries / SDKs
- Backend APIs
- Microservices
- Data processing pipelines
- CLI tools

**Usually Not Needed When**
- Thin wrappers around external SDKs with no logic.
- Disposable prototypes (though minimal coverage is still recommended).

---

## 1.2 Integration Tests

**Purpose**
- Validate interaction between components.
- Often include database, filesystem, message broker, cache, or external APIs.

**Use When**
- External dependencies exist.
- Infrastructure interactions are critical.

**Recommended For**
- Backend services
- Microservices
- Event-driven systems
- ETL / data pipelines
- CLI tools using filesystem or subprocesses

**Less Useful When**
- Pure libraries without external dependencies.
- Third-party systems cannot be meaningfully simulated (consider contract tests instead).

---

## 1.3 End-to-End (E2E) Tests

**Purpose**
- Validate complete user flows.
- Simulate real-world behavior across full stack.

**Use When**
- Application includes UI + backend + persistence.
- Critical business journeys exist (login, checkout, onboarding).

**Recommended For**
- Web applications
- SaaS platforms
- Multi-component systems

**Avoid Overuse When**
- UI changes frequently and tests become brittle.
- CI time becomes excessive.
- A smaller set of critical flows is sufficient.

---

## 1.4 Smoke Tests

**Purpose**
- Ensure system starts and basic functionality works after deployment.

**Use When**
- Deploying to staging or production environments.

**Recommended For**
- All deployed services
- APIs
- Infrastructure deployments

**Not Needed For**
- Pure libraries with no runtime deployment.

---

## 1.5 Sanity Tests

**Purpose**
- Quick validation after a bug fix or minor change.

**Use When**
- Confirming narrow-scope fixes.

**Often Redundant When**
- Comprehensive regression suites already exist.

---

## 1.6 Regression Tests

**Purpose**
- Ensure previously working features still function.

**Use When**
- Systems evolve over time.
- Releases occur frequently.

**Recommended For**
- Production systems
- Refactor-heavy projects

**Less Valuable For**
- Very early-stage prototypes.

---

# 2. Architectural & Advanced Testing

## 2.1 Contract Tests

**Purpose**
- Validate API contracts between services or teams.

**Use When**
- Microservices architecture.
- Frontend ↔ Backend separation.
- Consumer-driven contracts required.

**Recommended For**
- Multi-team environments
- API-driven systems

**Not Necessary When**
- Monolith without external consumers.

---

## 2.2 API Tests

**Purpose**
- Validate HTTP-level behavior without full UI involvement.

**Use When**
- Backend APIs exist.
- UI tests are too fragile or slow.

**Recommended For**
- Backend services
- Microservices

---

## 2.3 Property-Based Testing

**Purpose**
- Validate invariants across many randomized inputs.

**Use When**
- Parsing, serialization, algorithms.
- Edge-case heavy domains.

**Recommended For**
- Core libraries
- Validation logic
- Scientific/data processing systems

**Less Useful When**
- CRUD-heavy systems without complex logic.

---

## 2.4 Mutation Testing

**Purpose**
- Validate test suite effectiveness by introducing artificial faults.

**Use When**
- High reliability is required.
- Critical business logic modules.

**Avoid When**
- CI time constraints are strict.
- System is very large and mutation scope is unclear.

---

# 3. Non-Functional Testing

## 3.1 Performance / Load Testing

**Purpose**
- Validate throughput, latency, scalability.

**Use When**
- SLAs exist.
- High traffic expected.
- Cloud cost control matters.

**Recommended For**
- Public APIs
- High-scale services
- Real-time systems

**Not Critical When**
- Internal low-traffic tools.

---

## 3.2 Stress Testing

**Purpose**
- Identify system breaking points.

**Use When**
- Resilience planning required.
- High availability systems.

---

## 3.3 Soak / Endurance Testing

**Purpose**
- Detect memory leaks or long-term degradation.

**Use When**
- Long-running services.
- Stateful systems.

---

## 3.4 Security Testing

Includes:
- SAST (static analysis)
- DAST (dynamic scanning)
- Dependency scanning
- Container scanning

**Use When**
- Always, once deploying or using third-party dependencies.

**Mandatory For**
- Public repositories
- Internet-facing services
- Systems handling sensitive data

---

# 4. Testing by Project Type

---

## 4.1 Library / SDK

Recommended:
- Heavy Unit Tests
- Property-Based Tests (if logic-heavy)
- Dependency Scans

Optional:
- Minimal Integration Tests

Avoid:
- E2E Tests
- Deployment Smoke Tests

---

## 4.2 Backend API / Microservice

Recommended:
- Unit Tests
- Integration Tests (DB/cache/broker)
- API Tests
- Contract Tests (if distributed)
- Smoke Tests
- Security Scanning
- Performance Baseline (if SLA-driven)

Avoid:
- Excessive cross-service E2E tests

---

## 4.3 Web Application (Frontend + Backend)

Recommended:
- Unit Tests (logic)
- Component Tests (frontend)
- Integration Tests (backend)
- API Tests
- Limited Critical E2E Flows
- Smoke Tests
- Security Scanning
- Optional Visual Regression

Avoid:
- Large brittle E2E suites replacing other test layers

---

## 4.4 Data / ETL / Workflow Systems (e.g., Nextflow)

Recommended:
- Unit Tests (transformations)
- Integration Tests (I/O + format validation)
- Smoke Test (mini dataset run)
- Golden-output regression tests
- Performance tests (for scale)
- Security scans

Avoid:
- Full-scale production-size runs in CI

---

## 4.5 CLI Tools

Recommended:
- Unit Tests
- Integration Tests (filesystem/subprocess)
- Smoke Tests (`--help`, basic command)

Optional:
- End-to-end command workflows

---

## 4.6 Infrastructure / Kubernetes / OpenShift

Recommended:
- YAML/schema validation
- Policy tests (OPA/Conftest)
- Image/container scanning
- Smoke deployment test (rollout success)

Avoid:
- Traditional unit tests unless generating manifests programmatically

---

# 5. When Tests Do NOT Make Sense

- Extremely short-lived PoCs.
- Disposable experimental code.
- Ultra-simple glue code without logic.
- Systems where mocking provides no meaningful signal.

However:
- Even minimal coverage of critical logic is almost always beneficial.

---

# 6. Practical Rule of Thumb

- Unit Tests: Almost always required.
- Integration Tests: Required when external systems exist.
- E2E Tests: Only for critical user journeys.
- Smoke Tests: Always after deployment.
- Contract Tests: Required for multi-service architectures.
- Security Scans: Always once deploying or using dependencies.
- Performance Tests: Required if SLAs or scale matter.

---

# 7. Testing Philosophy

- Test risk, not lines of code.
- Favor fast, deterministic tests.
- Avoid over-reliance on slow, brittle E2E suites.
- Balance coverage with maintainability.
- Keep CI pipelines proportional to project complexity.
