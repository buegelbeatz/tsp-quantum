<!-- layer: digital-generic-team -->
# /quality-fix Prompt

Work through the findings reported by `/quality` and implement the corresponding fixes in the current repository scope.

```bash
make quality-fix
```

## Execution mode

- Execute exactly one shell command for this prompt: `make quality-fix`.
- Do not execute additional ad-hoc shell snippets from prompt prose unless the user explicitly asks for manual step-by-step execution.
- All detailed remediation logic belongs inside the invoked make target and its runtime scripts.

## Naming Clarification

- User-facing command: `/quality-fix`
- Runtime skill implementation: `shared/orchestration`
- Rationale: prompt names stay stable and short; skill folders are layer-scoped and explicit.

## What it does

1. Routes through the centralized `quality-expert` orchestrator (`make quality-fix`).
2. Runs `/quality` first to get the current report.
3. Uses that report as the authoritative worklist and fixes the reported points in scope.
4. If a finding requires a large or ambiguous refactor, it records the item as advisory follow-up instead of applying a risky change silently.
5. Re-runs `/quality` to show status deltas.

## Agent communication flow

1. `copilot` (`/quality-fix`) invokes the centralized `quality-expert` orchestrator.
2. `quality-expert` produces and updates runtime quality evidence in `.tests/python/reports/quality-expert-session.md`.
3. `shared/orchestration` consumes that report and works through the reported findings as the remediation backlog.
4. `shared/orchestration` re-checks and writes `.tests/python/reports/layer-quality-current.md`.
5. If deeper expert interpretation or an extensive refactor is required, the active delivery agent records an advisory follow-up in the run summary and may open a separate expert consultation later.
6. If results are transferred to review or delivery continuation, the transfer must use `work_handoff_v1`.

## Communication checkpoints (who/when/with whom)

- Before remediation: `copilot` -> `quality-expert` (orchestrator runtime gates).
- During remediation scope decisions: delivery agent records extensive or ambiguous refactors as advisory follow-up items in the `/quality-fix` summary.
- After remediation and re-check: delivery agent -> reviewer/delivery-next via `work_handoff_v1`.

## Constraints

- Scope: findings from the current report only.
- Work from the current `/quality` report instead of inventing unrelated cleanup work.
- Extensive refactors are reported as advisory follow-up and are not force-applied in the same automated run.
- No MCP servers.

## Handoff communication

- If fix results are handed to reviewer/delivery flow, use `work_handoff_v1`.

## Audit handoff output (mandatory)

After completing the fix run, write a structured handoff file and register it in the audit.

1. Store the YAML handoff under runtime handoff storage: `.digital-runtime/handoffs/audit/YYYY-MM-DD/<audit-code>/<message-id>-handoff.yaml`.
2. The file must contain a `kind:` field: `work_handoff_v1` for delivery transfer.
3. Run `make audit-amend MESSAGE_ID=<message-id> HANDOFF_FILE=<path>` to register it (the script keeps/normalizes the handoff under runtime storage).

Example handoff file:
```yaml
kind: work_handoff_v1
from: quality-expert
to: copilot
summary: Applied N low-risk fixes. Re-check passed. Ready for review.
assumptions: []
open_questions: []
```
