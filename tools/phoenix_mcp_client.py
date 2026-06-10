"""PhoenixGuard — Phoenix MCP Client Layer (Phase 2 Upgrade).

This module isolates all interactions with Phoenix Cloud. It attempts to connect
to the official Arize Phoenix MCP Server using ``PhoenixMCPAdapter``. If that fails
or is not configured, it falls back to the REST client using ``PhoenixTools`` from
``tools/phoenix_tools.py``. If both fail, it falls back gracefully to high-fidelity
mock data.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# Set up logging
logger = logging.getLogger(__name__)

# Try to import real PhoenixTools
try:
    from tools.phoenix_tools import PhoenixTools
except ImportError:
    PhoenixTools = None  # type: ignore[assignment, misc]

# Try to import MCP Adapter
try:
    from tools.phoenix_mcp_adapter import PhoenixMCPAdapter
except ImportError:
    PhoenixMCPAdapter = None  # type: ignore[assignment, misc]


# ────────────────────────────────────────────────────────────────────
# High-Fidelity Mock Data Generator
# ────────────────────────────────────────────────────────────────────

def _get_mock_traces(limit: int = 20) -> List[Dict[str, Any]]:
    """Generate high-fidelity mock traces representing realistic agent execution.

    Contains a mix of:
    - Successful tool runs
    - High-latency tool runs (latency > 5.0 seconds)
    - Tool failures (AccessDenied error in get_system_health)
    - Excessive token consumption runs (> 8,000 tokens)
    """
    now = datetime.now(timezone.utc)
    
    traces = [
        # Trace 1: Successful weather query
        {
            "id": "VHJhY2U6MTAx",
            "trace_id": "a1b2c3d4e5f67890a1b2c3d4e5f67890",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=5)).isoformat(),
            "end_time": (now - timedelta(minutes=5, seconds=2)).isoformat(),
            "token_count_prompt": 1450,
            "token_count_completion": 180,
            "token_count_total": 1630,
            "spans": [
                {
                    "id": "U3BhbjoxMDAx",
                    "span_id": "1001",
                    "parent_id": None,
                    "name": "invocation [phoenixguard]",
                    "span_kind": "CHAIN",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=5)).isoformat(),
                    "end_time": (now - timedelta(minutes=5, seconds=2)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMDAy",
                    "span_id": "1002",
                    "parent_id": "1001",
                    "name": "agent_run [phoenixguard_agent]",
                    "span_kind": "AGENT",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=5)).isoformat(),
                    "end_time": (now - timedelta(minutes=5, seconds=2)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMDAz",
                    "span_id": "1003",
                    "parent_id": "1002",
                    "name": "call_llm",
                    "span_kind": "LLM",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=5)).isoformat(),
                    "end_time": (now - timedelta(minutes=5, seconds=1)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMDA4",
                    "span_id": "1004",
                    "parent_id": "1002",
                    "name": "execute_tool get_weather",
                    "span_kind": "TOOL",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=5, seconds=1)).isoformat(),
                    "end_time": (now - timedelta(minutes=5, seconds=1, milliseconds=500)).isoformat(),
                }
            ]
        },
        # Trace 2: High latency trace (Slow Weather API)
        {
            "id": "VHJhY2U6MTAy",
            "trace_id": "b2c3d4e5f67890a1b2c3d4e5f67890a1",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=10)).isoformat(),
            "end_time": (now - timedelta(minutes=10) + timedelta(seconds=8)).isoformat(),
            "token_count_prompt": 1500,
            "token_count_completion": 210,
            "token_count_total": 1710,
            "spans": [
                {
                    "id": "U3BhbjoxMTAx",
                    "span_id": "1101",
                    "parent_id": None,
                    "name": "invocation [phoenixguard]",
                    "span_kind": "CHAIN",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=10)).isoformat(),
                    "end_time": (now - timedelta(minutes=10) + timedelta(seconds=8)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMTAy",
                    "span_id": "1102",
                    "parent_id": "1101",
                    "name": "agent_run [phoenixguard_agent]",
                    "span_kind": "AGENT",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=10)).isoformat(),
                    "end_time": (now - timedelta(minutes=10) + timedelta(seconds=8)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMTAz",
                    "span_id": "1103",
                    "parent_id": "1102",
                    "name": "execute_tool get_weather",
                    "span_kind": "TOOL",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=10, seconds=1)).isoformat(),
                    "end_time": (now - timedelta(minutes=10, seconds=7)).isoformat(),  # Takes 6 seconds!
                }
            ]
        },
        # Trace 3: Tool failure (Access Denied on system health)
        {
            "id": "VHJhY2U6MTAz",
            "trace_id": "c3d4e5f67890a1b2c3d4e5f67890a1b2",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=15)).isoformat(),
            "end_time": (now - timedelta(minutes=15, seconds=1)).isoformat(),
            "token_count_prompt": 1200,
            "token_count_completion": 80,
            "token_count_total": 1280,
            "spans": [
                {
                    "id": "U3BhbjoxMjAx",
                    "span_id": "1201",
                    "parent_id": None,
                    "name": "invocation [phoenixguard]",
                    "span_kind": "CHAIN",
                    "status_code": "ERROR",
                    "start_time": (now - timedelta(minutes=15)).isoformat(),
                    "end_time": (now - timedelta(minutes=15, seconds=1)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMjAy",
                    "span_id": "1202",
                    "parent_id": "1201",
                    "name": "agent_run [phoenixguard_agent]",
                    "span_kind": "AGENT",
                    "status_code": "ERROR",
                    "start_time": (now - timedelta(minutes=15)).isoformat(),
                    "end_time": (now - timedelta(minutes=15, seconds=1)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMjAz",
                    "span_id": "1203",
                    "parent_id": "1202",
                    "name": "execute_tool get_system_health",
                    "span_kind": "TOOL",
                    "status_code": "ERROR",
                    "start_time": (now - timedelta(minutes=15, milliseconds=500)).isoformat(),
                    "end_time": (now - timedelta(minutes=15, milliseconds=900)).isoformat(),
                    "status_message": "psutil.AccessDenied: CPU times could not be retrieved due to insufficient OS privileges"
                }
            ]
        },
        # Trace 4: Excessive token usage
        {
            "id": "VHJhY2U6MTA0",
            "trace_id": "d4e5f67890a1b2c3d4e5f67890a1b2c3",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=20)).isoformat(),
            "end_time": (now - timedelta(minutes=20, seconds=4)).isoformat(),
            "token_count_prompt": 9500,
            "token_count_completion": 1200,
            "token_count_total": 10700,
            "spans": [
                {
                    "id": "U3BhbjoxMzAx",
                    "span_id": "1301",
                    "parent_id": None,
                    "name": "invocation [phoenixguard]",
                    "span_kind": "CHAIN",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=20)).isoformat(),
                    "end_time": (now - timedelta(minutes=20, seconds=4)).isoformat(),
                },
                {
                    "id": "U3BhbjoxMzAy",
                    "span_id": "1302",
                    "parent_id": "1301",
                    "name": "call_llm",
                    "span_kind": "LLM",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=20)).isoformat(),
                    "end_time": (now - timedelta(minutes=20, seconds=4)).isoformat(),
                }
            ]
        },
        # Trace 5: Successful system health query
        {
            "id": "VHJhY2U6MTA1",
            "trace_id": "e5f67890a1b2c3d4e5f67890a1b2c3d4",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=25)).isoformat(),
            "end_time": (now - timedelta(minutes=25, seconds=2)).isoformat(),
            "token_count_prompt": 1300,
            "token_count_completion": 140,
            "token_count_total": 1440,
            "spans": [
                {
                    "id": "U3BhbjoxNDAx",
                    "span_id": "1401",
                    "parent_id": None,
                    "name": "invocation [phoenixguard]",
                    "span_kind": "CHAIN",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=25)).isoformat(),
                    "end_time": (now - timedelta(minutes=25, seconds=2)).isoformat(),
                },
                {
                    "id": "U3BhbjoxNDAy",
                    "span_id": "1402",
                    "parent_id": "1401",
                    "name": "execute_tool get_system_health",
                    "span_kind": "TOOL",
                    "status_code": "OK",
                    "start_time": (now - timedelta(minutes=25, seconds=1)).isoformat(),
                    "end_time": (now - timedelta(minutes=25, seconds=1, milliseconds=300)).isoformat(),
                }
            ]
        }
    ]
    return traces[:limit]


def _get_mock_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Generate high-fidelity mock sessions."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "c2Vzc2lvbjox",
            "session_id": "session-weather-analysis-01",
            "project_id": "UHJvamVjdDoz",
            "start_time": (now - timedelta(minutes=30)).isoformat(),
            "end_time": now.isoformat(),
            "token_count_prompt": 14950,
            "token_count_completion": 1810,
            "token_count_total": 16760
        }
    ][:limit]


def _get_mock_prompts() -> List[Dict[str, Any]]:
    """Generate mock prompt data templates."""
    return [
        {
            "name": "system_instruction",
            "version": "1.0",
            "template": (
                "You are **PhoenixGuard**, an AI Reliability Engineer built for production observability. "
                "You can monitor your own traces and analyze agent performance..."
            )
        },
        {
            "name": "weather_prompt",
            "version": "1.2",
            "template": "What is the weather in {{city}}? Output JSON containing temperature and condition."
        }
    ]


def _get_mock_experiments() -> List[Dict[str, Any]]:
    """Generate mock experiments data."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "ZXhwZXJpbWVudDox",
            "name": "gemini-2.5-flash-vs-gemini-1.5-pro",
            "dataset_id": "ZGF0YXNldDox",
            "repetitions": 1,
            "project_name": "phoenixguard",
            "created_at": (now - timedelta(days=2)).isoformat(),
            "example_count": 20,
            "successful_run_count": 18,
            "failed_run_count": 2
        }
    ]


