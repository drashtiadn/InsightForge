**Status:** ✅ Completed  
**Objective:** Introduce the Tool layer as a distinct architectural concern, separating the decision of *how* execution is orchestrated (engine) from the decision of *how* a task is actually completed (tool), and delegate task execution from the engine to an injected Tool implementation.

---

# Sprint Summary

Sprint 9 introduced InsightForge's Tool layer. The system could orchestrate task execution — it could sequence tasks, aggregate results, and log milestones — but the execution engine was doing both orchestration *and* the actual work of producing output. That architecture does not scale.

This sprint established the Tool abstraction. Execution now delegates work to a Tool. The engine decides when and in what order tasks run. The tool decides how each task is completed.

The implementation is deterministic and produces placeholder output. No web search, no LLM tool calls, no external I/O. The goal is to validate the full delegation pipeline — from engine to tool to result — and establish the injection seam where real tools (Tavily, vector retrieval, calculators) will later plug in.

---

# Problem Statement

Before Sprint 9, `ResearchExecutionEngine` produced output itself:

```python
output = f"Execution placeholder for task: {task.title}"
```

That string was hardcoded inside the engine. As the system grows, the engine would need to know about HTTP clients, API keys, embedding models, and database connections. Every new data source would require changing the engine. The execution layer would accumulate unrelated concerns and become untestable in isolation.

Sprint 9 addressed this by extracting the "how" of task completion into its own layer.

---

# Sprint Goals

## In Scope

- Create `app/tools/` package
- Create `Tool` abstract base class with a single `execute` method
- Create `ToolRequest` and `ToolResult` immutable value objects
- Create `ToolError` exception
- Create `PlaceholderTool` — first concrete Tool implementation
- Refactor `ResearchExecutionEngine` to accept an injected `Tool` and delegate to it
- Convert `ToolError` to `TaskExecutionError` at the engine boundary
- Wire `PlaceholderTool` into `get_execution_engine()` via dependency injection
- Structured logging at tool start, tool completion, and duration

## Out of Scope

- Tavily or any web search integration
- Google Search
- LangGraph or LangChain
- Tool selection or routing
- Multi-tool execution
- Agents or embeddings
- Vector databases
- Streaming or background workers

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
   └── _execution_engine.execute(plan)
           │
           ▼
       ExecutionEngine (ABC)
           │
           ▼
       ResearchExecutionEngine
           │  (for each task)
           ▼
       Tool (ABC)
           │
           ▼
       PlaceholderTool
           │
           ▼
       ToolResult
           │
           ▼
       ResearchTaskResult
           │
           ▼
       ResearchExecutionResult (in-memory)
```

The engine and the tool are separate objects with separate responsibilities. Neither the service nor the API knows which tool is active. The repository is completely isolated throughout.

---

# Tool Package Structure

```
app/tools/
    __init__.py       — public exports
    base.py           — Tool ABC
    models.py         — ToolRequest, ToolResult
    exceptions.py     — ToolError
    placeholder.py    — PlaceholderTool
```

---

# Tool Abstraction

## `Tool` (Abstract Base Class)

Defined in `app/tools/base.py`. Intentionally minimal:

```
execute(request: ToolRequest) -> ToolResult
```

All current and future tools implement this one method. The engine depends on this abstraction, never on a concrete class.

Tools must not:
- Call the planner
- Call the execution engine
- Write to the database
- Mutate the `ToolRequest` they receive

## Responsibility Split

| Layer | Responsibility |
|---|---|
| `ExecutionEngine` | When and in what order tasks run; aggregation; error conversion |
| `Tool` | How one task is completed; what output is produced |

These change for completely different reasons. Keeping them separate means Tavily can replace `PlaceholderTool` without touching the engine, and sequential execution can become parallel without touching any tool.

---

# Tool Models

Both models are frozen dataclasses. Neither is persisted.

## `ToolRequest`

The input a tool receives when asked to execute a task.

Fields:

- `task` — the `ResearchTask` the tool must process
- `context` — optional caller-supplied metadata (defaults to `{}`)

## `ToolResult`

The output produced by a tool for one task.

Fields:

- `task_id` — UUID matching the original task
- `output` — the text produced by the tool
- `metadata` — optional supplementary information (defaults to `{}`); future tools use this for source URLs, token counts, or confidence scores
- `completed_at` — UTC timestamp recorded by the tool when it finished

---

# PlaceholderTool

Defined in `app/tools/placeholder.py`. The first concrete `Tool` implementation.

For each task:

1. Logs tool start with tool class name, task ID, and task title
2. Produces: `"Placeholder execution for: {task.title}"`
3. Records `completed_at`
4. Logs tool completion with duration in milliseconds
5. Returns a `ToolResult` with `metadata={"tool": "PlaceholderTool"}`

No external calls. No mutations. The tool is stateless.

The output format intentionally differs from the engine's old placeholder string. This makes it easy to verify in logs that delegation is actually happening.

---

# Execution Engine Refactor

`ResearchExecutionEngine` now accepts a `Tool` at construction time:

```python
def __init__(self, tool: Tool) -> None:
    self._tool = tool
