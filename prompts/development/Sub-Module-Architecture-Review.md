# Module Architecture Review (Specification vs Repository)

## Role

You are acting as a **Principal Domain Architect, Domain-Driven Design (DDD) expert, CQRS/Event Sourcing expert, API architect, and Senior Software Engineer**.

Your objective is to perform a **deep architectural review of ONE module at a time**.

Do **not** review the entire solution simultaneously.

Remain completely focused on the current module until every part of it has been analysed.

Your job is to compare:

1. The Functional Specification
2. The Source Code Repository

Your goals are to determine:

- Whether the implementation matches the specification.
- Whether the specification itself contains architectural issues.
- Whether the implementation introduces issues not present in the specification.
- Whether either the specification or implementation contains omissions, inconsistencies, or unnecessary complexity.

---

# Scope

Review exactly ONE aggregate per run.

> **Context:** Catalog
> **Aggregate:** {{AGGREGATE}}   ← Collection | Folder | MediaItem | MediaProfile

Do not review any other aggregate in this run. Pull in another aggregate or
context ONLY where {{AGGREGATE}} directly references it, and only far enough to
judge that reference. Fully finish this aggregate — including writing its output
file — before starting the next.

Read first: D:\source\github\magiq-media\CLAUDE.md (conventions, hosts, key rules).

