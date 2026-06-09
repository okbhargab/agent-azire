"""PhoenixGuard — Unit Tests for Reliability Agents (Phases 3 to 8).

Verifies the analysis, detection, diagnostics, scoring, prompt optimization,
and report generation pipeline end-to-end.
"""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock, patch

from agents.failure_detector import FailureDetector
from agents.prompt_optimizer import PromptOptimizer
from agents.report_generator import ReportGenerator
from agents.root_cause_analyzer import RootCauseAnalyzer
from agents.trace_analyzer import TraceAnalyzer
from tools.phoenix_mcp_client import PhoenixMCPClient
from tools.scoring import calculate_reliability_score


class TestReliabilityPipeline(unittest.TestCase):
    """Verifies that TraceAnalyzer, FailureDetector, and RootCauseAnalyzer function correctly."""

    def setUp(self) -> None:
        # Enable mock mode explicitly for tests to ensure predictable traces
        os.environ["PHOENIX_USE_MOCK"] = "true"
        self.mcp_client = PhoenixMCPClient()
        self.traces = self.mcp_client.get_recent_traces()

    def test_phoenix_mcp_client_mock_data(self) -> None:
        """Verify that the Phoenix MCP Client returns realistic mock traces when requested."""
        self.assertTrue(len(self.traces) > 0)
        first_trace = self.traces[0]
        self.assertIn("trace_id", first_trace)
        self.assertIn("spans", first_trace)
        self.assertTrue(len(first_trace["spans"]) > 0)

    def test_trace_analyzer_metrics(self) -> None:
        """Verify that TraceAnalyzer computes metrics correctly on mock traces."""
        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(self.traces)

        # Basic keys checking
        required_keys = {
            "total_traces",
            "success_rate",
            "failure_rate",
            "avg_latency",
            "avg_token_usage",
            "tool_usage_frequency",
            "tool_failures"
        }
        self.assertTrue(required_keys.issubset(metrics.keys()))
        
        # Check specific values from our mock traces
        # We have 5 mock traces:
        # - Trace 1: Successful weather query (duration 2s)
        # - Trace 2: High latency weather query (duration 8s)
        # - Trace 3: Tool failure on system health (duration 1s, ERROR status)
        # - Trace 4: Excessive tokens (duration 4s)
        # - Trace 5: Successful health query (duration 2s)
        # Thus total = 5, success = 4/5 (80%), failure = 1/5 (20%)
        self.assertEqual(metrics["total_traces"], 5)
        self.assertEqual(metrics["success_rate"], 80.0)
        self.assertEqual(metrics["failure_rate"], 20.0)
        self.assertEqual(metrics["tool_failures"], 1)  # Trace 3's get_system_health fails
        
        # Tool frequencies: get_weather is called in Trace 1, 2. get_system_health in Trace 3, 5.
        self.assertEqual(metrics["tool_usage_frequency"].get("get_weather"), 2)
        self.assertEqual(metrics["tool_usage_frequency"].get("get_system_health"), 2)

    def test_failure_detector_rules(self) -> None:
        """Verify that FailureDetector pre-detects anomalies correctly using rules."""
        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(self.traces)
        
        detector = FailureDetector()
        # Test rule-based detection in isolation
        rule_issues = detector._run_rule_based_detection(self.traces, metrics)
        
        self.assertTrue(len(rule_issues) >= 3)  # expect tool failure, high latency, excessive token consumption
        
        # Check tool failure presence
        tool_failure_detected = any("Tool Execution Failure" in issue["issue"] for issue in rule_issues)
        self.assertTrue(tool_failure_detected)
        
        # Check latency issue presence
        latency_detected = any("High Latency" in issue["issue"] for issue in rule_issues)
        self.assertTrue(latency_detected)

        # Check token usage presence
        token_detected = any("Excessive Token" in issue["issue"] for issue in rule_issues)
        self.assertTrue(token_detected)

    @patch("google.genai.Client")
    def test_failure_detector_llm(self, mock_genai_client_class: MagicMock) -> None:
        """Verify FailureDetector handles LLM JSON integration correctly."""
        # Mocking Gemini client response
        mock_response = MagicMock()
        mock_response.text = """
        [
            {
                "issue": "Tool Execution Failure: get_system_health",
                "severity": "High",
                "explanation": "Permission denied on CPU metric fetch."
            }
        ]
        """
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(self.traces)

        detector = FailureDetector(gemini_client=mock_client)
        detected_issues = detector.detect_failures(self.traces, metrics)

        self.assertEqual(len(detected_issues), 1)
        self.assertEqual(detected_issues[0]["issue"], "Tool Execution Failure: get_system_health")
        self.assertEqual(detected_issues[0]["severity"], "High")

    @patch("google.genai.Client")
    def test_root_cause_analyzer(self, mock_genai_client_class: MagicMock) -> None:
        """Verify RootCauseAnalyzer diagnoses failures correctly using LLM."""
        mock_response = MagicMock()
        mock_response.text = """
        {
            "root_cause": "The system health tool fails because of OS privileges restriction for psutil.",
            "confidence": "High",
            "recommended_fix": "Add try-except blocks to run_system_health tool."
        }
        """
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(self.traces)
        
        # Prepare mock failures
        failures = [
            {
                "issue": "Tool Execution Failure: get_system_health",
                "severity": "High",
                "explanation": "Permission denied on CPU metric fetch."
            }
        ]

        rca = RootCauseAnalyzer(gemini_client=mock_client)
        result = rca.analyze_root_cause(metrics, failures)

        self.assertEqual(result["confidence"], "High")
        self.assertIn("psutil", result["root_cause"])
        self.assertIn("try-except", result["recommended_fix"])

    def test_reliability_scoring_math(self) -> None:
        """Verify weighted reliability scoring math outputs correct value and grade."""
        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(self.traces)

        # Average latency = 1.6 seconds
        # latency_points = 100 - (1.6 - 1.0) * 10 = 94.0
        # success_rate = 80.0
        # total_tool_calls = 4, tool_failures = 1. tool_quality_points = 100 - 25 = 75.0
        # error_rate = 20.0, error_rate_points = 80.0
        # Weighted score: 80.0*0.4 + 94.0*0.2 + 75.0*0.2 + 80.0*0.2 = 32 + 18.8 + 15.0 + 16 = 81.8
        res = calculate_reliability_score(metrics)
        self.assertEqual(res["score"], 81.8)
        self.assertEqual(res["grade"], "B")
        self.assertEqual(res["components"]["success_rate_points"], 80.0)
        self.assertEqual(res["components"]["latency_points"], 94.0)
        self.assertEqual(res["components"]["tool_quality_points"], 75.0)

    @patch("google.genai.Client")
    def test_prompt_optimizer_llm(self, mock_genai_client_class: MagicMock) -> None:
        """Verify PromptOptimizer processes LLM optimization successfully."""
        mock_response = MagicMock()
        mock_response.text = """
        {
            "weaknesses": ["Vague guidelines on tool arguments"],
            "prompt_improvements": ["Instruct strict schema adherence"],
            "rewritten_prompt": "You are a reliable agent..."
        }
        """
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        optimizer = PromptOptimizer(gemini_client=mock_client)
        res = optimizer.optimize_prompt(self.traces, "Current Prompt Template")
        self.assertEqual(res["rewritten_prompt"], "You are a reliable agent...")
        self.assertEqual(len(res["weaknesses"]), 1)

    def test_prompt_optimizer_fallback(self) -> None:
        """Verify PromptOptimizer returns fallback optimization when no client is present."""
        optimizer = PromptOptimizer(gemini_client=None)
        # Clear mock address to force fallback path
        optimizer.client = None

        res = optimizer.optimize_prompt(self.traces, "Current Prompt Template")
        self.assertTrue(len(res["weaknesses"]) > 0)
        self.assertIn("Current Prompt Template", res["rewritten_prompt"])

    @patch("google.genai.Client")
    def test_report_generator_llm(self, mock_genai_client_class: MagicMock) -> None:
        """Verify ReportGenerator constructs Executive Markdown Report successfully via LLM."""
        mock_response = MagicMock()
        mock_response.text = "# PhoenixGuard Reliability Report\n\nHealth Score: A"
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        metrics = {"success_rate": 100}
        failures = []
        rca = {"root_cause": "none"}
        score = {"score": 100, "grade": "A"}
        optimization = {"prompt_improvements": []}

        generator = ReportGenerator(gemini_client=mock_client)
        report = generator.generate_executive_report(metrics, failures, rca, score, optimization)
        self.assertIn("PhoenixGuard Reliability Report", report)

    def test_report_generator_fallback(self) -> None:
        """Verify ReportGenerator returns programmatic markdown report when no client is present."""
        generator = ReportGenerator(gemini_client=None)
        generator.client = None

        metrics = {"success_rate": 80.0, "avg_latency": 3.4}
        failures = [{"issue": "Test Latency", "severity": "Medium", "explanation": "took 8s"}]
        rca = {"root_cause": "API Delay", "confidence": "High", "recommended_fix": "Timeout reduction"}
        score = {"score": 78.2, "grade": "C", "components": {"success_rate_points": 80.0}}
        optimization = {"prompt_improvements": ["Strict timeouts"]}

        report = generator.generate_executive_report(metrics, failures, rca, score, optimization)
        self.assertIn("# PhoenixGuard Reliability Report", report)
        self.assertIn("Health Score: **78.2%** (Grade: **C**)", report)
        self.assertIn("API Delay", report)


if __name__ == "__main__":
    unittest.main()
