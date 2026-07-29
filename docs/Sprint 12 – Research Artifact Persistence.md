**Status:** ✅ Completed  
**Objective:** Persist completed `ResearchReport` aggregates through a dedicated repository and normalized database schema, without embedding storage concerns in planning, execution, or report generation.

---

# Sprint Summary

Sprint 12 introduced durable storage for research reports. After Sprint 11, the pipeline could plan, execute, and synthesize a coherent `ResearchReport` — but every artifact disappeared when the request finished.

This sprint established report persistence as its own concern. Reporting still produces immutable domain objects. A new `ResearchReportRepository` maps those objects to ORM models and writes them to PostgreSQL. The service orchestrates the save; it does not contain mapping or SQL.

Plans and execution results remain in memory. Only the generated report is persisted. No history API, export, editing, or OpenAPI changes were introduced.

---

# Problem Statement

Before Sprint 12, successful research produced:

```
ResearchPlan                 → discarded
ResearchExecutionResult      → discarded
ResearchReport               → discarded
```

Users cannot revisit reports, compare prior runs, continue research, or export results while artifacts live only in process memory.

Persistence does not belong inside:

- the **Planner** — which decides *what* to research
- the **Execution Engine** — which decides *when* and *in what order* tasks run
- the **Report Generator** — which decides *what the user should read*
- the **Service** — which should orchestrate collaborators, not own SQLAlchemy mapping

Sprint 12 addressed this by extracting report storage into a repository with an explicit domain ↔ ORM mapping layer.

---

# Sprint Goals

## In Scope

- Create `ResearchReportModel` and `ResearchSectionModel` ORM models
- Create `ResearchReportRepository` with `save`, `get_by_report_id`, and `get_by_session_id`
- Create mapping functions between domain and persistence models
- Add `report_id` to the domain `ResearchReport` for round-trip identity
- Inject `ResearchReportRepository` into `ResearchSessionService`
- Persist the generated report after report generation
- Alembic migration for `research_reports` and `research_sections`
- Structured logging for save start, report/session IDs, duration, and completion

## Out of Scope

- Search history API
- Report editing
- Versioning
- Soft delete
- Export / PDF / Markdown
- Sharing
- Full-text search
- Vector storage / embeddings
- Multi-user permissions
- Persisting plans or execution results
- OpenAPI / response schema changes

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
   ├── _report_generator.generate(execution_result)
   │         │
   │         ▼
   │     ResearchReport (domain)
   │
   └── _report_repository.save(report)
             │
             ▼
         ResearchReportRepository
             │
             ├── domain → ORM mapping
             │
             ▼
         PostgreSQL
             ├── research_reports
             └── research_sections
```

Planner, execution, tools, and report generation remain unchanged. Persistence is an independent step after synthesis.

---

# Folder Structure

```
app/
    models/
        research_report.py              — ResearchReportModel, ResearchSectionModel
    repositories/
        research_report_repository.py   — repository + mappers
    reporting/
        models.py                       — domain ResearchReport / ResearchSection
alembic/
    versions/
        a1b2c3d4e5f6_create_research_reports_tables.py
```

---

# Database Models

## `ResearchReportModel`

Defined in `app/models/research_report.py`.

| Column | Purpose |
|---|---|
| `id` | UUID primary key (domain `report_id`) |
| `session_id` | FK → `research_sessions.id` (CASCADE) |
| `title` | Report title |
| `summary` | Report summary |
| `generated_at` | UTC timestamp when the report was assembled |

## `ResearchSectionModel`

Normalized child rows for report sections.

| Column | Purpose |
|---|---|
| `id` | UUID primary key |
| `report_id` | FK → `research_reports.id` (CASCADE) |
| `title` | Section heading |
| `content` | Section body |
| `order_index` | Stable section order within the report |

Sections are loaded with `selectinload` and ordered by `order_index`. Cascade delete keeps the aggregate consistent when a report is removed.

**Why normalized tables instead of a JSON blob?**

- Clear relational integrity with sessions
- Ordered sections without opaque document parsing
- Room to query or export individual sections later
- Matches the existing SQLAlchemy / Alembic conventions

---

# Domain Model Update

`ResearchReport` gained an identity field:

```
report_id: uuid.UUID = field(default_factory=uuid.uuid4)
```

`SimpleReportGenerator` did not change. The default factory assigns an ID when a report is constructed, so persistence can round-trip without teaching the generator about storage.

Domain models remain frozen dataclasses. ORM models never leave the repository.

---

# Mapper Layer

Mapping lives inside `research_report_repository.py`:

| Direction | Functions |
|---|---|
| Domain → ORM | `_report_to_model`, `_section_to_model` |
| ORM → Domain | `_report_to_domain`, `_section_to_domain` |

On save, list position becomes `order_index`. On load, sections are sorted by `order_index` before rebuilding the domain report.

Callers never receive `ResearchReportModel` or `ResearchSectionModel`.

---

# Repository Interface

`ResearchReportRepository` responsibilities:

| Method | Behavior |
|---|---|
| `save(report)` | Map domain → ORM, stage rows, flush, return domain report |
| `get_by_report_id(id)` | Load one report with sections, or `None` |
| `get_by_session_id(id)` | Load all reports for a session, newest first |

No business rules. No report generation. No planner or execution calls.

---

# Service Integration

`ResearchSessionService` now accepts an injected report repository:

```python
def __init__(
    self,
    session: AsyncSession,
    repository: ResearchSessionRepository,
    report_repository: ResearchReportRepository,
    planner: ResearchPlanner,
    execution_engine: ExecutionEngine,
    report_generator: ReportGenerator,
) -> None:
    ...
