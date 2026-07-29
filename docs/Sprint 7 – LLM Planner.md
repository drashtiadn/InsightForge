**Status:** ✅ Completed  
**Objective:** Replace the deterministic `SimpleResearchPlanner` with an LLM-backed planner that uses a structured prompt to decompose research queries into actionable tasks, while keeping the planning abstraction and all surrounding layers unchanged.

---

# Sprint Summary

Sprint 7 introduced the first real AI behavior into InsightForge. The planning layer established in Sprint 6 provided a stable abstract contract — `ResearchPlanner` — that made this swap possible without touching the service, the repository, or the API.

The sprint introduced two new sub-packages: `app/llm/` for the raw LLM client and response models, and extensions to `app/planning/` for the LLM-backed planner and its exception handling. The `SimpleResearchPlanner` remains available as a fallback. The LLM planner is now the default.

---

# Problem Statement

After Sprint 6, the system generated plans using local heuristics. These plans were structurally valid but not meaningful — they could not reason about the query, consider context, or adapt task decomposition to the nature of the research request.

Without LLM-backed planning:

- every plan had the same shape regardless of the query
- the system could not demonstrate genuine AI research reasoning
- the planning seam existed but was never exercised with a real model
- the project could not progress toward real agent execution

Sprint 7 addressed this by introducing a structured LLM call at the planning stage.

---

# Sprint Goals

## In Scope

- Create `app/llm/` package with LLM client abstraction
- Create LLM request and response models
- Create `LLMResearchPlanner` implementing `ResearchPlanner`
- Create `app/planning/exceptions.py` with planning-specific exceptions
- Integrate LLM planner as the default via dependency injection
- Keep `SimpleResearchPlanner` intact as a fallback
- Structured logging throughout the LLM planning path

## Out of Scope

- Web search or Tavily
- LangGraph or agent frameworks
- Tool calling or function calling
- Streaming responses
- LLM output caching
- Persisting plans
- Background workers
- Prompt versioning

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
   └── _planner.create_plan(session)
           │
           ▼
       LLMResearchPlanner
           │
           ├── Builds structured prompt
           ├── Calls LLMClient
           │       │
           │       ▼
           │   OpenAI API (or compatible)
           │
           ├── Parses structured response
           ├── Raises PlanningError on failure
           │
           ▼
       ResearchPlan (in-memory)
```

The `ResearchPlanner` abstraction from Sprint 6 remains the contract. The service, repository, and API are untouched.

---

# New Packages

## `app/llm/`

Encapsulates all LLM communication. Nothing outside this package sends HTTP requests to an LLM provider.

### `LLMClient`

Wraps the OpenAI-compatible API. Accepts a prompt and returns a structured response. Has no knowledge of planning, sessions, or tasks.

### LLM Models

Request and response dataclasses for communicating with the LLM. These are transport-level models — they describe what goes in and what comes out of the API call, not what those values mean to the planning domain.

## `app/planning/exceptions.py`

Planning-specific exceptions raised when the LLM response cannot be parsed or is structurally invalid.

- `PlanningError` — base class for all planning failures
- `LLMPlanningError` — raised when the LLM response does not produce a usable plan

These exceptions let callers catch planning failures without catching generic exceptions, and without importing LLM internals.

---

# LLM Planner Implementation

## `LLMResearchPlanner`

Implements `ResearchPlanner`. Its `create_plan()` method:

1. Constructs a structured prompt instructing the LLM to decompose the query into a small number of ordered research tasks
2. Calls `LLMClient` with the prompt
3. Parses the structured response into `ResearchTask` objects
4. Wraps them in a `ResearchPlan`
5. Raises `LLMPlanningError` if the response is invalid or unparseable

The planner is stateless. It holds an `LLMClient` injected at construction. It does not retry, cache, or stream.

## Prompt Design

The prompt is a structured instruction that asks the LLM to return a JSON array of tasks. Each task has a title and a description. The prompt provides:

- the original query
- instructions to produce 3–6 focused tasks
- a required output format

Structured output rather than free text is used because the response must be parsed into typed models. Free-form text would require post-processing heuristics and introduce fragility.

---

# Dependency Injection

The LLM planner is injected in the same way the simple planner was:

```python
def get_research_planner() -> ResearchPlanner:
    return LLMResearchPlanner(client=LLMClient())
```

To fall back to the deterministic planner, only this provider changes. The service, the service constructor, and the endpoints are untouched.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|-----------|-------------------------|---------------------|------------|
| Separate `app/llm/` package | LLM calls inside planner | Isolates HTTP concerns; LLM client is reusable across future planners and agents | Extra package for a single client |
| Structured JSON prompt | Free-text prompt | Enables deterministic parsing without regex heuristics | LLM must follow format instructions reliably |
| `LLMPlanningError` exception | Generic `ValueError` | Typed failures; callers can catch planning errors specifically | More exception types to maintain |
| `SimpleResearchPlanner` kept intact | Removed | Provides a reliable fallback for offline testing and CI | Two planner implementations to maintain |
| Planner remains synchronous | `async` planner | Consistent with existing service interface; async can be introduced later | Blocking I/O on the LLM call |

---

# Validation

The implementation was validated by:

- confirming `LLMResearchPlanner` implements `ResearchPlanner` without modifying the ABC
- confirming the service constructor signature is unchanged
- confirming the API dependency provider is the only change in the API layer
- confirming `SimpleResearchPlanner` is still importable and functional
- checking touched files for linter diagnostics

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|------------|----------|----------|
| LLM responses are not guaranteed to be valid JSON | Wrap parsing in try/except and raise `LLMPlanningError` | LLM output must always be treated as untrusted until validated |
| Temptation to call the LLM client directly inside the planner | Created a dedicated `LLMClient` class | Communication concerns should be isolated so planners are testable without real API calls |
| Deciding how many tasks to request | Prompt instructs 3–6 tasks | Task count should match execution complexity, not be arbitrarily large |
| Keeping the service unchanged | Abstract planner contract from Sprint 6 | Designing abstractions at seams pays off when implementations change |

---

# Deliverables

- `app/llm/__init__.py`
- `app/llm/client.py` — `LLMClient`
- `app/llm/models.py` — LLM request and response models
- `app/planning/exceptions.py` — `PlanningError`, `LLMPlanningError`
- `app/planning/llm_planner.py` — `LLMResearchPlanner`
- Updated API dependency provider — `LLMResearchPlanner` as default
- Structured logging for LLM calls and plan parsing

---

# Outcome

Sprint 7 introduced InsightForge's first genuine AI behavior. The planning layer now calls a real LLM, receives a structured decomposition of the research query, and converts it into an ordered `ResearchPlan`. The abstract `ResearchPlanner` contract that Sprint 6 established made this introduction clean — the service, the repository, and the API were untouched. The system is now ready for Sprint 8, which will introduce an execution engine to carry out the plans the LLM produces.
