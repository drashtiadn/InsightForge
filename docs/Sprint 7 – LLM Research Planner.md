**Status:** ✅ Completed  
**Objective:** Replace the deterministic planner with an LLM-backed implementation that uses Google Gemini to generate structured research plans, while keeping the service layer, API, and `ResearchPlanner` interface entirely unchanged.

---

# Sprint Summary

Sprint 6 established the planning abstraction. Sprint 7 activated it. The `SimpleResearchPlanner` was a heuristic placeholder that validated the architecture. This sprint introduced `LLMResearchPlanner`, which asks an LLM to decompose the research query into a logical task list and returns a structured `ResearchPlan`.

Importantly, only the provider layer and dependency injection changed. The service, repository, OpenAPI schema, and database remained untouched.

---

# Problem Statement

The deterministic planner can only produce shallow, pattern-matched plans. It cannot understand arbitrary research questions, reason about scope, or produce task descriptions that reflect real domain knowledge.

The LLM planner addresses this while the planning abstraction already in place ensures the change is contained entirely within the `planning` and `llm` packages.

---

# Sprint Goals

## In Scope

- Create `app/llm/` package with `client.py`, `models.py`, `__init__.py`
- Define `LLMClient` abstract base class and `GeminiLLMClient` implementation
- Create `LLMResearchPlanner` in `app/planning/llm_planner.py`
- Define planning-specific exceptions: `PlanningFailed`, `InvalidPlannerResponse`, `LLMUnavailable`
- Structured JSON output using Gemini's `response_json_schema`
- Configuration-driven planner selection (`PLANNER_TYPE=simple` or `llm`)
- Add `PLANNER_TYPE`, `LLM_MODEL`, `LLM_TEMPERATURE`, `GEMINI_API_KEY` to config

## Out of Scope

- Web search, Tavily, LangGraph, LangChain
- Report generation
- Streaming or background workers
- Persistence of research plans

---

# Architecture

```
Client
   │
   ▼
API Layer
   │
   ▼
Service Layer (unchanged)
   │
   ▼
ResearchPlanner interface
   │
   ├── SimpleResearchPlanner (deterministic, default)
   └── LLMResearchPlanner
           │
           ▼
       LLMClient (abstract)
           │
           └── GeminiLLMClient
                   │
                   ▼
               Google Gemini API
```

**Boundaries:**

- Planner owns prompts and schema validation
- `LLMClient` owns provider communication
- Service is provider-agnostic; it catches planning exceptions, not SDK errors

---

# Implementation

## LLM Package

`app/llm/` isolates all provider-specific code.

**`app/llm/models.py`** — transport value objects:

| Class | Purpose |
|-------|---------|
| `LLMMessage` | A single `role` + `content` pair |
| `LLMRequest` | Messages, model, temperature, JSON schema |
| `LLMResponse` | Parsed `dict` from the provider |

**`app/llm/client.py`** — abstraction and implementation:

| Class | Purpose |
|-------|---------|
| `LLMClient` | ABC with `complete_json(request) -> LLMResponse` |
| `GeminiLLMClient` | Calls `google-genai`, uses `response_json_schema` for structured output |
| `LLMClientError` | Base transport error |
| `LLMConnectionError` | Provider unreachable |
| `LLMResponseError` | Provider returned unusable content |

`GeminiLLMClient` maps the `LLMRequest` message list to Gemini's `system_instruction` + `contents` format, requests `response_mime_type="application/json"`, and parses the JSON text response.

---

## Planning Exceptions

`app/planning/exceptions.py` translates LLM transport failures into domain language:

| Exception | When raised |
|-----------|------------|
| `PlanningFailed` | Unclassified LLM error |
| `InvalidPlannerResponse` | Response fails schema validation |
| `LLMUnavailable` | Provider not configured or unreachable |

The service catches these instead of SDK-specific exceptions, keeping it provider-agnostic.

---

## LLM Research Planner

`app/planning/llm_planner.py` implements `ResearchPlanner`:

**Prompts (module constants):**

- `PLANNING_SYSTEM_PROMPT` — instructs the model to plan, not research
- `PLANNING_USER_PROMPT` — formats the query and task requirements

**Structured output:**

- `_PlanTaskSchema` (Pydantic) — validates each task `{title, description}`
- `_PlanSchema` (Pydantic) — validates the top-level `{tasks: [...]}` envelope
- Both schemas are passed to Gemini via `response_json_schema` for provider-side enforcement
- Pydantic validates the response a second time before building `ResearchPlan`

**Logging:**

| Event | Fields |
|-------|--------|
| Planning started | `session_id` |
| Planning completed | `session_id`, `task_count`, `duration_ms` |

---

## Configuration

Four new fields in `Settings`:

| Field | Default | Purpose |
|-------|---------|---------|
| `PLANNER_TYPE` | `simple` | Selects planner implementation |
| `LLM_MODEL` | `gemini-2.0-flash` | Model passed to the provider |
| `LLM_TEMPERATURE` | `0.2` | Controls output determinism |
| `GEMINI_API_KEY` | `""` | Provider API key |

---

## Dependency Injection

`get_research_planner()` in `app/api/v1/research_sessions.py` reads `settings.planner_type` and constructs either implementation. No other file changes. The service, routes, and repository are unaware of which planner is active.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|----------|-------------------------|---------------------|------------|
| `LLMClient` abstraction | Call Gemini SDK directly in planner | Keeps provider code out of planning logic; mockable in tests | One extra indirection layer |
| Prompts as module constants | Prompts in config or database | Prompts are planning policy — they belong with the planner | Requires code change to update prompts |
| Pydantic double-validation | Trust provider schema enforcement | Provider enforcement is a hint; Pydantic catches schema drift | Slightly more code |
| Config-driven planner selection | Code change to swap planners | Allows environment-level control without touching application code | Misconfigured `PLANNER_TYPE` raises at request time |
| Sync `create_plan()` | Async interface | Matches existing `ResearchPlanner` contract; keeps service simple | LLM call blocks the thread; async upgrade is a future concern |

---

# Why the LLM Client Exists

Without the `LLMClient` abstraction:

- Every planner would import a provider SDK directly
- Switching providers requires editing planning logic
- Tests need real network calls or complex monkeypatching
- Provider-specific error types leak into domain code

With `LLMClient`, the planner only calls `complete_json()`. Swapping Gemini for another provider means adding a new `LLMClient` implementation and updating `get_research_planner()` — no service or planner changes.

---

# Deliverables

- `app/llm/__init__.py`, `app/llm/models.py`, `app/llm/client.py`
- `app/planning/exceptions.py`
- `app/planning/llm_planner.py`
- Updated `app/core/config.py` with LLM configuration fields
- Updated `app/api/v1/research_sessions.py` DI factory
- Updated `requirements.txt` with `google-genai==2.14.0`
- Updated `.env.example` with Gemini environment variables

---

# Outcome

Sprint 7 activated the planning abstraction introduced in Sprint 6. The system can now produce AI-quality research task lists using Google Gemini. The service layer, API, and database remain unchanged. Switching back to the deterministic planner requires only a config variable change. The architecture is ready for future execution agents to receive and act on these plans.
