---
layer: digital-generic-team
---
# agents

## Purpose

**Agents** are autonomous software entities with defined roles, behavioral contracts, and delegation surfaces. They represent specialized capabilities that can operate independently and interact with users, skills, and other agents.

## What Is an Agent?

An agent is:
- **Autonomous:** Makes decisions within its role scope; doesn't require explicit instructions for every action.
- **Specialized:** Deep expertise in one domain (Kubernetes, security, quality, etc.) or broad generalist capability (delivery, orchestration).
- **Contractual:** Clear input/output interfaces; transparent about what it can and cannot do.
- **Delegatable:** Other agents and prompts can request its expertise via well-defined handoff protocols.

## Agent Categories

### Delivery & Orchestration

**generic-deliver** — Converts prompts, instructions, and skill invocations into actionable deployments.
- Input: Work items, task lists, user intent.
- Output: Code changes, file artifacts, test results.
- Scope: Cross-layer execution; coordinates skill chains.
- Handoff: `work_handoff_v1` (receives tasks, returns completion status).

**shared/local-command-orchestration** — Manages execution of shell commands and scripts in local environment.
- Input: Command registry, target system details.
- Output: Execution logs, error handling, resource cleanup.
- Scope: Shell script orchestration; local system calls.
- Handoff: CLI arguments and environment setup.

**shared/task-orchestration** — Coordinates multi-step workflows and dependency chains.
- Input: Task DAG (directed acyclic graph), success/failure criteria.
- Output: Step completion markers, aggregated results.
- Scope: Workflow scheduling; parallel execution where safe.

### Expert Consultants

**ai-expert** — Large language models, prompt design, fine-tuning strategies.
- Input: ML questions, model selection criteria, dataset specs.
- Output: Recommendations, hyperparameter guidance, evaluation metrics.
- Scope: Advisory; does not modify code directly.
- Handoff: `expert_request_v1` (consultative, not executory).

**security-expert** — Threat modeling, vulnerability assessment, defense patterns.
- Input: Code review, architecture diagrams, threat scenarios.
- Output: Risk analysis, mitigation strategies, best practices.
- Scope: Advisory; escalation to human security team for critical findings.

**kubernetes-expert** — Cluster design, deployment patterns, troubleshooting.
- Input: K8S architecture questions, resource specs, failure modes.
- Output: Configuration examples, scaling guidance, operational runbooks.
- Scope: Advisory; handles K3S-specific variants (IoT, edge scenarios).

**quality-expert** — Code standards, testing strategies, refactoring guidance.
- Input: Quality findings (from `/quality` reports), escalation items.
- Output: Remediation examples, refactoring strategies, coverage analysis.
- Scope: Understanding; recommendations for manual work (escalations).

### Domain Specialists

**fullstack-engineer** — End-to-end application architecture.
- Input: Feature requirements, technology stack, performance targets.
- Output: Component design, data flow diagrams, implementation roadmap.

**agile-coach** — Sprint planning, team coordination, delivery cadence.
- Input: Backlog items, team capacity, release goals.
- Output: Sprint plans, risk identification, process improvements.

**container-expert** — Docker, Kubernetes, container orchestration.
- Input: Containerization needs, deployment targets.
- Output: Dockerfile templates, K8S manifests, registry strategies.

**ux-designer** — User flow evaluation, UX scribble generation, user review cycle orchestration.
- Input: Form MDs in `10-data/`, UX review requests, user_review_v1 feedback.
- Output: SVG scribbles, developer specifications, bugs/features from user reviews, wiki docs.
- Handoff: Sends `work_handoff_v1` to `user-standard`; receives `user_review_v1` back.

**user-standard** — Non-technical user simulation for UX validation.
- Input: `work_handoff_v1` from `ux-designer` with SVG scribble path and task description.
- Output: `user_review_v1` feedback with 1–5 ratings and `user-review-*.md` artifact.
- Handoff: `user_review_v1` (new schema — see `.github/handoffs/USER_REVIEW.schema.yaml`).
- Note: Never self-activating; always initiated by `ux-designer`.

