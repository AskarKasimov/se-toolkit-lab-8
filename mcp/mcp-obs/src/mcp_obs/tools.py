"""Tool schemas, handlers, and registry for the observability MCP server."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from typing import Any

from mcp.types import Tool
from pydantic import BaseModel, Field

from mcp_obs.observability import VictoriaLogsClient, VictoriaTracesClient


class LogsSearchParams(BaseModel):
    query: str = Field(
        description="LogsQL query string, e.g. '_time:10m service.name:\"Learning Management Service\" severity:ERROR'"
    )
    limit: int = Field(
        default=50,
        ge=1,
        le=500,
        description="Max number of log entries to return (default 50).",
    )


class LogsErrorCountParams(BaseModel):
    service: str = Field(
        default="",
        description="Service name to filter errors (e.g. 'Learning Management Service'). Leave empty for all services.",
    )
    time_range: str = Field(
        default="1h",
        description="Time window for error count, e.g. '10m', '1h', '24h' (default '1h').",
    )


class TracesListParams(BaseModel):
    service: str = Field(description="Service name to list traces for.")
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Max number of traces to return (default 20).",
    )


class TracesGetParams(BaseModel):
    trace_id: str = Field(description="Trace ID to fetch, e.g. 'abc123def456'.")


ToolPayload = BaseModel | Sequence[BaseModel] | dict[str, Any] | list[Any] | str
ToolHandler = Callable[
    [VictoriaLogsClient, VictoriaTracesClient, BaseModel], Awaitable[ToolPayload]
]


@dataclass(frozen=True, slots=True)
class ToolSpec:
    name: str
    description: str
    model: type[BaseModel]
    handler: ToolHandler

    def as_tool(self) -> Tool:
        schema = self.model.model_json_schema()
        schema.pop("$defs", None)
        schema.pop("title", None)
        return Tool(name=self.name, description=self.description, inputSchema=schema)


async def _logs_search(
    logs_client: VictoriaLogsClient,
    _traces_client: VictoriaTracesClient,
    args: BaseModel,
) -> ToolPayload:
    params = _require_logs_search_params(args)
    results = await logs_client.query_logs(params.query, limit=params.limit)
    if not results:
        return "No logs found matching the query."
    # Return concise summary instead of raw JSON
    return json.dumps(results, indent=2, ensure_ascii=False)


async def _logs_error_count(
    logs_client: VictoriaLogsClient,
    _traces_client: VictoriaTracesClient,
    args: BaseModel,
) -> ToolPayload:
    params = _require_error_count_params(args)
    service = params.service if params.service else None
    results = await logs_client.count_errors(service, time_range=params.time_range)
    count = len(results)
    if service:
        return f"Found {count} error(s) for service '{service}' in the last {params.time_range}."
    return f"Found {count} error(s) across all services in the last {params.time_range}."


async def _traces_list(
    _logs_client: VictoriaLogsClient,
    traces_client: VictoriaTracesClient,
    args: BaseModel,
) -> ToolPayload:
    params = _require_traces_list_params(args)
    results = await traces_client.list_traces(params.service, limit=params.limit)
    if not results:
        return f"No traces found for service '{params.service}'."
    # Return trace summaries instead of full data
    summaries = []
    for trace in results[:10]:  # Limit display to first 10
        trace_id = trace.get("traceID", "")
        spans = trace.get("spans", [])
        duration_ms = _calculate_trace_duration_ms(trace)
        summaries.append(
            {
                "trace_id": trace_id,
                "spans": len(spans),
                "duration_ms": duration_ms,
                "start_time": spans[0].get("startTime", "") if spans else "",
            }
        )
    return json.dumps(summaries, indent=2, ensure_ascii=False)


async def _traces_get(
    _logs_client: VictoriaLogsClient,
    traces_client: VictoriaTracesClient,
    args: BaseModel,
) -> ToolPayload:
    params = _require_traces_get_params(args)
    trace = await traces_client.get_trace(params.trace_id)
    if not trace:
        return f"No trace found with ID '{params.trace_id}'."
    # Return trace with span hierarchy summary
    spans = trace.get("spans", [])
    span_summary = {
        "trace_id": trace.get("traceID", ""),
        "total_spans": len(spans),
        "duration_ms": _calculate_trace_duration_ms(trace),
        "spans": [
            {
                "operation": span.get("operationName", ""),
                "service": span.get("processID", ""),
                "duration_ms": span.get("duration", 0),
                "tags": span.get("tags", []),
            }
            for span in spans
        ],
    }
    return json.dumps(span_summary, indent=2, ensure_ascii=False)


def _calculate_trace_duration_ms(trace: dict[str, Any]) -> float:
    """Calculate total trace duration in milliseconds from span data."""
    spans = trace.get("spans", [])
    if not spans:
        return 0
    # Find the earliest start time and latest end time
    start_times = [span.get("startTime", 0) for span in spans]
    durations = [span.get("duration", 0) for span in spans]
    if not start_times or not durations:
        return 0
    earliest_start = min(start_times)
    latest_end = max(s + d for s, d in zip(start_times, durations))
    return latest_end - earliest_start


def _require_logs_search_params(args: BaseModel) -> LogsSearchParams:
    if not isinstance(args, LogsSearchParams):
        raise TypeError(f"Expected {LogsSearchParams.__name__}, got {type(args).__name__}")
    return args


def _require_error_count_params(args: BaseModel) -> LogsErrorCountParams:
    if not isinstance(args, LogsErrorCountParams):
        raise TypeError(
            f"Expected {LogsErrorCountParams.__name__}, got {type(args).__name__}"
        )
    return args


def _require_traces_list_params(args: BaseModel) -> TracesListParams:
    if not isinstance(args, TracesListParams):
        raise TypeError(
            f"Expected {TracesListParams.__name__}, got {type(args).__name__}"
        )
    return args


def _require_traces_get_params(args: BaseModel) -> TracesGetParams:
    if not isinstance(args, TracesGetParams):
        raise TypeError(f"Expected {TracesGetParams.__name__}, got {type(args).__name__}")
    return args


TOOL_SPECS = (
    ToolSpec(
        "obs_logs_search",
        "Search structured logs using LogsQL query. Use this to find log entries by service, severity, time range, or keywords.",
        LogsSearchParams,
        _logs_search,
    ),
    ToolSpec(
        "obs_logs_error_count",
        "Count error-level log entries for a service over a time window. Use this to quickly check for recent errors.",
        LogsErrorCountParams,
        _logs_error_count,
    ),
    ToolSpec(
        "obs_traces_list",
        "List recent traces for a service. Returns trace IDs, span counts, and durations.",
        TracesListParams,
        _traces_list,
    ),
    ToolSpec(
        "obs_traces_get",
        "Fetch a full trace by trace ID. Returns the span hierarchy with operation names and durations.",
        TracesGetParams,
        _traces_get,
    ),
)
TOOLS_BY_NAME = {spec.name: spec for spec in TOOL_SPECS}
