---
name: "Test-expert / Kuttls"
description: "KUTTL Instructions (Kubernetes Integration Tests via YAML)"
layer: digital-generic-team
---
# KUTTL Instructions (Kubernetes Integration Tests via YAML)


These rules apply to all **KUTTL** tests in this repository.
KUTTL is used to validate Kubernetes/OpenShift resources and behaviors using YAML steps.

---

## 1. Purpose & Scope

Use KUTTL to validate:
- Kubernetes manifests apply successfully
- workloads become Ready (deployments, statefulsets)
- services/endpoints exist
- configmaps/secrets are referenced correctly
- CRDs/operators behave as expected (if applicable)

Do NOT use KUTTL for:
- deep API business logic (use Tavern/StepCI)
- UI end-to-end tests
- load/performance testing

---

## 2. Repository Structure

Recommended layout:

```
tests/
  kuttl/
    kuttl-test.yaml
    test-suite/
      01-deploy/
        00-install.yaml
        01-assert.yaml
      02-smoke/
        00-assert-ready.yaml
```

Rules:
- Keep suites small and ordered.
- Separate deploy and assertions into clear steps.
- Use one test suite per component if needed.

---

## 3. Naming Conventions

- Step files use numeric prefixes:
  - `00-*.yaml`, `01-*.yaml`, ...
- Keep steps focused:
  - install/apply
  - assert
  - cleanup (optional)

---

## 4. Cluster Targeting (Mandatory)

KUTTL tests must support:
- local cluster (kind/k3d)
- CI cluster / staging cluster

Rules:
- Namespace must be configurable.
- Do not hardcode cluster contexts.
- Do not depend on cluster-global state unless explicitly required.

---

## 5. Assertions & Readiness

- Prefer readiness-based assertions rather than sleep-based waits.
- Validate:
  - Deployment available replicas
  - Pod Ready condition
  - Services exist
  - Routes/Ingress exist (if applicable)

Avoid:
- fixed sleep delays
- fragile label selectors without stability

---

## 6. Example Assertion Pattern

Example: assert a deployment becomes available (conceptual):

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: my-app
status:
  availableReplicas: 1
```

Rules:
- Assertions should check stable fields.
- Do not assert fields that are volatile across clusters.

---

## 7. Running Tests (Local & CI)

KUTTL is typically executed against a running cluster.

Rules:
- Provide a consistent `make itest-k8s` target.
- Tests must fail the pipeline if any step fails.
- Ensure cleanup is performed for ephemeral environments.

---

## 8. OpenShift Notes

- For OpenShift, validate `Route` objects where applicable.
- Avoid assumptions about fixed user IDs (OpenShift runs arbitrary UIDs by default).

---

## 9. Anti-Patterns (Prohibited)

- ❌ relying on `sleep` instead of readiness checks
- ❌ hardcoding namespaces/contexts
- ❌ asserting volatile status fields (timestamps, UIDs)
- ❌ coupling tests to production-only resources
