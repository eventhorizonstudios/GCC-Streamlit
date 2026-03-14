"""
Home.py — GCC Overview  (TV monitoring display)

Layout:
  • Sticky header bar — GCC branding + 8 global KPIs + last-poll clock
  • Body — 4 BU sections stacked vertically, each containing 3 region columns
    (West / Central / East).  Every region column lists its 6 activities.
  • Each activity row shows:
      [status dot]  [name + BU/region]  [latest SL value]  [SL sparkline]
  • Click the ▶ / ▼ toggle button to expand an activity row and reveal all
    5 metric charts beneath it.  Click again to collapse.
  • Multiple activities can be expanded simultaneously.
"""

import time
import streamlit as st
from utils import (
    GLOBAL_CSS, BUS, REGIONS, ACTIVITIES, QUEUE_KEYS, QK_META,
    BU_COLORS, REGION_COLORS, ACTIVITY_COLORS, ACTIVITY_SHORT,
    CHART_METRIC_CFG, ALL_METRICS,
    init_and_tick, latest_values, render_sidebar_status,
    severity_score, sev_color, sev_label,
    make_sl_sparkline, make_single_activity_chart,
    POLL_SECS, _qk,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GCC · Overview",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",   # maximise screen real estate on TV
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Extra TV-optimised CSS
st.markdown("""
<style>
  /* Tighten block padding for dense TV layout */
  .block-container { padding: 3rem 1.5rem 1rem !important; }

  /* Activity row hover highlight */
  .act-row:hover { background: #131b2e !important; }

  /* Hide sidebar toggle button — TV mode */
  [data-testid="collapsedControl"] { display: none !important; }

  /* Reduce plotly chart top whitespace */
  .js-plotly-plot .plotly { margin-top: 0 !important; }

  /* BU section header */
  .bu-header {
    font-size: 1.1rem; font-weight: 900; letter-spacing: 0.08em;
    padding: 10px 0 6px; margin-bottom: 4px;
    border-bottom: 2px solid;
  }

  /* Region column header */
  .region-header {
    font-size: 0.68rem; font-weight: 700; letter-spacing: 0.12em;
    text-transform: uppercase; padding: 6px 0 4px;
    border-bottom: 1px solid #1e293b; margin-bottom: 6px;
  }

  /* Expand button — ghost style */
  div[data-testid="stButton"] > button {
    background: transparent !important;
    border: none !important;
    color: #334155 !important;
    padding: 0 4px !important;
    font-size: 0.65rem !important;
    line-height: 1 !important;
    min-height: 0 !important;
    height: 18px !important;
  }
  div[data-testid="stButton"] > button:hover {
    color: #38bdf8 !important;
    background: transparent !important;
  }

  /* Expanded metric panel */
  .metric-panel {
    background: #0d1117;
    border: 1px solid #1e293b;
    border-radius: 8px;
    padding: 12px;
    margin: 4px 0 10px;
  }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA TICK + SESSION STATE
# ═══════════════════════════════════════════════════════════════════════════════
init_and_tick()
render_sidebar_status()

# Track which activity rows are expanded (set of queue keys)
if "expanded" not in st.session_state:
    st.session_state.expanded = set()

lv = latest_values()

# ═══════════════════════════════════════════════════════════════════════════════
# HEADER BAR
# ═══════════════════════════════════════════════════════════════════════════════
latest_ts = max(st.session_state.prev_msg[qk]["ts"] for qk in QUEUE_KEYS)

hc1, hc2, hc3, hc4, hc5, hc6, hc7, hc8, hc9, hc10 = st.columns([3, 1, 1, 1, 1, 1, 1, 1, 1, 1.5])

with hc1:
    st.markdown(
        "<div style='padding:4px 0;'>"
        "<span style='font-size:1.3rem;font-weight:900;color:#38bdf8;"
        "letter-spacing:0.1em;'>📡 GCC</span>"
        "<span style='font-size:0.65rem;color:#334155;margin-left:10px;"
        "letter-spacing:0.08em;'>GLOBAL CONTACT CENTRE · LIVE MONITOR</span>"
        "</div>",
        unsafe_allow_html=True,
    )

kpi_defs = [
    ("Agents",    f"{int(lv['agents_logged'].sum())}"),
    ("In Queue",  f"{lv['queue_volume'].sum():.0f}"),
    ("Peak Q",    f"{lv['queue_volume'].max():.0f}"),
    ("Avg AHT",   f"{lv['aht_seconds'].mean():.0f}s"),
    ("Svc Level", f"{lv['service_level_pct'].mean():.0f}%"),
    ("Occupancy", f"{lv['occupancy_pct'].mean():.0f}%"),
    ("Adherence", f"{lv['adherence_pct'].mean():.0f}%"),
]
for col, (label, val) in zip([hc2, hc3, hc4, hc5, hc6, hc7, hc8], kpi_defs):
    with col:
        st.markdown(
            f"<div style='text-align:center;background:#111827;border:1px solid #1e293b;"
            f"border-radius:8px;padding:5px 4px;'>"
            f"<div style='font-size:0.58rem;color:#475569;text-transform:uppercase;"
            f"letter-spacing:0.07em;'>{label}</div>"
            f"<div style='font-size:1.1rem;font-weight:800;color:#f1f5f9;'>{val}</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

with hc9:
    # Collapse-all / expand-all controls
    st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)
    if st.button("⊕ All", key="expand_all", help="Expand all activities"):
        st.session_state.expanded = set(QUEUE_KEYS)
        st.rerun()

with hc10:
    st.markdown(
        f"<div style='text-align:right;padding:4px 0;'>"
        f"<span style='font-size:0.6rem;color:#334155;letter-spacing:0.08em;'>LAST POLL</span><br>"
        f"<span style='font-size:1rem;font-weight:800;color:#38bdf8;'>"
        f"{latest_ts.strftime('%H:%M:%S')}</span>"
        f"<span style='font-size:0.6rem;color:#1e293b;margin-left:6px;'>"
        f"#{st.session_state.tick}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin:6px 0 10px;border-color:#1e293b;'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# MAIN GRID — Region tabs × BU sections (stacked) × 2×3 activity card grid
# ═══════════════════════════════════════════════════════════════════════════════
region_tabs = st.tabs([f"📍 {r}" for r in REGIONS])

for tab, region in zip(region_tabs, REGIONS):
    with tab:
        # 4 BU sections stacked vertically, each with a 2×3 sparkline card grid
        for bu in BUS:
            bu_color = BU_COLORS[bu]

            # BU section header
            st.markdown(
                f"<div class='bu-header' style='color:{bu_color};"
                f"border-color:{bu_color}33;'>{bu}</div>",
                unsafe_allow_html=True,
            )

            # Split 6 activities into two rows of 3
            row_a = ACTIVITIES[:3]   # A1, A2, A3
            row_b = ACTIVITIES[3:]   # A4, A5, A6

            for row_acts in (row_a, row_b):
                card_cols = st.columns(3)

                # ── 3 sparkline cards ─────────────────────────────────────────
                for card_col, activity in zip(card_cols, row_acts):
                    qk        = _qk(bu, region, activity)
                    row_data  = lv[lv["queue_key"] == qk].iloc[0]
                    act_color = ACTIVITY_COLORS[activity]
                    short     = ACTIVITY_SHORT[activity]
                    sl_val    = row_data["service_level_pct"]
                    sl_sc     = severity_score("service_level_pct", sl_val)
                    sl_clr    = sev_color(sl_sc)
                    dot_clr   = sl_clr
                    is_exp    = qk in st.session_state.expanded

                    # Overall worst score for the card border
                    card_sc   = max(severity_score(mk, row_data[mk]) for mk in ALL_METRICS)
                    card_clr  = sev_color(card_sc)
                    card_lbl  = sev_label(card_sc)

                    with card_col:
                        # Card header row — name + badge + SL value + toggle
                        hc1, hc2, hc3 = st.columns([2, 1, 0.8])

                        with hc1:
                            st.markdown(
                                f"<div style='padding-top:4px;'>"
                                f"<span style='display:inline-block;width:8px;height:8px;"
                                f"border-radius:50%;background:{dot_clr};"
                                f"margin-right:5px;vertical-align:middle;'></span>"
                                f"<span style='font-size:0.82rem;font-weight:700;"
                                f"color:{act_color};'>{short}</span>"
                                f"<span style='font-size:0.62rem;color:#475569;"
                                f"margin-left:4px;'>{activity}</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        with hc2:
                            st.markdown(
                                f"<div style='text-align:center;padding-top:2px;'>"
                                f"<span style='font-size:1.25rem;font-weight:900;"
                                f"color:{sl_clr};'>{sl_val:.0f}%</span>"
                                f"<span style='font-size:0.55rem;color:#334155;"
                                f"display:block;margin-top:-2px;'>SL</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        with hc3:
                            toggle_label = "▼" if is_exp else "▶"
                            if st.button(toggle_label, key=f"tog_{qk}",
                                         help="Expand / hide metrics"):
                                if is_exp:
                                    st.session_state.expanded.discard(qk)
                                else:
                                    st.session_state.expanded.add(qk)
                                st.rerun()

                        # Sparkline — full width of the card
                        fig_sl = make_sl_sparkline(qk, act_color, height=80)
                        st.plotly_chart(
                            fig_sl, use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"sl_{qk}",
                        )

                # ── Expanded panels for this row — full width, one per activity
                for activity in row_acts:
                    qk       = _qk(bu, region, activity)
                    row_data = lv[lv["queue_key"] == qk].iloc[0]
                    act_color = ACTIVITY_COLORS[activity]
                    short     = ACTIVITY_SHORT[activity]
                    is_exp    = qk in st.session_state.expanded

                    exp_slot = st.empty()
                    if is_exp:
                        with exp_slot.container():
                            all_sc  = max(severity_score(mk, row_data[mk]) for mk in ALL_METRICS)
                            hdr_clr = sev_color(all_sc)

                            # Alert summary bar
                            alert_parts = []
                            for mk, mname, unit in [
                                ("queue_volume",      "Q",   ""),
                                ("aht_seconds",       "AHT", "s"),
                                ("service_level_pct", "SL",  "%"),
                                ("occupancy_pct",     "Occ", "%"),
                                ("adherence_pct",     "Adh", "%"),
                            ]:
                                sc  = severity_score(mk, row_data[mk])
                                clr = sev_color(sc)
                                lbl = sev_label(sc)
                                alert_parts.append(
                                    f"<span style='color:{clr};font-size:0.72rem;"
                                    f"font-weight:700;'>{lbl} {mname}:"
                                    f"<b>{row_data[mk]:.0f}{unit}</b></span>"
                                )
                            sep = "&nbsp;<span style='color:#1e293b;'>|</span>&nbsp;"

                            st.markdown(
                                f"<div style='background:#0d1117;"
                                f"border:1px solid {hdr_clr}33;"
                                f"border-left:3px solid {hdr_clr};"
                                f"border-radius:6px;padding:7px 12px;"
                                f"margin:2px 0 6px;'>"
                                f"<span style='font-size:0.72rem;font-weight:800;"
                                f"color:{act_color};margin-right:10px;'>"
                                f"{short} · {activity}</span>"
                                f"{sep.join(alert_parts)}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                            # 4 metric charts — SL omitted (already visible as sparkline)
                            non_sl_cfg = [(mk, mn, u, w, c, inv)
                                          for mk, mn, u, w, c, inv in CHART_METRIC_CFG
                                          if mk != "service_level_pct"]
                            chart_cols = st.columns(4)
                            for cc, (mkey, mname, unit, warn, crit, invert) in zip(
                                chart_cols, non_sl_cfg
                            ):
                                with cc:
                                    fig_m = make_single_activity_chart(
                                        qk, mkey, mname, unit,
                                        warn, crit, invert,
                                        act_color, height=155,
                                    )
                                    st.plotly_chart(
                                        fig_m, use_container_width=True,
                                        config={"displayModeBar": False},
                                        key=f"m_{qk}_{mkey}",
                                    )

            st.markdown("<div style='height:8px;'></div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# AUTO-REFRESH
# ═══════════════════════════════════════════════════════════════════════════════
st.rerun(after=POLL_SECS)