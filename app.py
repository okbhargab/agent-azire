"""PhoenixGuard: Self-Improving AI Reliability Engineer.

Main entry point.  Creates a Google ADK agent powered by Gemini 2.5 Flash
with two functional tools, fully traced via OpenInference to Phoenix Cloud.

Usage:
    python app.py              # interactive CLI
    python app.py --once "msg" # single-shot query
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys

from dotenv import load_dotenv

load_dotenv()

# Google ADK reads GOOGLE_API_KEY from the environment.
# Map the existing GENAI_API_KEY if GOOGLE_API_KEY is not set.
if not os.getenv("GOOGLE_API_KEY") and os.getenv("GENAI_API_KEY"):
    os.environ["GOOGLE_API_KEY"] = os.getenv("GENAI_API_KEY", "")

# ── 2. Phoenix tracing (MUST happen before any ADK import) ─────────
PHOENIX_PROJECT = os.getenv("PHOENIX_PROJECT_NAME", "phoenixguard")

try:
    from phoenix.otel import register  # noqa: E402
    from openinference.instrumentation.google_adk import GoogleADKInstrumentor  # noqa: E402
    PHOENIX_TRACING_AVAILABLE = True
except ImportError:
    PHOENIX_TRACING_AVAILABLE = False

if PHOENIX_TRACING_AVAILABLE:
    try:
        tracer_provider = register(project_name=PHOENIX_PROJECT)
        GoogleADKInstrumentor().instrument(tracer_provider=tracer_provider)
    except Exception as e:
        print(f"Warning: Failed to initialize Phoenix SDK tracing: {e}", file=sys.stderr)

# ── 3. ADK imports (after instrumentation is active) ────────────────
from google.adk.agents import Agent  # noqa: E402
from google.adk.runners import Runner  # noqa: E402
from google.adk.sessions import InMemorySessionService  # noqa: E402
from google.genai import types  # noqa: E402

from tools.agent_tools import get_weather, get_system_health  # noqa: E402
from tools.phoenix_mcp_client import (  # noqa: E402
    get_phoenix_projects,
    get_phoenix_traces,
    get_phoenix_spans,
    get_phoenix_sessions,
    get_phoenix_datasets,
    get_phoenix_experiments,
)

# ── Import diagnostic pipeline agents and scoring tools ───────────
from agents.trace_analyzer import TraceAnalyzer  # noqa: E402
from agents.failure_detector import FailureDetector  # noqa: E402
from agents.root_cause_analyzer import RootCauseAnalyzer  # noqa: E402
from agents.prompt_optimizer import PromptOptimizer  # noqa: E402
from agents.report_generator import ReportGenerator  # noqa: E402
from tools.scoring import calculate_reliability_score  # noqa: E402
from tools import phoenix_mcp_client  # noqa: E402

# ── 4. Logging ──────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s │ %(levelname)-7s │ %(name)s │ %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("phoenixguard")

# ── 5. Constants ────────────────────────────────────────────────────
APP_NAME = "phoenixguard"
USER_ID = "default_user"
MODEL = os.getenv("PHOENIXGUARD_MODEL", "gemini-2.5-flash")

SYSTEM_INSTRUCTION = """\
You are **PhoenixGuard**, an AI Reliability Engineer built for production
observability.  You can monitor your own traces and analyze agent performance.

## Your Capabilities

### General Tools
1. **Weather Lookup** – Use `get_weather` for weather in any city.
2. **System Health** – Use `get_system_health` for CPU, memory, disk, uptime.

### Self-Introspection Tools (Phoenix)
3. **List Projects** – Use `get_phoenix_projects` to list all Phoenix projects.
4. **View Traces** – Use `get_phoenix_traces` to retrieve recent traces with
   timing and token counts.
5. **View Spans** – Use `get_phoenix_spans` to see individual spans (LLM calls,
   tool executions, agent runs).  Filter by span_kind: 'LLM', 'TOOL', 'AGENT',
   'CHAIN'.
6. **View Sessions** – Use `get_phoenix_sessions` to see user conversation
   sessions.
7. **List Datasets** – Use `get_phoenix_datasets` to list evaluation datasets.
8. **List Experiments** – Use `get_phoenix_experiments` to list experiments.

