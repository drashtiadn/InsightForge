**Status:** ✅ Completed  
**Objective:** Introduce the Reporting layer as a distinct architectural concern that transforms independent execution results into one coherent `ResearchReport`, without embedding synthesis in the planner, execution engine, tools, or service.

---

# Sprint Summary

Sprint 11 introduced InsightForge's Reporting layer. After Sprint 10, the system could plan research, execute tasks through real web search (`TavilySearchTool`), and aggregate task results — but it never combined those results into something a user should read.

This sprint established the reporting abstraction. Execution still produces independent task outputs. Reporting synthesizes those outputs into a structured document. The service orchestrates both; it does not implement synthesis itself.

The implementation is deterministic. No LLM summarization, no Markdown rendering, no PDF/DOCX/HTML export, and no persistence. The goal is to validate the synthesis seam — from `ResearchExecutionResult` to `ResearchReport` — and establish the injection point where richer generators can later plug in.

---

# Problem Statement

Before Sprint 11, `start_research()` returned raw execution artifacts:

```
ResearchExecutionResult
  └── task_results[]  (independent outputs)
```

Users should not receive a list of task artifacts. They should receive a coherent report. That synthesis does not belong in:

- the **Planner** — which decides *what* to research
- the **Execution Engine** — which decides *when* and *in what order* tasks run
- a **Tool** — which decides *how* one task is completed
- the **Service** — which should orchestrate collaborators, not synthesize documents

Sprint 11 addressed this by extracting report generation into its own layer.

---

# Sprint Goals

## In Scope

- Create `app/reporting/` package
- Create `ReportGenerator` abstract base class with a single `generate` method
- Create immutable `ResearchReport` and `ResearchSection` value objects
- Create `ReportGenerationError` exception
- Create `SimpleReportGenerator` — deterministic first implementation
- Inject `ReportGenerator` into `ResearchSessionService`
- Wire `SimpleReportGenerator` via dependency injection in the API layer
- Structured logging for report generation start, section count, duration, and completion

## Out of Scope

- LLM summarization
- Markdown rendering
- PDF / DOCX / HTML export
- Streaming
- Persistence
- LangGraph
- Multi-agent synthesis
- Citation formatting
- References section
- Report editing

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
   ├── _planner.create_plan(session)
   │         │
   │         ▼
   │     ResearchPlan
   │
   ├── _execution_engine.execute(plan)
   │         │
   │         ▼
   │     ResearchExecutionResult
   │
   └── _report_generator.generate(execution_result)
             │
             ▼
         ReportGenerator (ABC)
             │
             ▼
         SimpleReportGenerator
             │
             ▼
         ResearchReport (in-memory)
```

Planner, execution, tools, and reporting remain independent. The service wires them; the repository never sees the plan, execution result, or report.

---

# Reporting Package Structure

```
app/reporting/
    __init__.py       — public exports
    generator.py      — ReportGenerator ABC, SimpleReportGenerator
    models.py         — ResearchSection, ResearchReport
    exceptions.py     — ReportGenerationError
```

---

# Report Generator Abstraction

## `ReportGenerator` (Abstract Base Class)

Defined in `app/reporting/generator.py`. Intentionally minimal:

```
generate(execution_result: ResearchExecutionResult) -> ResearchReport
```

All current and future generators implement this one method. The service depends on this abstraction, never on a concrete class.

Generators must not:

- Call the planner
- Call the execution engine
- Call tools
- Write to the database
- Mutate the `ResearchExecutionResult` they receive

## Responsibility Split

| Layer | Responsibility |
|---|---|
| `ExecutionEngine` | Run tasks and aggregate raw outputs |
| `Tool` | Complete one task / retrieve evidence |
| `ReportGenerator` | Synthesize outputs into one coherent report |
| `ResearchSessionService` | Orchestrate planner → engine → report generator |

Execution answers “what did each task produce?” Reporting answers “what should the user read?”

---

# Report Models

Both models are frozen dataclasses. Neither is persisted.

## `ResearchSection`

A single titled block within a research report.

Fields:

- `title` — section heading (typically the task title)
- `content` — section body (typically the task output)

## `ResearchReport`

The synthesized report for one research session.

Fields:

- `session_id` — UUID of the owning research session
- `title` — report title (original research query for the simple generator)
- `summary` — brief introduction
- `sections` — ordered list of `ResearchSection`
- `generated_at` — UTC timestamp when the report was assembled

---

# SimpleReportGenerator

Defined in `app/reporting/generator.py`. The first concrete `ReportGenerator` implementation.

For each `ResearchExecutionResult`:

1. Logs report generation start with `session_id` and `section_count`
2. Sets `title` to `execution_result.plan.original_query`
3. Builds a brief summary naming the task count and query
4. Creates one `ResearchSection` per `ResearchTaskResult` (`title` = task title, `content` = task output)
5. Logs completion with section count and duration in milliseconds
6. Returns an immutable `ResearchReport`

No prompts. No LLM calls. No external I/O. The mapping is fully deterministic.

---

# Service Integration

`ResearchSessionService` now accepts an injected `ReportGenerator`:

```python
def __init__(
    self,
    session: AsyncSession,
    repository: ResearchSessionRepository,
    planner: ResearchPlanner,
    execution_engine: ExecutionEngine,
    report_generator: ReportGenerator,
) -> None:
    ...
