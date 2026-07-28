**Status:** ✅ Completed  
**Objective:** Introduce InsightForge’s first business domain entity—`ResearchSession`—with a typed ORM model, lifecycle status enum, initial Alembic migration, and a dedicated repository for persistence, without exposing API endpoints or business workflows yet.

---

# Sprint Summary

Sprint 3 focused on domain modeling and data persistence for research sessions. With async SQLAlchemy and Alembic available from Sprint 2, this sprint defined *what* the system stores and *how* it is accessed—while deliberately postponing HTTP APIs, services, and AI orchestration.

The result is a working persistence layer around a single aggregate: `ResearchSession`. Future sprints can build APIs and workflows on top of this contract without redesigning the data model.

---

# Problem Statement

Sprint 2 provided database connectivity and migration tooling, but the schema was empty and no domain concepts existed in code. InsightForge’s core unit of work—a research session that moves through planning, research, and report generation—had no durable representation.

Without a model, migration, and repository:

- There is nowhere to store a user’s research request
- Lifecycle status cannot be tracked reliably
- Higher layers (API, services, agents) have no persistence boundary to depend on

Sprint 3 addressed this by introducing the first aggregate and a thin data-access layer.

---

# Sprint Goals

## In Scope

- Create the `ResearchSession` ORM model
- Define a `ResearchSessionStatus` lifecycle enum
- Organize models under `app/models/`
- Register models with Alembic metadata discovery
- Generate the initial migration for `research_sessions`
- Create `ResearchSessionRepository` with `create`, `get_by_id`, and `list`
- Reuse `get_db()` / `AsyncSession` for dependency injection

## Out of Scope

- API endpoints
- Service layer
- Background jobs
- AI agents / LangGraph
- Redis
- Authentication / authorization
- Report generation
- Vector database
- Celery
- Business workflow transitions

---

# Architecture Snapshot

```
API (not yet)
   │
   ▼
Repository  ◄── ResearchSessionRepository
   │
   ▼
Models      ◄── ResearchSession + ResearchSessionStatus
   │
   ▼
Database    ◄── PostgreSQL (research_sessions + enum)
```

Layering remains intentionally shallow:

```
API → Repository → Database
```

Business logic will sit between API and Repository in a later sprint.

Project Structure

```text
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       └── cee8f2d5b2f3_create_research_sessions_table.py
└── app/
    ├── database/
    │   ├── base.py
    │   └── session.py
    ├── models/
    │   ├── __init__.py
    │   └── research_session.py
    └── repositories/
        ├── __init__.py
        └── research_session_repository.py
```

---

# Implementation

## ResearchSession Model

Created `app/models/research_session.py` using SQLAlchemy 2.0 typed ORM (`Mapped` / `mapped_column`).

Fields:

| Field | Purpose |
|-------|---------|
| `id` | UUID primary key |
| `title` | Short session label (`String(255)`) |
| `query` | Full research prompt (`Text`) |
| `status` | Lifecycle state (PostgreSQL enum) |
| `created_at` | Timezone-aware creation timestamp |
| `updated_at` | Timezone-aware last-update timestamp |

**Why?**

A research session is the aggregate root for InsightForge’s core workflow. Persisting it first establishes the data contract every later feature depends on.

---

## Status Enum

Introduced `ResearchSessionStatus` with:

- `PENDING`
- `PLANNING`
- `RESEARCHING`
- `REPORT_GENERATION`
- `COMPLETED`
- `FAILED`

**Why an enum instead of free-text?**

- Database-level integrity (invalid values are rejected)
- Self-documenting allowed states
- Stronger typing in Python
- Safer refactors via migrations instead of silent string drift

---

## Model Package Organization

Added `app/models/` and imported models in `alembic/env.py` so they register on `Base.metadata`.

**Why?**

Alembic only migrates what appears in metadata. Defining a model file is not enough—modules must be imported for discovery.

---

## Initial Alembic Migration

Created revision `cee8f2d5b2f3` to:

- Create the `research_session_status` enum type
- Create the `research_sessions` table
- Enforce the UUID primary key and NOT NULL constraints
- Apply server defaults for `status`, `created_at`, and `updated_at`
- Drop table and enum cleanly on downgrade

**Why?**

Schema changes must be reproducible across local and future deployed environments.

---

## ResearchSession Repository

Created `ResearchSessionRepository` with persistence-only methods:

- `create()` — insert and return the ORM instance
- `get_by_id()` — fetch by UUID or return `None`
- `list()` — return sessions ordered by newest first

The repository receives an `AsyncSession` in its constructor. No global sessions or singleton repositories.

**Why?**

Repositories isolate SQL/ORM details behind a small API so routes and services do not scatter query logic. Business validation and workflow rules stay out of this layer.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|-----------|-------------------------|---------------------|------------|
| UUID primary keys | Auto-increment integers | Non-guessable; safe for distributed creation; portable across systems | Slightly larger indexes; less human-readable |
| Native PostgreSQL enum | Free-text `VARCHAR` / integer codes | Enforces lifecycle integrity at the DB and type layers | Enum changes require migrations |
| Dedicated repository (no generic base) | `BaseRepository[T]`, generic CRUD helpers | One aggregate → one explicit class; easier to read | Some repeated patterns across future repos |
| Commit inside `create()` | Caller-managed unit of work | Simple and correct with current `get_db()` (no auto-commit) | Multi-entity transactions may later move commit upward |
| Models stay persistence-focused | Rich domain methods on the ORM class | Keeps table mapping separate from workflow logic | Domain behavior lives in a future service layer |
| No API yet | REST endpoints in the same sprint | Validates persistence independently of HTTP design | Manual/scripted validation until Sprint 4 |

---

# Validation

The implementation was validated by:

- Model registration on `Base.metadata`
- Successful `alembic upgrade head` against PostgreSQL
- Presence of `research_sessions` and `research_session_status`
- Repository `create()` persisting rows with UUID primary keys
- Repository `get_by_id()` retrieving persisted sessions
- Repository `list()` returning created records
- Python compilation / import checks for new modules

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|------------|----------|----------|
| Alembic autogenerate failed until DB credentials were correct | Fixed `DATABASE_URL`, then applied the migration | Autogenerate and upgrades need a live, authenticated database |
| Stale shell `DATABASE_URL` overrode `.env` | Cleared the environment variable so Settings loaded from `.env` | Process env vars take precedence over `env_file` in pydantic-settings |
| Temptation to add services/APIs early | Kept the sprint to model + migration + repository | Persist the domain before designing HTTP or workflows |
| Risk of generic repository abstractions | Implemented one concrete repository | Prefer explicit code until duplication proves a shared base is needed |

---

# Deliverables

- `ResearchSession` ORM model
- `ResearchSessionStatus` enum
- `app/models` package with Alembic discovery wiring
- Initial `research_sessions` migration
- `ResearchSessionRepository` (`create`, `get_by_id`, `list`)
- Working persistence layer validated against PostgreSQL
- No API endpoints or business workflow logic

---

# Outcome

Sprint 3 successfully introduced InsightForge’s first business domain and a working persistence path for it.

The system can now store and retrieve research sessions with typed lifecycle status, versioned schema history, and a clean repository boundary. Higher-level features—APIs, services, and agent workflows—can build on this foundation without revisiting the core data model.

---

# Next Sprint

Sprint 4 should introduce the first API and/or service layer for research sessions, building on the existing model and repository without redesigning the persistence stack.
