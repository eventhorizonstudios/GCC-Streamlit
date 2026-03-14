"""
Home.py — GCC Overview (TV monitoring display)
Run with:  streamlit run Home.py
"""

from datetime import datetime
from zoneinfo import ZoneInfo
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from utils import (
    GLOBAL_CSS, BUS, REGIONS, ACTIVITIES, QUEUE_KEYS, QK_META,
    BU_COLORS, REGION_COLORS, ACTIVITY_COLORS, ACTIVITY_SHORT,
    CHART_METRIC_CFG, ALL_METRICS, POLL_SECS,
    init_and_tick, latest_values,
    severity_score, sev_color, sev_label,
    make_sl_sparkline, make_single_activity_chart, make_plain_chart,
    _qk,
)

# ═══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ═══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="GCC · Overview",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={},
)

st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Non-blocking refresh — no sleep, button clicks remain instant
st_autorefresh(interval=POLL_SECS * 1000, key="data_refresh")

# TV-optimised CSS additions
st.markdown("""
<style>
  .block-container { padding: 0.5rem 1.5rem 1rem !important; }
  .bu-header {
    font-size: 1.1rem; font-weight: 900; letter-spacing: 0.08em;
    padding: 10px 0 6px; margin-bottom: 4px; border-bottom: 2px solid;
  }
  div[data-testid="stButton"] > button {
    background: transparent !important; border: none !important;
    color: #334155 !important; padding: 0 4px !important;
    font-size: 0.65rem !important; line-height: 1 !important;
    min-height: 0 !important; height: 18px !important;
  }
  div[data-testid="stButton"] > button:hover {
    color: #38bdf8 !important; background: transparent !important;
  }
</style>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# DATA + SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
init_and_tick()
if "expanded" not in st.session_state:
    st.session_state.expanded = set()

# Timezone mapping for region summary clocks
REGION_TZ = {
    "West":    ZoneInfo("America/Chicago"),
    "Central": ZoneInfo("Europe/Tallinn"),
    "East":    ZoneInfo("Asia/Singapore"),
}

# Pre-computed once — SL excluded from expansion charts (shown as sparkline)
NON_SL_CFG = [
    (mk, mn, u, w, c, inv)
    for mk, mn, u, w, c, inv in CHART_METRIC_CFG
    if mk != "service_level_pct"
]

lv = latest_values()

# ═══════════════════════════════════════════════════════════════════════════════
# TITLE BAR
# ═══════════════════════════════════════════════════════════════════════════════
latest_ts = max(st.session_state.prev_msg[qk]["ts"] for qk in QUEUE_KEYS)

title_col, clock_col = st.columns([8, 1.5])
with title_col:
    st.markdown(
        "<div style='padding:4px 0;'>"
        "<span style='font-size:1.3rem;font-weight:900;color:#38bdf8;"
        "letter-spacing:0.1em;'>📡 GCC</span>"
        "<span style='font-size:0.65rem;color:#334155;margin-left:10px;"
        "letter-spacing:0.08em;'>GLOBAL CONTACT CENTRE · LIVE MONITOR</span>"
        "</div>",
        unsafe_allow_html=True,
    )
with clock_col:
    st.markdown(
        f"<div style='text-align:right;padding:4px 0;'>"
        f"<span style='font-size:0.6rem;color:#334155;letter-spacing:0.08em;'>LAST POLL (UTC)</span><br>"
        f"<span style='font-size:0.65rem;color:#475569;'>{latest_ts.strftime('%d/%m/%Y')}</span><br>"
        f"<span style='font-size:1rem;font-weight:800;color:#38bdf8;'>"
        f"{latest_ts.strftime('%H:%M:%S')}</span>"
        f"<span style='font-size:0.6rem;color:#1e293b;margin-left:6px;'>"
        f"#{st.session_state.tick}</span>"
        f"</div>",
        unsafe_allow_html=True,
    )
st.markdown("<hr style='margin:4px 0 8px;border-color:#1e293b;'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# REGION SUMMARY ROWS  (one per region, identical metrics scoped to that region)
# ═══════════════════════════════════════════════════════════════════════════════
def _region_summary_row(region: str):
    reg_color = REGION_COLORS[region]
    reg_keys  = [qk for qk in QUEUE_KEYS if QK_META[qk]["region"] == region]
    reg_lv    = lv[lv["region"] == region]

    # Status counts — scoped to SVC Level only, consistent with sparklines and worst queue tile
    r_crit = sum(
        1 for qk in reg_keys
        if severity_score("service_level_pct",
                          st.session_state.prev_msg[qk]["service_level_pct"]) >= 1.0
    )
    r_warn = sum(
        1 for qk in reg_keys
        if severity_score("service_level_pct",
                          st.session_state.prev_msg[qk]["service_level_pct"]) == 0.5
    )
    r_ok = len(reg_keys) - r_crit - r_warn

    # Worst queue by SVC Level in this region
    worst_row  = reg_lv.loc[reg_lv["service_level_pct"].idxmin()]
    worst_sl   = worst_row["service_level_pct"]
    worst_sl_sc  = severity_score("service_level_pct", worst_sl)
    worst_sl_clr = sev_color(worst_sl_sc)

    # Column layout: region label | CRIT | WARN | OK | Avg SL | Worst Queue | Queue Vol | Occupancy | Adherence
    (label_col, crit_col, warn_col, ok_col,
     sl_col, worst_col, agents_col, qvol_col, occ_col, adh_col) = st.columns(
        [1.2, 0.65, 0.65, 0.65, 0.85, 0.85, 0.8, 0.8, 0.8, 0.8]
    )

    # Region label + local clock
    local_dt  = datetime.now(REGION_TZ[region])
    local_date = local_dt.strftime('%d/%m/%Y')
    local_time = local_dt.strftime('%H:%M:%S')
    with label_col:
        st.markdown(
            f"<div style='background:#111827;border:1px solid #1e293b;"
            f"border-left:3px solid {reg_color};border-radius:8px;"
            f"padding:6px 10px;display:flex;justify-content:space-between;"
            f"align-items:center;'>"
            f"<div>"
            f"<div style='font-size:0.58rem;color:#475569;text-transform:uppercase;"
            f"letter-spacing:0.1em;'>Region</div>"
            f"<div style='font-size:1rem;font-weight:900;color:{reg_color};'>"
            f"📍 {region}</div>"
            f"</div>"
            f"<div style='text-align:right;'>"
            f"<div style='font-size:0.65rem;font-weight:700;color:#475569;'>{local_date}</div>"
            f"<div style='font-size:0.75rem;font-weight:800;color:#64748b;font-family:monospace;'>{local_time}</div>"
            f"</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # CRIT / WARN / OK status tiles
    for col, label, count, clr in [
        (crit_col, "SL CRIT", r_crit, "#ef4444"),
        (warn_col, "SL WARN", r_warn, "#f59e0b"),
        (ok_col,   "SL OK",   r_ok,   "#22c55e"),
    ]:
        with col:
            st.markdown(
                f"<div style='text-align:center;background:#111827;"
                f"border:1px solid #1e293b;border-top:2px solid {clr};"
                f"border-radius:8px;padding:5px 4px;'>"
                f"<div style='font-size:0.52rem;font-weight:700;color:{clr};"
                f"text-transform:uppercase;letter-spacing:0.07em;'>{label}</div>"
                f"<div style='font-size:1.05rem;font-weight:800;color:{clr};'>"
                f"{count}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

    # Avg SVC Level — coloured border matching severity
    avg_sl     = reg_lv["service_level_pct"].mean()
    avg_sl_sc  = severity_score("service_level_pct", avg_sl)
    avg_sl_clr = sev_color(avg_sl_sc)
    with sl_col:
        st.markdown(
            f"<div style='text-align:center;background:#111827;"
            f"border:1px solid {avg_sl_clr}55;border-top:2px solid {avg_sl_clr};"
            f"border-radius:8px;padding:5px 4px;'>"
            f"<div style='font-size:0.52rem;color:#475569;text-transform:uppercase;"
            f"letter-spacing:0.05em;line-height:1.3;'>Avg Svc Level</div>"
            f"<div style='font-size:1.05rem;font-weight:800;color:{avg_sl_clr};'>"
            f"{avg_sl:.0f}%</div>"
            f"</div>",
            unsafe_allow_html=True,
        )

    # Worst performing queue by SVC Level — BU · Queue · SL% on one line
    with worst_col:
        st.markdown(
            f"<div style='background:#111827;"
            f"border:1px solid {worst_sl_clr}55;border-top:2px solid {worst_sl_clr};"
            f"border-radius:8px;padding:5px 8px;'>"
            f"<div style='font-size:0.52rem;color:#475569;text-transform:uppercase;"
            f"letter-spacing:0.05em;margin-bottom:3px;'>Worst SL Queue</div>"
            f"<div style='display:flex;align-items:baseline;gap:5px;"
            f"flex-wrap:nowrap;overflow:hidden;'>"
            f"<span style='font-size:0.78rem;font-weight:800;color:{worst_sl_clr};"
            f"white-space:nowrap;'>{worst_row['bu']}</span>"
            f"<span style='font-size:0.62rem;color:#475569;'>·</span>"
            f"<span style='font-size:0.78rem;font-weight:700;color:{worst_sl_clr};"
            f"white-space:nowrap;flex:1;overflow:hidden;text-overflow:ellipsis;'>"
            f"{ACTIVITY_SHORT[worst_row['activity']]}</span>"
            f"<span style='font-size:0.78rem;font-weight:900;color:{worst_sl_clr};"
            f"white-space:nowrap;margin-left:auto;'>{worst_sl:.0f}%</span>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

    # Remaining KPIs
    for col, label, val in [
        (agents_col, "Agents Online", f"{int(reg_lv['agents_logged'].sum())}"),
        (qvol_col,   "Queue Volume",  f"{reg_lv['queue_volume'].sum():.0f}"),
        (occ_col,    "Occupancy",     f"{reg_lv['occupancy_pct'].mean():.0f}%"),
        (adh_col,    "Adherence",     f"{reg_lv['adherence_pct'].mean():.0f}%"),
    ]:
        with col:
            st.markdown(
                f"<div style='text-align:center;background:#111827;"
                f"border:1px solid #1e293b;border-radius:8px;padding:5px 4px;'>"
                f"<div style='font-size:0.52rem;color:#475569;text-transform:uppercase;"
                f"letter-spacing:0.05em;line-height:1.3;'>{label}</div>"
                f"<div style='font-size:1.05rem;font-weight:800;color:#f1f5f9;'>{val}</div>"
                f"</div>",
                unsafe_allow_html=True,
            )

for region in REGIONS:
    _region_summary_row(region)

st.markdown("<hr style='margin:8px 0 6px;border-color:#1e293b;'>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════════════════
# FILTER + MAIN GRID
# ═══════════════════════════════════════════════════════════════════════════════
fcol1, fcol2 = st.columns([1, 9])
with fcol1:
    st.markdown(
        "<div style='font-size:0.6rem;color:#475569;text-transform:uppercase;"
        "letter-spacing:0.1em;padding-top:8px;'>Filter queues</div>",
        unsafe_allow_html=True,
    )
with fcol2:
    sl_filter = st.radio(
        "sl_filter",
        options=["All", "🔴 Critical", "🟡 Warning", "🟢 OK"],
        horizontal=True,
        label_visibility="collapsed",
    )

st.markdown("<div style='height:4px;'></div>", unsafe_allow_html=True)

region_tabs = st.tabs([f"📍 {r}" for r in REGIONS])

for tab, region in zip(region_tabs, REGIONS):
    with tab:
        for bu in BUS:
            bu_color = BU_COLORS[bu]

            st.markdown(
                f"<div class='bu-header' style='color:{bu_color};"
                f"border-color:{bu_color}33;'>{bu}</div>",
                unsafe_allow_html=True,
            )

            row_a = ACTIVITIES[:3]
            row_b = ACTIVITIES[3:]

            for row_acts in (row_a, row_b):
                card_cols = st.columns(3)

                for card_col, activity in zip(card_cols, row_acts):
                    qk        = _qk(bu, region, activity)
                    row_data  = lv[lv["queue_key"] == qk].iloc[0]
                    act_color = ACTIVITY_COLORS[activity]
                    short     = ACTIVITY_SHORT[activity]
                    sl_val    = row_data["service_level_pct"]
                    sl_sc     = severity_score("service_level_pct", sl_val)
                    sl_clr    = sev_color(sl_sc)
                    is_exp    = qk in st.session_state.expanded

                    # Apply severity filter — skip card if it doesn't match
                    if sl_filter == "🔴 Critical" and sl_sc < 1.0:
                        continue
                    if sl_filter == "🟡 Warning"  and sl_sc != 0.5:
                        continue
                    if sl_filter == "🟢 OK"       and sl_sc > 0.0:
                        continue

                    with card_col:
                        hdr1, hdr2, hdr3 = st.columns([2, 1, 0.8])

                        with hdr1:
                            st.markdown(
                                f"<div style='padding-top:4px;'>"
                                f"<span style='display:inline-block;width:8px;height:8px;"
                                f"border-radius:50%;background:{sl_clr};"
                                f"margin-right:5px;vertical-align:middle;'></span>"
                                f"<span style='font-size:0.82rem;font-weight:700;"
                                f"color:{act_color};'>{short}</span>"
                                f"<span style='font-size:0.62rem;color:#475569;"
                                f"margin-left:4px;'>{activity}</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        with hdr2:
                            st.markdown(
                                f"<div style='text-align:center;padding-top:2px;'>"
                                f"<span style='font-size:1.25rem;font-weight:900;"
                                f"color:{sl_clr};'>{sl_val:.0f}%</span>"
                                f"<span style='font-size:0.55rem;color:#334155;"
                                f"display:block;margin-top:-2px;'>SL</span>"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                        with hdr3:
                            toggle_label = "▼" if is_exp else "▶"
                            if st.button(toggle_label, key=f"tog_{qk}",
                                         help="Expand / hide metrics"):
                                if is_exp:
                                    st.session_state.expanded.discard(qk)
                                else:
                                    st.session_state.expanded.add(qk)
                                st.rerun()

                        fig_sl = make_sl_sparkline(qk, act_color, height=80)
                        st.plotly_chart(
                            fig_sl, use_container_width=True,
                            config={"displayModeBar": False},
                            key=f"sl_{qk}",
                        )

                # Expanded panels for this row of 3
                for activity in row_acts:
                    qk        = _qk(bu, region, activity)
                    row_data  = lv[lv["queue_key"] == qk].iloc[0]
                    act_color = ACTIVITY_COLORS[activity]
                    short     = ACTIVITY_SHORT[activity]
                    is_exp    = qk in st.session_state.expanded

                    # Skip expansion panel for filtered-out queues
                    sl_sc_exp = severity_score("service_level_pct",
                                               row_data["service_level_pct"])
                    if sl_filter == "🔴 Critical" and sl_sc_exp < 1.0: continue
                    if sl_filter == "🟡 Warning"  and sl_sc_exp != 0.5: continue
                    if sl_filter == "🟢 OK"       and sl_sc_exp > 0.0:  continue

                    exp_slot = st.empty()
                    if is_exp:
                        with exp_slot.container():
                            all_sc  = max(severity_score(mk, row_data[mk]) for mk in ALL_METRICS)
                            hdr_clr = sev_color(all_sc)

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
                                f"border-radius:6px;padding:7px 12px;margin:2px 0 6px;'>"
                                f"<span style='font-size:0.72rem;font-weight:800;"
                                f"color:{act_color};margin-right:10px;'>"
                                f"{short} · {activity}</span>"
                                f"{sep.join(alert_parts)}"
                                f"</div>",
                                unsafe_allow_html=True,
                            )

                            # 4 metric charts (SL omitted — shown as sparkline) + Agents Online
                            chart_cols = st.columns(5)
                            with chart_cols[0]:
                                fig_ag = make_plain_chart(
                                    qk, "agents_logged", "Agents Online", "",
                                    act_color, height=155,
                                )
                                st.plotly_chart(
                                    fig_ag, use_container_width=True,
                                    config={"displayModeBar": False},
                                    key=f"m_{qk}_agents",
                                )
                            for cc, (mkey, mname, unit, warn, crit, invert) in zip(
                                chart_cols[1:], NON_SL_CFG
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