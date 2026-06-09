"""PhoenixGuard — Root Cause Analyzer Agent (Phase 5).

Analyzes trace statistics and detected anomalies to determine the underlying
root causes of failures and provide actionable recommendations.
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


class RootCauseAnalyzer:
    """Agent that performs root cause analysis and suggests fixes for reliability issues."""

    def __init__(self, gemini_client: Optional[genai.Client] = None) -> None:
        self.client = gemini_client or self._init_client()
        self.model = os.getenv("PHOENIXGUARD_MODEL", "gemini-2.5-flash")
        logger.info("RootCauseAnalyzer initialized with model: %s", self.model)

    def _init_client(self) -> Optional[genai.Client]:
        """Initialize the Google GenAI Client using available environment keys."""
        api_key = os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.warning("No Gemini API key found in env. Root cause analysis will fall back to default.")
            return None
        try:
            return genai.Client(api_key=api_key)
        except Exception as exc:
            logger.warning("Failed to initialize Gemini client: %s. Falling back to default.", exc)
            return None

    def analyze_root_cause(
        self, trace_analysis: Dict[str, Any], failures: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Perform root cause analysis based on trace statistics and detected failures.

        Args:
            trace_analysis: Metrics dictionary computed by TraceAnalyzer.
            failures: List of issues detected by FailureDetector.

        Returns:
            Dict containing: root_cause, confidence, recommended_fix.
        """
        # Define fallback early in case we need it
        first_issue = failures[0].get("issue", "Unknown issue") if failures else "System failure"
        first_expl = failures[0].get("explanation", "No explanation available") if failures else ""
        fallback = {
            "root_cause": f"Primary failure detected: {first_issue}. {first_expl}",
            "confidence": "Medium",
            "recommended_fix": "Inspect the logs and stack trace for the failing components, and review tool error boundaries."
        }

        # If there are no failures and success rate is 100%
        if not failures or trace_analysis.get("success_rate", 100.0) == 100.0:
            logger.info("No failures detected. Returning healthy system status.")
            return {
                "root_cause": "The system is functioning normally. All traces succeeded without error.",
                "confidence": "High",
                "recommended_fix": "No action required. Continue monitoring performance metrics."
            }

        # If no client is available, return fallback
        if self.client is None:
            logger.info("No Gemini API client available. Returning fallback diagnostics.")
            return fallback

        prompt = f"""\
You are an expert AI Reliability Engineer. Your task is to perform root cause analysis on a set of LLM agent traces that encountered failures.

Below are the aggregated metrics and the list of detected failures.

## Aggregated Trace Metrics
{json.dumps(trace_analysis, indent=2)}

## Detected Failures & Anomalies
{json.dumps(failures, indent=2)}

## Instructions
Analyze the connection between the metrics and the failures. Diagnose:
1. What is the primary root cause of these failures? (e.g. API timeouts, permission errors, code logic bugs, hallucinated parameters, loop conditions).
2. What is your confidence level in this diagnosis? ("High", "Medium", or "Low")
3. What is the specific, actionable recommendation to fix or mitigate the issue?

Your response MUST be a single JSON object with EXACTLY these three keys:
- "root_cause": Detailed explanation of the primary root cause.
- "confidence": Your confidence in the diagnosis ("High", "Medium", or "Low").
- "recommended_fix": The concrete recommended fix or mitigation strategy.

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

            response_text = response.text.strip() if response.text else "{}"
            # Strip potential code blocks
            if response_text.startswith("```"):
                if response_text.startswith("```json"):
                    response_text = response_text[7:]
                else:
                    response_text = response_text[3:]
                if response_text.endswith("```"):
                    response_text = response_text[:-3]
                response_text = response_text.strip()

            rca_result = json.loads(response_text)
            
            # Ensure correct keys are present
            required_keys = ["root_cause", "confidence", "recommended_fix"]
            if all(k in rca_result for k in required_keys):
                logger.info("RootCauseAnalyzer completed analysis. Confidence: %s", rca_result["confidence"])
                return rca_result
            else:
                logger.warning("RCA result missing required keys. Falling back to default payload.")
                
        except Exception as exc:
            logger.error("Root Cause Analysis failed: %s. Generating fallback result.", exc)

        # Fallback diagnostics
        first_issue = failures[0].get("issue", "Unknown issue") if failures else "System failure"
        first_expl = failures[0].get("explanation", "No explanation available") if failures else ""
        
        fallback = {
            "root_cause": f"Primary failure detected: {first_issue}. {first_expl}",
            "confidence": "Medium",
            "recommended_fix": "Inspect the logs and stack trace for the failing components, and review tool error boundaries."
        }
        return fallback
