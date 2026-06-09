"""PhoenixGuard — Reliability Scorer (Phase 7).

Computes a reliability score from 0 to 100 using a weighted formula:
- 40% Success Rate
- 20% Latency Score
- 20% Tool Usage Quality Score
- 20% Error Rate Score (Success rate counterpart)
"""

from __future__ import annotations

import logging
from typing import Any, Dict

# Set up logging
logger = logging.getLogger(__name__)


def calculate_reliability_score(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate the consolidated reliability score and assign a grade.

    Args:
        metrics: Dictionary of trace analysis metrics computed by TraceAnalyzer.

    Returns:
        Dict with keys: score, grade, components.
    """
    # 1. Success Rate Component (40%)
    success_rate = float(metrics.get("success_rate", 100.0))
    success_score = success_rate * 0.40

    # 2. Latency Component (20%)
    # Smooth score where latency <= 1.0s is 100, drops linearly by 10% per second.
    avg_latency = float(metrics.get("avg_latency", 0.0))
    if avg_latency <= 1.0:
        latency_points = 100.0
    else:
        latency_points = max(0.0, 100.0 - (avg_latency - 1.0) * 10.0)
    latency_score = latency_points * 0.20

    # 3. Tool Usage Quality Component (20%)
    tool_failures = int(metrics.get("tool_failures", 0))
    tool_usage = metrics.get("tool_usage_frequency", {}) or {}
    total_tool_calls = sum(tool_usage.values()) if isinstance(tool_usage, dict) else 0

    if total_tool_calls == 0:
        # If no tools were called and no tool failures occurred, tool quality is perfect.
        tool_quality_points = 100.0 if tool_failures == 0 else 0.0
    else:
        tool_quality_points = max(0.0, 100.0 - (tool_failures / total_tool_calls * 100.0))
    tool_quality_score = tool_quality_points * 0.20

    # 4. Error Rate Component (20%)
    # Success Rate counterpart (where 100 - failure_rate represents success).
    failure_rate = float(metrics.get("failure_rate", 0.0))
    error_rate_points = max(0.0, 100.0 - failure_rate)
    error_rate_score = error_rate_points * 0.20

    # Calculate final score (out of 100)
    total_score = success_score + latency_score + tool_quality_score + error_rate_score
    total_score = round(total_score, 1)

    # Determine Grade
    if total_score >= 90.0:
        grade = "A"
    elif total_score >= 80.0:
        grade = "B"
    elif total_score >= 70.0:
        grade = "C"
    elif total_score >= 60.0:
        grade = "D"
    else:
        grade = "F"

    logger.info("Calculated reliability score: %s, grade: %s", total_score, grade)

    return {
        "score": total_score,
        "grade": grade,
        "components": {
            "success_rate_points": round(success_rate, 1),
            "latency_points": round(latency_points, 1),
            "tool_quality_points": round(tool_quality_points, 1),
            "error_rate_points": round(error_rate_points, 1),
        }
    }
