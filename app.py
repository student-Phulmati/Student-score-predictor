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
import plotly.express as px

# =====================================================
# APP CONFIG
# =====================================================
APP_NAME = "ScoreWise AI"
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

st.set_page_config(page_title=APP_NAME, page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

# =====================================================
# BASIC STORAGE HELPERS
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
        return f'<img src="data:image/jpeg;base64,{b64}" />'
    return fallback

# =====================================================
# OTP FUNCTIONS
# =====================================================
def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(email, otp):
    data = load_json(OTP_FILE, {})
    data[email] = {"otp": otp, "timestamp": datetime.now().isoformat(), "verified": False}
    save_json(OTP_FILE, data)

def verify_otp(email, entered):
    data = load_json(OTP_FILE, {})
    if email not in data:
        return False, "OTP not found. Please send OTP again."
    saved = data[email]
    seconds = (datetime.now() - datetime.fromisoformat(saved["timestamp"])).total_seconds()
    if seconds > 600:
        return False, "OTP expired. Please send a new OTP."
    if saved["otp"] != entered:
        return False, "Invalid OTP. Please check and try again."
    data[email]["verified"] = True
    save_json(OTP_FILE, data)
    return True, "OTP verified successfully."

def send_otp_email(receiver, otp, name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME} OTP"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver
        html = f"""
        <div style='font-family:Arial;background:#184e77;color:white;padding:26px;border-radius:18px'>
          <h2 style='color:#d9ed92'>{APP_NAME}</h2>
          <p>Hello <b>{name}</b>, your signup OTP is:</p>
          <div style='font-size:34px;letter-spacing:8px;font-weight:800;color:#99d98c'>{otp}</div>
          <p>This OTP is valid for 10 minutes.</p>
        </div>
        """
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver, msg.as_string())
        return True, "OTP sent to email."
    except Exception as e:
        return False, str(e)

