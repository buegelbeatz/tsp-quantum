<!-- layer: digital-generic-team -->
# /audit-off Prompt

Disable deterministic audit logging for prompt and task workflows in this repository.

Default behavior is enabled; this prompt writes an explicit OFF override.

```bash
make audit-off
```

## Execution contract

- Writes the audit state flag under `.digital-runtime/layers/<layer>/audit/state.env`.
- Disables hook-based audit emission for wrapped prompts and task audit logging.
- Does not start MCP servers.

## Documentation contract

- Keep this prompt aligned with `task-audit-toggle.sh` behavior and output schema.

## Verification

- Run `make audit-off` and verify `enabled: "0"` is reported.
