# InsightForge

InsightForge is a production-oriented AI research platform being built step by step with clear architectural boundaries between API, service, planning, repository, and database layers.

## Current Backend Progress

The backend currently supports:

- creating research sessions
- retrieving one or many research sessions
- starting research workflow execution
- validating explicit lifecycle state transitions
- decomposing research queries into structured task plans
- generating plans using a deterministic heuristic planner or Google Gemini

Current workflow:

`PENDING -> PLANNING -> RESEARCHING -> REPORT_GENERATION -> COMPLETED`

Failure paths currently supported:

- `RESEARCHING -> FAILED`
- `REPORT_GENERATION -> FAILED`

## Architecture

```
Client -> API -> Service -> Planner -> (ResearchPlan, in memory)
                    |
                    v
              Repository -> Database
```

- `API` handles HTTP input/output and status-code mapping
- `Service` owns business rules, workflow validation, and transactions
- `Planner` decomposes research queries into task lists (no persistence)
- `Repository` persists and retrieves data only
- `Database` stores durable research session state

## Planner Configuration

Set in `.env`:

```env
# simple = deterministic heuristics (default, no API key needed)
# llm    = Google Gemini-backed planning
PLANNER_TYPE=simple

GEMINI_API_KEY=your-key-here
LLM_MODEL=gemini-2.0-flash
LLM_TEMPERATURE=0.2
```

## Documentation

Sprint documentation lives in `docs/`.

- `docs/Sprint 0 – Project Foundation.md`
- `docs/Sprint 1 – Application Infrastructure.md`
- `docs/Sprint 2 – Persistence Infrastructure.md`
- `docs/Sprint 3 – ResearchSession Domain Model.md`
- `docs/Sprint 4 – ResearchSession REST API.md`
- `docs/Sprint 5 – Research Workflow.md`
- `docs/Sprint 6 – Research Planning Layer.md`
- `docs/Sprint 7 – LLM Research Planner.md`
- `docs/Sprint 8 – Execution Layer.md`
- `docs/Sprint 9 – Tool Layer.md`
- `docs/Sprint 10 – Tavily Search Tool.md`
- `docs/Sprint 11 – Reporting Layer.md`
