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
REGIONS    = ["Region 1", "Region 2", "Region 3"]
ACTIVITIES = ["Activity 1", "Activity 2", "Activity 3",
              "Activity 4", "Activity 5", "Activity 6"]


def _qk(bu: str, region: str, activity: str) -> str:
    """Canonical queue key — spaces stripped: 'BU1_Region1_Activity3'"""
    return f"{bu}_{region.replace(' ', '')}_{activity.replace(' ', '')}"


QUEUE_KEYS = [_qk(bu, r, a) for bu in BUS for r in REGIONS for a in ACTIVITIES]  # 72

QK_META = {
    _qk(bu, r, a): {"bu": bu, "region": r, "activity": a}
    for bu in BUS for r in REGIONS for a in ACTIVITIES
}

REGION_SHORT   = {"Region 1": "R1",  "Region 2": "R2",  "Region 3": "R3"}
ACTIVITY_SHORT = {f"Activity {i}": f"A{i}" for i in range(1, 7)}

# ═══════════════════════════════════════════════════════════════════════════════
# COLOURS & DISPLAY
# ═══════════════════════════════════════════════════════════════════════════════
ACTIVITY_COLORS = {
    "Activity 1": "#38bdf8",  # sky blue
    "Activity 2": "#a78bfa",  # violet
    "Activity 3": "#34d399",  # emerald
    "Activity 4": "#fb923c",  # orange
    "Activity 5": "#f472b6",  # pink
    "Activity 6": "#facc15",  # yellow
}

BU_COLORS = {
    "BU1": "#38bdf8",
    "BU2": "#f472b6",
    "BU3": "#fb923c",
    "BU4": "#a78bfa",
}

