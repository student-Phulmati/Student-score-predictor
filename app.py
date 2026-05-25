import streamlit as st
import joblib
import pandas as pd
import json
import os
import hashlib
import time
import base64
from datetime import date, datetime, timezone, timedelta
import plotly.graph_objects as go
import io
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.utils import ImageReader

# IST timezone for timestamps
IST = timezone(timedelta(hours=5, minutes=30))

# ── PAGE CONFIG ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="EduPredict – Student Score Predictor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed")

# ── SESSION STATE INIT ─────────────────────────────────────────────────────────
for k, v in {
    "logged_in":        False,
    "user":             None,
    "auth_mode":        "login",
    "prediction_result": None,
    "dark_mode":        True,
    "show_profile":     False,
    "show_history":     False,   # ← NEW: history panel toggle
    "show_help_support": False,  # ← Help & Support panel toggle
    "edit_profile":     False,
    "view":             "dashboard",
    "last_inputs":      {},
    # ── OTP verification state ──
    "otp_sent":         False,   # OTP bheja gaya?
    "otp_code":         None,    # Generated 6-digit OTP
    "otp_email":        "",      # Kis email pe bheja
    "otp_expiry":       None,    # Expiry timestamp
    "otp_pending_data": None,    # Signup data hold karo OTP verify hone tak
    "otp_verified":     False,   # OTP verify ho gaya?
}.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── THEME ──────────────────────────────────────────────────────────────────────
def get_theme():
    if st.session_state.dark_mode:
        return {
            "mode": "dark",
            "bg": "#0f0e17",
            "bg_grad": "linear-gradient(145deg,#0f0e17 0%,#1a0a2e 50%,#0f0e17 100%)",
            "card_bg": "rgba(255,255,255,0.05)",
            "card_border": "rgba(255,255,255,0.10)",
            "text_primary": "#fffffe",
            "text_secondary": "#a7a9be",
            "text_muted": "#72757e",
            "input_bg": "rgba(26,22,46,0.95)",
            "input_border": "rgba(255,100,180,0.25)",
            "input_color": "#fffffe",
            "divider": "rgba(255,255,255,0.08)",
            "header_bg": "rgba(15,14,23,0.96)",
            "header_border": "rgba(255,100,180,0.12)",
            "radial1": "rgba(255,100,180,0.18)",
            "radial2": "rgba(94,96,206,0.20)",
            "radial3": "rgba(255,200,0,0.08)",
            "toggle_icon": "☀️",
            "toggle_label": "Light",
            "shadow": "0 28px 70px rgba(0,0,0,0.6)",
            "result_bar_bg": "rgba(255,255,255,0.08)",
            "section_border": "rgba(255,100,180,0.15)",
            "select_option_bg": "#1a0a2e",
            "select_option_color": "#fffffe",
            "placeholder_color": "#72757e",
            "acc1": "#ff6eb4",
            "acc2": "#ffd60a",
            "acc3": "#5e60ce",
            "acc4": "#06d6a0",
            "grad_main": "linear-gradient(135deg,#ff6eb4,#5e60ce)",
            "grad_alt":  "linear-gradient(135deg,#ffd60a,#ff6eb4)",
            "grad_result": "linear-gradient(135deg,#ff6eb4,#06d6a0)",
            "tip_bg": "rgba(255,255,255,0.04)",
            "tip_border": "rgba(255,255,255,0.10)",}
    else:
        return {
            "mode": "light",
            "bg": "#fff8f0",
            "bg_grad": "linear-gradient(145deg,#fff8f0 0%,#fde8ff 50%,#fff0f8 100%)",
            "card_bg": "rgba(255,255,255,0.88)",
            "card_border": "rgba(255,100,180,0.20)",
            "text_primary": "#1a1a2e",
            "text_secondary": "#3d3d60",
            "text_muted": "#7a7a9a",
            "input_bg": "#ffffff",
            "input_border": "rgba(255,100,180,0.30)",
            "input_color": "#1a1a2e",
            "divider": "rgba(0,0,0,0.07)",
            "header_bg": "rgba(255,255,255,0.92)",
            "header_border": "rgba(255,100,180,0.18)",
            "radial1": "rgba(255,100,180,0.12)",
            "radial2": "rgba(94,96,206,0.10)",
            "radial3": "rgba(255,200,0,0.10)",
            "toggle_icon": "🌙",
            "toggle_label": "Dark",
            "shadow": "0 20px 56px rgba(255,100,180,0.18)",
            "result_bar_bg": "rgba(0,0,0,0.07)",
            "section_border": "rgba(255,100,180,0.18)",
            "select_option_bg": "#ffffff",
            "select_option_color": "#1a1a2e",
            "placeholder_color": "#aaaacc",
            "acc1": "#ff4da6",
            "acc2": "#f5a623",
            "acc3": "#5e60ce",
            "acc4": "#06b88a",
            "grad_main": "linear-gradient(135deg,#ff4da6,#5e60ce)",
            "grad_alt":  "linear-gradient(135deg,#f5a623,#ff4da6)",
            "grad_result": "linear-gradient(135deg,#ff4da6,#06b88a)",
            "tip_bg": "rgba(255,255,255,0.80)",
            "tip_border": "rgba(255,100,180,0.20)",}

T = get_theme()

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700&display=swap');
*, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
#MainMenu, footer, header,
[data-testid="stToolbar"],
[data-testid="stDecoration"],
[data-testid="stStatusWidget"] {{ visibility: hidden !important; height: 0 !important; display: none !important; }}
[data-testid="stSidebar"] {{ display: none !important; }}
.block-container,
[data-testid="stAppViewBlockContainer"],
[data-testid="stVerticalBlockBorderWrapper"],
div[class*="appview-container"],
section[data-testid="stMain"] > div {{
    padding-top: 0 !important;
    margin-top: 0 !important;}}
.block-container {{
    padding-bottom: 0 !important;
    padding-left: 0 !important;
    padding-right: 0 !important;
    max-width: 100% !important;}}
html, body,
[data-testid="stAppViewContainer"],
[data-testid="stApp"] {{
    background: {T['bg_grad']} !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    color: {T['text_primary']} !important;
    min-height: 100vh;}}
body::before {{
    content: '';
    position: fixed; top: -120px; right: -120px;
    width: 420px; height: 420px; border-radius: 50%;
    background: radial-gradient(circle, {T['acc1']}22 0%, transparent 70%);
    pointer-events: none; z-index: 0;}}
body::after {{
    content: '';
    position: fixed; bottom: -100px; left: -100px;
    width: 360px; height: 360px; border-radius: 50%;
    background: radial-gradient(circle, {T['acc3']}22 0%, transparent 70%);
    pointer-events: none; z-index: 0;}}
.brand-badge {{
    display: inline-flex; align-items: center; gap: 6px;
    background: {T['grad_main']};
    color: #fff; -webkit-text-fill-color: #fff;
    font-size: 10px; font-weight: 700;
    letter-spacing: 2.5px; text-transform: uppercase;
    padding: 5px 14px; border-radius: 20px;
    margin-bottom: 22px;
    box-shadow: 0 4px 18px {T['acc1']}44;}}
.brand-title {{
    font-family: 'Syne', sans-serif;
    font-size: 58px; font-weight: 800; line-height: 1.06;
    color: {T['text_primary']}; margin-bottom: 8px;
    letter-spacing: -1px;}}
.brand-title .g1 {{
    background: {T['grad_main']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;}}
.brand-title .g2 {{
    background: {T['grad_alt']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;}}
.brand-sub {{
    font-size: 15px; color: {T['text_secondary']};
    line-height: 1.7; margin-bottom: 32px; font-weight: 300; max-width: 380px;}}
.feat {{
    display: flex; align-items: center; gap: 12px;
    font-size: 13.5px; color: {T['text_secondary']}; margin-bottom: 12px;}}
.feat-dot {{
    width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0;
    background: {T['grad_main']};
    box-shadow: 0 0 8px {T['acc1']}88;}}
.auth-card {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 24px; padding: 38px 34px;
    backdrop-filter: blur(32px);
    box-shadow: {T['shadow']};
    position: relative; overflow: hidden;}}
.auth-card::before {{
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 160px; height: 160px; border-radius: 50%;
    background: {T['acc1']}15;
    pointer-events: none;}}
.auth-title {{
    font-family: 'Syne', sans-serif;
    font-size: 26px; font-weight: 800;
    color: {T['text_primary']}; text-align: center; margin-bottom: 3px;
    letter-spacing: -0.5px;}}
.auth-sub {{
    font-size: 13px; color: {T['text_muted']};
    text-align: center; margin-bottom: 22px;}}
.role-lbl {{
    font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: {T['text_muted']}; margin-bottom: 8px;}}
.hdivider {{
    display: flex; align-items: center; gap: 10px;
    margin: 16px 0; font-size: 11px; color: {T['text_muted']};}}
.hdivider::before,.hdivider::after {{
    content:''; flex:1; height:1px; background:{T['divider']};}}
.sw-txt {{ text-align:center; font-size:13px; color:{T['text_muted']}; margin-top:13px; }}
.sec-title {{
    font-size: 10px; font-weight: 700; letter-spacing: 2.5px;
    text-transform: uppercase;
    background: {T['grad_main']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    margin: 20px 0 10px 0; padding-bottom: 8px;
    border-bottom: 1px solid {T['section_border']};
    display: inline-block; width: 100%;}}
[data-testid="stTextInput"] label,
[data-testid="stSelectbox"] label,
[data-testid="stNumberInput"] label,
[data-testid="stFileUploader"] label,
[data-testid="stDateInput"] label {{
    font-size: 10px !important; font-weight: 700 !important;
    color: {T['text_muted']} !important; letter-spacing: 1px !important;
    text-transform: uppercase !important;
    font-family: 'Plus Jakarta Sans',sans-serif !important;
    margin-bottom: 4px !important;}}
[data-testid="stTextInput"] input,
[data-testid="stNumberInput"] input {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['input_border']} !important;
    border-radius: 10px !important;
    color: {T['input_color']} !important;
    -webkit-text-fill-color: {T['input_color']} !important;
    caret-color: {T['acc1']} !important;
    font-family: 'Plus Jakarta Sans',sans-serif !important;
    font-size: 14px !important;
    padding: 10px 13px !important;
    transition: border-color 0.2s, box-shadow 0.2s !important;}}
[data-testid="stTextInput"] input::placeholder,
[data-testid="stNumberInput"] input::placeholder {{
    color: {T['placeholder_color']} !important;
    -webkit-text-fill-color: {T['placeholder_color']} !important;
    opacity: 1 !important;}}
[data-testid="stTextInput"] input:focus,
[data-testid="stNumberInput"] input:focus {{
    border-color: {T['acc1']} !important;
    box-shadow: 0 0 0 3px {T['acc1']}22 !important;
    outline: none !important;}}
[data-testid="stDateInput"] > div > div > input {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['input_border']} !important;
    border-radius: 10px !important;
    color: {T['input_color']} !important;
    -webkit-text-fill-color: {T['input_color']} !important;
    font-family: 'Plus Jakarta Sans',sans-serif !important;
    font-size: 14px !important;
    padding: 10px 13px !important;}}
[data-testid="stDateInput"] > div > div > input:focus {{
    border-color: {T['acc1']} !important;
    box-shadow: 0 0 0 3px {T['acc1']}22 !important;}}
[data-testid="stSelectbox"] > div > div,
[data-testid="stSelectbox"] > div > div > div {{
    background: {T['input_bg']} !important;
    border: 1.5px solid {T['input_border']} !important;
    border-radius: 10px !important;
    color: {T['input_color']} !important;
    -webkit-text-fill-color: {T['input_color']} !important;}}
[data-testid="stSelectbox"] span,
[data-testid="stSelectbox"] p,
[data-testid="stSelectbox"] div[data-baseweb="select"] span {{
    color: {T['input_color']} !important;
    -webkit-text-fill-color: {T['input_color']} !important;}}
ul[data-testid="stSelectboxVirtualDropdown"],
li[role="option"],
div[data-baseweb="menu"],
div[data-baseweb="popover"] ul,
div[data-baseweb="popover"] li {{
    background: {T['select_option_bg']} !important;
    color: {T['select_option_color']} !important;}}
li[role="option"]:hover,
li[role="option"][aria-selected="true"] {{
    background: {T['acc1']}22 !important;
    color: {T['acc1']} !important;}}
[data-testid="stSelectbox"] svg {{ fill: {T['text_muted']} !important; }}
[data-testid="stRadio"] label,
[data-testid="stRadio"] p {{
    color: {T['text_primary']} !important;
    -webkit-text-fill-color: {T['text_primary']} !important;}}
[data-testid="stRadio"] > div {{ gap: 10px !important; }}
[data-testid="stFileUploader"] section {{
    background: {T['input_bg']} !important;
    border: 1.5px dashed {T['input_border']} !important;
    border-radius: 12px !important;}}
[data-testid="stFileUploader"] section * {{
    color: {T['input_color']} !important;
    -webkit-text-fill-color: {T['input_color']} !important;}}
/* ── Main action buttons ── */
.stButton > button {{
    background: {T['grad_main']} !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans',sans-serif !important;
    font-weight: 700 !important; font-size: 14px !important;
    padding: 12px 22px !important; width: 100% !important;
    transition: all 0.2s !important; letter-spacing: 0.3px !important;
    box-shadow: 0 6px 20px {T['acc1']}44 !important;}}
.stButton > button:hover {{
    opacity: 0.88 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px {T['acc1']}55 !important;}}

