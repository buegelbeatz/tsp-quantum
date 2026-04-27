---
name: "Platform-architect / Umls"
description: "UML and PlantUML Documentation Standards"
layer: digital-generic-team
---
# UML and PlantUML Documentation Standards


This document specifies which diagram types to create, where to store them, and when each type is most valuable.

**Note**: This guide is technology- and project-agnostic. Adapt paths and examples to your project's architecture.

## Overview

All diagrams are stored in `./docs/uml/` and organized by type. Prefer PlantUML for version control and automation.

## Repository-Specific Selection Profile (WebAuthn)

Use this priority order for this repository:

1. **PlantUML sequence diagrams first** for authentication, registration, QR scanning, ticket polling, and degraded/wait flows.
2. **PlantUML activity diagrams** for simplified cross-flow overview and policy decision maps.
3. **Graphviz diagrams** only when a dedicated topology/dependency view adds unique value.
4. **Mermaid diagrams** only for lightweight communication views and quick onboarding summaries.

For authentication-related work, at least these sequence scenarios should be maintained:
- Admin bootstrap registration via QR scan.
- Admin login with mobile scan and desktop polling.
- Non-admin app login with audience context.
- Mobile direct-link policy rejection during bootstrap.
- Sidecar/provider wait-page polling while provider is unavailable.

Documentation safety requirements for public sharing:
- Use anonymized hosts and placeholders (for example `{DOMAIN_POSTFIX}`, `<app>`, `{ticket}`).
- Never include real invitation codes, real domains, secrets, or internal identifiers.

Container-first rendering policy (repository-specific):
- Reuse `.github/scripts/container_runtime.sh` for runtime detection.
- Reuse `.github/scripts/render_diagrams_container.sh` as the unified renderer.
- Prefer public, tool-specific images over local installations:
  - PlantUML: `docker.io/plantuml/plantuml:1.2026.1`
  - Mermaid CLI: `docker.io/minlag/mermaid-cli:latest` (optional auxiliary views)
- Keep rendering GitHub-compatible by avoiding machine-local dependencies where possible.

## Diagram Types and Criteria

### 1) Use Case Diagram

**Purpose**: Show actors, use cases (what users/systems do), and relationships from a user's perspective.

**When to create**:
- Initial project setup (required).
- When adding new user roles or major features.
- Documenting public API surface or core user workflows.

**When NOT needed**:
- Internal refactoring.
- Performance optimizations with no new capability.

**Storage**: `./docs/uml/use-cases.puml`

