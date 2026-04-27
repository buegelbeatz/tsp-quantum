<!-- layer: digital-generic-team -->
# /update Prompt

Run the full layer update — refreshes `.github/` from inherited layers and adapts `.claude/` from the updated `.github/`:

```bash
make update
```

Report after completion:
- Which layers were fetched (names and sources)
- Files added/updated/removed in `.github/` (grouped by type: agents, instructions, skills, prompts, hooks)
- Files generated/updated in `.claude/` (commands, agents, CLAUDE.md with import count)
- The `layer:` attribution summary (how many files per layer)
- Any warnings or errors encountered

Reporting constraint:
- Use the summary emitted by `make update` itself.
- Do not run ad-hoc follow-up terminal analysis commands (for example extra `git`/`python` report commands) only to build the `/update` report.

## How the update works

Implementation constraint:
- `update.sh` must not use shell heredoc blocks for embedded scripts.
- Python helper logic is delegated to `.github/skills/shared/runtime/scripts/update_runtime.py`.

1. **Phase 1 — `.github/` refresh:**
   - Reads `.digital-team/layers.yaml` for the ordered list of parent layers.
   - Backs up local files (those tagged `layer: <current-repo>` or untagged).
   - For each parent layer: clones/copies source, merges its `.github/` content,
     injects `layer: <layer-name>` into every file's YAML/Markdown/shell frontmatter.
   - Re-applies local files on top (local overrides win).
   - Regenerates `index.instructions.md` for each instruction category.

2. **Phase 2 — `.claude/` adaptation:**
   - `.github/prompts/*.prompt.md` → `.claude/commands/*.md` (filename: `.prompt` removed)
   - `.github/agents/*.agent.md` → `.claude/agents/*.md` (Copilot-specific keys removed)
   - `.github/instructions/**/*.md` → `.claude/CLAUDE.md` (via `@`-imports, no duplication)

## Developing in this repo

- Edit files directly in `.github/` — no more `.digital-team/NN-*/` indirection.
- New files: leave the `layer:` key unset or set it to this repo's name. `/update` preserves them.
- Inherited files (different `layer:` value): refreshed from parent on each `/update`.
- Run `/update` after editing to keep `.claude/` in sync.
