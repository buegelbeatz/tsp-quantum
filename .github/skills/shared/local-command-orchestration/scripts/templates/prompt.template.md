---
layer: digital-generic-team
---
# /__PROMPT_NAME__ Prompt

__PROMPT_PURPOSE__

Default command:

```bash
make __PROMPT_NAME__
```

## Execution contract

- Keep command execution deterministic.
- Use only `make ...` invocations for tool/script execution examples.
- Emit explicit progress markers where long-running orchestration is expected.

## Information flow

- Producer: /__PROMPT_NAME__ prompt wrapper and assigned delivery/expert agents.
- Consumer: reviewers, downstream role agents, and audit logs.
- Trigger: prompt invocation start, delegated execution steps, and completion.
- Payload summary: command intent, handoff metadata, execution status, and resulting artifacts.

## Documentation contract

- Keep one-line purpose in `prompts/help.prompt.md` in sync with this prompt.
- Reference canonical skills from `## Execution contract` — do NOT create a `skills/prompt-__PROMPT_NAME__/SKILL.md` wrapper.
- Keep the canonical make target in `.github/make/commands.mk` named `__PROMPT_NAME__`.
- Keep examples concise and executable with repository-local make targets.