**What to include**:
- External actors (humans, external systems, APIs).
- Use cases: described as user goals (e.g., "authenticate user", "publish data", "query API").
- Relationships: includes, extends, associations.
- System boundary (what's inside vs. outside your system).

**Example**:
```
actor User
actor Admin
system [Your System]

User --> (Login)
User --> (View Dashboard)
Admin --> (Manage Users)
(Login) <-- (Validate Credentials)
```

---

### 2) Component Diagram

**Purpose**: Show logical components (services, modules, subsystems), their interfaces, and dependencies.

**When to create**:
- During architecture design or refactor.
- When introducing new internal services or layers.
- Documenting public service interfaces (APIs, protocols).

**When NOT needed**:
- Bug fixes or minor internal changes.

**Storage**: `./docs/uml/components.puml`

**What to include**:
- Components: major services/modules (e.g., backend API, database layer, UI layer).
- Interfaces: REST endpoints, message queues, gRPC, database connections.
- Dependencies: which components call which (and in what direction).
- External systems: third-party services, databases, caches.

**Example**:
```
component [Frontend]
component [API Gateway]
component [Business Logic]
component [Database]

Frontend --> API Gateway
API Gateway --> Business Logic
Business Logic --> Database
```

---

### 3) Sequence Diagram

**Purpose**: Show step-by-step message flow between components over time.

**When to create**:
- Multi-component workflows (critical user journeys, feature flows).
- Security-sensitive scenarios (authentication, authorization, data access).
- Complex error/recovery scenarios (timeouts, retries, fallbacks).
- Debugging suspected integration issues.

**When NOT needed**:
- Single-component internal logic (use activity diagrams instead).
- Trivial one-off requests.

**Storage**: `./docs/uml/sequences/`
  - One `.puml` file per workflow (e.g., `sequences/user-login.puml`, `sequences/data-sync.puml`).

**What to include**:
- Participants: actors, services, databases.
- Messages: method calls, API requests, responses.
- Lifelines: when a component is active.
- alt/opt: conditional branches,error paths.
- Timing: where delays, waits, or timeouts occur.

**Example**:
```
User -> API: POST /login
API -> Database: SELECT user
Database --> API: user data
API -> ExternalAuth: validate token
ExternalAuth --> API: token valid
API --> User: 200 OK, session token
```

---

### 4) Activity Diagram

**Purpose**: Show decision branches, loops, and state transitions within a single component or process.

**When to create**:
- Complex state machines (workflow states, lifecycle management).
- Conditional logic with multiple paths (mobile vs. desktop, happy path vs. error paths).
- Retry/backoff logic, polling patterns, queuing behavior.
- Decision trees with criteria (role-based access, feature flags, etc.).

**When NOT needed**:
- Simple linear flows (use sequence diagrams instead).
- Single boolean decisions.
- Rare edge cases not critical to understanding flow.

**Storage**: `./docs/uml/activities/`
  - One `.puml` file per activity (e.g., `activities/user-onboarding.puml`, `activities/data-validation.puml`).

**What to include**:
- Start/end nodes.
- Activities (tasks, operations).
- Decision diamonds (if/else, switch).
- Loops (while, for).
- Swimlanes (different responsible components/actors).
- Exceptions/error handling branches.

**Example**:
```
start
:User submits form;
:Validate input;
if (Valid?) then
  :Save to database;
  :Send confirmation;
else
  :Show error message;
  :Ask for retry;
endif
stop
```

---

### 5) Deployment Diagram

**Purpose**: Show runtime infrastructure: container/pod topology, network, persistent storage, and dependencies.

**When to create**:
- Kubernetes or similar container orchestration setup.
- Local development environment documentation.
- Multiple deployment variants (cloud, on-premises, hybrid, local).
- Infrastructure changes (autoscaling, storage, networking).

**When NOT needed**:
- Single stable deployment with no planned changes.

**Storage**: `./docs/uml/deployment/`
  - `deployment/production.puml` - Production environment topology.
  - `deployment/staging.puml` - Staging variant (if significantly different).
  - `deployment/local-dev.puml` - Local development setup.

**What to include**:
- Nodes: physical/virtual machines, containers, pods.
- Services: load balancers, ingress controllers, service meshes.
- Artifacts: container images, compiled binaries.
- Connections: network protocols, communication paths.
- Storage: volumes, persistent claims, databases.
- Secrets/ConfigMaps/environment configurations.

**Example**:
```
node Kubernetes {
  component Pod1 [API Container]
  component Pod2 [Worker Container]
  component DB [Postgres Pod]
  
  Pod1 -.-> DB
  Pod2 -.-> DB
}

node External {
  component Cache [Redis]
  component Queue [Message Broker]
}

Pod1 -.-> Cache
Pod1 -.-> Queue
```

---

### 6) C4 Model Diagram

**Purpose**: Hierarchical view of system architecture: from high-level system context down to code-level details.

**When to create**:
- Architecture documentation for stakeholders (executives, teams, onboarding).
- During architectural decisions (which services communicate, why).
- When multiple teams work on the same system.

**When NOT needed**:
- Bug fixes or routine maintenance.
- Stable architecture with no planned changes.

**Storage**: `./docs/uml/c4/`
  - `c4/system-context.puml` - System inside a box; external actors and systems around it.
  - `c4/container.puml` - Major containers (services, databases, caches) and their interactions.
  - `c4/component-[service].puml` - Detailed components within a specific service (layers, modules).
  - `c4/code-[domain].puml` - Code-level entities (classes, domain objects), only if complex.

**What to include**:

**System Context** (Level 1):
- The software system as a single box.
- External users and external systems it interacts with.
- High-level data flows (arrows).

**Container** (Level 2):
- Major containers: services (API backend, worker, UI), databases, caches, queues.
- Technology choices (Node.js API, React UI, Postgres database, etc.).
- Communication between containers (sync/async, protocols).

**Component** (Level 3, optional, per-service):
- Internal structure of a single container (e.g., API service).
- Layers (controllers, services, repositories).
- Internal interfaces between components.

**Code** (Level 4, rare):
- Class structures, domain objects, key methods.
- Only for highly complex domains (e.g., business rules engine, DSL parser).

**Example**:
```
System: [User Interface] - users interact with
[User Interface] --> [Backend API]
[Backend API] --> [Database]
[Backend API] --> [Cache]
[Backend API] <-- [External Payment Service] - integrates with
```
- Component: Router, Service, Middleware, Repository layers.
- Code: Class structures, method dependencies (only where architecture is not obvious).

---

## Multi-Diagram Methodology: Sequences & Activities

Since a system typically has **multiple workflows, user journeys, and decision trees**, Sequence and Activity diagrams require a structured two-phase approach to achieve completeness and coherence.

### Phase 1: Analysis & Inventory

**Objective**: Identify and document **all** relevant workflows and activities, not just the most obvious ones.

**For Sequence Diagrams**:
1. List all multi-component workflows in your system:
   - Primary user journeys (happy path).
   - Error/recovery scenarios (timeouts, retries, failures).
   - Admin/system maintenance workflows.
   - Background processes and async jobs.
2. For each workflow, capture:
   - Start/end points (who initiates, who responds).
   - All intermediate services/components involved.
   - All data exchanges (requests, responses, side effects).
3. Document naming conventions for diagram files (e.g., `login-flow.puml`, `payment-processing.puml`, `error-recovery.puml`).

**For Activity Diagrams**:
1. List all decision points and state machines in your system:
   - User role-based access control (admin, user, guest).
   - Feature flag or configuration-driven branching.
   - State transitions (order statuses, job lifecycles).
   - Validation and error-handling branches.
   - Retry loops, polling, backoff strategies.
2. For each activity, document:
   - Where the decision occurs (which component).
   - What conditions drive each branch.
   - What happens in each path (success, failure, timeouts).
3. Name files clearly (e.g., `user-registration.puml`, `order-fulfillment.puml`, `data-sync.puml`).

**Execution**:
- Create a checklist (spreadsheet, issue, wiki) of planned diagrams.
- Review with teammates: "What workflows or decision trees are we missing?"
- Iterate with code review feedback: "Are there error paths not yet diagrammed?"

### Phase 2: Documentation & Contextualization

**Objective**: Connect the individual workflows and activities to each other and to the broader architecture.

**For Sequence Diagrams**:
1. **Ordering**: Define which workflows call into which others:
   - Does "user-login" precede "data-sync"?
   - Does "error-recovery" apply to all workflows or a subset?
2. **Dependencies**: Identify shared participants and interfaces:
   - Which diagrams use the same API, database, or service?
   - Where might a change in one workflow affect another?
3. **Cross-references**: In each sequence diagram, include notes or linked documentation pointing to related workflows:
   - "On failure, see `sequences/error-recovery.puml`."
   - "This workflow uses the component contract defined in `components.puml`."

**For Activity Diagrams**:
1. **State continuity**: Document how decisions in one activity lead to states in another:
   - Does the user role assigned in "user-registration" determine branches in "data-access"?
   - Does job status from "background-job" affect behavior in "reporting"?
2. **Shared logic**: Identify common decision patterns and consolidate:
   - If the same "Is authenticated?" or "Has permission?" check appears in multiple activities, call it out.
   - Consider extracting a shared decision block or referencing from a single authoritative diagram.
3. **Timing and dependencies**: Show when workflows execute in relation to each other:
   - "First run `user-registration` (activity), then trigger the workflow in `sequences/data-sync.puml`."

**Documentation Artifact**:
- Create a **Workflow & Activity Index** (in README or dedicated doc) that lists all diagrams with a one-sentence purpose:
  ```
  ## Sequence Diagrams
  - sequences/login-flow.puml - User authentication via WebAuthn
  - sequences/data-sync.puml - Periodic sync of user profile (depends on login-flow)
  - sequences/error-recovery.puml - Retry logic for all failed requests (used by login-flow, data-sync)
  
  ## Activity Diagrams
  - activities/admin-startup.puml - Admin UI initialization (fed by login-flow)
  - activities/permission-check.puml - Role-based access decision (used by all workflows)
  ```

**Tips**:
- Use cross-references liberally: "See `permission-check.puml` for role-based branching."
- In comments or linked docs, note which sequence diagrams depend on which activities (e.g., "data-sync assumes the user is authenticated per `activities/permission-check.puml`").
- When a new workflow or activity is added, update the index and verify it doesn't duplicate existing diagrams.

---

## Update Triggers

Update diagrams when:
- ✅ Adding a new component, service, or module.
- ✅ Introducing a new endpoint, workflow, or user journey.
- ✅ Changing system architecture (services, data flow, dependencies).
- ✅ Modifying deployment topology or infrastructure.
- ✅ Major refactoring of internal structure.

Do NOT update for:
- ❌ Variable or function renames (unless changing public API).
- ❌ Bug fixes or internal optimization.
- ❌ Test-only changes.
- ❌ Documentation-only updates (comments, docstrings).

---

## File Organization

```
project-root/
  docs/
    uml/
      use-cases.puml                     # All user-centric workflows
      components.puml                    # All system components and interfaces
      activities/
        [feature-name].puml              # Decision trees, state machines
      sequences/
        [workflow-name].puml             # Multi-component message flows
      deployment/
        production.puml                  # Production topology
        staging.puml                     # Staging (if different)
        local-dev.puml                   # Local development setup
      c4/
        system-context.puml              # System overview
        container.puml                   # Major containers
        component-[service].puml         # Service internals
```

---

## Maintenance Guidelines

1. **Review after major PRs**: Check if architecture or workflows changed.
2. **Versioning**: Commit diagrams with changes; git history tracks versions.
3. **Accessibility**: Include alt-text descriptions when linking from README/docs.
4. **Tool**: Use PlantUML (online editor or CLI) for rendering; avoid hand-drawn images.
5. **Sync documentation**: When diagrams change, update related README/architecture docs.

---

## Cross-Reference in Documentation

Link diagrams from relevant documentation sections. Examples:

- **Architecture README / Design Docs**:
  - Link to `use-cases.puml`, `components.puml`, `c4/system-context.puml`, `c4/container.puml`.

- **Deployment / Operations Guides**:
  - Link to `deployment/production.puml`, `deployment/staging.puml`, `deployment/local-dev.puml`.

- **Security / Feature Documentation**:
  - Link to relevant `sequences/*.puml` (e.g., authentication flow, data access flow).
  - Link to relevant `activities/*.puml` (e.g., permission checks, validation logic).

- **API / Integration Documentation**:
  - Link to `components.puml` (interfaces and contracts).
  - Link to `c4/container.puml` (which systems integrate and how).

- **Component-Specific README** (e.g., `backend/README.md`, `services/auth/README.md`):
  - Link to `c4/component-[service].puml`.
  - Link to relevant `sequences/*.puml` (user journeys affecting this component).

---

## Tips for Writing Good Diagrams

### Use Case Diagrams
- Use clear, action-verb naming (e.g., "Authenticate User", not "Auth System").
- Group related use cases; use `<<include>>` and `<<extend>>` sparingly.
- Keep to one or two levels of detail; avoid over-splitting.

### Component Diagrams
- Name components by responsibility (e.g., "API Gateway", "User Service", "Data Repository").
- Use consistent interface naming (REST APIs, message topics, DB connections).
- Show **interfaces** (contracts), not just names.

### Sequence Diagrams
- Use actor/system names consistently with other diagrams.
- Label messages with method names and parameters.
- Use `alt` blocks for conditional branches; label conditions clearly.
- Include timing markers (`par`, `loop`, `opt`) for complex flows.

### Activity Diagrams
- One swimlane per responsible component/actor.
- Decision nodes should have clear labels (e.g., "User authenticated?", "Valid email?").
- Use `note` blocks to explain complex logic.

### Deployment Diagrams
- Use node types consistently (pod, container, VM, service).
- Label connection types (HTTP, gRPC, TCP, filesystem mount).
- Group logically (e.g., separate zones for data, app, cache layers).

### C4 Diagrams
- **Context**: One box (the system), minimal labeling.
- **Container**: 5-10 boxes max; show all communication flows.
- **Component**: 10-15 boxes max per service; focus on layers or key modules.
- **Code**: Rare; only if architecture is not obvious from L3.
