"""PhoenixGuard — Demo Data Generator (Phase 12).

Generates realistic mock trace data structures for five specific scenarios:
- Scenario A: Healthy Traces
- Scenario B: Latency Spikes
- Scenario C: Tool Failures
- Scenario D: Repeated Failures
- Scenario E: Excessive Token Consumption

These mock traces match the official Arize Phoenix OTEL span dictionary schema
perfectly, allowing TraceAnalyzer, FailureDetector, and RootCauseAnalyzer to
process them directly.
"""

from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List


def _generate_span(
    span_id: str,
    name: str,
    kind: str,
    status: str,
    start_time: datetime,
    duration_sec: float,
    parent_id: str | None = None,
    status_message: str | None = None,
) -> Dict[str, Any]:
    """Helper to generate a single structured span dictionary."""
    end_time = start_time + timedelta(seconds=duration_sec)
    span = {
        "id": f"U3Bhbjo{random.randint(10000, 99999)}",
        "span_id": span_id,
        "parent_id": parent_id,
        "name": name,
        "span_kind": kind,
        "status_code": status,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
    }
    if status_message:
        span["status_message"] = status_message
    return span


def get_scenario_a_healthy() -> List[Dict[str, Any]]:
    """Scenario A: Healthy traces (fast, no errors, reasonable tokens)."""
    now = datetime.now(timezone.utc)
    traces = []
    
    # 5 healthy traces
    for i in range(5):
        t_start = now - timedelta(minutes=5 * (i + 1))
        trace_id = f"a0a0a0a0a0a0a0a0a0a0a0a0a0a0a0{i}a"
        traces.append({
            "id": f"VHJhY2U6NDA{i}",
            "trace_id": trace_id,
            "project_id": "UHJvamVjdDoz",
            "start_time": t_start.isoformat(),
            "end_time": (t_start + timedelta(seconds=1.2)).isoformat(),
            "token_count_prompt": 1200,
            "token_count_completion": 150,
            "token_count_total": 1350,
            "spans": [
                _generate_span("1", "invocation [phoenixguard]", "CHAIN", "OK", t_start, 1.2),
                _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "OK", t_start, 1.2, "1"),
                _generate_span("3", "call_llm", "LLM", "OK", t_start, 0.4, "2"),
                _generate_span("4", "execute_tool get_weather", "TOOL", "OK", t_start + timedelta(seconds=0.4), 0.3, "2"),
                _generate_span("5", "call_llm", "LLM", "OK", t_start + timedelta(seconds=0.7), 0.5, "2"),
            ]
        })
    return traces


def get_scenario_b_latency_spikes() -> List[Dict[str, Any]]:
    """Scenario B: Latency Spikes (slow reasoning, slow tool executions)."""
    now = datetime.now(timezone.utc)
    traces = []

    # Trace 1: Slow Weather Tool (takes 7.5 seconds)
    t1_start = now - timedelta(minutes=10)
    traces.append({
        "id": "VHJhY2U6NDAx",
        "trace_id": "b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1b1",
        "project_id": "UHJvamVjdDoz",
        "start_time": t1_start.isoformat(),
        "end_time": (t1_start + timedelta(seconds=9.0)).isoformat(),
        "token_count_prompt": 1400,
        "token_count_completion": 200,
        "token_count_total": 1600,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "OK", t1_start, 9.0),
            _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "OK", t1_start, 9.0, "1"),
            _generate_span("3", "execute_tool get_weather", "TOOL", "OK", t1_start + timedelta(seconds=1.0), 7.5, "2"),
        ]
    })

    # Trace 2: Slow LLM reasoning (takes 11.2 seconds)
    t2_start = now - timedelta(minutes=12)
    traces.append({
        "id": "VHJhY2U6NDAy",
        "trace_id": "b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2b2",
        "project_id": "UHJvamVjdDoz",
        "start_time": t2_start.isoformat(),
        "end_time": (t2_start + timedelta(seconds=11.5)).isoformat(),
        "token_count_prompt": 2500,
        "token_count_completion": 600,
        "token_count_total": 3100,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "OK", t2_start, 11.5),
            _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "OK", t2_start, 11.5, "1"),
            _generate_span("3", "call_llm", "LLM", "OK", t2_start + timedelta(seconds=0.1), 11.2, "2"),
        ]
    })

    return traces