```

`start_research()` orchestration is now:

1. Validate session state
2. Transition `PENDING → PLANNING`
3. Call `self._planner.create_plan(session)`
4. Call `self._execution_engine.execute(plan)`
5. Call `self._report_generator.generate(execution_result)`
6. Return a four-tuple: `(ResearchSession, ResearchPlan, ResearchExecutionResult, ResearchReport)`

The service orchestrates. It does not contain report-generation logic.

The API endpoint unpacks the tuple and discards plan, execution result, and report. `ResearchSessionResponse` is unchanged — no OpenAPI changes.

---

# Exception Hierarchy

`app/reporting/exceptions.py` defines:

- `ReportGenerationError` — base exception for all reporting-layer failures

Future generators (for example LLM-backed synthesis) can introduce subclasses without changing callers that catch the base type.

---

# Structured Logging

Every significant reporting milestone is logged with structured context using `loguru`:

| Event | Fields |
|---|---|
| Report generation started | `session_id`, `section_count` |
| Report generation completed | `session_id`, `section_count`, `duration_ms` |

No secrets are logged. `print()` is never used.

---

# Dependency Injection

`get_report_generator()` was added to `app/api/v1/research_sessions.py`:

```python
def get_report_generator() -> ReportGenerator:
    return SimpleReportGenerator()
```

`get_research_session_service()` receives the generator via `Depends` and passes it into the service constructor. To introduce an LLM report generator later, only this provider changes:

```python
def get_report_generator() -> ReportGenerator:
    return LLMReportGenerator(llm_client=...)
```

Nothing above or below the provider is affected.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|---|---|---|---|
| Dedicated `reporting/` package | Put synthesis in the service or engine | Keeps synthesis replaceable and independent of orchestration / retrieval | Another package to navigate |
| Abstract `ReportGenerator` | Concrete generator injected directly | Enables LLM / executive / export-oriented swaps without service changes | Extra indirection for a single implementation today |
| Frozen dataclasses for report models | Pydantic models | Lightweight, immutable, consistent with planning/execution/tool models | Less convenient if reports are later exposed via API |
| Report not persisted | Store report in the database | Avoids premature schema design while the report contract is unstable | Report is lost after the request |
| Deterministic section-per-task mapping | Jump straight to LLM summarization | Validates the seam before introducing cost, latency, and non-determinism | Not a polished narrative yet |
| Keep returning plan + execution + report | Return only `ResearchReport` | Intermediate artifacts remain available for architecture validation and debugging | Service return tuple grows further |
| No OpenAPI exposure yet | Add a report response schema now | Matches prior sprints: prove in-memory first, expose when the contract is stable | Clients cannot fetch the report yet |

---

# Validation

The implementation was validated by:

- confirming `ExecutionEngine`, planner, and tools are unchanged
- confirming `ReportGenerator` is injected into the service, not instantiated inside it
- confirming `SimpleReportGenerator.generate()` maps each task result to one section
- confirming report title equals the original query
- confirming no LLM calls are made in the reporting layer
- confirming no database writes occur for plan, execution result, or report
- confirming no OpenAPI schema changes were introduced
- confirming structured logs emit start, section count, duration, and completion

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|---|---|---|
| Temptation to synthesize inside the execution engine | Created a dedicated `reporting/` package | Execution aggregates evidence; reporting produces the user-facing document |
| Temptation to implement report logic in the service | Injected `ReportGenerator` and called one method | Services should orchestrate collaborators, not grow domain algorithms |
| Deciding what a “report” means before LLM quality exists | Deterministic title / summary / sections | Stabilize the document model first; improve content quality later |
| Return signature of `start_research()` grew again | Extended to a four-tuple | Prefer a result object if the return shape grows further |
| Report is not exposed via API yet | Discarded at the API layer for now | In-memory synthesis validates architecture; exposure follows when the contract is stable |

---

# Deliverables

- `app/reporting/__init__.py`
- `app/reporting/models.py` — `ResearchSection`, `ResearchReport`
- `app/reporting/exceptions.py` — `ReportGenerationError`
- `app/reporting/generator.py` — `ReportGenerator` (ABC), `SimpleReportGenerator`
- Updated `ResearchSessionService` — `ReportGenerator` injected; `start_research()` returns four-tuple
- Updated API layer — `get_report_generator()` dependency provider; no OpenAPI changes

---

# Outcome

Sprint 11 completed InsightForge's Reporting layer. The pipeline is now:

**Plan → Execute → Report**

Execution still produces independent task results. Reporting turns those results into one coherent in-memory `ResearchReport`. The injection seam is in place: an LLM report generator, executive-summary generator, or export-oriented formatter can replace `SimpleReportGenerator` without touching the planner, execution engine, tools, repository, or OpenAPI contract.

The architecture is ready for richer synthesis and, later, persistence and export formats that consume `ResearchReport` as their input.
