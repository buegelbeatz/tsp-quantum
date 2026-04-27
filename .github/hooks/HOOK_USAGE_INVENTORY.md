---
layer: digital-generic-team
---
# Hook Usage Inventory

Status: active-maintained
Last updated: 2026-04-22

## Purpose

Track usage evidence, ownership, and cleanup safety for hook scripts in `.github/hooks/`.

## Classification Keys

- `active-confirmed`: script has verified callers or observed usage.
- `active-likely`: script is part of lifecycle flow but needs stronger evidence.
- `needs-verification`: no current evidence collected yet.
- `unused-candidate`: no callers found, candidate for deprecation review.

## Inventory

| Hook file | Trigger path | Caller(s) | Last known evidence | Risk | Status |
|---|---|---|---|---|---|
| `pre-message.sh` | per-message pre-processing | `prompt-invoke-runtime.sh` | Hook resolution in [prompt-invoke-runtime.sh](prompt-invoke-runtime.sh#L57) + event mapping in `.github/skills/shared/runtime/scripts/update_runtime.py:411` | high | active-confirmed |
| `post-message.sh` | per-message post-processing | `prompt-invoke-runtime.sh` | Hook resolution in [prompt-invoke-runtime.sh](prompt-invoke-runtime.sh#L58) + event mapping in `.github/skills/shared/runtime/scripts/update_runtime.py:412` | high | active-confirmed |
| `session-start.sh` | session bootstrap | runtime adapter generation | Hook adapter mapping in `.github/skills/shared/runtime/scripts/update_runtime.py:410` | high | active-confirmed |
| `session-end.sh` | session teardown | unknown | Confirmed: no direct caller found in current repository scan (grep 2026-04-21). `update_runtime.py` maps `session-start` and `pre/post-message` but not `session-end`. | high | unused-candidate |
| `prompt-invoke.sh` | prompt wrapper entry | make command targets + governance | make mapping in `.github/make/commands.mk:24` + governance mandate in `.github/instructions/governance-layer/prompt-governance.instructions.md:62` | high | active-confirmed |
| `prompt-invoke-args.sh` | prompt invoke parsing | `prompt-invoke.sh` | sourced by `.github/hooks/prompt-invoke.sh:25` | medium | active-confirmed |
| `prompt-invoke-helpers.sh` | helper functions | `prompt-invoke.sh` | sourced by `.github/hooks/prompt-invoke.sh:26` | medium | active-confirmed |
| `prompt-invoke-paths.sh` | path resolution | `prompt-invoke.sh` | sourced by `.github/hooks/prompt-invoke.sh:27` | medium | active-confirmed |
| `prompt-invoke-runtime.sh` | runtime setup + hook dispatch | `prompt-invoke.sh` | sourced by `.github/hooks/prompt-invoke.sh:29` | medium | active-confirmed |
| `prompt-invoke-trace.sh` | trace output | `prompt-invoke.sh` | sourced by `.github/hooks/prompt-invoke.sh:28` | medium | active-confirmed |
| `README.md` | documentation | human readers | repository docs | low | active-confirmed |

## Cleanup Policy

- No hook may be deleted while status is `active-confirmed` or `active-likely`.
- A hook can move to `unused-candidate` only after caller grep evidence is attached.
- Deletion requires two-step flow:
  1. set status `unused-candidate` with evidence,
  2. deprecate one cycle with warning trace,
  3. remove only after no regressions.

## Current Closure State

1. `session-end.sh` has been moved to `unused-candidate` with documented no-caller evidence.
2. High-risk hooks have explicit caller evidence and remain `active-confirmed`.
3. Inventory is now maintained and revalidated when prompt-runtime or governance wiring changes.
