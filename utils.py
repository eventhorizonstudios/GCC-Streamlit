"""
utils.py — shared constants, data generation, helpers, and chart factories.
Structure: 4 BUs × 3 Regions × 6 Activities = 72 queues total.
"""
import time
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════════
# STRUCTURE
# ═══════════════════════════════════════════════════════════════════════════════
BUS        = ["BU1", "BU2", "BU3", "BU4"]
REGIONS    = ["West", "Central", "East"]
QUEUES = ["Queue 1", "Queue 2", "Queue 3",
              "Queue 4", "Queue 5", "Queue 6"]

def _qk(bu: str, region: str, queue: str) -> str:
    """Canonical queue key — spaces stripped: 'BU1_Region1_Queue3'"""
    return f"{bu}_{region.replace(' ', '')}_{queue.replace(' ', '')}"

QUEUE_KEYS = [_qk(bu, r, a) for bu in BUS for r in REGIONS for a in QUEUES]  # 72

QK_META = {
    _qk(bu, r, a): {"bu": bu, "region": r, "queue": a}
    for bu in BUS for r in REGIONS for a in QUEUES
}

QUEUE_SHORT = {f"Queue {i}": f"A{i}" for i in range(1, 7)}

# ═══════════════════════════════════════════════════════════════════════════════
# COLOURS & DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════
QUEUE_COLORS = {
    "Queue 1": "#38bdf8",  # sky blue
    "Queue 2": "#a78bfa",  # violet
    "Queue 3": "#34d399",  # emerald
    "Queue 4": "#fb923c",  # orange
    "Queue 5": "#f472b6",  # pink
    "Queue 6": "#facc15",  # yellow
}

BU_COLORS = {
    "BU1": "#38bdf8",
    "BU2": "#f472b6",
    "BU3": "#fb923c",
    "BU4": "#a78bfa",
}

REGION_COLORS = {
    "West": "#60a5fa",
    "Central": "#c084fc",
    "East": "#4ade80",
}

