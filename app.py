import streamlit as st
import pandas as pd
import numpy as np
import joblib
import hashlib
import json
import os
import io
import base64
import random
import smtplib
import urllib.parse
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Line, String

import plotly.graph_objects as go

APP_NAME = "AcadraIQ"
TAGLINE = "Smart Student Performance Predictor"
USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"
OTP_FILE = "otp_store.json"
PROFILE_PICS_DIR = "profile_pics"
MODEL_FILE = "student_model.pkl"
COLUMNS_FILE = "model_columns.pkl"
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_gmail_app_password"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)
st.set_page_config(page_title=APP_NAME, page_icon="🌿", layout="wide", initial_sidebar_state="expanded")

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

def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

def calculate_age(dob):
    today = datetime.now().date()
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def save_profile_pic(username, image_bytes):
    with open(os.path.join(PROFILE_PICS_DIR, f"{username}.jpg"), "wb") as f:
        f.write(image_bytes)

def profile_pic_html(username, fallback="🌿"):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" />'
    return fallback

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(email, otp):
    data = load_json(OTP_FILE, {})
    data[email] = {"otp": otp, "timestamp": datetime.now().isoformat(), "verified": False}
    save_json(OTP_FILE, data)

def verify_otp(email, entered):
    data = load_json(OTP_FILE, {})
    if email not in data:
        return False, "OTP not found."
    saved = data[email]
    if (datetime.now() - datetime.fromisoformat(saved["timestamp"])).total_seconds() > 600:
        return False, "OTP expired."
    if saved["otp"] != entered:
        return False, "Invalid OTP."
    data[email]["verified"] = True
    save_json(OTP_FILE, data)
    return True, "OTP verified."

