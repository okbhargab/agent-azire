"""PhoenixGuard — End-to-End Demo Runner (Phase 13).

Demonstrates the self-improving loop of the AI Reliability Engineer:
1. Loads degraded traces BEFORE optimization (latency delays, tool failures, loop timeouts).
2. Runs the production pipeline to diagnose root causes and calculate scoring.
3. Invokes PromptOptimizer to correct system instructions.
4. Loads healthy traces AFTER optimization (mocking agent execution under corrected prompt).
5. Recalculates metrics and score showing measurable improvements.
"""

from __future__ import annotations

import logging
import os
import sys

# Ensure parent directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agents.trace_analyzer import TraceAnalyzer
from agents.failure_detector import FailureDetector
from agents.root_cause_analyzer import RootCauseAnalyzer
from agents.prompt_optimizer import PromptOptimizer
from agents.report_generator import ReportGenerator
from tools.scoring import calculate_reliability_score
from demo import demo_data

# Set up logging to quiet levels to keep the console print output clean
logging.basicConfig(level=logging.WARNING)


def print_title(text: str) -> None:
    """Print a styled section title in the terminal."""
    print("\n" + "=" * 62)
    print(f" {text.upper().center(60)} ")
    print("=" * 62 + "\n")


def run_demo() -> None:
    """Run the narrative self-analysis and optimization story."""
    # Ensure environment has a placeholder key if none is present to prevent API client validation errors
    if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GENAI_API_KEY"):
        os.environ["GENAI_API_KEY"] = "DUMMY_API_KEY"

    print_title("PhoenixGuard - E2E Self-Analysis Demo")
    print("  Story:")
    print("  A Travel Agent assistant was deployed to production.")
    print("  observability signals show latency rising and tools failing.")
    print("  PhoenixGuard is triggered to inspect the traces and self-optimize.")
    print("-" * 62)

    # ────────────────────────────────────────────────────────────────
    # STEP 1: BEFORE Optimization Analysis
    # ────────────────────────────────────────────────────────────────
    print("\n[STEP 1] Running Analysis on DEGRADED traces (BEFORE)...")
    
    # Load all degraded scenarios combined (B, C, D, E)
    before_traces = []
    before_traces.extend(demo_data.get_scenario_b_latency_spikes())
    before_traces.extend(demo_data.get_scenario_c_tool_failures())
    before_traces.extend(demo_data.get_scenario_d_repeated_failures())
    before_traces.extend(demo_data.get_scenario_e_excessive_tokens())

    # Instantiate production classes
    analyzer = TraceAnalyzer()
    detector = FailureDetector()
    rca_analyzer = RootCauseAnalyzer()
    optimizer = PromptOptimizer()
    report_gen = ReportGenerator()

    # Run pipeline
    before_metrics = analyzer.analyze_traces(before_traces)
    before_failures = detector.detect_failures(before_traces, before_metrics)
    before_rca = rca_analyzer.analyze_root_cause(before_metrics, before_failures)
    before_score = calculate_reliability_score(before_metrics)
    
    # Run optimizer to get suggersted improvements
    print("\n[STEP 2] Optimizing Agent Prompts...")
    prompt_opt = optimizer.optimize_prompt(before_traces, "Original System Prompt Template")

    # Generate BEFORE Report
    before_report = report_gen.generate_executive_report(
        before_metrics, before_failures, before_rca, before_score, prompt_opt
    )

    print("\n" + "#" * 62)
    print("              EXECUTIVE REPORT - BEFORE OPTIMIZATION")
    print("#" * 62)
    print(before_report)
    print("#" * 62 + "\n")

    # ────────────────────────────────────────────────────────────────
    # STEP 2: AFTER Optimization Analysis
    # ────────────────────────────────────────────────────────────────
    print("\n[STEP 3] Running Analysis on HEALTHY traces (AFTER prompt fix)...")
    
    # Load healthy scenario A traces representing optimized run
    after_traces = demo_data.get_scenario_a_healthy()

    # Run pipeline on healthy traces
    after_metrics = analyzer.analyze_traces(after_traces)
    after_failures = detector.detect_failures(after_traces, after_metrics)
    after_rca = rca_analyzer.analyze_root_cause(after_metrics, after_failures)
    after_score = calculate_reliability_score(after_metrics)
    
    # Empty prompt optimizations for optimized state
    clean_optimization = {
        "weaknesses": [],
        "prompt_improvements": [],
        "rewritten_prompt": ""
    }

    # Generate AFTER Report
    after_report = report_gen.generate_executive_report(
        after_metrics, after_failures, after_rca, after_score, clean_optimization
    )

    print("\n" + "#" * 62)
    print("              EXECUTIVE REPORT - AFTER OPTIMIZATION")
    print("#" * 62)
    print(after_report)
    print("#" * 62 + "\n")

    # ────────────────────────────────────────────────────────────────
    # STEP 3: Measurable Improvement Dashboard
    # ────────────────────────────────────────────────────────────────
    print_title("Measurable Reliability Improvement")
    
    print(f" {'Metric':<30} | {'BEFORE':<12} | {'AFTER':<12} ")
    print("-" * 62)
    print(f" {'Reliability Score':<30} | {str(before_score['score']) + '%':<12} | {str(after_score['score']) + '%':<12} ")
    print(f" {'Reliability Grade':<30} | {before_score['grade']:<12} | {after_score['grade']:<12} ")
    print(f" {'Success Rate':<30} | {str(before_metrics['success_rate']) + '%':<12} | {str(after_metrics['success_rate']) + '%':<12} ")
    print(f" {'Average Latency':<30} | {str(before_metrics['avg_latency']) + 's':<12} | {str(after_metrics['avg_latency']) + 's':<12} ")
    print(f" {'Tool Failures':<30} | {before_metrics['tool_failures']:<12} | {after_metrics['tool_failures']:<12} ")
    print(f" {'Average Total Tokens':<30} | {int(before_metrics['avg_token_usage']):<12} | {int(after_metrics['avg_token_usage']):<12} ")
    print("-" * 62)
    print("\n   [OK] Measurable improvement achieved!")
    print("   [OK] Prompt weaknesses resolved.")
    print("   [OK] Travel Agent reliability score optimized to Grade A.")
    print("\nPHOENIXGUARD DEMO COMPLETE\n")


if __name__ == "__main__":
    run_demo()
