# Project Overview — PhoenixGuard

PhoenixGuard is a self-improving AI Reliability Engineer designed to address the challenges of observability, testing, and prompting in agentic LLM systems.

## Problem Statement
Modern AI agents are increasingly deployed in business-critical processes (customer support, data ingestion, system maintenance). However, developers often face significant difficulties:
1. **Silent Failures**: Agents fail silently, hallucinate parameters, or hit API limits, which are only discovered after users complain.
2. **Context Drifts**: Observability data (traces and span metrics) is generated in massive volumes but rarely analyzed systematically to improve system reliability.
3. **Manual Prompt Engineering**: Diagnosing prompt degradation or edge cases is a slow, manual process of trial and error.

---

## Solution
PhoenixGuard bridges the gap between **Observability (Arize Phoenix)** and **Automation (Google ADK)** by enabling agents to inspect their own operational traces, identify reliability issues, calculate performance scores, and optimize their own system instructions.

It establishes an automated self-analysis loop:
1. **Traces Collection**: OpenTelemetry instrumentation captures every LLM and tool span and streams them to Phoenix Cloud.
2. **Analysis and Scoring**: Multi-agent pipelines evaluate success rates, latency averages, tool execution reliability, and token consumption.
3. **Self-Correction**: Prompt Optimizer reviews failures and rewrites instructions to prevent repeat errors.

---

## Value Proposition
* **Resilience**: Agents learn from their mistakes in production, automatically mitigating validation errors and API usage bottlenecks.
* **Measurable Reliability**: Provides engineering teams with concrete scores and grades (A–F) using a transparent scoring math formula.
* **Zero Downtime Optimization**: Optimizes prompt instructions continuously based on actual telemetry logs.

---

## Why PhoenixGuard?
Built specifically for the **Arize x Google Cloud Rapid Agent Hackathon**, PhoenixGuard demonstrates a real-world implementation of agents using their own observability data to improve over time. By isolating connection APIs, utilizing rule-based logic for accuracy, and leveraging Gemini 2.5 Flash for reasoning, it provides a highly robust, enterprise-ready diagnostic tool.
