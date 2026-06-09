# Technical Design — PhoenixGuard

This document provides a detailed technical description of the classes, modules, scoring formulas, and orchestration paths in **PhoenixGuard**.

## Module Specifications

### 1. Observability API Gateway
* **Module**: [tools/phoenix_mcp_client.py](file:///c:/Users/PC/Desktop/arize-agent/tools/phoenix_mcp_client.py)
* **Class**: `PhoenixMCPClient`
* **Public Interface**:
  * `get_recent_traces(limit: int = 20) -> list[dict]`
  * `get_recent_sessions(limit: int = 20) -> list[dict]`
  * `get_prompts() -> list[dict]`
  * `get_experiments() -> list[dict]`
  * `get_datasets() -> list[dict]`
  * `data_source` property (returns `"LIVE_PHOENIX"` or `"MOCK_DATA"`)
* **Under the Hood**: Auto-detects live connection credentials. If missing or if connection fails, triggers high-fidelity trace generators in [demo/demo_data.py](file:///c:/Users/PC/Desktop/arize-agent/demo/demo_data.py).

### 2. Trace Statistics Engine
* **Module**: [agents/trace_analyzer.py](file:///c:/Users/PC/Desktop/arize-agent/agents/trace_analyzer.py)
* **Class**: `TraceAnalyzer`
* **Method**: `analyze_traces(traces: list[dict]) -> dict`
* **Logic**: Iterates over all spans inside traces. Checks if `status_code == 'ERROR'` to flag trace failures. Parses ISO 8601 timestamps dynamically to compute latency. Aggregates prompt and completion tokens.

### 3. Anomaly Detector
* **Module**: [agents/failure_detector.py](file:///c:/Users/PC/Desktop/arize-agent/agents/failure_detector.py)
* **Class**: `FailureDetector`
* **Method**: `detect_failures(traces: list[dict], metrics: dict) -> list[dict]`
* **Heuristics**:
  * Latency > 5.0 seconds in any span
  * Tool executions with `ERROR` status code
  * Token usage > 8,000 total tokens
* **Reasoning**: Passes clean trace structures to Gemini 2.5 Flash to group anomalies and determine severity (High, Medium, Low). Falls back to rule-based diagnostics if Gemini returns error code 503/400.

### 4. Diagnostic Root Cause Agent
* **Module**: [agents/root_cause_analyzer.py](file:///c:/Users/PC/Desktop/arize-agent/agents/root_cause_analyzer.py)
* **Class**: `RootCauseAnalyzer`
* **Method**: `analyze_root_cause(metrics: dict, failures: list[dict]) -> dict`
* **Reasoning**: Feeds failures list and statistical metrics to Gemini 2.5 Flash to diagnose why the failures are happening and prescribe actionable fixes (e.g. timeout handler adjustments).

### 5. Instruction Optimization Agent
* **Module**: [agents/prompt_optimizer.py](file:///c:/Users/PC/Desktop/arize-agent/agents/prompt_optimizer.py)
* **Class**: `PromptOptimizer`
* **Method**: `optimize_prompt(traces: list[dict], current_prompt: str) -> dict`
* **Reasoning**: Analyzes prompt guidelines against traces to locate logical gaps and outputs prompt improvements along with a rewritten system instruction template.

### 6. Executive Report Compiler
* **Module**: [agents/report_generator.py](file:///c:/Users/PC/Desktop/arize-agent/agents/report_generator.py)
* **Class**: `ReportGenerator`
* **Method**: `generate_executive_report(metrics: dict, failures: list[dict], rca: dict, score: dict, optimization: dict) -> str`
* **Reasoning**: Uses Gemini to synthesize metrics, root causes, score details, and prompt updates into a polished Markdown executive dashboard report.

---

## Reliability Scoring Logic

The scoring engine is defined in [tools/scoring.py](file:///c:/Users/PC/Desktop/arize-agent/tools/scoring.py). It aggregates metrics into a consolidated score out of 100 using a weighted formula:

$$Score = (SuccessRate \times 0.40) + (LatencyScore \times 0.20) + (ToolQualityScore \times 0.20) + (ErrorRateScore \times 0.20)$$

### 1. Success Rate Score (40% Weight)
* Directly mapped to the percentage of successful traces (traces where no span failed).
* Success Rate Points = `success_rate` (0–100)

### 2. Latency Score (20% Weight)
* Maps average latency to points:
  * If average latency $\le 1.0$s: $100$ points
  * If average latency $> 1.0$s: $Max(0.0, 100.0 - (avg\_latency - 1.0) \times 10.0)$ (drops 10% per second of delay)

### 3. Tool Usage Quality Score (20% Weight)
* Measures the percentage of successful tool calls:
  * If no tool calls occurred: $100.0$ points
  * Otherwise: $Max(0.0, 100.0 - (tool\_failures / total\_tool\_calls \times 100.0))$

### 4. Error Rate Score (20% Weight)
* Inverse of trace failure rate:
  * Points = $Max(0.0, 100.0 - failure\_rate)$

### 5. Grade Matrix
* Score $\ge 90$: **Grade A**
* Score $\ge 80$: **Grade B**
* Score $\ge 70$: **Grade C**
* Score $\ge 60$: **Grade D**
* Score $< 60$: **Grade F**
