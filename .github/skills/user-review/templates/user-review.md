---
schema: user_review_v1
review_id: "{{review_id}}"
from_role: user-standard
to_role: ux-designer
design_artifact: "{{design_artifact}}"
iteration: {{iteration}}
task_performed: "{{task_performed}}"
criteria_ratings:
  discoverability:
    score: {{score_discoverability}}
    justification: "{{justification_discoverability}}"
  clarity:
    score: {{score_clarity}}
    justification: "{{justification_clarity}}"
  navigation:
    score: {{score_navigation}}
    justification: "{{justification_navigation}}"
  error_recovery:
    score: {{score_error_recovery}}
    justification: "{{justification_error_recovery}}"
  mobile_familiarity:
    score: {{score_mobile_familiarity}}
    justification: "{{justification_mobile_familiarity}}"
composite_score: {{composite_score}}
positive_findings:
  - "{{positive_finding_1}}"
confusion_findings: []
blocking_issues: []
recommendation: "{{recommendation}}"
review_artifact: "{{review_artifact}}"
layer: digital-generic-team
---

# User Review: {{feature_name}} — Iteration r{{iteration}}

**Reviewed by:** user-standard  
**Date:** {{date}}  
**Design artifact:** `{{design_artifact}}`  
**Task:** {{task_performed}}

---

## First Impressions

<!-- What does the user see and think immediately on first screen load? 2-4 sentences max. -->

---

## Task Walkthrough

<!-- Simulate the user completing the stated task, step by step. -->

| Step | Action | Observation |
|------|--------|-------------|
| 1 | | |
| 2 | | |
| 3 | | |

---

## Interview Questionnaire

<!-- Template-based question catalog. Fill answers from the simulated user perspective. -->

| Question | Answer |
|----------|--------|
| What is the first thing you would tap and why? | |
| Which label or control was most confusing? | |
| Did you ever feel lost in the flow? Where? | |
| What error/help feedback was missing when you hesitated? | |
| What one change would most improve this screen? | |

---

## Positive Findings

<!-- What works naturally from the user's perspective. At least one item required. -->

- 

---

## Confusion Findings

<!-- What caused hesitation, friction, or confusion. Write as the user would describe it. -->
<!-- Leave the table empty if no confusion found. -->

| Location | What the user notices | Severity |
|----------|-----------------------|----------|
| | | minor / moderate / major |

---

## Blocking Issues

<!-- List anything that prevents task completion. Write NONE if the list is empty. -->

- NONE

---

## Ratings

| Criterion | Score (1–5) | Justification |
|-----------|-------------|---------------|
| Discoverability | {{score_discoverability}} | {{justification_discoverability}} |
| Clarity | {{score_clarity}} | {{justification_clarity}} |
| Navigation | {{score_navigation}} | {{justification_navigation}} |
| Error Recovery | {{score_error_recovery}} | {{justification_error_recovery}} |
| Mobile Familiarity | {{score_mobile_familiarity}} | {{justification_mobile_familiarity}} |
| **Composite** | **{{composite_score}}** | |

---

## Recommendation: {{recommendation | upper}}

<!-- One paragraph explaining the recommendation. -->
<!-- proceed  → what works, confirm readiness for specification -->
<!-- revise   → which specific pain points must be addressed in the next iteration -->
<!-- redesign → why the fundamental approach needs rethinking -->
