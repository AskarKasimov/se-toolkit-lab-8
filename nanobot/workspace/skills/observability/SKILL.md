---
name: observability
description: Use observability MCP tools to investigate errors, logs, and traces
always: true
---

# Observability Skill

Use observability MCP tools to investigate errors, logs, and traces from the LMS backend and other services. This skill teaches the agent how to diagnose problems using structured logging and distributed tracing.

## Available Tools

| Tool | Parameters | Description |
|------|------------|-------------|
| `obs_logs_search` | `query` (LogsQL string), `limit` (int, default 50) | Search structured logs using LogsQL. Use to find log entries by service, severity, time range, or keywords. |
| `obs_logs_error_count` | `service` (string, optional), `time_range` (string, default "1h") | Count error-level log entries for a service over a time window. Quick check for recent errors. |
| `obs_traces_list` | `service` (string), `limit` (int, default 20) | List recent traces for a service. Returns trace IDs, span counts, and durations. |
| `obs_traces_get` | `trace_id` (string) | Fetch a full trace by trace ID. Returns span hierarchy with operation names and durations. |

## Strategy

### When the user asks "What went wrong?" or "Check system health"

Perform a **full one-shot investigation** automatically — do not ask the user for permission between steps:

1. **Start with `obs_logs_error_count`** — get a quick count of recent errors scoped to the LMS backend and a narrow recent window (prefer `_time:10m`).
2. **If errors > 0, use `obs_logs_search`** — dig into the actual error log entries. Use `_time:10m service.name:"Learning Management Service" severity:ERROR`. Look for `trace_id` fields in error records.
3. **Always fetch the matching trace** — if you find a `trace_id` in the logs, immediately call `obs_traces_get` with that trace ID. Do not ask the user whether to do this.
4. **Summarize findings concisely in one coherent report** — don't dump raw JSON. Present:
   - What failed (service name, operation)
   - Log evidence (timestamp, event, error message)
   - Trace evidence (trace ID, which span failed, error tags)
   - Root cause hypothesis

### When the user asks about errors or problems (general)

1. **Start with `obs_logs_error_count`** — get a quick count of recent errors scoped to the service and time window the user cares about.
2. **If errors exist, use `obs_logs_search`** — dig into the actual log entries to understand what happened. Look for `trace_id` fields in error records.
3. **If you find a trace ID, use `obs_traces_get`** — fetch the full trace to see where the failure occurred in the request flow.
4. **Summarize findings concisely** — don't dump raw JSON. Present a short summary: what failed, when, and where in the trace.

### LogsQL query patterns

Useful LogsQL patterns for this stack:

```
_time:10m service.name:"Learning Management Service" severity:ERROR
_time:1h severity:ERROR
_time:30m trace_id:"abc123..."
```

Field names that matter:
- `service.name` — which service emitted the log
- `severity` — log level (ERROR, INFO, DEBUG, etc.)
- `event` — structured event name (e.g., `db_query`, `request_completed`)
- `trace_id` — links logs to traces

### When to search traces directly

Use `obs_traces_list` when:
- The user asks "what happened to my request?"
- You need to find a trace ID that wasn't in the logs
- Comparing healthy vs error request patterns

### Time window scoping

**Always scope queries to a recent, narrow time window** when the user asks about current problems:
- Prefer `_time:10m` over `_time:1h` for "right now" questions
- Include the service name to avoid noise from other services
- If the user asks about a specific incident, match the time window to when it happened

### Formatting responses

- **Error counts**: "Found N error(s) for service 'X' in the last Y minutes."
- **Log search results**: Summarize key fields (timestamp, service, event, error message) from each entry. Don't dump full JSON.
- **Trace results**: Show the span hierarchy with durations, highlighting where errors occurred.
- **No results**: "No errors found for service 'X' in the last Y minutes." — be specific about the scope.

### When to use structured-ui

If multiple traces or log entries are found and the user needs to pick one, use the `structured-ui` skill to present a choice interface instead of listing them as text.

## Limits

- Read-only: cannot modify logs or traces
- VictoriaLogs and VictoriaTraces retain data for 7 days (configured in docker-compose)
- Large time windows may return many results — use `limit` parameter to cap output
