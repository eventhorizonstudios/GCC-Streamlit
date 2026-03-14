"""
Home.py — GCC Overview page.
Run with:  streamlit run Home.py
"""
import time
import streamlit as st
from utils import (
    GLOBAL_CSS, BUS, REGIONS, ACTIVITIES, BU_COLORS, REGION_COLORS,
    ACTIVITY_COLORS, ACTIVITY_SHORT, REGION_SHORT, ALL_METRICS, QK_META,
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

# ── Page ───────────────────────────────────────────────────────────────────────
render_header("OVERVIEW", "4 BUs  ·  3 REGIONS  ·  6 ACTIVITIES  ·  72 QUEUES")
lv = latest_values()

# ── Global Summary KPIs ────────────────────────────────────────────────────────
st.markdown('<p class="section-label">🌐 Global Summary</p>', unsafe_allow_html=True)
c1, c2, c3, c4, c5, c6, c7, c8 = st.columns(8)
c1.metric("Total Queues",    "72")
c2.metric("Total Agents",    f"{int(lv['agents_logged'].sum())}")
c3.metric("Cases In Queue",  f"{lv['queue_volume'].sum():.0f}")
c4.metric("Peak Queue",      f"{lv['queue_volume'].max():.0f}")
c5.metric("Global Avg AHT",  f"{lv['aht_seconds'].mean():.0f}s")
c6.metric("Global Svc Level",f"{lv['service_level_pct'].mean():.0f}%")
c7.metric("Global Occupancy",f"{lv['occupancy_pct'].mean():.0f}%")
c8.metric("Global Adherence",f"{lv['adherence_pct'].mean():.0f}%")

st.markdown("<br>", unsafe_allow_html=True)

# ── BU Status Roll-up ─────────────────────────────────────────────────────────
st.markdown('<p class="section-label">🏢 BU Status Roll-up</p>', unsafe_allow_html=True)
bu_cols = st.columns(4)

for col, bu in zip(bu_cols, BUS):
    bu_rows = lv[lv["bu"] == bu]
    all_scores = [
        severity_score(mk, v)
        for mk in ALL_METRICS
        for v in bu_rows[mk]
    ]
    worst  = max(all_scores) if all_scores else 0
    bu_clr = sev_color(worst)
    bu_lbl = sev_label(worst)

    region_html = ""
    for region in REGIONS:
        reg_rows  = bu_rows[bu_rows["region"] == region]
        reg_scores = [severity_score(mk, v) for mk in ALL_METRICS for v in reg_rows[mk]]
        reg_sc    = max(reg_scores) if reg_scores else 0
        reg_clr   = sev_color(reg_sc)
        q_worst   = reg_rows["queue_volume"].max()
        sl_worst  = reg_rows["service_level_pct"].min()
        q_sc      = severity_score("queue_volume",      q_worst)
        sl_sc     = severity_score("service_level_pct", sl_worst)
        rshort    = REGION_SHORT[region]
        region_html += (
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;padding:5px 0;border-bottom:1px solid #1e293b;'>"
            f"<span style='font-size:0.75rem;font-weight:600;"
            f"color:{REGION_COLORS[region]};'>{rshort}</span>"
            f"<span style='font-size:0.68rem;color:#64748b;'>"
            f"Q:<b style='color:{sev_color(q_sc)};'>{q_worst:.0f}</b>"
            f"&nbsp;SL:<b style='color:{sev_color(sl_sc)};'>{sl_worst:.0f}%</b>"
            f"</span>"
            f"<span style='font-size:0.65rem;font-weight:800;color:{reg_clr};'>"
            f"{sev_label(reg_sc)}</span></div>"
        )

    with col:
        st.markdown(
            f"<div style='background:#111827;border:1px solid #1e293b;"
            f"border-top:3px solid {BU_COLORS[bu]};border-radius:8px;padding:14px;'>"
            f"<div style='display:flex;justify-content:space-between;"
            f"align-items:center;margin-bottom:10px;'>"
            f"<span style='font-size:1.05rem;font-weight:900;color:{BU_COLORS[bu]};'>"
            f"{bu}</span>"
            f"<span style='font-size:0.65rem;font-weight:800;color:{bu_clr};"
            f"background:rgba(0,0,0,0.4);padding:3px 8px;border-radius:4px;'>"
            f"{bu_lbl}</span></div>"
            f"{region_html}</div>",
            unsafe_allow_html=True,
        )

st.markdown("<br>", unsafe_allow_html=True)

# ── Worst Performers ──────────────────────────────────────────────────────────
st.markdown('<p class="section-label">🚨 Worst Performers — live ranked across all 72 queues</p>',
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
            val      = row[mkey]
            score    = severity_score(mkey, val)
            clr      = sev_color(score)
            lbl      = sev_label(score)
            bu_clr   = BU_COLORS[row["bu"]]
            act_clr  = ACTIVITY_COLORS[row["activity"]]
            ashort   = ACTIVITY_SHORT[row["activity"]]
            rshort   = REGION_SHORT[row["region"]]
            st.markdown(
                f"<div style='background:#0d1117;border:1px solid #1e293b;"
                f"border-left:3px solid {clr};border-radius:6px;"
                f"padding:8px 10px;margin-bottom:5px;'>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:center;margin-bottom:2px;'>"
                f"<span style='font-size:0.75rem;font-weight:700;color:{bu_clr};'>"
                f"#{rank} {row['bu']}</span>"
                f"<span style='font-size:0.58rem;font-weight:800;color:{clr};"
                f"background:rgba(0,0,0,0.4);padding:2px 5px;border-radius:3px;'>"
                f"{lbl}</span></div>"
                f"<div style='display:flex;justify-content:space-between;"
                f"align-items:baseline;'>"
                f"<span style='font-size:0.68rem;color:#475569;'>"
                f"{rshort} · <span style='color:{act_clr};'>{ashort}</span></span>"
                f"<span style='font-size:1.1rem;font-weight:800;color:{clr};'>{val:.0f}"
                f"<span style='font-size:0.62rem;font-weight:400;color:#64748b;'> {unit}</span>"
                f"</span></div></div>",
                unsafe_allow_html=True,
            )

st.markdown("<br>", unsafe_allow_html=True)

# ── Health Heatmap ────────────────────────────────────────────────────────────
st.markdown(
    '<p class="section-label">🗺 Region Health Heatmap — 12 regions × 5 metrics '
    '(worst activity per cell)</p>',
    unsafe_allow_html=True,
)
st.plotly_chart(make_heatmap(lv), use_container_width=True,
                config={"displayModeBar": False})

# ── Auto-refresh ──────────────────────────────────────────────────────────────
time.sleep(1)
st.rerun()