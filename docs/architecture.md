# Architecture & Data Flow — PhoenixGuard

This document details the system architecture and sequence flows of **PhoenixGuard**, highlighting the integration of **Google ADK**, **Gemini 2.5 Flash**, and **Arize Phoenix**.

## System Architecture

```mermaid
graph TD
    User([User / CLI]) -->|Query / Command| Orchestrator[app.py Orchestrator]
    
    subgraph Agent Loop
        Orchestrator -->|Run Conversation| ADK[Google ADK Agent]
        ADK -->|Generate Span| OpenTelemetry[OTEL Instrumentation]
        ADK -->|Execute Tool| Tool[agent_tools.py]
    end
    
    OpenTelemetry -->|Stream Telemetry| PhoenixCloud[Arize Phoenix Cloud]
    
    subgraph Observability Pipeline
        Orchestrator -->|Request Logs| MCP[phoenix_mcp_client.py]
        MCP -->|Fetch Traces/Spans| Adapter[phoenix_mcp_adapter.py]
        Adapter -->|Stdio JSONRPC| MCPServer[Phoenix MCP Server]
        MCPServer -->|REST APIs| PhoenixCloud
        MCP -->|SDK Fallback| SDKTools[phoenix_tools.py]
        SDKTools -->|REST APIs| PhoenixCloud
        MCP -->|Mock Fallback| Mocks[demo_data.py Mocks]
        
        Orchestrator -->|Analyze Traces| TraceAnalyzer[TraceAnalyzer]
        Orchestrator -->|Detect Failures| FailureDetector[FailureDetector]
        Orchestrator -->|Diagnose| RCA[RootCauseAnalyzer]
        Orchestrator -->|Optimize| PromptOptimizer[PromptOptimizer]
        Orchestrator -->|Score| Scorer[scoring.py]
        Orchestrator -->|Report| ReportGen[ReportGenerator]
    end
    
    TraceAnalyzer -.-> FailureDetector
    FailureDetector -.-> RCA
    RCA -.-> PromptOptimizer
    Scorer -.-> ReportGen
    PromptOptimizer -.-> ReportGen
```

---

## Component Interactions

1. **Google ADK Agent (`app.py`)**:
   Runs the main agent loop. Wrapped in `google-adk`'s `Runner` with an `InMemorySessionService`. It executes general tools (`get_weather`, `get_system_health`) and self-introspection tools (`get_phoenix_traces`, etc.).
   
2. **OpenTelemetry Instrumentation**:
   `GoogleADKInstrumentor` listens to all agent and LLM spans and routes them to Arize Phoenix Cloud using `register(project_name="phoenixguard")`.

3. **Phoenix MCP Client (`phoenix_mcp_client.py`) & Adapter (`phoenix_mcp_adapter.py`)**:
   Acts as the central API gateway. It auto-detects connectivity and connects to Phoenix Cloud via the **official Arize Phoenix MCP Server** using Stdio transport. If the MCP server is not available, it falls back to the **Phoenix Python SDK REST Client (`PhoenixTools`)**, and then to local high-fidelity mock data if offline.


4. **Orchestrator Pipeline**:
   Coordinates the analysis flow:
   * **TraceAnalyzer** parses traces and computes latency, token, and success averages.
   * **FailureDetector** evaluates rules (latency > 5s, tool crashes, tokens > 8k) and calls Gemini to identify pattern errors.
   * **RootCauseAnalyzer** correlates metrics to diagnose root causes and recommend fixes.
   * **PromptOptimizer** suggestions prompt changes based on errors.
   * **Scorer** aggregates components into a weighted score (40% Success, 20% Latency, 20% Tool Quality, 20% Error Rate) and letter grade (A–F).
   * **ReportGenerator** compiles the dashboard Markdown report.

---

## Data Flow Sequence

```mermaid
sequenceDiagram
    autonumber
    actor User as Engineer
    participant Orch as app.py Orchestrator
    participant MCP as phoenix_mcp_client.py
    participant TA as TraceAnalyzer
    participant FD as FailureDetector
    participant RCA as RootCauseAnalyzer
    participant PO as PromptOptimizer
    participant Sc as scoring.py
    participant RG as ReportGenerator

    User->>Orch: Run Analysis ("--report" / "Generate report")
    Orch->>MCP: get_recent_traces(limit=20)
    MCP-->>Orch: Returns Traces (Live/Mock)
    Orch->>TA: analyze_traces(traces)
    TA-->>Orch: Computed Metrics (Success, Latency, Tokens)
    Orch->>FD: detect_failures(traces, metrics)
    FD-->>Orch: Log of Anomalies (Severity, Explanation)
    Orch->>RCA: analyze_root_cause(metrics, failures)
    RCA-->>Orch: Root Cause Diagnosis & Recommended Fix
    Orch->>PO: optimize_prompt(traces, current_prompt)
    PO-->>Orch: weaknesses & rewritten_prompt
    Orch->>Sc: calculate_reliability_score(metrics)
    Sc-->>Orch: final score & letter grade (A-F)
    Orch->>RG: generate_executive_report(metrics, failures, rca, score, optimization)
    RG-->>Orch: markdown dashboard report
    Orch->>User: Display Reliability Dashboard
```
