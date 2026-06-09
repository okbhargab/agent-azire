"""PhoenixGuard — Trace Analyzer Agent (Phase 3).

Analyzes raw Phoenix traces to compute performance, latency, and success/failure
metrics. Computes calculations deterministically in Python to guarantee accuracy
and speed.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List

# Set up logging
logger = logging.getLogger(__name__)


def _parse_iso_datetime(dt_str: str) -> datetime:
    """Parse an ISO-8601 datetime string robustly, handling 'Z' suffix."""
    if not dt_str:
        return datetime.now()
    if dt_str.endswith("Z"):
        dt_str = dt_str[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        # Fallback if there are fractional microseconds differences
        # e.g., if there are too many digits in the microsecond part
        if "." in dt_str:
            base, frac = dt_str.split(".")
            # keep only up to 6 digits of microsecond + timezone
            tz_part = ""
            if "+" in frac:
                frac, tz_part = frac.split("+", 1)
                tz_part = "+" + tz_part
            elif "-" in frac:
                frac, tz_part = frac.split("-", 1)
                tz_part = "-" + tz_part
            frac = frac[:6]
            dt_str = f"{base}.{frac}{tz_part}"
        return datetime.fromisoformat(dt_str)


class TraceAnalyzer:
    """Agent that calculates execution statistics and aggregates metrics from traces."""

    def __init__(self) -> None:
        logger.info("TraceAnalyzer initialized.")

    def analyze_traces(self, traces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze a list of traces and compute key reliability metrics.

        Args:
            traces: List of trace dictionaries retrieved from Phoenix/MCP.

        Returns:
            A structured dict containing computed stats: success_rate, avg_latency, etc.
        """
        total_traces = len(traces)
        if total_traces == 0:
            return {
                "total_traces": 0,
                "success_rate": 100.0,
                "failure_rate": 0.0,
                "avg_latency": 0.0,
                "avg_token_usage": 0.0,
                "avg_prompt_tokens": 0.0,
                "avg_completion_tokens": 0.0,
                "tool_usage_frequency": {},
                "tool_failures": 0,
            }

        failed_traces_count = 0
        total_latency_seconds = 0.0
        total_prompt_tokens = 0
        total_completion_tokens = 0
        total_tokens = 0
        
        tool_usage_frequency: Dict[str, int] = {}
        tool_failures = 0

        for trace in traces:
            # 1. Parse Latency
            start_time = _parse_iso_datetime(trace.get("start_time", ""))
            end_time = _parse_iso_datetime(trace.get("end_time", ""))
            duration = (end_time - start_time).total_seconds()
            total_latency_seconds += max(0.0, duration)

            # 2. Parse Token Counts
            total_prompt_tokens += trace.get("token_count_prompt", 0) or 0
            total_completion_tokens += trace.get("token_count_completion", 0) or 0
            total_tokens += trace.get("token_count_total", 0) or 0

            # 3. Analyze Spans for Success/Failure and Tool Usage
            spans = trace.get("spans", []) or []
            trace_failed = False
            
            for span in spans:
                status_code = span.get("status_code", "UNSET")
                span_kind = span.get("span_kind", "")
                span_name = span.get("name", "")

                # Check if trace failed (any span with ERROR is a trace-level error)
                if status_code == "ERROR":
                    trace_failed = True

                # Tool usage analysis
                if span_kind == "TOOL" or span_name.startswith("execute_tool "):
                    # Extract tool name from span name (e.g. "execute_tool get_weather" -> "get_weather")
                    tool_name = span_name
                    if span_name.startswith("execute_tool "):
                        tool_name = span_name.replace("execute_tool ", "", 1).strip()
                    
                    tool_usage_frequency[tool_name] = tool_usage_frequency.get(tool_name, 0) + 1
                    
                    if status_code == "ERROR":
                        tool_failures += 1
            
            if trace_failed:
                failed_traces_count += 1

        success_rate = ((total_traces - failed_traces_count) / total_traces) * 100.0
        failure_rate = (failed_traces_count / total_traces) * 100.0

        analysis = {
            "total_traces": total_traces,
            "success_rate": round(success_rate, 2),
            "failure_rate": round(failure_rate, 2),
            "avg_latency": round(total_latency_seconds / total_traces, 3),
            "avg_token_usage": round(total_tokens / total_traces, 1),
            "avg_prompt_tokens": round(total_prompt_tokens / total_traces, 1),
            "avg_completion_tokens": round(total_completion_tokens / total_traces, 1),
            "tool_usage_frequency": tool_usage_frequency,
            "tool_failures": tool_failures,
        }

        logger.info("Analyzed %d traces: success_rate=%s%% tool_failures=%d", 
                    total_traces, analysis["success_rate"], tool_failures)
        return analysis
