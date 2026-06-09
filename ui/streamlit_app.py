"""PhoenixGuard — Streamlit Dashboard (Phase 11).

Interactive web dashboard presenting the real-time reliability diagnostics of
the agent. Directly imports and runs the production analysis pipeline classes to
maintain a single source of truth.
"""

from __future__ import annotations

import os
import sys
import streamlit as st

# Ensure parent directory is in search path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.phoenix_mcp_client import PhoenixMCPClient
from agents.trace_analyzer import TraceAnalyzer
from agents.failure_detector import FailureDetector
from agents.root_cause_analyzer import RootCauseAnalyzer
from agents.prompt_optimizer import PromptOptimizer
from agents.report_generator import ReportGenerator
from tools.scoring import calculate_reliability_score
from app import SYSTEM_INSTRUCTION


# ────────────────────────────────────────────────────────────────────
# Streamlit Page Config & Premium Styling
# ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PhoenixGuard — AI Reliability Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Custom premium HSL CSS styling
st.markdown("""
<style>
    /* Dark theme overrides */
    .stApp {
        background-color: #0d0f12;
        color: #e2e8f0;
        font-family: 'Inter', sans-serif;
    }
    
    /* Header card styling */
    .header-card {
        background: linear-gradient(135deg, #1e1b4b 0%, #311042 100%);
        border: 1px solid #4338ca;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 24px;
        box-shadow: 0 4px 20px rgba(67, 56, 202, 0.15);
    }
    
    /* Metric card styling */
    .metric-card {
        background-color: #161a22;
        border: 1px solid #2d3748;
        border-radius: 10px;
        padding: 20px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        text-align: center;
        margin-bottom: 16px;
    }
    .metric-value {
        font-size: 32px;
        font-weight: 700;
        color: #00f2fe;
        margin: 8px 0;
    }
    .metric-label {
        font-size: 14px;
        color: #a0aec0;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    /* Grade card styling */
    .grade-card {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        border: 2px solid #5850ec;
        border-radius: 12px;
        padding: 24px;
        text-align: center;
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.3);
    }
    .grade-value {
        font-size: 96px;
        font-weight: 800;
        color: #38bdf8;
        line-height: 1;
        margin: 10px 0;
        text-shadow: 0 0 20px rgba(56, 189, 248, 0.4);
    }
    
    /* Anomaly Table badges */
    .badge-high {
        background-color: #7f1d1d;
        color: #fecaca;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-medium {
        background-color: #7c2d12;
        color: #ffedd5;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
    .badge-low {
        background-color: #713f12;
        color: #fef9c3;
        padding: 4px 8px;
        border-radius: 4px;
        font-weight: 600;
        font-size: 12px;
    }
    
    /* Diagnosis container */
    .diagnosis-box {
        background-color: #1a1e27;
        border-left: 4px solid #38bdf8;
        padding: 20px;
        border-radius: 0 8px 8px 0;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)


# ────────────────────────────────────────────────────────────────────
# Core State Manager (Single Source of Truth)
# ────────────────────────────────────────────────────────────────────

# Initialize environment keys if missing
if not os.getenv("GOOGLE_API_KEY") and not os.getenv("GENAI_API_KEY"):
    os.environ["GENAI_API_KEY"] = "DUMMY_API_KEY"

@st.cache_resource
def get_mcp_client() -> PhoenixMCPClient:
    """Caching MCP client instance to prevent multiple connections."""
    return PhoenixMCPClient()

client = get_mcp_client()

# Session state initialization for holding report/analysis caches
if "metrics" not in st.session_state:
    st.session_state.metrics = None
if "failures" not in st.session_state:
    st.session_state.failures = []
if "rca" not in st.session_state:
    st.session_state.rca = None
if "score_data" not in st.session_state:
    st.session_state.score_data = None
if "prompt_opt" not in st.session_state:
    st.session_state.prompt_opt = None
if "report" not in st.session_state:
    st.session_state.report = ""


def run_pipeline_analysis() -> None:
    """Runs the exact production analysis agents and caches outputs in session state."""
    with st.spinner("Executing analysis pipeline..."):
        # Fetch Traces
        traces = client.get_recent_traces(limit=40)
        
        # 1. Trace Analyzer
        analyzer = TraceAnalyzer()
        metrics = analyzer.analyze_traces(traces)
        st.session_state.metrics = metrics

        # 2. Failure Detector
        detector = FailureDetector()
        failures = detector.detect_failures(traces, metrics)
        st.session_state.failures = failures

        # 3. Root Cause Analyzer
        rca_analyzer = RootCauseAnalyzer()
        rca = rca_analyzer.analyze_root_cause(metrics, failures)
        st.session_state.rca = rca

        # 4. Reliability Scorer
        score_data = calculate_reliability_score(metrics)
        st.session_state.score_data = score_data

        # 5. Prompt Optimizer
        optimizer = PromptOptimizer()
        prompt_opt = optimizer.optimize_prompt(traces, SYSTEM_INSTRUCTION)
        st.session_state.prompt_opt = prompt_opt

        # 6. Report Generator
        generator = ReportGenerator()
        report = generator.generate_executive_report(metrics, failures, rca, score_data, prompt_opt)
        st.session_state.report = report


# Run initial analysis if not already cached
if st.session_state.metrics is None:
    run_pipeline_analysis()


# ────────────────────────────────────────────────────────────────────
# Header & Data Source Status Badge
# ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="header-card">
    <h1 style="margin:0; font-size: 32px; font-weight:800; background: linear-gradient(to right, #00f2fe, #4facfe); -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
        🛡️ PhoenixGuard Dashboard
    </h1>
    <p style="margin:8px 0 0 0; color:#cbd5e1; font-size:16px;">
        Self-Improving AI Reliability Engineer — Production Observability Portal
    </p>
</div>
""", unsafe_allow_html=True)

