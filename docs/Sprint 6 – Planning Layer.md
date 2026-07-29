**Status:** ✅ Completed  
**Objective:** Introduce the planning layer as a distinct architectural concern, separating the decision of *what* to research from the service orchestration that manages the session lifecycle.

---

# Sprint Summary

Sprint 6 introduced InsightForge's first domain-specific layer beyond persistence: the planning layer. Prior to this sprint, the service managed the research session lifecycle but had no concept of decomposing a query into actionable research tasks. This sprint created that concept.

The implementation was intentionally deterministic. No LLM calls, no HTTP, no external dependencies. The planner used local heuristics to produce a `ResearchPlan` from a `ResearchSession`, validating the architectural seam between service orchestration and planning logic before AI was introduced.

---

# Problem Statement

Before Sprint 6, `ResearchSessionService.start_research()` transitioned a session to `PLANNING` and returned. The PLANNING state had no meaning beyond a label — no plan was generated, no tasks were defined, and no research direction was established.

Without a planning layer:

- the service would eventually accumulate planning logic, violating single responsibility
- planning and session management would become entangled and difficult to evolve independently
- AI-backed planners could not be introduced without redesigning the service
- the architecture had no clean seam for swapping planning strategies

Sprint 6 addressed this by establishing the planning abstraction and its first concrete implementation.

---

# Sprint Goals

## In Scope

- Create `app/planning/` package
- Create `ResearchTask` and `ResearchPlan` in-memory dataclasses
- Create `ResearchPlanner` abstract base class
- Create `SimpleResearchPlanner` deterministic implementation
- Integrate planner into `ResearchSessionService` via dependency injection
- Wire planner provider into the API layer
- Return `ResearchPlan` from `start_research()` in memory

## Out of Scope

- LLM integration
- Web search or Tavily
- Prompt engineering
- LangGraph
- Background workers
- Persisting plans or tasks
- Agent tool calling

---

# Architecture Snapshot

```
Client
   │
   ▼
API Layer
   │
   ▼
ResearchSessionService
   │
   ├── Lifecycle orchestration
   │
   ├── _planner.create_plan(session)
   │       │
   │       ▼
   │   ResearchPlanner (ABC)
   │       │
   │       ▼
   │   SimpleResearchPlanner
   │       │
   │       └── Returns ResearchPlan (in-memory)
   │
   ▼
Repository → Database
```

The planner is a collaborator of the service, not a layer below it. The repository remains unchanged and has no awareness of plans or tasks.

---

# Planning Models

## `ResearchTask`

A single actionable step in a research plan.

Fields:

- `id` — UUID
- `title` — short label
- `description` — detailed instructions for the task

## `ResearchPlan`

An ordered collection of tasks for a single research session.

Fields:

- `session_id` — UUID linking the plan to its session
- `original_query` — the user's original research query
- `tasks` — ordered list of `ResearchTask` objects

Both models are frozen dataclasses. They are never persisted. They are value objects representing a planning decision made at a point in time.

---

# Implementation

## Planning Abstraction

`ResearchPlanner` is an abstract base class with one method:

```
create_plan(session: ResearchSession) -> ResearchPlan
```

The abstract contract ensures:

- any concrete planner can be injected without changing the service
- LLM-backed planners can be introduced by implementing the same interface
- the service depends on the abstraction, not a concrete class

## `SimpleResearchPlanner`

The first implementation. Fully deterministic. No external calls.

Behavior:

- detects comparison queries using keyword matching (`compare`, `vs`, `versus`)
- extracts subjects from comparison queries using a regex split
- produces `Understand <subject>` tasks for each detected subject
- produces a `Compare features` task when two or more subjects are found
- falls back to `Investigate the topic` for non-comparative queries
- always appends a `Summarize findings` task

This heuristic approach produces meaningful enough output to validate the full planning pipeline without needing an LLM.

## Service Integration

`ResearchSessionService.__init__()` now accepts a `ResearchPlanner` as a constructor argument. The service calls `self._planner.create_plan(session)` after the `PENDING -> PLANNING` transition and returns both the session and the plan from `start_research()`.

The service does not inspect the plan. It orchestrates — the planner decides.

## Dependency Injection

A `get_research_planner()` provider was added to the API layer:

```python
def get_research_planner() -> ResearchPlanner:
    return SimpleResearchPlanner()
```

`get_research_session_service()` receives the planner via `Depends`. Swapping planners requires only changing this provider.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|-----------|-------------------------|---------------------|------------|
| Abstract `ResearchPlanner` base class | Concrete planner injected directly | Enables future swap without service changes | Extra indirection for a small codebase |
| Frozen dataclasses for plan models | Pydantic models | Lightweight, immutable, no schema generation overhead | Less convenient for serialization later |
| Plans not persisted | Store tasks in the database | Avoids premature schema design while contract is unstable | Results are lost on every request |
| Deterministic planner first | Start with LLM planner | Validates architecture without external dependencies | Output is not real research planning |
| DI via FastAPI `Depends` | Global planner instance | Per-request injection, testable, swappable | Slightly more wiring in the API layer |

---

# Validation

The implementation was validated by:

- confirming `ResearchPlan` and `ResearchTask` are immutable and in-memory only
- confirming the planner is injected via constructor, not instantiated inside the service
- confirming `start_research()` returns both the session and the plan
- confirming the API endpoint unpacks the tuple and discards the plan without error
- checking touched files for linter diagnostics

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|------------|----------|----------|
| Temptation to put planning logic inside the service | Created a dedicated `planning/` package | Services should orchestrate collaborators, not implement domain decisions |
| Deciding how to detect comparison queries | Regex markers and split pattern | Simple heuristics are sufficient to validate architecture before AI is introduced |
| Plan models needed to be immutable | Used `frozen=True` dataclasses | Value objects that represent decisions should not be mutated after creation |
| Planner needed to be swappable | Abstract base class + DI | Abstractions at seams allow independent evolution of planning strategies |

---

# Deliverables

- `app/planning/__init__.py`
- `app/planning/models.py` — `ResearchTask`, `ResearchPlan`
- `app/planning/planner.py` — `ResearchPlanner` (ABC), `SimpleResearchPlanner`
- Updated `ResearchSessionService` — planner injected, `start_research()` returns plan
- Updated API layer — `get_research_planner()` dependency provider

---

# Outcome

Sprint 6 established InsightForge's planning layer as a first-class architectural concern. The service now orchestrates a planning collaborator rather than implementing planning itself. The abstract contract is stable enough for an LLM-backed planner to replace `SimpleResearchPlanner` in the next sprint without any changes to the service, repository, or API structure.
