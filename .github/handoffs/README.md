---
layer: digital-generic-team
---
# handoffs

## Purpose

Handoff schemas define structured payload contracts for expert consultations and delivery transfers.

Review-oriented payloads should always expose both recommendation and confidence, and should prefer explicit 1-5 scoring when the output influences a go/no-go decision.

## Available Schemas

| Schema | File | Direction | Use Case |
|--------|------|-----------|----------|
| `work_handoff_v1` | `WORK_HANDOFF.schema.yaml` | Any → Any | Delivery task transfer |
| `expert_request_v1` | `EXPERT_REQUEST.schema.yaml` | Agent → Expert | Consultative request |
| `expert_response_v1` | `EXPERT_RESPONSE.schema.yaml` | Expert → Agent | Advisory response |
| `agile_info_exchange_v1` | `AGILE_INFO_EXCHANGE.schema.yaml` | Any ↔ agile-coach | Board/Wiki request-response exchange |
| `user_review_v1` | `USER_REVIEW.schema.yaml` | user-standard → ux-designer | UX review feedback with 1–5 ratings |

## user_review_v1

Used exclusively for the user-standard → ux-designer feedback loop.

Fields beyond `work_handoff_v1`:
- `criteria_ratings`: structured 1–5 scores per criterion (discoverability, clarity, navigation, error_recovery, mobile_familiarity)
- `composite_score`: arithmetic mean of all 5 scores
- `positive_findings`: what works naturally from user perspective
- `confusion_findings`: friction points with location, description, severity
- `blocking_issues`: show-stoppers preventing task completion
- `recommendation`: `proceed` / `revise` / `redesign`

See `.specifications/user-standard/handoffs.md` for full protocol and examples.

## agile_info_exchange_v1

Used for board/wiki information exchange with agile-coach as the governance gateway.

Required intent:
- Other agents or generic roles request board/wiki information or actions from agile-coach.
- Agile-coach responds with results, decisions, and produced artifact references.

Mandatory fields beyond `work_handoff_v1`:
- `direction`: `request_to_agile_coach` or `response_from_agile_coach`
- `requested_domain`: `board`, `wiki`, or `board_and_wiki`
- `expected_outputs`: explicit expected response payload
- `completion_criteria`: explicit definition for done exchange

## Recommended Trigger Pattern

For agent-triggered delivery flows that remain inside the repository, use `work_handoff_v1`
with these additional fields populated:
- `expected_outputs`
- `completion_criteria`
- `completed_items`
- `remaining_items`
- `definition_of_done`

Example use case:
- `agile-coach -> ux-designer` to create a stakeholder-ready PowerPoint deck from the canonical project stage description.
- `ux-designer -> agile-coach` to return the generated deck artifact so the Agile Coach can embed it into the wiki start page (`Home.md`).

## Quality Workflows

- `/quality` verifies schema presence and protocol coverage.
- `/quality-fix` can create missing contract baselines and normalize references.

## Skill Templates And Runtime Sync

- Authoring templates are located in `.github/skills/handoff/templates/`.
- Canonical contracts remain in this folder (`.github/handoffs/`).
- Runtime sync helper: `.github/skills/handoff/scripts/handoff-runtime-sync.sh`
	- creates `.digital-runtime/layers/<layer>/handoffs/`
	- copies canonical schema files
	- removes stale runtime schema files not present in canonical source
	- writes `handoff-index.tsv` with schema, file, and checksum

## Review Contract Guidance

- Review artifacts must not be prose-only when they are used for decisions.
- Include a recommendation field and confidence signal in every structured review output.
- Prefer 1-5 scoring for trust/readiness-sensitive reviews so downstream agents can compare results consistently.

## How to Create a New Handoff Schema

```bash
make scaffold-handoff HANDOFF_NAME=MY_HANDOFF HANDOFF_SCHEMA=my_handoff_v1
```

Rules:
- Use uppercase file names with underscores only.
- Keep the top-level `schema:` field aligned with the handoff protocol family.
- Include the shared required fields used by delivery and expert flows.
