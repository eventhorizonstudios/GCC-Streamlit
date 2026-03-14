import time
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from utils import GLOBAL_CSS, POLL_SECS, init_and_tick, render_sidebar_status, render_bu_page

st.set_page_config(page_title="GCC · BU4", page_icon="🏢", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# Non-blocking auto-refresh — fires every POLL_SECS without sleeping
st_autorefresh(interval=POLL_SECS * 1000, key='data_refresh')

init_and_tick()
render_sidebar_status()
render_bu_page("BU4")