## Agent Metadata (AGENT.md)

Every agent **must** have an `{name}.agent.md` file documenting:

```yaml
---
name: "Agent Name"
role: "Role / Expertise"
description: "One-line summary of this agent's primary capability."
layer: {layer-name}
scope: "Global | Layer | Project"
delegation: "Autonomous | Expert-only | Handoff-required"
---

# Agent: {Name}

## Mission
Multi-paragraph explanation of the agent's purpose and scope.
Who uses it and when (primary use cases)?

## Role Boundaries
What this agent **does**:
- Specific capability 1
- Specific capability 2

What this agent **does NOT**:
- Out-of-scope item 1
- Why not (security, expertise, etc.)

## Handoff Protocol
How other agents or prompts invoke this agent.

**Request Format:** `expert_request_v1` for consultants; `work_handoff_v1` for delivery.

**Example Request:**
```yaml
type: expert_request_v1
expert: kubernetes-expert
context: |
  We need to scale our K3S cluster to 50 nodes.
  Current bottleneck: etcd performance under load.
assumptions:
  - Single-master K3S cluster on Raspberry Pi 4s
  - Using flannel CNI
open_questions:
  - What happens to existing workloads during etcd migration?
```

**Example Response:**
```yaml
type: expert_response_v1
agent: kubernetes-expert
analysis: |
  etcd performance on Pi 4s maxes at ~20 nodes due to disk I/O.
  Recommendation: Move to external etcd cluster (managed service or dedicated VMs).
recommendations:
  - Use Patroni for HA external etcd
  - Pin etcd to compute nodes with NVMe storage
artifacts:
  - etcd-migration-runbook.md
  - k3s-cluster-config.yaml
