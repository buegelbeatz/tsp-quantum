<!-- layer: digital-generic-team -->
# /stages-action Prompt

Run the full stage workflow for a given stage. In digital-generic-team, supported stage aliases are `/exploration` and `/project`.

Default command:

```bash
make stages-action STAGE=<stage>
```

## Parameters

- `stage` — required. Stage command name (`exploration` or `project`). Determines which stage instructions apply.
- `TARGET_REPO_ROOT` / `DIGITAL_TARGET_REPO_ROOT` — optional absolute path to the intended target repository. Defaults to current working directory.
- `TARGET_REPO_SLUG` / `DIGITAL_TARGET_REPO_SLUG` — optional GitHub slug override (`owner/repo`) for remote/API operations.

Example:

```bash
TARGET_REPO_ROOT=/Users/becchri1/Documents/tsp-quantum \
TARGET_REPO_SLUG=becchri1/tsp-quantum \
make stages-action STAGE=project
```

## Runtime contract

- This prompt is the canonical runtime entrypoint for `make stages-action STAGE=<stage>`.
- Runtime metadata is discovered from `.github/skills/stages-action/stages.yaml`.
- Normative stage rules, readiness gates, required inputs, language policy, and delivery/review governance live only in `.github/instructions/stages/*.instructions.md` plus shared governance instructions.
- Runtime output artifacts include stage diagnostics and status files under `.digital-artifacts/60-review/` and runtime handoffs under `.digital-runtime/handoffs/<stage>/`.

## Runtime behavior

1. Resolve the requested stage from prompt input.
2. Optionally read `make stages` output for status display.
3. Execute the canonical command:

```bash
make stages-action STAGE=<stage>
```

4. Surface the generated runtime status artifacts, especially:
   - `.digital-artifacts/60-review/*/<stage>/stage-handoff.md`
   - `.digital-artifacts/60-review/*/<stage>/delivery-automation-status.md`
   - `.digital-artifacts/60-review/*/<stage>/delivery-review-status.md`
   - `.digital-artifacts/60-review/*/<stage>/why-not-progressing.md`
   - `.digital-artifacts/60-review/*/<stage>/stage-completion-status.md`

## Mandatory delivery follow-up for stage=project

When `stage=project` and runtime reports `delivery=triggered` or `delivery=already_dispatched`, prompt execution MUST:

1. Read runtime handoffs from `.digital-runtime/handoffs/project/*-handoff.yaml`.
2. Dispatch each handoff that is either pending/missing status, or active (`in-progress`) without completion evidence (`pr_url`/`pr_link` + `approved_by`).
3. For each dispatchable handoff, invoke `runSubagent` with `agentName=<receiver>` and include handoff context.
4. Poll handoff progress via:

```bash
bash .github/skills/stages-action/scripts/check-delivery-work.sh project
```

5. Print intermediate chat progress updates (queued/active/done and changed tasks).
6. Include per-task context in polling updates (intent/source/age when available) and heartbeat updates at least every 20-30 seconds during long waits.
7. For active project tickets, attempt PR creation/evidence capture and always surface PR URL or explicit blocker/remediation.
8. Continue until no dispatchable handoffs remain or no additional automated dispatch is possible.

Do not stop at handoff generation while delivery is still pending.

## ExistingProjectFlow

- ExistingProjectFlow is the mandatory review follow-up path after delivery dispatch.
- If follow-up artifacts indicate unresolved blockers or review gaps, keep the stage in-progress and continue the review loop instead of forcing completion.

## Verification

- Progress markers are emitted by the runtime pipeline.
- Final output must identify the relevant generated status artifacts and next actionable state.
