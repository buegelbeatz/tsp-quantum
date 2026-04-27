---
layer: digital-generic-team
---
# Refactor Review

## Decision
- recommendation: {{RECOMMENDATION}}
- confidence_score: {{CONFIDENCE_SCORE}}

## Review Scores
| Dimension | Score (1-5) | Evidence |
|-----------|-------------|----------|
| Maintainability | {{SCORE_MAINTAINABILITY}} | {{EVIDENCE_MAINTAINABILITY}} |
| Complexity reduction | {{SCORE_COMPLEXITY}} | {{EVIDENCE_COMPLEXITY}} |
| Safety | {{SCORE_SAFETY}} | {{EVIDENCE_SAFETY}} |
| Documentation readiness | {{SCORE_DOCUMENTATION}} | {{EVIDENCE_DOCUMENTATION}} |

## Tracked files
- Relevant files reviewed in detail:
  - {{RELEVANT_FILE_LIST}}
- Remaining tracked files reviewed and summarized: {{REMAINING_TRACKED_COUNT}}

## Findings
- {{FINDINGS_BY_SEVERITY}}

## Refactor candidates
- Threshold: > {{MAX_LINES}} lines
- Candidates:
  - {{OVER_THRESHOLD_LIST}}
- Rationale:
  - {{REFACTOR_RATIONALE}}

## Security review
- Confirmed risks:
  - {{CONFIRMED_SECURITY_RISKS}}
- Missing controls:
  - {{MISSING_SECURITY_CONTROLS}}

## Documentation review
- Missing or weak inline documentation:
  - {{DOCUMENTATION_GAPS}}