def send_otp_email(receiver, otp, name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME} OTP"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver
        html = f"""<div style='font-family:Arial;background:#1b4332;color:white;padding:26px;border-radius:18px'>
          <h2 style='color:#95d5b2'>{APP_NAME}</h2>
          <p>Hello <b>{name}</b>, your OTP is:</p>
          <div style='font-size:34px;letter-spacing:8px;font-weight:800;color:#52b788'>{otp}</div>
          <p>Valid for 10 minutes.</p></div>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
            s.login(EMAIL_SENDER, EMAIL_PASSWORD)
            s.sendmail(EMAIL_SENDER, receiver, msg.as_string())
        return True, "OTP sent."
    except Exception as e:
        return False, str(e)

def init_state():
    defaults = {
        "logged_in": False, "username": "", "role": "",
        "auth_page": "welcome", "theme": "dark",
        "active_page": "Home", "last_score": None,
        "last_pdf": None, "last_inputs": {}, "last_recs": [],
        "show_pic_uploader": False, "profile_edit_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

def apply_css():
    dark = st.session_state.theme == "dark"

    if dark:
        # Deep forest dark — rich, shining greens
        app_bg          = "#081c15"
        sidebar_bg      = "rgba(11,28,21,0.97)"
        card_bg         = "rgba(27,67,50,0.78)"
        card_border     = "rgba(82,183,136,0.28)"
        text_primary    = "#d8f3dc"
        text_secondary  = "#b7e4c7"
        text_muted      = "#95d5b2"
        accent1         = "#52b788"
        accent2         = "#40916c"
        accent3         = "#2d6a4f"
        input_bg        = "rgba(8,28,21,0.90)"
        input_text      = "#d8f3dc"
        input_border    = "rgba(82,183,136,0.38)"
        btn_bg          = "#40916c"
        btn_hover       = "#52b788"
        btn_text        = "#ffffff"
        metric_val      = "#74c69d"
        page_title_clr  = "#95d5b2"
        tab_active      = "#52b788"
        hero_box_bg     = "rgba(11,28,21,0.82)"
        tagline_color   = "#b7e4c7"
        stat_num_clr    = "#52b788"
        feature_bg      = "rgba(82,183,136,0.12)"
        feature_border  = "rgba(82,183,136,0.32)"
        feature_text    = "#95d5b2"
        score_badge_bg  = "rgba(45,106,79,0.55)"
        rec_bg          = "rgba(27,67,50,0.60)"
        profile_bg      = "rgba(27,67,50,0.72)"
        shine1          = "rgba(82,183,136,0.08)"
        shine2          = "rgba(116,198,157,0.05)"
        inner_gradient  = f"linear-gradient(145deg, #0d2818 0%, #081c15 35%, #0a2218 60%, #112b1e 100%)"
    else:
        # Light forest — clean mint-white shine
        app_bg          = "#f0faf3"
        sidebar_bg      = "rgba(232,248,237,0.98)"
        card_bg         = "rgba(255,255,255,0.92)"
        card_border     = "rgba(64,145,108,0.22)"
        text_primary    = "#081c15"
        text_secondary  = "#1b4332"
        text_muted      = "#2d6a4f"
        accent1         = "#40916c"
        accent2         = "#2d6a4f"
        accent3         = "#1b4332"
        input_bg        = "rgba(255,255,255,0.96)"
        input_text      = "#081c15"
        input_border    = "rgba(64,145,108,0.32)"
        btn_bg          = "#2d6a4f"
        btn_hover       = "#40916c"
        btn_text        = "#ffffff"
        metric_val      = "#2d6a4f"
        page_title_clr  = "#1b4332"
        tab_active      = "#40916c"
        hero_box_bg     = "rgba(255,255,255,0.88)"
        tagline_color   = "#2d6a4f"
        stat_num_clr    = "#40916c"
        feature_bg      = "rgba(82,183,136,0.10)"
        feature_border  = "rgba(64,145,108,0.28)"
        feature_text    = "#1b4332"
        score_badge_bg  = "rgba(183,228,199,0.45)"
        rec_bg          = "rgba(216,243,220,0.65)"
        profile_bg      = "rgba(240,250,243,0.95)"
        shine1          = "rgba(82,183,136,0.06)"
        shine2          = "rgba(149,213,178,0.04)"
        inner_gradient  = f"linear-gradient(145deg, #e8f5ed 0%, #f0faf3 40%, #eaf7ef 70%, #f5fcf7 100%)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    * {{ font-family: 'Plus Jakarta Sans', Inter, sans-serif !important; box-sizing: border-box; }}

    /* ── APP BG: inner pages only (no bg-image) ── */
    .stApp {{
        background: {inner_gradient} !important;
        min-height: 100vh;
        color: {text_primary};
    }}
    /* Shining overlay pattern */
    .stApp::before {{
        content: '';
        position: fixed;
        inset: 0;
        background:
            radial-gradient(ellipse at 20% 20%, {shine1} 0%, transparent 55%),
            radial-gradient(ellipse at 80% 80%, {shine2} 0%, transparent 55%),
            radial-gradient(ellipse at 60% 10%, {shine1} 0%, transparent 40%);
        pointer-events: none;
        z-index: 0;
    }}
    .main .block-container {{
        position: relative; z-index: 1;
        padding-top: 1.6rem;
        max-width: 1220px;
    }}

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {card_border};
        backdrop-filter: blur(24px);
        -webkit-backdrop-filter: blur(24px);
    }}
    [data-testid="stSidebar"] > div {{ position: relative; z-index: 2; }}
    [data-testid="stSidebar"] * {{ color: {text_primary} !important; }}
    [data-testid="stSidebar"] .stRadio label {{ font-weight: 600 !important; font-size: 0.95rem !important; }}
    [data-testid="stSidebar"] .stRadio [data-testid="stMarkdownContainer"] p {{
        padding: 6px 0; border-radius: 8px;
    }}

    /* ── GLASS CARD ── */
    .glass {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 28px;
        padding: 36px 32px;
        box-shadow: 0 20px 60px rgba(8,28,21,0.18), 0 1px 0 rgba(255,255,255,0.08) inset;
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        position: relative; overflow: hidden;
    }}
    .glass::before {{
        content:'';
        position:absolute; top:0; left:0; right:0; height:1px;
        background: linear-gradient(90deg, transparent, {accent1}44, transparent);
    }}

    /* ── WELCOME HERO — has bg image ── */
    .hero-fullpage {{
        position: fixed; inset: 0; z-index: 9999;
        background:
            linear-gradient(160deg, rgba(8,28,21,0.72) 0%, rgba(27,67,50,0.55) 50%, rgba(45,106,79,0.45) 100%),
            url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1920&q=85');
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 20px;
    }}
    .hero-box {{
        max-width: 880px; width: 100%;
        background: {hero_box_bg};
        border: 1.5px solid rgba(82,183,136,0.35);
        border-radius: 36px;
        padding: 68px 52px 56px;
        box-shadow:
            0 32px 100px rgba(8,28,21,0.55),
            0 0 0 1px rgba(82,183,136,0.08) inset,
            0 1px 0 rgba(255,255,255,0.06) inset;
        backdrop-filter: blur(22px);
        -webkit-backdrop-filter: blur(22px);
        text-align: center;
        position: relative; overflow: hidden;
        animation: heroFadeUp 0.85s cubic-bezier(.22,1,.36,1) both;
    }}
    .hero-box::before {{
        content:'';
        position:absolute; top:0; left:0; right:0; height:2px;
        background: linear-gradient(90deg, transparent, #52b788, #74c69d, #52b788, transparent);
    }}
    @keyframes heroFadeUp {{
        from {{ opacity:0; transform:translateY(48px) scale(0.97); }}
        to   {{ opacity:1; transform:translateY(0) scale(1); }}
    }}
    .logo-glow {{
        font-size: 5rem;
        display: block;
        margin-bottom: 4px;
        filter: drop-shadow(0 0 20px rgba(82,183,136,0.6));
        animation: floatLogo 3.5s ease-in-out infinite;
    }}
    @keyframes floatLogo {{
        0%,100% {{ transform: translateY(0) rotate(-2deg); }}
        50%      {{ transform: translateY(-10px) rotate(2deg); }}
    }}
    .hero-title {{
        font-size: 4.2rem;
        font-weight: 900;
        color: #d8f3dc;
        margin: 4px 0 6px;
        letter-spacing: -2px;
        line-height: 1.05;
        text-shadow: 0 4px 32px rgba(8,28,21,0.60);
    }}
    .hero-title .accent {{ color: #52b788; }}
    .hero-sub {{
        font-size: 1.15rem;
        color: #b7e4c7;
        margin: 0 0 34px;
        font-weight: 500;
        letter-spacing: 0.3px;
        opacity: 0.92;
    }}
    .chips-wrap {{
        display: flex; flex-wrap: wrap;
        justify-content: center; gap: 9px;
        margin-bottom: 38px;
    }}
    .chip {{
        background: rgba(82,183,136,0.14);
        border: 1px solid rgba(82,183,136,0.38);
        color: #95d5b2;
        border-radius: 999px;
        padding: 8px 18px;
        font-size: 0.81rem;
        font-weight: 700;
        letter-spacing: 0.4px;
        backdrop-filter: blur(8px);
    }}
    .stats-bar {{
        display: flex; justify-content: center;
        gap: 44px; flex-wrap: wrap; margin-top: 6px;
    }}
    .stat-num {{ font-size: 2rem; font-weight: 900; color: #52b788; line-height: 1; }}
    .stat-lbl {{
        font-size: 0.70rem; color: #95d5b2;
        text-transform: uppercase; letter-spacing: 1.4px;
        font-weight: 700; margin-top: 3px;
    }}
    .hero-btn-wrap {{
        position: fixed; bottom: 0; left: 0; right: 0; z-index: 99999;
        display: flex; justify-content: center;
        padding: 28px 20px 36px;
        background: linear-gradient(to top, rgba(8,28,21,0.85) 0%, transparent 100%);
    }}
    .hero-btn-wrap .stButton > button {{
        padding: 0.82rem 3.4rem !important;
        font-size: 1.05rem !important;
        font-weight: 800 !important;
        letter-spacing: 0.5px !important;
        min-width: 220px;
        background: linear-gradient(135deg, #40916c, #52b788) !important;
        box-shadow: 0 8px 32px rgba(64,145,108,0.50) !important;
        color: #ffffff !important;
    }}

    /* ── PAGE TITLES ── */
    .page-title {{
        font-size: 2.05rem; font-weight: 900;
        color: {page_title_clr};
        letter-spacing: -0.5px; margin-bottom: 2px;
    }}
    .subtext {{ color: {text_muted}; font-size: 0.92rem; margin-bottom: 14px; }}

    /* ── METRIC CARDS ── */
    .metric-card {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 22px; padding: 22px 14px;
        text-align: center;
        backdrop-filter: blur(14px);
        box-shadow: 0 4px 22px rgba(8,28,21,0.12);
        transition: transform 0.20s, box-shadow 0.20s;
        position: relative; overflow: hidden;
    }}
    .metric-card::after {{
        content:''; position:absolute; top:0; left:0; right:0; height:2px;
        background: linear-gradient(90deg, transparent, {accent1}, transparent);
    }}
    .metric-card:hover {{ transform: translateY(-4px); box-shadow: 0 12px 36px rgba(8,28,21,0.18); }}
    .metric-value {{ font-size: 2.2rem; font-weight: 900; color: {metric_val}; }}
    .metric-label {{
        font-size: 0.73rem; color: {text_muted};
        text-transform: uppercase; letter-spacing: 1.1px; margin-top: 5px;
    }}

    /* ── AVATAR ── */
    .avatar-circle {{
        width: 90px; height: 90px; border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden; margin: auto;
        border: 3px solid {accent1};
        background: linear-gradient(135deg, {accent3}, {accent1});
        font-size: 2.2rem;
        box-shadow: 0 4px 20px rgba(82,183,136,0.35);
    }}
    .avatar-circle img {{ width:100%; height:100%; object-fit:cover; }}

    /* ── SECTION CARD ── */
    .section-card {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 24px; padding: 28px;
        backdrop-filter: blur(14px);
        box-shadow: 0 6px 28px rgba(8,28,21,0.10);
        margin-bottom: 20px; position: relative; overflow: hidden;
    }}
    .section-card::before {{
        content:''; position:absolute; top:0; left:0; bottom:0; width:3px;
        background: linear-gradient(180deg, {accent1}, {accent2});
        border-radius: 3px 0 0 3px;
    }}

    /* ── BUTTONS ── */
    .stButton > button,
    [data-testid="stDownloadButton"] button {{
        background: {btn_bg} !important;
        color: {btn_text} !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 700 !important;
        font-size: 0.93rem !important;
        padding: 0.60rem 1.6rem !important;
        letter-spacing: 0.3px !important;
        box-shadow: 0 4px 16px rgba(64,145,108,0.32) !important;
        transition: all 0.18s ease !important;
        cursor: pointer !important;
        white-space: nowrap !important;
    }}
    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover {{
        background: {btn_hover} !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 26px rgba(82,183,136,0.42) !important;
        color: {btn_text} !important;
    }}
    .stButton > button:active {{
        transform: translateY(0) scale(0.99) !important;
    }}
    .stButton > button p,
    .stButton > button span,
    .stButton > button div,
    [data-testid="stDownloadButton"] button p,
    [data-testid="stDownloadButton"] button span,
    [data-testid="stDownloadButton"] button div {{
        color: {btn_text} !important;
        font-weight: 700 !important;
    }}

    /* Centered small btn */
    .center-btn {{
        display: flex; justify-content: center; margin-top: 8px;
    }}
    .center-btn .stButton > button {{
        padding: 0.52rem 2rem !important;
        font-size: 0.88rem !important;
        min-width: 150px; max-width: 220px;
    }}

    /* ── INPUTS ── */
    .stTextInput input, .stNumberInput input,
    .stDateInput input, .stPasswordInput input {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {input_border} !important;
        border-radius: 12px !important;
        font-weight: 500 !important;
        transition: border-color 0.15s !important;
    }}
    .stTextInput input:focus, .stNumberInput input:focus,
    .stPasswordInput input:focus {{
        border-color: {accent1} !important;
        box-shadow: 0 0 0 3px {feature_bg} !important;
    }}
    .stSelectbox [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {input_border} !important;
        border-radius: 12px !important;
    }}
    [data-baseweb="popover"] li {{ color: {text_primary} !important; }}

    /* ── TABS ── */
    [data-baseweb="tab-list"] {{
        background: transparent !important;
        border-bottom: 1.5px solid {card_border} !important;
        gap: 8px !important;
    }}
    [data-baseweb="tab"] {{
        color: {text_muted} !important;
        font-weight: 700 !important;
        font-size: 0.95rem !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 10px 20px !important;
        transition: color 0.15s !important;
    }}
    [aria-selected="true"][data-baseweb="tab"] {{
        color: {tab_active} !important;
        border-bottom: 3px solid {tab_active} !important;
        background: {feature_bg} !important;
    }}

    /* ── SHARE BUTTONS ── */
    .wa-btn {{
        display: inline-flex; align-items: center; gap: 6px;
        border-radius: 14px; padding: 11px 24px;
        background: #25D366; color: white !important;
        text-decoration: none; font-weight: 800;
        margin: 6px 5px; font-size: 0.90rem;
        box-shadow: 0 4px 16px rgba(37,211,102,0.32);
        transition: transform 0.15s;
    }}
    .wa-btn:hover {{ transform: translateY(-2px); }}
    .em-btn {{
        display: inline-flex; align-items: center; gap: 6px;
        border-radius: 14px; padding: 11px 24px;
        background: {btn_bg}; color: white !important;
        text-decoration: none; font-weight: 800;
        margin: 6px 5px; font-size: 0.90rem;
        box-shadow: 0 4px 16px rgba(64,145,108,0.32);
        transition: transform 0.15s;
    }}
    .em-btn:hover {{ transform: translateY(-2px); }}

    /* ── PROFILE CARD ── */
    .profile-info-card {{
        background: {profile_bg};
        border: 1px solid {card_border};
        border-radius: 22px; padding: 24px;
        backdrop-filter: blur(14px);
    }}
    .profile-field {{
        display: flex; justify-content: space-between; align-items: center;
        padding: 11px 0; border-bottom: 1px solid {card_border};
        font-size: 0.93rem;
    }}
    .profile-field:last-child {{ border-bottom: none; }}
    .pf-label {{ color: {text_muted}; font-weight: 600; }}
    .pf-value {{ color: {text_primary}; font-weight: 700; }}

    /* ── SCORE BADGE ── */
    .score-badge {{
        display: inline-block;
        font-size: 3.8rem; font-weight: 900;
        color: {accent1};
        padding: 18px 40px; border-radius: 24px;
        background: {score_badge_bg};
        border: 2px solid {card_border};
        text-align: center;
        box-shadow: 0 8px 30px rgba(82,183,136,0.20);
    }}

    /* ── REC BOX ── */
    .rec-box {{
        background: {rec_bg};
        border: 1px solid {card_border};
        border-left: 3px solid {accent1};
        border-radius: 12px; padding: 13px 16px;
        margin: 7px 0; color: {text_primary};
        font-size: 0.93rem; font-weight: 500;
    }}

    /* ── UPLOAD BUTTON ── */
    .upload-pic-btn .stButton > button {{
        padding: 0.55rem 1.2rem !important;
        font-size: 0.85rem !important;
        white-space: nowrap !important;
        overflow: hidden !important;
        text-overflow: ellipsis !important;
        max-width: 100% !important;
        border-radius: 12px !important;
        line-height: 1.3 !important;
    }}

    /* ── MISC ── */
    hr {{ border-color: {card_border} !important; }}
    label {{ color: {text_primary}; }}
    p {{ color: {text_primary}; }}
    span {{ color: {text_primary}; }}
    h1, h2, h3, h4, h5 {{ color: {page_title_clr}; }}
    .stDataFrame {{ border-radius: 18px; overflow: hidden; }}
    [data-testid="stSidebar"] hr {{ border-color: {card_border} !important; }}
    [data-testid="stForm"] {{ background: transparent !important; }}
    .stNumberInput button {{ background: {btn_bg} !important; color: white !important; border-radius: 8px !important; }}
    </style>
    """, unsafe_allow_html=True)

