# Demo Script & Judge Presentation Guide

This guide outlines the exact script and CLI/Streamlit commands to run during a live demo or to present in a hackathon video.

---

## 1. Quick Presentation Outline (3 Minutes)

* **0:00 - 0:45: The Problem & Solution Pitch**
  "Modern LLM agents deployed in production frequently suffer from silent failures, context loops, and API limits. Teams only find out when users complain. Meet **PhoenixGuard**: a self-improving AI Reliability Engineer that monitors its own observability data and automatically fixes its prompt instructions."
* **0:45 - 1:45: The Streamlit Dashboard (Observability Portal)**
  "Let's look at the active dashboard. We see a status badge indicating whether we are connected to Live Phoenix Cloud or running in a local mock sandbox. We have score cards, latency breakdowns, and anomaly tables sorted by severity. Let's run a live analysis..."
* **1:45 - 2:30: The End-to-End Self-Correction Demo**
  "Let's run the E2E Demo simulation. We simulate a degraded Travel Agent assistant. First, PhoenixGuard detects latency spikes, tool permission errors, and retry loops. Our score starts at Grade F (41%). PhoenixGuard analyzes the root causes and suggest prompt improvements. It then deploys the rewritten prompt, bringing the success rate to 100% and score to Grade A (99%)."
* **2:30 - 3:00: Summary & Value**
  "By bridging Arize Phoenix and Google ADK, PhoenixGuard enables agents to observe, diagnose, and self-improve continuously."

---

## 2. Command Walkthrough

### Step 1: Run the E2E Demo Scenario (CLI Mode)
Execute this command in the terminal to show the self-improvement loop:
```powershell
python demo/demo_runner.py
```
* **Expected Output**:
  * Step 1 analyzes degraded traces, displaying a score of `41.3% (Grade: F)`. It lists failures (e.g. psutil AccessDenied, API timeout, loops).
  * Step 2 runs prompt optimizer, outputting weaknesses and suggested prompt fixes.
  * Step 3 analyzes optimized traces after the prompt is deployed. The score rises to `99.6% (Grade: A)`.
  * Prints a comparison metrics dashboard showing latency dropping from `7.0s` to `1.2s` and failures dropping to `0`.

---

### Step 2: Run the Streamlit Dashboard (UI Mode)
Execute this command to launch the web dashboard:
```powershell
streamlit run ui/streamlit_app.py
```
* **Expected Output**:
  * Opens your default browser at `http://localhost:8501`.
  * Shows status badge: `🟢 Connected to Live Phoenix Cloud` or `🟡 Running in Sandbox Mode`.
  * Displays a gauge progress bar of your reliability grade.
  * Lists individual tabs:
    * **Failure Summary**: Color-coded cards showing severity and details.
    * **Root Cause Analysis**: Diagnosis box showing confidence level.
    * **Prompt Recommendations**: Multi-column comparison of prompt weaknesses and the rewritten instruction template.
    * **Executive Report**: Markdown document compiled by the Report Generator.
  * Clicking **Run Analysis** fetches the latest traces and re-evaluates the pipeline.

---

### Step 3: Run Interactive Conversational Agent
Interact directly with the agent:
```powershell
python app.py
```
* **Expected Query**:
  * Type: `Show health score`
    * **Expected Response**: Displays your numerical score and grade components directly in the CLI.
  * Type: `Generate reliability report`
    * **Expected Response**: Displays the executive markdown report.
  * Type: `What is the weather in Paris?`
    * **Expected Response**: Invokes tool, returns simulated weather, and sends OTEL spans to Phoenix Cloud.
