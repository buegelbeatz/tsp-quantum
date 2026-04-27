---
name: "Test-expert / Test-standardss"
description: "Test Engineer Standards"
layer: digital-generic-team
---
# Test Engineer Standards


## Test Strategy

- Define unit, integration, and acceptance scope per feature.
- Focus on risk-driven test selection.
- Track coverage goals and critical-path reliability.

## Automation

- Integrate test execution in PR validation.
- Keep tests deterministic and fast where possible.
- Include negative-path and boundary scenarios.

## Release Gate

- No merge with failing required tests.
- Security-critical changes require explicit security regression coverage.