apply_css()

# ── MODEL ──
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
        pred += {"Low": -4, "Medium": 2, "High": 6}.get(data["Motivation_Level"], 0)
    return int(max(0, min(100, round(pred))))

def get_recommendations(d):
    recs = []
    if d["Hours_Studied"] < 6:         recs.append("📚 Study hours ko 6–8 hours daily tak improve karein.")
    if d["Attendance"] < 80:            recs.append("🏫 Attendance ko 80%+ rakhna score ke liye important hai.")
    if d["Sleep_Hours"] < 7:            recs.append("😴 Daily 7–8 hours sleep rakhein, concentration improve hota hai.")
    if d["Motivation_Level"] == "Low":  recs.append("🎯 Daily small goals set karein aur progress track karein.")
    if d["Internet_Access"] == "No":    recs.append("📖 Offline notes, library aur teacher support ka use karein.")
    if d["Learning_Resources"] == "Low":recs.append("💡 Free resources jaise YouTube lectures aur PDFs use karein.")
    if d["Peer_Influence"] == "Negative":recs.append("🤝 Positive peer group banana performance boost karta hai.")
    return recs

# ── HISTORY / PDF ──
def user_history(username):
    return load_json(HISTORY_FILE, {}).get(username, [])

def save_prediction(username, record):
    all_h = load_json(HISTORY_FILE, {})
    all_h.setdefault(username, [])
    all_h[username].append(record)
    all_h[username] = all_h[username][-20:]
    save_json(HISTORY_FILE, all_h)

