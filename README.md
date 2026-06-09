# PhoenixGuard — Self-Improving AI Reliability Engineer

> Built for the **Arize × Google Cloud Rapid Agent Hackathon**

PhoenixGuard is an autonomous AI Reliability Engineer that inspects its own operational traces, detects failures, identifies root causes, calculates reliability scores, and optimizes its own prompt instructions.

---

## Technical Stack

| Layer | Technology |
|---|---|
| **Agent Framework** | Google ADK (Agent Development Kit) |
| **Model** | Gemini 2.5 Flash |
| **Telemetry & Observability** | OpenTelemetry + OpenInference Google ADK Instrumentation |
| **Observability Backend** | Arize Phoenix Cloud (Telemetry Storage & Visualization) |
| **Introspection Interface** | Phoenix Python Client API Gateway / MCP |
| **Dashboard** | Streamlit |

---

## System Architecture

```
 User ────> CLI Orchestrator (app.py) ───> Streamlit UI Dashboard (ui/streamlit_app.py)
                    │                                    │
                    ▼                                    ▼
           [Google ADK Agent] ───────────────> [MCP Client Layer]
           (phoenixguard_agent)              (tools/phoenix_mcp_client.py)
                    │                                    │
                    ▼                                    ▼
       [OTEL / OpenInference Provider]        [MCP Server Adapter]
                    │                        (tools/phoenix_mcp_adapter.py)
                    ▼                                    │
           [Arize Phoenix Cloud] ◄──(Queries)── [Phoenix MCP Server]
           (Telemetry Storage)                (@arizeai/phoenix-mcp npx)
                                                         │
                                                         ▼
                                              [Observability Pipeline]
                                              ├── Trace Analyzer
                                              ├── Failure Detector
                                              ├── Root Cause Analyzer
                                              ├── Prompt Optimizer
                                              ├── Reliability Scorer
                                              └── Report Generator
```

---

## Project Structure

```
arize-agent/
├── app.py                          # Main Orchestrator, CLI loop & Command Interceptor
├── requirements.txt                # Project dependencies
├── .env                            # Active environment credentials
├── .env.example                    # Template for environment configuration
├── README.md                       # Setup and documentation
├── agents/
│   ├── __init__.py
│   ├── trace_analyzer.py           # Phase 3: Trace statistics aggregator
│   ├── failure_detector.py         # Phase 4: Rule + LLM anomaly detector
│   ├── root_cause_analyzer.py      # Phase 5: Diagnostic & fix analyzer
│   ├── prompt_optimizer.py         # Phase 6: System instruction optimizer
│   └── report_generator.py        # Phase 8: Markdown dashboard compiler
├── tools/
│   ├── __init__.py
│   ├── agent_tools.py              # Phase 1: Weather + system health tools
│   ├── phoenix_tools.py            # Phase 2: Phoenix SDK API wrapper
│   ├── phoenix_mcp_adapter.py      # compliance: Arize Phoenix MCP Server connection
│   ├── phoenix_mcp_client.py        # Phase 2 Upgrade: Phoenix client manager with SDK fallback
│   └── scoring.py                  # Phase 7: Weighted reliability scoring engine

├── demo/
│   ├── demo_data.py                # Phase 12: Scenario generator (Healthy, Latency, Errors)
│   └── demo_runner.py              # Phase 13: E2E BEFORE/AFTER comparison simulation
├── scripts/
│   └── verify_project.py           # Phase 16: Submission verification pre-check
├── docs/
│   ├── project_overview.md         # Problem and value proposition
│   ├── architecture.md             # Diagrams and data flows
│   ├── technical_design.md         # Module details and scoring math
│   └── demo_script.md              # Live walkthrough and script
├── tests/
│   └── test_agents.py              # Automated unit tests (10 tests)
└── venv/                           # Python virtual environment
```

---

## Installation & Setup

### 1. Clone the repository
```bash
git clone https://github.com/okbhargab/agent-azire.git
cd agent-azire
```

### 2. Create and Activate Virtual Environment
```bash
python -m venv venv
# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
```bash
copy .env.example .env
```
Edit `.env` and fill in your API keys:
* `GOOGLE_API_KEY`: Your Google AI Studio API key.
* `GENAI_API_KEY`: Alias for GOOGLE_API_KEY (both are loaded automatically).
* `PHOENIX_API_KEY`: Your Arize Phoenix Cloud API key.
* `PHOENIX_COLLECTOR_ENDPOINT`: Your Arize Phoenix Collector space URL.

---

## Running PhoenixGuard

### Interactive CLI Mode
Interact with the ADK agent. Any queries matching orchestrator commands will bypass the conversational loop and invoke the self-analysis pipeline directly.
```bash
python app.py
```

### Single-Shot Query Mode
```bash
python app.py --once "Check system health"
```

### Diagnostic Command Flags
Execute specific reliability analysis commands directly from the command line:
* `python app.py --analyze`: Calculate and display trace statistics.
* `python app.py --health`: Display the weighted reliability score and grade.
* `python app.py --root-cause`: Diagnose failures and print actionable fixes.
* `python app.py --prompt`: Review instruction weaknesses and suggest rewritten prompts.
* `python app.py --report`: Compile and display the comprehensive executive reliability Markdown report.

---

## Streamlit Dashboard UI (Phase 11)

Launch the premium Streamlit dark-themed dashboard to view scoring breakdowns, metrics, anomaly tables, and suggested prompt improvements:
```bash
streamlit run ui/streamlit_app.py
```

---

## End-to-End Demo Runner (Phase 13)

Run the simulation showing a Travel Agent's transition from a degraded BEFORE state (F grade) to an optimized AFTER state (A grade) using prompt correction:
```bash
python demo/demo_runner.py
```

---

## Submission Verification Pre-Check (Phase 16)

Run the sanity check script before demo submissions to verify environment variables, package dependencies, imports, and pipeline execution health:
```bash
python scripts/verify_project.py
```
* **Expected Successful Output**:
  ```
  ✓ Gemini Connected
  ✓ Phoenix Connected
  ✓ Agents Loaded
  ✓ Dashboard Ready
  ✓ Demo Ready

  Final Status:
  PHOENIXGUARD READY FOR DEMO
  ```

---

## Automated Unit Testing
Validate parser calculations and LLM reasoning wrappers across all modules:
```bash
python -m unittest tests/test_agents.py
```
* **Expected Output**: `Ran 10 tests in 0.006s -> OK`