# Connection Status Row
col_status, col_actions = st.columns([3, 2])
with col_status:
    if client.data_source == "LIVE_PHOENIX":
        st.markdown(
            "🟢 **Status**: Connected to Live Phoenix Cloud (`LIVE_PHOENIX` collector active)"
        )
    else:
        st.markdown(
            "🟡 **Status**: Running in Sandbox Mode (`MOCK_DATA` fallback active)"
        )

with col_actions:
    btn_col1, btn_col2 = st.columns(2)
    with btn_col1:
        if st.button("🔄 Run Analysis", use_container_width=True):
            run_pipeline_analysis()
            st.rerun()
    with btn_col2:
        auto_refresh = st.checkbox("Auto-Refresh", value=False)
        if auto_refresh:
            st.info("Polling active...")
            # We could add st.empty() timer loops if needed, keeping it simple.


# ────────────────────────────────────────────────────────────────────
# Row 1: Health Score & Trace Statistics
# ────────────────────────────────────────────────────────────────────
st.markdown("---")
col_score, col_metrics = st.columns([1, 2])

with col_score:
    if st.session_state.score_data:
        score_val = st.session_state.score_data["score"]
        grade_val = st.session_state.score_data["grade"]
        
        st.markdown(f"""
        <div class="grade-card">
            <div class="metric-label">Reliability Grade</div>
            <div class="grade-value">{grade_val}</div>
            <div class="metric-value" style="color: #cbd5e1; font-size: 24px;">Score: {score_val}%</div>
        </div>
        """, unsafe_allow_html=True)
        
        # Breakdown bars
        st.markdown("<br><b>Score Components</b>", unsafe_allow_html=True)
        comp = st.session_state.score_data["components"]
        st.progress(comp["success_rate_points"] / 100.0, text=f"Success Rate: {comp['success_rate_points']}%")
        st.progress(comp["latency_points"] / 100.0, text=f"Latency Score: {comp['latency_points']}%")
        st.progress(comp["tool_quality_points"] / 100.0, text=f"Tool Quality: {comp['tool_quality_points']}%")
        st.progress(comp["error_rate_points"] / 100.0, text=f"Error Rate Score: {comp['error_rate_points']}%")

