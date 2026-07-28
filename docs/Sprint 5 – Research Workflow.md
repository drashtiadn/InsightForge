**Status:** ✅ Completed  
**Objective:** Introduce InsightForge's first business workflow by modeling the `ResearchSession` lifecycle in the service layer, validating explicit state transitions, and exposing workflow endpoints without introducing AI agents, background workers, or new architectural layers.

---

# Sprint Summary

Sprint 5 focused on business behavior rather than infrastructure. Sprint 4 already allowed clients to create and retrieve research sessions, but sessions still behaved like static records. This sprint introduced the first workflow contract: a research session can now start execution and move through a controlled lifecycle.

The implementation intentionally stayed small and explicit. No workflow engine, no state machine library, no background jobs, and no AI integration were added. The goal was to make the domain rules visible and reusable in the service layer so later orchestration can depend on them without redesign.

---

# Problem Statement

Before Sprint 5, the system could persist and expose `ResearchSession` records, but it could not express business progress. A session had a status field in the database, yet there was no application-level rule enforcing what each state meant or which transitions were allowed.

Without workflow validation:

- clients could request invalid transitions such as `PENDING -> COMPLETED`
- completed or failed research could be restarted accidentally
- route handlers would be tempted to mutate ORM state directly
- future workers or AI agents would have no reusable business API for lifecycle updates

Sprint 5 addressed this by putting workflow rules into `ResearchSessionService` and leaving the repository persistence-only.

---

# Sprint Goals

## In Scope

- Add `start_research()` to `ResearchSessionService`
- Add `update_status()` to `ResearchSessionService`
- Validate lifecycle transitions explicitly
- Raise domain exceptions for invalid workflow requests
- Add repository persistence support for updates
- Add workflow endpoints for start and status changes
- Keep transaction ownership in the service layer

## Out of Scope

- LangGraph
- LLMs or AI agents
- Report generation logic
- Background workers
- Celery / Redis
- WebSockets / SSE
- Authentication / authorization
- Title/query updates
- Pagination, search, delete
- Generic workflow engines or state machine libraries

---

# Architecture Snapshot

```
Client
   │
   ▼
API Layer (/api/v1/research-sessions)
   │
   ├── Request parsing
   ├── Response serialization
   ├── HTTP error mapping
   │
   ▼
Service Layer (ResearchSessionService)
   │
   ├── Workflow rules
   ├── Transition validation
   ├── Domain exceptions
   ├── Commit / refresh / rollback
   │
   ▼
Repository Layer (ResearchSessionRepository)
   │
   ├── add / get_by_id / list / update
   │
   ▼
Database (PostgreSQL)
```

Workflow remains a service concern:

`Client -> API -> Service -> Repository -> Database`

The repository persists changes. The service decides whether a change is valid.

---

# Workflow Definition

Primary path:

`PENDING -> PLANNING -> RESEARCHING -> REPORT_GENERATION -> COMPLETED`

Failure path:

- `RESEARCHING -> FAILED`
- `REPORT_GENERATION -> FAILED`

Examples:

- Allowed: `PENDING -> PLANNING`
- Allowed: `PLANNING -> RESEARCHING`
- Allowed: `RESEARCHING -> FAILED`
- Not allowed: `PENDING -> COMPLETED`
- Not allowed: `COMPLETED -> RESEARCHING`
- Not allowed: `FAILED -> PLANNING`

This keeps the workflow readable and prevents clients from skipping business steps.

---

# Implementation

## Service Layer Workflow

`ResearchSessionService` now owns:

- `start_research()`
- `update_status()`
- explicit transition validation
- transaction commit / refresh / rollback for workflow updates

**Why here?**

Workflow is business behavior. The service understands what it means to "start research" and what counts as an invalid move through the lifecycle. This is exactly the kind of logic that should stay reusable outside FastAPI.

`start_research()` is intentionally narrow:

- it loads the session
- rejects restart attempts for completed sessions
- rejects duplicate starts for already-running sessions
- moves `PENDING -> PLANNING`

`update_status()` is the generic lifecycle operation used for the next valid step.

---

## Explicit Transition Validation

