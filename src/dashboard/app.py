"""
Assurance CI — Traceability Register Viewer
Streamlit dashboard for approvers to review the story→commit→test→gate evidence chain.
"""
import html
import json
from pathlib import Path

import streamlit as st

# ─── Design system tokens (Pharma Compliance Portal palette) ────────────────
st.set_page_config(
    page_title="Assurance CI — Register",
    page_icon="🔒",
    layout="wide",
)

_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=IBM+Plex+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {
    background-color: #F8FAFF !important;
    color: #1A2333 !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
}

/* Page title */
.ac-title {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    color: #1A2333;
    margin-bottom: 0.25rem;
}
.ac-subtitle {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.875rem;
    color: #6B7D96;
    margin-bottom: 2rem;
}

/* Metric cards */
.metric-row { display: flex; gap: 16px; margin-bottom: 2rem; }
.metric-card {
    flex: 1;
    background: #FFFFFF;
    border: 1px solid #D8E2F0;
    border-radius: 8px;
    padding: 1.25rem 1.5rem;
    box-shadow: 0 1px 3px rgba(0,91,171,0.06), 0 4px 16px rgba(0,91,171,0.08);
}
.metric-label {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6B7D96;
    margin-bottom: 0.4rem;
}
.metric-value {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    color: #1A2333;
}

/* Status badges */
.badge {
    display: inline-block;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    border-radius: 20px;
    padding: 3px 10px;
    border: 1px solid;
}
.badge-green {
    background: rgba(19,123,77,0.08);
    color: #137B4D;
    border-color: rgba(19,123,77,0.25);
}
.badge-red {
    background: rgba(192,57,43,0.08);
    color: #C0392B;
    border-color: rgba(192,57,43,0.25);
}

/* Story chip */
.story-chip {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    font-size: 0.82rem;
    color: #005BAB;
    background: rgba(0,91,171,0.08);
    border: 1px solid rgba(0,91,171,0.20);
    padding: 2px 8px;
    border-radius: 4px;
}

/* SHA chip */
.sha-chip {
    display: inline-block;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 400;
    font-size: 0.78rem;
    color: #6B7D96;
    background: rgba(0,91,171,0.04);
    border: 1px solid #D8E2F0;
    padding: 2px 8px;
    border-radius: 4px;
}