with col_metrics:
    m = st.session_state.metrics
    if m:
        # Metrics cards layout grid
        mc1, mc2, mc3 = st.columns(3)
        with mc1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Total Traces</div>
                <div class="metric-value" style="color:#38bdf8;">{m['total_traces']}</div>
            </div>
            """, unsafe_allow_html=True)
        with mc2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Average Latency</div>
                <div class="metric-value" style="color:#fbbf24;">{m['avg_latency']}s</div>
            </div>
            """, unsafe_allow_html=True)
        with mc3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Success Rate</div>
                <div class="metric-value" style="color:#34d399;">{m['success_rate']}%</div>
            </div>
            """, unsafe_allow_html=True)
            
        mc4, mc5, mc6 = st.columns(3)
        with mc4:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Prompt Tokens</div>
                <div class="metric-value" style="color:#a78bfa;">{int(m['avg_prompt_tokens'])}</div>
            </div>
            """, unsafe_allow_html=True)
        with mc5:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Avg Completion Tokens</div>
                <div class="metric-value" style="color:#c084fc;">{int(m['avg_completion_tokens'])}</div>
            </div>
            """, unsafe_allow_html=True)
        with mc6:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-label">Tool Failures</div>
                <div class="metric-value" style="color:#f87171;">{m['tool_failures']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        # Tool usage frequency chart
        if m["tool_usage_frequency"]:
            st.markdown("##### Tool Execution Frequencies")
            st.bar_chart(m["tool_usage_frequency"])


# ────────────────────────────────────────────────────────────────────
# Row 2: Tabs for Failures, Diagnostics, Prompt Optimizations, Report
# ────────────────────────────────────────────────────────────────────
st.markdown("---")
tab_failures, tab_rca, tab_prompt, tab_report = st.tabs([
    "🚨 Failure Summary", 
    "🔍 Root Cause Analysis", 
    "📝 Prompt Recommendations", 
    "📊 Executive Report"
])

with tab_failures:
    st.subheader("Anomaly and Failure Summary Logs")
    if st.session_state.failures:
        for idx, item in enumerate(st.session_state.failures, 1):
            severity = item.get("severity", "Low")
            issue = item.get("issue", "Issue")
            explanation = item.get("explanation", "")
            
            # Badge selection based on severity
            badge_class = "badge-low"
            if severity.lower() == "high":
                badge_class = "badge-high"
            elif severity.lower() == "medium":
                badge_class = "badge-medium"
                
            st.markdown(f"""
            <div style="background-color: #1a1e27; border: 1px solid #2d3748; padding: 16px; border-radius: 8px; margin-bottom: 12px;">
                <span class="{badge_class}">{severity.upper()}</span>
                <b style="font-size: 16px; margin-left: 8px; color: #f3f4f6;">{issue}</b>
                <p style="margin: 8px 0 0 0; color: #9ca3af; font-size:14px;">{explanation}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No anomalies or failures logged in the evaluated traces.")

with tab_rca:
    st.subheader("Root Cause Diagnostics")
    rca = st.session_state.rca
    if rca:
        st.markdown(f"""
        <div class="diagnosis-box">
            <h4>Primary Diagnosis</h4>
            <p style="font-size: 16px; color: #cbd5e1; line-height: 1.5;">{rca['root_cause']}</p>
            <hr style="border: 0; border-top: 1px solid #2d3748; margin: 15px 0;">
            <div style="display: flex; justify-content: space-between;">
                <div><b>Confidence</b>: <span style="color: #38bdf8;">{rca['confidence'].upper()}</span></div>
                <div><b>Mitigation strategy</b>: <span style="color: #10b981;">{rca['recommended_fix']}</span></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

with tab_prompt:
    st.subheader("Prompt Optimizations and Corrections")
    p = st.session_state.prompt_opt
    if p:
        col_w, col_imp = st.columns(2)
        with col_w:
            st.markdown("#### Identified Prompt Weaknesses")
            for w in p.get("weaknesses", []):
                st.markdown(f"- ❌ {w}")
        with col_imp:
            st.markdown("#### Suggested Improvements")
            for imp in p.get("prompt_improvements", []):
                st.markdown(f"- 💡 {imp}")
                
        st.markdown("---")
        st.markdown("#### Rewritten Prompt Template Suggestion")
        st.code(p.get("rewritten_prompt", ""), language="markdown")

with tab_report:
    st.subheader("Executive Reliability Report")
    if st.session_state.report:
        # Display raw report preview
        st.markdown(st.session_state.report)
    else:
        st.info("No report generated.")