The sprint uses an explicit transition map rather than a generic state engine.

**Why?**

- easier to read
- easier to debug
- easier to teach
- matches the current workflow size
- avoids premature abstraction

Invalid transitions raise `InvalidResearchStateTransition`, which is a domain error rather than an HTTP concern.

---

## Domain Exceptions

Added to `app/services/exceptions.py`:

- `InvalidResearchStateTransition`
- `ResearchAlreadyCompleted`
- `ResearchAlreadyRunning`

**Why?**

These exceptions describe business outcomes in domain language. The service should say "this session is already running" rather than "return HTTP 409." That separation is what makes the service reusable from route handlers, scripts, workers, and later AI orchestrators.

---

## Repository Update Support

Added:

- `update()`

to `ResearchSessionRepository`.

**Why only this?**

The repository should only persist a changed ORM object. It should not know whether a transition is valid, when a transaction should commit, or which statuses are terminal. That knowledge belongs to the service layer.

---

## API Endpoints

Added:

| Method | Path | Behavior |
|--------|------|----------|
| `POST` | `/api/v1/research-sessions/{id}/start` | Move `PENDING -> PLANNING` |
| `PATCH` | `/api/v1/research-sessions/{id}/status` | Move to the next valid lifecycle state |

Added schema:

- `ResearchSessionStatusUpdate`

Error mapping:

- `404` for missing sessions
- `409` for restart conflicts such as already completed or already running
- `400` for invalid state transitions

**Why keep this mapping in the API?**

HTTP is a transport concern. The API translates domain exceptions into status codes, while the service remains framework-agnostic.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|-----------|-------------------------|---------------------|------------|
| Workflow in service layer | Route handlers mutating status directly | Keeps business rules reusable and centralized | Service grows as behavior grows |
| Explicit transition map | Generic engine / library | Clear and readable for a small workflow | Manual updates needed when states evolve |
| Domain exceptions instead of `HTTPException` in service | Raise HTTP errors directly | Keeps service independent of FastAPI | API must translate exceptions |
| Repository `update()` only | Repository validates transitions too | Preserves separation between persistence and business rules | More coordination through service |
| Service-owned transactions | Repository commits updates | Maintains use-case transaction boundaries | Service must manage rollback paths |

---

# Validation

The implementation was validated by:

- checking touched files for linter diagnostics
- successful Python compilation of `backend/app`
- confirming the repository contains persistence operations only
- confirming workflow endpoints reuse the existing response schema
- confirming the API exposes the new start and status routes through OpenAPI

Behavior validated in code:

- cannot skip states
- cannot restart completed research
- cannot restart already-running research
- failed sessions cannot re-enter planning
- service owns commit / refresh / rollback behavior

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|------------|----------|----------|
| Status enum already existed but had no enforced behavior | Added workflow logic to the service instead of the model or repository | A stored state is not the same thing as a business workflow |
| Temptation to add a generic workflow abstraction | Used an explicit transition map | Small explicit code is usually better early in a domain |
| Need to support future non-HTTP callers | Kept exceptions domain-specific and HTTP mapping in routes | Reusable business services should not depend on web frameworks |
| Need to persist updates without leaking transactions into the repository | Added `update()` but kept commit in the service | Persistence and transaction orchestration are related, but not the same responsibility |

---

# Deliverables

- Research workflow progression in `ResearchSessionService`
- State transition validation
- `InvalidResearchStateTransition`
- `ResearchAlreadyCompleted`
- `ResearchAlreadyRunning`
- Repository `update()` persistence support
- `POST /api/v1/research-sessions/{id}/start`
- `PATCH /api/v1/research-sessions/{id}/status`
- `ResearchSessionStatusUpdate` schema
- OpenAPI exposure of workflow endpoints

---

# Outcome

Sprint 5 successfully introduced InsightForge's first real business workflow without changing the existing architecture.

Research sessions are no longer passive records. They now move through a controlled lifecycle enforced by the service layer, which gives the project a reusable workflow core for future AI agents and background workers. Later orchestrators will be able to call the same service methods directly, whether they are triggered by HTTP requests, async jobs, or internal automation, because the business rules are not tied to FastAPI.
