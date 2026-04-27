---
name: "Platform-architect / Architectures"
description: "Enterprise Architecture Planning Instructions"
layer: digital-generic-team
---
# Enterprise Architecture Planning Instructions


## Purpose

This document defines how to approach enterprise architecture planning.
It ensures that architectural decisions are only made when sufficient information is available and that all relevant constraints, requirements, and risks are properly evaluated.

---

## 1. Architecture Planning Readiness Criteria

Architecture planning MUST NOT start unless the following conditions are met.

### 1.1 Business Context Defined

* Clear business objective
* Defined use cases
* Identified stakeholders
* Expected business outcomes (KPIs)

### 1.2 Functional Requirements Available

* Core features are described
* User interactions are understood
* Edge cases are identified

### 1.3 Non-Functional Requirements (NFRs) Defined

* Performance (latency, throughput)
* Scalability expectations
* Availability (SLA/SLO)
* Security requirements
* Compliance constraints (e.g., GDPR, HIPAA)

### 1.4 Data Characteristics Known

* Data volume and growth expectations
* Data sensitivity/classification
* Data lifecycle (retention, archival, deletion)
* Integration points (sources/targets)

### 1.5 Technical Constraints Identified

* Existing systems and dependencies
* Required technologies or restrictions
* Infrastructure constraints (cloud, on-prem, hybrid)

### 1.6 Operational Context Defined

* Deployment model
* Monitoring and observability requirements
* Incident response expectations
* Maintenance and support model

---

## 2. Mandatory Clarification Questions

If any of the following is unclear, architecture planning MUST pause and request clarification.

### Business & Scope

* What problem are we solving?
* What is explicitly out of scope?
* What is the expected time-to-market?

### Load & Scale

* Expected number of users?
* Peak vs average load?
* Growth expectations?

### Data

* What data is processed?
* What are the consistency requirements?
* Is eventual consistency acceptable?

### Integration

* Which external/internal systems are involved?
* What are the interface contracts?

### Security & Compliance

* What are the authentication/authorization requirements?
* Are there regulatory constraints?

### Failure Handling

* What happens on failure?
* Is graceful degradation required?

---

## 3. Architecture Decision Principles

All architecture decisions MUST follow these principles:

### 3.1 Fit for Purpose

Do not over-engineer. Choose the simplest solution that satisfies requirements.

### 3.2 Explicit Trade-offs

Every decision must document:

* What is optimized
* What is sacrificed

### 3.3 Scalability Awareness

Design for expected scale, not hypothetical extremes.

### 3.4 Evolvability

Architecture must support change with minimal impact.

### 3.5 Observability First

Logging, metrics, and tracing are not optional.

### 3.6 Security by Design

Security must be integrated from the beginning, not added later.

---

## 4. Architecture Patterns (Selection Guide)

Choose architecture patterns based on context:

### Layered Architecture

* Use for standard business applications
* Clear separation of concerns

### Hexagonal (Ports & Adapters)

* Use when domain logic must be isolated
* Enables testability and flexibility

### Event-Driven Architecture

* Use for decoupled systems and high scalability
* Suitable for asynchronous workflows

### Microservices

* Use only when:

  * Clear domain boundaries exist
  * Independent scaling is required
  * Operational maturity is high

### Monolith (Modular)

* Preferred default
* Use unless strong reasons for distribution exist

---

## 5. Anti-Patterns to Avoid

* Starting architecture without requirements
* Choosing technology before defining the problem
* Over-engineering for unknown scale
* Ignoring operational complexity
* Tight coupling between services
* Lack of clear ownership

---

## 6. Architecture Deliverables

Every architecture must produce:

* System context diagram
* Component diagram
* Data flow description
* Key decisions (ADR - Architecture Decision Records)
* Risk assessment
* Deployment model

---

## 7. Decision Process (Recommended Workflow)

1. Validate readiness criteria
2. Clarify missing information
3. Identify constraints
4. Select candidate architecture patterns
5. Evaluate trade-offs
6. Document decisions (ADR)
7. Validate with stakeholders

---

## 8. When Architecture Planning is NOT Possible

Architecture planning must be postponed if:

* Requirements are vague or constantly changing
* No clear business goal exists
* Key constraints are unknown
* Stakeholders are not aligned
* Data characteristics are undefined

---

## 9. Continuous Validation

Architecture is not static.

* Re-evaluate decisions regularly
* Monitor real system behavior
* Adjust based on feedback and metrics

---

## 10. Guiding Principle

> "Architecture is a decision-making process under uncertainty.
> The goal is not perfection, but informed, transparent, and adaptable decisions."
