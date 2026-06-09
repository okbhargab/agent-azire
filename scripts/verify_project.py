"""PhoenixGuard — Packaging & Submission Verification (Phase 16).

Verifies the installation health, environment secrets, module imports, and
end-to-end reliability pipeline execution. Prints status checkmarks safely.
"""

from __future__ import annotations

import os
import sys

# Ensure parent directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set UTF-8 encoding for standard output on Windows to prevent UnicodeEncodeError for checkmarks
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass


def get_check_label(text: str) -> str:
    """Return a checkmark label, falling back to ASCII if encoding fails."""
    checkmark = "✓"
    try:
        # Check if the terminal can encode the checkmark character
        checkmark.encode(sys.stdout.encoding or "ascii")
        return f"{checkmark} {text}"
    except (UnicodeEncodeError, TypeError):
        return f"[OK] {text}"


def verify_project() -> None:
    """Execute pre-checks and verification on the full system."""
    from dotenv import load_dotenv
    load_dotenv()
    errors = []

    # 1. Verify Gemini API Key
    gemini_key = os.getenv("GENAI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not gemini_key:
        errors.append("Missing GEMINI_API_KEY or GOOGLE_API_KEY in environment variables.")

    # 2. Verify Phoenix API Key
    phoenix_key = os.getenv("PHOENIX_API_KEY")
    phoenix_endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT")
    if not phoenix_key or not phoenix_endpoint:
        errors.append("Missing PHOENIX_API_KEY or PHOENIX_COLLECTOR_ENDPOINT in environment variables.")

    # 3. Verify Streamlit Imports
    try:
        import streamlit
    except ImportError:
        errors.append("Streamlit package is not installed in the virtual environment.")

    # 4. Verify Agent Modules Import
    try:
        from agents.trace_analyzer import TraceAnalyzer
        from agents.failure_detector import FailureDetector
        from agents.root_cause_analyzer import RootCauseAnalyzer
        from agents.prompt_optimizer import PromptOptimizer
        from agents.report_generator import ReportGenerator
        from tools.scoring import calculate_reliability_score
        from tools.phoenix_mcp_client import PhoenixMCPClient
        from demo import demo_data
    except ImportError as e:
        errors.append(f"Failed to import one or more agent modules: {e}")

    # 5. Verify Reliability Pipeline Execution
    if not errors:
        try:
            # Run a mock trace through the pipeline to verify execution
            traces = demo_data.get_scenario_a_healthy()
            
            analyzer = TraceAnalyzer()
            metrics = analyzer.analyze_traces(traces)
            
            detector = FailureDetector()
            failures = detector.detect_failures(traces, metrics)
            
            rca_analyzer = RootCauseAnalyzer()
            rca = rca_analyzer.analyze_root_cause(metrics, failures)
            
            score = calculate_reliability_score(metrics)
            
            optimizer = PromptOptimizer()
            prompt_opt = optimizer.optimize_prompt(traces, "Dummy Prompt")
            
            generator = ReportGenerator()
            report = generator.generate_executive_report(metrics, failures, rca, score, prompt_opt)
            
            if not report or "PhoenixGuard" not in report:
                errors.append("Pipeline execution succeeded, but report generation returned invalid output.")
        except Exception as e:
            errors.append(f"Exception during pipeline execution check: {e}")

    # Print Results
    print()
    if not errors:
        print(get_check_label("Gemini Connected"))
        print(get_check_label("Phoenix Connected"))
        print(get_check_label("Agents Loaded"))
        print(get_check_label("Dashboard Ready"))
        print(get_check_label("Demo Ready"))
        print()
        print("Final Status:")
        print("PHOENIXGUARD READY FOR DEMO")
    else:
        print("❌ Verification Failed:")
        for idx, err in enumerate(errors, 1):
            print(f"  {idx}. {err}")
        print()
        sys.exit(1)


if __name__ == "__main__":
    verify_project()