/* ── THEME BUTTON: just emoji, circular ── */
.theme-btn .stButton > button {{
    background: {T['card_bg']} !important;
    color: {T['text_primary']} !important;
    -webkit-text-fill-color: {T['text_primary']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 50% !important;
    font-size: 20px !important;
    padding: 0px !important;
    width: 40px !important; height: 40px !important;
    min-width: 40px !important; max-width: 40px !important;
    font-weight: 400 !important; box-shadow: none !important;
    line-height: 1 !important;}}
.theme-btn .stButton > button:hover {{
    border-color: {T['acc2']} !important;
    transform: scale(1.12) !important;
    box-shadow: 0 0 12px {T['acc2']}55 !important;}}

/* ── Home button ── */
.home-btn .stButton > button {{
    background: {T['card_bg']} !important;
    color: {T['text_primary']} !important;
    -webkit-text-fill-color: {T['text_primary']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 12px !important; font-size: 13px !important;
    padding: 8px 16px !important; width: auto !important;
    font-weight: 700 !important; box-shadow: none !important;}}
.home-btn .stButton > button:hover {{
    border-color: {T['acc1']} !important;
    color: {T['acc1']} !important;
    -webkit-text-fill-color: {T['acc1']} !important;
    transform: none !important;}}

/* ── History button ── */
.hist-btn .stButton > button {{
    background: {T['card_bg']} !important;
    color: {T['text_secondary']} !important;
    -webkit-text-fill-color: {T['text_secondary']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 12px !important; font-size: 13px !important;
    padding: 8px 14px !important; width: auto !important;
    font-weight: 600 !important; box-shadow: none !important;}}
.hist-btn .stButton > button:hover {{
    border-color: {T['acc2']} !important;
    color: {T['acc2']} !important;
    -webkit-text-fill-color: {T['acc2']} !important;
    transform: none !important;}}

/* ── Sign out button ── */
.signout-btn .stButton > button {{
    background: transparent !important;
    color: {T['text_muted']} !important;
    -webkit-text-fill-color: {T['text_muted']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 10px !important; font-size: 13px !important;
    padding: 7px 16px !important; width: auto !important;
    font-weight: 600 !important; box-shadow: none !important;}}
.signout-btn .stButton > button:hover {{
    background: rgba(255,80,80,0.08) !important;
    border-color: #ff5555 !important;
    color: #ff5555 !important;
    -webkit-text-fill-color: #ff5555 !important;
    transform: none !important;}}

/* ── Back button ── */
.back-btn .stButton > button {{
    background: {T['card_bg']} !important;
    color: {T['text_primary']} !important;
    -webkit-text-fill-color: {T['text_primary']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 12px !important; font-size: 13px !important;
    padding: 8px 18px !important; width: auto !important;
    font-weight: 700 !important; box-shadow: none !important;}}
.back-btn .stButton > button:hover {{
    border-color: {T['acc1']} !important;
    color: {T['acc1']} !important;
    -webkit-text-fill-color: {T['acc1']} !important;
    transform: none !important;}}

/* ── Predict header button ── */
.predict-hdr-btn .stButton > button {{
    background: {T['grad_main']} !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: none !important;
    border-radius: 22px !important;
    font-size: 13px !important;
    padding: 8px 20px !important;
    width: auto !important;
    font-weight: 700 !important;
    box-shadow: 0 4px 18px {T['acc1']}55 !important;
    letter-spacing: 0.3px !important;}}

/* ── Profile toggle button ── */
.profile-toggle-btn .stButton > button {{
    background: transparent !important;
    border: none !important;
    padding: 0 !important;
    width: auto !important;
    box-shadow: none !important;
    border-radius: 50% !important;
    min-width: 0 !important;}}
.profile-toggle-btn .stButton > button:hover {{
    transform: scale(1.06) !important;
    box-shadow: 0 0 0 3px {T['acc1']}44 !important;}}

/* ── Download button ── */
[data-testid="stDownloadButton"] > button {{
    background: linear-gradient(135deg,#ff6eb4,#5e60ce) !important;
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;
    border: none !important;
    border-radius: 12px !important;
    font-family: 'Plus Jakarta Sans',sans-serif !important;
    font-weight: 700 !important; font-size: 14px !important;
    padding: 12px 22px !important; width: 100% !important;
    transition: all 0.2s !important;
    box-shadow: 0 6px 20px rgba(255,110,180,0.40) !important;}}
[data-testid="stDownloadButton"] > button:hover {{
    opacity: 0.88 !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 10px 28px rgba(255,110,180,0.55) !important;}}
[data-testid="stDownloadButton"] > button p,
[data-testid="stDownloadButton"] > button span {{
    color: #fff !important;
    -webkit-text-fill-color: #fff !important;}}

/* ── Dashboard header ── */
.dash-hdr {{
    background: {T['header_bg']};
    border-bottom: 1px solid {T['header_border']};
    padding: 14px 36px;
    display: flex; align-items: center; justify-content: space-between;
    backdrop-filter: blur(20px);
    position: sticky; top: 0; z-index: 100;}}
.dash-logo {{
    font-family: 'Syne',sans-serif; font-size: 21px; font-weight: 800;
    background: {T['grad_main']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    letter-spacing: -0.5px;}}

/* ── Profile panel ── */
.profile-panel {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 20px;
    padding: 28px 24px;
    backdrop-filter: blur(32px);
    box-shadow: {T['shadow']};
    margin: 0 24px 0 0;
    position: relative; overflow: hidden;}}
.profile-panel::before {{
    content: '';
    position: absolute; top: 0; left: 0; right: 0; height: 80px;
    background: {T['grad_main']};
    opacity: 0.12;
    border-radius: 20px 20px 0 0;}}
.pp-avatar-wrap {{
    text-align: center; margin-bottom: 16px; position: relative; z-index: 1;}}
.pp-name {{
    font-family: 'Syne', sans-serif; font-size: 20px; font-weight: 800;
    color: {T['text_primary']}; text-align: center; margin-bottom: 2px;
    letter-spacing: -0.3px;}}
.pp-role-badge {{
    display: inline-block;
    background: {T['grad_main']};
    color: #fff; -webkit-text-fill-color: #fff;
    font-size: 10px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; padding: 3px 12px; border-radius: 20px;
    margin-bottom: 20px;}}
.pp-row {{
    display: flex; align-items: center; gap: 10px;
    padding: 7px 0; border-bottom: 1px solid {T['divider']};}}
.pp-row:last-child {{ border-bottom: none; }}
.pp-icon {{
    font-size: 13px; flex-shrink: 0;
    width: 26px; height: 26px; border-radius: 7px;
    background: {T['acc1']}18;
    display: flex; align-items: center; justify-content: center;}}
.pp-label {{
    font-size: 9px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: {T['text_muted']}; margin-bottom: 1px;}}
.pp-value {{
    font-size: 12.5px; font-weight: 500; color: {T['text_primary']};
    -webkit-text-fill-color: {T['text_primary']};
    word-break: break-word;}}
.pp-grid {{
    display: grid; grid-template-columns: 1fr 1fr; gap: 0 10px;}}
.pp-grid .pp-row:nth-last-child(-n+2) {{ border-bottom: none; }}

/* ── Result card ── */
.result-card {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 20px; padding: 40px 32px; text-align: center; margin-top: 24px;
    position: relative; overflow: hidden;
    box-shadow: {T['shadow']};}}
.result-card::before {{
    content: '';
    position: absolute; top: -40px; right: -40px;
    width: 200px; height: 200px; border-radius: 50%;
    background: {T['acc1']}0f;}}
.result-lbl {{
    font-size: 10px; font-weight: 700; letter-spacing: 3px;
    text-transform: uppercase; color: {T['acc1']}; margin-bottom: 10px;}}
.result-num {{
    font-family: 'Syne',sans-serif; font-size: 90px; font-weight: 800;
    background: {T['grad_result']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1; margin-bottom: 8px; letter-spacing: -3px;}}
.result-grade {{
    font-size: 15px; color: {T['text_secondary']}; margin-bottom: 22px;}}
.bar-bg {{
    background: {T['result_bar_bg']}; border-radius: 12px; height: 8px;
    overflow: hidden; max-width: 380px; margin: 0 auto;}}
.bar-fill {{
    height: 100%; border-radius: 12px;
    background: {T['grad_result']};
    box-shadow: 0 0 12px {T['acc4']}88;}}

/* ── Stat card ── */
.stat-card {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 18px;
    padding: 20px 16px;
    text-align: center;
    backdrop-filter: blur(20px);}}
.stat-icon {{ font-size: 26px; margin-bottom: 6px; }}
.stat-val {{
    font-family: 'Syne',sans-serif; font-size: 28px; font-weight: 800;
    background: {T['grad_main']};
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
    line-height: 1.1;}}
.stat-lbl {{
    font-size: 11px; font-weight: 600; letter-spacing: 1px;
    text-transform: uppercase; color: {T['text_muted']}; margin-top: 4px;}}
[data-testid="stAlert"] {{ border-radius: 12px !important; font-family:'Plus Jakarta Sans',sans-serif !important; }}
.pic-label {{ text-align:center; font-size:11px; color:{T['text_muted']}; margin-bottom:8px; }}

/* ── Auth wrap ── */
.auth-wrap {{
    padding: 52px 44px 64px;
    background:
        radial-gradient(ellipse 65% 50% at 15% 35%, {T['radial1']} 0%, transparent 55%),
        radial-gradient(ellipse 50% 40% at 85% 70%, {T['radial2']} 0%, transparent 50%),
        radial-gradient(ellipse 40% 30% at 50% 10%, {T['radial3']} 0%, transparent 60%);}}

/* ── Tip cards ── */
.tip-card {{
    background: {T['tip_bg']};
    border: 1px solid {T['tip_border']};
    border-radius: 16px;
    padding: 18px 20px;
    position: relative; overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    height: 100%;}}
.tip-card:hover {{
    transform: translateY(-3px);
    box-shadow: 0 12px 32px rgba(0,0,0,0.3);}}
.tip-card-accent {{
    position: absolute; top: 0; left: 0; width: 100%; height: 3px;
    border-radius: 16px 16px 0 0;}}
.tip-card-icon {{ font-size: 28px; margin-bottom: 10px; display: block;}}
.tip-card-title {{
    font-family: 'Syne', sans-serif;
    font-size: 13px; font-weight: 800;
    color: {T['text_primary']}; margin-bottom: 6px; letter-spacing: -0.2px;}}
.tip-card-body {{
    font-size: 12.5px; color: {T['text_secondary']};
    line-height: 1.6; font-weight: 400;}}
.tip-card-tag {{
    display: inline-block;
    font-size: 9px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase;
    padding: 3px 10px; border-radius: 20px; margin-top: 12px;}}

/* ── Dashboard welcome ── */
.dash-welcome {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 24px; padding: 32px 36px;
    position: relative; overflow: hidden; margin-bottom: 20px;}}
.dash-welcome::before {{
    content: '';
    position: absolute; top: -60px; right: -60px;
    width: 240px; height: 240px; border-radius: 50%;
    background: {T['acc1']}0d; pointer-events: none;}}
.dash-welcome::after {{
    content: '';
    position: absolute; bottom: -40px; left: 40%;
    width: 160px; height: 160px; border-radius: 50%;
    background: {T['acc3']}0a; pointer-events: none;}}
.dash-quote {{
    font-size: 12px; font-style: italic;
    color: {T['text_muted']}; border-left: 2px solid {T['acc1']};
    padding-left: 12px; margin-top: 16px; line-height: 1.6;}}
.dash-steps-wrap {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 20px; padding: 24px 28px; margin-top: 4px;}}
.dash-step {{
    display: flex; align-items: flex-start; gap: 14px;
    padding: 12px 0; border-bottom: 1px solid {T['divider']};}}
.dash-step:last-child {{ border-bottom: none; padding-bottom: 0; }}
.dash-step-num {{
    width: 30px; height: 30px; border-radius: 50%; flex-shrink: 0;
    display: flex; align-items: center; justify-content: center;
    font-size: 12px; font-weight: 800; color: #fff;
    -webkit-text-fill-color: #fff;}}
.dash-step-title {{
    font-size: 13px; font-weight: 700; color: {T['text_primary']};
    -webkit-text-fill-color: {T['text_primary']}; margin-bottom: 2px;}}
.dash-step-sub {{
    font-size: 11.5px; color: {T['text_muted']}; line-height: 1.5;}}

/* ── Quick Action Buttons ── */
.qa-btn-1 .stButton > button,
.qa-btn-2 .stButton > button,
.qa-btn-3 .stButton > button {{
    background: {T['card_bg']} !important;
    border: 1.5px solid {T['card_border']} !important;
    border-radius: 18px !important;
    color: {T['text_primary']} !important;
    -webkit-text-fill-color: {T['text_primary']} !important;
    font-size: 13px !important; font-weight: 600 !important;
    padding: 16px 20px !important; height: auto !important;
    text-align: left !important; white-space: pre-wrap !important;
    box-shadow: {T['shadow']} !important;
    line-height: 1.5 !important; transition: all 0.2s !important;}}
.qa-btn-1 .stButton > button {{ border-top: 3px solid {T['acc1']} !important; }}
.qa-btn-2 .stButton > button {{ border-top: 3px solid {T['acc2']} !important; }}
.qa-btn-3 .stButton > button {{ border-top: 3px solid {T['acc4']} !important; }}
.qa-btn-1 .stButton > button:hover,
.qa-btn-2 .stButton > button:hover,
.qa-btn-3 .stButton > button:hover {{
    transform: translateY(-3px) !important;
    box-shadow: 0 16px 40px rgba(0,0,0,0.25) !important;}}

/* ── History panel ── */
.hist-entry {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 14px;
    padding: 14px 18px;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 14px;}}
.hist-entry:hover {{ border-color: {T['acc1']}55; }}
.hist-score-badge {{
    width: 52px; height: 52px; border-radius: 12px; flex-shrink: 0;
    display: flex; flex-direction: column; align-items: center; justify-content: center;
    font-family: 'Syne', sans-serif; font-weight: 800;}}
.hist-score-num {{ font-size: 20px; line-height: 1; }}
.hist-grade {{ font-size: 9px; letter-spacing: 1px; text-transform: uppercase; margin-top: 2px; }}
.hist-meta {{ flex: 1; min-width: 0; }}
.hist-time {{ font-size: 10px; color: {T['text_muted']}; margin-bottom: 3px; }}
.hist-factors {{ font-size: 11px; color: {T['text_secondary']}; }}

/* ── Admin dashboard ── */
.admin-stat-card {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 18px; padding: 22px 20px;
    text-align: center; position: relative; overflow: hidden;}}
.admin-user-row {{
    background: {T['card_bg']};
    border: 1px solid {T['card_border']};
    border-radius: 14px; padding: 14px 20px;
    margin-bottom: 10px;
    display: flex; align-items: center; gap: 16px;}}
.admin-user-row:hover {{ border-color: {T['acc1']}44; }}
.admin-badge {{
    display: inline-block;
    background: {T['grad_main']};
    color: #fff; -webkit-text-fill-color: #fff;
    font-size: 9px; font-weight: 700; letter-spacing: 2px;
    text-transform: uppercase; padding: 3px 10px; border-radius: 20px;}}
.blocked-banner {{
    background: rgba(255,60,60,0.10);
    border: 1px solid rgba(255,60,60,0.30);
    border-radius: 8px; padding: 4px 10px;
    font-size: 10px; font-weight: 700; color: #ff5555;
    letter-spacing: 1px; text-transform: uppercase; display:inline-block;}}
/* Admin action buttons */
div[data-testid="stButton"] > button.admin-view-btn {{
    background: {T['acc3']}22 !important; color: {T['acc3']} !important;
    border: 1px solid {T['acc3']}55 !important;
    border-radius: 8px !important; font-size: 11px !important;
    padding: 4px 10px !important; font-weight: 700 !important; width:100%;}}
div[data-testid="stButton"] > button.admin-block-btn {{
    background: {T['acc2']}22 !important; color: {T['acc2']} !important;
    border: 1px solid {T['acc2']}55 !important;
    border-radius: 8px !important; font-size: 11px !important;
    padding: 4px 10px !important; font-weight: 700 !important; width:100%;}}
div[data-testid="stButton"] > button.admin-del-btn {{
    background: rgba(255,60,60,0.12) !important; color: #ff5555 !important;
    border: 1px solid rgba(255,60,60,0.35) !important;
    border-radius: 8px !important; font-size: 11px !important;
    padding: 4px 10px !important; font-weight: 700 !important; width:100%;}}
.notif-btn-wrap {{ position: relative; display: inline-block; }}
.notif-dot {{
    position: absolute; top: -4px; right: -4px;
    width: 16px; height: 16px; border-radius: 50%;
    background: #ff5555; color: #fff; -webkit-text-fill-color: #fff;
    font-size: 9px; font-weight: 800;
    display: flex; align-items: center; justify-content: center;
    z-index: 10; pointer-events: none; line-height: 1;}}
.contact-support-card {{
    background: rgba(255,60,60,0.07);
    border: 1px solid rgba(255,60,60,0.25);
    border-radius: 14px; padding: 16px 18px; margin-top: 10px;}}
.help-btn .stButton > button {{
    background: linear-gradient(135deg,{T['acc4']},{T['acc3']});
    color: #fff; -webkit-text-fill-color: #fff;
    border: none; border-radius: 14px; font-weight: 700;
    font-size: 13px; padding: 9px 18px; width: 100%;
    cursor: pointer; transition: opacity 0.2s;}}
.help-btn .stButton > button:hover {{ opacity: 0.88; }}
.msg-card {{
    background: {T['card_bg']}; border: 1px solid {T['card_border']};
    border-radius: 14px; padding: 14px 18px; margin-bottom: 10px;}}
.msg-card.unread {{ border-left: 4px solid {T['acc1']}; }}
.msg-card.read-msg {{ border-left: 4px solid {T['text_muted']}; opacity: 0.75; }}

@media (max-width: 768px) {{
    .brand-title {{ font-size: 38px; }}
    .auth-card {{ padding: 26px 18px; }}
    .auth-wrap {{ padding: 26px 16px 44px; }}}}
</style>
""", unsafe_allow_html=True)

# ── USER DATABASE ──────────────────────────────────────────────────────────────
USERS_FILE = "users.json"

def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

# ── MESSAGES / SUPPORT DATABASE ───────────────────────────────────────────────
MESSAGES_FILE = "support_messages.json"

def load_messages():
    if os.path.exists(MESSAGES_FILE):
        with open(MESSAGES_FILE, "r") as f:
            try:
                return json.load(f)
            except Exception:
                return []
    return []

def save_message(msg_dict):
    msgs = load_messages()
    msgs.insert(0, msg_dict)   # newest first
    with open(MESSAGES_FILE, "w") as f:
        json.dump(msgs, f)

def mark_message_read(idx):
    msgs = load_messages()
    if 0 <= idx < len(msgs):
        msgs[idx]["read"] = True
    with open(MESSAGES_FILE, "w") as f:
        json.dump(msgs, f)

def delete_message(idx):
    """Admin ke liye: specific index pe message delete karo."""
    msgs = load_messages()
    if 0 <= idx < len(msgs):
        msgs.pop(idx)
    with open(MESSAGES_FILE, "w") as f:
        json.dump(msgs, f)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ── OTP EMAIL SYSTEM ───────────────────────────────────────────────────────────
import smtplib
import random
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ⚠️  Apna Gmail aur App Password yahan daalo
SMTP_SENDER_EMAIL    = "your_gmail@gmail.com"      # ← apna Gmail
SMTP_APP_PASSWORD    = "xxxx xxxx xxxx xxxx"        # ← Gmail App Password

def generate_otp():
    """6-digit random OTP generate karo."""
    return str(random.randint(100000, 999999))

def send_otp_email(to_email: str, otp: str, user_name: str = "") -> tuple[bool, str]:
    """
    Gmail SMTP se OTP email bhejo.
    Returns (True, "") on success, (False, error_msg) on failure.
    """
    try:
        subject = "🎓 EduPredict – Your Email Verification OTP"
        greeting = f"Hello {user_name}," if user_name else "Hello,"
        html_body = f"""
        <div style="font-family:'Segoe UI',Arial,sans-serif;max-width:480px;
                    margin:0 auto;background:#0f0e17;border-radius:18px;
                    padding:36px 32px;color:#fffffe;">
          <div style="font-size:22px;font-weight:800;margin-bottom:6px;">
            🎓 EduPredict
          </div>
          <div style="font-size:13px;color:#a7a9be;margin-bottom:28px;">
            Email Verification
          </div>
          <div style="font-size:15px;font-weight:600;margin-bottom:8px;">
            {greeting}
          </div>
          <div style="font-size:13px;color:#a7a9be;margin-bottom:24px;line-height:1.7;">
            Use the OTP below to verify your email address.
            This code is valid for <strong style="color:#ff6eb4;">10 minutes</strong>.
          </div>
          <div style="background:linear-gradient(135deg,#ff6eb4,#5e60ce);
                      border-radius:14px;padding:24px;text-align:center;margin-bottom:24px;">
            <div style="font-size:11px;letter-spacing:3px;text-transform:uppercase;
                        color:rgba(255,255,255,0.75);margin-bottom:8px;">
              Your OTP Code
            </div>
            <div style="font-size:42px;font-weight:900;letter-spacing:10px;
                        color:#ffffff;font-family:monospace;">
              {otp}
            </div>
          </div>
          <div style="font-size:11px;color:#72757e;line-height:1.6;">
            If you did not request this, please ignore this email.
            Do not share this OTP with anyone.
          </div>
        </div>
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"EduPredict <{SMTP_SENDER_EMAIL}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(SMTP_SENDER_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SMTP_SENDER_EMAIL, to_email, msg.as_string())
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, "Gmail authentication failed. Check SMTP_APP_PASSWORD in app_part1.py."
    except Exception as e:
        return False, f"Email send failed: {str(e)}"

def register_user(data_dict):
    users = load_users()
    email = data_dict["email"]
    if email in users:
        return False, "An account with this email already exists."
    data_dict["password"] = hash_pw(data_dict["password"])
    users[email] = data_dict
    save_users(users)
    return True, "Account created!"

# ── PREDEFINED ADMIN CREDENTIALS ──────────────────────────────────────────────
ADMIN_EMAIL    = "admin@edupredict.com"
ADMIN_PASSWORD = "Admin@123"   # change this to whatever you want

def login_user(email, pw, role):
    # ── Admin: check ONLY against hardcoded credentials ──
    if role == "Admin":
        if email.strip().lower() == ADMIN_EMAIL and pw == ADMIN_PASSWORD:
            # Return/create admin user object (no DB lookup needed)
            users = load_users()
            admin_user = users.get(ADMIN_EMAIL, {
                "name": "Admin", "email": ADMIN_EMAIL,
                "password": hash_pw(ADMIN_PASSWORD), "role": "Admin",
                "phone": "", "dob": "", "gender": "",
                "city": "", "profile_pic": "", "prediction_history": [],
            })
            return True, admin_user
        else:
            return False, "❌ Invalid admin credentials. Please try again."

    # ── Student / Parent: normal DB lookup ──
    users = load_users()
    if email not in users:
        return False, "⛔ Your account has been deleted by the admin. Please sign up to create a new account."
    if users[email]["password"] != hash_pw(pw):
        return False, "Incorrect password."
    if users[email].get("blocked", False):
        return False, "🚫 Your account has been blocked by the admin. Please contact support."
    if users[email]["role"] != role:
        return False, f"This account is registered as '{users[email]['role']}', not '{role}'."
    return True, users[email]

def seed_admin():
    """Ensure predefined admin entry exists in users store."""
    try:
        users = load_users()
        if ADMIN_EMAIL not in users:
            users[ADMIN_EMAIL] = {
                "name": "Admin", "email": ADMIN_EMAIL,
                "password": hash_pw(ADMIN_PASSWORD), "role": "Admin",
                "phone": "", "dob": "", "gender": "",
                "city": "", "profile_pic": "", "prediction_history": [],
            }
            save_users(users)
    except Exception:
        pass

# ── MODEL ──────────────────────────────────────────────────────────────────────
@st.cache_resource
def load_model():
    try:
        return joblib.load("student_model.pkl"), joblib.load("model_columns.pkl")
    except Exception:
        return None, None

model, columns = load_model()
seed_admin()   # ← ensure admin exists on every start

# ── DELETED-ACCOUNT VALIDATOR ──────────────────────────────────────────────────
def check_session_still_valid():
    """
    Har rerun pe call hota hai. Agar logged-in user ka account
    users.json mein nahi mila (admin ne delete kar diya), to
    session clear karo aur flag set karo message ke liye.
    Admin role ke liye yeh check skip hota hai (hardcoded credentials).
    """
    if not st.session_state.get("logged_in"):
        return  # already logged out

    user = st.session_state.get("user")
    if user is None:
        return

    # Admin hardcoded hai — uska account kabhi delete nahi hota
    if user.get("role") == "Admin":
        return

    users = load_users()
    email = user.get("email", "")
    if email not in users:
        # Account delete ho gaya — force logout
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state["logged_in"]           = False
        st.session_state["user"]                = None
        st.session_state["auth_mode"]           = "login"
        st.session_state["view"]                = "dashboard"
        st.session_state["dark_mode"]           = True
        st.session_state["show_profile"]        = False
        st.session_state["show_history"]        = False
        st.session_state["edit_profile"]        = False
        st.session_state["prediction_result"]   = None
        st.session_state["last_inputs"]         = {}
        st.session_state["account_deleted_msg"] = True   # ← message flag
        st.rerun()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def get_grade(s):
    if s >= 90:   return "A+", "Outstanding! 🌟"
    elif s >= 80: return "A",  "Excellent! 🎉"
    elif s >= 70: return "B",  "Good work! 👍"
    elif s >= 60: return "C",  "Average – keep pushing 📈"
    else:         return "D",  "Needs improvement 💪"

def theme_btn(key):
    """Render theme toggle as a single emoji circle button (☀️ or 🌙)."""
    st.markdown('<div class="theme-btn">', unsafe_allow_html=True)
    if st.button(T['toggle_icon'], key=key):   # ← only emoji, no label
        st.session_state.dark_mode = not st.session_state.dark_mode
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

def img_to_b64(uploaded_file):
    if uploaded_file is None:
        return ""
    uploaded_file.seek(0)
    return base64.b64encode(uploaded_file.read()).decode("utf-8")

def render_pic_ring(b64, size=80, placeholder="🧑‍🎓"):
    if b64:
        inner = f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;" />'
    else:
        inner = f'<div style="width:100%;height:100%;border-radius:50%;background:{T["input_bg"]};display:flex;align-items:center;justify-content:center;font-size:{size//3}px;">{placeholder}</div>'
    return f"""<div style="width:{size}px;height:{size}px;border-radius:50%;
        background:{T['grad_main']};padding:3px;margin:0 auto 6px;
        box-shadow:0 4px 18px {T['acc1']}55;
        display:flex;align-items:center;justify-content:center;">{inner}</div>"""

def render_hdr_avatar_html(user, initials, size=38):
    pic = user.get("profile_pic", "")
    if pic:
        inner = f'<img src="data:image/jpeg;base64,{pic}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;display:block;" />'
    else:
        inner = f'<div style="width:100%;height:100%;border-radius:50%;background:{T["grad_main"]};display:flex;align-items:center;justify-content:center;font-size:14px;font-weight:800;color:#fff;-webkit-text-fill-color:#fff;">{initials}</div>'
    return f'<div style="width:{size}px;height:{size}px;border-radius:50%;background:{T["grad_main"]};padding:2.5px;box-shadow:0 4px 14px {T["acc1"]}55;cursor:pointer;">{inner}</div>'

# ── DOB HELPERS ───────────────────────────────────────────────────────────────
def dob_str_to_date(dob_str):
    if not dob_str:
        return date(2000, 1, 1)
    try:
        return datetime.strptime(dob_str, "%d/%m/%Y").date()
    except Exception:
        return date(2000, 1, 1)

def date_to_dob_str(d):
    if d is None:
        return ""
    return d.strftime("%d/%m/%Y")

# ── PROFILE PANEL ─────────────────────────────────────────────────────────────
def render_profile_panel(user):
    role    = user.get("role", "")
    pic     = user.get("profile_pic", "")
    editing = st.session_state.edit_profile

    if not editing:
        st.markdown('<div class="profile-panel">', unsafe_allow_html=True)
        st.markdown('<div class="pp-avatar-wrap">', unsafe_allow_html=True)
        st.markdown(render_pic_ring(pic, size=72, placeholder="🧑‍🎓" if role == "Student" else "👨‍👩‍👧"), unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="pp-name" style="font-size:17px;">{user["name"]}</div>', unsafe_allow_html=True)
        role_label = "🎒 Student" if role == "Student" else ("👨‍👩‍👧 Parent" if role == "Parent" else "🔐 Admin")
        st.markdown(f'<div style="text-align:center;margin-bottom:14px;"><span class="pp-role-badge">{role_label}</span></div>', unsafe_allow_html=True)

        def row(icon, label, value, icon_bg=None):
            bg  = icon_bg or f"{T['acc1']}18"
            val = value if value else "—"
            return f"""
            <div class="pp-row">
                <div class="pp-icon" style="background:{bg};">{icon}</div>
                <div>
                    <div class="pp-label">{label}</div>
                    <div class="pp-value">{val}</div>
                </div>
            </div>"""

        left_rows = [
            row("📧", "Email",  user.get("email",""),  f"{T['acc3']}22"),
            row("📱", "Phone",  user.get("phone",""),  f"{T['acc4']}22"),
            row("🎂", "DOB",    user.get("dob",""),    f"{T['acc2']}22"),
        ]
        right_rows = [
            row("⚧",  "Gender", user.get("gender",""), f"{T['acc1']}18"),
            row("🏙", "City",   user.get("city",""),   f"{T['acc3']}22"),
        ]
        if role == "Student":
            right_rows.append(row("🏫", "School",    user.get("school_name",""),   f"{T['acc4']}22"))
            left_rows.append( row("📚", "Class",     user.get("student_class",""), f"{T['acc2']}22"))
            left_rows.append( row("🎂", "Age",       user.get("student_age",""),   f"{T['acc1']}18"))
        elif role == "Parent":
            right_rows.append(row("🤝", "Relation",  user.get("relation",""),      f"{T['acc4']}22"))
        # Admin: no extra fields needed

        max_rows = max(len(left_rows), len(right_rows))
        while len(left_rows)  < max_rows: left_rows.append("")
        while len(right_rows) < max_rows: right_rows.append("")

        grid_html = '<div class="pp-grid">'
        for l, r in zip(left_rows, right_rows):
            grid_html += l + r
        grid_html += '</div>'
        st.markdown(grid_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", key="toggle_edit_profile"):
                st.session_state.edit_profile = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        with btn_c2:
            st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
            if st.button("🚪 Sign Out", key="logout_panel"):
                for key in ["logged_in","user","prediction_result","show_profile",
                             "edit_profile","show_history"]:
                    st.session_state[key] = False if key != "user" and key != "prediction_result" else None
                st.session_state.view = "dashboard"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    else:
        st.markdown(f"""
        <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
             border-top:3px solid {T['acc1']};border-radius:16px;padding:18px 16px 10px;
             margin-bottom:8px;">
          <div style="font-family:'Syne',sans-serif;font-size:15px;font-weight:800;
               color:{T['text_primary']};margin-bottom:2px;">✏️ Edit Profile</div>
          <div style="font-size:11px;color:{T['text_muted']};margin-bottom:12px;">
               Your profile will be updated after saving changes.</div>
        </div>
        """, unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1: new_name  = st.text_input("Full Name",    value=user.get("name",""),  key="ep_name")
        with c2: new_phone = st.text_input("Phone Number", value=user.get("phone",""), key="ep_phone")

        c3, c4 = st.columns(2)
        with c3: new_city = st.text_input("City / Town", value=user.get("city",""), key="ep_city")
        with c4:
            gender_options = ["Prefer not to say","Female","Male","Non-binary / Other"]
            current_gender = user.get("gender","Prefer not to say")
            gender_index   = gender_options.index(current_gender) if current_gender in gender_options else 0
            new_gender = st.selectbox("Gender", gender_options, index=gender_index, key="ep_gender")

        current_dob_date = dob_str_to_date(user.get("dob",""))
        new_dob_date = st.date_input(
            "🎂 Date of Birth", value=current_dob_date,
            min_value=date(1940,1,1), max_value=date.today(), key="ep_dob")
        new_dob = date_to_dob_str(new_dob_date)

        if role == "Student":
            c5, c6 = st.columns(2)
            with c5: new_school = st.text_input("School / College", value=user.get("school_name",""), key="ep_school")
            with c6: new_age    = st.text_input("Age",              value=user.get("student_age",""),  key="ep_age")
            class_options = ["Class 6","Class 7","Class 8","Class 9","Class 10",
                             "Class 11","Class 12","Undergraduate","Postgraduate"]
            current_class = user.get("student_class","Class 10")
            class_index   = class_options.index(current_class) if current_class in class_options else 0
            new_class = st.selectbox("Class", class_options, index=class_index, key="ep_class")
        elif role == "Parent":
            relation_options = ["Father","Mother","Guardian","Elder Sibling","Other"]
            current_relation = user.get("relation","Father")
            relation_index   = relation_options.index(current_relation) if current_relation in relation_options else 0
            new_relation = st.selectbox("Relation with Student", relation_options, index=relation_index, key="ep_relation")
        # Admin: no extra fields

        st.markdown(f'<div style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{T["text_muted"]};margin:10px 0 4px;">🖼️ Profile Picture</div>', unsafe_allow_html=True)
        new_pic = st.file_uploader("New Photo (JPG/PNG)", type=["jpg","jpeg","png"],
                                   key="ep_pic", label_visibility="collapsed")
        if new_pic:
            new_pic.seek(0)
            b64p = base64.b64encode(new_pic.read()).decode()
            new_pic.seek(0)
            st.markdown(render_pic_ring(b64p, size=50), unsafe_allow_html=True)
            st.markdown(f'<div class="pic-label" style="color:{T["acc4"]};">✓ Photo ready</div>', unsafe_allow_html=True)

        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        sv_col, cn_col = st.columns(2)
        with sv_col:
            if st.button("💾 Save Changes", key="save_profile_btn"):
                users = load_users()
                email = user["email"]
                if email in users:
                    users[email]["name"]   = new_name.strip() if new_name.strip() else user["name"]
                    users[email]["phone"]  = new_phone
                    users[email]["city"]   = new_city
                    users[email]["dob"]    = new_dob
                    users[email]["gender"] = new_gender
                    if role == "Student":
                        users[email]["school_name"]   = new_school
                        users[email]["student_age"]   = new_age
                        users[email]["student_class"] = new_class
                    elif role == "Parent":
                        users[email]["relation"] = new_relation
                    # Admin: no role-specific fields to save
                    if new_pic:
                        users[email]["profile_pic"] = img_to_b64(new_pic)
                    save_users(users)
                    st.session_state.user         = users[email]
                    st.session_state.edit_profile = False
                    st.success("✅ Profile updated!")
                    st.rerun()
        with cn_col:
            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
            if st.button("✖ Cancel", key="cancel_edit_profile"):
                st.session_state.edit_profile = False
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════════
#  APP PART 2 — Auth Page · Prediction Form · History Panel
# ══════════════════════════════════════════════════════════════════════════════

# ── AUTH PAGE ─────────────────────────────────────────────────────────────────
def render_auth():
    _, tb = st.columns([9, 1])
    with tb:
        theme_btn("theme_auth")
    st.markdown('<div class="auth-wrap">', unsafe_allow_html=True)
    left_col, right_col = st.columns([1.15, 1], gap="large")
    with left_col:
        st.markdown(f"""
        <div style="padding: 20px 10px 0 10px;">
            <div class="brand-badge">✨ AI-Powered Education</div>
            <div class="brand-title">
                Pre<span class="g1">dict.</span><br/>
                Im<span class="g2">prove.</span><br/>
                Excel.
            </div>
            <div class="brand-sub">
                EduPredict uses machine learning to forecast exam scores
                and reveal the habits that drive academic success.
            </div>
            <div class="feat"><div class="feat-dot"></div> Personalised score predictions</div>
            <div class="feat"><div class="feat-dot"></div> Track study habits &amp; attendance</div>
            <div class="feat"><div class="feat-dot"></div> Parent dashboard access</div>
            <div class="feat"><div class="feat-dot"></div> Instant AI-powered results</div>
        </div>
        """, unsafe_allow_html=True)
    with right_col:
        st.markdown('<div class="auth-card">', unsafe_allow_html=True)
        mode = st.session_state.auth_mode
        if mode == "login":
            st.markdown('<div class="auth-title">Welcome Back 👋</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Sign in to your EduPredict account</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="auth-title">Join EduPredict 🚀</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Create your free account in seconds</div>', unsafe_allow_html=True)

        st.markdown('<div class="role-lbl">I am a</div>', unsafe_allow_html=True)

        # ── Login shows Admin; Signup only Student / Parent ──
        if mode == "login":
            role_options = ["🎒 Student", "👨‍👩‍👧 Parent", "🔐 Admin"]
        else:
            role_options = ["🎒 Student", "👨‍👩‍👧 Parent"]

        role_choice = st.radio(
            "Role", role_options,
            horizontal=True, label_visibility="collapsed", key="role_select")

        if "Student" in role_choice:
            selected_role = "Student"
        elif "Parent" in role_choice:
            selected_role = "Parent"
        else:
            selected_role = "Admin"

        # ── LOGIN ──────────────────────────────────────────────────────────
        if mode == "login":

            # ── Account deleted by admin — inform user ────────────────────
            if st.session_state.get("account_deleted_msg", False):
                st.markdown(f"""
                <div style="
                    background: rgba(255,60,60,0.10);
                    border: 1.5px solid rgba(255,60,60,0.35);
                    border-left: 4px solid #ff4444;
                    border-radius: 14px;
                    padding: 16px 20px;
                    margin-bottom: 18px;">
                    <div style="font-family:'Syne',sans-serif;font-size:14px;
                         font-weight:800;color:#ff4444;margin-bottom:6px;">
                        ⛔ Account Removed
                    </div>
                    <div style="font-size:12px;color:{T['text_secondary']};line-height:1.65;">
                        Aapka account admin dwara delete kar diya gaya hai.<br/>
                        <span style="color:{T['text_muted']};">
                            Agar aapko lagta hai yeh galti se hua hai, to
                            ek naya account banayein ya seedha admin se sampark karein.
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                dismiss_c, _ = st.columns([1, 3])
                with dismiss_c:
                    st.markdown('<div class="back-btn">', unsafe_allow_html=True)
                    if st.button("✖ Dismiss", key="dismiss_deleted_msg"):
                        st.session_state["account_deleted_msg"] = False
                        st.rerun()
                    st.markdown('</div>', unsafe_allow_html=True)

            email    = st.text_input("Email Address", placeholder="you@example.com", key="login_email")
            password = st.text_input("Password", type="password", placeholder="••••••••", key="login_pass")
            if st.button("Sign In →", key="login_btn"):
                if not email or not password:
                    st.error("Please fill in all fields.")
                else:
                    with st.spinner("Verifying..."):
                        time.sleep(0.35)
                        ok, result = login_user(email, password, selected_role)
                    if ok:
                        st.session_state.logged_in    = True
                        st.session_state.user         = result
                        st.session_state.view         = "dashboard"
                        st.session_state["show_contact_support"] = False
                        st.rerun()
                    else:
                        st.error(result)
                        if "blocked" in result.lower():
                            st.session_state["show_contact_support"] = True
                            st.session_state["blocked_user_email"]   = email

            # ── Contact Support form (shown only after blocked error) ──────
            if st.session_state.get("show_contact_support", False):
                blocked_email = st.session_state.get("blocked_user_email", email)
                st.markdown(f"""
                <div class="contact-support-card">
                  <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
                       color:#ff5555;margin-bottom:4px;">🚫 Account Blocked</div>
                  <div style="font-size:12px;color:{T['text_secondary']};margin-bottom:12px;">
                    Your account has been restricted. Send a message to the admin to request access.
                  </div>
                </div>
                """, unsafe_allow_html=True)
                support_msg = st.text_area(
                    "Your message to admin *",
                    placeholder="Explain why you need access to be restored...",
                    key="support_msg_text", height=100)
                if st.button("📨 Send Message to Admin", key="send_support_msg"):
                    if not support_msg.strip():
                        st.error("Please write a message before sending.")
                    else:
                        now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")
                        save_message({
                            "from_email": blocked_email,
                            "from_name":  blocked_email,
                            "message":    support_msg.strip(),
                            "timestamp":  now_ist,
                            "type":       "blocked_appeal",
                            "read":       False,
                        })
                        st.success("✅ Message sent! Admin will review your request.")
                        st.session_state["show_contact_support"] = False

            st.markdown('<div class="hdivider">or</div>', unsafe_allow_html=True)
            st.markdown("<div class='sw-txt'>Don't have an account?</div>", unsafe_allow_html=True)
            if st.button("Create Free Account", key="go_signup"):
                st.session_state.auth_mode = "signup"
                st.rerun()

        # ── SIGNUP ─────────────────────────────────────────────────────────
        else:
            # ── ADMIN SIGNUP: minimal form ──────────────────────────────────
            if selected_role == "Admin":
                st.markdown(f"""
                <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
                     border-left:4px solid {T['acc2']};border-radius:14px;
                     padding:14px 18px;margin-bottom:14px;">
                  <div style="font-size:12px;font-weight:700;color:{T['acc2']};margin-bottom:3px;">
                    🔐 Admin Account
                  </div>
                  <div style="font-size:11px;color:{T['text_muted']};">
                    Admin accounts have full access to the user dashboard and all platform data.
                  </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="sec-title">👤 Admin Details</div>', unsafe_allow_html=True)
                adm_name = st.text_input("Full Name *", placeholder="Admin Name", key="signup_adm_name")

                st.markdown('<div class="sec-title">🔐 Account Credentials</div>', unsafe_allow_html=True)
                adm_email = st.text_input("Email Address *", placeholder="admin@example.com", key="signup_adm_email")
                ap1, ap2  = st.columns(2)
                with ap1: adm_pw  = st.text_input("Password *",         type="password", placeholder="••••••••", key="signup_adm_pass")
                with ap2: adm_pw2 = st.text_input("Confirm Password *", type="password", placeholder="••••••••", key="signup_adm_confirm")

                st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                if st.button("Create Admin Account →", key="signup_btn"):
                    if not adm_name or not adm_email or not adm_pw or not adm_pw2:
                        st.error("Please fill in all required fields (*).")
                    elif len(adm_pw) < 6:
                        st.error("Password must be at least 6 characters.")
                    elif adm_pw != adm_pw2:
                        st.error("Passwords do not match.")
                    elif "@" not in adm_email:
                        st.error("Please enter a valid email address.")
                    else:
                        user_data = {
                            "name": adm_name, "email": adm_email, "password": adm_pw,
                            "role": "Admin", "phone": "", "dob": "", "gender": "",
                            "city": "", "profile_pic": "", "prediction_history": [],
                        }
                        with st.spinner("Creating admin account..."):
                            time.sleep(0.35)
                            ok, msg = register_user(user_data)
                        if ok:
                            st.success("🎉 Admin account created! You can now sign in.")
                            st.session_state.auth_mode = "login"
                            st.rerun()
                        else:
                            st.error(msg)

            # ── STUDENT / PARENT SIGNUP ─────────────────────────────────────
            else:
                # ════════════════════════════════════════════════════════════
                # STEP 2 — OTP Verification screen
                # ════════════════════════════════════════════════════════════
                if st.session_state.get("otp_sent", False):
                    otp_email = st.session_state.get("otp_email", "")
                    expiry    = st.session_state.get("otp_expiry")
                    now_ts    = datetime.now(IST).timestamp()
                    expired   = expiry and now_ts > expiry

                    st.markdown(f"""
                    <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
                         border-top:4px solid {T['acc4']};border-radius:16px;
                         padding:18px 20px;margin-bottom:16px;">
                      <div style="font-family:'Syne',sans-serif;font-size:15px;
                           font-weight:800;color:{T['text_primary']};margin-bottom:4px;">
                        📧 Verify Your Email
                      </div>
                      <div style="font-size:12px;color:{T['text_muted']};line-height:1.6;">
                        A 6-digit OTP has been sent to
                        <strong style="color:{T['acc4']};">{otp_email}</strong>.<br/>
                        Check your inbox (and spam folder). Valid for <strong>10 minutes</strong>.
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    if expired:
                        st.markdown(f"""
                        <div style="background:rgba(255,60,60,0.10);border-left:4px solid #ff4444;
                             border-radius:10px;padding:12px 16px;margin-bottom:12px;">
                          <div style="font-size:12px;color:#ff4444;font-weight:700;">
                            ⏰ OTP expired. Please go back and try again.
                          </div>
                        </div>
                        """, unsafe_allow_html=True)
                        if st.button("← Go Back", key="otp_expired_back"):
                            st.session_state["otp_sent"]         = False
                            st.session_state["otp_code"]         = None
                            st.session_state["otp_pending_data"] = None
                            st.rerun()
                    else:
                        # Remaining time
                        remaining = int(expiry - now_ts) if expiry else 0
                        mins, secs = divmod(remaining, 60)
                        st.markdown(f"""
                        <div style="font-size:11px;color:{T['acc2']};font-weight:700;
                             margin-bottom:10px;">
                          ⏱ OTP expires in: {mins}m {secs}s
                        </div>
                        """, unsafe_allow_html=True)

                        entered_otp = st.text_input(
                            "Enter 6-digit OTP *",
                            placeholder="e.g. 482916",
                            max_chars=6, key="otp_input_field")

                        verify_c, back_c, resend_c = st.columns([1.4, 1, 1.4])

                        with verify_c:
                            st.markdown('<div class="predict-hdr-btn">', unsafe_allow_html=True)
                            if st.button("✅ Verify & Create Account", key="verify_otp_btn"):
                                if not entered_otp.strip():
                                    st.error("Please enter the OTP.")
                                elif entered_otp.strip() != st.session_state.get("otp_code",""):
                                    st.error("❌ Incorrect OTP. Please try again.")
                                else:
                                    # OTP correct — register the user
                                    pending = st.session_state.get("otp_pending_data", {})
                                    with st.spinner("Verifying & creating account..."):
                                        time.sleep(0.3)
                                        ok, msg = register_user(pending)
                                    if ok:
                                        # Clear OTP state
                                        for k in ["otp_sent","otp_code","otp_email",
                                                  "otp_expiry","otp_pending_data","otp_verified"]:
                                            st.session_state[k] = False if k == "otp_sent" else None
                                        st.success("🎉 Account created! You can now sign in.")
                                        st.session_state.auth_mode = "login"
                                        st.rerun()
                                    else:
                                        st.error(msg)
                            st.markdown('</div>', unsafe_allow_html=True)

                        with back_c:
                            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
                            if st.button("← Back", key="otp_back_btn"):
                                st.session_state["otp_sent"]         = False
                                st.session_state["otp_code"]         = None
                                st.session_state["otp_pending_data"] = None
                                st.rerun()
                            st.markdown('</div>', unsafe_allow_html=True)

                        with resend_c:
                            st.markdown('<div class="hist-btn">', unsafe_allow_html=True)
                            if st.button("🔁 Resend OTP", key="resend_otp_btn"):
                                new_otp    = generate_otp()
                                new_expiry = datetime.now(IST).timestamp() + 600
                                pending    = st.session_state.get("otp_pending_data", {})
                                with st.spinner("Sending OTP..."):
                                    ok_mail, err = send_otp_email(
                                        otp_email, new_otp,
                                        pending.get("name",""))
                                if ok_mail:
                                    st.session_state["otp_code"]   = new_otp
                                    st.session_state["otp_expiry"] = new_expiry
                                    st.success("✅ New OTP sent! Check your inbox.")
                                    st.rerun()
                                else:
                                    st.error(f"Failed to resend: {err}")
                            st.markdown('</div>', unsafe_allow_html=True)

                # ════════════════════════════════════════════════════════════
                # STEP 1 — Signup Form
                # ════════════════════════════════════════════════════════════
                else:
                    st.markdown('<div class="sec-title" style="margin-top:4px;">📸 Profile Picture</div>', unsafe_allow_html=True)
                    pic_file = st.file_uploader(
                        "Upload Photo (JPG / PNG)", type=["jpg","jpeg","png"],
                        key="signup_pic", label_visibility="collapsed")
                    if pic_file:
                        pic_file.seek(0)
                        b64p = base64.b64encode(pic_file.read()).decode()
                        pic_file.seek(0)
                        st.markdown(render_pic_ring(b64p, size=78), unsafe_allow_html=True)
                        st.markdown(f'<div class="pic-label" style="color:{T["acc4"]};">✓ Photo uploaded</div>', unsafe_allow_html=True)
                    else:
                        st.markdown(render_pic_ring("", size=78), unsafe_allow_html=True)
                        st.markdown('<div class="pic-label">Tap above to upload</div>', unsafe_allow_html=True)

                    st.markdown('<div class="sec-title">👤 Personal Info</div>', unsafe_allow_html=True)
                    n1, n2 = st.columns(2)
                    with n1: name  = st.text_input("Full Name *",    placeholder="Jane Smith",     key="signup_name")
                    with n2: phone = st.text_input("Phone Number *", placeholder="+91 9876543210", key="signup_phone")
                    d1, d2 = st.columns(2)
                    with d1:
                        gender = st.selectbox("Gender *", ["Prefer not to say","Female","Male","Non-binary / Other"], key="signup_gender")
                    with d2:
                        dob_date = st.date_input(
                            "🎂 Date of Birth *", value=date(2000, 1, 1),
                            min_value=date(1940, 1, 1), max_value=date.today(), key="signup_dob")
                        dob = date_to_dob_str(dob_date)
                    city = st.text_input("City / Town *", placeholder="Mumbai", key="signup_city")

                    if selected_role == "Student":
                        st.markdown('<div class="sec-title">🎒 Student Details</div>', unsafe_allow_html=True)
                        s1, s2, s3 = st.columns(3)
                        with s1:
                            student_class = st.selectbox("Class *", [
                                "Class 6","Class 7","Class 8","Class 9","Class 10",
                                "Class 11","Class 12","Undergraduate","Postgraduate"
                            ], key="signup_class")
                        with s2: student_age = st.text_input("Age *",              placeholder="16",        key="signup_age")
                        with s3: school_name = st.text_input("School / College *", placeholder="DPS Delhi", key="signup_school")
                    else:
                        st.markdown('<div class="sec-title">👨‍👩‍👧 Parent Details</div>', unsafe_allow_html=True)
                        relation = st.selectbox("Relation with Student *",
                            ["Father","Mother","Guardian","Elder Sibling","Other"], key="signup_relation")

                    st.markdown('<div class="sec-title">🔐 Account Credentials</div>', unsafe_allow_html=True)
                    email = st.text_input("Email Address *", placeholder="you@example.com", key="signup_email")
                    p1, p2 = st.columns(2)
                    with p1: pw  = st.text_input("Password *",         type="password", placeholder="••••••••", key="signup_pass")
                    with p2: pw2 = st.text_input("Confirm Password *", type="password", placeholder="••••••••", key="signup_confirm")

                    # OTP badge info
                    st.markdown(f"""
                    <div style="background:rgba(6,214,160,0.08);border:1px solid rgba(6,214,160,0.25);
                         border-radius:10px;padding:10px 14px;margin:10px 0 6px;">
                      <div style="font-size:11px;color:{T['acc4']};font-weight:700;">
                        🔐 Email Verification Required
                      </div>
                      <div style="font-size:11px;color:{T['text_muted']};margin-top:2px;">
                        A 6-digit OTP will be sent to your email to verify your account before creation.
                      </div>
                    </div>
                    """, unsafe_allow_html=True)

                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                    if st.button("Send OTP & Verify Email →", key="signup_btn"):
                        missing = not name or not email or not pw or not pw2 or not phone or not dob or not city
                        if selected_role == "Student":
                            missing = missing or not student_age or not school_name
                        if missing:
                            st.error("Please fill in all required fields (*).")
                        elif len(pw) < 6:
                            st.error("Password must be at least 6 characters.")
                        elif pw != pw2:
                            st.error("Passwords do not match.")
                        elif "@" not in email or "." not in email.split("@")[-1]:
                            st.error("Please enter a valid email address.")
                        else:
                            # Build user_data but DO NOT register yet
                            pic_b64   = img_to_b64(pic_file) if pic_file else ""
                            user_data = {
                                "name": name, "email": email, "password": pw,
                                "role": selected_role, "phone": phone, "dob": dob,
                                "gender": gender, "city": city, "profile_pic": pic_b64,
                                "prediction_history": [],
                            }
                            if selected_role == "Student":
                                user_data.update({
                                    "student_class": student_class,
                                    "student_age":   student_age,
                                    "school_name":   school_name,
                                })
                            else:
                                user_data["relation"] = relation

                            # Generate & send OTP
                            otp = generate_otp()
                            with st.spinner("Sending OTP to your email..."):
                                ok_mail, err = send_otp_email(email, otp, name)
                            if ok_mail:
                                st.session_state["otp_code"]         = otp
                                st.session_state["otp_email"]        = email
                                st.session_state["otp_expiry"]       = datetime.now(IST).timestamp() + 600
                                st.session_state["otp_pending_data"] = user_data
                                st.session_state["otp_sent"]         = True
                                st.rerun()
                            else:
                                st.error(f"❌ Could not send OTP: {err}")

            st.markdown('<div class="hdivider">or</div>', unsafe_allow_html=True)
            st.markdown("<div class='sw-txt'>Already have an account?</div>", unsafe_allow_html=True)
            if st.button("Sign In Instead", key="go_login"):
                st.session_state.auth_mode = "login"
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── PREDICTION FORM ───────────────────────────────────────────────────────────
def render_prediction_form():
    st.markdown(f"""
    <div style="
        margin: 10px 24px 8px;
        background: {T['card_bg']};
        border: 1px solid {T['card_border']};
        border-top: 4px solid {T['acc1']};
        border-radius: 20px;
        padding: 24px 28px 28px;
        backdrop-filter: blur(32px);
        box-shadow: {T['shadow']};">
      <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:800;
                  color:{T['text_primary']};margin-bottom:4px;letter-spacing:-0.3px;">
        🔮 Score Prediction Form
      </div>
      <div style="font-size:12px;color:{T['text_muted']};margin-bottom:2px;">
        Fill all fields below and click Predict.
      </div>
    </div>
    """, unsafe_allow_html=True)

    with st.container():
        st.markdown('<div style="padding: 0 24px 24px;">', unsafe_allow_html=True)

        st.markdown('<div class="sec-title">📊 Academic Inputs</div>', unsafe_allow_html=True)
        c1, c2, c3, c4 = st.columns(4)
        with c1: hours      = st.number_input("⏱ Hours Studied",  min_value=0, max_value=24,  value=0, step=1, key="f_hours")
        with c2: attendance = st.number_input("📅 Attendance (%)", min_value=0, max_value=100, value=0, step=1, key="f_attend")
        with c3: previous   = st.number_input("📝 Previous Score", min_value=0, max_value=100, value=0, step=1, key="f_prev")
        with c4: sleep      = st.number_input("🌙 Sleep Hours",    min_value=0, max_value=12,  value=0, step=1, key="f_sleep")

        st.markdown('<div class="sec-title">🏫 School &amp; Environment</div>', unsafe_allow_html=True)
        c5, c6, c7, c8 = st.columns(4)
        with c5: motivation = st.selectbox("💪 Motivation Level", ["Low","Medium","High"],    key="f_motiv")
        with c6: teacher    = st.selectbox("👩‍🏫 Teacher Quality",  ["Poor","Average","Good"],  key="f_teacher")
        with c7: school_t   = st.selectbox("🏛 School Type",       ["Public","Private"],        key="f_school")
        with c8: internet   = st.selectbox("🌐 Internet Access",   ["Yes","No"],               key="f_net")

        st.markdown('<div class="sec-title">👨‍👩‍👧 Family &amp; Social Factors</div>', unsafe_allow_html=True)
        c9, c10, c11, c12, c13, c14 = st.columns(6)
        with c9:  income     = st.selectbox("💰 Family Income",        ["Low","Medium","High"],           key="f_income")
        with c10: parent_inv = st.selectbox("🤝 Parental Involvement", ["Low","Medium","High"],           key="f_parent")
        with c11: education  = st.selectbox("🎓 Parent Education",     ["School","College"],              key="f_edu")
        with c12: peer       = st.selectbox("👥 Peer Influence",       ["Negative","Neutral","Positive"], key="f_peer")
        with c13: resources  = st.selectbox("📚 Learning Resources",   ["Low","Medium","High"],           key="f_res")
        with c14: activities = st.selectbox("🎭 Extracurricular",      ["Yes","No"],                      key="f_extra")

        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        btn_col, back_col, _ = st.columns([1.2, 1, 3])
        with btn_col:
            predict_clicked = st.button("🔮 Predict My Score", key="form_predict_btn")
        with back_col:
            st.markdown('<div class="back-btn">', unsafe_allow_html=True)
            if st.button("← Back", key="back_from_form"):
                st.session_state.view = "dashboard"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        if predict_clicked:
            if model is None or columns is None:
                st.error("⚠️ Model files not found. Place student_model.pkl and model_columns.pkl in the same folder.")
            else:
                with st.spinner("Running AI prediction..."):
                    time.sleep(0.45)
                    data = {
                        "Hours_Studied":              hours,
                        "Attendance":                 attendance,
                        "Previous_Scores":            previous,
                        "Sleep_Hours":                sleep,
                        "Motivation_Level":           motivation,
                        "Teacher_Quality":            teacher,
                        "School_Type":                school_t,
                        "Internet_Access":            internet,
                        "Family_Income":              income,
                        "Parental_Involvement":       parent_inv,
                        "Parental_Education_Level":   education,
                        "Peer_Influence":             peer,
                        "Learning_Resources":         resources,
                        "Extracurricular_Activities": activities,
                    }
                    last_inp = {
                        "hours": hours, "attendance": attendance, "sleep": sleep,
                        "motivation": motivation, "internet": internet, "peer": peer,
                    }
                    st.session_state.last_inputs = last_inp

                    df   = pd.DataFrame([data])
                    df   = pd.get_dummies(df)
                    df   = df.reindex(columns=columns, fill_value=0)
                    pred = model.predict(df)
                    final_score = int(round(max(40, min(100, pred[0]))))
                    st.session_state.prediction_result = final_score

                    # ── Save prediction to user's history (IST timestamp) ──
                    grade_h, _ = get_grade(final_score)
                    history_entry = {
                        "score":     final_score,
                        "grade":     grade_h,
                        "timestamp": datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST"),
                        "hours":     hours,
                        "attendance": attendance,
                        "sleep":     sleep,
                        "motivation": motivation,
                    }
                    try:
                        all_users = load_users()
                        email_key = st.session_state.user["email"]
                        if "prediction_history" not in all_users[email_key]:
                            all_users[email_key]["prediction_history"] = []
                        all_users[email_key]["prediction_history"].insert(0, history_entry)
                        all_users[email_key]["prediction_history"] = \
                            all_users[email_key]["prediction_history"][:15]   # keep last 15
                        save_users(all_users)
                        st.session_state.user = all_users[email_key]
                    except Exception:
                        pass   # don't block the result even if save fails

                    st.session_state.view = "result"
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ── HISTORY PANEL ─────────────────────────────────────────────────────────────
def render_history_panel():
    """Show past predictions for the current user, newest first."""
    history = st.session_state.user.get("prediction_history", [])

    st.markdown(f"""
    <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
         border-top:4px solid {T['acc2']};border-radius:20px;
         padding:22px 24px 8px;margin-bottom:12px;">
      <div style="font-family:'Syne',sans-serif;font-size:17px;font-weight:800;
           color:{T['text_primary']};margin-bottom:2px;">📜 Prediction History</div>
      <div style="font-size:12px;color:{T['text_muted']};margin-bottom:14px;">
        Your last {len(history)} predictions (newest first)
      </div>
    """, unsafe_allow_html=True)

    if not history:
        st.markdown(f"""
        <div style="text-align:center;padding:32px 0 20px;">
          <div style="font-size:40px;margin-bottom:12px;">🔮</div>
          <div style="font-size:14px;font-weight:600;color:{T['text_secondary']};">
            No predictions yet.
          </div>
          <div style="font-size:12px;color:{T['text_muted']};margin-top:4px;">
            Use the Predict Score button to make your first prediction!
          </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Grade → color mapping
        def grade_color(g):
            return {"A+": T['acc4'], "A": T['acc4'], "B": T['acc3'],
                    "C": T['acc2'], "D": "#ff5555"}.get(g, T['acc1'])

        for i, entry in enumerate(history):
            sc   = entry.get("score", 0)
            gr   = entry.get("grade", "-")
            ts   = entry.get("timestamp", "—")
            hrs  = entry.get("hours", "-")
            att  = entry.get("attendance", "-")
            slp  = entry.get("sleep", "-")
            mot  = entry.get("motivation", "-")
            gc   = grade_color(gr)
            # background opacity alternates slightly
            row_bg = T['card_bg'] if i % 2 == 0 else "rgba(255,255,255,0.03)"
            st.markdown(f"""
            <div class="hist-entry" style="background:{row_bg};">
              <div class="hist-score-badge"
                   style="background:{gc}18;border:1.5px solid {gc}44;">
                <div class="hist-score-num" style="color:{gc};">{sc}</div>
                <div class="hist-grade"     style="color:{gc};">{gr}</div>
              </div>
              <div class="hist-meta">
                <div class="hist-time">🕐 {ts}</div>
                <div class="hist-factors">
                  ⏱ {hrs}h study &nbsp;·&nbsp; 📅 {att}% attend
                  &nbsp;·&nbsp; 🌙 {slp}h sleep &nbsp;·&nbsp; 💪 {mot}
                </div>
              </div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # Close button
    close_c, _ = st.columns([1, 3])
    with close_c:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("✖ Close History", key="close_history_panel"):
            st.session_state.show_history = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
# ══════════════════════════════════════════════════════════════════════════════
#  APP PART 3 — Charts · PDF · Tips · Result · Dashboard · Admin · Router
# ══════════════════════════════════════════════════════════════════════════════

# ── DASHBOARD CHARTS ──────────────────────────────────────────────────────────
def render_charts(score):
    is_dark = T['mode'] == 'dark'
    bg_col  = 'rgba(0,0,0,0)'
    grid_c  = 'rgba(255,255,255,0.07)' if is_dark else 'rgba(0,0,0,0.06)'
    text_c  = '#a9aac8' if is_dark else '#3d3560'
    paper_c = 'rgba(0,0,0,0)'
    base_layout = dict(
        paper_bgcolor=paper_c, plot_bgcolor=bg_col,
        font=dict(color=text_c, family="Plus Jakarta Sans"),
        margin=dict(l=10, r=10, t=10, b=10))

    col1, col2 = st.columns(2)
    with col1:
        st.markdown(f"""
        <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
             border-radius:18px;padding:16px 18px 4px;margin-bottom:16px;">
          <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
               color:{T['text_primary']};">🎯 Score Gauge</div>
          <div style="font-size:11px;color:{T['text_muted']};margin-bottom:4px;">Predicted vs maximum</div>
        """, unsafe_allow_html=True)
        fig_gauge = go.Figure(go.Indicator(
            mode="gauge+number", value=score,
            number={"font": {"size": 36, "color": T['acc1']}, "suffix": "/100"},
            gauge={
                "axis": {"range": [0, 100], "tickcolor": text_c, "tickfont": {"color": text_c}},
                "bar":  {"color": T['acc1'], "thickness": 0.25},
                "bgcolor": "rgba(0,0,0,0)", "borderwidth": 0,
                "steps": [
                    {"range": [0,  60], "color": "rgba(255,80,80,0.15)"},
                    {"range": [60, 75], "color": "rgba(255,200,0,0.15)"},
                    {"range": [75,100], "color": "rgba(0,229,160,0.15)"},],
                "threshold": {"line": {"color": T['acc4'], "width": 3},
                              "thickness": 0.75, "value": score},},))
        fig_gauge.update_layout(**base_layout, height=220)
        st.plotly_chart(fig_gauge, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown(f"""
        <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
             border-radius:18px;padding:16px 18px 4px;margin-bottom:16px;">
          <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
               color:{T['text_primary']};">📊 Grade Benchmark</div>
          <div style="font-size:11px;color:{T['text_muted']};margin-bottom:4px;">Your score vs grade cutoffs</div>
        """, unsafe_allow_html=True)
        grades  = ["D (55)", "C (65)", "B (75)", "A (85)", "A+ (95)", f"You ({score})"]
        values  = [55, 65, 75, 85, 95, score]
        bcolors = ["rgba(255,100,100,0.6)", "rgba(255,200,0,0.6)",
                   "rgba(94,96,206,0.6)",   "rgba(0,229,160,0.6)",
                   "rgba(0,200,255,0.6)",   T['acc1']]
        fig_bar = go.Figure(go.Bar(x=grades, y=values, marker_color=bcolors, marker_line_width=0))
        fig_bar.update_layout(
            **base_layout, height=220,
            xaxis=dict(gridcolor=grid_c, tickfont=dict(color=text_c)),
            yaxis=dict(gridcolor=grid_c, tickfont=dict(color=text_c), range=[0, 110]))
        st.plotly_chart(fig_bar, use_container_width=True, config={"displayModeBar": False})
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown(f"""
    <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
         border-radius:18px;padding:16px 18px 4px;margin-bottom:16px;">
      <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
           color:{T['text_primary']};">📉 Study Hours → Score Trend</div>
      <div style="font-size:11px;color:{T['text_muted']};margin-bottom:4px;">How study time correlates with performance</div>
    """, unsafe_allow_html=True)
    study_hrs    = list(range(1, 11))
    trend_scores = [min(100, int(40 + h * 5.8)) for h in study_hrs]
    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=study_hrs, y=trend_scores, mode="lines+markers",
        line=dict(color=T['acc3'], width=3), marker=dict(color=T['acc3'], size=7),
        fill="tozeroy", fillcolor="rgba(0,200,255,0.10)", name="Expected Score"))
    fig_line.update_layout(
        **base_layout, height=200,
        xaxis=dict(title=dict(text="Study Hours/day", font=dict(color=text_c)),
                   gridcolor=grid_c, tickfont=dict(color=text_c)),
        yaxis=dict(title=dict(text="Score", font=dict(color=text_c)),
                   gridcolor=grid_c, tickfont=dict(color=text_c), range=[30, 110]),
        showlegend=False)
    st.plotly_chart(fig_line, use_container_width=True, config={"displayModeBar": False})
    st.markdown('</div>', unsafe_allow_html=True)

    inp = st.session_state.get("last_inputs", {})
    def level_to_pct(val, options):
        if val not in options: return 50
        return int((options.index(val) / max(len(options)-1, 1)) * 100)

    factors = {
        "Study Hrs":  min(100, int(inp.get("hours", 6) / 10 * 100)),
        "Attendance": int(inp.get("attendance", 85)),
        "Sleep":      min(100, int(inp.get("sleep", 7) / 10 * 100)),
        "Motivation": level_to_pct(inp.get("motivation","Medium"), ["Low","Medium","High"]),
        "Internet":   100 if inp.get("internet","Yes") == "Yes" else 30,
        "Peer Env":   level_to_pct(inp.get("peer","Neutral"), ["Negative","Neutral","Positive"]),}
    st.markdown(f"""
    <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
         border-radius:18px;padding:16px 18px 4px;margin-bottom:16px;">
      <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
           color:{T['text_primary']};">🕸️ Your Success Factors</div>
      <div style="font-size:11px;color:{T['text_muted']};margin-bottom:12px;">Based on your last prediction inputs</div>
    """, unsafe_allow_html=True)
    factor_colors = [T['acc1'], T['acc3'], T['acc4'], T['acc2'], "#e879f9", "#38bdf8"]
    for i, (factor, pct) in enumerate(factors.items()):
        col = factor_colors[i % len(factor_colors)]
        st.markdown(f"""
        <div style="margin-bottom:10px;">
          <div style="display:flex;justify-content:space-between;
               font-size:12px;color:{T['text_secondary']};margin-bottom:4px;">
            <span>{factor}</span><span style="font-weight:700;color:{col};">{pct}%</span>
          </div>
          <div style="background:{T['result_bar_bg']};border-radius:8px;height:7px;overflow:hidden;">
            <div style="width:{pct}%;height:100%;border-radius:8px;background:{col};
                 transition:width 0.6s ease;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)


# ── PDF REPORT CARD ───────────────────────────────────────────────────────────
def generate_report_card_pdf(user, score, grade, feedback, percentile, perf, inp):
    buf = io.BytesIO()
    W, H = A4
    c = rl_canvas.Canvas(buf, pagesize=A4)

    def hx(h):
        h = h.strip("#")
        return tuple(int(h[i:i+2], 16)/255 for i in (0, 2, 4))

    PINK   = hx("b46fff")
    PURPLE = hx("5e60ce")
    TEAL   = hx("00e5a0")
    GOLD   = hx("ffcc00")
    DARK   = hx("07060f")
    DARK2  = hx("120826")
    WHITE  = (1, 1, 1)
    LGREY  = hx("a9aac8")
    MGREY  = hx("6b6d80")

    c.setFillColorRGB(*DARK)
    c.rect(0, 0, W, H, fill=1, stroke=0)
    c.setFillColorRGB(0.37, 0.38, 0.81)
    c.setFillAlpha(0.18)
    c.circle(W + 30, H + 30, 160, fill=1, stroke=0)
    c.setFillColorRGB(*PINK)
    c.setFillAlpha(0.12)
    c.circle(-40, -40, 130, fill=1, stroke=0)
    c.setFillAlpha(1)

    banner_h = 110
    for i in range(banner_h):
        t = i / banner_h
        r = PINK[0] + t * (PURPLE[0] - PINK[0])
        g = PINK[1] + t * (PURPLE[1] - PINK[1])
        b = PINK[2] + t * (PURPLE[2] - PINK[2])
        c.setFillColorRGB(r, g, b)
        c.rect(0, H - banner_h + i, W, 1, fill=1, stroke=0)

    # ── FIXED: use IST timestamp instead of local server time ──
    gen_date = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.92, 0.92, 0.92)
    c.drawString(28, H - 104, gen_date)

    name   = user.get("name", "Student")
    role   = user.get("role", "Student")
    dob    = user.get("dob", "-")
    school = user.get("school_name", user.get("city", "-"))

    cx, cy, cr = W - 44, H - 65, 34
    c.setStrokeColorRGB(*PURPLE)
    c.setLineWidth(5)
    c.setFillColorRGB(*DARK2)
    c.circle(cx, cy, cr, fill=1, stroke=1)
    c.setFillColorRGB(*PINK)
    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(cx, cy + 5, str(score))
    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(1, 1, 1)
    c.drawCentredString(cx, cy - 8, "/ 100")

    pic_b64   = user.get("profile_pic", "")
    photo_cx  = W - 44 - cr - 34 - 36
    photo_cy  = H - 65
    photo_r   = 34

    c.setStrokeColorRGB(*PINK)
    c.setFillColorRGB(*DARK2)
    c.setLineWidth(3)
    c.circle(photo_cx, photo_cy, photo_r, fill=1, stroke=1)

    if pic_b64:
        try:
            import base64 as _b64
            from PIL import Image as _PILImage
            raw     = _b64.b64decode(pic_b64)
            pil_img = _PILImage.open(io.BytesIO(raw)).convert("RGBA")
            pw2, ph = pil_img.size
            side    = min(pw2, ph)
            left    = (pw2 - side) // 2
            top     = (ph - side) // 2
            pil_img = pil_img.crop((left, top, left + side, top + side))
            size_px = int(photo_r * 2 * 2.83)
            pil_img = pil_img.resize((size_px, size_px), _PILImage.LANCZOS)
            mask    = _PILImage.new("L", (size_px, size_px), 0)
            from PIL import ImageDraw as _ImageDraw
            draw_mask = _ImageDraw.Draw(mask)
            draw_mask.ellipse((0, 0, size_px - 1, size_px - 1), fill=255)
            pil_img.putalpha(mask)
            img_buf = io.BytesIO()
            pil_img.save(img_buf, format="PNG")
            img_buf.seek(0)
            ir      = ImageReader(img_buf)
            diam_pt = photo_r * 2
            c.drawImage(ir, photo_cx - photo_r, photo_cy - photo_r,
                        width=diam_pt, height=diam_pt, mask="auto")
        except Exception:
            c.setFillColorRGB(*LGREY)
            c.setFont("Helvetica-Bold", 22)
            c.drawCentredString(photo_cx, photo_cy - 6, "?")
    else:
        initials = "".join([p[0].upper() for p in name.split()[:2]])
        c.setFillColorRGB(*PINK)
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(photo_cx, photo_cy - 6, initials)

    c.setFillColorRGB(*WHITE)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(28, H - 76, name)
    c.setFont("Helvetica", 9.5)
    c.setFillColorRGB(1, 1, 1)
    c.drawString(28, H - 92, f"{role}   |   DOB: {dob}   |   School: {school}")

    y_div = H - 124
    c.setStrokeColorRGB(*PURPLE)
    c.setLineWidth(0.5)
    c.setDash(3, 4)
    c.line(28, y_div, W - 28, y_div)
    c.setDash()

    stats   = [("Predicted Score", str(score), PINK), ("Grade", grade, TEAL),
               ("Performance", perf, GOLD), ("Percentile", percentile, PURPLE)]
    box_y   = y_div - 82
    box_w   = (W - 56 - 18) / 4
    box_h   = 68
    for i, (lbl, val, clr) in enumerate(stats):
        bx = 28 + i * (box_w + 6)
        c.setFillColorRGB(0.12, 0.10, 0.18)
        c.roundRect(bx, box_y, box_w, box_h, 8, fill=1, stroke=0)
        c.setFillColorRGB(*clr)
        c.roundRect(bx, box_y + box_h - 4, box_w, 4, 2, fill=1, stroke=0)
        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(*clr)
        c.drawCentredString(bx + box_w / 2, box_y + 30, val)
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*LGREY)
        c.drawCentredString(bx + box_w / 2, box_y + 14, lbl.upper())

    bar_y = box_y - 36
    c.setFont("Helvetica-Bold", 10)
    c.setFillColorRGB(*WHITE)
    c.drawString(28, bar_y + 14, "Score Progress")
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(*MGREY)
    c.drawRightString(W - 28, bar_y + 14, f"{score}/100")
    c.setFillColorRGB(0.15, 0.13, 0.22)
    c.roundRect(28, bar_y, W - 56, 10, 5, fill=1, stroke=0)
    fill_w = (W - 56) * score / 100
    seg = max(1, int(fill_w))
    for i in range(seg):
        t = i / max(seg - 1, 1)
        r = PINK[0] + t * (TEAL[0] - PINK[0])
        g = PINK[1] + t * (TEAL[1] - PINK[1])
        b = PINK[2] + t * (TEAL[2] - PINK[2])
        c.setFillColorRGB(r, g, b)
        c.rect(28 + i, bar_y, 1, 10, fill=1, stroke=0)

    for pct, lbl in [(60, "D"), (70, "C"), (80, "B"), (90, "A"), (100, "A+")]:
        bx = 28 + (W - 56) * pct / 100
        c.setStrokeColorRGB(*MGREY)
        c.setLineWidth(0.5)
        c.line(bx, bar_y, bx, bar_y + 10)
        c.setFont("Helvetica", 6)
        c.setFillColorRGB(*MGREY)
        c.drawCentredString(bx, bar_y - 8, lbl)

    sf_y = bar_y - 52
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(*PINK)
    c.drawString(28, sf_y, "SUCCESS FACTORS")
    c.setStrokeColorRGB(*PINK)
    c.setLineWidth(1.5)
    c.line(28, sf_y - 3, 180, sf_y - 3)

    def level_to_pct(val, options):
        if val not in options: return 50
        return int((options.index(val) / max(len(options) - 1, 1)) * 100)

    factors = [
        ("Study Hours",  min(100, int(inp.get("hours", 6) / 10 * 100)),    PINK),
        ("Attendance",   int(inp.get("attendance", 85)),                    PURPLE),
        ("Sleep",        min(100, int(inp.get("sleep", 7) / 10 * 100)),    TEAL),
        ("Motivation",   level_to_pct(inp.get("motivation","Medium"), ["Low","Medium","High"]), GOLD),
        ("Internet",     100 if inp.get("internet","Yes") == "Yes" else 30, hx("b46fff")),
        ("Peer Env",     level_to_pct(inp.get("peer","Neutral"), ["Negative","Neutral","Positive"]), hx("00c8ff")),
    ]
    col_w = (W - 56) / 3
    for i, (fname, fpct, fclr) in enumerate(factors):
        col  = i % 3
        row  = i // 3
        fx   = 28 + col * col_w
        fy   = sf_y - 22 - row * 36
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(*LGREY)
        c.drawString(fx, fy, fname)
        c.setFont("Helvetica-Bold", 8)
        c.setFillColorRGB(*fclr)
        c.drawRightString(fx + col_w - 10, fy, f"{fpct}%")
        bar_track_w = col_w - 10
        c.setFillColorRGB(0.15, 0.13, 0.22)
        c.roundRect(fx, fy - 10, bar_track_w, 5, 2, fill=1, stroke=0)
        c.setFillColorRGB(*fclr)
        fill = max(3, bar_track_w * fpct / 100)
        c.roundRect(fx, fy - 10, fill, 5, 2, fill=1, stroke=0)

    tips_raw = []
    if inp.get("hours", 6) < 4:              tips_raw.append("Study at least 4-6 hours daily to improve retention.")
    if inp.get("attendance", 85) < 75:        tips_raw.append("Attendance is low – aim for above 75% to stay on track.")
    if inp.get("sleep", 7) < 6:              tips_raw.append("Sleep deprivation hurts memory. Aim for 7-8 hours nightly.")
    if inp.get("motivation","Medium") == "Low": tips_raw.append("Set small daily goals to build consistent motivation.")
    if inp.get("internet","Yes") == "No":     tips_raw.append("Visit a library for better online learning resources.")
    if inp.get("peer","Neutral") == "Negative": tips_raw.append("Surround yourself with positive, goal-oriented peers.")
    if not tips_raw:                          tips_raw.append("Great habits! Keep it up for excellent results.")

    tip_y = sf_y - 22 - 2 * 36 - 28
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(*TEAL)
    c.drawString(28, tip_y, "PERSONALISED TIPS")
    c.setStrokeColorRGB(*TEAL)
    c.setLineWidth(1.5)
    c.line(28, tip_y - 3, 190, tip_y - 3)

    for j, tip in enumerate(tips_raw[:4]):
        ty = tip_y - 20 - j * 22
        c.setFillColorRGB(*TEAL)
        c.setFillAlpha(0.25)
        c.circle(38, ty + 4, 6, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFillColorRGB(*TEAL)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(38, ty + 1, str(j + 1))
        c.setFont("Helvetica", 8.5)
        c.setFillColorRGB(*LGREY)
        words = tip.split()
        line, lines = [], []
        for w in words:
            test = " ".join(line + [w])
            if c.stringWidth(test, "Helvetica", 8.5) < W - 80:
                line.append(w)
            else:
                lines.append(" ".join(line))
                line = [w]
        if line: lines.append(" ".join(line))
        for k, ln in enumerate(lines[:2]):
            c.drawString(50, ty - k * 11, ln)

    bench_y = tip_y - 20 - len(tips_raw[:4]) * 22 - 36
    c.setFont("Helvetica-Bold", 11)
    c.setFillColorRGB(*GOLD)
    c.drawString(28, bench_y, "GRADE BENCHMARK")
    c.setStrokeColorRGB(*GOLD)
    c.setLineWidth(1.5)
    c.line(28, bench_y - 3, 190, bench_y - 3)

    bench = [("D", 55, hx("ff5050")), ("C", 65, hx("ffc800")),
             ("B", 75, hx("5e60ce")), ("A", 85, hx("00e5a0")),
             ("A+", 95, hx("00c8ff")), ("You", score, PINK)]
    bw = (W - 56) / len(bench)
    for i, (gl, gv, gc2) in enumerate(bench):
        bx = 28 + i * bw + bw / 2
        bar_max_h = 40
        bh = bar_max_h * gv / 110
        c.setFillColorRGB(*gc2)
        c.setFillAlpha(0.85 if gl != "You" else 1.0)
        c.roundRect(bx - bw * 0.35, bench_y - 12 - bh, bw * 0.7, bh, 3, fill=1, stroke=0)
        c.setFillAlpha(1)
        c.setFont("Helvetica-Bold" if gl == "You" else "Helvetica", 8)
        c.setFillColorRGB(*gc2)
        c.drawCentredString(bx, bench_y - 20 - bar_max_h, gl)
        c.setFont("Helvetica", 7)
        c.setFillColorRGB(*MGREY)
        c.drawCentredString(bx, bench_y - 30 - bar_max_h, str(gv))

    footer_y = 28
    c.setFillColorRGB(0.12, 0.10, 0.18)
    c.rect(0, 0, W, footer_y + 16, fill=1, stroke=0)
    c.setFont("Helvetica-Bold", 8)
    c.setFillColorRGB(*PINK)
    c.drawString(28, footer_y, "EduPredict  |  AI-Powered Education Platform")
    c.setFont("Helvetica", 7)
    c.setFillColorRGB(*MGREY)
    c.drawRightString(W - 28, footer_y, "This report is computer-generated. For guidance, consult your educator.")
    c.setStrokeColorRGB(*PINK)
    c.setLineWidth(1.5)
    c.line(0, footer_y + 16, W, footer_y + 16)

    c.save()
    buf.seek(0)
    return buf


# ── TIP CARDS ─────────────────────────────────────────────────────────────────
def render_tip_cards():
    inp = st.session_state.get("last_inputs", {})
    tip_data = []
    if inp.get("hours", 6) < 4:
        tip_data.append({"icon": "📖", "title": "Study More Daily",
            "body": "Aim for at least 4–6 hours of focused study each day. Consistent effort boosts long-term retention significantly.",
            "tag": "Study Habit", "tag_color": T['acc1'], "accent": T['acc1'], "priority": "High Priority"})
    if inp.get("attendance", 85) < 75:
        tip_data.append({"icon": "📅", "title": "Improve Attendance",
            "body": "Your attendance is below 75%. Regular class presence helps you stay current and avoid last-minute exam stress.",
            "tag": "Attendance", "tag_color": T['acc2'], "accent": T['acc2'], "priority": "Important"})
    if inp.get("sleep", 7) < 6:
        tip_data.append({"icon": "🌙", "title": "Fix Your Sleep Schedule",
            "body": "Less than 6 hours of sleep hurts memory consolidation. Target 7–8 hours nightly for peak brain performance.",
            "tag": "Health", "tag_color": T['acc3'], "accent": T['acc3'], "priority": "Critical"})
    if inp.get("motivation","Medium") == "Low":
        tip_data.append({"icon": "💪", "title": "Build Daily Motivation",
            "body": "Set small, achievable daily goals. Celebrate tiny wins — they compound into big results over time.",
            "tag": "Mindset", "tag_color": "#e879f9", "accent": "#e879f9", "priority": "Recommended"})
    if inp.get("internet","Yes") == "No":
        tip_data.append({"icon": "🌐", "title": "Access Learning Resources",
            "body": "Visit your school library or a nearby internet café for access to online notes, videos, and practice papers.",
            "tag": "Resources", "tag_color": "#38bdf8", "accent": "#38bdf8", "priority": "Helpful"})
    if inp.get("peer","Neutral") == "Negative":
        tip_data.append({"icon": "👥", "title": "Choose Better Peers",
            "body": "Surround yourself with goal-oriented, positive friends. A study group with the right people can boost your score by 15%+.",
            "tag": "Social", "tag_color": T['acc4'], "accent": T['acc4'], "priority": "Helpful"})
    if not tip_data:
        tip_data.append({"icon": "🌟", "title": "Keep Up the Great Work!",
            "body": "Your habits are excellent. Maintain consistency, stay curious, and keep pushing for even higher scores.",
            "tag": "All Good", "tag_color": T['acc4'], "accent": T['acc4'], "priority": "Excellent"})

    num = len(tip_data)
    cols_per_row = min(num, 3)
    for row_start in range(0, num, cols_per_row):
        row_tips = tip_data[row_start:row_start + cols_per_row]
        cols = st.columns(len(row_tips))
        for col, tip in zip(cols, row_tips):
            with col:
                st.markdown(f"""
                <div class="tip-card">
                    <div class="tip-card-accent" style="background:{tip['accent']};"></div>
                    <span class="tip-card-icon">{tip['icon']}</span>
                    <div class="tip-card-title">{tip['title']}</div>
                    <div class="tip-card-body">{tip['body']}</div>
                    <span class="tip-card-tag"
                          style="background:{tip['tag_color']}18;color:{tip['tag_color']};
                                 border:1px solid {tip['tag_color']}44;">
                        {tip['tag']} · {tip['priority']}
                    </span>
                </div>
                """, unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)


# ── RESULT PAGE ───────────────────────────────────────────────────────────────
def render_result_page():
    score = st.session_state.prediction_result
    grade, feedback = get_grade(score)
    percentile = "Top 10%" if score >= 90 else "Top 25%" if score >= 80 else "Top 50%" if score >= 70 else "Average"
    perf       = "↑ High" if score >= 75 else "→ Mid" if score >= 50 else "↓ Low"

    st.markdown('<div style="padding:22px 36px 56px;">', unsafe_allow_html=True)
    back_col, title_col, predict_again_col = st.columns([1, 4, 1.5])
    with back_col:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("← Back", key="back_from_result"):
            st.session_state.view = "dashboard"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with title_col:
        st.markdown(f"""
        <div style="font-family:'Syne',sans-serif;font-size:28px;font-weight:800;
                    color:{T['text_primary']};letter-spacing:-0.5px;padding-top:6px;">
            Your Prediction Result 🎓
        </div>
        """, unsafe_allow_html=True)
    with predict_again_col:
        st.markdown('<div class="predict-hdr-btn">', unsafe_allow_html=True)
        if st.button("🔮 Predict Again", key="predict_again_btn"):
            st.session_state.view = "predict_form"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    inp_data = st.session_state.get("last_inputs", {})
    pdf_buf  = generate_report_card_pdf(
        user=st.session_state.user,
        score=score, grade=grade, feedback=feedback,
        percentile=percentile, perf=perf, inp=inp_data)
    pdf_buf.seek(0)
    pdf_bytes    = pdf_buf.read()
    student_name = st.session_state.user.get("name", "Student").replace(" ", "_")
    filename     = f"EduPredict_Report_{student_name}.pdf"

    st.markdown(f"""
    <div style="
        background: {T['card_bg']};
        border: 1px solid {T['card_border']};
        border-left: 4px solid {T['acc1']};
        border-radius: 18px; padding: 20px 28px; margin-bottom: 20px;">
      <div style="font-family:'Syne',sans-serif;font-size:15px;font-weight:800;
           color:{T['text_primary']};margin-bottom:3px;">📄 Your Report Card is Ready!</div>
      <div style="font-size:12px;color:{T['text_muted']};">
        Download your personalised PDF report card below.
      </div>
    </div>
    """, unsafe_allow_html=True)

    dl_col, _ = st.columns([1, 1])
    with dl_col:
        st.download_button(
            label="⬇️ Download PDF Report",
            data=pdf_bytes, file_name=filename,
            mime="application/pdf", key="download_pdf_btn",
            use_container_width=True)

    s1, s2, s3, s4 = st.columns(4)
    for col, icon, val, lbl in [
        (s1, "📊", str(score), "Predicted Score"),
        (s2, "🎯", grade,      "Grade"),
        (s3, "📈", perf,       "Performance"),
        (s4, "⭐", percentile, "Percentile"),]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div class="stat-icon">{icon}</div>
                <div class="stat-val">{val}</div>
                <div class="stat-lbl">{lbl}</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div class="result-card">
        <div class="result-lbl">✨ Predicted Exam Score</div>
        <div class="result-num">{score}</div>
        <div class="result-grade">Grade: <strong>{grade}</strong> — {feedback}</div>
        <div class="bar-bg"><div class="bar-fill" style="width:{score}%"></div></div>
        <div style="font-size:11px;color:{T['text_muted']};margin-top:10px;">out of 100</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div style="height:24px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title">💡 Personalised Suggestions</div>', unsafe_allow_html=True)
    render_tip_cards()

    st.markdown('<div style="height:20px"></div>', unsafe_allow_html=True)
    st.markdown('<div class="sec-title">📈 Analytics Dashboard</div>', unsafe_allow_html=True)
    render_charts(score)
    st.markdown('</div>', unsafe_allow_html=True)


# ── ADMIN DASHBOARD ───────────────────────────────────────────────────────────
def render_admin_dashboard():
    user = st.session_state.user

    # Sticky header
    st.markdown(f"""
    <div class="dash-hdr">
        <div class="dash-logo">🎓 EduPredict <span style="font-size:13px;
             background:{T['grad_alt']};-webkit-background-clip:text;
             -webkit-text-fill-color:transparent;">· Admin</span></div>
        <div style="display:flex;align-items:center;gap:10px;">
            <span class="admin-badge">🔐 Admin Panel</span>
            <div style="font-size:13px;font-weight:700;color:{T['text_primary']};margin-left:6px;">
                {user.get('name','Admin')}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Action bar
    tb_col, so_col, pf_col, notif_col, _ = st.columns([0.5, 1, 1, 1.4, 2])
    with tb_col:
        theme_btn("theme_admin")
    with so_col:
        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
        if st.button("Sign Out", key="admin_logout"):
            st.session_state.logged_in = False
            st.session_state.user      = None
            st.session_state.view      = "dashboard"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with pf_col:
        st.markdown('<div class="profile-toggle-btn">', unsafe_allow_html=True)
        lbl_adm = "✖ Close" if st.session_state.get("admin_show_profile", False) else "👤 My Profile"
        if st.button(lbl_adm, key="admin_toggle_profile"):
            st.session_state["admin_show_profile"] = not st.session_state.get("admin_show_profile", False)
            st.session_state["admin_show_notif"]   = False
            st.session_state.edit_profile          = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with notif_col:
        all_msgs    = load_messages()
        unread_cnt  = sum(1 for m in all_msgs if not m.get("read", False))
        notif_open  = st.session_state.get("admin_show_notif", False)
        notif_label = "✖ Close" if notif_open else ("🔔 Messages" + (f" ({unread_cnt})" if unread_cnt else ""))
        st.markdown('<div class="hist-btn">', unsafe_allow_html=True)
        if st.button(notif_label, key="admin_toggle_notif"):
            st.session_state["admin_show_notif"]   = not notif_open
            st.session_state["admin_show_profile"] = False
            st.session_state.edit_profile          = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Admin profile panel ────────────────────────────────────────────────
    if st.session_state.get("admin_show_profile", False):
        prof_col, info_col = st.columns([1.5, 2.5])
        with prof_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            render_profile_panel(user)
        with info_col:
            st.markdown("<div style='height:14px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="padding:28px 24px;">
                <div style="font-family:'Syne',sans-serif;font-size:22px;font-weight:800;
                            color:{T['text_primary']};margin-bottom:6px;">
                    Hello, {user.get('name','Admin').split()[0]}! 🔐
                </div>
                <div style="font-size:12px;color:{T['text_muted']};margin-bottom:20px;">
                    You are logged in as <strong style="color:{T['acc2']}">Admin</strong>.
                    Edit your profile details on the left.
                </div>
                <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
                    border-left:4px solid {T['acc2']};border-radius:14px;padding:16px 20px;">
                    <div style="font-size:12px;font-weight:700;color:{T['text_primary']};margin-bottom:3px;">
                        🛡️ Admin Privileges
                    </div>
                    <div style="font-size:11px;color:{T['text_muted']};">
                        You have full access to all registered users, their predictions, and platform stats.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        return

    # ── Notifications / Messages panel ────────────────────────────────────
    if st.session_state.get("admin_show_notif", False):
        st.markdown("<div style='padding:20px 36px 40px;'>", unsafe_allow_html=True)
        st.markdown(
            '<div style="font-family:\'Syne\',sans-serif;font-size:20px;font-weight:800;color:'
            + T['text_primary'] + ';margin-bottom:4px;">🔔 Support Messages</div>'
            + '<div style="font-size:12px;color:' + T['text_muted'] + ';margin-bottom:18px;">'
            + 'Messages sent by blocked users requesting account access.</div>',
            unsafe_allow_html=True)

        msgs = load_messages()
        if not msgs:
            st.markdown(
                '<div style="text-align:center;padding:40px 0;">'
                + '<div style="font-size:32px;margin-bottom:10px;">📭</div>'
                + '<div style="font-size:14px;color:' + T['text_muted'] + ';">No messages yet.</div></div>',
                unsafe_allow_html=True)
        else:
            mark_all_col, del_all_col, _ = st.columns([1.5, 1.8, 5])
            with mark_all_col:
                st.markdown('<div class="back-btn">', unsafe_allow_html=True)
                if st.button("✅ Mark All Read", key="mark_all_read"):
                    all_m = load_messages()
                    for m in all_m:
                        m["read"] = True
                    with open(MESSAGES_FILE, "w") as _f:
                        json.dump(all_m, _f)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            with del_all_col:
                st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
                if st.button("🗑️ Delete All Messages", key="delete_all_msgs"):
                    with open(MESSAGES_FILE, "w") as _f:
                        json.dump([], _f)
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            for idx, msg in enumerate(msgs):
                is_unread    = not msg.get("read", False)
                msg_type     = msg.get("type", "blocked_appeal")
                card_class   = "msg-card unread" if is_unread else "msg-card read-msg"
                unread_dot   = ('<span style="display:inline-block;width:8px;height:8px;border-radius:50%;'
                               + 'background:#ff5555;margin-right:6px;vertical-align:middle;"></span>') if is_unread else ""

                # Type badge
                if msg_type == "help_request":
                    type_badge = ('<span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;'
                                 + 'background:rgba(6,214,160,0.15);color:#06d6a0;margin-left:8px;">💬 Help Request</span>')
                else:
                    type_badge = ('<span style="font-size:10px;font-weight:600;padding:2px 8px;border-radius:10px;'
                                 + 'background:rgba(255,60,60,0.15);color:#ff5555;margin-left:8px;">🚫 Blocked Appeal</span>')

                subject_line = msg.get("subject", "")
                subject_html = (
                    '<div style="font-size:11px;font-weight:700;color:' + T['acc4'] + ';margin-bottom:2px;">'
                    + '📌 ' + subject_line + '</div>') if subject_line else ""

                st.markdown(
                    '<div class="' + card_class + '">'
                    + '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:6px;">'
                    + '<div>' + unread_dot
                    + '<span style="font-size:13px;font-weight:700;color:' + T['text_primary'] + ';">'
                    + msg.get("from_name", msg.get("from_email","Unknown")) + '</span>'
                    + '<span style="font-size:11px;color:' + T['text_muted'] + ';margin-left:6px;">('
                    + msg.get("from_email","") + ')</span>'
                    + type_badge
                    + '</div>'
                    + '<div style="font-size:10px;color:' + T['text_muted'] + ';">' + msg.get("timestamp","") + '</div>'
                    + '</div>'
                    + subject_html
                    + '<div style="font-size:12px;color:' + T['text_secondary'] + ';line-height:1.6;'
                    + 'background:' + T['input_bg'] + ';border-radius:10px;padding:10px 14px;margin-top:4px;">'
                    + msg.get("message","") + '</div></div>',
                    unsafe_allow_html=True)

                # Action buttons row
                if is_unread and msg_type == "blocked_appeal":
                    mr_col, unblock_col, del_col, _ = st.columns([1.2, 1.5, 1.2, 3])
                    with mr_col:
                        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
                        if st.button("✓ Mark Read", key=f"read_{idx}"):
                            mark_message_read(idx)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with unblock_col:
                        sender_email = msg.get("from_email","")
                        st.markdown('<div class="predict-hdr-btn">', unsafe_allow_html=True)
                        if st.button("✅ Unblock User", key=f"unblock_from_msg_{idx}"):
                            users_db = load_users()
                            if sender_email in users_db:
                                users_db[sender_email]["blocked"] = False
                                save_users(users_db)
                            mark_message_read(idx)
                            st.success(f"✅ {sender_email} has been unblocked.")
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with del_col:
                        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete", key=f"del_msg_{idx}"):
                            delete_message(idx)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                elif is_unread and msg_type == "help_request":
                    mr_col, del_col, _ = st.columns([1.2, 1.2, 5])
                    with mr_col:
                        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
                        if st.button("✓ Mark Read", key=f"read_{idx}"):
                            mark_message_read(idx)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)
                    with del_col:
                        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete", key=f"del_msg_{idx}"):
                            delete_message(idx)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

                else:
                    # Already read — only delete button
                    del_col, _ = st.columns([1.2, 6])
                    with del_col:
                        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
                        if st.button("🗑️ Delete", key=f"del_msg_{idx}"):
                            delete_message(idx)
                            st.rerun()
                        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)
        return   # don't render user table when notifications panel is open


    st.markdown('<div style="padding:20px 36px 56px;">', unsafe_allow_html=True)

    # Load all users
    all_users = load_users()
    user_list = [v for v in all_users.values() if v.get("role") != "Admin"]
    students  = [u for u in user_list if u.get("role") == "Student"]
    parents   = [u for u in user_list if u.get("role") == "Parent"]
    blocked_count = sum(1 for u in user_list if u.get("blocked", False))
    total_preds = sum(len(u.get("prediction_history", [])) for u in user_list)

    # ── Stats row ──
    st.markdown(f'<div class="sec-title">📊 Platform Overview</div>', unsafe_allow_html=True)
    sc1, sc2, sc3, sc4, sc5 = st.columns(5)
    for col, icon, val, lbl, clr in [
        (sc1, "👥", len(user_list),   "Total Users",  T['acc1']),
        (sc2, "🎒", len(students),    "Students",     T['acc3']),
        (sc3, "👨‍👩‍👧", len(parents),    "Parents",      T['acc2']),
        (sc4, "🔮", total_preds,      "Predictions",  T['acc4']),
        (sc5, "🚫", blocked_count,    "Blocked",      "#ff5555"),
    ]:
        with col:
            st.markdown(
                '<div class="admin-stat-card">'
                + '<div style="font-size:28px;margin-bottom:6px;">' + icon + '</div>'
                + '<div style="font-family:\'Syne\',sans-serif;font-size:28px;font-weight:800;color:'
                + clr + ';line-height:1;">' + str(val) + '</div>'
                + '<div style="font-size:10px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:'
                + T['text_muted'] + ';margin-top:4px;">' + lbl + '</div></div>',
                unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # ── View profile modal (session state driven) ──────────────────────────
    viewing_email = st.session_state.get("admin_view_email", None)
    if viewing_email and viewing_email in all_users:
        vu = all_users[viewing_email]
        vu_role  = vu.get("role","")
        vu_pic   = vu.get("profile_pic","")
        vu_preds = vu.get("prediction_history", [])
        is_blocked_v = vu.get("blocked", False)
        blocked_tag_v = " &nbsp;<span style='font-size:10px;font-weight:700;padding:2px 8px;border-radius:10px;background:rgba(255,60,60,0.15);color:#ff5555;'>🚫 BLOCKED</span>" if is_blocked_v else ""

        st.markdown(
            '<div style="background:' + T['card_bg'] + ';border:2px solid ' + T['acc3'] + '55;'
            + 'border-radius:20px;padding:24px 28px;margin-bottom:20px;">'
            + '<div style="display:flex;align-items:center;gap:10px;margin-bottom:18px;">'
            + '<div style="font-family:\'Syne\',sans-serif;font-size:18px;font-weight:800;color:'
            + T['text_primary'] + ';">👁️ User Profile — ' + vu.get('name','') + '</div>'
            + blocked_tag_v + '</div></div>',
            unsafe_allow_html=True)

        p_col, d_col = st.columns([1, 2])
        with p_col:
            if vu_pic:
                st.markdown(
                    '<div style="text-align:center;margin-bottom:10px;">'
                    + '<img src="data:image/jpeg;base64,' + vu_pic
                    + '" style="width:90px;height:90px;border-radius:50%;object-fit:cover;'
                    + 'border:3px solid ' + T['acc3'] + ';" /></div>',
                    unsafe_allow_html=True)
            else:
                initials_v = "".join([p[0].upper() for p in vu.get("name","?").split()[:2]])
                st.markdown(
                    '<div style="text-align:center;margin-bottom:10px;">'
                    + '<div style="width:90px;height:90px;border-radius:50%;background:'
                    + T['grad_main'] + ';display:flex;align-items:center;justify-content:center;'
                    + 'font-size:28px;font-weight:800;color:#fff;margin:0 auto;">'
                    + initials_v + '</div></div>',
                    unsafe_allow_html=True)
            role_clr_v = T['acc3'] if vu_role == "Student" else T['acc2']
            st.markdown(
                '<div style="text-align:center;">'
                + '<span style="font-size:11px;font-weight:700;padding:3px 12px;border-radius:20px;'
                + 'background:' + role_clr_v + '22;color:' + role_clr_v + ';">'
                + ('🎒 ' if vu_role == "Student" else '👨‍👩‍👧 ') + vu_role + '</span></div>',
                unsafe_allow_html=True)

        with d_col:
            def vrow(icon, label, val):
                return (
                    '<div style="display:flex;gap:10px;align-items:flex-start;'
                    + 'margin-bottom:8px;padding:8px 12px;background:' + T['card_bg']
                    + ';border:1px solid ' + T['card_border'] + ';border-radius:10px;">'
                    + '<span style="font-size:14px;flex-shrink:0;">' + icon + '</span>'
                    + '<div><div style="font-size:9px;font-weight:700;letter-spacing:1px;'
                    + 'text-transform:uppercase;color:' + T['text_muted'] + ';">' + label + '</div>'
                    + '<div style="font-size:12px;font-weight:600;color:' + T['text_primary'] + ';">'
                    + str(val if val else "—") + '</div></div></div>'
                )
            detail_html = (
                vrow("📧", "Email",  vu.get("email",""))
                + vrow("📱", "Phone",  vu.get("phone",""))
                + vrow("🏙", "City",   vu.get("city",""))
                + vrow("🎂", "DOB",    vu.get("dob",""))
                + vrow("⚧",  "Gender", vu.get("gender",""))
            )
            if vu_role == "Student":
                detail_html += vrow("🏫", "School", vu.get("school_name","")) + vrow("📚", "Class", vu.get("student_class",""))
            elif vu_role == "Parent":
                detail_html += vrow("🤝", "Relation", vu.get("relation",""))
            st.markdown(detail_html, unsafe_allow_html=True)

        if vu_preds:
            st.markdown(
                '<div style="font-size:11px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:'
                + T['text_muted'] + ';margin:12px 0 8px;">🔮 Prediction History (' + str(len(vu_preds)) + ')</div>',
                unsafe_allow_html=True)
            for ph in vu_preds[:5]:
                gc = {"A+": T['acc4'], "A": T['acc4'], "B": T['acc3'], "C": T['acc2'], "D": "#ff5555"}.get(ph.get("grade",""), T['acc1'])
                st.markdown(
                    '<div style="display:flex;justify-content:space-between;align-items:center;'
                    + 'padding:8px 14px;background:' + T['card_bg'] + ';border:1px solid ' + T['card_border']
                    + ';border-radius:10px;margin-bottom:6px;">'
                    + '<div style="font-size:11px;color:' + T['text_muted'] + ';">' + str(ph.get("timestamp","")) + '</div>'
                    + '<div style="font-family:\'Syne\',sans-serif;font-size:18px;font-weight:800;color:'
                    + gc + ';">' + str(ph.get("score","")) + ' <span style="font-size:11px;">' + str(ph.get("grade","")) + '</span></div></div>',
                    unsafe_allow_html=True)

        close_c, _ = st.columns([1, 3])
        with close_c:
            if st.button("✖ Close Profile", key="close_view_profile"):
                st.session_state["admin_view_email"] = None
                st.rerun()
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # ── Confirm delete dialog ──────────────────────────────────────────────
    del_email = st.session_state.get("admin_confirm_delete", None)
    if del_email and del_email in all_users:
        del_name = all_users[del_email].get("name", del_email)
        st.markdown(
            '<div style="background:rgba(255,60,60,0.08);border:2px solid rgba(255,60,60,0.35);'
            + 'border-radius:16px;padding:18px 24px;margin-bottom:16px;">'
            + '<div style="font-family:\'Syne\',sans-serif;font-size:15px;font-weight:800;color:#ff5555;margin-bottom:6px;">⚠️ Confirm Delete</div>'
            + '<div style="font-size:12px;color:' + T['text_secondary'] + ';">Are you sure you want to permanently delete '
            + '<strong style="color:' + T['text_primary'] + ';">' + del_name + '</strong>\'s account? This cannot be undone.</div></div>',
            unsafe_allow_html=True)
        yes_c, no_c, _ = st.columns([1, 1, 4])
        with yes_c:
            if st.button("🗑️ Yes, Delete", key="confirm_del_yes"):
                users_db = load_users()
                if del_email in users_db:
                    del users_db[del_email]
                    save_users(users_db)
                st.session_state["admin_confirm_delete"] = None
                st.success(f"✅ Account of {del_name} deleted.")
                st.rerun()
        with no_c:
            if st.button("Cancel", key="confirm_del_no"):
                st.session_state["admin_confirm_delete"] = None
                st.rerun()

    # ── User table ──────────────────────────────────────────────────────────
    st.markdown(f'<div class="sec-title">👤 All Registered Users</div>', unsafe_allow_html=True)

    filter_tab = st.session_state.get("admin_filter", "All")
    ft1, ft2, ft3, ft4, _ = st.columns([0.6, 0.9, 0.9, 0.9, 4])
    for col, lbl in [(ft1,"All"),(ft2,"Students"),(ft3,"Parents"),(ft4,"Blocked")]:
        with col:
            active = filter_tab == lbl
            btn_style = "predict-hdr-btn" if active else "back-btn"
            st.markdown(f'<div class="{btn_style}">', unsafe_allow_html=True)
            if st.button(lbl, key=f"filter_{lbl}"):
                st.session_state["admin_filter"] = lbl
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    search = st.text_input("🔍 Search by name, email or city", placeholder="Type to filter...", key="admin_search")
    search_lower = search.strip().lower()

    all_users = load_users()
    user_list = [v for v in all_users.values() if v.get("role") != "Admin"]
    if filter_tab == "Students":
        user_list = [u for u in user_list if u.get("role") == "Student"]
    elif filter_tab == "Parents":
        user_list = [u for u in user_list if u.get("role") == "Parent"]
    elif filter_tab == "Blocked":
        user_list = [u for u in user_list if u.get("blocked", False)]

    filtered = [u for u in user_list
                if not search_lower
                or search_lower in u.get("name","").lower()
                or search_lower in u.get("email","").lower()
                or search_lower in u.get("city","").lower()]

    if not filtered:
        st.info("No users match your search.")
    else:
        st.markdown(
            '<div style="font-size:11px;color:' + T['text_muted'] + ';margin-bottom:10px;">'
            + 'Showing ' + str(len(filtered)) + ' of ' + str(len(user_list)) + ' users</div>',
            unsafe_allow_html=True)

        for u in filtered:
            u_email  = u.get("email","")
            role_u   = u.get("role","")
            preds_u  = u.get("prediction_history", [])
            last_sc  = preds_u[0]["score"] if preds_u else None
            last_gr  = preds_u[0]["grade"] if preds_u else None
            last_ts  = preds_u[0]["timestamp"] if preds_u else "—"
            school_u = u.get("school_name", u.get("city","—"))
            role_icon = "🎒" if role_u == "Student" else "👨‍👩‍👧"
            role_clr  = T['acc3'] if role_u == "Student" else T['acc2']
            is_blocked = u.get("blocked", False)

            pic = u.get("profile_pic","")
            if pic:
                avatar_html = (
                    '<img src="data:image/jpeg;base64,' + pic
                    + '" style="width:44px;height:44px;border-radius:50%;object-fit:cover;'
                    + 'border:2px solid ' + role_clr + '44;flex-shrink:0;" />')
            else:
                initials = "".join([p[0].upper() for p in u.get("name","?").split()[:2]])
                avatar_html = (
                    '<div style="width:44px;height:44px;border-radius:50%;background:'
                    + T['grad_main'] + ';display:flex;align-items:center;justify-content:center;'
                    + 'font-size:14px;font-weight:800;color:#fff;flex-shrink:0;">' + initials + '</div>')

            info_col, score_col, act_col = st.columns([5, 1, 2])

            with info_col:
                blocked_tag = " &nbsp;<span style='font-size:9px;font-weight:700;padding:2px 7px;border-radius:10px;background:rgba(255,60,60,0.15);color:#ff5555;'>🚫 BLOCKED</span>" if is_blocked else ""
                st.markdown(
                    '<div class="admin-user-row">'
                    + avatar_html
                    + '<div style="flex:1;min-width:0;">'
                    + '<div style="display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:2px;">'
                    + '<span style="font-family:\'Syne\',sans-serif;font-size:14px;font-weight:800;color:'
                    + T['text_primary'] + ';">' + u.get('name','—') + '</span>'
                    + '<span style="font-size:10px;font-weight:700;letter-spacing:1px;text-transform:uppercase;'
                    + 'padding:2px 8px;border-radius:20px;background:' + role_clr + '22;color:' + role_clr + ';">'
                    + role_icon + ' ' + role_u + '</span>' + blocked_tag
                    + '</div>'
                    + '<div style="font-size:11px;color:' + T['text_muted'] + ';">'
                    + '📧 ' + u_email + ' &nbsp;·&nbsp; 🏙 ' + u.get('city','—')
                    + ' &nbsp;·&nbsp; 🏫 ' + school_u + '</div>'
                    + '<div style="font-size:10px;color:' + T['text_muted'] + ';margin-top:2px;">'
                    + '🕐 Last: ' + str(last_ts) + '</div>'
                    + '</div></div>',
                    unsafe_allow_html=True)

            with score_col:
                if last_sc is not None:
                    gc = {"A+": T['acc4'], "A": T['acc4'], "B": T['acc3'], "C": T['acc2'], "D": "#ff5555"}.get(last_gr, T['acc1'])
                    st.markdown(
                        '<div style="text-align:right;padding-top:10px;">'
                        + '<div style="font-family:\'Syne\',sans-serif;font-size:22px;font-weight:800;color:'
                        + gc + ';line-height:1;">' + str(last_sc) + '</div>'
                        + '<div style="font-size:9px;font-weight:700;text-transform:uppercase;color:'
                        + gc + ';">' + str(last_gr) + '</div>'
                        + '<div style="font-size:9px;color:' + T['text_muted'] + ';margin-top:1px;">'
                        + str(len(preds_u)) + ' pred(s)</div></div>',
                        unsafe_allow_html=True)
                else:
                    st.markdown(
                        '<div style="font-size:10px;color:' + T['text_muted'] + ';padding-top:14px;text-align:right;">No preds</div>',
                        unsafe_allow_html=True)

            with act_col:
                st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
                b1, b2, b3 = st.columns(3)
                with b1:
                    if st.button("👁️", key=f"view_{u_email}", help="View Profile"):
                        st.session_state["admin_view_email"] = u_email
                        st.session_state["admin_confirm_delete"] = None
                        st.rerun()
                with b2:
                    block_icon = "✅" if is_blocked else "🚫"
                    block_help = "Unblock User" if is_blocked else "Block User"
                    if st.button(block_icon, key=f"block_{u_email}", help=block_help):
                        users_db = load_users()
                        if u_email in users_db:
                            users_db[u_email]["blocked"] = not is_blocked
                            save_users(users_db)
                        st.rerun()
                with b3:
                    if st.button("🗑️", key=f"del_{u_email}", help="Delete Account"):
                        st.session_state["admin_confirm_delete"] = u_email
                        st.session_state["admin_view_email"] = None
                        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)



# ── HEADER (shared for predict/result views) ──────────────────────────────────
def render_logged_in_header():
    user     = st.session_state.user
    name     = user["name"]
    role     = user["role"]
    initials = "".join([p[0].upper() for p in name.split()[:2]])
    avatar_html = render_hdr_avatar_html(user, initials, size=40)

    st.markdown(f"""
    <div class="dash-hdr">
        <div class="dash-logo">🎓 EduPredict</div>
        <div style="display:flex;align-items:center;gap:14px;">
            <div style="text-align:right;">
                <div style="font-size:13px;font-weight:700;color:{T['text_primary']}">{name}</div>
                <div style="font-size:11px;color:{T['text_muted']}">{role}</div>
            </div>
            {avatar_html}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── HELP & SUPPORT PANEL ──────────────────────────────────────────────────────
def render_help_support_panel():
    user       = st.session_state.user
    user_name  = user.get("name", "")
    user_email = user.get("email", "")

    st.markdown(f"""
    <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
         border-top:4px solid {T['acc4']};border-radius:20px;
         padding:22px 26px 10px;margin-bottom:16px;">
      <div style="font-family:'Syne',sans-serif;font-size:19px;font-weight:800;
           color:{T['text_primary']};margin-bottom:4px;">💬 Help & Support</div>
      <div style="font-size:12px;color:{T['text_muted']};margin-bottom:6px;">
        Have a question or issue? Send a message directly to the admin.
        You will not receive a reply here — admin will review and take action if needed.
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Already sent flag
    if st.session_state.get("help_msg_sent", False):
        st.markdown(f"""
        <div style="background:rgba(6,214,160,0.10);border:1.5px solid rgba(6,214,160,0.35);
             border-left:4px solid {T['acc4']};border-radius:14px;
             padding:16px 20px;margin-bottom:16px;">
          <div style="font-family:'Syne',sans-serif;font-size:14px;font-weight:800;
               color:{T['acc4']};margin-bottom:4px;">✅ Message Sent!</div>
          <div style="font-size:12px;color:{T['text_secondary']};line-height:1.6;">
            Your message has been delivered to the admin. They will review it shortly.
          </div>
        </div>
        """, unsafe_allow_html=True)
        if st.button("📨 Send Another Message", key="help_send_another"):
            st.session_state["help_msg_sent"] = False
            st.rerun()
        return

    subject = st.text_input(
        "Subject",
        placeholder="e.g. Issue with prediction, Account problem...",
        key="help_subject")

    message = st.text_area(
        "Your Message *",
        placeholder="Describe your issue or question in detail...",
        height=130, key="help_msg_text")

    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
    send_c, close_c, _ = st.columns([1.4, 1, 3])
    with send_c:
        st.markdown('<div class="help-btn">', unsafe_allow_html=True)
        if st.button("📨 Send to Admin", key="send_help_msg_btn"):
            if not message.strip():
                st.error("Please write a message before sending.")
            else:
                now_ist = datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")
                save_message({
                    "from_email": user_email,
                    "from_name":  user_name,
                    "subject":    subject.strip() if subject.strip() else "General Enquiry",
                    "message":    message.strip(),
                    "timestamp":  now_ist,
                    "type":       "help_request",
                    "read":       False,
                })
                st.session_state["help_msg_sent"] = True
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with close_c:
        st.markdown('<div class="back-btn">', unsafe_allow_html=True)
        if st.button("✖ Close", key="close_help_panel"):
            st.session_state["show_help_support"] = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# ── MAIN DASHBOARD ────────────────────────────────────────────────────────────
def render_dashboard():
    user     = st.session_state.user
    name     = user["name"]
    role     = user["role"]
    initials = "".join([p[0].upper() for p in name.split()[:2]])
    avatar_html = render_hdr_avatar_html(user, initials, size=40)

    # Sticky header
    st.markdown(f"""
    <div class="dash-hdr">
        <div class="dash-logo">🎓 EduPredict</div>
        <div style="display:flex;align-items:center;gap:14px;">
            <div style="text-align:right;">
                <div style="font-size:13px;font-weight:700;color:{T['text_primary']}">{name}</div>
                <div style="font-size:11px;color:{T['text_muted']}">{role}</div>
            </div>
            {avatar_html}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Action bar: Home | Theme | History | Help | Sign Out | Predict | Profile ──
    home_col, tb_col, hist_col, help_col, so_col, pred_col, pf_col = st.columns([1, 0.6, 1.2, 1.2, 1.2, 1.6, 1.2])

    with home_col:
        st.markdown('<div class="home-btn">', unsafe_allow_html=True)
        if st.button("🏠 Home", key="home_btn"):
            st.session_state.view              = "dashboard"
            st.session_state.show_profile      = False
            st.session_state.show_history      = False
            st.session_state.show_help_support = False
            st.session_state.edit_profile      = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with tb_col:
        theme_btn("theme_dash")

    with hist_col:
        hist_lbl = "✖ History" if st.session_state.show_history else "📜 History"
        st.markdown('<div class="hist-btn">', unsafe_allow_html=True)
        if st.button(hist_lbl, key="toggle_history"):
            st.session_state.show_history      = not st.session_state.show_history
            st.session_state.show_profile      = False
            st.session_state.show_help_support = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with help_col:
        help_lbl = "✖ Help" if st.session_state.get("show_help_support", False) else "💬 Help"
        st.markdown('<div class="help-btn">', unsafe_allow_html=True)
        if st.button(help_lbl, key="toggle_help_support"):
            st.session_state["show_help_support"] = not st.session_state.get("show_help_support", False)
            st.session_state.show_history          = False
            st.session_state.show_profile          = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with so_col:
        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
        if st.button("Sign Out", key="logout_main"):
            for k in ["logged_in","user","prediction_result",
                      "show_profile","edit_profile","show_history","show_help_support"]:
                st.session_state[k] = False if k != "user" and k != "prediction_result" else None
            st.session_state.view = "dashboard"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with pred_col:
        st.markdown('<div class="predict-hdr-btn">', unsafe_allow_html=True)
        if st.button("🔮 Predict Score", key="open_predict_btn"):
            st.session_state.view = "predict_form"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with pf_col:
        st.markdown('<div class="profile-toggle-btn">', unsafe_allow_html=True)
        lbl = "✖ Close" if st.session_state.show_profile else "👤 Profile"
        if st.button(lbl, key="toggle_profile"):
            st.session_state.show_profile      = not st.session_state.show_profile
            st.session_state.show_history      = False
            st.session_state.show_help_support = False
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── History panel ──────────────────────────────────────────────────────
    if st.session_state.show_history:
        st.markdown('<div style="padding:18px 36px 0;">', unsafe_allow_html=True)
        render_history_panel()
        st.markdown('</div>', unsafe_allow_html=True)
        return   # don't render rest of dashboard when history is open

    # ── Help & Support panel ───────────────────────────────────────────────
    if st.session_state.get("show_help_support", False):
        st.markdown('<div style="padding:18px 36px 40px;">', unsafe_allow_html=True)
        render_help_support_panel()
        st.markdown('</div>', unsafe_allow_html=True)
        return   # don't render rest of dashboard when help is open

    # ── Profile panel ──────────────────────────────────────────────────────
    if st.session_state.show_profile:
        col_ratio = [1.6, 2.4] if st.session_state.edit_profile else [1, 3]
        panel_col, close_col = st.columns(col_ratio, gap="small")
        with panel_col:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            render_profile_panel(user)
        with close_col:
            st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
            st.markdown(f"""
            <div style="padding: 32px 28px;">
                <div style="font-family:'Syne',sans-serif;font-size:26px;font-weight:800;
                            color:{T['text_primary']};margin-bottom:8px;">
                    Hello, {name.split()[0]}! 👋
                </div>
                <div style="font-size:13px;color:{T['text_muted']};margin-bottom:28px;">
                    Your profile is open on the left. Click <strong style="color:{T['acc1']}">✖ Close</strong> to go back.
                </div>
                <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
                    border-left:4px solid {T['acc1']};border-radius:16px;padding:20px 24px;margin-bottom:14px;">
                    <div style="font-size:13px;font-weight:700;color:{T['text_primary']};margin-bottom:4px;">
                        🔮 Ready to predict your score?
                    </div>
                    <div style="font-size:12px;color:{T['text_muted']};">
                        Use the <strong style="color:{T['acc1']}">Predict Score</strong> button in the top bar.
                    </div>
                </div>
                <div style="background:{T['card_bg']};border:1px solid {T['card_border']};
                    border-left:4px solid {T['acc4']};border-radius:16px;padding:20px 24px;">
                    <div style="font-size:13px;font-weight:700;color:{T['text_primary']};margin-bottom:4px;">
                        ✏️ Update your profile?
                    </div>
                    <div style="font-size:12px;color:{T['text_muted']};">
                        Use the <strong style="color:{T['acc4']}">Edit Profile</strong> button below your profile info.
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        return

    # ── Main dashboard content ──────────────────────────────────────────────
    st.markdown('<div style="padding:22px 36px 56px;">', unsafe_allow_html=True)

    first_name = name.split()[0]
    hour       = datetime.now(IST).hour
    greeting   = "Good Morning" if hour < 12 else "Good Afternoon" if hour < 17 else "Good Evening"
    quotes = [
        "Success is the sum of small efforts, repeated day in and day out.",
        "The secret of getting ahead is getting started.",
        "Education is the most powerful weapon you can use to change the world.",
        "Push yourself, because no one else is going to do it for you.",
    ]
    import hashlib as _h
    quote = quotes[int(_h.md5(name.encode()).hexdigest(), 16) % len(quotes)]

    st.markdown(f"""
    <div class="dash-welcome">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;flex-wrap:wrap;gap:16px;">
            <div style="flex:1;min-width:260px;">
                <div style="font-size:11px;font-weight:700;letter-spacing:2px;text-transform:uppercase;
                            color:{T['acc1']};margin-bottom:8px;">{greeting} ✨</div>
                <div style="font-family:'Syne',sans-serif;font-size:30px;font-weight:800;
                            color:{T['text_primary']};letter-spacing:-0.5px;line-height:1.2;margin-bottom:6px;">
                    Welcome back,<br/><span style="background:{T['grad_main']};-webkit-background-clip:text;-webkit-text-fill-color:transparent;">{first_name}!</span>
                </div>
                <div style="font-size:13px;color:{T['text_muted']};margin-bottom:6px;">
                    {"🎒 Student" if role == "Student" else "👨‍👩‍👧 Parent"} &nbsp;·&nbsp; EduPredict Dashboard
                </div>
                <div class="dash-quote">"{quote}"</div>
            </div>
            <div style="flex-shrink:0;"><div style="font-size:72px;line-height:1;">🎓</div></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Quick Actions
    st.markdown(f'<div class="sec-title">⚡ Quick Actions</div>', unsafe_allow_html=True)
    qa1, qa2, qa3 = st.columns(3)

    with qa1:
        st.markdown('<div class="qa-btn-1">', unsafe_allow_html=True)
        if st.button("🔮  Predict Score\n\nGet your AI-powered exam score prediction in seconds.", key="qa_predict"):
            st.session_state.view = "predict_form"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with qa2:
        prev_score = st.session_state.get("prediction_result")
        label = "📊  View Analytics\n\nSee your charts & performance graphs." if prev_score \
                else "📊  View Analytics\n\nCharts appear after your first prediction."
        st.markdown('<div class="qa-btn-2">', unsafe_allow_html=True)
        if st.button(label, key="qa_analytics"):
            st.session_state.view = "result" if prev_score else "predict_form"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with qa3:
        st.markdown('<div class="qa-btn-3">', unsafe_allow_html=True)
        if st.button("📄  Download Report\n\nGet a beautiful PDF report card after prediction.", key="qa_report"):
            st.session_state.view = "result" if st.session_state.get("prediction_result") else "predict_form"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # How It Works
    st.markdown(f'<div class="sec-title" style="margin-top:8px;">🗺️ How It Works</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="dash-steps-wrap">
        <div class="dash-step">
            <div class="dash-step-num" style="background:{T['grad_main']};">1</div>
            <div>
                <div class="dash-step-title">Fill the Prediction Form</div>
                <div class="dash-step-sub">Enter your study hours, attendance, sleep, motivation, and other factors.</div>
            </div>
        </div>
        <div class="dash-step">
            <div class="dash-step-num" style="background:{T['grad_alt']};">2</div>
            <div>
                <div class="dash-step-title">Get Your AI Score</div>
                <div class="dash-step-sub">Our machine learning model predicts your exam score in real time.</div>
            </div>
        </div>
        <div class="dash-step">
            <div class="dash-step-num" style="background:linear-gradient(135deg,{T['acc4']},{T['acc3']});">3</div>
            <div>
                <div class="dash-step-title">Read Your Personalised Tips</div>
                <div class="dash-step-sub">Get smart suggestions tailored to your specific habits and areas to improve.</div>
            </div>
        </div>
        <div class="dash-step">
            <div class="dash-step-num" style="background:linear-gradient(135deg,{T['acc2']},{T['acc1']});">4</div>
            <div>
                <div class="dash-step-title">Download Your Report</div>
                <div class="dash-step-sub">Save your personalised PDF report card with full analytics.</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Last Prediction
    prev_score = st.session_state.get("prediction_result")
    if prev_score:
        grade, feedback = get_grade(prev_score)
        st.markdown(f'<div class="sec-title" style="margin-top:20px;">📌 Your Last Prediction</div>', unsafe_allow_html=True)
        p1, p2, p3, p4 = st.columns(4)
        for col, icon, val, lbl in [
            (p1, "📊", str(prev_score), "Score"),
            (p2, "🎯", grade,           "Grade"),
            (p3, "📈", "↑ High" if prev_score >= 75 else "→ Mid", "Level"),
            (p4, "⭐", "Top 25%" if prev_score >= 80 else "Top 50%", "Percentile"),
        ]:
            with col:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="stat-icon">{icon}</div>
                    <div class="stat-val">{val}</div>
                    <div class="stat-lbl">{lbl}</div>
                </div>""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        view_col, _ = st.columns([1, 3])
        with view_col:
            st.markdown('<div class="predict-hdr-btn">', unsafe_allow_html=True)
            if st.button("📋 View Full Result", key="view_result_dash"):
                st.session_state.view = "result"
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)


# ── SESSION VALIDITY CHECK (har rerun pe) ─────────────────────────────────────
check_session_still_valid()

# ── ROUTER ────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    render_auth()
else:
    user = st.session_state.user
    # Admin gets their own dedicated view
    if user and user.get("role") == "Admin":
        render_admin_dashboard()
    else:
        view = st.session_state.get("view", "dashboard")
        if view == "predict_form":
            render_logged_in_header()
            render_prediction_form()
        elif view == "result":
            render_logged_in_header()
            render_result_page()
        else:
            render_dashboard()
