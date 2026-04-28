---
layer: digital-generic-team
---
# Pull Request Review Report

- pr_title: {{pr_title}}
- branch: {{branch_name}}
- scope: {{scope}}
- recommendation: {{recommendation}}
- confidence_score: {{confidence_score}}

## Summary
{{summary}}

## Review Scores

| Dimension | Score (1-5) | Evidence |
|-----------|-------------|----------|
| Correctness | {{score_correctness}} | {{evidence_correctness}} |
| Risk | {{score_risk}} | {{evidence_risk}} |
| Test confidence | {{score_test_confidence}} | {{evidence_test_confidence}} |
| Merge readiness | {{score_merge_readiness}} | {{evidence_merge_readiness}} |

## Checks
- tests: {{tests_status}}
- lint: {{lint_status}}
- typing: {{typing_status}}

## Risks
{{risks}}