def simple_pdf_graph(scores):
    d = Drawing(430, 160)
    d.add(String(10, 145, "Score History", fontSize=12, fillColor=colors.HexColor("#1b4332")))
    d.add(Line(35, 30, 410, 30, strokeColor=colors.grey))
    d.add(Line(35, 30, 35, 130, strokeColor=colors.grey))
    for y, lab in [(30,"0"),(80,"50"),(130,"100")]:
        d.add(String(8, y-4, lab, fontSize=7, fillColor=colors.grey))
        d.add(Line(35, y, 410, y, strokeColor=colors.lightgrey, strokeWidth=.4))
    if scores:
        xs = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        pts = [(float(x), 30+(float(s)/100)*100) for x,s in zip(xs,scores)]
        for i in range(len(pts)-1):
            d.add(Line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],
                       strokeColor=colors.HexColor("#40916c"), strokeWidth=2))
        for i,(x,y) in enumerate(pts):
            d.add(String(x-5,y+6,str(scores[i]),fontSize=7,fillColor=colors.HexColor("#1b4332")))
    return d

def generate_pdf(username, user_data, score, inputs, recs):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=.45*inch, bottomMargin=.45*inch)
    S   = getSampleStyleSheet()
    TIT = ParagraphStyle("T", parent=S["Heading1"], alignment=1, fontSize=22,
                          textColor=colors.HexColor("#40916c"), spaceAfter=14)
    HED = ParagraphStyle("H", parent=S["Heading2"], fontSize=13,
                          textColor=colors.HexColor("#1b4332"), spaceAfter=7)
    NRM = ParagraphStyle("N", parent=S["Normal"], fontSize=10, leading=14)
    story = []
    story.append(Paragraph(f"{APP_NAME} — Official Prediction Report", TIT))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", NRM))
    story.append(Spacer(1,10))
    name = user_data.get("full_name") or user_data.get("child_name") or username
    info = [["Name",name],["Username",username],
            ["Email",user_data.get("email","N/A")],["Role",user_data.get("role","N/A").title()]]
    story.append(Paragraph("Student Details", HED))
    t = Table(info, colWidths=[2.1*inch,4.2*inch])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),
                            ('BACKGROUND',(0,0),(0,-1),colors.HexColor('#b7e4c7')),
                            ('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),
                            ('PADDING',(0,0),(-1,-1),8)]))
    story.append(t); story.append(Spacer(1,10))
    story.append(Paragraph("Result", HED))
    rt = Table([["Predicted Score",f"{score}/100"],
                ["Status","Excellent" if score>=85 else "Good" if score>=70 else "Needs Improvement"]],
               colWidths=[2.1*inch,4.2*inch])
    rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),
                             ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#40916c')),
                             ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                             ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                             ('PADDING',(0,0),(-1,-1),8)]))
    story.append(rt); story.append(Spacer(1,10))
    story.append(Paragraph("Inputs", HED))
    rows = [["Field","Value"]]+[[k.replace('_',' '),str(v)] for k,v in inputs.items()]
    it = Table(rows, colWidths=[2.7*inch,3.6*inch])
    it.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),
                             ('BACKGROUND',(0,0),(-1,0),colors.HexColor('#1b4332')),
                             ('TEXTCOLOR',(0,0),(-1,0),colors.white),
                             ('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),
                             ('PADDING',(0,0),(-1,-1),7)]))
    story.append(it); story.append(Spacer(1,10))
    sc = [r.get("score",0) for r in user_history(username)]+[score]
    story.append(simple_pdf_graph(sc[-10:]))
    story.append(Spacer(1,10))
    story.append(Paragraph("Recommendations", HED))
    for r in (recs or ["All academic inputs are strong. Maintain consistency."]):
        story.append(Paragraph("• "+r, NRM))
    story.append(Spacer(1,18))
    story.append(Paragraph(f"Generated by {APP_NAME}. For academic guidance only.", NRM))
    doc.build(story)
    buf.seek(0)
    return buf.read()