```

## Error Handling
What happens when this agent encounters:
- Missing inputs
- Out-of-scope questions
- Internal errors (timeouts, API failures)

**Strategy:** Fail fast with clear error message and suggested next step.

## Dependencies

### Other Agents
- Does this agent delegate to other agents? (e.g., delivery → quality-expert for recommendations).

### Skills Used
- List of skills this agent invokes (e.g., `skill: prompt-quality`, `skill: shared/shell`).

### External Tools
- Required tools/services (e.g., kubectl, docker, terraform).

## Best Practices

### Interaction Patterns
1. **Consultant agents:** Analyze and recommend; do NOT modify code.
2. **Delivery agents:** Execute work; report results via handoff.
3. **Orchestration agents:** Coordinate other agents and skills.

### Failure Modes
- Always explain what went wrong and why.
- Suggest next steps (retry, escalate, clarify input).
- Log sufficient context for debugging.

### Cross-Agent Communication
- Use formal handoffs (expert_request_v1, work_handoff_v1).
- Avoid direct method calls; serialize via JSON/YAML.
- Document assumptions explicitly.

## Testing

### Unit Tests
- Mock external dependencies.
- Test decision logic (routing, prioritization).
- Test error handling paths.

### Integration Tests
- Multi-agent workflows (e.g., delivery → quality-expert → deliver).
- Actual skill invocations in sandbox.
- Handoff deserialization and validation.

### Coverage Target
- Minimum 80% for all agent logic.
- 100% for error paths (security-critical).

## Examples

### Consultant Agent (kubernetes-expert)

**Purpose:** Provide Kubernetes/K3S expertise and operational guidance.

**Mission:**
This agent analyzes Kubernetes architectures, cluster designs, and operational challenges. It provides recommendations for scaling, security, troubleshooting, and deployment patterns. It does NOT directly modify cluster state; it recommends actions that human operators execute.

**Scope:**
- Kubernetes (all versions) and K3S (edge/IoT variants).
- Cluster design, networking, storage, security policies.
- Troubleshooting performance, reliability, cost.
- Does NOT: Operate clusters, deploy production workloads without approval.

**Handoff:**
Accepts `expert_request_v1` queries about cluster architecture and operational challenges. Returns `expert_response_v1` with analysis and recommendations.

### Delivery Agent (generic-deliver)

**Purpose:** Execute work items end-to-end.

**Mission:**
This agent converts tasks (prompts, skill invocations, code changes) into fully tested, documented, committed artifacts. It orchestrates skill chains, validates quality, and reports completion status.

**Scope:**
- Accept `work_handoff_v1` with task specifications.
- Invoke skills in dependency order.
- Run tests; report coverage.
- Commit with conventional messages.
- Return `work_handoff_v1` with completion status and artifacts.

**Dependencies:**
- Skills: `prompt-quality`, `prompt-quality-fix`, `shared/shell`, others as needed.
- External: Git, Python, Docker, test frameworks.

### Specialized Agent (agile-coach)

**Purpose:** Plan sprints and coordinate team delivery.

**Mission:**
This agent analyzes project state, capacity, and backlog to produce sprint plans. It identifies risks, suggests process improvements, and tracks burndown.

**Scope:**
- Sprint planning (4–6 person teams, 1-week sprints).
- Capacity planning and risk identification.
- Process retrospectives.
- Does NOT: Make product decisions or set organizational strategy.

## Quality Audits

### What `/quality` Checks for Agents
- Frontmatter metadata completeness (name, role, description, layer, scope).
- File naming consistency (`{name}.agent.md`, not `agent.md` or `{name}.md`).
- Contract sections present (Mission, Role Boundaries, Handoff Protocol, Dependencies, Examples).
- No hardcoded secrets, credentials, or internal paths.
- References to skills and other agents are valid.

### What `/quality-fix` Does for Agents
**Autofix:**
- Adds missing frontmatter fields.
- Normalizes file naming.
- Ensuresuires required contract sections exist.

**Escalation (manual):**
- Incomplete role boundaries (unclear scope).
- Missing handoff protocol documentation.
- Conflicting agent responsibilities (overlap with other agents).

## How to Create a New Agent

### 1. Define the Role
- **Mission:** What is this agent's primary expertise?
- **Scope:** Autonomous, expert-only, or handoff-required?
- **Users:** Who will invoke this agent and when?

### 2. Write the Metadata File
Start with:

```bash
make scaffold-agent AGENT_NAME=<name> AGENT_PURPOSE="use when ..."
```

Then refine `agents/{name}.agent.md` with frontmatter and sections.

### 3. Document Role Boundaries
- What it **does** (3–5 key capabilities).
- What it **doesn't** (why, or references to other agents).

### 4. Design the Handoff Protocol
- Format: `expert_request_v1` or `work_handoff_v1`?
- Required fields in request and response.
- Example request and response (YAML).

### 5. List Dependencies
- Other agents this agent depends on or coordinates with.
- Skills this agent invokes.
- External tools and versions.

### 6. Add Examples
- Real-world scenario showing typical request and response.
- Show error handling (what happens if inputs are invalid).

### 7. Define Error Handling
- Failure scenarios: missing inputs, out-of-scope, timeouts.
- Recovery strategy for each.

### 8. Validate
```bash
make quality        # Checks metadata, references, contract completeness
make test           # If agent tests exist
```

## References
- [Handoff Rules](../instructions/shared/handoff.instructions.md) — Formal handoff formats.
- [Governance: Layer Override](../instructions/governance-layer/layer-override.instructions.md) — Agent inheritance rules.
- [Example Agent: Generic Deliver](./roles/generic-deliver.agent.md) — Delivery agent implementation.
- [Example Agent: Kubernetes Expert](./kubernetes-expert.agent.md) — Consultant agent implementation.
- [Skill Contracts](../skills/README.md) — How agents invoke skills.

## Quality Workflows

- `/quality` verifies agent contract completeness and mapping hygiene.
- `/quality-fix` remediates deterministic agent metadata issues.
