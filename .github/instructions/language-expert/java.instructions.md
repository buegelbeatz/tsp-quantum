---
name: "Language-expert / Javas"
description: "Java Backend Instructions"
layer: digital-generic-team
---
# Java Backend Instructions


## Scope

Java service implementations, libraries, and backend tooling.

## Coding Requirements

- Use explicit package structure by bounded context.
- Keep classes focused and avoid god objects.
- Use constructor injection for dependencies.
- Validate input and prefer immutable DTOs where feasible.

## Testing

- Unit tests for service and utility logic.
- Integration tests for repository and API boundaries.
- Contract tests for external interfaces when applicable.

## Build and Quality

- Enforce formatting and static checks in CI.
- Fail build on test failures or critical vulnerabilities.
