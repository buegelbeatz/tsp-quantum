---
name: layer-override
description: Governance rules for safe creation of agents, instructions, and skills in intermediate and app layers — prevents accidental parent-layer overrides
layer: digital-generic-team
---

# Layer Override Governance

## When This Applies

These rules apply whenever you are working in a **Layer N** (intermediate layer) or **App layer** repo — i.e. any repo whose `.digital-team/layers.yaml` contains at least one parent entry.

Layer 0 (`digital-generic-team`) has no parents; override checks are not applicable there.

## The Override Risk

When `/update` merges parent layers into `.github/`, any file in the current repo that shares the **same path** as a parent-layer file **silently replaces** the inherited version. This is intentional for explicit customization — but unintentional overrides cause hard-to-trace behavioral changes.

Affected asset types: `agents/`, `instructions/`, `skills/`, `prompts/`, `hooks/`.

## Mandatory Check Before Creating New Assets

Before creating any new agent, instruction, skill, or prompt in a Layer N or App repo, you MUST:

1. **Check for name collisions** — search the inherited `.github/` for an existing file with the same path:
   ```bash
   # Check all parent-layer files with their layer: tag
   grep -r "^layer:" .github/agents/ .github/instructions/ .github/skills/ .github/prompts/ \
     | grep -v "layer: <current-repo>"
   ```
2. **If a collision exists:** decide explicitly:
   - **Override intended** → document the reason in the file's frontmatter with `override-reason: <why>` and proceed.
   - **Override NOT intended** → choose a different name (e.g. prefix with the current layer name).

## Rules for Automated Asset Creation (Chat / Agent Workflows)

When creating assets automatically through slash commands or agent workflows, apply these rules **without prompting the user for confirmation** unless a collision is detected:

- **No collision found** → create the asset, set `layer: <current-repo>` in frontmatter, continue.
- **Collision found** → **STOP and inform the user explicitly:**
  ```
  ⚠ LAYER OVERRIDE WARNING
  The file `.github/<type>/<name>` already exists in parent layer '<parent-layer>'.
  Creating it here will replace the inherited behavior on the next /update.
  
  Options:
    A) Override intentionally — add `override-reason:` to the frontmatter and proceed.
    B) Use a different name — suggest: `<current-layer>-<name>` or `<name>-<current-layer>`.
    C) Abort — do not create the file.
  
  Please choose A, B, or C.
  ```

## Frontmatter Convention for Intentional Overrides

```yaml
---
name: quality-expert          # same as parent — intentional override
layer: my-app                 # current repo
override-reason: "Adds domain-specific Python linting rules not present in base layer"
---
```

The `override-reason:` key is informational only — it is preserved by `/update` and serves as a self-documenting audit trail.

## Mandatory Override Registry (Enterprise)

Intentional overrides MUST also be listed in `.digital-team/overrides.yaml`.

Required fields per entry:

```yaml
overrides:
  - path: prompts/help.prompt.md
    owner_layer: digital-iot-team
    base_layer: digital-generic-team
    base_hash: <sha256-of-parent-file-content>
    reason: "Adds domain-specific prompt guidance"
    mode: replace
```

Validation rules during `/update`:

- Every local path collision with inherited `.github/` files MUST have an override entry.
- `owner_layer` MUST match the current repo layer.
- `base_hash` MUST match the current inherited parent content.
- Hash mismatch is treated as override drift and blocks update completion.

## Verification

`make layer-quality` (or `/quality`) validates override hygiene:
- Files with `layer: <current-repo>` that share a path with an inherited file but lack `override-reason:` are flagged as **unintentional override candidates**.
