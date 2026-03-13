"""
Home.py — GCC Overview page (entry point).
Run with:  streamlit run Home.py
"""
import time
import streamlit as st
from utils import (
    GLOBAL_CSS, BUS, BU_COLORS, CHANNEL_ICONS, ALL_METRICS,
    init_and_tick, latest_values, render_header, render_sidebar_status,
    severity_score, sev_color, sev_label, make_heatmap, POLL_SECS,
)

st.set_page_config(
    page_title="GCC · Overview",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# ── Data tick ──────────────────────────────────────────────────────────────────
init_and_tick()

render_sidebar_status()

# ── Page content ───────────────────────────────────────────────────────────────
render_header("OVERVIEW", "ALL BUs · ALL QUEUES")
lv = latest_values()

# Fleet KPIs
st.markdown('<p class="section-label">🌐 Global Summary</p>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
c1.metric("Total Queues",    "12")
c2.metric("Total Agents",    f"{int(lv['agents_logged'].sum())}")
c3.metric("Cases In Queue",  f"{lv['queue_volume'].sum():.0f}")
c4.metric("Peak Queue",      f"{lv['queue_volume'].max():.0f}")
c5.metric("Global Avg AHT",   f"{lv['aht_seconds'].mean():.0f}s")
c6.metric("Global Svc Level", f"{lv['service_level_pct'].mean():.0f}%")
c7.metric("Global Occupancy", f"{lv['occupancy_pct'].mean():.0f}%")
c8.metric("Global Adherence", f"{lv['adherence_pct'].mean():.0f}%")

st.markdown("<br>", unsafe_allow_html=True)

# BU Roll-up Cards
st.markdown('<p class="section-label">🏢 BU Status Roll-up</p>', unsafe_allow_html=True)
bu_cols = st.columns(4)

for col, bu in zip(bu_cols, BUS):
    bu_rows = lv[lv["bu"] == bu]
    all_scores = [
        severity_score(mk, row[mk])
        for _, row in bu_rows.iterrows()
        for mk in ALL_METRICS
    ]
    worst  = max(all_scores) if all_scores else 0
    bu_clr = sev_color(worst)
    bu_lbl = sev_label(worst)

    ch_html = ""
    for _, row in bu_rows.iterrows():
        ch_sc  = max(severity_score(mk, row[mk]) for mk in ALL_METRICS)
        ch_clr = sev_color(ch_sc)
        q_sc   = severity_score("queue_volume",      row["queue_volume"])
        sl_sc  = severity_score("service_level_pct", row["service_level_pct"])
        ch_html += (
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:5px 0;border-bottom:1px solid #1e293b;'>"
            f"<span style='font-size:0.75rem;color:#94a3b8;'>"
            f"{CHANNEL_ICONS[row['channel']]} {row['channel']}</span>"
            f"<span style='font-size:0.68rem;color:#64748b;'>"
            f"Q:<b style='color:{sev_color(q_sc)};'>{row['queue_volume']:.0f}</b>"
            f" SL:<b style='color:{sev_color(sl_sc)};'>{row['service_level_pct']:.0f}%</b>"
            f"</span>"
            f"<span style='font-size:0.65rem;font-weight:800;color:{ch_clr};'>"
            f"{sev_label(ch_sc)}</span></div>"
        )

    with col:
        st.markdown(
            f"<div style='background:#111827;border:1px solid #1e293b;"
            f"border-top:3px solid {BU_COLORS[bu]};border-radius:8px;padding:14px;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;"
            f"margin-bottom:10px;'>"
            f"<span style='font-size:1.05rem;font-weight:900;color:{BU_COLORS[bu]};'>{bu}</span>"
            f"<span style='font-size:0.65rem;font-weight:800;color:{bu_clr};"
            f"background:rgba(0,0,0,0.4);padding:3px 8px;border-radius:4px;'>{bu_lbl}</span>"
            f"</div>{ch_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# Worst Performers
st.markdown('<p class="section-label">🚨 Worst Performers — live ranked</p>',
            unsafe_allow_html=True)

wp_panels = [
    ("queue_volume",      "📥 Queue Volume",  "cases", False),
    ("aht_seconds",       "⏱ AHT",            "s",     False),
    ("service_level_pct", "📶 Service Level",  "%",     True),
    ("occupancy_pct",     "🔥 Occupancy",      "%",     False),
    ("adherence_pct",     "📋 Adherence",      "%",     True),
]
wp_cols = st.columns(5)

for col, (mkey, mname, unit, invert) in zip(wp_cols, wp_panels):
    with col:
        st.markdown(
            f"<p style='font-size:0.65rem;font-weight:700;letter-spacing:0.12em;"
            f"color:#64748b;text-transform:uppercase;margin-bottom:8px;'>{mname}</p>",
            unsafe_allow_html=True,
        )
        ranked = lv.nsmallest(5, mkey) if invert else lv.nlargest(5, mkey)
        for rank, (_, row) in enumerate(ranked.iterrows(), 1):
            val    = row[mkey]
            score  = severity_score(mkey, val)
            clr    = sev_color(score)
            lbl    = sev_label(score)
            bu_clr = BU_COLORS[row["bu"]]
            ch_ic  = CHANNEL_ICONS[row["channel"]]
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #1e293b;"
                f"border-left:3px solid {clr};border-radius:6px;"
                f"padding:8px 10px;margin-bottom:5px;'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:2px;'>"
                f"<span style='font-size:0.78rem;font-weight:700;color:{bu_clr};'>"
                f"#{rank} {row['bu']}</span>"
                f"<span style='font-size:0.58rem;font-weight:800;color:{clr};"
                f"background:rgba(0,0,0,0.4);padding:2px 5px;border-radius:3px;'>"
                f"{lbl}</span></div>"
                f"<div style='display:flex;justify-content:space-between;align-items:baseline;'>"
                f"<span style='font-size:0.72rem;color:#64748b;'>{ch_ic} {row['channel']}</span>"
                f"<span style='font-size:1.1rem;font-weight:800;color:{clr};'>{val:.0f}"
                f"<span style='font-size:0.62rem;font-weight:400;color:#64748b;'> {unit}</span>"
                f"</span></div></div>",
                unsafe_allow_html=True,
            )

st.markdown("<br>", unsafe_allow_html=True)

# Heatmap
st.markdown(
    '<p class="section-label">🗺 Queue Health Heatmap — 12 queues × 5 metrics</p>',
    unsafe_allow_html=True,
)
st.plotly_chart(make_heatmap(lv), use_container_width=True,
                config={"displayModeBar": False})

# Auto-refresh
time.sleep(1)
st.rerun()