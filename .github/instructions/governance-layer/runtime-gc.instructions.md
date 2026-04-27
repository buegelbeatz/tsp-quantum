---
name: "Runtime Garbage Collection Governance"
description: "Defines safe retention, cleanup cadence, and guardrails for .digital-runtime lifecycle data"
applyTo: "**"
layer: digital-generic-team
---

# Runtime Garbage Collection Governance

## Purpose

Keep `.digital-runtime/` healthy and bounded without breaking active developer sessions.

## Scope

Applies to all runtime subdirectories under `.digital-runtime/`.

## Retention Classes

- **Short TTL (3-7 days)**
  - `.digital-runtime/tmp/`
  - `.digital-runtime/temp/`
- **Medium TTL (14-30 days unless pinned)**
  - `.digital-runtime/reports/`
  - `.digital-runtime/chrome/`
- **Persistent (do not auto-delete)**
  - `.digital-runtime/layers/`
  - `.digital-runtime/handoffs/`

## Cleanup Rules

- Cleanup must default to dry-run mode.
- Destructive cleanup requires an explicit flag.
- Pinned artifacts must be excluded from deletion.
- Active session artifacts must never be deleted.

## Pinning

A runtime artifact can be protected by one of the following:
- sibling `.pin` marker file,
- path listed in a cleanup allowlist override file,
- active session reference in runtime metadata.

## Safety Checks

Before destructive cleanup:
1. Verify no active session references the target path.
2. Verify target is not in persistent class.
3. Print deterministic summary of candidate removals.

After cleanup:
- Emit structured report with:
  - removed path count,
  - reclaimed size,
  - skipped pinned paths,
  - skipped active-session paths.

## Operational Contract

- Runtime cleanup tooling must be idempotent.
- Cleanup jobs must log to `.digital-runtime/reports/`.
- Cleanup scripts must not mutate files outside `.digital-runtime/`.

## Governance

- `/quality` should flag cleanup scripts that do not offer dry-run mode.
- `/quality` should flag runtime cleanup scripts that target `.digital-runtime/layers/` by default.
