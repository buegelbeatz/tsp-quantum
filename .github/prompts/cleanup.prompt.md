<!-- layer: digital-generic-team -->
# /cleanup

Run the repository cleanup workflow for board/sprint/wiki artifacts and mandatory GitHub resources.

Default command:

```bash
make cleanup
```

## Parameters

- `DRY_RUN` — `0` (default) runs destructive cleanup, `1` runs dry-run mode.
- `CONFIRM` — `1` (default) confirms destructive mode in non-interactive runs.
- `GITHUB_CLEANUP` — MUST be `1` (`/cleanup` requires GitHub-side cleanup).
- `REMOTE` — MUST be `1` (`/cleanup` requires remote ref cleanup).
- `BOARD` — optional board filter for board-scoped cleanup.

## Runtime contract

- Prompt frontdoor: `/cleanup`
- Make frontdoor: `make cleanup`
- Runtime implementation: `.github/skills/shared/orchestration/scripts/cleanup.sh`

## Information flow

| Field    | Value |
|----------|-------|
| Producer | `/cleanup` prompt / `make cleanup` target |
| Consumer | local git refs, local wiki files, mandatory GitHub resources |
| Trigger  | User invokes `/cleanup` or `make cleanup` |
| Payload  | Cleanup report and status output |