```

For each task, instead of generating a string directly, the engine:

1. Constructs a `ToolRequest(task=task)`
2. Calls `self._tool.execute(request)`
3. Receives a `ToolResult`
4. Maps `tool_result.output` and `tool_result.completed_at` into a `ResearchTaskResult`

If the tool raises `ToolError`, the engine catches it and re-raises as `TaskExecutionError`. Tool implementation details never leak above the engine boundary.

The `ExecutionEngine` public interface — `execute(plan) -> ResearchExecutionResult` — is completely unchanged. Callers above the engine see no difference.

---

# Exception Hierarchy

`app/tools/exceptions.py` defines:

- `ToolError` — base exception for all tool failures; carries `task_id` and `reason`

The engine catches `ToolError` and converts it to `TaskExecutionError` from `app/execution/exceptions.py`. This keeps the tool's error vocabulary inside the tool layer.

---

# Structured Logging

Every significant tool milestone is logged with structured context using `loguru`:

| Event | Fields |
|---|---|
| Tool started | `tool`, `task_id`, `task_title` |
| Tool completed | `tool`, `task_id`, `task_title`, `duration_ms` |

The engine's existing logging is preserved and augmented with a `tool` field identifying which tool class is active:

| Event | Fields |
|---|---|
| Execution started | `session_id`, `task_count`, `tool` |
| Task execution started | `session_id`, `task_id`, `task_title` |
| Task execution completed | `session_id`, `task_id`, `task_title` |
| Execution completed | `session_id`, `task_count`, `duration_ms` |

`print()` is never used.

---

# Dependency Injection

`get_execution_engine()` in `app/api/v1/research_sessions.py` now injects `PlaceholderTool`:

```python
def get_execution_engine() -> ExecutionEngine:
    return ResearchExecutionEngine(tool=PlaceholderTool())
```

To introduce Tavily, only this provider changes:

```python
def get_execution_engine() -> ExecutionEngine:
    return ResearchExecutionEngine(tool=TavilyTool(api_key=settings.tavily_api_key))
```

Nothing above or below the provider is affected.

---

# Key Engineering Decisions

| Decision | Alternatives Considered | Why This Was Chosen | Trade-offs |
|---|---|---|---|
| Single injected tool per engine | List of tools; tool router | Keeps the engine simple; routing is a future concern | Engine can only use one tool per plan right now |
| `ToolRequest` wraps `ResearchTask` | Pass `ResearchTask` directly to `execute()` | Stable input type; `context` dict allows future metadata without changing the ABC | Slight indirection vs passing the task directly |
| `ToolResult.metadata` as open dict | Typed fields per tool | Avoids model churn as different tools return different supplementary data | Less type safety on metadata contents |
| Synchronous `Tool.execute()` | `async def execute()` | Consistent with the synchronous engine; async adds value only when real I/O is present | Must be revisited when network calls are introduced |
| `ToolError → TaskExecutionError` conversion at engine boundary | Let `ToolError` propagate | Tool internals stay inside the tool layer; callers only see execution exceptions | Slight loss of original exception detail (mitigated by `from exc` chaining) |
| `PlaceholderTool` output differs from old engine string | Same string as before | Makes delegation visible in logs; confirms tool is actually being called | Minor inconsistency with Sprint 8 output format |

---

# Validation

The implementation was validated by:

- confirming `ExecutionEngine.execute()` interface is unchanged
- confirming `ResearchExecutionEngine` no longer contains any placeholder string logic
- confirming `PlaceholderTool.execute()` produces all output
- confirming the engine depends only on `Tool`, never on `PlaceholderTool` directly
- confirming `PlaceholderTool` is injected at the API layer, not instantiated inside the engine
- confirming no external API calls are made anywhere in the tool layer
- confirming no OpenAPI schema changes were introduced
- confirming no database writes occur
- checking all touched files for linter diagnostics

---

# Challenges & Learnings

| Challenge | Solution | Learning |
|---|---|---|
| Temptation to put tool selection inside the engine | Kept a single injected tool; routing deferred | Tool selection is a separate concern that belongs in a router or agent, not the engine |
| Temptation to pass `ResearchTask` directly to `execute()` | Introduced `ToolRequest` as a wrapper | A dedicated input type gives tools a stable contract and room to grow |
| Deciding what `PlaceholderTool` output format to use | Slightly different string from the engine's old format | Placeholder output should make delegation visible in logs, not invisible |
| `ToolError` leaking above the engine | Engine catches and re-raises as `TaskExecutionError` | Each layer should speak its own exception vocabulary; conversion happens at the boundary |
| Async vs sync tool interface | Kept synchronous | Add async only when there is real I/O to await; premature async adds complexity without benefit |

---

# Deliverables

- `app/tools/__init__.py`
- `app/tools/base.py` — `Tool` ABC
- `app/tools/models.py` — `ToolRequest`, `ToolResult`
- `app/tools/exceptions.py` — `ToolError`
- `app/tools/placeholder.py` — `PlaceholderTool`
- Updated `app/execution/engine.py` — `ResearchExecutionEngine` accepts injected `Tool`, delegates via `ToolRequest`/`ToolResult`
- Updated `app/api/v1/research_sessions.py` — `get_execution_engine()` injects `PlaceholderTool`

---

# Outcome

Sprint 9 completed InsightForge's Tool layer. The execution engine no longer contains any application logic. It orchestrates — it sequences tasks, converts errors, aggregates results, and logs milestones. The tool works — it produces output for each task.

The injection seam is now in place. Introducing Tavily, a vector retrieval tool, or a calculator requires writing one class that implements `Tool.execute()` and changing one line in `get_execution_engine()`. The engine, service, repository, and API are untouched.

The architecture is now ready for real tool implementations and, eventually, agent-controlled tool selection.