# =====================================================
# SESSION STATE
# =====================================================
def init_state():
    defaults = {
        "logged_in": False,
        "username": "",
        "role": "",
        "auth_page": "welcome",
        "theme": "dark",
        "active_page": "Home",
        "last_score": None,
        "last_pdf": None,
        "last_inputs": {},
        "last_recs": [],
        "show_pic_uploader": False,
        "profile_edit_mode": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# COLOR PALETTE (from coolors.co)
# Dark mode  : bg=#07111f, card=rgba(24,78,119,.82), accents from palette
# Light mode : bg=#f0faf5, card=rgba(255,255,255,.90), accents from palette
# Palette: #d9ed92 #b5e48c #99d98c #76c893 #52b69a #34a0a4 #168aad #1a759f #1e6091 #184e77
# =====================================================
def apply_css():
    dark = st.session_state.theme == "dark"
    is_welcome = (not st.session_state.logged_in and st.session_state.auth_page == "welcome")

    if dark:
        app_gradient = "linear-gradient(135deg,#03045e 0%,#023e8a 35%,#0077b6 70%,#00b4d8 100%)"
        text_primary  = "#F8FCFF"
        text_secondary= "#D9F7FF"
        text_muted    = "#ADE8F4"
        border_color  = "rgba(144,224,239,0.24)"
        input_bg      = "rgba(255,255,255,0.12)"
        input_text    = "#FFFFFF"
        card_bg       = "rgba(2,18,54,0.72)"
        soft_card_bg  = "rgba(255,255,255,0.08)"
        sidebar_bg    = "rgba(3,4,94,0.88)"
        shadow        = "0 22px 70px rgba(0,0,0,0.38)"
    else:
        app_gradient = "linear-gradient(135deg,#caf0f8 0%,#ade8f4 35%,#90e0ef 70%,#48cae4 100%)"
        text_primary  = "#03045e"
        text_secondary= "#023e8a"
        text_muted    = "#0077b6"
        border_color  = "rgba(2,62,138,0.20)"
        input_bg      = "rgba(255,255,255,0.88)"
        input_text    = "#03045e"
        card_bg       = "rgba(255,255,255,0.72)"
        soft_card_bg  = "rgba(255,255,255,0.55)"
        sidebar_bg    = "rgba(255,255,255,0.78)"
        shadow        = "0 20px 60px rgba(2,62,138,0.22)"

    welcome_img = "https://images.unsplash.com/photo-1524995997946-a1c2e315a42f?auto=format&fit=crop&w=1900&q=85"
    if is_welcome:
        app_background = f"linear-gradient(90deg,rgba(1,8,35,0.95),rgba(3,37,83,0.88),rgba(5,22,54,0.70)), url('{welcome_img}')"
        background_extra = "background-size: cover; background-position: center; background-attachment: fixed;"
        block_padding = "0.75rem 2.2rem 0.6rem 2.2rem"
    else:
        app_background = app_gradient
        background_extra = "background-size: 220% 220%; animation: shineBg 12s ease infinite;"
        block_padding = "1.35rem 2rem 2rem 2rem"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    * {{
        font-family: Inter, sans-serif !important;
        box-sizing: border-box;
    }}

    html, body, .stApp {{
        color: {text_primary};
    }}

    .stApp {{
        background: {app_background};
        {background_extra}
    }}

    @keyframes shineBg {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    .main .block-container {{
        padding: {block_padding};
        max-width: 1240px;
    }}

    [data-testid="stDecoration"],
    #MainMenu,
    footer,
    header {{
        visibility: hidden;
        height: 0;
    }}

    /* Fixed emoji theme button */
    .theme-fixed {{
        position: fixed;
        top: 18px;
        right: 22px;
        z-index: 99999;
        width: 84px;
        height: 48px;
        border-radius: 24px;
        background: rgba(255,255,255,0.12);
        border: 1px solid rgba(255,255,255,0.32);
        backdrop-filter: blur(16px);
        box-shadow: 0 10px 28px rgba(0,0,0,0.25);
        pointer-events: none;
    }}
    div[data-testid="stButton"] button[kind="secondary"] {{
        cursor: pointer !important;
    }}
    .fixed-theme-holder {{
        position: fixed;
        top: 18px;
        right: 22px;
        z-index: 100000;
        width: 84px;
    }}
    .fixed-theme-holder .stButton > button {{
        width: 84px !important;
        height: 48px !important;
        border-radius: 24px !important;
        padding: 0 !important;
        font-size: 1.35rem !important;
        background: rgba(255,255,255,0.12) !important;
        border: 1px solid rgba(255,255,255,0.32) !important;
        color: #fff !important;
        box-shadow: 0 10px 28px rgba(0,0,0,0.25) !important;
        backdrop-filter: blur(16px) !important;
    }}

    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_color};
        backdrop-filter: blur(24px);
    }}
    [data-testid="stSidebar"] * {{
        color: {text_primary} !important;
    }}

    .glass,
    .metric-card,
    .profile-info-card,
    .score-badge {{
        background: {card_bg};
        border: 1px solid {border_color};
        box-shadow: {shadow};
        backdrop-filter: blur(22px);
    }}

    .glass {{
        border-radius: 26px;
        padding: 28px;
    }}

    /* Welcome page fixed one-screen layout */
    .welcome-fixed {{
        height: calc(100vh - 30px);
        min-height: 660px;
        max-height: 900px;
        overflow: hidden;
        position: relative;
        display: flex;
        flex-direction: column;
        justify-content: center;
        gap: 20px;
    }}

    .welcome-top {{
        display: grid;
        grid-template-columns: 240px 1fr;
        align-items: center;
        gap: 28px;
        margin-bottom: 4px;
    }}

    .cap-icon {{
        width: 190px;
        height: 150px;
        border-radius: 34px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 6.4rem;
        filter: drop-shadow(0 0 22px rgba(255,184,28,0.38));
    }}

    .animated-title {{
        margin: 0;
        font-size: clamp(3.2rem, 6vw, 5.4rem);
        line-height: 0.95;
        font-weight: 900;
        letter-spacing: -2px;
        color: #ffffff;
        text-shadow: 0 10px 36px rgba(0,0,0,0.45);
    }}
    .animated-title span {{
        background: linear-gradient(90deg,#ffffff,#90e0ef,#48cae4,#9b5cff);
        background-size: 240% auto;
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        animation: titleShine 5s linear infinite;
    }}
    @keyframes titleShine {{
        0% {{ background-position: 0% center; }}
        100% {{ background-position: 240% center; }}
    }}
    .welcome-subtitle {{
        margin-top: 14px;
        color: #EAFBFF;
        font-size: 1.32rem;
        font-weight: 700;
        text-shadow: 0 6px 18px rgba(0,0,0,0.35);
    }}

    .feature-row {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 28px;
        align-items: stretch;
    }}
    .welcome-card {{
        min-height: 305px;
        border-radius: 28px;
        padding: 24px 26px;
        background: rgba(1,15,45,0.66);
        border: 2px solid var(--card-color);
        box-shadow: 0 0 0 1px rgba(255,255,255,0.05), 0 22px 55px rgba(0,0,0,0.32), 0 0 24px var(--card-glow);
        backdrop-filter: blur(12px);
        color: white;
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }}
    .welcome-card .icon {{
        width: 96px;
        height: 96px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 3.1rem;
        background: rgba(255,255,255,0.08);
        border: 2px solid rgba(255,255,255,0.16);
        margin-bottom: 15px;
        box-shadow: inset 0 0 26px rgba(255,255,255,0.08);
    }}
    .welcome-card h3 {{
        margin: 4px 0 12px 0;
        color: #ffffff;
        font-size: 1.75rem;
        font-weight: 900;
        text-shadow: 0 5px 15px rgba(0,0,0,0.35);
    }}
    .mini-line {{
        width: 58px;
        height: 4px;
        border-radius: 8px;
        background: var(--card-color);
        margin: 0 auto 16px auto;
        box-shadow: 0 0 14px var(--card-color);
    }}
    .welcome-card ul {{
        width: 100%;
        padding-left: 0;
        margin: 0;
        list-style: none;
        text-align: left;
    }}
    .welcome-card li {{
        color: #F3FAFF;
        font-size: 0.98rem;
        line-height: 1.72;
        font-weight: 650;
        margin: 3px 0;
    }}
    .welcome-card li::before {{
        content: "●";
        color: var(--card-color);
        margin-right: 12px;
        text-shadow: 0 0 10px var(--card-color);
    }}

    .used-title {{
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 18px;
        color: #fff;
        font-weight: 900;
        font-size: 1.25rem;
        margin: 0;
    }}
    .used-title:before, .used-title:after {{
        content: "";
        width: 160px;
        height: 1px;
        background: linear-gradient(90deg,transparent,rgba(255,255,255,0.65),transparent);
    }}
    .used-row {{
        display: grid;
        grid-template-columns: repeat(5, 1fr);
        gap: 14px;
        margin-top: 12px;
    }}
    .used-item {{
        text-align: center;
        color: white;
        padding: 6px 8px;
        border-right: 1px solid rgba(255,255,255,0.20);
    }}
    .used-item:last-child {{ border-right: 0; }}
    .used-icon {{
        font-size: 1.85rem;
        margin-bottom: 4px;
    }}
    .used-name {{
        font-weight: 900;
        font-size: 0.93rem;
    }}
    .used-desc {{
        color: #D7F8FF;
        font-size: 0.79rem;
        line-height: 1.22;
        margin-top: 3px;
        font-weight: 550;
    }}
    .stats-strip {{
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 0;
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(144,224,239,0.26);
        border-radius: 22px;
        padding: 12px 16px;
        box-shadow: 0 18px 42px rgba(0,0,0,0.24);
        backdrop-filter: blur(14px);
    }}
    .stat-box {{
        display: flex;
        gap: 12px;
        justify-content: center;
        align-items: center;
        color: white;
        border-right: 1px solid rgba(255,255,255,0.20);
    }}
    .stat-box:last-child {{ border-right: 0; }}
    .stat-icon {{ font-size: 2rem; }}
    .stat-num {{
        font-size: 1.25rem;
        font-weight: 900;
        line-height: 1;
    }}
    .stat-label {{
        font-size: 0.80rem;
        color: #D7F8FF;
        font-weight: 650;
        margin-top: 3px;
    }}
    .welcome-footer {{
        text-align: center;
        color: #E9FBFF;
        font-size: 0.86rem;
        font-weight: 600;
        margin-top: -4px;
    }}

    .page-title {{
        font-size: 2.25rem;
        font-weight: 900;
        margin-bottom: 4px;
        color: {text_primary};
        letter-spacing: -0.8px;
        text-shadow: 0 4px 20px rgba(0,0,0,0.12);
    }}
    .subtext {{
        color: {text_secondary};
        font-size: 0.98rem;
        margin-bottom: 14px;
        font-weight: 600;
    }}

    .metric-card {{
        border-radius: 22px;
        padding: 22px 14px;
        text-align: center;
        transition: 0.22s ease;
    }}
    .metric-card:hover {{
        transform: translateY(-4px);
        background: {soft_card_bg};
    }}
    .metric-value {{
        font-size: 2.25rem;
        font-weight: 900;
        color: #90e0ef;
    }}
    .metric-label {{
        font-size: 0.78rem;
        color: {text_muted};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
        font-weight: 800;
    }}

    .avatar-circle {{
        width: 92px;
        height: 92px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        margin: auto;
        border: 3px solid #48cae4;
        background: linear-gradient(135deg,#90e0ef,#00b4d8);
        font-size: 2.2rem;
        box-shadow: 0 12px 34px rgba(0,0,0,0.22);
    }}
    .avatar-circle img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .stButton > button,
    [data-testid="stDownloadButton"] button,
    .stFormSubmitButton > button {{
        border-radius: 999px !important;
        border: 0 !important;
        font-weight: 900 !important;
        cursor: pointer !important;
        padding: 0.66rem 1.5rem !important;
        background: linear-gradient(135deg,#03045e,#0077b6,#00b4d8) !important;
        color: white !important;
        box-shadow: 0 12px 26px rgba(0,119,182,0.34) !important;
        transition: all 0.22s ease !important;
        letter-spacing: 0.2px !important;
    }}
    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover,
    .stFormSubmitButton > button:hover {{
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 18px 38px rgba(0,180,216,0.42) !important;
        background: linear-gradient(135deg,#0077b6,#00b4d8,#90e0ef) !important;
        color: white !important;
    }}

    input, textarea, [data-baseweb="select"] > div {{
        border-radius: 15px !important;
    }}
    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stPasswordInput input,
    textarea {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {border_color} !important;
        font-weight: 650 !important;
    }}
    .stSelectbox [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {border_color} !important;
    }}
    label, p, span, div {{
        color: {text_primary};
    }}

    [data-baseweb="tab-list"] {{
        background: transparent !important;
        border-bottom: 1px solid {border_color} !important;
    }}
    [data-baseweb="tab"] {{
        color: {text_muted} !important;
        font-weight: 800 !important;
    }}
    [aria-selected="true"][data-baseweb="tab"] {{
        color: #90e0ef !important;
        border-bottom: 3px solid #90e0ef !important;
    }}

    .whatsapp-btn {{
        display: inline-block;
        border-radius: 999px;
        padding: 11px 22px;
        color: white !important;
        text-decoration: none;
        font-weight: 900;
        margin: 6px 4px;
        font-size: 0.92rem;
        box-shadow: 0 10px 24px rgba(0,0,0,0.18);
        background: linear-gradient(135deg,#25D366,#128C7E);
    }}

    .profile-info-card {{
        border-radius: 22px;
        padding: 24px;
    }}
    .profile-field {{
        display: flex;
        justify-content: space-between;
        gap: 14px;
        padding: 11px 0;
        border-bottom: 1px solid {border_color};
        font-size: 0.95rem;
    }}
    .profile-field:last-child {{ border-bottom: none; }}
    .pf-label {{ color: {text_muted}; font-weight: 800; }}
    .pf-value {{ color: {text_primary}; font-weight: 900; }}

    .score-badge {{
        display: inline-block;
        font-size: 3.5rem;
        font-weight: 900;
        color: #90e0ef;
        padding: 18px 34px;
        border-radius: 24px;
        text-align: center;
    }}

    hr {{ border-color: {border_color} !important; }}
    .stAlert {{ border-radius: 18px !important; }}
    .stDataFrame {{ border-radius: 18px; overflow: hidden; }}

    @media (max-width: 1000px) {{
        .welcome-fixed {{
            height: auto;
            overflow: visible;
            min-height: auto;
            padding-bottom: 20px;
        }}
        .welcome-top {{ grid-template-columns: 1fr; text-align: center; gap: 6px; }}
        .cap-icon {{ margin: 0 auto; width: 120px; height: 90px; font-size: 4rem; }}
        .feature-row {{ grid-template-columns: 1fr; }}
        .used-row {{ grid-template-columns: repeat(2,1fr); }}
        .stats-strip {{ grid-template-columns: repeat(2,1fr); row-gap: 14px; }}
        .used-title:before, .used-title:after {{ width: 80px; }}
    }}
    </style>
    """, unsafe_allow_html=True)


apply_css()


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
    if d["Hours_Studied"] < 6:    recs.append("📚 Improve daily study hours to 6–8 hours.")
    if d["Attendance"] < 80:       recs.append("🏫 Keep attendance above 80% for stronger performance.")
    if d["Sleep_Hours"] < 7:       recs.append("😴 Maintain 7–8 hours of sleep to improve concentration.")
    if d["Motivation_Level"] == "Low": recs.append("🎯 Set small daily goals and track your progress.")
    if d["Internet_Access"] == "No":   recs.append("📖 Use offline notes, library support, and teacher guidance.")
    if d["Learning_Resources"] == "Low": recs.append("💡 Use free learning resources such as lectures, notes, and PDFs.")
    if d["Peer_Influence"] == "Negative": recs.append("🤝 Build a positive peer group to improve academic consistency.")
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
        xs = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        pts = [(float(x), 30 + (float(s) / 100) * 100) for x, s in zip(xs, scores)]
        for i in range(len(pts)-1):
            drawing.add(Line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1],
                             strokeColor=colors.HexColor("#34a0a4"), strokeWidth=2))
        for i, (x, y) in enumerate(pts):
            drawing.add(String(x-5, y+6, str(scores[i]), fontSize=7, fillColor=colors.HexColor("#184e77")))
    return drawing

def generate_pdf(username, user_data, score, inputs, recs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=.45*inch, bottomMargin=.45*inch)
    styles = getSampleStyleSheet()
    title  = ParagraphStyle("TitleX",  parent=styles["Heading1"], alignment=1, fontSize=22, textColor=colors.HexColor("#168aad"), spaceAfter=16)
    head   = ParagraphStyle("HeadX",   parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#184e77"), spaceAfter=8)
    normal = ParagraphStyle("NormX",   parent=styles["Normal"], fontSize=10, leading=14)
    story  = []
    story.append(Paragraph(f"{APP_NAME} — Official Prediction Report", title))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", normal))
    story.append(Spacer(1, 10))
    student_name = user_data.get("full_name") or user_data.get("child_name") or username
    info = [["Name", student_name], ["Username", username], ["Email", user_data.get("email","N/A")], ["Role", user_data.get("role","N/A").title()]]
    story.append(Paragraph("Student / User Details", head))
    t = Table(info, colWidths=[2.1*inch, 4.2*inch])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#d9ed92')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),8)]))
    story.append(t); story.append(Spacer(1, 12))
    result = [["Predicted Score", f"{score}/100"], ["Status", "Excellent" if score>=85 else "Good" if score>=70 else "Needs Improvement"]]
    story.append(Paragraph("Prediction Result", head))
    rt = Table(result, colWidths=[2.1*inch, 4.2*inch])
    rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#168aad')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),8)]))
    story.append(rt); story.append(Spacer(1, 12))
    story.append(Paragraph("Input Details", head))
    input_rows = [["Field", "Value"]] + [[k.replace('_',' '), str(v)] for k, v in inputs.items()]
    it = Table(input_rows, colWidths=[2.7*inch, 3.6*inch])
    it.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#184e77')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),7)]))
    story.append(it); story.append(Spacer(1, 12))
    scores = [r.get("score",0) for r in user_history(username)] + [score]
    story.append(simple_pdf_graph(scores[-10:]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommendations", head))
    if recs:
        for r in recs: story.append(Paragraph("• " + r, normal))
    else:
        story.append(Paragraph("Your current academic inputs are strong. Maintain consistency.", normal))
    story.append(Spacer(1, 20))
    story.append(Paragraph(f"Generated by {APP_NAME}. This report is for academic guidance only.", normal))
    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# =====================================================
# UI HELPERS
# =====================================================
def toggle_theme_button(key):
    label = "☀️ / 🌙" if st.session_state.theme == "dark" else "🌙 / ☀️"
    st.markdown("<div class='fixed-theme-holder'>", unsafe_allow_html=True)
    if st.button(label, key=key):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def get_chart_colors():
    dark = st.session_state.theme == "dark"
    return {
        "paper":   "rgba(0,0,0,0)",
        "plot":    "rgba(0,0,0,0)",
        "line":    "#52b69a" if dark else "#1e6091",
        "marker":  "#34a0a4" if dark else "#168aad",
        "bar":     "#34a0a4" if dark else "#1a759f",
        "bar2":    "#168aad" if dark else "#52b69a",
        "text":    "#d9ed92" if dark else "#184e77",
        "grid":    "rgba(82,182,154,0.15)" if dark else "rgba(26,117,159,0.12)",
    }

def score_trend_chart(records):
    cc = get_chart_colors()
    scores = [r["score"] for r in records]
    dates  = [r.get("date", f"#{i+1}") for i,r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=scores,
        mode="lines+markers+text",
        name="Score",
        text=scores, textposition="top center",
        line=dict(width=3, color=cc["line"]),
        marker=dict(size=10, color=cc["marker"], line=dict(width=2, color="white")),
        fill="tozeroy",
        fillcolor=f"rgba(52,160,164,0.12)",
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#b5e48c", annotation_text="Pass Line", annotation_font_color="#b5e48c")
    fig.add_hline(y=85, line_dash="dot",  line_color="#d9ed92", annotation_text="Excellent",  annotation_font_color="#d9ed92")
    fig.update_layout(
        title=dict(text="📈 Score Trend Over Time", font=dict(color=cc["text"], size=15)),
        height=320, margin=dict(l=10,r=10,t=45,b=10),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0,110]),
        showlegend=False,
    )
    return fig

def radar_chart(inputs):
    cc = get_chart_colors()
    cats   = ["Study Hours", "Attendance", "Sleep", "Motivation", "Resources", "Peer Influence"]
    scores_raw = [
        min(inputs.get("Hours_Studied",0) / 10 * 100, 100),
        inputs.get("Attendance", 0),
        min(inputs.get("Sleep_Hours",0) / 9 * 100, 100),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
        {"Negative":10,"Neutral":55,"Positive":100}.get(inputs.get("Peer_Influence","Neutral"),55),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=scores_raw + [scores_raw[0]],
        theta=cats + [cats[0]],
        fill="toself",
        fillcolor=f"rgba(52,160,164,0.20)",
        line=dict(color=cc["line"], width=2.5),
        marker=dict(color=cc["marker"], size=7),
    ))
    fig.update_layout(
        title=dict(text="🕸️ Academic Profile Radar", font=dict(color=cc["text"], size=15)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0,100], color=cc["text"], gridcolor=cc["grid"]),
            angularaxis=dict(color=cc["text"]),
        ),
        height=340, margin=dict(l=20,r=20,t=50,b=20),
        paper_bgcolor=cc["paper"],
        showlegend=False,
    )
    return fig

def factor_bar_chart(inputs):
    cc = get_chart_colors()
    factors = {
        "Hours Studied":     min(inputs.get("Hours_Studied",0) / 10 * 100, 100),
        "Attendance":        inputs.get("Attendance", 0),
        "Prev Score":        inputs.get("Previous_Scores", 0),
        "Sleep Quality":     min(inputs.get("Sleep_Hours",0) / 9 * 100, 100),
        "Motivation":        {"Low":25,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        "Learning Res.":     {"Low":25,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
    }
    fig = go.Figure(go.Bar(
        x=list(factors.keys()),
        y=list(factors.values()),
        marker=dict(
            color=list(factors.values()),
            colorscale=[[0,"#1e6091"],[0.4,"#34a0a4"],[0.7,"#76c893"],[1,"#d9ed92"]],
            showscale=False,
        ),
        text=[f"{v:.0f}" for v in factors.values()],
        textposition="outside",
        textfont=dict(color=cc["text"], size=11),
    ))
    fig.update_layout(
        title=dict(text="📊 Key Factors Contributing to Score", font=dict(color=cc["text"], size=15)),
        height=320, margin=dict(l=10,r=10,t=50,b=10),
        paper_bgcolor=cc["paper"], plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0,115]),
        showlegend=False,
    )
    return fig

# =====================================================
# WELCOME PAGE
# =====================================================
def welcome_page():
    toggle_theme_button("theme_welcome_fixed")

    st.markdown(f"""
    <div class="welcome-fixed">
        <div class="welcome-top">
            <div class="cap-icon">🎓</div>
            <div>
                <h1 class="animated-title">ScoreWise <span>AI</span></h1>
                <div class="welcome-subtitle">Smart Student Performance Predictor ✨</div>
            </div>
        </div>

        <div class="feature-row">
            <div class="welcome-card" style="--card-color:#2f86ff;--card-glow:rgba(47,134,255,0.42);">
                <div class="icon">📊</div>
                <h3>Smart Graph</h3>
                <div class="mini-line"></div>
                <ul>
                    <li>Visualize academic trends</li>
                    <li>Compare key study factors</li>
                    <li>Understand performance clearly</li>
                </ul>
            </div>

            <div class="welcome-card" style="--card-color:#42d957;--card-glow:rgba(66,217,87,0.38);">
                <div class="icon">🔮</div>
                <h3>Prediction</h3>
                <div class="mini-line"></div>
                <ul>
                    <li>AI score prediction</li>
                    <li>Simple result view</li>
                    <li>Quick and accurate output</li>
                </ul>
            </div>

            <div class="welcome-card" style="--card-color:#9b45ff;--card-glow:rgba(155,69,255,0.42);">
                <div class="icon">📄</div>
                <h3>PDF Report</h3>
                <div class="mini-line"></div>
                <ul>
                    <li>Downloadable report</li>
                    <li>Professional format</li>
                    <li>Easy WhatsApp sharing</li>
                </ul>
            </div>
        </div>

        <div>
            <div class="used-title">Used For</div>
            <div class="used-row">
                <div class="used-item">
                    <div class="used-icon">🎓</div>
                    <div class="used-name">Students</div>
                    <div class="used-desc">Track and improve performance</div>
                </div>
                <div class="used-item">
                    <div class="used-icon">👨‍👩‍👧</div>
                    <div class="used-name">Parents</div>
                    <div class="used-desc">Monitor child progress</div>
                </div>
                <div class="used-item">
                    <div class="used-icon">📚</div>
                    <div class="used-name">Teachers</div>
                    <div class="used-desc">Analyze and support students</div>
                </div>
                <div class="used-item">
                    <div class="used-icon">🏫</div>
                    <div class="used-name">Schools</div>
                    <div class="used-desc">Improve academic outcomes</div>
                </div>
                <div class="used-item">
                    <div class="used-icon">💼</div>
                    <div class="used-name">Counselors</div>
                    <div class="used-desc">Guide future decisions</div>
                </div>
            </div>
        </div>

        <div class="stats-strip">
            <div class="stat-box"><div class="stat-icon">👥</div><div><div class="stat-num">5000+</div><div class="stat-label">Students Helped</div></div></div>
            <div class="stat-box"><div class="stat-icon">📊</div><div><div class="stat-num">25K+</div><div class="stat-label">Predictions Made</div></div></div>
            <div class="stat-box"><div class="stat-icon">📑</div><div><div class="stat-num">10K+</div><div class="stat-label">Reports Generated</div></div></div>
            <div class="stat-box"><div class="stat-icon">🛡️</div><div><div class="stat-num">99%</div><div class="stat-label">Accuracy Rate</div></div></div>
        </div>

        <div class="welcome-footer">♡ Made with ❤️ for Students | Empowering Education with AI</div>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([2.2, 1, 2.2])
    with col2:
        if st.button("Get Started →", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


def auth_page():
    users = load_json(USER_DB_FILE, {})

    # Top bar
    c1,c2 = st.columns([8,1])
    with c1:
        if st.button("← Back"):
            st.session_state.auth_page = "welcome"; st.rerun()
    with c2:
        toggle_theme_button("theme_auth")

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>{APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:18px'>Secure Login & OTP Signup</p>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Login", "✍️ Sign Up"])

        with tab_login:
            username = st.text_input("Username", key="login_user", placeholder="Enter username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter password")
            st.markdown("<div class='login-btn-wrap'>", unsafe_allow_html=True)
            login_clicked = st.button("Login", key="do_login")
            st.markdown("</div>", unsafe_allow_html=True)
            if login_clicked:
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in  = True
                    st.session_state.username   = username
                    st.session_state.role       = users[username].get("role","student")
                    st.session_state.active_page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with tab_signup:
            role      = st.selectbox("Account Type", ["student","parent"], format_func=lambda x: x.title())
            username  = st.text_input("Create Username", key="su_user")
            email     = st.text_input("Email for OTP",   key="su_email")
            full_name = st.text_input("Full Name",        key="su_name")
            password  = st.text_input("Password",         type="password", key="su_pass")
            confirm   = st.text_input("Confirm Password", type="password", key="su_confirm")
            if role == "student":
                dob    = st.date_input("Date of Birth", key="su_dob", min_value=datetime(1990,1,1), max_value=datetime.now())
                grade  = st.selectbox("Class / Course", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                school = st.text_input("School / College")
            else:
                child_name = st.text_input("Child Name")
                grade      = st.selectbox("Child Class / Course", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                relation   = st.selectbox("Relation", ["Father","Mother","Guardian"])

            st.markdown("<div class='login-btn-wrap'>", unsafe_allow_html=True)
            send_otp_clicked = st.button("Send OTP", key="send_otp_btn")
            st.markdown("</div>", unsafe_allow_html=True)
            if send_otp_clicked:
                if not email:
                    st.warning("Email required.")
                else:
                    otp = generate_otp(); store_otp(email, otp)
                    ok, msg = send_otp_email(email, otp, full_name or "User")
                    if ok:  st.success("OTP sent. Check email inbox.")
                    else:   st.warning(f"Email not configured. Testing OTP: {otp}")

            otp_entered = st.text_input("Enter OTP", max_chars=6)
            st.markdown("<div class='login-btn-wrap'>", unsafe_allow_html=True)
            verify_clicked = st.button("Verify & Create Account", key="verify_otp_btn")
            st.markdown("</div>", unsafe_allow_html=True)
            if verify_clicked:
                if not username or not email or not password or not full_name:
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
                        data = {"password": hash_password(password), "email": email, "full_name": full_name, "role": role, "created_at": datetime.now().isoformat()}
                        if role == "student":
                            data.update({"dob": str(dob), "age": calculate_age(dob), "grade": grade, "school": school})
                        else:
                            data.update({"child_name": child_name, "child_grade": grade, "relation": relation})
                        users[username] = data
                        save_json(USER_DB_FILE, users)

                        # Auto-login immediately after successful signup
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.role = role
                        st.session_state.active_page = "Home"
                        st.session_state.auth_page = "welcome"
                        st.success("Account created successfully! Opening your dashboard...")
                        st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# MAIN APP PAGES
# =====================================================
def sidebar(user):
    with st.sidebar:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(st.session_state.username, icon)}</div>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;margin:10px 0 2px'>{user.get('full_name', st.session_state.username)}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p class='subtext' style='text-align:center;margin-bottom:14px'>{user.get('role','student').title()} Account</p>", unsafe_allow_html=True)
        st.markdown("---")
        pages = ["🏠 Home","🔮 Prediction","📄 Report & Share","📚 History","👤 Profile"]
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


def home_page(user):
    records = user_history(st.session_state.username)
    name = user.get("full_name", st.session_state.username)
    st.markdown(f"<div class='page-title'>👋 Welcome, {name}!</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Your academic performance dashboard — all insights in one place.</p>", unsafe_allow_html=True)

    scores = [r["score"] for r in records]
    c1,c2,c3,c4 = st.columns(4)
    metrics = [("🎯 Attempts", len(records)), ("🏆 Best Score", max(scores) if scores else 0),
               ("📊 Average", int(np.mean(scores)) if scores else 0), ("🕐 Last Score", scores[-1] if scores else 0)]
    for col,(label,val) in zip([c1,c2,c3,c4], metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
    else:
        st.info("🚀 Go to the Prediction page and generate your first score!")


def prediction_page(user):
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Enter academic details and get only the final predicted result here. Graphs and report are available on the Report page.</p>", unsafe_allow_html=True)

    with st.form("prediction_form"):
        col1, col2 = st.columns(2)
        with col1:
            hours      = st.number_input("📖 Hours Studied (per day)",   0, 24, 5, 1)
            attendance = st.number_input("🏫 Attendance (%)",            0, 100, 75, 1)
            previous   = st.number_input("📝 Previous Score",            0, 100, 60, 1)
            sleep      = st.number_input("😴 Sleep Hours",               0, 12, 7, 1)
            motivation = st.selectbox("💡 Motivation Level",  ["Low","Medium","High"])
            teacher    = st.selectbox("👨‍🏫 Teacher Quality",  ["Poor","Average","Good"])
            school_type= st.selectbox("🏢 School Type",       ["Public","Private"])
        with col2:
            internet   = st.selectbox("🌐 Internet Access",              ["Yes","No"])
            income     = st.selectbox("💰 Family Income",                ["Low","Medium","High"])
            parental   = st.selectbox("👨‍👩‍👦 Parental Involvement",          ["Low","Medium","High"])
            education  = st.selectbox("🎓 Parent Education",             ["School","College"])
            peer       = st.selectbox("🤝 Peer Influence",               ["Negative","Neutral","Positive"])
            resources  = st.selectbox("📚 Learning Resources",           ["Low","Medium","High"])
            activities = st.selectbox("⚽ Extracurricular Activities",   ["Yes","No"])

        submitted = st.form_submit_button("🚀 Predict My Score", use_container_width=True)

    if submitted:
        data = {
            "Hours_Studied": int(hours), "Attendance": int(attendance),
            "Previous_Scores": int(previous), "Sleep_Hours": int(sleep),
            "Motivation_Level": motivation, "Teacher_Quality": teacher, "School_Type": school_type,
            "Internet_Access": internet, "Family_Income": income,
            "Parental_Involvement": parental, "Parental_Education_Level": education,
            "Peer_Influence": peer, "Learning_Resources": resources, "Extracurricular_Activities": activities,
        }
        score = predict_score(data)
        recs  = get_recommendations(data)
        record = {"date": datetime.now().strftime("%d-%m-%Y %H:%M"), "score": score, "inputs": data, "recommendations": recs}
        save_prediction(st.session_state.username, record)
        st.session_state.last_score  = score
        st.session_state.last_inputs = data
        st.session_state.last_recs   = recs
        st.session_state.last_pdf    = generate_pdf(st.session_state.username, user, score, data, recs)

        status = "🌟 Excellent!" if score>=85 else "👍 Good" if score>=70 else "📈 Needs Improvement"
        st.markdown(f"""
        <div style='text-align:center;padding:34px 0'>
          <div class='score-badge'>{score}<span style='font-size:1.2rem'>/100</span></div>
          <p style='margin-top:12px;font-size:1.18rem;font-weight:900'>{status}</p>
          <p class='subtext'>Open Report & Share page to view smart graphs and download the PDF report.</p>
        </div>
        """, unsafe_allow_html=True)

        col_a, col_b, col_c = st.columns([1.4,1,1.4])
        with col_b:
            if st.button("📄 Go to Report", use_container_width=True):
                st.session_state.active_page = "Report & Share"
                st.rerun()


def report_page(user):
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Download the PDF report and view smart performance graphs here.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Please generate a score from the Prediction page first.")
        return
    latest = records[-1] if records else {"score": st.session_state.last_score, "inputs": st.session_state.last_inputs, "recommendations": st.session_state.last_recs}
    score, inputs, recs = latest["score"], latest["inputs"], latest.get("recommendations",[])
    pdf = st.session_state.last_pdf or generate_pdf(st.session_state.username, user, score, inputs, recs)

    col1,col2,col3 = st.columns([1,1,1])
    with col2:
        st.markdown(f"<div class='metric-card'><div class='metric-label'>Predicted Score</div><div class='metric-value'>{score}/100</div></div>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button("📥 Download PDF Report", data=pdf, file_name=f"ScoreWise_Report_{st.session_state.username}.pdf", mime="application/pdf", use_container_width=True)

    share_text = f"{APP_NAME} Report%0APredicted Score: {score}/100%0AHours Studied: {inputs.get('Hours_Studied')}%0AAttendance: {inputs.get('Attendance')}%25"
    wa_url    = "https://wa.me/?text=" + share_text
    st.markdown(f"""
    <div style='text-align:center;margin:16px 0'>
      <a class='whatsapp-btn' target='_blank' href='{wa_url}'>📱 Share on WhatsApp</a>
    </div>
    """, unsafe_allow_html=True)
    st.caption("Note: PDF attachment ke liye pehle download karein, phir WhatsApp me manually attach karein.")

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


def history_page(user):
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>View all your predictions in one place.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records:
        st.info("No prediction history yet.")
        return
    df = pd.DataFrame([{
        "Date": r["date"], "Score": r["score"],
        "Hours": r["inputs"].get("Hours_Studied"),
        "Attendance": r["inputs"].get("Attendance"),
        "Previous": r["inputs"].get("Previous_Scores"),
    } for r in records])
    st.dataframe(df, use_container_width=True)
    st.plotly_chart(score_trend_chart(records), use_container_width=True)


def profile_page(user):
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Edit your profile details and update your profile picture.</p>", unsafe_allow_html=True)

    users = load_json(USER_DB_FILE, {})
    uname = st.session_state.username

    col1, col2 = st.columns([1, 2])
    with col1:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(uname, icon)}</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        upload = st.file_uploader("📸 Upload Profile Picture", type=["jpg","jpeg","png"])
        if upload and st.button("💾 Save Picture", use_container_width=True):
            save_profile_pic(uname, upload.read())
            st.success("Profile picture updated!")
            st.rerun()

    with col2:
        edit = st.session_state.profile_edit_mode

        if not edit:
            st.markdown("<div class='profile-info-card'>", unsafe_allow_html=True)
            fields = [
                ("Username",    uname),
                ("Full Name",   user.get("full_name","N/A")),
                ("Email",       user.get("email","N/A")),
                ("Role",        user.get("role","N/A").title()),
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
                    ("Child Name",    user.get("child_name","N/A")),
                    ("Child Grade",   user.get("child_grade","N/A")),
                    ("Relation",      user.get("relation","N/A")),
                ]
            for label, val in fields:
                st.markdown(f"<div class='profile-field'><span class='pf-label'>{label}</span><span class='pf-value'>{val}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", use_container_width=True):
                st.session_state.profile_edit_mode = True
                st.rerun()

        else:
            # EDIT MODE
            with st.form("edit_profile_form"):
                st.markdown("##### ✏️ Edit Your Details")
                new_name  = st.text_input("Full Name",  value=user.get("full_name",""))
                new_email = st.text_input("Email",      value=user.get("email",""))

                if user.get("role") == "student":
                    dob_val = user.get("dob","2000-01-01")
                    try:
                        dob_date = datetime.strptime(dob_val, "%Y-%m-%d").date()
                    except Exception:
                        dob_date = date(2000,1,1)
                    new_dob    = st.date_input("Date of Birth", value=dob_date, min_value=date(1990,1,1), max_value=date.today())
                    grade_opts = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_grade  = user.get("grade","Class 10")
                    g_idx      = grade_opts.index(cur_grade) if cur_grade in grade_opts else 2
                    new_grade  = st.selectbox("Class / Grade", grade_opts, index=g_idx)
                    new_school = st.text_input("School / College", value=user.get("school",""))
                else:
                    new_child  = st.text_input("Child Name",  value=user.get("child_name",""))
                    grade_opts = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cur_grade  = user.get("child_grade","Class 10")
                    g_idx      = grade_opts.index(cur_grade) if cur_grade in grade_opts else 2
                    new_cgrade = st.selectbox("Child Grade", grade_opts, index=g_idx)
                    rel_opts   = ["Father","Mother","Guardian"]
                    cur_rel    = user.get("relation","Father")
                    r_idx      = rel_opts.index(cur_rel) if cur_rel in rel_opts else 0
                    new_rel    = st.selectbox("Relation", rel_opts, index=r_idx)

                st.markdown("##### 🔒 Change Password (optional)")
                old_pass = st.text_input("Current Password", type="password")
                new_pass = st.text_input("New Password",     type="password")
                cnf_pass = st.text_input("Confirm New Password", type="password")

                col_s1, col_s2 = st.columns(2)
                with col_s1:
                    save_clicked   = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with col_s2:
                    cancel_clicked = st.form_submit_button("❌ Cancel",       use_container_width=True)

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


def main_app():
    users = load_json(USER_DB_FILE, {})
    user  = users.get(st.session_state.username, {})
    sidebar(user)
    page = st.session_state.active_page
    if   page == "Home":          home_page(user)
    elif page == "Prediction":    prediction_page(user)
    elif page == "Report & Share":report_page(user)
    elif page == "History":       history_page(user)
    elif page == "Profile":       profile_page(user)

# =====================================================
# ROUTER
# =====================================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()