# ═══════════════════════════════════════════════════════════════════════════════
# QUEUE PROFILES  (programmatically generated — all baselines inside OK)
# ═══════════════════════════════════════════════════════════════════════════════
#   Thresholds reminder:
#     queue_volume  : warn ≥ 50,  crit ≥ 80
#     aht_seconds   : warn ≥ 300, crit ≥ 420
#     occupancy_pct : warn ≥ 85,  crit ≥ 95
#     adherence_pct : warn < 88,  crit < 80  (inverted)
#     service_level : warn < 80,  crit < 70  (inverted)
def _build_profiles() -> dict:
    bu_off  = {"BU1":  0, "BU2":  6, "BU3": -4, "BU4": 12}
    reg_off = {"West": 0, "Central": 3, "East": -2}
    act_off = {"Queue 1": 0, "Queue 2": 2, "Queue 3": 1,
               "Queue 4": 3, "Queue 5": 1, "Queue 6": 2}
    profiles = {}
    for bu in BUS:
        for r in REGIONS:
            for a in QUEUES:
                off = bu_off[bu] + reg_off[r] + act_off[a]
                profiles[_qk(bu, r, a)] = {
                    "queue":  max(5,  18 + off),
                    "aht":    max(160, 205 + off * 2),
                    "occ":    int(min(80, max(50, 60 + off * 0.7))),
                    "adh":    int(min(97, max(89, 95 - off * 0.25))),
                    "sl":     int(min(97, max(83, 92 - off * 0.3))),
                    "agents": max(3, 6 + off // 4),
                }
    return profiles

QUEUE_PROFILES = _build_profiles()

# ═══════════════════════════════════════════════════════════════════════════════
# THRESHOLDS & CHART CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
THRESHOLDS = {
    "queue_volume":      {"warn": 50,  "crit": 80,  "invert": False},
    "aht_seconds":       {"warn": 300, "crit": 420, "invert": False},
    "occupancy_pct":     {"warn": 85,  "crit": 95,  "invert": False},
    "adherence_pct":     {"warn": 88,  "crit": 80,  "invert": True},
    "service_level_pct": {"warn": 80,  "crit": 70,  "invert": True},
}

# (key, display name, unit, warn, crit, invert)
CHART_METRIC_CFG = [
    ("queue_volume",      "Queue Volume",  "cases", 50,  80,  False),
    ("aht_seconds",       "AHT",           "s",     300, 420, False),
    ("service_level_pct", "Service Level", "%",     80,  70,  True),
    ("occupancy_pct",     "Occupancy",     "%",     85,  95,  False),
    ("adherence_pct",     "Adherence",     "%",     88,  80,  True),
]

ALL_METRICS = list(THRESHOLDS.keys())
CHART_BG    = "#111827"
GRID_COLOR  = "#1e293b"
HIST_LEN    = 120
POLL_SECS   = 60

# ═══════════════════════════════════════════════════════════════════════════════
# GLOBAL CSS
# ═══════════════════════════════════════════════════════════════════════════════
GLOBAL_CSS = """
<style>
  html, body,
  [data-testid="stAppViewContainer"],
  [data-testid="stMain"] {
    background-color: #0b0f1a !important;
    color: #e2e8f0;
  }
  [data-testid="stHeader"]         { background: #0b0f1a !important; }



  /* Tabs styling */
  [data-testid="stTabs"] [data-testid="stMarkdownContainer"] p { margin:0; }
  button[data-baseweb="tab"] {
    background: #111827 !important;
    color: #64748b !important;
    border-bottom: 2px solid #1e293b !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    padding: 8px 18px !important;
  }
  button[data-baseweb="tab"][aria-selected="true"] {
    color: #38bdf8 !important;
    border-bottom: 2px solid #38bdf8 !important;
    background: #0f172a !important;
  }
  [data-testid="stTabPanel"] {
    background: #0b0f1a !important;
    padding-top: 16px !important;
  }

  [data-testid="stExpander"] {
    background:#111827 !important; border:1px solid #1e293b !important;
    border-radius:8px !important;
  }
  hr { border-color:#1e293b !important; }
  .block-container { padding-top:1rem !important; }
  #MainMenu, footer, [data-testid="stDeployButton"] { visibility:hidden; }
  ::-webkit-scrollbar       { width:4px; }
  ::-webkit-scrollbar-track { background:#0b0f1a; }
  ::-webkit-scrollbar-thumb { background:#1e293b; border-radius:2px; }

</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_message(qkey: str, prev: dict) -> dict:
    p = QUEUE_PROFILES[qkey]

    def mean_revert(prev_val, baseline, lo, hi, sigma=0.025, pull=0.15):
        target = prev_val + pull * (baseline - prev_val)
        noise  = np.random.normal(0, max(abs(target) * sigma, 0.3))
        return float(np.clip(target + noise, lo, hi))

    q  = mean_revert(prev.get("queue_volume",      p["queue"]), p["queue"], 0,   120)
    a  = mean_revert(prev.get("aht_seconds",       p["aht"]),   p["aht"],   60,  500)
    o  = mean_revert(prev.get("occupancy_pct",     p["occ"]),   p["occ"],   30,  100)
    d  = mean_revert(prev.get("adherence_pct",     p["adh"]),   p["adh"],   65,  100)
    sl = mean_revert(prev.get("service_level_pct", p["sl"]),    p["sl"],    50,  100)

    # Spikes: 1.5% chance — sized to nudge toward WARN; only rare doubles reach CRIT
    if random.random() < 0.015: q  = min(q  * random.uniform(1.4, 1.8), 120)
    if random.random() < 0.015: a  = min(a  * random.uniform(1.15, 1.4), 500)
    if random.random() < 0.015: sl = max(sl * random.uniform(0.82, 0.93), 50)

    # Agents change infrequently — 8% chance per tick of a +1/-1 shift,
    # otherwise carry the previous value forward for stability.
    prev_agents = prev.get("agents_logged", p["agents"])
    if random.random() < 0.08:
        agents = max(1, prev_agents + random.choice([-1, 1]))
    else:
        agents = prev_agents
    offered = random.randint(int(q * 1.4), int(q * 3.0 + 15))
    handled = min(offered, int(offered * random.uniform(0.88, 0.99)))

    return {
        "ts":                datetime.now(),
        "queue_volume":      round(q,  1),
        "aht_seconds":       round(a,  1),
        "occupancy_pct":     round(o,  1),
        "adherence_pct":     round(d,  1),
        "service_level_pct": round(sl, 1),
        "agents_logged":     agents,
        "cases_offered":     offered,
        "cases_handled":     handled,
    }

def warm_history(qkey: str, n: int = 120) -> pd.DataFrame:
    rows, prev = [], {}
    base_ts = datetime.now() - timedelta(seconds=POLL_SECS * n)
    for i in range(n):
        msg = generate_message(qkey, prev)
        msg["ts"] = base_ts + timedelta(seconds=POLL_SECS * i)
        rows.append(msg)
        prev = msg
    return pd.DataFrame(rows)

# ═══════════════════════════════════════════════════════════════════════════════
# SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
def init_and_tick():
    if "history" not in st.session_state:
        st.session_state.history        = {qk: warm_history(qk) for qk in QUEUE_KEYS}
        st.session_state.prev_msg       = {
            qk: st.session_state.history[qk].iloc[-1].to_dict() for qk in QUEUE_KEYS
        }
        st.session_state.tick           = 0
        st.session_state.last_data_tick = time.time() - POLL_SECS

    now = time.time()
    if now - st.session_state.last_data_tick >= POLL_SECS:
        for qk in QUEUE_KEYS:
            msg = generate_message(qk, st.session_state.prev_msg[qk])
            st.session_state.history[qk] = (
                pd.concat([st.session_state.history[qk], pd.DataFrame([msg])],
                          ignore_index=True).tail(HIST_LEN)
            )
            st.session_state.prev_msg[qk] = msg
        st.session_state.tick          += 1
        st.session_state.last_data_tick = now

# ═══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════════
def severity_score(metric: str, val: float) -> float:
    t = THRESHOLDS[metric]
    if t["invert"]:
        if val < t["crit"]: return 1.0
        if val < t["warn"]: return 0.5
        return 0.0
    else:
        if val >= t["crit"]: return 1.0
        if val >= t["warn"]: return 0.5
        return 0.0

def sev_color(score: float) -> str:
    if score >= 1.0: return "#ef4444"
    if score >= 0.5: return "#f59e0b"
    return "#22c55e"

def sev_label(score: float) -> str:
    if score >= 1.0: return "CRIT"
    if score >= 0.5: return "WARN"
    return "OK"

def latest_values() -> pd.DataFrame:
    rows = []
    for qk in QUEUE_KEYS:
        lat  = st.session_state.history[qk].iloc[-1]
        meta = QK_META[qk]
        rows.append({
            "queue_key":         qk,
            "bu":                meta["bu"],
            "region":            meta["region"],
            "queue":          meta["queue"],
            "queue_volume":      lat["queue_volume"],
            "aht_seconds":       lat["aht_seconds"],
            "occupancy_pct":     lat["occupancy_pct"],
            "adherence_pct":     lat["adherence_pct"],
            "service_level_pct": lat["service_level_pct"],
            "agents_logged":     lat["agents_logged"],
            "cases_offered":     lat["cases_offered"],
            "cases_handled":     lat["cases_handled"],
        })
    return pd.DataFrame(rows)

# ═══════════════════════════════════════════════════════════════════════════════
# SHARED HEADER
# ═══════════════════════════════════════════════════════════════════════════════
def render_header(page_title: str, subtitle: str = ""):
    latest_ts = max(st.session_state.prev_msg[qk]["ts"] for qk in QUEUE_KEYS)
    c1, c2, c3 = st.columns([0.5, 7, 2])
    with c1:
        st.markdown("<div style='font-size:2rem;margin-top:4px;'>📡</div>",
                    unsafe_allow_html=True)
    with c2:
        st.markdown(
            f"<h1 style='margin:0;font-size:1.4rem;font-weight:900;letter-spacing:0.05em;"
            f"color:#f1f5f9;line-height:1.2;'>GCC"
            f"<span style='color:#38bdf8;'> · {page_title}</span></h1>"
            f"<p style='margin:2px 0 0;font-size:0.67rem;color:#475569;letter-spacing:0.1em;'>"
            f"KAFKA TOPIC: <code style='color:#38bdf8;background:#0f172a;padding:1px 5px;"
            f"border-radius:3px;'>gcc.realtime.metrics</code>"
            f"{'  ·  ' + subtitle if subtitle else ''}</p>",
            unsafe_allow_html=True,
        )
    with c3:
        st.markdown(
            f"<div style='text-align:right;padding-top:4px;'>"
            f"<span style='font-size:0.63rem;color:#475569;letter-spacing:0.1em;'>LAST POLL</span><br>"
            f"<span style='font-size:1.1rem;font-weight:800;color:#38bdf8;'>"
            f"{latest_ts.strftime('%H:%M:%S')}</span>"
            f"<span style='font-size:0.62rem;color:#334155;margin-left:6px;'>"
            f"TICK #{st.session_state.tick}</span></div>",
            unsafe_allow_html=True,
        )
    st.markdown("<hr style='margin:8px 0 16px;'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# CHART FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════

def _hex_rgba(color: str, alpha: float) -> str:
    """Convert a '#rrggbb' hex color to an rgba() CSS string."""
    return f"rgba({int(color[1:3],16)},{int(color[3:5],16)},{int(color[5:7],16)},{alpha})"

def _base_layout(height: int) -> dict:
    return dict(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=8, r=8, t=8, b=8), height=height,
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(color="#475569", size=9), tickformat="%H:%M"),
        yaxis=dict(showgrid=True, gridcolor=GRID_COLOR, zeroline=False,
                   tickfont=dict(color="#475569", size=9)),
        hovermode="x unified",
    )

def _add_bands(fig, warn, crit, y_min, y_max, invert):
    if not invert:
        fig.add_hrect(y0=warn, y1=min(crit, y_max),
                      fillcolor="#f59e0b", opacity=0.07, line_width=0)
        fig.add_hrect(y0=crit, y1=y_max,
                      fillcolor="#ef4444", opacity=0.09, line_width=0)
    else:
        fig.add_hrect(y0=max(y_min, crit), y1=warn,
                      fillcolor="#f59e0b", opacity=0.07, line_width=0)
        fig.add_hrect(y0=y_min, y1=crit,
                      fillcolor="#ef4444", opacity=0.09, line_width=0)
    fig.add_hline(y=warn, line=dict(color="#f59e0b", dash="dash", width=1), opacity=0.5)
    fig.add_hline(y=crit, line=dict(color="#ef4444", dash="dash", width=1), opacity=0.5)

def make_sl_sparkline(qk: str, color: str, height: int = 90) -> go.Figure:
    """Compact service-level sparkline — no axes, just the coloured line
    and warn/crit bands. Designed to be read at a glance on a TV screen."""
    df_q = st.session_state.history[qk]
    warn, crit = 80, 70
    vals = df_q["service_level_pct"]
    y_min = max(min(vals) * 0.92, 0)
    y_max = min(max(vals) * 1.05, 100)

    fig = go.Figure()

    # Threshold bands
    fig.add_hrect(y0=crit, y1=warn, fillcolor="#f59e0b", opacity=0.10, line_width=0)
    fig.add_hrect(y0=y_min, y1=crit, fillcolor="#ef4444", opacity=0.12, line_width=0)
    fig.add_hline(y=warn, line=dict(color="#f59e0b", dash="dot", width=1), opacity=0.5)
    fig.add_hline(y=crit, line=dict(color="#ef4444", dash="dot", width=1), opacity=0.5)

    # Line
    fig.add_trace(go.Scatter(
        x=df_q["ts"], y=vals,
        line=dict(color=color, width=2), mode="lines",
        fill="tozeroy",
        fillcolor=_hex_rgba(color, 0.06),
        hovertemplate="%{y:.0f}%<br>%{x|%H:%M:%S}<extra></extra>",
        showlegend=False,
    ))
    # Latest dot
    fig.add_trace(go.Scatter(
        x=[df_q["ts"].iloc[-1]], y=[vals.iloc[-1]],
        mode="markers",
        marker=dict(color=color, size=6, line=dict(color="#0b0f1a", width=2)),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        xaxis=dict(visible=False),
        yaxis=dict(visible=False, range=[y_min, y_max]),
        hovermode="x unified",
    )
    return fig

def make_single_queue_chart(qk: str, metric_key: str, label: str,
                                unit: str, warn: float, crit: float,
                                invert: bool, color: str,
                                height: int = 160) -> go.Figure:
    """Full metric chart for a single queue queue — used in expanded view."""
    df_q = st.session_state.history[qk]
    vals = df_q[metric_key]
    y_max = max(vals.max() * 1.15, crit * 1.1)
    y_min = max(vals.min() * 0.88, 0)

    fig = go.Figure()
    _add_bands(fig, warn, crit, y_min, y_max, invert)

    fig.add_trace(go.Scatter(
        x=df_q["ts"], y=vals,
        line=dict(color=color, width=2), mode="lines",
        fill="tozeroy",
        fillcolor=_hex_rgba(color, 0.07),
        hovertemplate=f"%{{y:.0f}} {unit}<br>%{{x|%H:%M:%S}}<extra></extra>",
        showlegend=False,
    ))
    fig.add_trace(go.Scatter(
        x=[df_q["ts"].iloc[-1]], y=[vals.iloc[-1]],
        mode="markers",
        marker=dict(color=color, size=6, line=dict(color="#0b0f1a", width=2)),
        showlegend=False, hoverinfo="skip",
    ))

    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        margin=dict(l=4, r=4, t=20, b=4), height=height,
        title=dict(text=f"<b>{label}</b>", font=dict(color="#64748b", size=10), x=0.01, y=0.98),
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(color="#334155", size=8), tickformat="%H:%M"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", zeroline=False,
                   tickfont=dict(color="#334155", size=8),
                   ticksuffix=f" {unit}"),
        hovermode="x unified",
    )
    return fig

def make_plain_chart(qk: str, metric_key: str, label: str, unit: str,
                     color: str, height: int = 160) -> go.Figure:
    """Step chart for discrete metrics like agents_logged — honest representation
    of values that change in steps rather than smoothly."""
    df_q = st.session_state.history[qk]
    vals = df_q[metric_key]
    y_max = max(vals.max() * 1.25, 1)
    y_min = max(vals.min() * 0.75, 0)
    rgba  = _hex_rgba(color, 0.15)

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_q["ts"], y=vals,
        line=dict(color=color, width=2, shape="hv"),
        mode="lines",
        fill="tozeroy",
        fillcolor=rgba,
        hovertemplate=f"%{{y:.0f}} {unit}<br>%{{x|%H:%M:%S}}<extra></extra>",
        showlegend=False,
    ))
    # Latest value dot
    fig.add_trace(go.Scatter(
        x=[df_q["ts"].iloc[-1]], y=[vals.iloc[-1]],
        mode="markers+text",
        marker=dict(color=color, size=8, line=dict(color="#0b0f1a", width=2)),
        text=[f"{int(vals.iloc[-1])}"],
        textposition="top center",
        textfont=dict(color=color, size=10, family="monospace"),
        showlegend=False, hoverinfo="skip",
    ))
    fig.update_layout(
        paper_bgcolor="#0d1117", plot_bgcolor="#0d1117",
        margin=dict(l=4, r=4, t=20, b=4), height=height,
        title=dict(text=f"<b>{label}</b>", font=dict(color="#64748b", size=10), x=0.01, y=0.98),
        xaxis=dict(showgrid=False, zeroline=False,
                   tickfont=dict(color="#334155", size=8), tickformat="%H:%M"),
        yaxis=dict(showgrid=True, gridcolor="#1e293b", zeroline=False,
                   tickfont=dict(color="#334155", size=8),
                   tickformat="d", range=[y_min, y_max]),
        hovermode="x unified",
    )
    return fig