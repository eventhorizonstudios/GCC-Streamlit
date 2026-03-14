"""
utils.py — shared constants, data generation, helpers, and chart factories.
Imported by every page so logic lives in one place.
"""
import time
import random
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════
BUS        = ["BU1", "BU2", "BU3", "BU4"]
CHANNELS   = ["Calls", "Texts", "Emails"]
QUEUE_KEYS = [f"{bu}_{ch}" for bu in BUS for ch in CHANNELS]

CHANNEL_COLORS = {"Calls": "#38bdf8", "Texts": "#a78bfa", "Emails": "#34d399"}
CHANNEL_ICONS  = {"Calls": "📞",       "Texts": "💬",       "Emails": "📧"}
BU_COLORS      = {"BU1": "#38bdf8",   "BU2": "#f472b6",   "BU3": "#fb923c", "BU4": "#a78bfa"}

# Baselines are comfortably inside OK territory for every metric.
# Mean reversion in generate_message() keeps values anchored to these baselines.
# Spikes (1.5 % chance) push toward WARN; only rare compounding reaches CRIT.
#   queue_volume  : warn ≥ 50,  crit ≥ 80   → baselines 10–38
#   aht_seconds   : warn ≥ 300, crit ≥ 420  → baselines 190–265
#   occupancy_pct : warn ≥ 85,  crit ≥ 95   → baselines 55–78
#   adherence_pct : warn < 88,  crit < 80   → baselines 91–97
#   service_level : warn < 80,  crit < 70   → baselines 85–94
QUEUE_PROFILES = {
    "BU1_Calls":  {"queue": 25, "aht": 220, "occ": 68, "adh": 93, "sl": 89, "agents": 12},
    "BU1_Texts":  {"queue": 16, "aht": 155, "occ": 60, "adh": 94, "sl": 91, "agents":  7},
    "BU1_Emails": {"queue": 11, "aht": 240, "occ": 56, "adh": 95, "sl": 92, "agents":  5},
    "BU2_Calls":  {"queue": 35, "aht": 245, "occ": 72, "adh": 92, "sl": 86, "agents": 16},
    "BU2_Texts":  {"queue": 22, "aht": 175, "occ": 65, "adh": 93, "sl": 87, "agents":  9},
    "BU2_Emails": {"queue": 18, "aht": 255, "occ": 60, "adh": 94, "sl": 88, "agents":  7},
    "BU3_Calls":  {"queue": 18, "aht": 200, "occ": 60, "adh": 95, "sl": 92, "agents": 10},
    "BU3_Texts":  {"queue": 10, "aht": 135, "occ": 52, "adh": 96, "sl": 94, "agents":  5},
    "BU3_Emails": {"queue":  8, "aht": 210, "occ": 47, "adh": 97, "sl": 95, "agents":  4},
    "BU4_Calls":  {"queue": 38, "aht": 260, "occ": 76, "adh": 91, "sl": 85, "agents": 19},
    "BU4_Texts":  {"queue": 28, "aht": 200, "occ": 70, "adh": 92, "sl": 87, "agents": 12},
    "BU4_Emails": {"queue": 22, "aht": 265, "occ": 65, "adh": 93, "sl": 88, "agents":  8},
}

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
# GLOBAL CSS  (call once per page)
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

  /* Sidebar nav links */
  [data-testid="stSidebarNav"] { display: none !important; }

  /* Style manual page links */
  [data-testid="stPageLink"] p {
    font-size: 0.88rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    padding: 2px 0 !important;
  }
  [data-testid="stPageLink"]:hover p,
  [data-testid="stPageLink"][aria-current] p {
    color: #38bdf8 !important;
  }