def get_scenario_c_tool_failures() -> List[Dict[str, Any]]:
    """Scenario C: Tool Failures (AccessDenied or API Timeouts)."""
    now = datetime.now(timezone.utc)
    traces = []

    # Trace 1: CPU retrieval permission error
    t1_start = now - timedelta(minutes=20)
    traces.append({
        "id": "VHJhY2U6NDAz",
        "trace_id": "c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1c1",
        "project_id": "UHJvamVjdDoz",
        "start_time": t1_start.isoformat(),
        "end_time": (t1_start + timedelta(seconds=1.5)).isoformat(),
        "token_count_prompt": 1200,
        "token_count_completion": 90,
        "token_count_total": 1290,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "ERROR", t1_start, 1.5),
            _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "ERROR", t1_start, 1.5, "1"),
            _generate_span("3", "execute_tool get_system_health", "TOOL", "ERROR", t1_start + timedelta(seconds=0.5), 0.8, "2",
                           status_message="psutil.AccessDenied: Permission denied for CPU metrics query on host operating system."),
        ]
    })

    # Trace 2: Weather API Timeout
    t2_start = now - timedelta(minutes=25)
    traces.append({
        "id": "VHJhY2U6NDA0",
        "trace_id": "c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2c2",
        "project_id": "UHJvamVjdDoz",
        "start_time": t2_start.isoformat(),
        "end_time": (t2_start + timedelta(seconds=6.2)).isoformat(),
        "token_count_prompt": 1100,
        "token_count_completion": 50,
        "token_count_total": 1150,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "ERROR", t2_start, 6.2),
            _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "ERROR", t2_start, 6.2, "1"),
            _generate_span("3", "execute_tool get_weather", "TOOL", "ERROR", t2_start + timedelta(seconds=0.2), 6.0, "2",
                           status_message="httpx.TimeoutException: Connection timed out to Weather API Server (http://api.weather.local)."),
        ]
    })

    return traces


def get_scenario_d_repeated_failures() -> List[Dict[str, Any]]:
    """Scenario D: Repeated Failures (infinite loops or successive tool failures)."""
    now = datetime.now(timezone.utc)
    traces = []

    # Trace 1: Weather tool failing repeatedly in a loop
    t1_start = now - timedelta(minutes=30)
    traces.append({
        "id": "VHJhY2U6NDA1",
        "trace_id": "d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1d1",
        "project_id": "UHJvamVjdDoz",
        "start_time": t1_start.isoformat(),
        "end_time": (t1_start + timedelta(seconds=8.5)).isoformat(),
        "token_count_prompt": 3800,
        "token_count_completion": 450,
        "token_count_total": 4250,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "ERROR", t1_start, 8.5),
            _generate_span("2", "agent_run [phoenixguard_agent]", "AGENT", "ERROR", t1_start, 8.5, "1"),
            _generate_span("3", "execute_tool get_weather", "TOOL", "ERROR", t1_start + timedelta(seconds=1.0), 2.0, "2",
                           status_message="httpx.ConnectError: Connection refused."),
            _generate_span("4", "execute_tool get_weather", "TOOL", "ERROR", t1_start + timedelta(seconds=3.5), 2.0, "2",
                           status_message="httpx.ConnectError: Connection refused."),
            _generate_span("5", "execute_tool get_weather", "TOOL", "ERROR", t1_start + timedelta(seconds=6.0), 2.0, "2",
                           status_message="httpx.ConnectError: Connection refused."),
        ]
    })

    return traces


def get_scenario_e_excessive_tokens() -> List[Dict[str, Any]]:
    """Scenario E: Excessive token consumption (exploding contexts)."""
    now = datetime.now(timezone.utc)
    traces = []

    # Trace 1: Exploding LLM context
    t1_start = now - timedelta(minutes=45)
    traces.append({
        "id": "VHJhY2U6NDA2",
        "trace_id": "e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1e1",
        "project_id": "UHJvamVjdDoz",
        "start_time": t1_start.isoformat(),
        "end_time": (t1_start + timedelta(seconds=5.5)).isoformat(),
        "token_count_prompt": 12500,
        "token_count_completion": 1800,
        "token_count_total": 14300,
        "spans": [
            _generate_span("1", "invocation [phoenixguard]", "CHAIN", "OK", t1_start, 5.5),
            _generate_span("2", "call_llm", "LLM", "OK", t1_start, 5.5, "1"),
        ]
    })

    return traces


def get_all_scenarios_combined() -> List[Dict[str, Any]]:
    """Combine all scenarios into a single list of traces representing complex history."""
    all_traces = []
    all_traces.extend(get_scenario_a_healthy())
    all_traces.extend(get_scenario_b_latency_spikes())
    all_traces.extend(get_scenario_c_tool_failures())
    all_traces.extend(get_scenario_d_repeated_failures())
    all_traces.extend(get_scenario_e_excessive_tokens())
    return all_traces
