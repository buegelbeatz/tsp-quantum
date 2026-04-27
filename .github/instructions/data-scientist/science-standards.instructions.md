---
name: "Data-scientist / Data-science-standardss"
description: "Data Scientist Standards"
layer: digital-generic-team
---
# Data Scientist Standards


## Scope Boundaries

- This Layer 1 scope covers data-science enablement only.
- Bioinformatics-specific role design is explicitly deferred to a dedicated future agent.
- All generated guidance must stay public-safe and must not reference internal repositories.

## Data Workflow

- Define data sources, assumptions, and quality constraints.
- Keep transformations reproducible and versioned.
- Separate exploratory notebooks from reusable implementation logic.

## Required Domains

- Jupyter notebook workflows and reproducibility guardrails.
- Statistics and stochastics foundations for experiment design.
- Machine-learning baseline and evaluation patterns.
- Scientific-paper intake and evidence extraction.

## Statistical Rigor

- State hypotheses and evaluation metrics before analysis.
- Report uncertainty and confidence assumptions explicitly.
- Avoid unsupported causal claims from correlational evidence.

## Delivery

- Provide decision-ready summaries in plain language.
- Expose model and feature limitations.
- Include reproducibility instructions for reruns.
- Keep runnable examples and test outputs under `.tests/` conventions.
