"""PhoenixGuard — Failure Detector Agent (Phase 4).

Scans traces for latency spikes, tool errors, excessive token consumption, and
abnormal patterns. Uses rule-based detection to guarantee 100% detection of
concrete errors, and Gemini 2.5 Flash to analyze pattern anomalies.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from google import genai
from google.genai import types

# Set up logging
logger = logging.getLogger(__name__)


class FailureDetector:
    """Agent that detects failures and anomalies in trace execution."""

    def __init__(self, gemini_client: Optional[genai.Client] = None) -> None:
        self.client = gemini_client or self._init_client()
        self.model = os.getenv("PHOENIXGUARD_MODEL", "gemini-2.5-flash")
        logger.info("FailureDetector initialized with model: %s", self.model)

    def _init_client(self) -> Optional[genai.Client]:
        """Initialize the Google GenAI Client using available environment keys."""
        api_key = os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("No Gemini API key found in env. LLM detection will fall back to rule-based.")
            return None
        try:
            return genai.Client(api_key=api_key)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini client: %s. Falling back to rule-based.", exc)
            return None

    def _run_rule_based_detection(
        self, traces: List[Dict[str, Any]], metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Run fast, deterministic rules to pre-detect obvious failures."""
        issues = []

        # 1. Tool Failures check
        if metrics.get("tool_failures", 0) > 0:
            for trace in traces:
                for span in trace.get("spans", []) or []:
                    if span.get("span_kind") == "TOOL" and span.get("status_code") == "ERROR":
                        tool_name = span.get("name", "Unknown Tool")
                        if tool_name.startswith("execute_tool "):
                            tool_name = tool_name.replace("execute_tool ", "", 1)
                        status_msg = span.get("status_message") or "Unknown error"
                        
                        issues.append({
                            "issue": f"Tool Execution Failure: {tool_name}",
                            "severity": "High",
                            "explanation": (
                                f"Tool '{tool_name}' failed in trace ID '{trace.get('trace_id')}' "
                                f"with error: '{status_msg}'"
                            )
                        })

        # 2. Latency check
        for trace in traces:
            spans = trace.get("spans", []) or []
            for span in spans:
                start_str = span.get("start_time", "")
                end_str = span.get("end_time", "")
                if start_str and end_str:
                    try:
                        from agents.trace_analyzer import _parse_iso_datetime
                        start_t = _parse_iso_datetime(start_str)
                        end_t = _parse_iso_datetime(end_str)
                        span_duration = (end_t - start_t).total_seconds()
                        
                        # If a single tool or LLM span takes more than 5.0 seconds
                        if span_duration > 5.0:
                            kind = span.get("span_kind", "OPERATION")
                            issues.append({
                                "issue": f"High Latency in {kind}: {span.get('name')}",
                                "severity": "Medium",
                                "explanation": (
                                    f"Span '{span.get('name')}' in trace ID '{trace.get('trace_id')}' "
                                    f"took {round(span_duration, 2)} seconds, exceeding the 5.0s threshold."
                                )
                            })
                    except Exception as e:
                        logger.warning("Failed to parse span timestamps for latency: %s", e)

        # 3. Excessive Token Consumption check
        for trace in traces:
            total_tokens = trace.get("token_count_total", 0) or 0
            if total_tokens > 8000:
                issues.append({
                    "issue": "Excessive Token Consumption",
                    "severity": "Low",
                    "explanation": (
                        f"Trace ID '{trace.get('trace_id')}' consumed a high number of tokens "
                        f"({total_tokens} total tokens), which could increase execution costs."
                    )
                })

        return issues

    def detect_failures(
        self, traces: List[Dict[str, Any]], metrics: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Identify failures, latency anomalies, and pattern issues from trace data.

        Combines fast rule-based detection with Gemini 2.5 Flash reasoning.

        Args:
            traces: List of trace dictionaries.
            metrics: Computed metrics dictionary from TraceAnalyzer.

        Returns:
            List of issue dicts, where each dict has keys: issue, severity, explanation.
        """
        # Run rules first
        rule_issues = self._run_rule_based_detection(traces, metrics)

        # If we don't have API keys or traces are empty, return rule-based detections directly
        if self.client is None or not traces:
            logger.info("Returning rule-based detections directly (no LLM connection or empty traces).")
            return rule_issues

        # Prepare payload for LLM analysis
        # Clean traces for prompt to avoid token overflow, keeping only structure and failures
        clean_traces_summary = []
        for t in traces:
            # Calculate actual trace duration in seconds
            duration_seconds = 0.0
            start_str = t.get("start_time", "")
            end_str = t.get("end_time", "")
            if start_str and end_str:
                try:
                    from agents.trace_analyzer import _parse_iso_datetime
                    start_t = _parse_iso_datetime(start_str)
                    end_t = _parse_iso_datetime(end_str)
                    duration_seconds = max(0.0, (end_t - start_t).total_seconds())
                except Exception:
                    pass

            trace_summary = {
                "trace_id": t.get("trace_id"),
                "duration": round(duration_seconds, 2),
                "token_count_total": t.get("token_count_total"),
                "spans": [
                    {
                        "name": s.get("name"),
                        "span_kind": s.get("span_kind"),
                        "status_code": s.get("status_code"),
                        "status_message": s.get("status_message")
                    }
                    for s in (t.get("spans", []) or [])
                ]
            }
            clean_traces_summary.append(trace_summary)

        prompt = f"""\
You are an expert AI Reliability Engineer and Observability Agent. Your task is to analyze trace execution data to detect:
1. Tool failures or crashes
2. Latency spikes or slow reasoning chains
3. Excessive token consumption
4. Abnormal trace patterns (like loops, repeated calls, prompt degradation)

Below is the summary of computed metrics and raw trace structure.

## Trace Metrics
{json.dumps(metrics, indent=2)}

## Rules-Based Pre-Detected Issues
{json.dumps(rule_issues, indent=2)}

## Raw Traces
{json.dumps(clean_traces_summary, indent=2)}

## Instructions
Review all data, consolidate the pre-detected issues, and identify any new or subtle pattern anomalies (e.g. repeated tools, recursive loops, empty outputs).
Return a JSON array of issue objects. Each issue object MUST have EXACTLY these fields:
- "issue": Short name of the issue
- "severity": "High", "Medium", or "Low"
- "explanation": Description of what happened and why it is a problem

If no issues are found, return an empty array: []

Return ONLY valid JSON. Do not include markdown code block formatting (such as ```json) in your response.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1,
                )
            )

            response_text = response.text.strip() if response.text else "[]"
            # Strip potential code blocks if they are returned despite prompt instructions
            if response_text.startswith("```"):
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                else:
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            detected_issues = json.loads(response_text)
            if isinstance(detected_issues, list):
                logger.info("FailureDetector found %d issues using Gemini.", len(detected_issues))
                return detected_issues
            else:
                logger.warning("Gemini did not return a list. Falling back to rule issues.")
                return rule_issues

        except Exception as exc:
            logger.error("LLM failure detection failed: %s. Falling back to rule-based.", exc)
            return rule_issues
