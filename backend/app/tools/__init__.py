"""Tool layer — abstractions and implementations for task execution.

The tool layer sits below the execution engine and above external data sources.
Each tool implements one mechanism for completing a ResearchTask.

Exports:
    Tool              — abstract base class all tools must implement
    ToolRequest       — input value object passed to a tool
    ToolResult        — output value object returned by a tool
    ToolError         — base exception for tool failures
    PlaceholderTool   — deterministic implementation used before real tools exist
    TavilySearchTool  — production web-search tool backed by Tavily
"""

from app.tools.base import Tool
from app.tools.exceptions import ToolError
from app.tools.models import ToolRequest, ToolResult
from app.tools.placeholder import PlaceholderTool
from app.tools.tavily import TavilySearchTool

__all__ = [
    "Tool",
    "ToolError",
    "ToolRequest",
    "ToolResult",
    "PlaceholderTool",
    "TavilySearchTool",
]
