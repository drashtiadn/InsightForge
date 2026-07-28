# InsightForge

InsightForge is a production-oriented research platform being built step by step with clear architectural boundaries between API, service, repository, and database layers.

## Current Backend Progress

The backend currently supports:

- creating research sessions
- retrieving one or many research sessions
- starting research workflow execution
- validating explicit lifecycle state transitions

Current workflow:

`PENDING -> PLANNING -> RESEARCHING -> REPORT_GENERATION -> COMPLETED`

Failure paths currently supported:

- `RESEARCHING -> FAILED`
- `REPORT_GENERATION -> FAILED`

## Architecture

The project currently follows this application flow:

`Client -> API -> Service -> Repository -> Database`

- `API` handles HTTP input/output and status-code mapping
- `Service` owns business rules, workflow validation, and transactions
- `Repository` persists and retrieves data only
- `Database` stores the durable research session state

## Documentation

Sprint documentation lives in `docs/`.

- `docs/Sprint 0 – Project Foundation.md`
- `docs/Sprint 1 – Application Infrastructure.md`
- `docs/Sprint 2 – Persistence Infrastructure.md`
- `docs/Sprint 3 – ResearchSession Domain Model.md`
- `docs/Sprint 4 – ResearchSession REST API.md`
- `docs/Sprint 5 – Research Workflow.md`
