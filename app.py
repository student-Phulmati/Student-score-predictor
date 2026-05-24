import streamlit as st
import pandas as pd
import numpy as np
import joblib
import hashlib
import json
import os
import io
import base64
import urllib.parse
from datetime import datetime, date
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Line, String

import plotly.graph_objects as go
import plotly.express as px

# =====================================================
# CONSTANTS
# =====================================================
APP_NAME         = "🎓 ScoreWise AI"
APP_NAME_PLAIN   = "ScoreWise AI"
TAGLINE          = "Smart Student Performance Predictor"
USER_DB_FILE     = "users.json"
HISTORY_FILE     = "prediction_history.json"
PROFILE_PICS_DIR = "profile_pics"
MODEL_FILE       = "student_model.pkl"
COLUMNS_FILE     = "model_columns.pkl"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

st.set_page_config(
    page_title=APP_NAME_PLAIN,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# UTILITY FUNCTIONS
# =====================================================
def load_json(path, default):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_age(dob):
    today = datetime.now().date()
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def save_profile_pic(username, image_bytes):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    with open(path, "wb") as f:
        f.write(image_bytes)

def profile_pic_html(username, fallback="🎓"):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />'
    return fallback

# =====================================================
# SESSION STATE INIT
# =====================================================
def init_state():
    defaults = {
        "logged_in":         False,
        "username":          "",
        "role":              "",
        "auth_page":         "welcome",
        "theme":             "light",
        "active_page":       "Home",
        "previous_page":     "Home",
        "last_score":        None,
        "last_pdf":          None,
        "last_inputs":       {},
        "last_recs":         [],
        "show_pic_uploader": False,
        "profile_edit_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# CSS — COMBINED (Welcome + Auth + Top Navbar Dashboard)
# =====================================================
def apply_css():
    dark       = st.session_state.theme == "dark"
    is_welcome = (not st.session_state.logged_in and st.session_state.auth_page == "welcome")

    BG_IMAGE = "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1900&q=85"

    if dark:
        app_bg        = f"linear-gradient(135deg,rgba(8,15,60,0.75) 0%,rgba(0,40,90,0.80) 100%), url('{BG_IMAGE}')" if not is_welcome else f"linear-gradient(135deg,rgba(3,4,94,0.55) 0%,rgba(0,119,182,0.30) 100%), url('{BG_IMAGE}')"
        card_bg       = "rgba(255,255,255,0.09)"
        soft_card_bg  = "rgba(255,255,255,0.07)"
        text_primary  = "#eaf4ff"
        text_secondary= "#b8d8f0"
        text_muted    = "#88c0e8"
        border_color  = "rgba(140,200,240,0.18)"
        input_bg      = "rgba(255,255,255,0.93)"
        input_text    = "#0a0f3c"
        input_border  = "rgba(0,150,220,0.40)"
        accent1       = "#52b6e8"
        accent2       = "#38a8dc"
        accent3       = "#1a95cc"
        topbar_bg     = "rgba(8,18,60,0.96)"
        topbar_border = "rgba(82,182,232,0.18)"
        topbar_text   = "#eaf4ff"
        topbar_role   = "#88c0e8"
        shadow        = "0 16px 50px rgba(0,0,0,0.28)"
    else:
        app_bg        = f"linear-gradient(135deg,rgba(240,250,255,0.84) 0%,rgba(220,242,255,0.88) 100%), url('{BG_IMAGE}')" if not is_welcome else f"linear-gradient(135deg,rgba(245,252,255,0.50) 0%,rgba(210,240,255,0.40) 100%), url('{BG_IMAGE}')"
        card_bg       = "rgba(255,255,255,0.65)"
        soft_card_bg  = "rgba(255,255,255,0.50)"
        text_primary  = "#03045e"
        text_secondary= "#023e8a"
        text_muted    = "#0077b6"
        border_color  = "rgba(2,62,138,0.16)"
        input_bg      = "rgba(255,255,255,0.95)"
        input_text    = "#03045e"
        input_border  = "rgba(0,119,182,0.30)"
        accent1       = "#0077b6"
        accent2       = "#0096c7"
        accent3       = "#00b4d8"
        topbar_bg     = "rgba(255,255,255,0.97)"
        topbar_border = "rgba(2,62,138,0.12)"
        topbar_text   = "#03045e"
        topbar_role   = "#0077b6"
        shadow        = "0 16px 50px rgba(2,62,138,0.18)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    * {{ font-family: 'Plus Jakarta Sans', sans-serif !important; box-sizing: border-box; }}

    /* ── Hide Streamlit chrome ── */
    .stApp > header {{ background: transparent !important; height: 0rem !important; }}
    [data-testid="stDecoration"] {{ display: none !important; }}
    #MainMenu, footer {{ visibility: hidden; height: 0; }}
    [data-testid="stToolbar"] {{ visibility: hidden !important; height: 0px !important; position: fixed !important; }}
    [data-testid="stSidebar"],
    [data-testid="stSidebarNav"],
    [data-testid="stSidebarCollapseButton"],
    [data-testid="collapsedControl"] {{
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        min-width: 0 !important;
    }}

    /* ── App background ── */
    .stApp {{
        background: {app_bg} !important;
        background-size: cover !important;
        background-position: center !important;
        background-attachment: fixed !important;
        color: {text_primary};
        min-height: 100vh;
    }}
    .main .block-container {{
        padding-top: 0 !important;
        padding-bottom: 1rem !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        max-width: 100% !important;
        margin-top: 0 !important;
    }}

    /* ══════════════════════════════════════════
       TOP NAVIGATION BAR
    ══════════════════════════════════════════ */
    .topbar-shell {{
        width: 100%;
        background: {topbar_bg};
        border-bottom: 1px solid {topbar_border};
        box-shadow: 0 4px 24px rgba(0,0,0,0.14);
        backdrop-filter: blur(28px);
        -webkit-backdrop-filter: blur(28px);
        padding: 10px 20px 8px 20px;
        position: sticky;
        top: 0;
        z-index: 9999;
    }}
    .top-profile {{
        display: flex;
        align-items: center;
        gap: 10px;
    }}
    .top-avatar {{
        width: 52px; height: 52px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden;
        background: linear-gradient(135deg,#0a1f6e,#0077b6,#00b4d8);
        font-size: 1.5rem;
        box-shadow: 0 4px 14px rgba(0,119,182,0.30);
        border: 2px solid {accent2};
        flex-shrink: 0;
    }}
    .top-name {{
        font-size: 1.05rem; font-weight: 900;
        color: {topbar_text}; line-height: 1.1;
    }}
    .top-role {{
        font-size: 0.75rem; font-weight: 600;
        color: {topbar_role}; margin-top: 2px;
    }}

    /* Back icon button and theme button in topbar */
    .back-icon-btn .stButton > button,
    .theme-top-btn .stButton > button {{
        width: 42px !important; min-width: 42px !important;
        height: 42px !important; border-radius: 12px !important;
        padding: 0 !important;
        background: {'rgba(255,255,255,0.10)' if dark else 'rgba(2,62,138,0.08)'} !important;
        color: {topbar_text} !important;
        border: 1px solid {topbar_border} !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.10) !important;
        font-size: 1.1rem !important;
        transition: all 0.18s ease !important;
    }}
    .back-icon-btn .stButton > button:hover,
    .theme-top-btn .stButton > button:hover {{
        background: linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color: white !important;
        transform: scale(1.06) !important;
        border-color: #00b4d8 !important;
    }}
    .signout-top-btn .stButton > button {{
        height: 42px !important;
        border-radius: 999px !important;
        padding: 0 1.1rem !important;
        font-size: 0.85rem !important;
    }}

    /* Segmented control nav */
    div[data-testid="stSegmentedControl"] {{
        background: transparent !important;
    }}
    div[data-testid="stSegmentedControl"] button {{
        border-radius: 10px !important;
        background: transparent !important;
        color: {topbar_role} !important;
        box-shadow: none !important;
        border: 0 !important;
        font-weight: 700 !important;
        font-size: 0.82rem !important;
        padding: 6px 10px !important;
        transition: all 0.15s ease !important;
    }}
    div[data-testid="stSegmentedControl"] button[aria-pressed="true"] {{
        color: {'#52b6e8' if dark else '#0077b6'} !important;
        background: {'rgba(82,182,232,0.14)' if dark else 'rgba(0,119,182,0.10)'} !important;
        border-bottom: 2px solid {'#52b6e8' if dark else '#0077b6'} !important;
        border-radius: 10px 10px 0 0 !important;
    }}

    /* ══════════════════════════════════════════
       DASHBOARD PAGE AREA
    ══════════════════════════════════════════ */
    .dash-page {{
        width: 100%;
        min-height: calc(100vh - 72px);
        padding: 36px 5vw 28px 5vw;
    }}
    .dash-title {{
        font-size: clamp(1.8rem, 3vw, 2.5rem);
        font-weight: 900; color: {text_primary};
        margin: 0 0 4px 0; letter-spacing: -0.6px;
    }}
    .dash-subtitle {{
        font-size: 0.95rem; font-weight: 700;
        color: {text_secondary}; margin-bottom: 28px;
    }}
    .chart-glass {{
        background: {card_bg};
        border: 1px solid {border_color};
        box-shadow: {shadow};
        backdrop-filter: blur(18px);
        -webkit-backdrop-filter: blur(18px);
        border-radius: 24px;
        padding: 18px 18px 4px 18px;
        margin-top: 20px;
    }}

    /* ── Glass cards ── */
    .glass {{
        background: {card_bg};
        border: 1px solid {border_color};
        box-shadow: {shadow};
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border-radius: 24px;
        padding: 26px;
    }}

    /* ── Page title ── */
    .page-title {{
        font-size: 1.9rem; font-weight: 900; margin-bottom: 2px; margin-top: 0;
        color: {text_primary}; letter-spacing: -0.5px;
    }}
    .subtext {{ color: {text_secondary}; font-size: 0.90rem; margin-bottom: 12px; font-weight: 600; }}

    /* ── Metric cards ── */
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        box-shadow: {shadow};
        backdrop-filter: blur(18px);
        border-radius: 20px; padding: 20px 12px; text-align: center; transition: 0.22s ease;
    }}
    .metric-card:hover {{ transform: translateY(-3px); background: {soft_card_bg}; }}
    .metric-value {{ font-size: 2.1rem; font-weight: 900; color: {accent1}; }}
    .metric-label {{ font-size: 0.72rem; color: {text_muted}; text-transform: uppercase; letter-spacing: 1px; margin-top: 4px; font-weight: 800; }}

    /* ── Avatar ── */
    .avatar-circle {{
        width: 86px; height: 86px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; margin: auto;
        border: 3px solid {accent2};
        background: linear-gradient(135deg,{accent1},{accent3});
        font-size: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.20);
    }}
    .avatar-circle img {{ width: 100%; height: 100%; object-fit: cover; border-radius: 50%; }}

    /* ── All buttons default ── */
    .stButton > button,
    [data-testid="stDownloadButton"] button,
    .stFormSubmitButton > button {{
        border-radius: 999px !important; border: 0 !important;
        font-weight: 800 !important; cursor: pointer !important;
        padding: 0.60rem 1.4rem !important;
        background: linear-gradient(135deg,#0a1f6e,#0077b6,#00b4d8) !important;
        color: white !important;
        box-shadow: 0 8px 22px rgba(0,119,182,0.28) !important;
        transition: all 0.20s ease !important;
    }}
    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover,
    .stFormSubmitButton > button:hover {{
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 14px 32px rgba(0,180,216,0.36) !important;
        background: linear-gradient(135deg,#0077b6,#00b4d8,#7dd8f5) !important;
        color: white !important;
    }}

    /* ── Inputs ── */
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stPasswordInput input,
    textarea {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {input_border} !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
        caret-color: {input_text} !important;
    }}
    .stTextInput input::placeholder,
    .stPasswordInput input::placeholder {{
        color: rgba(10,15,60,0.45) !important;
    }}
    .stSelectbox [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {input_border} !important;
        border-radius: 12px !important;
    }}
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div,
    .stSelectbox [data-baseweb="select"] input {{
        color: {input_text} !important;
    }}
    [data-baseweb="menu"] {{ background: {input_bg} !important; }}
    [data-baseweb="menu"] li {{ color: {input_text} !important; font-weight: 600 !important; }}
    [data-baseweb="menu"] li:hover {{ background: rgba(0,150,220,0.14) !important; }}
    [data-testid="stNumberInputField"] input {{
        color: {input_text} !important;
        background: {input_bg} !important;
    }}

    /* Labels */
    label, p {{ color: {text_primary} !important; }}
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stDateInput label, .stRadio label, .stCheckbox label,
    [data-baseweb="form-control"] label, .stSlider label {{
        color: {text_primary} !important;
        font-weight: 700 !important;
        font-size: 0.87rem !important;
    }}

    /* ── Tabs ── */
    [data-baseweb="tab-list"] {{ background: transparent !important; border-bottom: 1px solid {border_color} !important; }}
    [data-baseweb="tab"] {{ color: {text_muted} !important; font-weight: 800 !important; }}
    [aria-selected="true"][data-baseweb="tab"] {{ color: {accent1} !important; border-bottom: 3px solid {accent1} !important; }}

    /* ── WhatsApp button ── */
    .whatsapp-btn {{
        display: inline-block; border-radius: 999px; padding: 11px 22px;
        color: white !important; text-decoration: none; font-weight: 900;
        margin: 6px 4px; font-size: 0.92rem;
        box-shadow: 0 8px 22px rgba(0,0,0,0.18);
        background: linear-gradient(135deg,#25D366,#128C7E);
    }}

    /* ── Profile card ── */
    .profile-info-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        backdrop-filter: blur(18px);
        border-radius: 20px; padding: 22px;
    }}
    .profile-field {{
        display: flex; justify-content: space-between; gap: 14px;
        padding: 10px 0; border-bottom: 1px solid {border_color}; font-size: 0.92rem;
    }}
    .profile-field:last-child {{ border-bottom: none; }}
    .pf-label {{ color: {text_muted}; font-weight: 800; }}
    .pf-value {{ color: {text_primary}; font-weight: 900; }}

    /* ── Score badge ── */
    .score-badge {{
        display: inline-block; font-size: 3.4rem; font-weight: 900;
        color: {accent1}; padding: 16px 32px; border-radius: 22px; text-align: center;
        background: {card_bg};
        border: 1px solid {border_color};
        backdrop-filter: blur(16px);
    }}

    hr {{ border-color: {border_color} !important; }}
    .stAlert {{ border-radius: 16px !important; }}
    .stDataFrame {{ border-radius: 16px; overflow: hidden; }}

    /* ══════════════════════════════════════════
       WELCOME PAGE
    ══════════════════════════════════════════ */
    .hero-title {{
        font-size: clamp(2.2rem,4.5vw,3.4rem); font-weight: 900;
        color: {'white' if dark else '#03045e'}; margin: 0;
        letter-spacing: -1px; text-shadow: 0 3px 18px rgba(0,0,0,0.25); line-height: 1.05;
    }}
    .hero-tagline {{
        font-size: 1.02rem; color: {'#b8e0f7' if dark else '#0077b6'};
        font-weight: 600; margin: 6px 0 0 0;
    }}
    .welcome-divider {{
        border: 0; height: 1px;
        background: {'rgba(255,255,255,0.22)' if dark else 'rgba(2,62,138,0.14)'};
        margin: 10px auto 14px auto; max-width: 600px;
    }}
    .feature-cards-row {{ display: flex; gap: 14px; justify-content: center; flex-wrap: wrap; margin: 0 0 18px 0; }}
    .feat-card {{
        flex: 1 1 200px; max-width: 250px;
        background: {'rgba(255,255,255,0.11)' if dark else 'rgba(255,255,255,0.75)'};
        border: 1px solid {'rgba(255,255,255,0.22)' if dark else 'rgba(2,62,138,0.16)'};
        border-radius: 18px; padding: 20px 16px 16px 16px;
        text-align: center; backdrop-filter: blur(16px);
        box-shadow: 0 10px 30px rgba(0,0,0,0.14); transition: transform 0.20s ease;
    }}
    .feat-card:hover {{ transform: translateY(-4px); }}
    .feat-icon {{ font-size: 2rem; display:block; margin-bottom:7px; }}
    .feat-title {{ font-size: 1rem; font-weight: 900; color: {'white' if dark else '#03045e'}; margin: 0 0 4px 0; }}
    .feat-sep {{ width: 32px; height: 3px; background: linear-gradient(90deg,#00b4d8,#7dd8f5); border-radius: 99px; margin: 0 auto 8px auto; }}
    .feat-desc {{ font-size: 0.78rem; color: {'#b8e0f7' if dark else '#0077b6'}; font-weight: 600; line-height: 1.55; }}
    .used-for-row {{ display: flex; gap: 10px; justify-content: center; flex-wrap: wrap; margin: 0 0 6px 0; }}
    .used-item {{ text-align: center; padding: 4px 8px; }}
    .used-icon {{ font-size: 1.4rem; display:block; margin-bottom:2px; }}
    .used-label {{ font-size: 0.67rem; font-weight: 800; color: {'#b8e0f7' if dark else '#023e8a'}; text-transform: uppercase; letter-spacing: 0.6px; }}
    .stats-strip {{
        display: flex; gap: 10px; justify-content: center; flex-wrap: wrap;
        padding: 12px 10px;
        border-top: 1px solid {'rgba(255,255,255,0.20)' if dark else 'rgba(2,62,138,0.12)'};
        border-bottom: 1px solid {'rgba(255,255,255,0.20)' if dark else 'rgba(2,62,138,0.12)'};
        margin: 12px 0 16px 0;
    }}
    .stat-chip {{
        display: flex; align-items: center; gap: 6px; padding: 6px 12px;
        border-radius: 999px; background: rgba(0,180,216,0.12);
        border: 1px solid rgba(0,180,216,0.22);
    }}
    .stat-chip-num {{ font-size: 1.08rem; font-weight:900; color:{'white' if dark else '#03045e'}; }}
    .stat-chip-lbl {{ font-size: 0.70rem; font-weight:700; color:{'#b8e0f7' if dark else '#0096c7'}; text-transform:uppercase; letter-spacing:0.7px; }}
    .welcome-footer {{ text-align: center; font-size: 0.78rem; color: {'#b8e0f7' if dark else '#0077b6'}; padding: 6px 0 10px 0; font-weight: 600; }}

    /* ── Auth page back button ── */
    .back-btn-wrap .stButton > button {{
        background: {card_bg} !important;
        border: 1.5px solid {border_color} !important;
        color: {text_primary} !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.12) !important;
        padding: 0.38rem 1.1rem !important;
        font-size: 0.88rem !important;
        border-radius: 999px !important;
    }}
    .back-btn-wrap .stButton > button:hover {{
        background: {soft_card_bg} !important;
        transform: translateX(-2px) !important;
    }}
    .auth-theme-btn .stButton > button {{
        width: 46px !important; height: 40px !important;
        min-width: 46px !important; border-radius: 12px !important;
        padding: 0 !important; font-size: 1.1rem !important;
        background: {'rgba(8,15,60,0.85)' if dark else 'rgba(255,255,255,0.85)'} !important;
        border: 1.4px solid {border_color} !important;
        box-shadow: 0 4px 14px rgba(0,0,0,0.18) !important;
        color: {text_primary} !important;
    }}
    .auth-theme-btn .stButton > button:hover {{
        transform: scale(1.06) !important;
        border-color: #00b4d8 !important;
        background: linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color: white !important;
    }}

    /* ══════════════════════════════════════════
       WEBSITE STYLE DASHBOARD TOPBAR OVERRIDES
    ══════════════════════════════════════════ */
    .topbar-shell {{
        width: 100% !important;
        background: rgba(255,255,255,0.98) !important;
        border-bottom: 1px solid rgba(2,62,138,0.08) !important;
        box-shadow: 0 8px 28px rgba(3,4,94,0.10) !important;
        padding: 14px 18px !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 9999 !important;
    }}

    .brand-wrap {{
        display:flex;
        align-items:center;
        gap:12px;
        min-width:230px;
    }}
    .brand-logo {{
        width:54px;
        height:54px;
        border-radius:50%;
        display:flex;
        align-items:center;
        justify-content:center;
        background:linear-gradient(135deg,#004aad,#00b4d8);
        box-shadow:0 7px 20px rgba(0,119,182,0.25);
        color:white;
        font-size:1.55rem;
        flex-shrink:0;
    }}
    .brand-title {{
        color:#03045e;
        font-weight:900;
        font-size:1.55rem;
        line-height:1;
        letter-spacing:-0.5px;
    }}
    .brand-sub {{
        color:#023e8a;
        font-weight:600;
        font-size:0.72rem;
        margin-top:5px;
    }}

    .back-icon-btn .stButton > button {{
        width:52px !important;
        min-width:52px !important;
        height:52px !important;
        padding:0 !important;
        border-radius:12px !important;
        background:#ffffff !important;
        color:#03045e !important;
        border:1.5px solid rgba(2,62,138,0.14) !important;
        box-shadow:0 8px 20px rgba(3,4,94,0.08) !important;
        font-size:1.25rem !important;
        font-weight:900 !important;
    }}
    .back-icon-btn .stButton > button:hover {{
        background:#eef7ff !important;
        color:#004aad !important;
        transform:translateX(-2px) !important;
        border-color:rgba(0,119,182,0.25) !important;
    }}

    .nav-pill .stButton > button {{
        width:100% !important;
        min-height:52px !important;
        padding:0 16px !important;
        border-radius:12px !important;
        background:transparent !important;
        color:#1f3266 !important;
        border:0 !important;
        box-shadow:none !important;
        font-size:0.98rem !important;
        font-weight:800 !important;
    }}
    .nav-pill .stButton > button:hover {{
        background:#eef7ff !important;
        color:#0057c7 !important;
        transform:none !important;
        box-shadow:none !important;
    }}
    .nav-pill-active .stButton > button {{
        background:#e8f3ff !important;
        color:#0057c7 !important;
        box-shadow:0 6px 18px rgba(0,119,182,0.09) !important;
    }}

    .signout-top-btn .stButton > button {{
        height:52px !important;
        border-radius:18px !important;
        padding:0 24px !important;
        background:linear-gradient(135deg,#004aad,#0066d9) !important;
        color:white !important;
        font-size:0.95rem !important;
        font-weight:900 !important;
        box-shadow:0 10px 22px rgba(0,74,173,0.25) !important;
        white-space:nowrap !important;
    }}

    .theme-top-btn .stButton > button {{
        width:52px !important;
        min-width:52px !important;
        height:52px !important;
        padding:0 !important;
        border-radius:50% !important;
        background:#eaf4ff !important;
        color:#0057c7 !important;
        border:0 !important;
        box-shadow:none !important;
        font-size:1.1rem !important;
    }}

    .top-profile {{
        display:flex !important;
        align-items:center !important;
        justify-content:flex-start !important;
        gap:10px !important;
        min-width:130px !important;
    }}
    .top-avatar {{
        width:52px !important;
        height:52px !important;
        border-radius:50% !important;
        background:linear-gradient(135deg,#0077b6,#90e0ef) !important;
        color:white !important;
        border:0 !important;
        box-shadow:0 7px 20px rgba(0,119,182,0.20) !important;
        font-size:1.45rem !important;
    }}
    .top-name {{
        color:#03045e !important;
        font-size:1.02rem !important;
        font-weight:900 !important;
        line-height:1.05 !important;
    }}
    .top-role {{
        color:#334b78 !important;
        font-size:0.72rem !important;
        font-weight:600 !important;
        margin-top:4px !important;
        white-space:nowrap !important;
    }}

    .dash-page {{
        padding:54px 3.8vw 34px 3.8vw !important;
        min-height:calc(100vh - 82px) !important;
    }}
    .dash-title {{
        color:#03045e !important;
        font-size:clamp(2.0rem,3.1vw,2.8rem) !important;
        margin-bottom:16px !important;
    }}
    .dash-subtitle {{
        color:#1f3266 !important;
        font-size:1.02rem !important;
        margin-bottom:38px !important;
    }}
    .metric-card {{
        min-height:164px !important;
        border-radius:24px !important;
        background:rgba(255,255,255,0.78) !important;
        border:1px solid rgba(2,62,138,0.10) !important;
        box-shadow:0 12px 28px rgba(3,4,94,0.10) !important;
        display:flex !important;
        flex-direction:column !important;
        align-items:center !important;
        justify-content:center !important;
    }}
    .metric-value {{
        color:#0066d9 !important;
        font-size:2.8rem !important;
        line-height:1 !important;
    }}
    .metric-label {{
        color:#334b78 !important;
        font-size:0.92rem !important;
        margin-top:20px !important;
        letter-spacing:0 !important;
    }}
    .metric-accent {{
        width:64px;
        height:4px;
        border-radius:999px;
        margin:22px auto 0 auto;
    }}
    .chart-glass {{
        background:rgba(255,255,255,0.76) !important;
        border:1px solid rgba(2,62,138,0.10) !important;
        box-shadow:0 12px 28px rgba(3,4,94,0.10) !important;
        border-radius:24px !important;
        padding:18px 24px 8px 24px !important;
        margin-top:34px !important;
    }}

    @media (max-width: 900px) {{
        .brand-sub {{ display:none; }}
        .brand-title {{ font-size:1.15rem; }}
        .nav-pill .stButton > button {{ font-size:0.78rem !important; padding:0 6px !important; }}
        .dash-page {{ padding-left:22px !important; padding-right:22px !important; }}
    }}



    /* =====================================================
       FINAL STREAMLIT FIT FIX — compact navbar + no big gap
       ===================================================== */
    html, body, .stApp {{
        overflow-x: hidden !important;
    }}
    .main .block-container,
    [data-testid="stAppViewContainer"] .main .block-container {{
        padding-top: 0rem !important;
        padding-left: 0rem !important;
        padding-right: 0rem !important;
        max-width: 100% !important;
    }}
    .topbar-shell {{
        width: 100vw !important;
        margin-left: 0 !important;
        margin-right: 0 !important;
        padding: 8px 14px !important;
        min-height: 66px !important;
        display: block !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 999999 !important;
    }}
    .brand-wrap {{
        min-width: 0 !important;
        gap: 9px !important;
    }}
    .brand-logo,
    .top-avatar,
    .theme-top-btn .stButton > button,
    .back-icon-btn .stButton > button {{
        width: 42px !important;
        min-width: 42px !important;
        height: 42px !important;
    }}
    .brand-logo {{ font-size: 1.22rem !important; }}
    .brand-title {{
        font-size: 1.18rem !important;
        white-space: nowrap !important;
    }}
    .brand-sub {{
        font-size: 0.62rem !important;
        white-space: nowrap !important;
    }}
    .nav-pill .stButton > button,
    .nav-pill-active .stButton > button {{
        min-height: 42px !important;
        height: 42px !important;
        padding: 0 8px !important;
        border-radius: 11px !important;
        font-size: 0.80rem !important;
        line-height: 1 !important;
        white-space: nowrap !important;
    }}
    .signout-top-btn .stButton > button {{
        height: 42px !important;
        min-height: 42px !important;
        border-radius: 13px !important;
        padding: 0 12px !important;
        font-size: 0.78rem !important;
        white-space: nowrap !important;
    }}
    .top-profile {{ min-width: 0 !important; gap: 7px !important; }}
    .top-name {{
        font-size: 0.82rem !important;
        max-width: 92px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }}
    .top-role {{
        font-size: 0.58rem !important;
        max-width: 92px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
    }}
    .dash-page {{
        padding: 16px 3.2vw 26px 3.2vw !important;
        min-height: calc(100vh - 66px) !important;
    }}
    .dash-title {{
        margin-top: 0 !important;
        margin-bottom: 6px !important;
        font-size: clamp(1.45rem, 2.4vw, 2.1rem) !important;
    }}
    .dash-subtitle {{
        margin-bottom: 18px !important;
        font-size: 0.90rem !important;
    }}
    .metric-card {{
        min-height: 118px !important;
        padding: 14px 8px !important;
    }}
    .metric-value {{ font-size: 2.05rem !important; }}
    .metric-label {{
        font-size: 0.76rem !important;
        margin-top: 10px !important;
    }}
    .metric-accent {{
        margin-top: 12px !important;
        height: 3px !important;
    }}
    .chart-glass {{ margin-top: 18px !important; }}

    @media (max-width: 1100px) {{
        .brand-sub, .top-role {{ display: none !important; }}
        .brand-title {{ font-size: 1.00rem !important; }}
        .nav-pill .stButton > button {{ font-size: 0.72rem !important; padding: 0 4px !important; }}
        .signout-top-btn .stButton > button {{ font-size: 0.70rem !important; padding: 0 8px !important; }}
        .top-name {{ max-width: 65px !important; font-size: 0.74rem !important; }}
    }}
    @media (max-width: 760px) {{
        .brand-title {{ display: none !important; }}
        .nav-pill .stButton > button {{ font-size: 0.66rem !important; }}
        .top-profile {{ display: none !important; }}
        .dash-page {{ padding: 12px 16px 22px 16px !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)

apply_css()

def apply_10x_layout_fix():
    st.markdown("""
    <style>
    .stApp > header,
    header[data-testid="stHeader"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
    }
    [data-testid="stAppViewContainer"] > .main {
        padding-top: 0 !important;
    }
    .main .block-container,
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
        padding-bottom: 0.8rem !important;
    }
    div[data-testid="stVerticalBlock"] { gap: 0.35rem !important; }
    .topbar-shell {
        background: transparent !important;
        border: 0 !important;
        box-shadow: none !important;
        backdrop-filter: none !important;
        -webkit-backdrop-filter: none !important;
        padding: 8px 3.2vw 4px 3.2vw !important;
        min-height: 54px !important;
        position: sticky !important;
        top: 0 !important;
    }
    .top-menu-title {
        font-size: 1.28rem;
        font-weight: 900;
        color: #03045e;
        line-height: 1.05;
    }
    .top-menu-sub {
        font-size: 0.72rem;
        font-weight: 700;
        color: #0077b6;
    }
    .top-menu-btn .stButton > button,
    .top-menu-btn-active .stButton > button {
        min-height: 38px !important;
        height: 38px !important;
        padding: 0 12px !important;
        border-radius: 999px !important;
        font-size: 0.82rem !important;
        box-shadow: none !important;
        border: 1px solid rgba(0,119,182,0.16) !important;
        background: rgba(255,255,255,0.56) !important;
        color: #023e8a !important;
        white-space: nowrap !important;
    }
    .top-menu-btn-active .stButton > button,
    .top-menu-btn .stButton > button:hover {
        background: linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color: #ffffff !important;
        transform: none !important;
    }
    .dash-page {
        padding: 8px 3.2vw 22px 3.2vw !important;
        min-height: auto !important;
    }
    .page-title, .dash-title { margin-top: 0 !important; }
    .dash-subtitle, .subtext { margin-bottom: 12px !important; }
    .glass { margin-top: 0 !important; }
    @media (max-width: 760px) {
        .top-menu-title, .top-menu-sub { display:none !important; }
        .top-menu-btn .stButton > button,
        .top-menu-btn-active .stButton > button { font-size: 0.68rem !important; padding: 0 6px !important; }
    }
    </style>
    """, unsafe_allow_html=True)

apply_10x_layout_fix()

def apply_professional_header_fix():
    st.markdown("""
    <style>
    /* ===== FINAL PROFESSIONAL HEADER + GAP FIX ===== */
    .stApp > header,
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
    }
    [data-testid="stAppViewContainer"] > .main,
    .main {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    .main .block-container,
    [data-testid="stAppViewContainer"] .main .block-container {
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin-top: 0 !important;
        max-width: 100% !important;
    }
    div[data-testid="stVerticalBlock"] {
        gap: 0.25rem !important;
    }

    .topbar-shell {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    .pro-header {
        width: 100vw !important;
        margin: 0 !important;
        padding: 8px 2.4vw 7px 2.4vw !important;
        background: rgba(255,255,255,0.92) !important;
        border-bottom: 1px solid rgba(2,62,138,0.10) !important;
        box-shadow: 0 8px 26px rgba(3,4,94,0.08) !important;
        backdrop-filter: blur(18px) !important;
        -webkit-backdrop-filter: blur(18px) !important;
        position: sticky !important;
        top: 0 !important;
        z-index: 999999 !important;
    }

    .header-title-wrap { line-height: 1.05; }
    .header-app {
        color: #03045e !important;
        font-size: 1.05rem !important;
        font-weight: 900 !important;
        letter-spacing: -0.3px !important;
        white-space: nowrap !important;
    }
    .active-page-chip {
        display: inline-flex !important;
        align-items: center !important;
        gap: 5px !important;
        margin-top: 4px !important;
        padding: 4px 10px !important;
        border-radius: 999px !important;
        background: linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color: #ffffff !important;
        font-size: 0.68rem !important;
        font-weight: 900 !important;
        box-shadow: 0 6px 16px rgba(0,119,182,0.18) !important;
    }
    .header-sub {
        color: #46617f !important;
        font-size: 0.64rem !important;
        font-weight: 700 !important;
        margin-top: 3px !important;
        white-space: nowrap !important;
    }

    .back-top-btn .stButton > button {
        width: 40px !important;
        min-width: 40px !important;
        height: 40px !important;
        padding: 0 !important;
        border-radius: 14px !important;
        background: #ffffff !important;
        color: #023e8a !important;
        border: 1px solid rgba(2,62,138,0.16) !important;
        box-shadow: 0 6px 14px rgba(3,4,94,0.08) !important;
        font-size: 1.15rem !important;
        font-weight: 900 !important;
    }
    .back-top-btn .stButton > button:hover {
        background: #eaf6ff !important;
        color: #0077b6 !important;
        transform: translateX(-2px) !important;
    }

    .nav-tab .stButton > button,
    .nav-tab-active .stButton > button {
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 10px !important;
        border-radius: 999px !important;
        font-size: 0.74rem !important;
        font-weight: 900 !important;
        box-shadow: none !important;
        border: 1px solid rgba(0,119,182,0.13) !important;
        white-space: nowrap !important;
        transform: none !important;
    }
    .nav-tab .stButton > button {
        background: rgba(255,255,255,0.56) !important;
        color: #1f3266 !important;
    }
    .nav-tab-active .stButton > button,
    .nav-tab .stButton > button:hover {
        background: linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color: #ffffff !important;
        border-color: transparent !important;
    }

    .corner-user {
        display: flex !important;
        align-items: center !important;
        justify-content: flex-end !important;
        gap: 8px !important;
        min-width: 0 !important;
    }
    .corner-avatar {
        width: 40px !important;
        height: 40px !important;
        border-radius: 50% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        overflow: hidden !important;
        background: linear-gradient(135deg,#0077b6,#90e0ef) !important;
        color: #ffffff !important;
        font-size: 1.15rem !important;
        box-shadow: 0 7px 16px rgba(0,119,182,0.18) !important;
        flex-shrink: 0 !important;
    }
    .corner-name {
        color: #03045e !important;
        font-size: 0.78rem !important;
        font-weight: 900 !important;
        line-height: 1.1 !important;
        max-width: 100px !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        white-space: nowrap !important;
        text-align: left !important;
    }
    .corner-role {
        color: #0077b6 !important;
        font-size: 0.60rem !important;
        font-weight: 800 !important;
        margin-top: 2px !important;
        white-space: nowrap !important;
    }

    .circle-tool-btn .stButton > button {
        width: 38px !important;
        min-width: 38px !important;
        height: 38px !important;
        padding: 0 !important;
        border-radius: 50% !important;
        background: #eaf6ff !important;
        color: #0066d9 !important;
        border: 1px solid rgba(0,119,182,0.10) !important;
        box-shadow: none !important;
        font-size: 1rem !important;
    }
    .logout-small-btn .stButton > button {
        height: 38px !important;
        min-height: 38px !important;
        padding: 0 12px !important;
        border-radius: 999px !important;
        background: #03045e !important;
        color: #ffffff !important;
        border: 0 !important;
        box-shadow: 0 8px 18px rgba(3,4,94,0.16) !important;
        font-size: 0.70rem !important;
        font-weight: 900 !important;
        white-space: nowrap !important;
    }

    .dash-page {
        padding: 14px 5.2vw 24px 5.2vw !important;
        min-height: auto !important;
    }
    .dash-title,
    .page-title {
        margin-top: 0 !important;
        margin-bottom: 4px !important;
        font-size: clamp(1.45rem, 2.1vw, 2.05rem) !important;
        line-height: 1.08 !important;
    }
    .dash-subtitle,
    .subtext {
        margin-top: 0 !important;
        margin-bottom: 14px !important;
        font-size: 0.88rem !important;
    }
    .metric-card {
        min-height: 105px !important;
        padding: 12px 10px !important;
        border-radius: 18px !important;
    }
    .metric-value {
        font-size: 1.85rem !important;
    }
    .metric-label {
        font-size: 0.70rem !important;
        margin-top: 8px !important;
    }
    .metric-accent {
        margin-top: 9px !important;
        height: 3px !important;
    }
    .chart-glass {
        margin-top: 12px !important;
        padding: 10px 14px 4px 14px !important;
        border-radius: 18px !important;
    }

    @media (max-width: 1050px) {
        .header-sub { display: none !important; }
        .header-app { font-size: 0.90rem !important; }
        .nav-tab .stButton > button,
        .nav-tab-active .stButton > button {
            font-size: 0.64rem !important;
            padding: 0 5px !important;
        }
        .corner-role { display: none !important; }
        .corner-name { max-width: 68px !important; font-size: 0.68rem !important; }
    }
    @media (max-width: 760px) {
        .header-app { display: none !important; }
        .active-page-chip { font-size: 0.60rem !important; padding: 4px 7px !important; }
        .corner-user-text { display: none !important; }
        .nav-tab .stButton > button,
        .nav-tab-active .stButton > button {
            font-size: 0.58rem !important;
            padding: 0 4px !important;
        }
        .dash-page {
            padding: 10px 18px 20px 18px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

apply_professional_header_fix()


def apply_final_no_gap_header_fix():
    st.markdown("""
    <style>
    /* ===== FINAL LAYOUT FIX: remove top gap, remove left/right gap, improve title spacing ===== */
    .stApp > header,
    header[data-testid="stHeader"],
    [data-testid="stToolbar"],
    [data-testid="stDecoration"] {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        visibility: hidden !important;
    }

    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    .main {
        margin: 0 !important;
        padding: 0 !important;
        overflow-x: hidden !important;
    }

    .main .block-container,
    [data-testid="stAppViewContainer"] .main .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        padding-top: 0 !important;
        padding-left: 0 !important;
        padding-right: 0 !important;
        margin-top: 0 !important;
        max-width: 100% !important;
    }

    /* Remove hidden/empty custom header space */
    .topbar-shell,
    .pro-header {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
    }

    /* Tight Streamlit row spacing */
    div[data-testid="stVerticalBlock"] {
        gap: 0.08rem !important;
    }
    div[data-testid="stHorizontalBlock"] {
        gap: 0.55rem !important;
        align-items: center !important;
    }

    /* Pull the first header row to the very top */
    .element-container:empty {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
    }

    .back-top-btn,
    .nav-tab,
    .nav-tab-active,
    .circle-tool-btn,
    .logout-small-btn,
    .header-title-wrap,
    .corner-user {
        margin: 0 !important;
        padding: 0 !important;
    }

    .header-title-wrap {
        line-height: 1.05 !important;
    }

    .back-top-btn .stButton > button {
        width: 38px !important;
        min-width: 38px !important;
        height: 38px !important;
        border-radius: 12px !important;
        margin: 0 !important;
    }

    .nav-tab .stButton > button,
    .nav-tab-active .stButton > button {
        height: 36px !important;
        min-height: 36px !important;
        padding: 0 10px !important;
        font-size: 0.76rem !important;
        margin: 0 !important;
    }

    .circle-tool-btn .stButton > button {
        width: 36px !important;
        min-width: 36px !important;
        height: 36px !important;
        margin: 0 !important;
    }

    .logout-small-btn .stButton > button {
        height: 36px !important;
        min-height: 36px !important;
        padding: 0 12px !important;
        margin: 0 !important;
    }

    .corner-avatar {
        width: 36px !important;
        height: 36px !important;
    }

    /* Main page spacing: less top gap and less left/right gap */
    .dash-page {
        padding: 4px 1.35vw 20px 1.35vw !important;
        margin: 0 !important;
        min-height: auto !important;
    }

    /* Bigger welcome/page title */
    .dash-title,
    .page-title {
        margin-top: 0 !important;
        margin-bottom: 8px !important;
        font-size: clamp(1.95rem, 3vw, 2.75rem) !important;
        line-height: 1.08 !important;
        font-weight: 900 !important;
    }

    /* Add clear spacing under Welcome title text */
    .dash-subtitle,
    .subtext {
        display: block !important;
        margin-top: 8px !important;
        margin-bottom: 16px !important;
        line-height: 1.45 !important;
        font-size: 0.95rem !important;
        font-weight: 800 !important;
    }

    .metric-card {
        min-height: 100px !important;
        padding: 10px 8px !important;
    }

    .chart-glass {
        margin-top: 8px !important;
    }

    @media (max-width: 1050px) {
        .nav-tab .stButton > button,
        .nav-tab-active .stButton > button {
            font-size: 0.64rem !important;
            padding: 0 5px !important;
        }
        .corner-name {
            max-width: 62px !important;
        }
        .dash-page {
            padding-left: 12px !important;
            padding-right: 12px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

apply_final_no_gap_header_fix()

# =====================================================
# FINAL USER REQUEST FIX — professional side gap, bigger titles,
# visible upload text in dark mode, larger profile picture
# =====================================================
def apply_profile_margin_title_fix():
    st.markdown("""
    <style>
    /* Small professional side spacing for full app content/header */
    .main .block-container,
    [data-testid="stAppViewContainer"] .main .block-container,
    [data-testid="stMainBlockContainer"],
    [data-testid="stAppViewBlockContainer"] {
        padding-left: 18px !important;
        padding-right: 18px !important;
        padding-top: 0 !important;
        max-width: 100% !important;
    }

    /* Keep page content clean with balanced left/right gap */
    .dash-page {
        padding: 8px 3.4vw 24px 3.4vw !important;
        margin: 0 !important;
        min-height: auto !important;
    }

    /* Bigger main title inside every page */
    .dash-title,
    .page-title {
        font-size: clamp(2.35rem, 4.2vw, 3.65rem) !important;
        line-height: 1.04 !important;
        font-weight: 900 !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
        letter-spacing: -1px !important;
    }

    /* Subtitle: smaller than title and placed slightly lower */
    .dash-subtitle,
    .subtext {
        display: block !important;
        font-size: clamp(0.95rem, 1.25vw, 1.12rem) !important;
        line-height: 1.55 !important;
        font-weight: 800 !important;
        margin-top: 12px !important;
        margin-bottom: 18px !important;
    }

    /* Larger profile picture */
    .avatar-circle {
        width: 118px !important;
        height: 118px !important;
        font-size: 2.65rem !important;
        border-width: 4px !important;
    }

    /* File uploader text visible in dark mode */
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] label p,
    [data-testid="stFileUploader"] section,
    [data-testid="stFileUploader"] section div,
    [data-testid="stFileUploader"] small,
    [data-testid="stFileUploader"] span,
    [data-testid="stFileUploaderDropzone"] div,
    [data-testid="stFileUploaderDropzone"] small,
    [data-testid="stFileUploaderDropzone"] span {
        color: #eaf4ff !important;
        opacity: 1 !important;
        font-weight: 800 !important;
        text-shadow: 0 2px 10px rgba(0,0,0,0.55) !important;
    }

    [data-testid="stFileUploaderDropzone"] {
        background: rgba(255,255,255,0.12) !important;
        border: 1.5px solid rgba(144,224,239,0.40) !important;
        border-radius: 14px !important;
    }

    [data-testid="stFileUploaderDropzone"] button {
        color: #03045e !important;
        background: rgba(255,255,255,0.95) !important;
        border: 1px solid rgba(144,224,239,0.45) !important;
        font-weight: 900 !important;
    }

    @media (max-width: 760px) {
        .main .block-container,
        [data-testid="stAppViewContainer"] .main .block-container,
        [data-testid="stMainBlockContainer"],
        [data-testid="stAppViewBlockContainer"] {
            padding-left: 10px !important;
            padding-right: 10px !important;
        }
        .dash-page {
            padding: 8px 14px 22px 14px !important;
        }
        .page-title,
        .dash-title {
            font-size: 2.15rem !important;
        }
        .avatar-circle {
            width: 104px !important;
            height: 104px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

apply_profile_margin_title_fix()

# =====================================================
# FINAL HEADER TITLE + ACTIVE PAGE HIGHLIGHT FIX
# =====================================================
def apply_header_title_active_fix():
    st.markdown("""
    <style>
    /* FINAL HEADER UPDATE: brand title large, no separate active chip, active page highlighted in top menu */
    .header-title-wrap {
        display: flex !important;
        flex-direction: column !important;
        align-items: flex-start !important;
        justify-content: center !important;
        gap: 0 !important;
        padding: 0 !important;
        margin: 0 !important;
    }

    .header-app {
        color: #03045e !important;
        font-size: clamp(1.55rem, 2.35vw, 2.35rem) !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        letter-spacing: -0.8px !important;
        white-space: nowrap !important;
        text-shadow: 0 2px 12px rgba(255,255,255,0.55) !important;
    }

    /* Hide old page text/chip under ScoreWise AI */
    .header-sub,
    .active-page-chip {
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        opacity: 0 !important;
        visibility: hidden !important;
    }

    /* Welcome title made smaller and cleaner */
    .dash-title,
    .page-title {
        font-size: clamp(1.45rem, 2.65vw, 2.35rem) !important;
        line-height: 1.06 !important;
        font-weight: 900 !important;
        letter-spacing: -0.6px !important;
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }

    .dash-subtitle,
    .subtext {
        margin-top: 10px !important;
        margin-bottom: 16px !important;
        font-size: clamp(0.88rem, 1.04vw, 0.98rem) !important;
        line-height: 1.45 !important;
    }

    /* Active page highlight directly on the top menu button */
    .nav-tab-active .stButton > button {
        position: relative !important;
        background: linear-gradient(135deg,#023e8a,#0077b6,#00b4d8) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.44) !important;
        box-shadow: 0 12px 26px rgba(0,119,182,0.28) !important;
        transform: translateY(-1px) !important;
    }

    .nav-tab-active .stButton > button::after {
        content: "" !important;
        position: absolute !important;
        left: 22% !important;
        right: 22% !important;
        bottom: -7px !important;
        height: 4px !important;
        border-radius: 999px !important;
        background: linear-gradient(90deg,#03045e,#0077b6,#00b4d8) !important;
        box-shadow: 0 5px 12px rgba(0,119,182,0.30) !important;
    }

    .nav-tab .stButton > button:hover {
        background: rgba(255,255,255,0.74) !important;
        color: #0077b6 !important;
        border-color: rgba(0,119,182,0.24) !important;
    }

    @media (max-width: 1050px) {
        .header-app { font-size: 1.25rem !important; }
        .dash-title,
        .page-title { font-size: 1.95rem !important; }
    }

    @media (max-width: 760px) {
        .header-app {
            display: block !important;
            font-size: 1.05rem !important;
        }
        .dash-title,
        .page-title { font-size: 1.65rem !important; }
    }
    </style>
    """, unsafe_allow_html=True)

apply_header_title_active_fix()


# =====================================================
# FINAL BACK ARROW DESIGN FIX — match compact dark rectangle style
# =====================================================
def apply_back_arrow_second_design_fix():
    st.markdown("""
    <style>
    .back-top-btn .stButton > button {
        width: 96px !important;
        min-width: 96px !important;
        max-width: 96px !important;
        height: 54px !important;
        min-height: 54px !important;
        padding: 0 !important;
        margin: 0 !important;
        border-radius: 9px !important;
        background: rgba(80, 92, 132, 0.82) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        box-shadow: none !important;
        font-size: 1.18rem !important;
        font-weight: 900 !important;
        line-height: 1 !important;
        transform: none !important;
    }

    .back-top-btn .stButton > button:hover {
        background: rgba(88, 102, 146, 0.95) !important;
        color: #ffffff !important;
        border-color: rgba(255,255,255,0.18) !important;
        box-shadow: none !important;
        transform: none !important;
    }

    .back-top-btn .stButton > button:active {
        background: rgba(65, 76, 112, 0.98) !important;
        color: #ffffff !important;
        transform: scale(0.98) !important;
    }

    @media (max-width: 760px) {
        .back-top-btn .stButton > button {
            width: 76px !important;
            min-width: 76px !important;
            max-width: 76px !important;
            height: 46px !important;
            min-height: 46px !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

apply_back_arrow_second_design_fix()


# =====================================================
# FINAL WELCOME TEXT STYLE FIX — smaller welcome title + styled subtitle
# =====================================================
def apply_final_welcome_text_style_fix():
    st.markdown("""
    <style>
    /* Welcome heading: smaller than ScoreWise AI title, cleaner premium style */
    .dash-title,
    .page-title {
        font-family: "Trebuchet MS", "Plus Jakarta Sans", sans-serif !important;
        font-size: clamp(1.18rem, 2.05vw, 1.82rem) !important;
        line-height: 1.12 !important;
        font-weight: 900 !important;
        letter-spacing: -0.35px !important;
        margin-top: 4px !important;
        margin-bottom: 0 !important;
        color: #03045e !important;
        text-shadow: 0 3px 14px rgba(255,255,255,0.56) !important;
    }

    /* Subtitle under Welcome: different text style, clear spacing, professional look */
    .dash-subtitle,
    .subtext {
        font-family: "Segoe UI", "Plus Jakarta Sans", sans-serif !important;
        display: block !important;
        max-width: 760px !important;
        margin-top: 14px !important;
        margin-bottom: 18px !important;
        font-size: clamp(0.82rem, 0.95vw, 0.94rem) !important;
        line-height: 1.65 !important;
        font-weight: 700 !important;
        letter-spacing: 0.15px !important;
        color: #1f3266 !important;
        text-shadow: 0 2px 10px rgba(255,255,255,0.45) !important;
    }

    /* Keep ScoreWise AI brand bigger than Welcome */
    .header-app {
        font-size: clamp(1.65rem, 2.55vw, 2.45rem) !important;
        font-weight: 900 !important;
        letter-spacing: -0.75px !important;
    }

    @media (max-width: 1050px) {
        .dash-title,
        .page-title {
            font-size: 1.55rem !important;
        }
        .dash-subtitle,
        .subtext {
            font-size: 0.84rem !important;
            margin-top: 12px !important;
        }
    }

    @media (max-width: 760px) {
        .dash-title,
        .page-title {
            font-size: 1.35rem !important;
        }
        .dash-subtitle,
        .subtext {
            font-size: 0.78rem !important;
            line-height: 1.55 !important;
        }
    }
    </style>
    """, unsafe_allow_html=True)

apply_final_welcome_text_style_fix()

# =====================================================
# FINAL DARK MODE WELCOME TEXT VISIBILITY FIX
# =====================================================
def apply_home_welcome_dark_visibility_fix():
    dark = st.session_state.theme == "dark"
    title_color = "#f4fbff" if dark else "#03045e"
    subtitle_color = "#dff4ff" if dark else "#1f3266"
    title_shadow = "0 3px 16px rgba(0,0,0,0.72)" if dark else "0 3px 14px rgba(255,255,255,0.56)"
    subtitle_shadow = "0 2px 12px rgba(0,0,0,0.70)" if dark else "0 2px 10px rgba(255,255,255,0.45)"

    st.markdown(f"""
    <style>
    /* Home welcome text visibility fix for dark/light mode */
    .dash-page > .dash-title {{
        color: {title_color} !important;
        text-shadow: {title_shadow} !important;
    }}

    .dash-page > .dash-subtitle {{
        color: {subtitle_color} !important;
        text-shadow: {subtitle_shadow} !important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_home_welcome_dark_visibility_fix()


# =====================================================
# FINAL ACTIVE NAV COLOR FIX — active page shown by button color only
# =====================================================
def apply_active_nav_color_fix():
    st.markdown("""
    <style>
    /* Inactive top navigation buttons: clean glass look */
    .nav-tab .stButton > button {
        background: rgba(255,255,255,0.62) !important;
        color: #023e8a !important;
        border: 1px solid rgba(0,119,182,0.18) !important;
        box-shadow: 0 6px 16px rgba(3,4,94,0.08) !important;
        transform: none !important;
    }

    .nav-tab .stButton > button:hover {
        background: rgba(234,246,255,0.92) !important;
        color: #004aad !important;
        border-color: rgba(0,119,182,0.32) !important;
        box-shadow: 0 8px 18px rgba(0,119,182,0.14) !important;
        transform: translateY(-1px) !important;
    }

    /* Active page highlight: changed color so current page is clearly visible */
    .nav-tab-active .stButton > button {
        position: relative !important;
        background: linear-gradient(135deg,#ff8a00,#ffb703,#ffd166) !important;
        color: #03045e !important;
        border: 1px solid rgba(255,255,255,0.70) !important;
        box-shadow: 0 12px 28px rgba(255,183,3,0.34) !important;
        transform: translateY(-1px) !important;
        font-weight: 900 !important;
    }

    /* Remove old blue underline from active button and use soft glow only */
    .nav-tab-active .stButton > button::after {
        content: "" !important;
        position: absolute !important;
        left: 26% !important;
        right: 26% !important;
        bottom: -6px !important;
        height: 4px !important;
        border-radius: 999px !important;
        background: linear-gradient(90deg,#ff8a00,#ffb703,#ffd166) !important;
        box-shadow: 0 6px 14px rgba(255,183,3,0.36) !important;
    }

    .nav-tab-active .stButton > button:hover {
        background: linear-gradient(135deg,#ff9f1c,#ffb703,#ffe08a) !important;
        color: #03045e !important;
        transform: translateY(-1px) !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_active_nav_color_fix()

# =====================================================
# FINAL AUTH DARK MODE VISIBILITY FIX — Login / OTP Signup text
# =====================================================
def apply_auth_dark_text_visibility_fix():
    dark = st.session_state.theme == "dark"
    tab_text = "#eaf4ff" if dark else "#03045e"
    tab_muted = "#b8e0f7" if dark else "#023e8a"
    active_tab = "#ffffff" if dark else "#0077b6"
    underline = "#90e0ef" if dark else "#0077b6"
    st.markdown(f"""
    <style>
    /* Make Login and Sign Up tabs visible in dark mode */
    [data-baseweb="tab-list"] {{
        border-bottom: 1px solid rgba(144,224,239,0.38) !important;
    }}

    [data-baseweb="tab"],
    [data-baseweb="tab"] *,
    [data-baseweb="tab"] p,
    [data-baseweb="tab"] span {{
        color: {tab_text} !important;
        opacity: 1 !important;
        font-weight: 900 !important;
        text-shadow: 0 2px 10px rgba(0,0,0,0.45) !important;
    }}

    [data-baseweb="tab"]:hover,
    [data-baseweb="tab"]:hover *,
    [data-baseweb="tab"][aria-selected="true"],
    [data-baseweb="tab"][aria-selected="true"] *,
    [aria-selected="true"][data-baseweb="tab"] {{
        color: {active_tab} !important;
        opacity: 1 !important;
    }}

    [aria-selected="true"][data-baseweb="tab"] {{
        border-bottom: 3px solid {underline} !important;
    }}

    /* Make subtitle below title readable in dark mode */
    h2 + .subtext,
    p.subtext {{
        color: {tab_muted} !important;
        opacity: 1 !important;
        text-shadow: 0 2px 12px rgba(0,0,0,0.45) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_auth_dark_text_visibility_fix()

# =====================================================
# FINAL MODE BUTTON GLASSY BOX FIX — frosted transparent look
# =====================================================
def apply_mode_button_glassy_box_fix():
    st.markdown("""
    <style>
    /* Mode change box/button: glassy transparent look with blur */
    .auth-theme-btn,
    .theme-top-btn,
    .circle-tool-btn {
        border-radius: 999px !important;
        background: rgba(255, 255, 255, 0.10) !important;
        border: 1px solid rgba(255, 255, 255, 0.26) !important;
        box-shadow: 0 12px 32px rgba(3, 4, 94, 0.18) !important;
        backdrop-filter: blur(22px) saturate(175%) !important;
        -webkit-backdrop-filter: blur(22px) saturate(175%) !important;
    }

    .auth-theme-btn .stButton,
    .theme-top-btn .stButton,
    .circle-tool-btn .stButton {
        margin: 0 !important;
        padding: 0 !important;
    }

    .auth-theme-btn .stButton > button,
    .theme-top-btn .stButton > button,
    .circle-tool-btn .stButton > button {
        background: linear-gradient(135deg, rgba(255,255,255,0.30), rgba(255,255,255,0.08)) !important;
        background-color: rgba(255, 255, 255, 0.14) !important;
        color: #ffffff !important;
        border: 1px solid rgba(255, 255, 255, 0.36) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.38), 0 10px 28px rgba(0, 119, 182, 0.18) !important;
        backdrop-filter: blur(24px) saturate(180%) !important;
        -webkit-backdrop-filter: blur(24px) saturate(180%) !important;
        text-shadow: 0 2px 10px rgba(0, 0, 0, 0.42) !important;
        transition: all 0.22s ease !important;
    }

    .auth-theme-btn .stButton > button:hover,
    .theme-top-btn .stButton > button:hover,
    .circle-tool-btn .stButton > button:hover {
        background: linear-gradient(135deg, rgba(0,180,216,0.38), rgba(255,255,255,0.16)) !important;
        color: #ffffff !important;
        border-color: rgba(255,255,255,0.58) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.48), 0 16px 36px rgba(0,119,182,0.30) !important;
        transform: translateY(-1px) scale(1.04) !important;
    }

    .auth-theme-btn .stButton > button:focus,
    .theme-top-btn .stButton > button:focus,
    .circle-tool-btn .stButton > button:focus {
        outline: none !important;
        box-shadow: 0 0 0 3px rgba(144,224,239,0.32), inset 0 1px 0 rgba(255,255,255,0.42) !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_mode_button_glassy_box_fix()


# =====================================================
# FINAL PROFILE PAGE FIX — uploader overlap, empty box removal, bigger avatar
# =====================================================
def apply_profile_page_final_fix():
    dark = st.session_state.theme == "dark"
    label_color = "#eaf4ff" if dark else "#03045e"
    helper_color = "#d8f3ff" if dark else "#023e8a"
    drop_bg = "rgba(255,255,255,0.16)" if dark else "rgba(255,255,255,0.72)"
    drop_border = "rgba(144,224,239,0.55)" if dark else "rgba(0,119,182,0.24)"
    st.markdown(f"""
    <style>
    /* Profile photo circle: bigger and clean */
    .avatar-circle {{
        width: 148px !important;
        height: 148px !important;
        min-width: 148px !important;
        min-height: 148px !important;
        font-size: 3.25rem !important;
        border-width: 4px !important;
        margin: 10px auto 18px auto !important;
    }}

    /* Upload text: no overlap + readable in light and dark mode */
    [data-testid="stFileUploader"] {{
        margin-top: 8px !important;
        max-width: 100% !important;
    }}
    [data-testid="stFileUploader"] label,
    [data-testid="stFileUploader"] label p {{
        color: {label_color} !important;
        opacity: 1 !important;
        font-weight: 900 !important;
        font-size: 0.88rem !important;
        line-height: 1.3 !important;
        margin-bottom: 8px !important;
        text-shadow: none !important;
    }}
    [data-testid="stFileUploaderDropzone"] {{
        min-height: 62px !important;
        padding: 10px 12px !important;
        display: flex !important;
        align-items: center !important;
        gap: 10px !important;
        overflow: hidden !important;
        background: {drop_bg} !important;
        border: 1.5px solid {drop_border} !important;
        border-radius: 16px !important;
    }}
    [data-testid="stFileUploaderDropzone"] * {{
        color: {helper_color} !important;
        opacity: 1 !important;
        font-weight: 800 !important;
        line-height: 1.25 !important;
        text-shadow: none !important;
        white-space: normal !important;
    }}
    [data-testid="stFileUploaderDropzone"] button {{
        flex-shrink: 0 !important;
        min-width: 92px !important;
        height: 38px !important;
        border-radius: 10px !important;
        color: #03045e !important;
        background: rgba(255,255,255,0.96) !important;
        border: 1px solid rgba(0,119,182,0.22) !important;
        font-weight: 900 !important;
        box-shadow: none !important;
    }}

    /* Profile information card: remove the empty rounded box above Username */
    .profile-info-card {{
        margin-top: 0 !important;
        padding: 18px 22px !important;
        background: rgba(255,255,255,0.42) !important;
        border: 1px solid rgba(0,119,182,0.16) !important;
        border-radius: 18px !important;
        box-shadow: none !important;
    }}
    .profile-info-card:empty {{
        display: none !important;
        height: 0 !important;
        min-height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        border: 0 !important;
        background: transparent !important;
    }}
    .profile-field {{
        display: flex !important;
        justify-content: space-between !important;
        align-items: center !important;
        gap: 18px !important;
        padding: 9px 0 !important;
        border-bottom: 1px solid rgba(0,119,182,0.14) !important;
    }}
    .pf-label {{ color: #0077b6 !important; font-weight: 900 !important; }}
    .pf-value {{ color: #03045e !important; font-weight: 900 !important; text-align: right !important; }}

    @media (max-width: 760px) {{
        .avatar-circle {{
            width: 122px !important;
            height: 122px !important;
            min-width: 122px !important;
            min-height: 122px !important;
        }}
        .profile-field {{ align-items: flex-start !important; flex-direction: column !important; gap: 4px !important; }}
        .pf-value {{ text-align: left !important; }}
    }}
    </style>
    """, unsafe_allow_html=True)

apply_profile_page_final_fix()


# =====================================================
# MODEL AND PREDICTION
# =====================================================
@st.cache_resource
def load_model_files():
    if os.path.exists(MODEL_FILE) and os.path.exists(COLUMNS_FILE):
        return joblib.load(MODEL_FILE), joblib.load(COLUMNS_FILE)
    return None, None

def predict_score(data):
    model, columns = load_model_files()
    if model is not None and columns is not None:
        df = pd.DataFrame([data])
        df = pd.get_dummies(df)
        df = df.reindex(columns=columns, fill_value=0)
        pred = model.predict(df)[0]
    else:
        pred = (
            data["Previous_Scores"] * 0.38 + data["Attendance"] * 0.22 +
            min(data["Hours_Studied"] * 7, 45) * 0.55 + data["Sleep_Hours"] * 2.2
        )
        bonus = {"Low": -4, "Medium": 2, "High": 6}.get(data["Motivation_Level"], 0)
        pred += bonus
    return int(max(0, min(100, round(pred))))

def get_recommendations(d):
    recs = []
    if d["Hours_Studied"] < 6:           recs.append("📚 Improve daily study hours to 6–8 hours.")
    if d["Attendance"] < 80:             recs.append("🏫 Keep attendance above 80% for stronger performance.")
    if d["Sleep_Hours"] < 7:             recs.append("😴 Maintain 7–8 hours of sleep to improve concentration.")
    if d["Motivation_Level"] == "Low":   recs.append("🎯 Set small daily goals and track your progress.")
    if d["Internet_Access"] == "No":     recs.append("📖 Use offline notes, library support, and teacher guidance.")
    if d["Learning_Resources"] == "Low": recs.append("💡 Use free learning resources such as lectures, notes, and PDFs.")
    if d["Peer_Influence"] == "Negative":recs.append("🤝 Build a positive peer group to improve academic consistency.")
    return recs

# =====================================================
# HISTORY AND PDF
# =====================================================
def user_history(username):
    all_h = load_json(HISTORY_FILE, {})
    return all_h.get(username, [])

def save_prediction(username, record):
    all_h = load_json(HISTORY_FILE, {})
    all_h.setdefault(username, [])
    all_h[username].append(record)
    all_h[username] = all_h[username][-20:]
    save_json(HISTORY_FILE, all_h)

def simple_pdf_graph(scores):
    drawing = Drawing(430, 160)
    drawing.add(String(10, 145, "Score History Graph", fontSize=12, fillColor=colors.HexColor("#184e77")))
    drawing.add(Line(35, 30, 410, 30, strokeColor=colors.grey))
    drawing.add(Line(35, 30, 35, 130, strokeColor=colors.grey))
    for y, lab in [(30, "0"), (80, "50"), (130, "100")]:
        drawing.add(String(8, y-4, lab, fontSize=7, fillColor=colors.grey))
        drawing.add(Line(35, y, 410, y, strokeColor=colors.lightgrey, strokeWidth=.4))
    if len(scores) >= 1:
        xs  = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        pts = [(float(x), 30 + (float(s) / 100) * 100) for x, s in zip(xs, scores)]
        for i in range(len(pts)-1):
            drawing.add(Line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                             strokeColor=colors.HexColor("#34a0a4"), strokeWidth=2))
        for i, (x, y) in enumerate(pts):
            drawing.add(String(x-5, y+6, str(scores[i]), fontSize=7, fillColor=colors.HexColor("#184e77")))
    return drawing

def generate_pdf(username, user_data, score, inputs, recs):
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch,
                                leftMargin=0.7*inch, rightMargin=0.7*inch)
    styles = getSampleStyleSheet()
    title_style    = ParagraphStyle("TitleX", parent=styles["Heading1"], alignment=1, fontSize=22,
                                    textColor=colors.HexColor("#168aad"), spaceAfter=4, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubX",   parent=styles["Normal"],   alignment=1, fontSize=10,
                                    textColor=colors.HexColor("#1a759f"), spaceAfter=14, fontName="Helvetica")
    head_style     = ParagraphStyle("HeadX",  parent=styles["Heading2"], fontSize=13, textColor=colors.white,
                                    spaceAfter=0, fontName="Helvetica-Bold", backColor=colors.HexColor("#184e77"),
                                    borderPadding=(8,10,8,10))
    normal_style   = ParagraphStyle("NormX",  parent=styles["Normal"],   fontSize=10, leading=15,
                                    textColor=colors.HexColor("#03045e"))
    rec_style      = ParagraphStyle("RecX",   parent=styles["Normal"],   fontSize=10, leading=15,
                                    textColor=colors.HexColor("#184e77"), leftIndent=10)
    story = []
    story.append(Paragraph(f"🎓 {APP_NAME_PLAIN}", title_style))
    story.append(Paragraph("Official Student Performance Prediction Report", subtitle_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y  |  %I:%M %p')}", subtitle_style))
    story.append(Table([[""]], colWidths=[6.6*inch],
        style=[("LINEBELOW",(0,0),(-1,-1),1.2,colors.HexColor("#168aad")),
               ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(Spacer(1,10))
    student_name = user_data.get("full_name") or user_data.get("child_name") or username
    story.append(Paragraph("  Student / User Details", head_style))
    story.append(Spacer(1,4))
    info_rows = [["Full Name", student_name], ["Username", username],
                 ["Email", user_data.get("email","N/A")], ["Role", user_data.get("role","N/A").title()]]
    if user_data.get("role") == "student":
        info_rows += [["Grade / Class", user_data.get("grade","N/A")],
                      ["School", user_data.get("school","N/A")],
                      ["Date of Birth", user_data.get("dob","N/A")]]
    else:
        info_rows += [["Child Name", user_data.get("child_name","N/A")],
                      ["Child Grade", user_data.get("child_grade","N/A")],
                      ["Relation", user_data.get("relation","N/A")]]
    t_info = Table([[Paragraph(f"<b>{r[0]}</b>", normal_style), Paragraph(r[1], normal_style)] for r in info_rows],
                   colWidths=[2.2*inch, 4.4*inch])
    t_info.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(1,0),(1,-1),"Helvetica"),
    ]))
    story.append(t_info); story.append(Spacer(1,14))
    story.append(Paragraph("  Prediction Result", head_style)); story.append(Spacer(1,4))
    status_label = "Excellent!" if score>=85 else ("Good" if score>=70 else "Needs Improvement")
    score_color  = colors.HexColor("#168aad") if score>=70 else colors.HexColor("#e85d04")
    result_rows  = [["Predicted Score", f"{score} / 100"], ["Performance Status", status_label]]
    t_result = Table([[Paragraph(f"<b>{r[0]}</b>", normal_style), Paragraph(r[1], normal_style)] for r in result_rows],
                     colWidths=[2.2*inch, 4.4*inch])
    t_result.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("BACKGROUND",(1,0),(1,0),colors.HexColor("#caf0f8")),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(1,0),(1,0),13),("TEXTCOLOR",(1,0),(1,0),score_color),("PADDING",(0,0),(-1,-1),9),
    ]))
    story.append(t_result); story.append(Spacer(1,14))
    story.append(Paragraph("  Academic Input Details", head_style)); story.append(Spacer(1,4))
    input_header = [[Paragraph("<b>Factor</b>", normal_style), Paragraph("<b>Value Provided</b>", normal_style)]]
    input_data   = [[Paragraph(k.replace("_"," "), normal_style), Paragraph(str(v), normal_style)] for k,v in inputs.items()]
    t_inputs = Table(input_header+input_data, colWidths=[2.9*inch, 3.7*inch])
    t_inputs.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#184e77")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
    ]))
    story.append(t_inputs); story.append(Spacer(1,14))
    scores_list = [r.get("score",0) for r in user_history(username)] + [score]
    if len(scores_list) > 1:
        story.append(Paragraph("  Score History Graph", head_style)); story.append(Spacer(1,6))
        story.append(simple_pdf_graph(scores_list[-10:])); story.append(Spacer(1,14))
    story.append(Paragraph("  Personalized Recommendations", head_style)); story.append(Spacer(1,6))
    if recs:
        for r in recs:
            clean = r
            for ch in ["📚","🏫","😴","🎯","📖","💡","🤝"," "]:
                clean = clean.lstrip(ch)
            story.append(Paragraph("• " + clean.strip(), rec_style))
            story.append(Spacer(1,3))
    else:
        story.append(Paragraph("Your current academic inputs are strong. Keep up the great work!", rec_style))
    story.append(Spacer(1,20))
    story.append(Table([[""]], colWidths=[6.6*inch],
        style=[("LINEABOVE",(0,0),(-1,-1),.8,colors.HexColor("#ade8f4")),
               ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(Paragraph(f"Generated by {APP_NAME_PLAIN}  |  {datetime.now().strftime('%d-%m-%Y')}  |  For academic guidance only.", subtitle_style))
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# =====================================================
# CHART HELPERS
# =====================================================
def get_chart_colors():
    dark = st.session_state.theme == "dark"
    return {
        "paper":  "rgba(0,0,0,0)",
        "plot":   "rgba(0,0,0,0)",
        "line":   "#7dd8f5" if dark else "#1e6091",
        "marker": "#52b6e8" if dark else "#168aad",
        "text":   "#eaf4ff" if dark else "#03045e",
        "axis":   "#dff6ff" if dark else "#3b4f68",
        "grid":   "rgba(234,244,255,0.18)" if dark else "rgba(26,117,159,0.12)",
    }

def score_trend_chart(records):
    cc = get_chart_colors()
    scores = [r["score"] for r in records]
    dates  = [r.get("date", f"#{i+1}") for i,r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=scores, mode="lines+markers+text", name="Score",
        text=scores, textposition="top center",
        line=dict(width=3, color=cc["line"]),
        marker=dict(size=10, color=cc["marker"], line=dict(width=2, color="white")),
        fill="tozeroy", fillcolor="rgba(56,168,220,0.10)",
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#52b6e8",
                  annotation_text="Pass Line", annotation_font_color="#52b6e8")
    fig.add_hline(y=85, line_dash="dot", line_color="#7dd8f5",
                  annotation_text="Excellent", annotation_font_color="#7dd8f5")
    fig.update_layout(
        title=dict(
            text="📈 Score Trend Over Time",
            font=dict(color=cc["text"], size=16),
            y=0.94,
            x=0.01,
            xanchor="left",
            yanchor="top",
        ),
        height=310, margin=dict(l=36, r=18, t=58, b=42),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(
            gridcolor=cc["grid"],
            color=cc["axis"],
            tickfont=dict(color=cc["axis"], size=12),
            title_font=dict(color=cc["axis"]),
            linecolor=cc["grid"],
            zerolinecolor=cc["grid"],
        ),
        yaxis=dict(
            gridcolor=cc["grid"],
            color=cc["axis"],
            tickfont=dict(color=cc["axis"], size=12),
            title_font=dict(color=cc["axis"]),
            linecolor=cc["grid"],
            zerolinecolor=cc["grid"],
            range=[0,110],
        ),
        showlegend=False,
    )
    return fig

def radar_chart(inputs):
    cc = get_chart_colors()
    cats = ["Study Hours","Attendance","Sleep","Motivation","Resources","Peer Influence"]
    vals = [
        min(inputs.get("Hours_Studied",0)/10*100, 100),
        inputs.get("Attendance",0),
        min(inputs.get("Sleep_Hours",0)/9*100, 100),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
        {"Negative":10,"Neutral":55,"Positive":100}.get(inputs.get("Peer_Influence","Neutral"),55),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
        fillcolor="rgba(56,168,220,0.16)",
        line=dict(color=cc["line"],width=2.5),
        marker=dict(color=cc["marker"],size=7),
    ))
    fig.update_layout(
        title=dict(text="🕸️ Academic Profile Radar",font=dict(color=cc["text"],size=15)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True,range=[0,100],color=cc["text"],gridcolor=cc["grid"]),
            angularaxis=dict(color=cc["text"]),
        ),
        height=320, margin=dict(l=20,r=20,t=48,b=20),
        paper_bgcolor=cc["paper"], showlegend=False,
    )
    return fig

def factor_bar_chart(inputs):
    cc = get_chart_colors()
    factors = {
        "Hours Studied": min(inputs.get("Hours_Studied",0)/10*100, 100),
        "Attendance":    inputs.get("Attendance",0),
        "Prev Score":    inputs.get("Previous_Scores",0),
        "Sleep Quality": min(inputs.get("Sleep_Hours",0)/9*100, 100),
        "Motivation":    {"Low":25,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        "Learning Res.": {"Low":25,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
    }
    fig = go.Figure(go.Bar(
        x=list(factors.keys()), y=list(factors.values()),
        marker=dict(
            color=list(factors.values()),
            colorscale=[[0,"#1e6091"],[0.4,"#38a8dc"],[0.7,"#7dd8f5"],[1,"#c8eeff"]],
            showscale=False
        ),
        text=[f"{v:.0f}" for v in factors.values()],
        textposition="outside", textfont=dict(color=cc["text"],size=11),
    ))
    fig.update_layout(
        title=dict(text="📊 Key Factors Contributing to Score",font=dict(color=cc["text"],size=15)),
        height=300, margin=dict(l=10,r=10,t=48,b=10),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"],color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"],color=cc["text"],range=[0,115]),
        showlegend=False,
    )
    return fig

# =====================================================
# WELCOME PAGE
# =====================================================
def welcome_page():
    dark = st.session_state.theme == "dark"
    card_desc = "#b8e0f7" if dark else "#0077b6"
    emoji = "☀️" if dark else "🌙"

    title_col, icon_col = st.columns([14, 1])
    with title_col:
        st.markdown(f"""
        <div style="text-align:center; padding: 18px 0 4px 0; margin:0;">
          <h1 class='hero-title'>{APP_NAME}</h1>
          <p class='hero-tagline'>{TAGLINE} ✨</p>
        </div>
        """, unsafe_allow_html=True)
    with icon_col:
        st.markdown("<div style='padding-top:22px'>", unsafe_allow_html=True)
        if st.button(emoji, key="theme_welcome"):
            st.session_state.theme = "light" if dark else "dark"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <hr class='welcome-divider'/>
    <div class='feature-cards-row'>
      <div class='feat-card'>
        <span class='feat-icon'>📊</span>
        <div class='feat-title'>Smart Graph</div>
        <div class='feat-sep'></div>
        <div class='feat-desc'>• Visualize academic trends<br>• Subject-wise performance<br>• Interactive &amp; insightful</div>
      </div>
      <div class='feat-card'>
        <span class='feat-icon'>🔮</span>
        <div class='feat-title'>Prediction</div>
        <div class='feat-sep'></div>
        <div class='feat-desc'>• AI score prediction<br>• Simple result<br>• Quick &amp; accurate</div>
      </div>
      <div class='feat-card'>
        <span class='feat-icon'>📄</span>
        <div class='feat-title'>PDF Report</div>
        <div class='feat-sep'></div>
        <div class='feat-desc'>• Downloadable report<br>• Share on WhatsApp<br>• Professional format</div>
      </div>
    </div>
    <div style='text-align:center;margin-bottom:7px;font-size:0.80rem;font-weight:700;color:{card_desc};letter-spacing:1.3px;text-transform:uppercase;'>─── Used For ───</div>
    <div class='used-for-row'>
      <div class='used-item'><span class='used-icon'>🎓</span><div class='used-label'>Students</div></div>
      <div class='used-item'><span class='used-icon'>👨‍👩‍👧</span><div class='used-label'>Parents</div></div>
      <div class='used-item'><span class='used-icon'>📖</span><div class='used-label'>Teachers</div></div>
      <div class='used-item'><span class='used-icon'>🏫</span><div class='used-label'>Schools</div></div>
      <div class='used-item'><span class='used-icon'>🧑‍💼</span><div class='used-label'>Counselors</div></div>
    </div>
    <div class='stats-strip'>
      <div class='stat-chip'><span class='stat-chip-num'>5000+</span><span class='stat-chip-lbl'>Students Helped</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>25K+</span><span class='stat-chip-lbl'>Predictions Made</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>10K+</span><span class='stat-chip-lbl'>Reports Generated</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>99%</span><span class='stat-chip-lbl'>Accuracy Rate</span></div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1.8, 1, 1.8])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    st.markdown("<div class='welcome-footer'>❤️ Made with love for Students &nbsp;|&nbsp; Empowering Education with AI</div>", unsafe_allow_html=True)

# =====================================================
# AUTH PAGE  (Login + Signup)
# =====================================================
def auth_page():
    users = load_json(USER_DB_FILE, {})
    dark  = st.session_state.theme == "dark"
    emoji = "☀️" if dark else "🌙"

    # Top bar: Back | spacer | Theme
    left_col, spacer_col, right_col = st.columns([2, 8, 1])
    with left_col:
        st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
        if st.button("← Back", key="auth_back"):
            st.session_state.auth_page = "welcome"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with right_col:
        st.markdown('<div class="auth-theme-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="theme_auth"):
            st.session_state.theme = "light" if dark else "dark"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # Login / Signup card
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>{APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:16px'>Secure Login & Signup</p>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Login", "✍️ Sign Up"])

        # ── LOGIN ──
        with tab_login:
            username = st.text_input("Username", key="login_user", placeholder="Enter username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
            st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
            if st.button("Login", key="do_login", use_container_width=True):
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in   = True
                    st.session_state.username    = username
                    st.session_state.role        = users[username].get("role","student")
                    st.session_state.active_page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        # ── SIGNUP WITHOUT OTP ──
        with tab_signup:
            role      = st.selectbox("Account Type", ["student","parent"], format_func=lambda x: x.title(), key="su_role")
            username  = st.text_input("Create Username",  key="su_user")
            email     = st.text_input("Email",            key="su_email")
            full_name = st.text_input("Full Name",         key="su_name")
            password  = st.text_input("Password",          type="password", key="su_pass")
            confirm   = st.text_input("Confirm Password",  type="password", key="su_confirm")

            if role == "student":
                dob    = st.date_input("Date of Birth", key="su_dob",
                                       min_value=datetime(1990,1,1).date(),
                                       max_value=datetime.now().date())
                grade  = st.selectbox("Class / Course",
                                      ["Class 8","Class 9","Class 10","Class 11","Class 12","College"],
                                      key="su_grade")
                school = st.text_input("School / College", key="su_school")
            else:
                child_name = st.text_input("Child Name",    key="su_child")
                grade      = st.selectbox("Child Class / Course",
                                          ["Class 8","Class 9","Class 10","Class 11","Class 12","College"],
                                          key="su_cgrade")
                relation   = st.selectbox("Relation", ["Father","Mother","Guardian"], key="su_relation")

            # Create account directly without email OTP verification
            if st.button("🚀 Create Account", key="create_account_btn", use_container_width=True):
                if not username or not email or not full_name or not password or not confirm:
                    st.warning("Please fill all required fields first.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif username in users:
                    st.error("Username already exists. Please choose another.")
                else:
                    data = {
                        "password":   hash_password(password),
                        "email":      email,
                        "full_name":  full_name,
                        "role":       role,
                        "created_at": datetime.now().isoformat()
                    }
                    if role == "student":
                        data.update({
                            "dob":    str(dob),
                            "age":    calculate_age(dob),
                            "grade":  grade,
                            "school": school
                        })
                    else:
                        data.update({
                            "child_name":  child_name,
                            "child_grade": grade,
                            "relation":    relation
                        })
                    users[username] = data
                    save_json(USER_DB_FILE, users)
                    st.session_state.logged_in   = True
                    st.session_state.username    = username
                    st.session_state.role        = role
                    st.session_state.active_page = "Home"
                    st.session_state.auth_page   = "welcome"
                    st.success("🎉 Account created! Opening your dashboard…")
                    st.rerun()


# =====================================================
# TOP NAVIGATION BAR
# =====================================================
def go_page(page_name):
    """Change page and remember previous page for Back button."""
    if st.session_state.active_page != page_name:
        st.session_state.previous_page = st.session_state.active_page
        st.session_state.active_page = page_name

def top_navbar(user):
    """Professional compact header with Back, active page indicator, menu, and user profile."""
    emoji = "🌙" if st.session_state.theme == "light" else "☀️"
    active = st.session_state.active_page
    name = user.get("full_name", st.session_state.username) or st.session_state.username
    role = user.get("role", st.session_state.role or "student").title()
    icon = "🎓" if user.get("role", "student") == "student" else "👨‍👩‍👧"
    avatar = profile_pic_html(st.session_state.username, icon)

    page_icons = {
        "Home": "🏠",
        "Prediction": "📈",
        "Report & Share": "📄",
        "History": "📚",
        "Profile": "👤",
    }
    page_subtitles = {
        "Home": "Dashboard overview",
        "Prediction": "Enter details and predict score",
        "Report & Share": "PDF report and sharing",
        "History": "Previous prediction records",
        "Profile": "User account details",
    }

    c_back, c_title, c_home, c_pred, c_report, c_hist, c_prof, c_user, c_theme, c_sign = st.columns(
        [0.55, 2.15, 0.72, 0.92, 0.92, 0.82, 0.82, 1.35, 0.48, 0.72],
        gap="small",
        vertical_alignment="center"
    )

    with c_back:
        st.markdown('<div class="back-top-btn">', unsafe_allow_html=True)
        if st.button("←", key="header_back", help="Back", use_container_width=True):
            prev = st.session_state.get("previous_page", "Home")
            if active == "Home":
                st.session_state.logged_in = False
                st.session_state.auth_page = "welcome"
            else:
                st.session_state.active_page = prev if prev != active else "Home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c_title:
        st.markdown(f"""
        <div class="header-title-wrap">
            <div class="header-app">🎓 {APP_NAME_PLAIN}</div>
            <div class="header-sub">{page_subtitles.get(active, TAGLINE)}</div>
        </div>
        """, unsafe_allow_html=True)

    menu_items = [
        (c_home, "Home", "Home"),
        (c_pred, "Prediction", "Predict"),
        (c_report, "Report & Share", "Report"),
        (c_hist, "History", "History"),
        (c_prof, "Profile", "Profile"),
    ]
    for col, page_name, label in menu_items:
        with col:
            active_cls = "nav-tab-active" if active == page_name else "nav-tab"
            st.markdown(f'<div class="{active_cls}">', unsafe_allow_html=True)
            if st.button(label, key=f"pro_nav_{page_name}", use_container_width=True):
                go_page(page_name)
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

    with c_user:
        st.markdown(f"""
        <div class="corner-user">
            <div class="corner-avatar">{avatar}</div>
            <div class="corner-user-text">
                <div class="corner-name">{name}</div>
                <div class="corner-role">{role} Account</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with c_theme:
        st.markdown('<div class="circle-tool-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="pro_theme", help="Toggle Theme", use_container_width=True):
            st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with c_sign:
        st.markdown('<div class="logout-small-btn">', unsafe_allow_html=True)
        if st.button("Logout", key="pro_logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.role = ""
            st.session_state.auth_page = "welcome"
            st.session_state.active_page = "Home"
            st.session_state.previous_page = "Home"
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


# =====================================================
# INNER PAGES
# =====================================================

# ── HOME ──
def home_page(user):
    records = user_history(st.session_state.username)
    name    = user.get("full_name", st.session_state.username)

    st.markdown("<div class='dash-page'>", unsafe_allow_html=True)
    st.markdown(f"<div class='dash-title'>👋 Welcome, {name}!</div>", unsafe_allow_html=True)
    st.markdown("<p class='dash-subtitle'>Your academic performance dashboard — all insights in one place.</p>", unsafe_allow_html=True)

    scores = [r["score"] for r in records]
    c1,c2,c3,c4 = st.columns(4)
    metrics = [
        ("🎯 Attempts",  len(records)),
        ("🏆 Best Score", max(scores) if scores else 0),
        ("📊 Average",    int(np.mean(scores)) if scores else 0),
        ("🕐 Last Score", scores[-1] if scores else 0),
    ]
    for col, (label, val) in zip([c1,c2,c3,c4], metrics):
        with col:
            accent_colors = ["#0066d9", "#20c970", "#9b42ff", "#ff8a00"]
            accent = accent_colors[[c1,c2,c3,c4].index(col)]
            st.markdown(f"""
            <div class='metric-card'>
              <div class='metric-value'>{val}</div>
              <div class='metric-label'>{label}</div>
              <div class='metric-accent' style='background:{accent}'></div>
            </div>
            """, unsafe_allow_html=True)

    if records:
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.info("🚀 Go to the **Prediction** page and generate your first score!")

    st.markdown("</div>", unsafe_allow_html=True)


# ── PREDICTION ──
def prediction_page(user):
    st.markdown("<div class='dash-page'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Enter academic details. Save keeps values; Predict opens the full report page.</p>", unsafe_allow_html=True)

    saved = st.session_state.last_inputs if isinstance(st.session_state.last_inputs, dict) else {}

    def saved_index(options, key, default):
        value = saved.get(key, default)
        return options.index(value) if value in options else options.index(default)

    with st.form("prediction_form", clear_on_submit=False):
        col1, col2 = st.columns(2)
        with col1:
            hours = st.number_input("📖 Hours Studied (per day)", 0, 24, int(saved.get("Hours_Studied", 5) or 5), 1)
            attendance = st.number_input("🏫 Attendance (%)", 0, 100, int(saved.get("Attendance", 75) or 75), 1)
            previous = st.number_input("📝 Previous Score", 0, 100, int(saved.get("Previous_Scores", 60) or 60), 1)
            sleep = st.number_input("😴 Sleep Hours", 0, 12, int(saved.get("Sleep_Hours", 7) or 7), 1)
            motivation = st.selectbox("💡 Motivation Level", ["Low","Medium","High"], index=saved_index(["Low","Medium","High"], "Motivation_Level", "Medium"))
            teacher = st.selectbox("👨‍🏫 Teacher Quality", ["Poor","Average","Good"], index=saved_index(["Poor","Average","Good"], "Teacher_Quality", "Average"))
            school_type = st.selectbox("🏢 School Type", ["Public","Private"], index=saved_index(["Public","Private"], "School_Type", "Public"))
        with col2:
            internet = st.selectbox("🌐 Internet Access", ["Yes","No"], index=saved_index(["Yes","No"], "Internet_Access", "Yes"))
            income = st.selectbox("💰 Family Income", ["Low","Medium","High"], index=saved_index(["Low","Medium","High"], "Family_Income", "Medium"))
            parental = st.selectbox("👨‍👩‍👦 Parental Involvement", ["Low","Medium","High"], index=saved_index(["Low","Medium","High"], "Parental_Involvement", "Medium"))
            education = st.selectbox("🎓 Parent Education", ["School","College"], index=saved_index(["School","College"], "Parental_Education_Level", "School"))
            peer = st.selectbox("🤝 Peer Influence", ["Negative","Neutral","Positive"], index=saved_index(["Negative","Neutral","Positive"], "Peer_Influence", "Neutral"))
            resources = st.selectbox("📚 Learning Resources", ["Low","Medium","High"], index=saved_index(["Low","Medium","High"], "Learning_Resources", "Medium"))
            activities = st.selectbox("⚽ Extracurricular", ["Yes","No"], index=saved_index(["Yes","No"], "Extracurricular_Activities", "Yes"))

        st.markdown("<br>", unsafe_allow_html=True)
        save_col, predict_col = st.columns(2)
        with save_col:
            save_clicked = st.form_submit_button("💾 Save Values", use_container_width=True)
        with predict_col:
            predict_clicked = st.form_submit_button("🚀 Predict & Open Report", use_container_width=True)

    data = {
        "Hours_Studied": int(hours),
        "Attendance": int(attendance),
        "Previous_Scores": int(previous),
        "Sleep_Hours": int(sleep),
        "Motivation_Level": motivation,
        "Teacher_Quality": teacher,
        "School_Type": school_type,
        "Internet_Access": internet,
        "Family_Income": income,
        "Parental_Involvement": parental,
        "Parental_Education_Level": education,
        "Peer_Influence": peer,
        "Learning_Resources": resources,
        "Extracurricular_Activities": activities,
    }

    total_hours = hours + sleep
    if (save_clicked or predict_clicked) and total_hours > 24:
        st.error("Study Hours + Sleep Hours cannot exceed 24 hours per day.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    if save_clicked:
        st.session_state.last_inputs = data
        st.success("✅ Values saved. Now click Predict & Open Report when you want the full report.")

    if predict_clicked:
        score = predict_score(data)
        recs = get_recommendations(data)
        record = {
            "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "score": score,
            "inputs": data,
            "recommendations": recs,
        }
        save_prediction(st.session_state.username, record)
        st.session_state.last_score = score
        st.session_state.last_inputs = data
        st.session_state.last_recs = recs
        st.session_state.last_pdf = generate_pdf(st.session_state.username, user, score, data, recs)
        go_page("Report & Share")
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


# ── REPORT & SHARE ──
def report_page(user):
    st.markdown("<div class='dash-page'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Download the PDF report and share it through WhatsApp.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Please generate a score from the Prediction page first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    latest = records[-1] if records else {
        "score":           st.session_state.last_score,
        "inputs":          st.session_state.last_inputs,
        "recommendations": st.session_state.last_recs
    }
    score  = latest["score"]
    inputs = latest["inputs"]
    recs   = latest.get("recommendations", [])
    pdf    = st.session_state.last_pdf or generate_pdf(
                 st.session_state.username, user, score, inputs, recs)

    col1, col2, col3 = st.columns([1,1,1])
    with col2:
        st.markdown(f"""
        <div class='metric-card'>
          <div class='metric-label'>Predicted Score</div>
          <div class='metric-value'>{score}/100</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 📥 Download Complete Report")

    download_col1, download_col2, download_col3 = st.columns([1, 1, 1])
    with download_col2:
        st.download_button(
            "📄 Download PDF Report",
            data=pdf,
            file_name=f"ScoreWise_Report_{st.session_state.username}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    share_message = (
        f"🎓 {APP_NAME_PLAIN} PDF Report\n"
        f"Predicted Score: {score}/100\n"
        f"Please attach the downloaded PDF report in this WhatsApp chat."
    )
    wa_url = "https://wa.me/?text=" + urllib.parse.quote(share_message)
    st.markdown(f"""
    <div style='text-align:center;margin:16px 0 6px 0'>
      <a class='whatsapp-btn' target='_blank' href='{wa_url}'>📱 Open WhatsApp to Share PDF</a>
    </div>
    """, unsafe_allow_html=True)
    st.caption("WhatsApp browser link PDF ko automatic attach nahi kar sakta. Pehle PDF download hoga, phir WhatsApp open karke wahi PDF attach karke send karein.")

    st.markdown("### 📊 Performance Graphs")
    col_g1, col_g2 = st.columns(2)
    with col_g1:
        st.plotly_chart(radar_chart(inputs), use_container_width=True)
    with col_g2:
        st.plotly_chart(factor_bar_chart(inputs), use_container_width=True)
    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)

    if recs:
        st.markdown("### 💬 Recommendations")
        for r in recs:
            st.info(r)

    st.markdown("</div>", unsafe_allow_html=True)


# ── HISTORY ──
def history_page(user):
    st.markdown("<div class='dash-page'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>View all your predictions in one place.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if not records:
        st.info("No prediction history yet. Go to Prediction page to get started!")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    df = pd.DataFrame([{
        "Date":       r["date"],
        "Score":      r["score"],
        "Hours":      r["inputs"].get("Hours_Studied"),
        "Attendance": r["inputs"].get("Attendance"),
        "Previous":   r["inputs"].get("Previous_Scores"),
    } for r in records])
    st.dataframe(df, use_container_width=True)
    st.plotly_chart(score_trend_chart(records), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


# ── PROFILE ──
def profile_page(user):
    st.markdown("<div class='dash-page'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Edit your profile details and update your profile picture.</p>", unsafe_allow_html=True)

    users = load_json(USER_DB_FILE, {})
    uname = st.session_state.username

    col1, col2 = st.columns([1, 2])

    with col1:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(uname, icon)}</div>",
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        upload = st.file_uploader("📸 Upload Profile Picture", type=["jpg","jpeg","png"])
        if upload and st.button("💾 Save Picture", use_container_width=True):
            save_profile_pic(uname, upload.read())
            st.success("Profile picture updated!")
            st.rerun()

    with col2:
        edit = st.session_state.profile_edit_mode

        if not edit:
            # View mode
            fields = [
                ("Username",  uname),
                ("Full Name", user.get("full_name","N/A")),
                ("Email",     user.get("email","N/A")),
                ("Role",      user.get("role","N/A").title()),
            ]
            if user.get("role") == "student":
                fields += [
                    ("Date of Birth", user.get("dob","N/A")),
                    ("Age",           str(user.get("age","N/A"))),
                    ("Class/Grade",   user.get("grade","N/A")),
                    ("School/College",user.get("school","N/A")),
                ]
            else:
                fields += [
                    ("Child Name",  user.get("child_name","N/A")),
                    ("Child Grade", user.get("child_grade","N/A")),
                    ("Relation",    user.get("relation","N/A")),
                ]

            profile_rows_html = "".join(
                f"""
                <div class='profile-field'>
                  <span class='pf-label'>{label}</span>
                  <span class='pf-value'>{val}</span>
                </div>
                """
                for label, val in fields
            )
            st.markdown(f"<div class='profile-info-card'>{profile_rows_html}</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", use_container_width=True):
                st.session_state.profile_edit_mode = True
                st.rerun()

        else:
            # Edit mode
            with st.form("edit_profile_form"):
                st.markdown("##### ✏️ Edit Your Details")
                new_name  = st.text_input("Full Name", value=user.get("full_name",""))
                new_email = st.text_input("Email",     value=user.get("email",""))

                if user.get("role") == "student":
                    dob_val  = user.get("dob","2000-01-01")
                    try:    dob_date = datetime.strptime(dob_val,"%Y-%m-%d").date()
                    except: dob_date = date(2000,1,1)
                    new_dob    = st.date_input("Date of Birth", value=dob_date,
                                               min_value=date(1990,1,1), max_value=date.today())
                    grade_opts = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_grade  = user.get("grade","Class 10")
                    g_idx      = grade_opts.index(cur_grade) if cur_grade in grade_opts else 2
                    new_grade  = st.selectbox("Class / Grade", grade_opts, index=g_idx)
                    new_school = st.text_input("School / College", value=user.get("school",""))
                else:
                    new_child  = st.text_input("Child Name", value=user.get("child_name",""))
                    grade_opts = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_grade  = user.get("child_grade","Class 10")
                    g_idx      = grade_opts.index(cur_grade) if cur_grade in grade_opts else 2
                    new_cgrade = st.selectbox("Child Grade", grade_opts, index=g_idx)
                    rel_opts   = ["Father","Mother","Guardian"]
                    cur_rel    = user.get("relation","Father")
                    r_idx      = rel_opts.index(cur_rel) if cur_rel in rel_opts else 0
                    new_rel    = st.selectbox("Relation", rel_opts, index=r_idx)

                st.markdown("##### 🔒 Change Password (optional)")
                old_pass = st.text_input("Current Password",      type="password")
                new_pass = st.text_input("New Password",          type="password")
                cnf_pass = st.text_input("Confirm New Password",  type="password")

                col_s1, col_s2 = st.columns(2)
                with col_s1: save_clicked   = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with col_s2: cancel_clicked = st.form_submit_button("❌ Cancel",        use_container_width=True)

            if cancel_clicked:
                st.session_state.profile_edit_mode = False
                st.rerun()

            if save_clicked:
                updated = users[uname].copy()
                updated["full_name"] = new_name
                updated["email"]     = new_email
                if user.get("role") == "student":
                    updated["dob"]    = str(new_dob)
                    updated["age"]    = calculate_age(new_dob)
                    updated["grade"]  = new_grade
                    updated["school"] = new_school
                else:
                    updated["child_name"]  = new_child
                    updated["child_grade"] = new_cgrade
                    updated["relation"]    = new_rel

                if old_pass or new_pass or cnf_pass:
                    if users[uname]["password"] != hash_password(old_pass):
                        st.error("Current password is incorrect.")
                        st.stop()
                    elif new_pass != cnf_pass:
                        st.error("New passwords do not match.")
                        st.stop()
                    elif len(new_pass) < 6:
                        st.error("Password must be at least 6 characters.")
                        st.stop()
                    else:
                        updated["password"] = hash_password(new_pass)

                users[uname] = updated
                save_json(USER_DB_FILE, users)
                st.session_state.profile_edit_mode = False
                st.success("✅ Profile updated successfully!")
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# MAIN APP SHELL  (Top Navbar + Page Router)
# =====================================================
def main_app():
    users = load_json(USER_DB_FILE, {})
    user  = users.get(st.session_state.username, {})

    top_navbar(user)

    page = st.session_state.active_page
    if   page == "Home":           home_page(user)
    elif page == "Prediction":     prediction_page(user)
    elif page == "Report & Share": report_page(user)
    elif page == "History":        history_page(user)
    elif page == "Profile":        profile_page(user)

# =====================================================
# ROUTER
# =====================================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()

# =====================================================
# FINAL HOME CHART DARK MODE FIX — visible title + remove thin top line
# =====================================================
def apply_home_chart_dark_fix():
    st.markdown("""
    <style>
    /* Score Trend chart title wrapper: remove the thin white box/line above chart */
    .chart-glass {
        border: 0 !important;
        border-top: 0 !important;
        box-shadow: none !important;
        background: transparent !important;
        padding-top: 0 !important;
        margin-top: 22px !important;
    }

    /* Keep the chart title and graph labels readable in dark mode */
    .chart-glass .gtitle {
        fill: #eaf4ff !important;
        color: #eaf4ff !important;
        font-weight: 900 !important;
    }
    .chart-glass .xtick text,
    .chart-glass .ytick text,
    .chart-glass .annotation-text {
        fill: #dff6ff !important;
        color: #dff6ff !important;
        font-weight: 800 !important;
    }
    </style>
    """, unsafe_allow_html=True)

apply_home_chart_dark_fix()
