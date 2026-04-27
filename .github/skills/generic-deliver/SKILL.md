---
name: generic-deliver
description: Reusable prefix and postfix workflow for delivery agents.
layer: digital-generic-team
---

# Skill: Generic Delivery

This skill provides deterministic delivery lifecycle wrappers for role-specific delivery agents.

## Prefix

- Discover assigned board work for a role.
- Set issue state to in-progress.
- Create and checkout delivery branch.
- Run language-expert bridge hook (deliver mode) and attach conventions/risk/confidence guidance.

## Postfix

- Stage/commit/push code changes.
- Generate and publish delivery review.
- Create or update pull request and publish review comment.
- Run language-expert bridge hook (review mode) before final reviewer handoff.
- Emit explicit human-approval gate reminder.

## Delivery Add-ons

- Container-oriented tickets may invoke `container-publish` to add or update governed GHCR publication in the target repository.
- Documentation for published images should be synchronized as a GHCR docs artifact, not kept only in source control.

## Delivery Evidence Tracking

The postfix workflow now includes automated delivery evidence generation to support stakeholder visibility and artifact recovery:

- **Delivery Evidence Artifacts**: Automatically generated records tracking handoff status, approval evidence, and quality metrics
- **Review Checkpoints**: Timestamped snapshots of all delivered tasks for human review gates
- **Artifact Recovery**: Verification that planning and handoff artifacts remain available after cleanup/restarts
- **Approval Recording**: Structured capture of human reviewer sign-off with evidence links

### Entry Point

```bash
scripts/delivery-evidence-integration.sh <stage> <task_id> [action]
```

Actions:
- `checkpoint`: Generate review checkpoint and recovery report
- `verify-recovery`: Check artifact availability for specified tasks

## Scripts

- `scripts/delivery-prefix.sh`
- `scripts/delivery-postfix.sh`
- `scripts/delivery-language-bridge.sh`
- `scripts/delivery_evidence_tracker.py` — Delivery evidence tracking module
- `scripts/delivery-evidence-integration.sh` — Integration wrapper
- `scripts/test_delivery_evidence_tracker.py` — Unit tests for evidence tracker

## Dependencies

- `../git`
- `../github`
- `../shared/pr-delivery`
- `../artifacts`
- `../container-publish`
- Python 3.8+
- PyYAML
