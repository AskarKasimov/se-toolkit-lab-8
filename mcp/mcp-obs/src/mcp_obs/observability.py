"""Async HTTP client for VictoriaLogs and VictoriaTraces APIs."""

from __future__ import annotations

from typing import Any

import httpx


class VictoriaLogsClient:
    """Client for the VictoriaLogs HTTP API (port 9428)."""

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

    async def __aenter__(self) -> VictoriaLogsClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()

    async def query_logs(
        self,
        query: str,
        *,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Search logs using LogsQL query."""
        response = await self._http_client.get(
            "/select/logsql/query",
            params={"query": query, "limit": limit},
        )
        response.raise_for_status()
        # VictoriaLogs returns newline-separated JSON objects
        results: list[dict[str, Any]] = []
        import json

        for line in response.text.strip().split("\n"):
            line = line.strip()
            if line:
                try:
                    results.append(json.loads(line))
                except json.JSONDecodeError:
                    # Some lines may be partial or malformed — skip them
                    continue
        return results

    async def count_errors(
        self,
        service: str | None = None,
        *,
        time_range: str = "1h",
    ) -> list[dict[str, Any]]:
        """Count errors per service over a time window."""
        query = f"_time:{time_range} severity:ERROR"
        if service:
            query = f'_time:{time_range} service.name:"{service}" severity:ERROR'
        return await self.query_logs(query, limit=1)


class VictoriaTracesClient:
    """Client for the VictoriaTraces HTTP API (port 10428, Jaeger-compatible)."""

    def __init__(
        self,
        base_url: str,
        *,
        http_client: httpx.AsyncClient | None = None,
        timeout: float = 10.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.AsyncClient(
            base_url=self.base_url,
            timeout=timeout,
        )

    async def __aenter__(self) -> VictoriaTracesClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        if self._owns_client:
            await self._http_client.aclose()

    async def list_traces(
        self,
        service: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """List recent traces for a service."""
        response = await self._http_client.get(
            "/select/jaeger/api/traces",
            params={"service": service, "limit": limit},
        )
        response.raise_for_status()
        data = response.json()
        # Jaeger API returns {"data": [traces]}
        return data.get("data", [])

    async def get_trace(self, trace_id: str) -> dict[str, Any] | None:
        """Fetch a specific trace by ID."""
        response = await self._http_client.get(
            f"/select/jaeger/api/traces/{trace_id}",
        )
        response.raise_for_status()
        data = response.json()
        traces = data.get("data", [])
        return traces[0] if traces else None
