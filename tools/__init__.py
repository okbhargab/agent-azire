"""PhoenixGuard Tools Package.

Provides functional tools for the ADK agent and Phoenix integration.
"""

from tools.agent_tools import get_weather, get_system_health
from tools.phoenix_mcp_client import (
    get_phoenix_projects,
    get_phoenix_traces,
    get_phoenix_spans,
    get_phoenix_sessions,
    get_phoenix_datasets,
    get_phoenix_experiments,
)

__all__ = [
    # Agent tools (Phase 1)
    "get_weather",
    "get_system_health",
    # Phoenix tools (Phase 2 compliance)
    "get_phoenix_projects",
    "get_phoenix_traces",
    "get_phoenix_spans",
    "get_phoenix_sessions",
    "get_phoenix_datasets",
    "get_phoenix_experiments",
]
