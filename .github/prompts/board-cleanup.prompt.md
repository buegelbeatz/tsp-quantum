<!-- layer: digital-generic-team -->
# /board-cleanup

Delete board refs under refs/board/* to clean up stale or wrongly assigned tickets.

The default execution is protected and requires explicit confirmation.

## Safety

- Without `APPLY=1`, execution aborts.
- Optional single-board cleanup (`BOARD=<name>`).
- Optional remote cleanup (`REMOTE=1`).

## Examples

```bash
# Alle lokalen Board-Refs löschen
make board-cleanup APPLY=1

# Delete only the project board
make board-cleanup APPLY=1 BOARD=project

# Delete local and remote refs
make board-cleanup APPLY=1 REMOTE=1
```

## Information flow

| Field    | Value |
|----------|-------|
| Producer | board-cleanup.sh |
| Consumer | git refs under refs/board/* |
| Trigger  | User invokes /board-cleanup |
| Payload  | Deleted board refs (local, optional remote) |