```

`start_research()` orchestration is now:

1. Validate session state
2. Transition `PENDING → PLANNING`
3. `self._planner.create_plan(session)`
4. `self._execution_engine.execute(plan)`
5. `self._report_generator.generate(execution_result)`
6. `self._report_repository.save(report)`
7. Commit the unit of work
8. Return `(ResearchSession, ResearchPlan, ResearchExecutionResult, ResearchReport)`

The service still orchestrates only. Mapping and SQL stay in the repository.

The API endpoint continues to discard plan, execution result, and report from the HTTP response. `ResearchSessionResponse` is unchanged — no OpenAPI changes.

---

# Dependency Injection

`get_research_session_service()` constructs the report repository with the request-scoped DB session:

```python
return ResearchSessionService(
    session=db,
    repository=ResearchSessionRepository(db),
    report_repository=ResearchReportRepository(db),
    planner=planner,
    execution_engine=execution_engine,
    report_generator=report_generator,
)
```

Repositories are not instantiated inside the service. To swap storage later, only the provider (or repository implementation) changes.

---

# Structured Logging

Every significant persistence milestone is logged with structured context using `loguru`:

| Event | Fields |
|---|---|
| Saving report | `report_id`, `session_id` |
| Report save completed | `report_id`, `session_id`, `duration_ms` |

No report title, summary, or section content is logged. `print()` is never used.

---

# Migration

Alembic revision `a1b2c3d4e5f6` creates:

- `research_reports` with FK to `research_sessions`
- `research_sections` with FK to `research_reports`
- Indexes on `session_id` and `report_id`

Models are registered through `app.models` so Alembic metadata discovery continues to work via `import app.models`.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|---|---|---|---|
| Dedicated report repository | Persist inside `ReportGenerator` or service | Keeps storage replaceable and independent of synthesis / orchestration | Another collaborator to inject |
| Separate ORM `*Model` types | Reuse domain dataclasses as ORM | Avoids leaking SQLAlchemy into reporting | Explicit mapping required |
| Normalized section table | JSON/JSONB document column | Preserves order, integrity, and queryability | Extra join on read |
| Persist reports only | Also persist plans and execution results | Smallest durable artifact users need next | Intermediate artifacts still ephemeral |
| Domain `report_id` default | Assign ID only in the repository | Enables clean round-trips without changing the generator | Domain gains persistence identity |
| No OpenAPI exposure yet | Add report fetch endpoints now | Prove durable storage before locking an HTTP contract | Clients still cannot retrieve reports via API |

---

# Validation

The implementation was validated by:

- confirming planner, execution engine, tools, and `ReportGenerator` are unchanged
- confirming `ResearchReportRepository` is injected into the service, not created inside it
- confirming ORM models do not escape the repository
- confirming mapper round-trips preserve section order via `order_index`
- confirming Alembic upgrade creates `research_reports` and `research_sections`
- confirming a smoke save/load through the repository succeeds
- confirming structured logs emit saving, IDs, duration, and completion without content
- confirming no OpenAPI schema changes were introduced

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|---|---|---|
| Temptation to save inside the report generator | Repository called only from the service | Synthesis and storage change for different reasons |
| Domain report had no identity | Added `report_id` with `default_factory` | Persistence round-trips need a stable ID without teaching generators about SQL |
| Section order is a list in domain, a column in SQL | Map list index ↔ `order_index` | Mapping exists to translate representation, not business rules |
| ORM convenience vs clean architecture | Keep `*Model` types repository-private | Services should speak domain language, not session-bound entities |
| Reports stored but not exposed | Persist first, expose later | Durable data unblocks history/export; API contract can follow |

---

# Deliverables

- `app/models/research_report.py` — `ResearchReportModel`, `ResearchSectionModel`
- `app/repositories/research_report_repository.py` — repository + mappers
- Alembic migration `a1b2c3d4e5f6_create_research_reports_tables.py`
- Updated domain `ResearchReport` — `report_id` field
- Updated `ResearchSessionService` — injected report repository; save + commit after generate
- Updated API DI — wires `ResearchReportRepository`; no OpenAPI changes

---

# Outcome

Sprint 12 completed InsightForge's report persistence seam. The pipeline is now:

**Plan → Execute → Report → Persist**

Reporting still produces an immutable `ResearchReport`. Persistence stores that aggregate in normalized tables through `ResearchReportRepository`. Planner, execution, tools, and report generation remain independent of storage technology.

The architecture is ready for report history APIs, comparison, and export formats that load a persisted `ResearchReport` without re-running research.