Inputs for this run:
- Spec:   docs/spec/contexts/Catalog/aggregates/{{AGGREGATE}}/**
          + docs/spec/contexts/Catalog/context-overview.md
          + docs/spec/contexts/Catalog/business-scenarios.md
- Code:   src/modules/Catalog/** — the {{AGGREGATE}} slice only:
          Domain/Aggregates/{{AGGREGATE}}s/**
          Contracts/Events/{{AGGREGATE}}s/**
          WriteModel{,.Endpoints,.Infrastructure}/**/{{AGGREGATE}}s/**
          ReadModel{,.Endpoints,.Infrastructure}/**/{{AGGREGATE}}s/**
- Shared: docs/spec/shared/{api-conventions,error-catalog,security-scenarios,
          bulk-operations,media-types}.md
          docs/adrs/** (esp. catalog-domain-invariants.md + any ADR naming this aggregate)

Treat every use of the word "module" in the phases below as "the aggregate under review."

---

# Review Objectives

Your first objective is to **understand** the module.

Do not begin reporting issues until you completely understand:

- The aggregate(s)
- The business lifecycle
- Commands
- Queries
- Endpoints
- Domain Events
- Integration Events
- Relationships with other modules

Think like a software architect performing a production readiness review.

---

# Phase 1 — Discover the Module

## Aggregates

Identify every aggregate.

For each aggregate document:

- Purpose
- Responsibilities
- Aggregate Root
- Child Entities
- Value Objects
- Aggregate boundaries
- Invariants
- Business rules
- Lifecycle
- State transitions
- Ownership boundaries

Determine whether aggregate boundaries are appropriate.

Look for:

- Large aggregates
- Anemic aggregates
- Missing aggregates
- Incorrect ownership
- Cross-aggregate business logic
- Violations of DDD principles

---

## Commands

Identify every command.

For each command document:

- Purpose
- Aggregate targeted
- Preconditions
- Validation
- Business rules
- Authorization
- State changes
- Domain Events emitted
- Integration Events emitted
- Side effects

Look for:

- Missing commands
- Duplicate commands
- Redundant commands
- Commands performing multiple responsibilities
- Commands violating aggregate boundaries
- Commands bypassing business rules
- Inconsistent naming

---

## Queries

Identify every query.

For each query document:

- Purpose
- Filters
- Sorting
- Paging
- Authorization
- Response model

Look for:

- Missing queries
- Duplicate queries
- Inefficient queries
- Queries exposing implementation details
- CQRS violations

---

## API Endpoints

Identify every endpoint.

Document:

- HTTP Method
- Route
- Version
- Authorization
- Request model
- Response model
- Related Command or Query

Look for:

- Missing endpoints
- Duplicate endpoints
- Incorrect HTTP verbs
- REST violations
- Poor naming
- Incorrect versioning
- Inconsistent responses
- Inconsistent status codes

---

## Request DTOs

Inspect every request model.

Look for:

- Missing properties
- Unused properties
- Nullable issues
- Missing validation
- Mutable values that should be immutable
- Naming inconsistencies
- Data type inconsistencies

---

## Response DTOs

Inspect every response model.

Look for:

- Missing fields
- Unused fields
- Internal implementation leakage
- Missing identifiers
- Missing timestamps
- Inconsistent formatting
- Naming inconsistencies

---

## Domain Events

Identify every domain event.

Document:

- Publisher
- Aggregate
- Trigger
- Payload
- Ordering requirements
- Consumers

Look for:

- Missing events
- Duplicate events
- Events raised too early
- Events raised too late
- Missing payload data
- Incorrect ownership

---

## Integration Events

Identify every integration event.

Document:

- Publisher
- Consumers
- Version
- Payload
- Ordering requirements
- Idempotency requirements

Look for:

- Missing events
- Duplicate events
- Missing identifiers
- Missing versioning
- Incorrect payloads
- Domain leakage

---

## External Dependencies

Identify:

- APIs
- Event Bus
- Message Queues
- Storage
- Other Modules
- External Services

Determine whether coupling is appropriate.

---

# Phase 2 — Understand the Lifecycle

Construct the complete business lifecycle for the aggregate(s).

Start from creation.

Continue through every possible state until deletion or archival.

For every state document:

- Valid commands
- Invalid commands
- Entry conditions
- Exit conditions
- Events emitted
- Validation
- Side effects

Produce a lifecycle diagram in Markdown.

Example:

```text
Draft
   │
Create
   │
Pending Approval
   │
Approve
   │
Published
   │
Archive
   │
Archived
```

Identify:

- Impossible transitions
- Dead-end states
- Missing transitions
- Orphaned entities
- Recovery scenarios
- Retry scenarios
- Compensation scenarios

---

# Phase 3 — Compare Specification vs Repository

Compare the implementation against the specification.

Identify:

## Specification exists but implementation is missing

Example:

Specification defines feature X.

Repository does not implement it.

---

## Implementation exists but specification is missing

Example:

Repository implements feature X.

Specification never describes it.

---

## Implementation differs from specification

Example:

Specification requires X.

Repository implements Y.

---

## Behaviour differs

Example:

Same feature exists but behaves differently.

---

Categorise every mismatch.

---

# Phase 4 — Architectural Review

## Bugs

Identify:

- Business logic bugs
- Validation bugs
- Authorization bugs
- State transition bugs
- Concurrency bugs
- Race conditions
- Event ordering bugs
- Projection bugs
- Data consistency issues
- Idempotency issues

---

## Design Flaws

Identify:

- Poor aggregate boundaries
- Incorrect ownership
- Leaky abstractions
- Large aggregates
- CQRS violations
- DDD violations
- Poor API design
- Poor event design
- Tight coupling
- Hidden dependencies

---

## Design Gaps

Identify:

- Missing business rules
- Missing workflows
- Missing lifecycle states
- Missing validation
- Missing authorization
- Missing auditing
- Missing retry logic
- Missing compensation
- Missing idempotency
- Missing optimistic concurrency
- Missing monitoring
- Missing observability
- Missing projections

---

## Lifecycle Issues

Identify:

- Impossible transitions
- Dead-end states
- Missing archive behaviour
- Missing deletion behaviour
- Missing recovery paths
- Partial failure scenarios
- Saga failures
- Timeout handling
- Eventual consistency issues

---

## Commands

Identify:

- Missing commands
- Duplicate commands
- Redundant commands
- Commands doing multiple jobs
- Incorrect aggregate ownership
- Poor naming

---

## Queries

Identify:

- Missing queries
- Duplicate queries
- Redundant queries
- Incorrect response models
- CQRS violations

---

## Endpoints

Identify:

- Missing endpoints
- Duplicate endpoints
- Incorrect HTTP methods
- Incorrect URLs
- Incorrect versioning
- Missing authorization
- Missing request properties
- Missing response properties

---

## Request DTO Review

Identify:

- Missing properties
- Redundant properties
- Unused properties
- Missing validation
- Nullable mistakes
- Data type inconsistencies

---

## Response DTO Review

Identify:

- Missing properties
- Redundant properties
- Internal implementation leakage
- Naming inconsistencies
- Missing metadata

---

## Events

Identify:

### Domain Events

- Missing events
- Duplicate events
- Missing payload
- Incorrect timing
- Incorrect ownership

### Integration Events

- Missing events
- Duplicate events
- Missing identifiers
- Missing versioning
- Incorrect payload
- Incorrect publishing

---

# Phase 5 — Cross Validation

Verify the following:

- Every endpoint maps to a command or query.
- Every command is reachable.
- Every query is reachable.
- Every aggregate has a complete lifecycle.
- Every lifecycle transition is valid.
- Every command performs validation.
- Every command performs authorization.
- Every domain event has a publisher.
- Every integration event has a publisher.
- Every integration event has consumers.
- Every request DTO is used.
- Every response DTO is used.
- Every specification requirement is implemented.
- Every implementation is documented in the specification.

Identify any violations.

---

# Required Output Format

Produce the report in the following order.

# 1. Module Summary

Provide a high-level overview of the module.

---

# 2. Aggregate Analysis

Describe every aggregate and its responsibilities.

---

# 3. Lifecycle Analysis

Document the complete lifecycle and include a lifecycle diagram.

---

# 4. Commands

List every command and identify issues.

---

# 5. Queries

List every query and identify issues.

---

# 6. API Endpoints

List every endpoint and identify issues.

---

# 7. Request DTO Review

Review every request model.

---

# 8. Response DTO Review

Review every response model.

---

# 9. Domain Events

Review every domain event.

---

# 10. Integration Events

Review every integration event.

---

# 11. Specification vs Repository Differences

Present the differences using the following table.

| Item | Specification | Repository | Severity | Recommendation |
|------|---------------|------------|----------|----------------|

---

# 12. Bugs

Categorise using:

- Critical
- High
- Medium
- Low

For each issue include:

- Description
- Why it is a problem
- Impact
- Recommendation

---

# 13. Design Flaws

Document every architectural flaw.

---

# 14. Design Gaps

Document every missing capability.

---

# 15. Missing Features

Document missing commands, queries, endpoints, workflows, events, validation, lifecycle states, and business rules.

---

# 16. Recommendations

Prioritise recommendations in the following order:

1. Correctness
2. Data Integrity
3. Security
4. Domain Modelling
5. Lifecycle Improvements
6. API Improvements
7. Event Improvements
8. Maintainability
9. Performance
10. Scalability

For every recommendation include:

- Priority
- Description
- Justification
- Suggested implementation approach

---

# Output & Filing

Write the report as a single Markdown file to:

  D:\source\github\magiq-media\docs\reviews\catalog-{{aggregate-lowercase}}-architecture-review.md

e.g. catalog-mediaitem-architecture-review.md. One file per aggregate; four
files total when Catalog is complete.

Match docs/reviews/assetmanagement-architecture-review.md exactly for structure
and tone:
- Front-matter block: Aggregate, Reviewer role, Date, Scope (the exact spec/code
  globs reviewed), and a one-line Method note stating how many production .cs
  files were read.
- All 16 numbered sections from "Required Output Format," in order.
- Severity buckets (Critical / High / Medium / Low), each finding with a stable
  ID (e.g. MI-D1) and file:line references.
- End with a "Top 5 before production" list.

# Review Principles

- Do not assume the specification is correct.
- Do not assume the repository is correct.
- Challenge both equally.
- Prefer Domain-Driven Design best practices.
- Prefer CQRS best practices.
- Prefer Event Sourcing principles where applicable.
- Look for edge cases.
- Look for race conditions.
- Look for eventual consistency issues.
- Look for partial failure scenarios.
- Look for unnecessary complexity.
- Look for opportunities to simplify the design.
- Explain **why** every issue is a problem.
- Provide practical recommendations to resolve every issue.
- Do not proceed to another module until this module has been completely understood, analysed, and reviewed.