/* Register table */
.reg-table {
    width: 100%;
    border-collapse: collapse;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 0.875rem;
}
.reg-table th {
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #6B7D96;
    text-align: left;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #D8E2F0;
}
.reg-table td {
    padding: 0.75rem 1rem;
    border-bottom: 1px solid #D8E2F0;
    color: #1A2333;
    vertical-align: middle;
}
.reg-table tr:hover td { background: #EFF3FB; }

/* Output block */
.output-block {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    line-height: 1.6;
    color: #1A2333;
    background: #F0F4FA;
    border: 1px solid #D8E2F0;
    border-radius: 6px;
    padding: 0.875rem 1rem;
    max-height: 300px;
    overflow-y: auto;
    white-space: pre-wrap;
}

/* Section header */
.section-header {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 700;
    font-size: 1.1rem;
    color: #1A2333;
    border-bottom: 2px solid #005BAB;
    padding-bottom: 0.5rem;
    margin-bottom: 1rem;
    margin-top: 1.5rem;
}

/* Streamlit overrides */
section[data-testid="stSidebar"] {
    background-color: #FFFFFF !important;
    border-right: 1px solid #D8E2F0 !important;
}
div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label { color: #6B7D96 !important; }
.stButton > button {
    background: rgba(0,91,171,0.08);
    color: #005BAB;
    border: 1px solid rgba(0,91,171,0.25);
    border-radius: 8px;
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-weight: 600;
}
</style>
"""

st.markdown(_CSS, unsafe_allow_html=True)

# ─── Data loading ────────────────────────────────────────────────────────────

REGISTER_PATH = Path(__file__).parent.parent.parent / "traceability" / "register.json"


@st.cache_data(ttl=30)
def load_register() -> list[dict]:
    """
    Return parsed records from register.json, or [] on missing file or parse
    error (errors are silently swallowed). Cached for 30 s via st.cache_data.
    """
    if not REGISTER_PATH.exists():
        return []
    try:
        return json.loads(REGISTER_PATH.read_text())
    except (json.JSONDecodeError, OSError):
        return []


# ─── Page header ────────────────────────────────────────────────────────────

st.markdown('<div class="ac-title">Assurance CI</div>', unsafe_allow_html=True)
st.markdown('<div class="ac-subtitle">Story → Commit → Generated Tests → Execution → Gate · Traceability Register</div>', unsafe_allow_html=True)

records = load_register()

# ─── KPI cards ──────────────────────────────────────────────────────────────

total = len(records)
green = sum(1 for r in records if r.get("gate_result", {}).get("status") == "green")
red = total - green
stories = len({r.get("story_id") for r in records})

st.markdown(
    f"""
    <div class="metric-row">
      <div class="metric-card">
        <div class="metric-label">Total Runs</div>
        <div class="metric-value">{total}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Green Gates</div>
        <div class="metric-value" style="color:#137B4D">{green}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Red Gates</div>
        <div class="metric-value" style="color:#C0392B">{red}</div>
      </div>
      <div class="metric-card">
        <div class="metric-label">Stories Covered</div>
        <div class="metric-value">{stories}</div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ─── Register table ─────────────────────────────────────────────────────────

st.markdown('<div class="section-header">Traceability Register</div>', unsafe_allow_html=True)

if not records:
    st.markdown("_No traceability records yet. Run the assurance pipeline to populate the register._")
else:
    # Filter controls
    col_filter, col_status, _ = st.columns([2, 2, 4])
    with col_filter:
        story_options = ["All stories"] + sorted({r.get("story_id", "") for r in records})
        selected_story = st.selectbox("Story", story_options, label_visibility="collapsed")
    with col_status:
        status_options = ["All statuses", "green", "red"]
        selected_status = st.selectbox("Status", status_options, label_visibility="collapsed")

    filtered = [
        r for r in records
        if (selected_story == "All stories" or r.get("story_id") == selected_story)
        and (selected_status == "All statuses" or r.get("gate_result", {}).get("status") == selected_status)
    ]

    rows_html = ""
    for r in reversed(filtered):  # most recent first
        gate = r.get("gate_result", {})
        status = gate.get("status", "red")
        badge_cls = "badge-green" if status == "green" else "badge-red"
        sha = html.escape(r.get("commit_sha", "")[:7])
        date = html.escape(r.get("appended_at", "")[:10])
        story_id = html.escape(r.get("story_id", ""))
        author = html.escape(r.get("author", ""))
        report = r.get("execution_report", {})
        passed = report.get("passed", 0)
        failed = report.get("failed", 0)
        rows_html += f"""
        <tr>
          <td><span class="story-chip">{story_id}</span></td>
          <td><span class="sha-chip">{sha}</span></td>
          <td>{author}</td>
          <td><span class="badge {badge_cls}">{status.upper()}</span></td>
          <td style="font-variant-numeric:tabular-nums;color:#6B7D96">{passed}P / {failed}F</td>
          <td style="color:#6B7D96;font-family:'IBM Plex Mono',monospace;font-size:0.78rem">{date}</td>
        </tr>
        """

    st.markdown(
        f"""
        <table class="reg-table">
          <thead>
            <tr>
              <th>Story</th><th>Commit</th><th>Author</th>
              <th>Gate</th><th>Scenarios</th><th>Date</th>
            </tr>
          </thead>
          <tbody>{rows_html}</tbody>
        </table>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(f"<div style='color:#6B7D96;font-size:0.75rem;margin-top:0.75rem'>{len(filtered)} record(s) shown</div>", unsafe_allow_html=True)

# ─── Detail panel ────────────────────────────────────────────────────────────

if records:
    st.markdown('<div class="section-header">Execution Detail</div>', unsafe_allow_html=True)

    run_labels = [
        f"{r.get('story_id','')} · {r.get('commit_sha','')[:7]} · {r.get('appended_at','')[:10]}"
        for r in reversed(records)
    ]
    selected_label = st.selectbox("Select run", run_labels, label_visibility="visible")
    idx = run_labels.index(selected_label)
    detail = list(reversed(records))[idx]

    col_a, col_b = st.columns(2)
    with col_a:
        gate = detail.get("gate_result", {})
        status = gate.get("status", "red")
        badge_cls = "badge-green" if status == "green" else "badge-red"
        report = detail.get("execution_report", {})
        d_story_id = html.escape(detail.get("story_id", ""))
        d_sha = html.escape(detail.get("commit_sha", "")[:7])
        d_author = html.escape(detail.get("author", ""))
        d_reason = html.escape(gate.get("reason", ""))
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #D8E2F0;border-radius:8px;padding:1.25rem 1.5rem;box-shadow:0 1px 3px rgba(0,91,171,0.06),0 4px 16px rgba(0,91,171,0.08)">
              <div class="metric-label">Story</div>
              <div style="margin-bottom:1rem"><span class="story-chip">{d_story_id}</span></div>
              <div class="metric-label">Commit</div>
              <div style="margin-bottom:1rem"><span class="sha-chip">{d_sha}</span></div>
              <div class="metric-label">Author</div>
              <div style="margin-bottom:1rem;font-size:0.875rem">{d_author}</div>
              <div class="metric-label">Gate</div>
              <div style="margin-bottom:1rem"><span class="badge {badge_cls}">{status.upper()}</span></div>
              <div class="metric-label">Reason</div>
              <div style="font-size:0.875rem;color:#6B7D96">{d_reason}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_b:
        feature_path = html.escape(detail.get("feature_file_path", ""))
        test_path = html.escape(detail.get("test_script_path", ""))
        environment = html.escape(report.get("environment", "—"))
        timestamp = html.escape(report.get("timestamp", "")[:19].replace("T", " "))
        st.markdown(
            f"""
            <div style="background:#FFFFFF;border:1px solid #D8E2F0;border-radius:8px;padding:1.25rem 1.5rem;box-shadow:0 1px 3px rgba(0,91,171,0.06),0 4px 16px rgba(0,91,171,0.08)">
              <div class="metric-label">Feature File</div>
              <div style="margin-bottom:1rem;font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:#6B7D96">{feature_path or "—"}</div>
              <div class="metric-label">Test Script</div>
              <div style="margin-bottom:1rem;font-family:'IBM Plex Mono',monospace;font-size:0.78rem;color:#6B7D96">{test_path or "—"}</div>
              <div class="metric-label">Environment</div>
              <div style="margin-bottom:1rem;font-size:0.875rem;color:#6B7D96">{environment}</div>
              <div class="metric-label">Timestamp</div>
              <div style="font-size:0.875rem;color:#6B7D96">{timestamp}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    output = detail.get("execution_report", {}).get("output", "")
    if output:
        st.markdown('<div class="metric-label" style="margin-top:1.5rem;margin-bottom:0.5rem;color:#6B7D96">TEST OUTPUT</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="output-block">{html.escape(output)}</div>', unsafe_allow_html=True)

# ─── Refresh ──────────────────────────────────────────────────────────────

with st.sidebar:
    st.markdown('<div style="font-family:\'Plus Jakarta Sans\',sans-serif;font-weight:800;font-size:1.1rem;color:#005BAB;margin-bottom:1rem">Assurance CI</div>', unsafe_allow_html=True)
    st.markdown('<div style="font-size:0.78rem;color:#6B7D96;margin-bottom:1.5rem">Traceability Register Viewer</div>', unsafe_allow_html=True)
    if st.button("↺ Refresh"):
        st.cache_data.clear()
        st.rerun()
    st.markdown(
        f'<div style="margin-top:2rem;font-size:0.75rem;color:#6B7D96">'
        f'Register: <span style="font-family:\'IBM Plex Mono\',monospace">{REGISTER_PATH}</span></div>',
        unsafe_allow_html=True,
    )
