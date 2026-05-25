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
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.graphics.shapes import Drawing, Line, String, Rect, Polygon, Circle

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

    /* ── Profile card — FIX: top empty box removed ── */
    .profile-info-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        backdrop-filter: blur(18px);
        border-radius: 20px;
        padding: 0 22px 22px 22px;
        margin-top: 0 !important;
        overflow: hidden;
    }}
    .profile-field {{
        display: flex; justify-content: space-between; gap: 14px;
        padding: 10px 0; border-bottom: 1px solid {border_color}; font-size: 0.92rem;
    }}
    .profile-field:first-child {{
        padding-top: 16px;
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

    /* Welcome heading */
    .dash-title,
    .page-title {
        font-family: "Trebuchet MS", "Plus Jakarta Sans", sans-serif !important;
        font-size: clamp(1.18rem, 2.05vw, 1.82rem) !important;
        line-height: 1.12 !important;
        font-weight: 900 !important;
        letter-spacing: -0.35px !important;
        margin-top: 4px !important;
        margin-bottom: 0 !important;
        color: #f4f8ff !important;
        text-shadow:
            0 3px 14px rgba(0,0,0,0.65),
            0 1px 3px rgba(0,0,0,0.55) !important;
    }

    /* Welcome subtitle FIXED for dark mode */
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

        color: #f1f5ff !important;

        text-shadow:
            0 2px 12px rgba(0,0,0,0.80),
            0 1px 3px rgba(0,0,0,0.65) !important;

        opacity: 1 !important;
    }

    </style>
    """, unsafe_allow_html=True)

apply_final_welcome_text_style_fix()
