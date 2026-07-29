**Status:** ✅ Completed  
**Objective:** Introduce the first AI-facing architecture by creating a Research Planning layer that converts a research session into an executable plan, without calling any LLM or external API.

---

# Sprint Summary

Sprint 6 established the planning abstraction that sits between the service layer and future AI agents. Before this sprint, starting research only moved a session into the `PLANNING` status — there was no concept of decomposing the query into concrete research tasks.

This sprint introduced the `planning` package as a domain concern: an abstract planner interface, an immutable data model for plans and tasks, and a deterministic default implementation. The architecture was validated with pure Python logic, leaving the LLM integration for the next sprint.

---

# Problem Statement

Before Sprint 6:

- Starting research only flipped a workflow status
- There was no concept of "what work needs to be done"
- AI agents had no structured contract to receive research objectives
- Planning logic had nowhere to live except inside the service, which would make it untestable and hard to replace

---

# Sprint Goals

## In Scope

- Create `app/planning/` package with `__init__.py`, `models.py`, `planner.py`
- Define immutable `ResearchTask` and `ResearchPlan` dataclasses
- Create `ResearchPlanner` abstract base class
- Implement `SimpleResearchPlanner` using deterministic heuristics
- Extend `start_research()` to invoke the planner and return a plan
- Inject the planner like the repository (constructor DI)
- Add structured logging for research start and plan generation

## Out of Scope

- OpenAI, Gemini, Claude, or any LLM
- LangChain, LangGraph
- Persistence of plans
- Streaming or background workers

---

# Architecture

```
Client
   │
   ▼
API Layer
   │
   ▼
Service Layer (ResearchSessionService)
   │
   ├── Workflow transition: PENDING → PLANNING
   ├── Invokes planner.create_plan(session)
   │
   ▼
Planner (ResearchPlanner / SimpleResearchPlanner)
   │
   └── Returns ResearchPlan (in memory only)
   │
   ▼
Repository Layer
   │
   ▼
Database
```

The planner is not a repository and not a service. It is a domain component responsible for planning.

---

# Implementation

## Planning Models

`app/planning/models.py` defines two frozen dataclasses:

**`ResearchTask`**

| Field | Type | Purpose |
|-------|------|---------|
| `id` | `uuid.UUID` | Unique task identity |
| `title` | `str` | Short label |
| `description` | `str` | What to research |

**`ResearchPlan`**

| Field | Type | Purpose |
|-------|------|---------|
| `session_id` | `uuid.UUID` | Links plan to session |
| `original_query` | `str` | The unmodified query |
| `tasks` | `list[ResearchTask]` | Ordered research steps |

Both are `frozen=True` — immutable value objects. They are never persisted.

---

## Planner Abstraction

`ResearchPlanner` in `app/planning/planner.py` is an abstract base class with one method:

```
create_plan(session: ResearchSession) -> ResearchPlan
```

Planners must not perform HTTP calls, database writes, or workflow transitions.

---

## SimpleResearchPlanner

A heuristic-based planner that produces deterministic plans.

For a comparison query such as `"Compare FastAPI and Django"`:

1. Understand FastAPI
2. Understand Django
3. Compare features
4. Summarize findings

For a general query such as `"Explain vector databases"`:

1. Investigate the topic
2. Summarize findings

This validates the architecture without incurring API costs.

---

## Service Integration

`start_research()` was extended to:

1. Validate workflow transition `PENDING → PLANNING`
2. Commit the status change
3. Call `planner.create_plan(session)`
4. Return `(ResearchSession, ResearchPlan)`

The plan is not stored. The return type changed from `ResearchSession` to `tuple[ResearchSession, ResearchPlan]`.

---

## Dependency Injection

`ResearchPlanner` is injected into `ResearchSessionService` via its constructor — the same pattern used for `ResearchSessionRepository`. `get_research_planner()` in the API layer creates and returns the configured implementation.

---

## Structured Logging

| Event | Fields |
|-------|--------|
| Research started | `session_id` |
| Plan generated | `session_id`, `task_count` |

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|----------|-------------------------|---------------------|------------|
| Separate `planning/` package | Planning inside service | Keeps planning policy independent of orchestration | One more package to maintain |
| Frozen dataclasses | SQLAlchemy models | Plans are ephemeral value objects, not persisted records | Must be rebuilt each call |
| Abstract base class | Protocol | ABC provides `@abstractmethod` enforcement and is idiomatic for DI | Slightly more verbose than Protocol |
| Deterministic planner first | Call LLM immediately | Validates architecture without cost or latency | Plans are shallow; replaced next sprint |
| Service returns tuple | Service returns only session | Caller gets full context without another round-trip | API must unpack tuple |

---

# Why Planning Is Its Own Layer

**Planning answers "what", not "how".**

- The service owns workflow: when does a session advance?
- The repository owns persistence: what is stored?
- The planner owns decomposition: what work needs to be done?

If planning lived inside the service, every AI model swap would require editing the same class that owns transactions and workflow rules. With a dedicated layer, swapping `SimpleResearchPlanner` for `LLMResearchPlanner` requires zero changes to the service.

---

# Deliverables

- `app/planning/__init__.py`
- `app/planning/models.py` — `ResearchTask`, `ResearchPlan`
- `app/planning/planner.py` — `ResearchPlanner` ABC, `SimpleResearchPlanner`
- Extended `start_research()` in `ResearchSessionService`
- Planner dependency injection in `app/api/v1/research_sessions.py`
- Structured logging for planning events

---

# Outcome

Sprint 6 introduced the planning abstraction that serves as the interface between the backend and future AI agents. The system can now convert a research query into a structured task list, even without an LLM. The architecture is ready for the LLM planner to replace the deterministic one without touching the service layer.
