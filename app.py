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