REGION_COLORS = {
    "Region 1": "#60a5fa",
    "Region 2": "#c084fc",
    "Region 3": "#4ade80",
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
    reg_off = {"Region 1": 0, "Region 2": 3, "Region 3": -2}
    act_off = {"Activity 1": 0, "Activity 2": 2, "Activity 3": 1,
               "Activity 4": 3, "Activity 5": 1, "Activity 6": 2}
    profiles = {}
    for bu in BUS:
        for r in REGIONS:
            for a in ACTIVITIES:
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
HIST_LEN    = 480
POLL_SECS   = 10

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
  [data-testid="stSidebar"]        { background: #080c14 !important; border-right: 1px solid #1e293b; }
  [data-testid="stSidebarContent"] { background: #080c14 !important; }

  [data-testid="metric-container"] {
    background: #111827; border: 1px solid #1e293b;
    border-radius: 10px; padding: 14px 18px;
    box-shadow: 0 0 14px rgba(56,189,248,0.06);
  }
  [data-testid="stMetricLabel"] { font-size:0.72rem; color:#64748b; letter-spacing:0.08em; text-transform:uppercase; }
  [data-testid="stMetricValue"] { font-size:1.8rem;  font-weight:800; color:#f1f5f9; }
  [data-testid="stMetricDelta"] { font-size:0.78rem; }

  .section-label {
    font-size:0.68rem; font-weight:700; letter-spacing:0.14em;
    text-transform:uppercase; color:#38bdf8; margin:0 0 6px 0;
  }

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

  /* Hide Streamlit's auto-generated nav */
  [data-testid="stSidebarNav"] { display: none !important; }

  /* Manual page links */
  [data-testid="stPageLink"] p {
    font-size: 0.88rem !important; font-weight: 600 !important;
    color: #94a3b8 !important; padding: 2px 0 !important;
  }
  [data-testid="stPageLink"]:hover p,
  [data-testid="stPageLink"][aria-current] p { color: #38bdf8 !important; }
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

    agents  = max(1, p["agents"] + random.randint(-1, 2))
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


def warm_history(qkey: str, n: int = 30) -> pd.DataFrame:
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
            "activity":          meta["activity"],
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
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar_status():
    with st.sidebar:
        st.markdown(
            "<div style='padding:14px 0 10px;'>"
            "<span style='font-size:1.1rem;font-weight:900;color:#38bdf8;"
            "letter-spacing:0.1em;'>📡 GCC</span><br>"
            "<span style='font-size:0.65rem;color:#475569;letter-spacing:0.08em;'>"
            "GLOBAL CONTACT CENTRE</span>"
            "</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<hr style='margin:0 0 10px;'>", unsafe_allow_html=True)

        st.page_link("Home.py",        label="Overview", icon="🌐")
        st.page_link("pages/1_BU1.py", label="BU1",      icon="🏢")
        st.page_link("pages/2_BU2.py", label="BU2",      icon="🏢")
        st.page_link("pages/3_BU3.py", label="BU3",      icon="🏢")
        st.page_link("pages/4_BU4.py", label="BU4",      icon="🏢")

        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown(
            "<p style='font-size:0.62rem;color:#334155;line-height:1.7;'>"
            "⚡ Auto-refresh: 10 s<br>"
            "📊 Rolling window: 480 ticks<br>"
            "🟢 OK &nbsp;🟡 WARN &nbsp;🔴 CRIT<br><br>"
            "<em>Swap <code>generate_message()</code> with a "
            "confluent-kafka consumer to go live.</em></p>",
            unsafe_allow_html=True,
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CHART FACTORIES
# ═══════════════════════════════════════════════════════════════════════════════
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


def make_activity_chart(bu: str, region: str, metric_key: str, unit: str,
                         warn: float, crit: float, invert: bool = False,
                         height: int = 220) -> go.Figure:
    """One chart per metric — 6 coloured lines, one per activity."""
    fig = go.Figure()
    all_vals = []
    for act in ACTIVITIES:
        all_vals.extend(st.session_state.history[_qk(bu, region, act)][metric_key].tolist())
    y_max = max(max(all_vals) * 1.2, crit * 1.1) if all_vals else crit * 1.2
    y_min = max(min(all_vals) * 0.85, 0)         if all_vals else 0
    _add_bands(fig, warn, crit, y_min, y_max, invert)

    for act in ACTIVITIES:
        qk    = _qk(bu, region, act)
        df_q  = st.session_state.history[qk]
        color = ACTIVITY_COLORS[act]
        short = ACTIVITY_SHORT[act]
        fig.add_trace(go.Scatter(
            x=df_q["ts"], y=df_q[metric_key],
            line=dict(color=color, width=1.8), mode="lines",
            name=short,
            hovertemplate=f"<b>{act}: %{{y:.0f}} {unit}</b><br>%{{x|%H:%M:%S}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[df_q["ts"].iloc[-1]], y=[df_q[metric_key].iloc[-1]],
            mode="markers",
            marker=dict(color=color, size=6, line=dict(color="#0b0f1a", width=2)),
            showlegend=False, hoverinfo="skip",
        ))

    layout = _base_layout(height)
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(color="#94a3b8", size=9), bgcolor="rgba(0,0,0,0)",
        traceorder="normal",
    )
    layout["yaxis"]["ticksuffix"] = f" {unit}"
    fig.update_layout(**layout)
    return fig


def make_heatmap(lv: pd.DataFrame) -> go.Figure:
    """12-row heatmap aggregated by (BU × Region) — worst score across activities."""
    metric_keys   = ["queue_volume", "aht_seconds", "occupancy_pct", "adherence_pct", "service_level_pct"]
    metric_labels = ["Queue Vol", "AHT (s)", "Occupancy %", "Adherence %", "Svc Level %"]
    units         = ["", "s", "%", "%", "%"]

    row_labels, z_vals, z_text = [], [], []

    for bu in BUS:
        for region in REGIONS:
            subset = lv[(lv["bu"] == bu) & (lv["region"] == region)]
            row_labels.append(f"{bu}  ·  {region}")
            row_z, row_t = [], []
            for mk, u in zip(metric_keys, units):
                # Worst value direction: max for normal metrics, min for inverted
                invert = THRESHOLDS[mk]["invert"]
                worst_val   = subset[mk].min() if invert else subset[mk].max()
                worst_score = severity_score(mk, worst_val)
                row_z.append(worst_score)
                row_t.append(f"{worst_val:.0f}{u}")
            z_vals.append(row_z)
            z_text.append(row_t)

    colorscale = [
        [0.0, "#14532d"], [0.45, "#14532d"],
        [0.5, "#78350f"], [0.74, "#78350f"],
        [0.75, "#7f1d1d"], [1.0, "#7f1d1d"],
    ]
    fig = go.Figure(data=go.Heatmap(
        z=z_vals, x=metric_labels, y=row_labels,
        text=z_text, texttemplate="<b>%{text}</b>",
        textfont=dict(size=11, color="white"),
        colorscale=colorscale, zmin=0, zmax=1,
        showscale=False, xgap=3, ygap=3,
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=10, r=10, t=10, b=10), height=480,
        xaxis=dict(side="top", tickfont=dict(color="#94a3b8", size=12), tickangle=0),
        yaxis=dict(tickfont=dict(color="#94a3b8", size=11), autorange="reversed"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# BU PAGE RENDERER
# ═══════════════════════════════════════════════════════════════════════════════
def render_bu_page(bu: str):
    render_header(bu, "3 REGIONS  ·  6 ACTIVITIES PER REGION")
    lv = latest_values()

    # ── Region tabs ────────────────────────────────────────────────────────────
    tabs = st.tabs([f"📍 {r}" for r in REGIONS])

    for tab, region in zip(tabs, REGIONS):
        with tab:
            _render_region(bu, region, lv)


def _render_region(bu: str, region: str, lv: pd.DataFrame):
    """Content for a single region tab on a BU page."""
    region_lv = lv[(lv["bu"] == bu) & (lv["region"] == region)].reset_index(drop=True)

    # ── Activity Snapshot Cards (2 rows × 3 cols) ───────────────────────────
    st.markdown('<p class="section-label">📊 Activity Snapshot</p>',
                unsafe_allow_html=True)

    row1 = st.columns(3)
    row2 = st.columns(3)
    card_cols = list(row1) + list(row2)

    for col, act in zip(card_cols, ACTIVITIES):
        row   = region_lv[region_lv["activity"] == act].iloc[0]
        qk    = _qk(bu, region, act)
        color = ACTIVITY_COLORS[act]
        short = ACTIVITY_SHORT[act]
        prev_df  = st.session_state.history[qk]
        prev_row = prev_df.iloc[-2] if len(prev_df) > 1 else prev_df.iloc[-1]

        # Overall worst score for this activity
        act_scores = [severity_score(mk, row[mk]) for mk in ALL_METRICS]
        act_score  = max(act_scores)
        badge_clr  = sev_color(act_score)
        badge_lbl  = sev_label(act_score)

        def _mini_kpi(label, val, mk):
            sc  = severity_score(mk, val)
            clr = sev_color(sc)
            return (
                f"<div style='text-align:center;'>"
                f"<div style='font-size:0.55rem;color:#475569;text-transform:uppercase;"
                f"letter-spacing:0.06em;margin-bottom:2px;'>{label}</div>"
                f"<div style='font-size:1.0rem;font-weight:800;color:{clr};'>{val:.0f}</div>"
                f"</div>"
            )

        kpis = (
            _mini_kpi("Queue",    row["queue_volume"],      "queue_volume")      +
            _mini_kpi("AHT",      row["aht_seconds"],       "aht_seconds")       +
            _mini_kpi("SL %",     row["service_level_pct"], "service_level_pct") +
            _mini_kpi("Occ %",    row["occupancy_pct"],     "occupancy_pct")     +
            _mini_kpi("Adh %",    row["adherence_pct"],     "adherence_pct")
        )

        handle_rate = (row["cases_handled"] / row["cases_offered"] * 100
                       if row["cases_offered"] > 0 else 0)

        with col:
            st.markdown(
                f"<div style='background:#111827;border:1px solid #1e293b;"
                f"border-top:3px solid {color};border-radius:10px;"
                f"padding:12px 14px;margin-bottom:8px;'>"
                # Header row
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:10px;'>"
                f"<span style='font-size:0.9rem;font-weight:800;color:{color};'>"
                f"{short}</span>"
                f"<span style='font-size:0.7rem;font-weight:700;color:{color};"
                f"opacity:0.7;'>{act}</span>"
                f"<span style='font-size:0.58rem;font-weight:800;color:{badge_clr};"
                f"background:rgba(0,0,0,0.4);padding:2px 6px;"
                f"border-radius:3px;'>{badge_lbl}</span>"
                f"</div>"
                # KPI row
                f"<div style='display:grid;grid-template-columns:repeat(5,1fr);"
                f"gap:4px;margin-bottom:10px;background:#0d1117;"
                f"border-radius:6px;padding:8px 4px;'>"
                f"{kpis}"
                f"</div>"
                # Footer
                f"<div style='font-size:0.62rem;color:#334155;"
                f"display:flex;justify-content:space-between;"
                f"border-top:1px solid #1e293b;padding-top:7px;'>"
                f"<span>👥 {int(row['agents_logged'])}</span>"
                f"<span>📥 {int(row['cases_offered'])}</span>"
                f"<span>✅ {handle_rate:.0f}%</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alert Status ────────────────────────────────────────────────────────
    with st.expander("🚨 Alert Status", expanded=False):
        for act in ACTIVITIES:
            row   = region_lv[region_lv["activity"] == act].iloc[0]
            color = ACTIVITY_COLORS[act]
            short = ACTIVITY_SHORT[act]
            parts = []
            for mk, name, unit in [
                ("queue_volume",      "Queue", ""),
                ("aht_seconds",       "AHT",   "s"),
                ("service_level_pct", "SL",    "%"),
                ("occupancy_pct",     "Occ",   "%"),
                ("adherence_pct",     "Adh",   "%"),
            ]:
                sc  = severity_score(mk, row[mk])
                clr = sev_color(sc)
                parts.append(
                    f"<span style='color:{clr};font-weight:700;'>"
                    f"{sev_label(sc)} {name}: {row[mk]:.0f}{unit}</span>"
                )
            sep = "&nbsp;·&nbsp;"
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #1e293b;"
                f"border-left:3px solid {color};border-radius:6px;"
                f"padding:8px 14px;margin-bottom:5px;font-size:0.78rem;'>"
                f"<strong style='color:{color};margin-right:10px;'>{short}</strong>"
                f"{sep.join(parts)}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Metric Trend Charts ─────────────────────────────────────────────────
    legend_html = "  ".join(
        f"<span style='display:inline-flex;align-items:center;gap:5px;'>"
        f"<span style='width:18px;height:3px;background:{ACTIVITY_COLORS[a]};"
        f"display:inline-block;border-radius:2px;'></span>"
        f"<span style='font-size:0.7rem;color:#64748b;'>{ACTIVITY_SHORT[a]}</span></span>"
        for a in ACTIVITIES
    )
    st.markdown(
        f'<p class="section-label">📈 Metric Trends</p>'
        f"<div style='margin-bottom:10px;'>{legend_html}</div>",
        unsafe_allow_html=True,
    )

    # Row 1: Queue | AHT | Service Level
    r1c1, r1c2, r1c3 = st.columns(3)
    # Row 2: Occupancy | Adherence
    r2c1, r2c2 = st.columns(2)

    chart_grid = [
        (r1c1, CHART_METRIC_CFG[0]),
        (r1c2, CHART_METRIC_CFG[1]),
        (r1c3, CHART_METRIC_CFG[2]),
        (r2c1, CHART_METRIC_CFG[3]),
        (r2c2, CHART_METRIC_CFG[4]),
    ]

    for c, (mkey, mname, unit, warn, crit, invert) in chart_grid:
        with c:
            st.markdown(f'<p class="section-label">{mname} ({unit})</p>',
                        unsafe_allow_html=True)
            fig = make_activity_chart(bu, region, mkey, unit, warn, crit, invert)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})