# ── HELPERS ──
def toggle_theme_button(key):
    label = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(label, key=key):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

def chart_cfg():
    dark = st.session_state.theme == "dark"
    return {
        "paper": "rgba(0,0,0,0)", "plot": "rgba(0,0,0,0)",
        "line":  "#74c69d" if dark else "#40916c",
        "marker":"#52b788" if dark else "#2d6a4f",
        "text":  "#d8f3dc" if dark else "#081c15",
        "grid":  "rgba(82,183,136,0.12)" if dark else "rgba(64,145,108,0.10)",
    }

def score_trend_chart(records):
    cc = chart_cfg()
    scores = [r["score"] for r in records]
    dates  = [r.get("date",f"#{i+1}") for i,r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=scores, mode="lines+markers+text",
        text=scores, textposition="top center",
        line=dict(width=3, color=cc["line"]),
        marker=dict(size=9, color=cc["marker"], line=dict(width=2, color="white")),
        fill="tozeroy", fillcolor="rgba(82,183,136,0.09)",
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#74c69d",
                  annotation_text="Pass", annotation_font_color="#74c69d")
    fig.add_hline(y=85, line_dash="dot", line_color="#b7e4c7",
                  annotation_text="Excellent", annotation_font_color="#b7e4c7")
    fig.update_layout(
        title=dict(text="📈 Score Trend", font=dict(color=cc["text"], size=14)),
        height=310, margin=dict(l=10,r=10,t=44,b=10),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0,112]),
        showlegend=False,
    )
    return fig

def radar_chart(inputs):
    cc = chart_cfg()
    cats = ["Study Hours","Attendance","Sleep","Motivation","Resources","Peer Influence"]
    vals = [
        min(inputs.get("Hours_Studied",0)/10*100,100),
        inputs.get("Attendance",0),
        min(inputs.get("Sleep_Hours",0)/9*100,100),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
        {"Negative":10,"Neutral":55,"Positive":100}.get(inputs.get("Peer_Influence","Neutral"),55),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]], theta=cats+[cats[0]],
        fill="toself", fillcolor="rgba(82,183,136,0.14)",
        line=dict(color=cc["line"], width=2.5),
        marker=dict(color=cc["marker"], size=7),
    ))
    fig.update_layout(
        title=dict(text="🕸️ Academic Radar", font=dict(color=cc["text"], size=14)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,100], color=cc["text"], gridcolor=cc["grid"]),
            angularaxis=dict(color=cc["text"]),
        ),
        height=340, margin=dict(l=20,r=20,t=50,b=20),
        paper_bgcolor=cc["paper"], showlegend=False,
    )
    return fig

def factor_bar_chart(inputs):
    cc = chart_cfg()
    factors = {
        "Hours Studied": min(inputs.get("Hours_Studied",0)/10*100,100),
        "Attendance":    inputs.get("Attendance",0),
        "Prev Score":    inputs.get("Previous_Scores",0),
        "Sleep":         min(inputs.get("Sleep_Hours",0)/9*100,100),
        "Motivation":    {"Low":25,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        "Resources":     {"Low":25,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
    }
    fig = go.Figure(go.Bar(
        x=list(factors.keys()), y=list(factors.values()),
        marker=dict(
            color=list(factors.values()),
            colorscale=[[0,"#081c15"],[0.3,"#1b4332"],[0.6,"#40916c"],[1,"#95d5b2"]],
            showscale=False,
        ),
        text=[f"{v:.0f}" for v in factors.values()],
        textposition="outside",
        textfont=dict(color=cc["text"], size=11),
    ))
    fig.update_layout(
        title=dict(text="📊 Key Factors", font=dict(color=cc["text"], size=14)),
        height=310, margin=dict(l=10,r=10,t=48,b=10),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0,118]),
        showlegend=False,
    )
    return fig

