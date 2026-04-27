<!-- layer: digital-generic-team -->
# /audit-on Prompt

Enable deterministic audit logging for prompt and task workflows in this repository.

Default behavior: audit logging is enabled when no explicit state file exists.

```bash
make audit-on
```

## Execution contract

- Writes the audit state flag under `.digital-runtime/layers/<layer>/audit/state.env`.
- Enables hook-based audit emission for wrapped prompts (for example `/quality` and `/quality-fix`).
- Does not start MCP servers.

## Documentation contract

- Keep this prompt aligned with `task-audit-toggle.sh` behavior and output schema.

## Verification

- Run `make audit-on` and verify `enabled: "1"` is reported.
