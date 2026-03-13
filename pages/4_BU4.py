import time
import streamlit as st
from utils import GLOBAL_CSS, init_and_tick, render_sidebar_status, render_bu_page

st.set_page_config(page_title="GCC · BU4", page_icon="🏢", layout="wide",
                   initial_sidebar_state="expanded")
st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

init_and_tick()
render_sidebar_status()
render_bu_page("BU4")

time.sleep(1)
st.rerun()