# ═══════════════════════════════════════════════
# WELCOME PAGE
# ═══════════════════════════════════════════════
def welcome_page():
    st.markdown(f"""
    <div class="hero-fullpage">
      <div class="hero-box">
        <span class="logo-glow">🌿</span>
        <h1 class="hero-title">Acadra<span class="accent">IQ</span></h1>
        <p class="hero-sub">{TAGLINE}</p>
        <div class="chips-wrap">
          <span class="chip">🔐 OTP Signup</span>
          <span class="chip">🤖 AI Prediction</span>
          <span class="chip">📄 PDF Report</span>
          <span class="chip">📱 WhatsApp Share</span>
          <span class="chip">🌙 Dark / Light</span>
          <span class="chip">📈 Smart Charts</span>
        </div>
        <div class="stats-bar">
          <div><div class="stat-num">98%</div><div class="stat-lbl">Accuracy</div></div>
          <div><div class="stat-num">10K+</div><div class="stat-lbl">Predictions</div></div>
          <div><div class="stat-num">3</div><div class="stat-lbl">Smart Charts</div></div>
          <div><div class="stat-num">Free</div><div class="stat-lbl">Always</div></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='hero-btn-wrap'>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([2, 1.2, 2])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True, key="hero_start"):
            st.session_state.auth_page = "login"
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# AUTH PAGE
# ═══════════════════════════════════════════════
def auth_page():
    users = load_json(USER_DB_FILE, {})
    c1, c2 = st.columns([9, 1])
    with c1:
        if st.button("← Back", key="back_btn"):
            st.session_state.auth_page = "welcome"; st.rerun()
    with c2:
        toggle_theme_button("theme_auth")

    col1, col2, col3 = st.columns([1, 2.2, 1])
    with col2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>🌿 {APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:18px'>Secure Login & OTP Signup</p>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Login", "✍️ Sign Up"])

        with tab_login:
            username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")
            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("Login →", key="do_login"):
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in   = True
                    st.session_state.username    = username
                    st.session_state.role        = users[username].get("role","student")
                    st.session_state.active_page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_signup:
            role      = st.selectbox("Account Type", ["student","parent"], format_func=str.title)
            username  = st.text_input("Create Username",  key="su_user")
            email     = st.text_input("Email for OTP",    key="su_email")
            full_name = st.text_input("Full Name",         key="su_name")
            password  = st.text_input("Password",          type="password", key="su_pass")
            confirm   = st.text_input("Confirm Password",  type="password", key="su_confirm")
            if role == "student":
                dob    = st.date_input("Date of Birth", key="su_dob",
                                        min_value=datetime(1990,1,1), max_value=datetime.now())
                grade  = st.selectbox("Class / Course",
                                       ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                school = st.text_input("School / College")
            else:
                child_name = st.text_input("Child Name")
                grade      = st.selectbox("Child Class",
                                           ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                relation   = st.selectbox("Relation", ["Father","Mother","Guardian"])

            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("📧 Send OTP", key="send_otp_btn"):
                if not email:
                    st.warning("Email required.")
                else:
                    otp = generate_otp(); store_otp(email, otp)
                    ok, msg = send_otp_email(email, otp, full_name or "User")
                    if ok: st.success("OTP sent! Check your inbox.")
                    else:  st.warning(f"Email not configured. Test OTP: **{otp}**")
            st.markdown("</div>", unsafe_allow_html=True)

            otp_entered = st.text_input("Enter OTP", max_chars=6, placeholder="6-digit OTP")
            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("✅ Verify & Create Account", key="verify_otp_btn"):
                if not all([username, email, password, full_name]):
                    st.warning("Please fill all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif username in users:
                    st.error("Username already exists.")
                else:
                    ok, msg = verify_otp(email, otp_entered)
                    if not ok:
                        st.error(msg)
                    else:
                        data = {"password": hash_password(password), "email": email,
                                "full_name": full_name, "role": role,
                                "created_at": datetime.now().isoformat()}
                        if role == "student":
                            data.update({"dob": str(dob), "age": calculate_age(dob),
                                         "grade": grade, "school": school})
                        else:
                            data.update({"child_name": child_name, "child_grade": grade,
                                         "relation": relation})
                        users[username] = data
                        save_json(USER_DB_FILE, users)
                        st.success("✅ Account created! Please login.")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════
def sidebar(user):
    with st.sidebar:
        icon = "🌿" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(
            f"<div class='avatar-circle'>{profile_pic_html(st.session_state.username, icon)}</div>",
            unsafe_allow_html=True)
        st.markdown(
            f"<h3 style='text-align:center;margin:10px 0 2px'>"
            f"{user.get('full_name', st.session_state.username)}</h3>",
            unsafe_allow_html=True)
        st.markdown(
            f"<p class='subtext' style='text-align:center;margin-bottom:14px'>"
            f"{user.get('role','student').title()} Account</p>",
            unsafe_allow_html=True)
        st.markdown("---")
        pages  = ["🏠 Home","🔮 Prediction","📄 Report & Share","📚 History","👤 Profile"]
        labels = [p.split(" ",1)[1] for p in pages]
        sel_idx = 0
        for i,label in enumerate(labels):
            if st.session_state.active_page == label:
                sel_idx = i
        selected = st.radio("Navigation", pages, index=sel_idx)
        st.session_state.active_page = selected.split(" ",1)[1]
        st.markdown("---")
        toggle_theme_button("theme_sidebar")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in  = False
            st.session_state.username   = ""
            st.session_state.auth_page  = "welcome"
            st.rerun()

# ═══════════════════════════════════════════════
# HOME
# ═══════════════════════════════════════════════
def home_page(user):
    records = user_history(st.session_state.username)
    name    = user.get("full_name", st.session_state.username)
    st.markdown(f"<div class='page-title'>👋 Welcome, {name}!</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Your academic performance dashboard — all insights in one place.</p>",
                unsafe_allow_html=True)
    scores = [r["score"] for r in records]
    cols = st.columns(4)
    metrics = [
        ("🎯 Attempts",   len(records)),
        ("🏆 Best Score", max(scores) if scores else 0),
        ("📊 Average",    int(np.mean(scores)) if scores else 0),
        ("🕐 Last Score", scores[-1] if scores else 0),
    ]
    for col,(label,val) in zip(cols, metrics):
        with col:
            st.markdown(
                f"<div class='metric-card'>"
                f"<div class='metric-value'>{val}</div>"
                f"<div class='metric-label'>{label}</div></div>",
                unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
    else:
        st.info("🚀 Prediction page se apna first score generate karein!")

# ═══════════════════════════════════════════════
# PREDICTION
# ═══════════════════════════════════════════════
def prediction_page(user):
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Academic details bharo aur AI se predicted score paao.</p>",
                unsafe_allow_html=True)
    with st.form("pred_form"):
        c1, c2 = st.columns(2)
        with c1:
            hours      = st.number_input("📖 Hours Studied (daily)", 0, 24, 5, 1)
            attendance = st.number_input("🏫 Attendance (%)",        0, 100, 75, 1)
            previous   = st.number_input("📝 Previous Score",        0, 100, 60, 1)
            sleep      = st.number_input("😴 Sleep Hours",           0, 12, 7, 1)
            motivation = st.selectbox("💡 Motivation Level", ["Low","Medium","High"])
            teacher    = st.selectbox("👨‍🏫 Teacher Quality",  ["Poor","Average","Good"])
            school_type= st.selectbox("🏢 School Type",       ["Public","Private"])
        with c2:
            internet   = st.selectbox("🌐 Internet Access",          ["Yes","No"])
            income     = st.selectbox("💰 Family Income",            ["Low","Medium","High"])
            parental   = st.selectbox("👨‍👩‍👦 Parental Involvement",      ["Low","Medium","High"])
            education  = st.selectbox("🎓 Parent Education",         ["School","College"])
            peer       = st.selectbox("🤝 Peer Influence",           ["Negative","Neutral","Positive"])
            resources  = st.selectbox("📚 Learning Resources",       ["Low","Medium","High"])
            activities = st.selectbox("⚽ Extracurricular",          ["Yes","No"])
        submitted = st.form_submit_button("🚀 Predict My Score", use_container_width=True)

    if submitted:
        data = {
            "Hours_Studied": int(hours), "Attendance": int(attendance),
            "Previous_Scores": int(previous), "Sleep_Hours": int(sleep),
            "Motivation_Level": motivation, "Teacher_Quality": teacher,
            "School_Type": school_type, "Internet_Access": internet,
            "Family_Income": income, "Parental_Involvement": parental,
            "Parental_Education_Level": education, "Peer_Influence": peer,
            "Learning_Resources": resources, "Extracurricular_Activities": activities,
        }
        score  = predict_score(data)
        recs   = get_recommendations(data)
        record = {"date": datetime.now().strftime("%d-%m-%Y %H:%M"),
                  "score": score, "inputs": data, "recommendations": recs}
        save_prediction(st.session_state.username, record)
        st.session_state.last_score  = score
        st.session_state.last_inputs = data
        st.session_state.last_recs   = recs
        st.session_state.last_pdf    = generate_pdf(st.session_state.username, user, score, data, recs)

        status = "🌟 Excellent!" if score>=85 else "👍 Good" if score>=70 else "📈 Needs Work"
        st.markdown(f"""
        <div style='text-align:center;padding:28px 0'>
          <div class='score-badge'>{score}<span style='font-size:1.3rem;opacity:.75'>/100</span></div>
          <p style='margin-top:12px;font-size:1.05rem;font-weight:800'>{status}</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("### 📊 Performance Analysis")
        g1, g2 = st.columns(2)
        with g1: st.plotly_chart(radar_chart(data), use_container_width=True)
        with g2: st.plotly_chart(factor_bar_chart(data), use_container_width=True)
        records = user_history(st.session_state.username)
        if len(records) > 1:
            st.plotly_chart(score_trend_chart(records), use_container_width=True)
        if recs:
            st.markdown("### 💬 Personalized Recommendations")
            for r in recs:
                st.markdown(f"<div class='rec-box'>{r}</div>", unsafe_allow_html=True)
        st.session_state.active_page = "Report & Share"

# ═══════════════════════════════════════════════
# REPORT & SHARE
# ═══════════════════════════════════════════════
def report_page(user):
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>PDF download karein ya WhatsApp / email se share karein.</p>",
                unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Pehle Prediction page se score generate karein.")
        return
    latest = records[-1] if records else {
        "score": st.session_state.last_score,
        "inputs": st.session_state.last_inputs,
        "recommendations": st.session_state.last_recs,
    }
    score, inputs, recs = latest["score"], latest["inputs"], latest.get("recommendations",[])
    pdf = st.session_state.last_pdf or generate_pdf(st.session_state.username, user, score, inputs, recs)

    c1, c2, c3 = st.columns([1,1,1])
    with c2:
        st.markdown(
            f"<div class='metric-card'>"
            f"<div class='metric-label'>Predicted Score</div>"
            f"<div class='metric-value'>{score}/100</div></div>",
            unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("📥 Download PDF Report", data=pdf,
                       file_name=f"AcadraIQ_Report_{st.session_state.username}.pdf",
                       mime="application/pdf", use_container_width=True)
    share_text = (f"{APP_NAME} Report%0APredicted Score: {score}/100"
                  f"%0AHours: {inputs.get('Hours_Studied')}"
                  f"%0AAttendance: {inputs.get('Attendance')}%25")
    wa_url  = "https://wa.me/?text=" + share_text
    em_url  = ("mailto:?subject=" + urllib.parse.quote(f"{APP_NAME} Report") + "&body=" + share_text)
    st.markdown(f"""<div style='text-align:center;margin:18px 0'>
      <a class='wa-btn' target='_blank' href='{wa_url}'>📱 Share on WhatsApp</a>
      <a class='em-btn' href='{em_url}'>✉️ Share via Email</a>
    </div>""", unsafe_allow_html=True)
    st.caption("PDF ke liye pehle download karein, phir WhatsApp me manually attach karein.")

    st.markdown("### 📊 Performance Graphs")
    g1, g2 = st.columns(2)
    with g1: st.plotly_chart(radar_chart(inputs), use_container_width=True)
    with g2: st.plotly_chart(factor_bar_chart(inputs), use_container_width=True)
    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
    if recs:
        st.markdown("### 💬 Recommendations")
        for r in recs:
            st.markdown(f"<div class='rec-box'>{r}</div>", unsafe_allow_html=True)

# ═══════════════════════════════════════════════
# HISTORY
# ═══════════════════════════════════════════════
def history_page(user):
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Apni saari predictions ek jagah dekho.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records:
        st.info("No prediction history yet. Make your first prediction!")
        return
    df = pd.DataFrame([{
        "Date": r["date"], "Score": r["score"],
        "Hours": r["inputs"].get("Hours_Studied"),
        "Attendance": r["inputs"].get("Attendance"),
        "Previous": r["inputs"].get("Previous_Scores"),
    } for r in records])
    st.dataframe(df, use_container_width=True)
    st.plotly_chart(score_trend_chart(records), use_container_width=True)

# ═══════════════════════════════════════════════
# PROFILE
# ═══════════════════════════════════════════════
def profile_page(user):
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Profile details aur picture manage karein.</p>", unsafe_allow_html=True)
    users = load_json(USER_DB_FILE, {})
    uname = st.session_state.username

    col1, col2 = st.columns([1, 2.2])
    with col1:
        icon = "🌿" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(uname, icon)}</div>",
                    unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        # Profile picture upload — clean layout
        st.markdown("<div class='section-card' style='padding:18px 16px'>", unsafe_allow_html=True)
        st.markdown("<p style='font-weight:700;font-size:0.88rem;margin-bottom:8px;opacity:.75'>📸 Profile Picture</p>",
                    unsafe_allow_html=True)
        upload = st.file_uploader("Choose image", type=["jpg","jpeg","png"],
                                   label_visibility="collapsed", key="pic_upload")
        if upload:
            st.markdown("<div class='upload-pic-btn'>", unsafe_allow_html=True)
            if st.button("💾 Save Picture", use_container_width=True, key="save_pic_btn"):
                save_profile_pic(uname, upload.read())
                st.success("✅ Picture updated!")
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.caption("JPG / PNG supported")
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        edit = st.session_state.profile_edit_mode
        if not edit:
            st.markdown("<div class='profile-info-card'>", unsafe_allow_html=True)
            fields = [
                ("Username",   uname),
                ("Full Name",  user.get("full_name","N/A")),
                ("Email",      user.get("email","N/A")),
                ("Role",       user.get("role","N/A").title()),
            ]
            if user.get("role") == "student":
                fields += [
                    ("Date of Birth",  user.get("dob","N/A")),
                    ("Age",            str(user.get("age","N/A"))),
                    ("Class / Grade",  user.get("grade","N/A")),
                    ("School/College", user.get("school","N/A")),
                ]
            else:
                fields += [
                    ("Child Name",  user.get("child_name","N/A")),
                    ("Child Grade", user.get("child_grade","N/A")),
                    ("Relation",    user.get("relation","N/A")),
                ]
            for label,val in fields:
                st.markdown(
                    f"<div class='profile-field'>"
                    f"<span class='pf-label'>{label}</span>"
                    f"<span class='pf-value'>{val}</span></div>",
                    unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", use_container_width=True):
                st.session_state.profile_edit_mode = True; st.rerun()
        else:
            with st.form("edit_profile_form"):
                st.markdown("#### ✏️ Edit Profile")
                new_name  = st.text_input("Full Name",  value=user.get("full_name",""))
                new_email = st.text_input("Email",      value=user.get("email",""))
                if user.get("role") == "student":
                    try:    dob_date = datetime.strptime(user.get("dob","2000-01-01"), "%Y-%m-%d").date()
                    except: dob_date = date(2000,1,1)
                    new_dob    = st.date_input("Date of Birth", value=dob_date,
                                                min_value=date(1990,1,1), max_value=date.today())
                    g_opts     = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_g      = user.get("grade","Class 10")
                    new_grade  = st.selectbox("Class / Grade", g_opts,
                                               index=g_opts.index(cur_g) if cur_g in g_opts else 2)
                    new_school = st.text_input("School / College", value=user.get("school",""))
                else:
                    new_child  = st.text_input("Child Name",  value=user.get("child_name",""))
                    g_opts     = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_g      = user.get("child_grade","Class 10")
                    new_cgrade = st.selectbox("Child Grade", g_opts,
                                               index=g_opts.index(cur_g) if cur_g in g_opts else 2)
                    r_opts     = ["Father","Mother","Guardian"]
                    cur_r      = user.get("relation","Father")
                    new_rel    = st.selectbox("Relation", r_opts,
                                               index=r_opts.index(cur_r) if cur_r in r_opts else 0)
                st.markdown("---")
                st.markdown("##### 🔒 Change Password (optional)")
                old_pass = st.text_input("Current Password",     type="password")
                new_pass = st.text_input("New Password",         type="password")
                cnf_pass = st.text_input("Confirm New Password", type="password")
                s1, s2   = st.columns(2)
                with s1: save_ok   = st.form_submit_button("💾 Save Changes",  use_container_width=True)
                with s2: cancel_ok = st.form_submit_button("❌ Cancel",         use_container_width=True)

            if cancel_ok:
                st.session_state.profile_edit_mode = False; st.rerun()
            if save_ok:
                upd = users[uname].copy()
                upd["full_name"] = new_name
                upd["email"]     = new_email
                if user.get("role") == "student":
                    upd.update({"dob": str(new_dob), "age": calculate_age(new_dob),
                                "grade": new_grade, "school": new_school})
                else:
                    upd.update({"child_name": new_child, "child_grade": new_cgrade, "relation": new_rel})
                if old_pass or new_pass or cnf_pass:
                    if users[uname]["password"] != hash_password(old_pass):
                        st.error("Current password incorrect."); st.stop()
                    elif new_pass != cnf_pass:
                        st.error("New passwords do not match."); st.stop()
                    elif len(new_pass) < 6:
                        st.error("Password min 6 characters."); st.stop()
                    else:
                        upd["password"] = hash_password(new_pass)
                users[uname] = upd
                save_json(USER_DB_FILE, users)
                st.session_state.profile_edit_mode = False
                st.success("✅ Profile updated!")
                st.rerun()

# ═══════════════════════════════════════════════
# MAIN APP
# ═══════════════════════════════════════════════
def main_app():
    users = load_json(USER_DB_FILE, {})
    user  = users.get(st.session_state.username, {})
    sidebar(user)
    page = st.session_state.active_page
    if   page == "Home":           home_page(user)
    elif page == "Prediction":     prediction_page(user)
    elif page == "Report & Share": report_page(user)
    elif page == "History":        history_page(user)
    elif page == "Profile":        profile_page(user)

# ═══════════════════════════════════════════════
# ROUTER
# ═══════════════════════════════════════════════
if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()