## Guidelines
- Always call the appropriate tool when the user's question matches a tool.
- Present tool results clearly with units (°C, %, GB, km/h).
- When analyzing traces, summarise key metrics: latency, token usage, status.
- Be concise, precise, and actionable.
- If a tool returns an error, report it honestly and suggest next steps.
"""

# ── 6. Build the ADK Agent ──────────────────────────────────────────
root_agent = Agent(
    name="phoenixguard_agent",
    model=MODEL,
    instruction=SYSTEM_INSTRUCTION,
    tools=[
        get_weather,
        get_system_health,
        get_phoenix_projects,
        get_phoenix_traces,
        get_phoenix_spans,
        get_phoenix_sessions,
        get_phoenix_datasets,
        get_phoenix_experiments,
    ],
)

# ── 7. Runner + Session Service ─────────────────────────────────────
session_service = InMemorySessionService()
runner = Runner(
    agent=root_agent,
    app_name=APP_NAME,
    session_service=session_service,
)


# ── 8. Core run function ────────────────────────────────────────────
async def run_agent(user_message: str, session_id: str) -> str:
    """Send *user_message* to the agent and return the final text response."""
    content = types.Content(
        role="user",
        parts=[types.Part(text=user_message)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content,
    ):
        if event.is_final_response():
            if event.content and event.content.parts:
                final_text = event.content.parts[0].text
    return final_text


# ── 8b. Main Orchestrator Pipeline (Phase 9) ──────────────────────────
def run_pipeline(user_input: str) -> bool:
    """Interceptors to run trace analysis agents and formatting dashboards.

    Args:
        user_input: The user query string.

    Returns:
        True if the query matched a pipeline command and was handled, otherwise False.
    """
    cmd = user_input.strip().lower()

    # Exact or sub-phrase matching for Phase 9 commands
    is_health_score = "show health score" in cmd or cmd == "health score"
    is_analyze_traces = "analyze my traces" in cmd or cmd == "analyze traces"
    is_root_causes = "find root causes" in cmd or cmd == "find root cause" or cmd == "root causes"
    is_improve_prompt = "improve my prompt" in cmd or cmd == "improve prompt"
    is_generate_report = "generate reliability report" in cmd or cmd == "generate report" or cmd == "reliability report"

    if not (is_health_score or is_analyze_traces or is_root_causes or is_improve_prompt or is_generate_report):
        return False

    print("\n[PhoenixGuard] Executing self-analysis pipeline...")

    try:
        # 1. Fetch Traces
        traces = phoenix_mcp_client.get_recent_traces(limit=20)
        
        # 2. Run Trace Analyzer
        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(traces)

        # 3. Analyze Traces Command
        if is_analyze_traces:
            print("\n" + "=" * 50)
            print("                 TRACE ANALYSIS                 ")
            print("=" * 50)
            print(f"Total Traces Evaluated  : {metrics['total_traces']}")
            print(f"Success Rate            : {metrics['success_rate']}%")
            print(f"Failure Rate            : {metrics['failure_rate']}%")
            print(f"Average Latency         : {metrics['avg_latency']}s")
            print(f"Average Total Tokens    : {metrics['avg_token_usage']}")
            print(f"Average Prompt Tokens   : {metrics['avg_prompt_tokens']}")
            print(f"Average Completion Tokens: {metrics['avg_completion_tokens']}")
            print("\nTool Usage Frequencies  :")
            for tool, count in metrics['tool_usage_frequency'].items():
                print(f"  - {tool}: {count} calls")
            print(f"Total Tool Failures     : {metrics['tool_failures']}")
            print("=" * 50 + "\n")
            return True

        # Run Failure Detector (required for Root Cause, Prompt Opt, and Reports)
        detector = FailureDetector()
        failures = detector.detect_failures(traces, metrics)

        # 4. Show Health Score Command
        if is_health_score:
            score_data = calculate_reliability_score(metrics)
            print("\n" + "=" * 50)
            print("                  HEALTH SCORE                  ")
            print("=" * 50)
            print(f"Reliability Score : **{score_data['score']}/100**")
            print(f"Grade             : **{score_data['grade']}**")
            print("\nComponents Breakdown:")
            print(f"  - Success Rate Points: {score_data['components']['success_rate_points']}/100")
            print(f"  - Latency Points     : {score_data['components']['latency_points']}/100")
            print(f"  - Tool Quality Points: {score_data['components']['tool_quality_points']}/100")
            print(f"  - Error Rate Points  : {score_data['components']['error_rate_points']}/100")
            print("=" * 50 + "\n")
            return True

        # 5. Find Root Causes Command
        if is_root_causes:
            rca_analyzer = RootCauseAnalyzer()
            rca = rca_analyzer.analyze_root_cause(metrics, failures)
            print("\n" + "=" * 50)
            print("             ROOT CAUSE ANALYSIS                ")
            print("=" * 50)
            print(f"Root Cause      : {rca['root_cause']}")
            print(f"Confidence      : {rca['confidence']}")
            print(f"Recommended Fix : {rca['recommended_fix']}")
            print("=" * 50 + "\n")
            return True

        # 6. Improve My Prompt Command
        if is_improve_prompt:
            optimizer = PromptOptimizer()
            prompt_opt = optimizer.optimize_prompt(traces, SYSTEM_INSTRUCTION)
            print("\n" + "=" * 50)
            print("             PROMPT OPTIMIZATION                ")
            print("=" * 50)
            print("Weaknesses Found:")
            for w in prompt_opt['weaknesses']:
                print(f"  - {w}")
            print("\nImprovements Suggestion:")
            for imp in prompt_opt['prompt_improvements']:
                print(f"  - {imp}")
            print("\nRewritten Prompt:")
            print("-" * 50)
            print(prompt_opt['rewritten_prompt'])
            print("-" * 50)
            print("=" * 50 + "\n")
            return True

        # 7. Generate Reliability Report Command
        if is_generate_report:
            rca_analyzer = RootCauseAnalyzer()
            rca = rca_analyzer.analyze_root_cause(metrics, failures)

            optimizer = PromptOptimizer()
            prompt_opt = optimizer.optimize_prompt(traces, SYSTEM_INSTRUCTION)

            score_data = calculate_reliability_score(metrics)

            generator = ReportGenerator()
            report = generator.generate_executive_report(metrics, failures, rca, score_data, prompt_opt)
            print("\n" + "=" * 50)
            print("           EXECUTIVE RELIABILITY REPORT         ")
            print("=" * 50)
            print(report)
            print("=" * 50 + "\n")
            return True

    except Exception as exc:
        logger.error("Error executing self-analysis pipeline: %s", exc, exc_info=True)
        print(f"\n[ERROR] Pipeline error: {exc}\n")
        return True

    return False


# ── 9. Interactive CLI loop ─────────────────────────────────────────
async def interactive_loop() -> None:
    """Run an interactive terminal session with PhoenixGuard."""
    collector = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "local")

    print()
    print("=" * 62)
    print("   PhoenixGuard — AI Reliability Engineer")
    print(f"   Model   : {MODEL}")
    print(f"   Phoenix : {PHOENIX_PROJECT}")
    print(f"   Tracing : {collector}")
    print("=" * 62)
    print()
    print("  Type a message to interact with PhoenixGuard.")
    print("  Try: 'What is the weather in Tokyo?'")
    print("  Try: 'Check system health'")
    print("  Try: 'Show me my recent traces'")
    print("  Try: 'What projects exist in Phoenix?'")
    print("  Type 'quit' to exit.")
    print()

    # Create a persistent session for the conversation
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    logger.info("Session created: %s", session.id)

    while True:
        try:
            user_input = input("You > ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        logger.info("User query: %s", user_input[:120])

        try:
            # Check if it was handled by the orchestrator pipeline (Phase 9)
            if run_pipeline(user_input):
                continue
            response = await run_agent(user_input, session.id)
            print(f"\nPhoenixGuard > {response}\n")
        except Exception as exc:
            logger.error("Agent error: %s", exc, exc_info=True)
            print(f"\n[ERROR] Error: {exc}\n")


# ── 10. Single-shot mode ────────────────────────────────────────────
async def single_shot(message: str) -> None:
    """Run a single query and exit (useful for scripting / testing)."""
    # Check if the query is a pipeline command (Phase 9)
    if run_pipeline(message):
        return

    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
    )
    response = await run_agent(message, session.id)
    print(response)


# ── 11. Entry point ─────────────────────────────────────────────────
def main() -> None:
    """CLI entry point with validation."""
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("ERROR: GOOGLE_API_KEY (or GENAI_API_KEY) is not set.")
        print("       Add it to your .env file.  See .env.example.")
        sys.exit(1)

    # CLI flags support (Phase 9)
    if len(sys.argv) >= 2:
        flag = sys.argv[1].lower()
        if flag == "--analyze":
            run_pipeline("Analyze my traces")
            return
        elif flag == "--report":
            run_pipeline("Generate reliability report")
            return
        elif flag == "--root-cause":
            run_pipeline("Find root causes")
            return
        elif flag == "--prompt":
            run_pipeline("Improve my prompt")
            return
        elif flag == "--health":
            run_pipeline("Show health score")
            return

    # --once "message" for single-shot mode
    if len(sys.argv) >= 3 and sys.argv[1] == "--once":
        asyncio.run(single_shot(" ".join(sys.argv[2:])))
    else:
        asyncio.run(interactive_loop())


if __name__ == "__main__":
    main()
