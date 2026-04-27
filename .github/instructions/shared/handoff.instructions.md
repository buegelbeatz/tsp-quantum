---
name: "Shared / Handoffs"
description: "Handoff Rules"
applyTo: "**"
layer: digital-generic-team
---
# Handoff Rules

All agent-to-agent communication must follow standardized handoff formats.

## Mandatory Rules

- Use `work_handoff_v1` for delivery agent handoffs.
- Use `expert_request_v1` for expert consultations.
- Use `expert_response_v1` for expert responses.
- Use `agile_info_exchange_v1` for any board/wiki request-response exchange involving `agile-coach`.
- Write all handoff content in English (keys, summaries, assumptions, open questions, and artifacts), unless a policy explicitly states otherwise.
- Do not use free-form text as a standalone handoff.
- Assumptions must be explicitly listed in `assumptions`.
- Open questions must be listed in `open_questions`.
- Relevant artifacts must be listed in `artifacts`.
- If required fields are missing, mark the handoff as incomplete.
- Expert agents must only provide analysis and recommendations.
- Expert agents must not modify files or continue workflows.

## Classification Rule

If unsure whether something is factual or inferred:
- factual → `current_state` or `context`
- inferred → `assumptions`

## Goal

Every handoff must be actionable without requiring clarification.

## Agent Trigger Contract

Agent-to-agent triggering MUST be represented as a handoff contract, not as implicit free-text instructions.

- If agent A triggers agent B, agent A MUST provide a handoff payload that states both the requested work and the expected return payload.
- Trigger requests MUST use one of the approved schemas (`work_handoff_v1` or `expert_request_v1`) and MUST NOT use ad-hoc formats.
- The receiving agent MUST answer with the matching response schema (`work_handoff_v1` continuation or `expert_response_v1`).
- Trigger handoffs MUST explicitly include:
	- requester (who asks)
	- receiver (who is asked)
	- intent (why the trigger exists)
	- expected_outputs (what must be returned)
	- completion_criteria (how success is evaluated)
	- artifacts (where outputs are persisted)
	- open_questions (what is still unclear)
- If `expected_outputs` or `completion_criteria` are missing, the trigger handoff is incomplete and MUST be rejected until completed.

## Agile Coach Gateway Contract

- Board (`refs/board/*`) and wiki (`docs/wiki/`) interactions requested by non-agile roles MUST go through `agile-coach` via `agile_info_exchange_v1`.
- The flow MUST support both directions:
	- request to agile-coach for board/wiki information or actions
	- response from agile-coach with decisions, evidence, and artifact links
- Free-form chat requests for board/wiki operations are not sufficient once agent-to-agent work is triggered.

## Review Output Rule

- Any handoff or artifact whose primary purpose is review, evaluation, or feedback MUST include an explicit recommendation.
- Review outputs MUST include a confidence indication.
- If the review is decision-relevant, prefer a numeric confidence or score on a 1-5 scale.
- If multiple dimensions are assessed, each dimension SHOULD be scored separately with short evidence-based justification.

## Code Snippets in Artifacts

`expert_response_v1` `artifacts` entries SHOULD include runnable code snippets when the request involves a technical domain (AI/ML, APIs, infrastructure).

- Use fenced Markdown code blocks inside the `artifact` item's `content` field.
- Reference environment variables instead of hardcoded values (e.g., `os.getenv("HUGGINGFACE_TOKEN")`).
- Label each snippet with its language and purpose.
- Keep snippets minimal and executable — not tutorial-length prose.

Example artifact entry:

```yaml
artifacts:
	- type: code_snippet
		language: python
		label: "HuggingFace model discovery"
		content: |
			import os
			from huggingface_hub import HfApi
			api = HfApi(token=os.getenv("HUGGINGFACE_TOKEN"))
			models = api.list_models(search="bert", task="text-classification", limit=5)
```