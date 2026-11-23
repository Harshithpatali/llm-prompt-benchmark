"""Shared visual system for the LLM Quality Intelligence dashboard."""
from __future__ import annotations
import streamlit as st

CSS = """
<style>
:root { color-scheme: dark; }
.block-container { max-width: 1280px; padding: 1.7rem 2rem 4rem; }
[data-testid="stAppViewContainer"] { background: #0b1020; }
[data-testid="stHeader"] { background: rgba(11,16,32,.82); }
[data-testid="stSidebar"] { background: #0e1629; border-right: 1px solid #24314a; }
[data-testid="stSidebar"] > div { padding-top: 1.3rem; }
h1,h2,h3 { letter-spacing: -.035em; }
h1 { font-size: clamp(1.8rem, 4vw, 2.5rem) !important; font-weight: 750 !important; }
h2 { font-size: 1.45rem !important; font-weight: 700 !important; }
h3 { font-size: 1.12rem !important; font-weight: 680 !important; }
p, label, [data-testid="stMarkdownContainer"] { line-height: 1.58; }
[data-testid="stVerticalBlockBorderWrapper"] { background: rgba(20,31,53,.62); border: 1px solid #293852; border-radius: 18px; }
div[data-testid="stMetric"] { background: #121e33; border: 1px solid #2a3a55; border-radius: 15px; padding: 15px 17px; }
div[data-testid="stMetricLabel"] { color: #aab9d0; }
div[data-testid="stMetricValue"] { font-weight: 750; }
.stButton > button, .stDownloadButton > button, [data-testid="stFormSubmitButton"] > button { border-radius: 11px; min-height: 2.8rem; font-weight: 650; border: 1px solid #3b4d6b; }
.stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] { background: #5577e8; border-color: #5577e8; color: white; }
.stTextInput input, .stTextArea textarea, .stSelectbox [data-baseweb="select"], .stNumberInput input { border-radius: 10px; background: #111c30; }
[data-testid="stTabs"] button { font-weight: 650; }
[data-testid="stAlert"] { border-radius: 13px; }
[data-testid="stExpander"] { border: 1px solid #293852; border-radius: 13px; overflow: hidden; }
[data-testid="stDataFrame"] { border: 1px solid #293852; border-radius: 12px; overflow: hidden; }
.small-muted { color: #9aabc4; font-size: .9rem; }
.hero { padding: 1.25rem 1.4rem; border: 1px solid #2b3b58; border-radius: 20px; background: linear-gradient(120deg, #142544, #111a2e 68%, #17213a); margin: .4rem 0 1.3rem; }
.hero-kicker { color: #9eb8ff; font-size: .76rem; font-weight: 750; text-transform: uppercase; letter-spacing: .12em; }
.hero-copy { color: #b7c5dc; margin-top: .35rem; max-width: 850px; }
.eyebrow { color: #9eb8ff; font-size: .76rem; font-weight: 750; letter-spacing: .1em; text-transform: uppercase; }
@media(max-width: 760px) {
 .block-container { padding: .85rem .85rem 2.5rem; }
 h1 { font-size: 1.75rem !important; }
 h2 { font-size: 1.25rem !important; }
 div[data-testid="stMetric"] { padding: 10px; }
}
</style>
"""

def apply_theme():
    st.markdown(CSS, unsafe_allow_html=True)

def page_header(kicker: str, title: str, description: str):
    st.markdown(
        f'<div class="hero"><div class="hero-kicker">{kicker}</div>'
        f'<h1 style="margin:.35rem 0 .2rem">{title}</h1>'
        f'<div class="hero-copy">{description}</div></div>',
        unsafe_allow_html=True,
    )

def section_title(title: str, description: str | None = None):
    st.subheader(title)
    if description:
        st.caption(description)
