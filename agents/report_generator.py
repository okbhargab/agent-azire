"""PhoenixGuard — Report Generator Agent (Phase 8).

Compiles all reliability metrics, detected failures, root causes, reliability scores,
and prompt optimization suggestions into a comprehensive executive markdown report.
Uses Gemini 2.5 Flash for high-impact report generation, falling back to programmatic
markdown construction if the API is unreachable.
"""

from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List, Optional

from google import genai

# Set up logging
logger = logging.getLogger(__name__)


def generate_fallback_report(
    metrics: Dict[str, Any],
    failures: List[Dict[str, Any]],
    rca: Dict[str, Any],
    score: Dict[str, Any],
    optimization: Dict[str, Any],
) -> str:
    """Programmatically construct a structured executive markdown report."""
    report_lines = [
        "# PhoenixGuard Reliability Report",
        "",
        f"## Health Score: **{score.get('score', 0.0)}%** (Grade: **{score.get('grade', 'F')}**)",
        "",
        "### Score Breakdown",
        f"- **Success Rate Points**: {score.get('components', {}).get('success_rate_points', 0.0)} / 100",
        f"- **Latency Points**: {score.get('components', {}).get('latency_points', 0.0)} / 100",
        f"- **Tool Quality Points**: {score.get('components', {}).get('tool_quality_points', 0.0)} / 100",
        f"- **Error Rate Points**: {score.get('components', {}).get('error_rate_points', 0.0)} / 100",
        "",
        "## Top Problems",
    ]

    if failures:
        for idx, item in enumerate(failures, 1):
            sev = item.get("severity", "Unknown")
            issue = item.get("issue", "Anomaly")
            expl = item.get("explanation", "")
            report_lines.append(f"{idx}. **[{sev}] {issue}**: {expl}")
    else:
        report_lines.append("- No significant issues or failures detected in the evaluated traces.")

    report_lines.extend([
        "",
        "## Root Causes",
        f"- **Primary Diagnosis**: {rca.get('root_cause', 'N/A')}",
        f"- **Confidence Level**: **{rca.get('confidence', 'N/A')}**",
        "",
        "## Recommendations",
        f"- **Immediate Fix**: {rca.get('recommended_fix', 'No immediate action recommended.')}",
    ])

    if optimization and optimization.get("prompt_improvements"):
        report_lines.append("")
        report_lines.append("### Suggested Prompt Improvements")
        for imp in optimization.get("prompt_improvements", []):
            report_lines.append(f"- {imp}")

    return "\n".join(report_lines)


class ReportGenerator:
    """Agent that compiles telemetry data and diagnostic logs into executive reports."""

    def __init__(self, gemini_client: Optional[genai.Client] = None) -> None:
        self.client = gemini_client or self._init_client()
        self.model = os.getenv("PHOENIXGUARD_MODEL", "gemini-2.5-flash")
        logger.info("ReportGenerator initialized with model: %s", self.model)

    def _init_client(self) -> Optional[genai.Client]:
        """Initialize the Google GenAI Client using available environment keys."""
        api_key = os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("No Gemini API key found in env. Executive reports will use programmatic templates.")
            return None
        try:
            return genai.Client(api_key=api_key)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini client: %s. Falling back to default report template.", exc)
            return None

    def generate_executive_report(
        self,
        metrics: Dict[str, Any],
        failures: List[Dict[str, Any]],
        rca: Dict[str, Any],
        score: Dict[str, Any],
        optimization: Dict[str, Any],
    ) -> str:
        """Create a Markdown executive report from reliability logs.

        Args:
            metrics: Dict of trace metrics from TraceAnalyzer.
            failures: List of issues from FailureDetector.
            rca: Dict of root causes from RootCauseAnalyzer.
            score: Dict containing score/grade from scoring.
            optimization: Dict containing prompt changes from PromptOptimizer.

        Returns:
            Executive report written in Markdown.
        """
        # Define the fallback report upfront
        fallback_report = generate_fallback_report(metrics, failures, rca, score, optimization)

        if self.client is None:
            logger.info("No LLM client available. Returning programmatic report.")
            return fallback_report

        prompt = f"""\
You are an expert AI Reliability Director and Observability Engineer. Write a high-impact, professional executive reliability report for PhoenixGuard based on the findings from previous analysis phases.

## Input Metrics & Diagnostics

### Aggregated Trace Metrics
{json.dumps(metrics, indent=2)}

### Reliability Scoring
{json.dumps(score, indent=2)}

### Detected Failures & Anomalies
{json.dumps(failures, indent=2)}

### Root Cause Analysis
{json.dumps(rca, indent=2)}

### Suggested Prompt Optimizations
{json.dumps(optimization, indent=2)}

## Instructions
Synthesize all this information into a cohesive, polished markdown executive dashboard report. Keep the tone professional, objective, and action-oriented.
The report MUST contain these headers exactly (though you may add content and sub-headers below them):
# PhoenixGuard Reliability Report
## Health Score
## Top Problems
## Root Causes
## Recommendations

Ensure the Health Score shows the grade and breakdown. For Top Problems, list the issues with their severity and explanations. For Root Causes, explain the primary diagnoses and your confidence. For Recommendations, explain what fixes to apply, including highlights from the suggested prompt optimizations.

Do not wrap your output in markdown code blocks (such as ```markdown). Just output the raw markdown text directly.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
            )
            report_text = response.text.strip() if response.text else ""
            if report_text.startswith("```"):
                if report_text.startswith("```markdown"):
                    report_text = report_text[11:]
                else:
                    report_text = report_text[3:]
                if report_text.endswith("```"):
                    report_text = report_text[:-3]
                report_text = report_text.strip()
            
            if report_text:
                logger.info("ReportGenerator successfully compiled executive report via Gemini.")
                return report_text
            else:
                logger.warning("Gemini returned empty report text. Using fallback template.")
                
        except Exception as exc:
            logger.error("LLM report generation failed: %s. Using fallback template.", exc)

        return fallback_report