</style>
"""

# ═══════════════════════════════════════════════════════════════════════════════
# DATA GENERATION
# ═══════════════════════════════════════════════════════════════════════════════
def generate_message(qkey: str, prev: dict) -> dict:
    p = QUEUE_PROFILES[qkey]

    def mean_revert(prev_val, baseline, lo, hi, sigma=0.025, pull=0.15):
        """Step toward baseline (pull) then add small noise.
        pull=0.15 means 15% of the gap to baseline is closed each tick,
        keeping the random walk anchored in OK territory."""
        target = prev_val + pull * (baseline - prev_val)
        noise  = np.random.normal(0, max(abs(target) * sigma, 0.3))
        return float(np.clip(target + noise, lo, hi))

    q  = mean_revert(prev.get("queue_volume",      p["queue"]), p["queue"], 0,   120)
    a  = mean_revert(prev.get("aht_seconds",       p["aht"]),   p["aht"],   60,  500)
    o  = mean_revert(prev.get("occupancy_pct",     p["occ"]),   p["occ"],   30,  100)
    d  = mean_revert(prev.get("adherence_pct",     p["adh"]),   p["adh"],   65,  100)
    sl = mean_revert(prev.get("service_level_pct", p["sl"]),    p["sl"],    50,  100)

    # Spikes: 1.5 % chance — sized to reach WARN territory, not CRIT.
    # A second independent spike on the same tick (0.015 * 0.015 = 0.02 %) is
    # what occasionally tips a value from WARN into CRIT, keeping CRIT rare.
    if random.random() < 0.015: q  = min(q  * random.uniform(1.4, 1.8), 120)
    if random.random() < 0.015: a  = min(a  * random.uniform(1.15, 1.4), 500)
    if random.random() < 0.015: sl = max(sl * random.uniform(0.82, 0.93), 50)

    agents  = max(1, p["agents"] + random.randint(-2, 3))
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
# SESSION STATE INIT + DATA TICK  (called at top of every page)
# ═══════════════════════════════════════════════════════════════════════════════
def init_and_tick():
    """Initialise session state on first load, then ingest a new data point
    only when POLL_SECS have elapsed — navigation reruns don't generate ticks."""
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
                          ignore_index=True)
                .tail(HIST_LEN)
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
        lat = st.session_state.history[qk].iloc[-1]
        rows.append({
            "queue_key":         qk,
            "bu":                qk.split("_")[0],
            "channel":           qk.split("_")[1],
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
# SIDEBAR STATUS PANEL  (call from every page)
# ═══════════════════════════════════════════════════════════════════════════════
def render_sidebar_status():
    with st.sidebar:
        # ── Branding ──────────────────────────────────────────────────────────
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

        # ── Manual navigation ─────────────────────────────────────────────────
        st.page_link("Home.py",          label="Overview", icon="🌐")
        st.page_link("pages/1_BU1.py",   label="BU1",      icon="🏢")
        st.page_link("pages/2_BU2.py",   label="BU2",      icon="🏢")
        st.page_link("pages/3_BU3.py",   label="BU3",      icon="🏢")
        st.page_link("pages/4_BU4.py",   label="BU4",      icon="🏢")

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


def make_multi_channel_chart(bu: str, metric_key: str, unit: str,
                              warn: float, crit: float, invert: bool = False,
                              height: int = 220) -> go.Figure:
    fig = go.Figure()
    all_vals = []
    for ch in CHANNELS:
        all_vals.extend(st.session_state.history[f"{bu}_{ch}"][metric_key].tolist())
    y_max = max(max(all_vals) * 1.2, crit * 1.1) if all_vals else crit * 1.2
    y_min = max(min(all_vals) * 0.85, 0)         if all_vals else 0
    _add_bands(fig, warn, crit, y_min, y_max, invert)

    for ch in CHANNELS:
        df_q  = st.session_state.history[f"{bu}_{ch}"]
        color = CHANNEL_COLORS[ch]
        fig.add_trace(go.Scatter(
            x=df_q["ts"], y=df_q[metric_key],
            line=dict(color=color, width=2.2), mode="lines",
            name=f"{CHANNEL_ICONS[ch]} {ch}",
            hovertemplate=f"<b>{ch}: %{{y:.0f}} {unit}</b><br>%{{x|%H:%M:%S}}<extra></extra>",
        ))
        fig.add_trace(go.Scatter(
            x=[df_q["ts"].iloc[-1]], y=[df_q[metric_key].iloc[-1]],
            mode="markers",
            marker=dict(color=color, size=7, line=dict(color="#0b0f1a", width=2)),
            showlegend=False, hoverinfo="skip",
        ))

    layout = _base_layout(height)
    layout["showlegend"] = True
    layout["legend"] = dict(
        orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
        font=dict(color="#94a3b8", size=10), bgcolor="rgba(0,0,0,0)",
    )
    layout["yaxis"]["ticksuffix"] = f" {unit}"
    fig.update_layout(**layout)
    return fig


def make_heatmap(lv: pd.DataFrame) -> go.Figure:
    metric_keys   = ["queue_volume", "aht_seconds", "occupancy_pct", "adherence_pct", "service_level_pct"]
    metric_labels = ["Queue Vol", "AHT (s)", "Occupancy %", "Adherence %", "Svc Level %"]
    units         = ["", "s", "%", "%", "%"]

    queue_labels, z_vals, z_text = [], [], []
    for _, row in lv.iterrows():
        queue_labels.append(f"{row['bu']}  {CHANNEL_ICONS[row['channel']]} {row['channel']}")
        row_z, row_t = [], []
        for mk, u in zip(metric_keys, units):
            row_z.append(severity_score(mk, row[mk]))
            row_t.append(f"{row[mk]:.0f}{u}")
        z_vals.append(row_z)
        z_text.append(row_t)

    colorscale = [
        [0.0, "#14532d"], [0.45, "#14532d"],
        [0.5, "#78350f"], [0.74, "#78350f"],
        [0.75, "#7f1d1d"], [1.0, "#7f1d1d"],
    ]
    fig = go.Figure(data=go.Heatmap(
        z=z_vals, x=metric_labels, y=queue_labels,
        text=z_text, texttemplate="<b>%{text}</b>",
        textfont=dict(size=11, color="white"),
        colorscale=colorscale, zmin=0, zmax=1,
        showscale=False, xgap=3, ygap=3,
        hovertemplate="<b>%{y}</b><br>%{x}: %{text}<extra></extra>",
    ))
    fig.update_layout(
        paper_bgcolor=CHART_BG, plot_bgcolor=CHART_BG,
        margin=dict(l=10, r=10, t=10, b=10), height=440,
        xaxis=dict(side="top", tickfont=dict(color="#94a3b8", size=12), tickangle=0),
        yaxis=dict(tickfont=dict(color="#94a3b8", size=11), autorange="reversed"),
    )
    return fig


# ═══════════════════════════════════════════════════════════════════════════════
# BU PAGE RENDERER  (reused by all four BU pages)
# ═══════════════════════════════════════════════════════════════════════════════
def render_bu_page(bu: str):
    render_header(bu, "📞 CALLS  ·  💬 TEXTS  ·  📧 EMAILS")
    lv    = latest_values()
    bu_lv = lv[lv["bu"] == bu].reset_index(drop=True)

    # ── Channel Snapshot Cards ──────────────────────────────────────────────
    st.markdown('<p class="section-label">📊 Channel Snapshot</p>', unsafe_allow_html=True)
    ch_cols = st.columns(3)

    for col, ch in zip(ch_cols, CHANNELS):
        row   = bu_lv[bu_lv["channel"] == ch].iloc[0]
        color = CHANNEL_COLORS[ch]
        icon  = CHANNEL_ICONS[ch]
        df_q  = st.session_state.history[f"{bu}_{ch}"]
        prev  = df_q.iloc[-2] if len(df_q) > 1 else df_q.iloc[-1]

        def _kpi_cell(label, val, fmt, unit, mk, prev_val):
            sc     = severity_score(mk, val)
            clr    = sev_color(sc)
            delta  = val - prev_val
            up_good = THRESHOLDS[mk]["invert"]
            if abs(delta) < 0.05:
                d_clr = "#475569"
            else:
                d_clr = "#22c55e" if (delta > 0) == up_good else "#ef4444"
            arrow = "▲" if delta > 0 else "▼"
            return (
                f"<div style='background:#0d1117;border-radius:6px;padding:10px 12px;"
                f"border:1px solid #1e293b;border-left:2px solid {clr};'>"
                f"<div style='font-size:0.6rem;color:#475569;text-transform:uppercase;"
                f"letter-spacing:0.08em;margin-bottom:3px;'>{label}</div>"
                f"<div style='font-size:1.3rem;font-weight:800;color:{clr};'>"
                f"{val:{fmt}}{unit}</div>"
                f"<div style='font-size:0.65rem;color:{d_clr};margin-top:1px;'>"
                f"{arrow} {abs(delta):.0f}</div></div>"
            )

        kpis = (
            _kpi_cell("Queue",         row["queue_volume"],      ".0f", "",  "queue_volume",      prev["queue_volume"])      +
            _kpi_cell("AHT",           row["aht_seconds"],       ".0f", "s", "aht_seconds",       prev["aht_seconds"])       +
            _kpi_cell("Service Level", row["service_level_pct"], ".0f", "%", "service_level_pct", prev["service_level_pct"]) +
            _kpi_cell("Occupancy",     row["occupancy_pct"],     ".0f", "%", "occupancy_pct",     prev["occupancy_pct"])     +
            _kpi_cell("Adherence",     row["adherence_pct"],     ".0f", "%", "adherence_pct",     prev["adherence_pct"])
        )

        handle_rate = (row["cases_handled"] / row["cases_offered"] * 100
                       if row["cases_offered"] > 0 else 0)

        with col:
            st.markdown(
                f"<div style='background:#111827;border:1px solid #1e293b;"
                f"border-top:3px solid {color};border-radius:10px;padding:16px;'>"
                f"<div style='font-size:1rem;font-weight:800;color:{color};"
                f"margin-bottom:12px;letter-spacing:0.04em;'>{icon} {ch}</div>"
                f"<div style='display:grid;grid-template-columns:1fr 1fr;"
                f"gap:8px;margin-bottom:12px;'>{kpis}</div>"
                f"<div style='font-size:0.68rem;color:#475569;"
                f"display:flex;justify-content:space-between;"
                f"border-top:1px solid #1e293b;padding-top:8px;'>"
                f"<span>👥 {int(row['agents_logged'])} agents</span>"
                f"<span>📥 {int(row['cases_offered'])} offered</span>"
                f"<span>✅ {handle_rate:.0f}% handled</span>"
                f"</div></div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Alert Banners ───────────────────────────────────────────────────────
    with st.expander("🚨 Alert Status", expanded=True):
        for ch in CHANNELS:
            row   = bu_lv[bu_lv["channel"] == ch].iloc[0]
            color = CHANNEL_COLORS[ch]
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
                    f"<span style='color:{clr};font-weight:700;'>{sev_label(sc)} "
                    f"{name}: {row[mk]:.0f}{unit}</span>"
                )
            sep = "&nbsp;&nbsp;·&nbsp;&nbsp;"
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #1e293b;"
                f"border-left:3px solid {color};border-radius:6px;"
                f"padding:9px 14px;margin-bottom:6px;font-size:0.8rem;'>"
                f"<strong style='color:{color};'>{CHANNEL_ICONS[ch]} {ch}</strong>"
                f"&emsp;&nbsp;{sep.join(parts)}</div>",
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Metric Charts ───────────────────────────────────────────────────────
    st.markdown(
        f'<p class="section-label">📈 Metric Trends — '
        f'<span style="color:#38bdf8;">📞 Calls</span> &nbsp;'
        f'<span style="color:#a78bfa;">💬 Texts</span> &nbsp;'
        f'<span style="color:#34d399;">📧 Emails</span></p>',
        unsafe_allow_html=True,
    )

    r1c1, r1c2, r1c3 = st.columns(3)
    r2c1, r2c2       = st.columns(2)

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
            fig = make_multi_channel_chart(bu, mkey, unit, warn, crit, invert)
            st.plotly_chart(fig, use_container_width=True,
                            config={"displayModeBar": False})