def _get_mock_datasets() -> List[Dict[str, Any]]:
    """Generate mock dataset structures."""
    now = datetime.now(timezone.utc)
    return [
        {
            "id": "ZGF0YXNldDox",
            "name": "reliability-eval-dataset",
            "description": "Evaluation dataset containing standard queries and expected responses for weather and system health metrics",
            "example_count": 20,
            "created_at": (now - timedelta(days=2)).isoformat(),
            "updated_at": (now - timedelta(days=2)).isoformat()
        }
    ]


# ────────────────────────────────────────────────────────────────────
# Phoenix MCP Client API Layer
# ────────────────────────────────────────────────────────────────────

class PhoenixMCPClient:
    """Isolates all operations with Phoenix Cloud, supporting mock fallbacks."""

    def __init__(self) -> None:
        self._use_mock = os.getenv("PHOENIX_USE_MOCK", "false").lower() == "true"
        self._real_client: Optional[Any] = None
        self._mcp_adapter: Optional[Any] = None
        self._data_source = "MOCK_DATA"

        if self._use_mock:
            logger.info("PhoenixMCPClient: Explicitly configured to use MOCK mode. Data source: MOCK_DATA")
            self._data_source = "MOCK_DATA"
            print("[PhoenixMCPClient] Active backend: MOCK")
            return

        # 1. Try to connect via official Arize Phoenix MCP Server (Arize Track compliance)
        if PhoenixMCPAdapter is not None:
            try:
                self._mcp_adapter = PhoenixMCPAdapter()
                self._data_source = "LIVE_PHOENIX"
                logger.info("PhoenixMCPClient: Connected via Arize Phoenix MCP Server. Data source: LIVE_PHOENIX")
                print("[PhoenixMCPClient] Active backend: MCP")
                return
            except Exception as mcp_exc:
                logger.info(
                    "PhoenixMCPClient: MCP Adapter initialization skipped or failed: %s. Trying SDK fallback.",
                    mcp_exc,
                )

        # 2. Try SDK-based fallback (PhoenixTools REST Client)
        if PhoenixTools is not None:
            try:
                api_key = os.getenv("PHOENIX_API_KEY", "")
                base_url = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "")
                
                if not api_key or not base_url:
                    logger.warning("PhoenixMCPClient: Connection credentials missing. Falling back to MOCK_DATA.")
                    self._use_mock = True
                    self._data_source = "MOCK_DATA"
                    print("[PhoenixMCPClient] Active backend: MOCK")
                else:
                    self._real_client = PhoenixTools()
                    self._data_source = "LIVE_PHOENIX"
                    logger.info("PhoenixMCPClient: Connected via SDK client. Data source: LIVE_PHOENIX")
                    print("[PhoenixMCPClient] Active backend: SDK")
            except Exception as exc:
                logger.warning(
                    "PhoenixMCPClient: Failed to initialize SDK client (%s). Falling back to MOCK_DATA.",
                    exc,
                )
                self._use_mock = True
                self._data_source = "MOCK_DATA"
                print("[PhoenixMCPClient] Active backend: MOCK")
        else:
            logger.warning("PhoenixMCPClient: PhoenixTools is not available. Falling back to MOCK_DATA.")
            self._use_mock = True
            self._data_source = "MOCK_DATA"
            print("[PhoenixMCPClient] Active backend: MOCK")

    @property
    def data_source(self) -> str:
        """Get the active data source identifier: 'LIVE_PHOENIX' or 'MOCK_DATA'."""
        return self._data_source

    def get_recent_traces(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent traces. Routing through MCP tool with SDK and mock fallbacks."""
        if self._use_mock:
            return _get_mock_traces(limit)

        # A. Try MCP
        if self._mcp_adapter is not None:
            try:
                traces = self._mcp_adapter.get_recent_traces(limit=limit)
                if traces:
                    logger.info("PhoenixMCPClient: Successfully retrieved traces via MCP server.")
                    return traces
            except Exception as exc:
                logger.warning("PhoenixMCPClient: MCP list-traces tool failed: %s. Falling back to SDK.", exc)

        # B. Try SDK Fallback
        if self._real_client is not None:
            try:
                traces = self._real_client.get_recent_traces(limit=limit, include_spans=True)
                if traces and not (len(traces) == 1 and "error" in traces[0]):
                    logger.info("PhoenixMCPClient: Successfully retrieved traces via SDK fallback.")
                    return traces
            except Exception as exc:
                logger.warning("PhoenixMCPClient: SDK get_recent_traces failed: %s. Falling back to mocks.", exc)

        return _get_mock_traces(limit)

    def get_recent_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Retrieve recent sessions. Routing through MCP tool with SDK and mock fallbacks."""
        if self._use_mock:
            return _get_mock_sessions(limit)

        # A. Try MCP
        if self._mcp_adapter is not None:
            try:
                sessions = self._mcp_adapter.get_recent_sessions(limit=limit)
                if sessions:
                    logger.info("PhoenixMCPClient: Successfully retrieved sessions via MCP server.")
                    return sessions
            except Exception as exc:
                logger.warning("PhoenixMCPClient: MCP list-sessions tool failed: %s. Falling back to SDK.", exc)

        # B. Try SDK Fallback
        if self._real_client is not None:
            try:
                sessions = self._real_client.get_recent_sessions(limit=limit)
                if sessions and not (len(sessions) == 1 and "error" in sessions[0]):
                    logger.info("PhoenixMCPClient: Successfully retrieved sessions via SDK fallback.")
                    return sessions
            except Exception as exc:
                logger.warning("PhoenixMCPClient: SDK get_recent_sessions failed: %s. Falling back to mocks.", exc)

        return _get_mock_sessions(limit)

    def get_prompts(self) -> List[Dict[str, Any]]:
        """Retrieve prompts. Routing through MCP tool with SDK and mock fallbacks."""
        if self._use_mock:
            return _get_mock_prompts()

        # A. Try MCP
        if self._mcp_adapter is not None:
            try:
                prompts = self._mcp_adapter.get_prompts()
                if prompts:
                    logger.info("PhoenixMCPClient: Successfully retrieved prompts via MCP server.")
                    return prompts
            except Exception as exc:
                logger.warning("PhoenixMCPClient: MCP list-prompts tool failed: %s. Falling back to SDK.", exc)

        # B. Try SDK Fallback
        if self._real_client is not None:
            try:
                prompts = self._real_client.get_prompts()
                if prompts and not (len(prompts) == 1 and "error" in prompts[0]):
                    logger.info("PhoenixMCPClient: Successfully retrieved prompts via SDK fallback.")
                    return prompts
            except Exception as exc:
                logger.warning("PhoenixMCPClient: SDK get_prompts failed: %s. Falling back to mocks.", exc)

        return _get_mock_prompts()

    def get_experiments(self, dataset_id: str = "") -> List[Dict[str, Any]]:
        """Retrieve experiments. Routing through MCP tool with SDK and mock fallbacks."""
        if self._use_mock:
            return _get_mock_experiments()

        # A. Try MCP
        if self._mcp_adapter is not None:
            try:
                experiments = self._mcp_adapter.get_experiments(dataset_id=dataset_id)
                if experiments:
                    logger.info("PhoenixMCPClient: Successfully retrieved experiments via MCP server.")
                    return experiments
            except Exception as exc:
                logger.warning("PhoenixMCPClient: MCP list-experiments tool failed: %s. Falling back to SDK.", exc)

        # B. Try SDK Fallback
        if self._real_client is not None:
            try:
                experiments = self._real_client.get_experiments(dataset_id=dataset_id)
                if experiments and not (len(experiments) == 1 and "error" in experiments[0]):
                    logger.info("PhoenixMCPClient: Successfully retrieved experiments via SDK fallback.")
                    return experiments
            except Exception as exc:
                logger.warning("PhoenixMCPClient: SDK get_experiments failed: %s. Falling back to mocks.", exc)

        return _get_mock_experiments()

    def get_datasets(self) -> List[Dict[str, Any]]:
        """Retrieve datasets. Routing through MCP tool with SDK and mock fallbacks."""
        if self._use_mock:
            return _get_mock_datasets()

        # A. Try MCP
        if self._mcp_adapter is not None:
            try:
                datasets = self._mcp_adapter.get_datasets()
                if datasets:
                    logger.info("PhoenixMCPClient: Successfully retrieved datasets via MCP server.")
                    return datasets
            except Exception as exc:
                logger.warning("PhoenixMCPClient: MCP list-datasets tool failed: %s. Falling back to SDK.", exc)

        # B. Try SDK Fallback
        if self._real_client is not None:
            try:
                datasets = self._real_client.get_datasets()
                if datasets and not (len(datasets) == 1 and "error" in datasets[0]):
                    logger.info("PhoenixMCPClient: Successfully retrieved datasets via SDK fallback.")
                    return datasets
            except Exception as exc:
                logger.warning("PhoenixMCPClient: SDK get_datasets failed: %s. Falling back to mocks.", exc)

        return _get_mock_datasets()


# ────────────────────────────────────────────────────────────────────
# Module-level wrapper functions
# ────────────────────────────────────────────────────────────────────

_mcp_client_instance: Optional[PhoenixMCPClient] = None


def _get_mcp_client() -> PhoenixMCPClient:
    """Singleton getter for PhoenixMCPClient."""
    global _mcp_client_instance
    if _mcp_client_instance is None:
        _mcp_client_instance = PhoenixMCPClient()
    return _mcp_client_instance


def get_recent_traces(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent traces from Phoenix Cloud (or mocks)."""
    client = _get_mcp_client()
    logger.info("get_recent_traces called. Data source: %s", client.data_source)
    return client.get_recent_traces(limit=limit)


def get_recent_sessions(limit: int = 20) -> List[Dict[str, Any]]:
    """Retrieve recent sessions from Phoenix Cloud (or mocks)."""
    client = _get_mcp_client()
    logger.info("get_recent_sessions called. Data source: %s", client.data_source)
    return client.get_recent_sessions(limit=limit)


def get_prompts() -> List[Dict[str, Any]]:
    """Retrieve prompts from Phoenix Cloud (or mocks)."""
    client = _get_mcp_client()
    logger.info("get_prompts called. Data source: %s", client.data_source)
    return client.get_prompts()


def get_experiments(dataset_id: str = "") -> List[Dict[str, Any]]:
    """Retrieve experiments from Phoenix Cloud (or mocks)."""
    client = _get_mcp_client()
    logger.info("get_experiments called. Data source: %s", client.data_source)
    return client.get_experiments(dataset_id=dataset_id)


def get_datasets() -> List[Dict[str, Any]]:
    """Retrieve datasets from Phoenix Cloud (or mocks)."""
    client = _get_mcp_client()
    logger.info("get_datasets called. Data source: %s", client.data_source)
    return client.get_datasets()


# ────────────────────────────────────────────────────────────────────
# ADK-compatible tool wrapper functions (routed through MCP)
# ────────────────────────────────────────────────────────────────────

def get_phoenix_projects() -> dict:
    """List all projects in Phoenix Cloud (via MCP or SDK fallback)."""
    client = _get_mcp_client()
    if client._use_mock:
        return {"projects": [{"id": "UHJvamVjdDoz", "name": "phoenixguard", "description": "Mock project"}], "count": 1}

    # A. Try MCP
    if client._mcp_adapter is not None:
        try:
            projects = client._mcp_adapter._call_mcp_tool("list-projects", {"limit": 100})
            if projects:
                return {"projects": projects, "count": len(projects)}
        except Exception as exc:
            logger.warning("PhoenixMCPClient: MCP list-projects tool failed: %s. Falling back to SDK.", exc)

    # B. Try SDK Fallback
    if client._real_client is not None:
        try:
            projects = client._real_client.get_projects()
            if projects and not (len(projects) == 1 and "error" in projects[0]):
                return {"projects": projects, "count": len(projects)}
        except Exception as exc:
            logger.warning("PhoenixMCPClient: SDK get_projects failed: %s. Falling back to mocks.", exc)

    return {"projects": [{"id": "UHJvamVjdDoz", "name": "phoenixguard", "description": "Mock project"}], "count": 1}


def get_phoenix_traces(limit: int = 20, lookback_hours: int = 24) -> dict:
    """Retrieve recent traces as a dict wrapper (Phase 2 compatibility)."""
    traces = get_recent_traces(limit=limit)
    return {"traces": traces, "count": len(traces)}


def get_phoenix_spans(limit: int = 50, lookback_hours: int = 24, span_kind: str = "") -> dict:
    """Get recent spans in Phoenix Cloud (via MCP or SDK fallback)."""
    client = _get_mcp_client()
    if client._use_mock:
        # Generate spans from mock traces
        all_spans = []
        for t in _get_mock_traces():
            for s in t.get("spans", []):
                if not span_kind or s.get("span_kind") == span_kind:
                    all_spans.append(s)
        return {"spans": all_spans[:limit], "count": len(all_spans[:limit])}

    # A. Try MCP
    if client._mcp_adapter is not None:
        try:
            args: dict = {"limit": limit}
            if span_kind:
                args["span_kinds"] = [span_kind]
            res = client._mcp_adapter._call_mcp_tool("get-spans", args)
            spans = res.get("spans", []) if isinstance(res, dict) else []
            return {"spans": spans, "count": len(spans)}
        except Exception as exc:
            logger.warning("PhoenixMCPClient: MCP get-spans tool failed: %s. Falling back to SDK.", exc)

    # B. Try SDK Fallback
    if client._real_client is not None:
        try:
            kwargs = {"limit": limit, "lookback_hours": lookback_hours}
            if span_kind:
                kwargs["span_kind"] = span_kind
            spans = client._real_client.get_recent_spans(**kwargs)
            if spans and not (len(spans) == 1 and "error" in spans[0]):
                return {"spans": spans, "count": len(spans)}
        except Exception as exc:
            logger.warning("PhoenixMCPClient: SDK get_recent_spans failed: %s. Falling back to mocks.", exc)

    # Mock Fallback
    all_spans = []
    for t in _get_mock_traces():
        for s in t.get("spans", []):
            if not span_kind or s.get("span_kind") == span_kind:
                all_spans.append(s)
    return {"spans": all_spans[:limit], "count": len(all_spans[:limit])}


def get_phoenix_sessions(limit: int = 20) -> dict:
    """Retrieve recent sessions as a dict wrapper (Phase 2 compatibility)."""
    sessions = get_recent_sessions(limit=limit)
    return {"sessions": sessions, "count": len(sessions)}


def get_phoenix_datasets() -> dict:
    """Retrieve datasets as a dict wrapper (Phase 2 compatibility)."""
    datasets = get_datasets()
    return {"datasets": datasets, "count": len(datasets)}


def get_phoenix_experiments(dataset_id: str = "") -> dict:
    """Retrieve experiments as a dict wrapper (Phase 2 compatibility)."""
    experiments = get_experiments(dataset_id=dataset_id)
    return {"experiments": experiments, "count": len(experiments)}
