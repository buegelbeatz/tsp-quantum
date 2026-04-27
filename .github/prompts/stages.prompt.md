<!-- layer: digital-generic-team -->
# /stages Prompt

Show all available stages, their status in this repository, and their source layer.

Default command:

```bash
make stages
```

## Runtime contract

1. Read centralized stage metadata from `.github/skills/stages-action/stages.yaml`.
2. Use `.github/instructions/stages/*.instructions.md` only as governance reference, not as runtime metadata source.
3. For each stage, inspect the canonical stage artifact/state and print a table:

   | Command | Stage | Status | Layer |
   |---------|-------|--------|-------|
   | `/exploration` | Exploration | available | digital-generic-team |
   | ... | | | |

4. Show the active stage (if any) prominently at the top.
5. Print the one-line description from stage metadata for each stage.

## Documentation contract

No files are written. Read-only overview.

## Verification

Output must include all stages discovered from `.github/skills/stages-action/stages.yaml`.
Output must include the `layer:` source for each stage.
