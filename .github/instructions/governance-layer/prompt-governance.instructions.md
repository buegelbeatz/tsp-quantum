---
name: prompt-governance
description: governance rules for adding and maintaining slash prompts
layer: digital-generic-team
---

# Prompt Governance Instructions

## Scope

Apply these rules whenever a new prompt is created or an existing prompt is changed.

## Mandatory prompt requirements

- Create prompt files as `prompts/<command>.prompt.md`.
- Do NOT create a matching `skills/prompt-<command>/SKILL.md` wrapper skill — this repo uses direct canonical skills (e.g., `skills/quality-expert/SKILL.md`). Reference them from the prompt's `## Execution contract` section instead.
- Expose slash prompts through direct make targets named exactly like the command token (`make <command>`); do not add user-facing `prompt-<command>` make aliases.
- Ensure `/help` contains exactly one one-line entry for each prompt command.
- Treat `.github/` as the only source of truth for prompt changes; never edit `.claude/commands/` directly.
- Synchronize `.claude/commands/` only via `/update` or `bash update.sh` after `.github/prompts/` changes.
- Use `make ...` command examples for all tool or script invocations in shell code blocks.
- Keep prompt content concise, deterministic, and execution-oriented.
- Prompt execution must be single-command by default: one `make <command>` call for the prompt entrypoint, with no additional ad-hoc shell command execution unless explicitly requested by the user.
- For prompt orchestration shell entrypoints, do not use shell heredoc blocks (for example `<<EOF` or `<<'PY'`). Move complex multiline logic into dedicated runtime files and invoke them from shell.
- Every new tooling asset generated for a prompt workflow MUST document an explicit information flow contract:
	- prompt file: include a dedicated `## Information flow` section.
	- any agent created or updated for the same tooling change: include a dedicated `## Information Flow` section.
- Information flow sections MUST explicitly state at least: producer, consumer, trigger, and payload summary.
- Every prompt MUST include a dedicated `## Dependencies` section that references canonical skill contracts.
- The `## Dependencies` section MUST contain at least one dependency path to an existing skill contract file (`SKILL.md`).
- Dependency entries SHOULD use repository-root relative paths under `.github/skills/.../SKILL.md` for deterministic validation.

## Prompt blueprint

Every new prompt should follow this minimum structure in order:

1. `# /<command> Prompt`
2. Short purpose paragraph (one to three lines)
3. `Default command` with one shell code block using `make ...`
4. `## Execution contract`
5. `## Information flow`
6. `## Documentation contract`
7. `## Verification`

Command token policy:

- Prompt filename: `prompts/<command>.prompt.md`
- Command token regex: `^[a-z0-9]+(-[a-z0-9]+)*$`

Command example policy:

- Shell code blocks that execute tools or scripts must use `make` targets.
- Prompt examples must use `make <command>` for the slash prompt itself, not `make prompt-<command>`.
- Avoid direct invocations such as `python ...`, `bash ...`, or raw script paths in prompt examples.
- If runtime flags are needed, pass them via make variables.
- Script resolution for prompt-internal script calls must use `.github/` paths.
- Use `resolve_script_path()` from `.github/skills/shared/shell/scripts/lib/governance.sh` for deterministic lookup.

## Automatic Hook Invocation (Message Lifecycle)

- Prompts that execute significant operations MUST wrap command execution with `.github/hooks/prompt-invoke.sh`.
- The wrapper triggers pre/post-message hooks and writes audit entries under `.digital-artifacts/70-audits/YYYY-MM-DD/`.
- Wrapper location in source-of-truth: `.github/hooks/prompt-invoke.sh`.
- Wire the wrapper inside the canonical `make <command>` target instead of exposing a separate wrapper alias.

## Preferred workflow

Use the scaffold hook for new prompts:

```bash
make scaffold-prompt PROMPT_NAME=<command> PROMPT_PURPOSE="one-line purpose"
```

After scaffold creation, replace placeholder make targets with existing repository targets and run quality checks.

Documentation sync:

- Add exactly one one-line command entry in `prompts/help.prompt.md`.
- Do NOT create `skills/prompt-<command>/SKILL.md` wrapper skills; reference canonical skills directly via the prompt's `## Execution contract`.
- Keep prompt dependency declarations concrete: list the canonical skill paths that the prompt delegates to.
- Keep prompt/skill/agent information flow sections aligned for the same command scope.
- Keep wording concise and operational.

## MCP Lifecycle Contract

Any prompt or skill that requires one or more MCP servers MUST declare an explicit lifecycle contract:

- List required server IDs in the prompt's `## Execution contract` section.
- Enable servers at the start of the execution via `make mcp-vscode-enable MCP_SERVERS="<id>,<id>"`.
- Disable all servers at the end via `make mcp-vscode-disable`.
- Prompts that do NOT require MCP servers MUST NOT enable them.
- Only server IDs registered in `metadata/mcp-servers.csv` with a declared `prompt_owner` are eligible for on-demand activation.
- Prompts that do not own a server (i.e., `prompt_owner` ≠ prompt name and ≠ `*`) must not activate it without explicit justification.

## Verification

- Run `make layer-quality` to validate prompt governance checks.
- Confirm that all prompts pass `## Dependencies` validation (section present, non-empty, resolvable paths).
- Resolve any failed findings before considering the prompt ready.

## Prompt Enablement Policy File

Prompt deactivation must be configured in `.digital-team/prompt-governance.yaml`.

Example:

```yaml
disabled_prompts:
	- quality
	- quality-fix
```

`/update` prunes disabled prompt files and removes stale lines from `/help` accordingly.
