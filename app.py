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
        app_gradient = "linear-gradient(135deg,#03045e 0%,#023e8a 24%,#0077b6 52%,#0096c7 76%,#00b4d8 100%)"
        panel_bg      = "rgba(3,4,94,0.72)"
        card_bg       = "rgba(255,255,255,0.10)"
        soft_card_bg  = "rgba(255,255,255,0.08)"
        text_primary  = "#f7fbff"
        text_secondary= "#caf0f8"
        text_muted    = "#ade8f4"
        border_color  = "rgba(202,240,248,0.22)"
        input_bg      = "rgba(255,255,255,0.12)"
        input_text    = "#ffffff"
        accent1       = "#90e0ef"
        accent2       = "#48cae4"
        accent3       = "#00b4d8"
        sidebar_bg    = "rgba(3,4,94,0.88)"
        shadow        = "0 22px 70px rgba(0,0,0,0.32)"
        welcome_overlay = "linear-gradient(90deg,rgba(3,4,94,0.66),rgba(0,119,182,0.26),rgba(0,0,0,0.12))"
    else:
        app_gradient = "linear-gradient(135deg,#caf0f8 0%,#ade8f4 22%,#90e0ef 48%,#48cae4 72%,#00b4d8 100%)"
        panel_bg      = "rgba(255,255,255,0.74)"
        card_bg       = "rgba(255,255,255,0.60)"
        soft_card_bg  = "rgba(255,255,255,0.46)"
        text_primary  = "#03045e"
        text_secondary= "#023e8a"
        text_muted    = "#0077b6"
        border_color  = "rgba(2,62,138,0.18)"
        input_bg      = "rgba(255,255,255,0.86)"
        input_text    = "#03045e"
        accent1       = "#0077b6"
        accent2       = "#0096c7"
        accent3       = "#00b4d8"
        sidebar_bg    = "rgba(255,255,255,0.78)"
        shadow        = "0 20px 60px rgba(2,62,138,0.22)"
        welcome_overlay = "linear-gradient(90deg,rgba(255,255,255,0.48),rgba(202,240,248,0.20),rgba(0,180,216,0.10))"

    welcome_img = "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1900&q=85"
    if is_welcome:
        app_background = f"{welcome_overlay}, url('{welcome_img}')"
        background_extra = "background-size: cover; background-position: center; background-attachment: fixed;"
    else:
        app_background = app_gradient
        background_extra = "background-size: 220% 220%; animation: shineBg 12s ease infinite;"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

    * {{
        font-family: Inter, sans-serif !important;
        box-sizing: border-box;
    }}

    .stApp {{
        background: {app_background};
        {background_extra}
        color: {text_primary};
    }}

    @keyframes shineBg {{
        0% {{ background-position: 0% 50%; }}
        50% {{ background-position: 100% 50%; }}
        100% {{ background-position: 0% 50%; }}
    }}

    .main .block-container {{
        padding-top: 1.4rem;
        max-width: 1180px;
    }}

    /* Hide unnecessary Streamlit decoration boxes */
    [data-testid="stDecoration"],
    #MainMenu,
    footer,
    header {{
        visibility: hidden;
        height: 0;
    }}

    /* Sidebar */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_color};
        backdrop-filter: blur(24px);
    }}
    [data-testid="stSidebar"] * {{
        color: {text_primary} !important;
    }}

    /* Clean professional panels */
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

    /* Welcome page: photo background only, no heavy box */
    .hero {{
        min-height: 82vh;
        display: flex;
        align-items: center;
        justify-content: flex-start;
        text-align: left;
        padding: 5vh 3vw;
    }}
    .hero-box {{
        max-width: 760px;
        background: transparent;
        border: 0;
        box-shadow: none;
        padding: 20px 8px;
        animation: fadeInUp 0.8s ease;
    }}
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(34px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .app-logo {{
        font-size: 4.2rem;
        display: block;
        margin-bottom: 8px;
        filter: drop-shadow(0 8px 22px rgba(0,0,0,0.35));
    }}
    .app-title {{
        font-size: clamp(3rem, 6vw, 5.4rem);
        font-weight: 900;
        line-height: 0.98;
        margin: 0 0 12px 0;
        color: white;
        text-shadow: 0 6px 28px rgba(0,0,0,0.42);
        letter-spacing: -2px;
    }}
    .tagline {{
        font-size: 1.22rem;
        color: #f7fbff;
        margin: 0 0 28px 0;
        font-weight: 600;
        max-width: 560px;
        text-shadow: 0 3px 16px rgba(0,0,0,0.42);
    }}
    .feature-mini {{
        display: inline-block;
        margin: 6px 8px 6px 0;
        padding: 10px 18px;
        border-radius: 999px;
        background: rgba(255,255,255,0.20);
        color: white;
        border: 1px solid rgba(255,255,255,0.32);
        font-weight: 800;
        font-size: 0.86rem;
        backdrop-filter: blur(10px);
    }}
    .stats-row {{
        display: flex;
        gap: 16px;
        margin-top: 28px;
        flex-wrap: wrap;
    }}
    .stat-item {{
        min-width: 112px;
        padding: 12px 16px;
        border-radius: 18px;
        background: rgba(255,255,255,0.18);
        border: 1px solid rgba(255,255,255,0.28);
        backdrop-filter: blur(12px);
        text-align: center;
    }}
    .stat-num {{
        font-size: 1.7rem;
        font-weight: 900;
        color: white;
    }}
    .stat-label {{
        font-size: 0.72rem;
        color: #e9fbff;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1px;
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
        color: {accent1};
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
        border: 3px solid {accent2};
        background: linear-gradient(135deg,{accent1},{accent3});
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
    label, p {{
        color: {text_primary} !important;
    }}
    .stTextInput label, .stNumberInput label, .stSelectbox label,
    .stDateInput label, .stRadio label, .stCheckbox label,
    [data-baseweb="form-control"] label,
    .stSlider label {{
        color: {text_primary} !important;
        font-weight: 700 !important;
    }}
    /* Input typed text */
    .stTextInput input, .stNumberInput input, .stPasswordInput input {{
        color: {input_text} !important;
        caret-color: {input_text} !important;
    }}
    .stSelectbox [data-baseweb="select"] span {{
        color: {input_text} !important;
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
        color: {accent1} !important;
        border-bottom: 3px solid {accent1} !important;
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
    .profile-field:last-child {{
        border-bottom: none;
    }}
    .pf-label {{
        color: {text_muted};
        font-weight: 800;
    }}
    .pf-value {{
        color: {text_primary};
        font-weight: 900;
    }}

    .score-badge {{
        display: inline-block;
        font-size: 3.5rem;
        font-weight: 900;
        color: {accent1};
        padding: 18px 34px;
        border-radius: 24px;
        text-align: center;
    }}

    hr {{
        border-color: {border_color} !important;
    }}
    .stAlert {{
        border-radius: 18px !important;
    }}
    .stDataFrame {{
        border-radius: 18px;
        overflow: hidden;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_css()

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
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch, leftMargin=0.7*inch, rightMargin=0.7*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle("TitleX", parent=styles["Heading1"],
        alignment=1, fontSize=22, textColor=colors.HexColor("#168aad"),
        spaceAfter=4, fontName="Helvetica-Bold")
    subtitle_style = ParagraphStyle("SubX", parent=styles["Normal"],
        alignment=1, fontSize=10, textColor=colors.HexColor("#1a759f"),
        spaceAfter=14, fontName="Helvetica")
    head_style = ParagraphStyle("HeadX", parent=styles["Heading2"],
        fontSize=13, textColor=colors.white, spaceAfter=0,
        fontName="Helvetica-Bold", backColor=colors.HexColor("#184e77"),
        borderPadding=(8,10,8,10))
    normal_style = ParagraphStyle("NormX", parent=styles["Normal"],
        fontSize=10, leading=15, textColor=colors.HexColor("#03045e"))
    rec_style = ParagraphStyle("RecX", parent=styles["Normal"],
        fontSize=10, leading=15, textColor=colors.HexColor("#184e77"),
        leftIndent=10)

    story = []

    # ── Header ──
    story.append(Paragraph(f"🎓 {APP_NAME}", title_style))
    story.append(Paragraph("Official Student Performance Prediction Report", subtitle_style))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y  |  %I:%M %p')}", subtitle_style))

    # Divider
    story.append(Table([[""]], colWidths=[6.6*inch],
        style=[("LINEBELOW",(0,0),(-1,-1),1.2,colors.HexColor("#168aad")),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]))

    story.append(Spacer(1, 10))

    # ── Student / User Details ──
    student_name = user_data.get("full_name") or user_data.get("child_name") or username
    story.append(Paragraph("  👤  Student / User Details", head_style))
    story.append(Spacer(1, 4))

    info_rows = [
        ["Full Name",  student_name],
        ["Username",   username],
        ["Email",      user_data.get("email","N/A")],
        ["Role",       user_data.get("role","N/A").title()],
    ]
    if user_data.get("role") == "student":
        info_rows += [
            ["Grade / Class", user_data.get("grade","N/A")],
            ["School",        user_data.get("school","N/A")],
            ["Date of Birth", user_data.get("dob","N/A")],
        ]
    else:
        info_rows += [
            ["Child Name",  user_data.get("child_name","N/A")],
            ["Child Grade", user_data.get("child_grade","N/A")],
            ["Relation",    user_data.get("relation","N/A")],
        ]

    t_info = Table([[Paragraph(f"<b>{r[0]}</b>",normal_style), Paragraph(r[1],normal_style)] for r in info_rows],
        colWidths=[2.2*inch, 4.4*inch])
    t_info.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white, colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTNAME",(1,0),(1,-1),"Helvetica"),
    ]))
    story.append(t_info)
    story.append(Spacer(1, 14))

    # ── Prediction Result ──
    story.append(Paragraph("  📊  Prediction Result", head_style))
    story.append(Spacer(1, 4))

    status_label = "🌟 Excellent!" if score >= 85 else ("👍 Good" if score >= 70 else "📈 Needs Improvement")
    score_color  = colors.HexColor("#168aad") if score >= 70 else colors.HexColor("#e85d04")
    result_rows  = [["Predicted Score", f"{score} / 100"],["Performance Status", status_label]]
    t_result = Table([[Paragraph(f"<b>{r[0]}</b>",normal_style), Paragraph(r[1],normal_style)] for r in result_rows],
        colWidths=[2.2*inch, 4.4*inch])
    t_result.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("BACKGROUND",(1,0),(1,0),colors.HexColor("#caf0f8")),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(1,0),(1,0),13),
        ("TEXTCOLOR",(1,0),(1,0),score_color),
        ("PADDING",(0,0),(-1,-1),9),
    ]))
    story.append(t_result)
    story.append(Spacer(1, 14))

    # ── Input Details ──
    story.append(Paragraph("  📋  Academic Input Details", head_style))
    story.append(Spacer(1, 4))

    input_header = [
        [Paragraph("<b>Factor</b>", normal_style), Paragraph("<b>Value Provided</b>", normal_style)]
    ]
    input_data   = [[Paragraph(k.replace("_"," "), normal_style), Paragraph(str(v), normal_style)] for k,v in inputs.items()]
    t_inputs = Table(input_header + input_data, colWidths=[2.9*inch, 3.7*inch])
    t_inputs.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#184e77")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white, colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
    ]))
    story.append(t_inputs)
    story.append(Spacer(1, 14))

    # ── Score History Graph ──
    scores = [r.get("score",0) for r in user_history(username)] + [score]
    if len(scores) > 1:
        story.append(Paragraph("  📈  Score History Graph", head_style))
        story.append(Spacer(1, 6))
        story.append(simple_pdf_graph(scores[-10:]))
        story.append(Spacer(1, 14))

    # ── Recommendations ──
    story.append(Paragraph("  💡  Personalized Recommendations", head_style))
    story.append(Spacer(1, 6))
    if recs:
        for r in recs:
            story.append(Paragraph("• " + r.lstrip("📚🏫😴🎯📖💡🤝 ").strip(), rec_style))
            story.append(Spacer(1, 3))
    else:
        story.append(Paragraph("✅ Your current academic inputs are strong. Keep up the great work and maintain consistency!", rec_style))

    story.append(Spacer(1, 20))

    # Footer
    story.append(Table([[""]], colWidths=[6.6*inch],
        style=[("LINEABOVE",(0,0),(-1,-1),.8,colors.HexColor("#ade8f4")),("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]))
    story.append(Paragraph(f"Generated by {APP_NAME}  •  {datetime.now().strftime('%d-%m-%Y')}  •  This report is for academic guidance only.", subtitle_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

# =====================================================
# UI HELPERS
# =====================================================
def toggle_theme_button(key):
    label = "☀️ Light Mode" if st.session_state.theme == "dark" else "🌙 Dark Mode"
    if st.button(label, key=key):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

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
    # Theme toggle top-right
    c1,c2,c3 = st.columns([1,8,1])
    with c3: toggle_theme_button("theme_welcome")

    dark = st.session_state.theme == "dark"
    hero_text   = "white" if dark else "#03045e"
    hero_sub    = "#caf0f8" if dark else "#0077b6"
    card_border = "rgba(255,255,255,0.28)" if dark else "rgba(2,62,138,0.20)"
    card_bg_1   = "rgba(255,255,255,0.13)" if dark else "rgba(255,255,255,0.72)"
    card_title  = "white" if dark else "#03045e"
    card_desc   = "#caf0f8" if dark else "#0077b6"
    used_icon_c = "#caf0f8" if dark else "#023e8a"
    btn_bg      = "linear-gradient(135deg,#0077b6,#00b4d8)" if dark else "linear-gradient(135deg,#03045e,#0077b6)"
    stat_text   = "white" if dark else "#03045e"
    stat_sub    = "#caf0f8" if dark else "#0096c7"
    divider_c   = "rgba(255,255,255,0.30)" if dark else "rgba(2,62,138,0.18)"
    btn_line_c  = "rgba(255,255,255,0.50)" if dark else "rgba(2,62,138,0.35)"

    st.markdown(f"""
    <style>
    .welcome-wrap {{ padding: 2vh 1vw 0 1vw; }}
    .hero-header {{
        text-align: center;
        padding: 36px 10px 20px 10px;
    }}
    .hero-logo {{ font-size: 3.6rem; display:block; margin-bottom:6px; }}
    .hero-title {{
        font-size: clamp(2.6rem,5.5vw,4.6rem);
        font-weight: 900;
        color: {hero_text};
        margin: 0 0 10px 0;
        letter-spacing: -1.5px;
        text-shadow: 0 4px 22px rgba(0,0,0,0.35);
    }}
    .hero-tagline {{
        font-size: 1.14rem;
        color: {hero_sub};
        font-weight: 600;
        margin-bottom: 0;
        text-shadow: 0 2px 10px rgba(0,0,0,0.28);
    }}
    .welcome-divider {{
        border: 0;
        height: 1px;
        background: {divider_c};
        margin: 22px auto;
        max-width: 640px;
    }}
    .feature-cards-row {{
        display: flex;
        gap: 18px;
        justify-content: center;
        flex-wrap: wrap;
        margin: 0 0 28px 0;
    }}
    .feat-card {{
        flex: 1 1 220px;
        max-width: 270px;
        background: {card_bg_1};
        border: 1px solid {card_border};
        border-radius: 22px;
        padding: 28px 22px 22px 22px;
        text-align: center;
        backdrop-filter: blur(18px);
        box-shadow: 0 12px 36px rgba(0,0,0,0.16);
        transition: transform 0.22s ease;
    }}
    .feat-card:hover {{ transform: translateY(-5px); }}
    .feat-icon {{ font-size: 2.5rem; display:block; margin-bottom:10px; }}
    .feat-title {{
        font-size: 1.12rem;
        font-weight: 900;
        color: {card_title};
        margin: 0 0 6px 0;
    }}
    .feat-sep {{
        width: 40px; height: 3px;
        background: linear-gradient(90deg,#00b4d8,#90e0ef);
        border-radius: 99px;
        margin: 0 auto 10px auto;
    }}
    .feat-desc {{
        font-size: 0.82rem;
        color: {card_desc};
        font-weight: 600;
        line-height: 1.6;
    }}
    .feat-btn {{
        display: inline-block;
        margin-top: 14px;
        padding: 9px 22px;
        border-radius: 999px;
        background: {btn_bg};
        color: white !important;
        font-weight: 800;
        font-size: 0.84rem;
        text-decoration: none;
        cursor: pointer;
        border: none;
        box-shadow: 0 6px 18px rgba(0,119,182,0.30);
    }}
    .used-for-row {{
        display: flex;
        gap: 14px;
        justify-content: center;
        flex-wrap: wrap;
        margin: 0 0 10px 0;
    }}
    .used-item {{
        text-align: center;
        padding: 6px 10px;
    }}
    .used-icon {{ font-size: 1.6rem; display:block; margin-bottom:2px; }}
    .used-label {{
        font-size: 0.72rem;
        font-weight: 800;
        color: {used_icon_c};
        text-transform: uppercase;
        letter-spacing: 0.6px;
    }}
    .stats-strip {{
        display: flex;
        gap: 14px;
        justify-content: center;
        flex-wrap: wrap;
        padding: 18px 10px;
        border-top: 1px solid {divider_c};
        border-bottom: 1px solid {divider_c};
        margin: 18px 0 24px 0;
    }}
    .stat-chip {{
        display: flex; align-items: center; gap: 8px;
        padding: 8px 16px;
        border-radius: 999px;
        background: rgba(0,180,216,0.14);
        border: 1px solid rgba(0,180,216,0.25);
    }}
    .stat-chip-num {{ font-size: 1.2rem; font-weight:900; color:{stat_text}; }}
    .stat-chip-lbl {{ font-size: 0.75rem; font-weight:700; color:{stat_sub}; text-transform:uppercase; letter-spacing:0.8px; }}
    .welcome-footer {{
        text-align: center;
        font-size: 0.82rem;
        color: {card_desc};
        padding-bottom: 18px;
        font-weight: 600;
    }}
    .get-started-wrap {{
        display: flex;
        justify-content: center;
        margin: 8px 0 22px 0;
    }}
    .get-started-link {{
        padding: 13px 48px;
        border-radius: 999px;
        background: {btn_bg};
        color: white !important;
        font-weight: 900;
        font-size: 1.08rem;
        border: 1.5px solid {btn_line_c};
        box-shadow: 0 12px 34px rgba(0,119,182,0.36);
        text-decoration: none;
        transition: all 0.22s;
    }}
    </style>

    <div class='welcome-wrap'>
      <div class='hero-header'>
        <span class='hero-logo'>🎓</span>
        <h1 class='hero-title'>{APP_NAME}</h1>
        <p class='hero-tagline'>{TAGLINE} ✨</p>
      </div>
      <hr class='welcome-divider'/>

      <div class='feature-cards-row'>
        <div class='feat-card'>
          <span class='feat-icon'>📊</span>
          <div class='feat-title'>Smart Graph</div>
          <div class='feat-sep'></div>
          <div class='feat-desc'>
            • Visualize academic trends<br>
            • Subject-wise performance<br>
            • Interactive &amp; insightful
          </div>
        </div>
        <div class='feat-card'>
          <span class='feat-icon'>🔮</span>
          <div class='feat-title'>Prediction</div>
          <div class='feat-sep'></div>
          <div class='feat-desc'>
            • AI score prediction<br>
            • Simple result<br>
            • Quick &amp; accurate
          </div>
        </div>
        <div class='feat-card'>
          <span class='feat-icon'>📄</span>
          <div class='feat-title'>PDF Report</div>
          <div class='feat-sep'></div>
          <div class='feat-desc'>
            • Downloadable report<br>
            • Share on WhatsApp<br>
            • Professional format
          </div>
        </div>
      </div>

      <div style='text-align:center;margin-bottom:10px;font-size:0.85rem;font-weight:700;color:{card_desc};letter-spacing:1.5px;text-transform:uppercase;'>─── Used For ───</div>
      <div class='used-for-row'>
        <div class='used-item'><span class='used-icon'>🎓</span><div class='used-label'>Students</div><div style='font-size:0.68rem;color:{card_desc};font-weight:600;'>Track &amp; improve</div></div>
        <div class='used-item'><span class='used-icon'>👨‍👩‍👧</span><div class='used-label'>Parents</div><div style='font-size:0.68rem;color:{card_desc};font-weight:600;'>Monitor child</div></div>
        <div class='used-item'><span class='used-icon'>📖</span><div class='used-label'>Teachers</div><div style='font-size:0.68rem;color:{card_desc};font-weight:600;'>Analyze &amp; support</div></div>
        <div class='used-item'><span class='used-icon'>🏫</span><div class='used-label'>Schools</div><div style='font-size:0.68rem;color:{card_desc};font-weight:600;'>Improve outcomes</div></div>
        <div class='used-item'><span class='used-icon'>🧑‍💼</span><div class='used-label'>Counselors</div><div style='font-size:0.68rem;color:{card_desc};font-weight:600;'>Guide decisions</div></div>
      </div>

      <div class='stats-strip'>
        <div class='stat-chip'><span class='stat-chip-num'>5000+</span><span class='stat-chip-lbl'>Students Helped</span></div>
        <div class='stat-chip'><span class='stat-chip-num'>25K+</span><span class='stat-chip-lbl'>Predictions Made</span></div>
        <div class='stat-chip'><span class='stat-chip-num'>10K+</span><span class='stat-chip-lbl'>Reports Generated</span></div>
        <div class='stat-chip'><span class='stat-chip-num'>99%</span><span class='stat-chip-lbl'>Accuracy Rate</span></div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Centered Get Started button
    col1, col2, col3 = st.columns([1.8, 1, 1.8])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

    st.markdown(f"<div class='welcome-footer'>❤️ Made with love for Students &nbsp;|&nbsp; Empowering Education with AI</div>", unsafe_allow_html=True)

# =====================================================
# AUTH PAGE
# =====================================================
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
    st.markdown("<p class='subtext'>Enter academic details and get an AI-based predicted score.</p>", unsafe_allow_html=True)

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

        # Show score badge
        status = "🌟 Excellent!" if score>=85 else "👍 Good" if score>=70 else "📈 Needs Work"
        st.markdown(f"""
        <div style='text-align:center;padding:24px 0'>
          <div class='score-badge'>{score}<span style='font-size:1.2rem'>/100</span></div>
          <p style='margin-top:10px;font-size:1.1rem;font-weight:700'>{status}</p>
        </div>
        """, unsafe_allow_html=True)

        # 3 Graphs
        st.markdown("### 📊 Your Performance Analysis")
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(radar_chart(data), use_container_width=True)
        with col_g2:
            st.plotly_chart(factor_bar_chart(data), use_container_width=True)

        records = user_history(st.session_state.username)
        if len(records) > 1:
            st.plotly_chart(score_trend_chart(records), use_container_width=True)

        if recs:
            st.markdown("### 💬 Personalized Recommendations")
            for r in recs:
                st.info(r)

        st.session_state.active_page = "Report & Share"


def report_page(user):
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Download the PDF report and share it through WhatsApp or email.</p>", unsafe_allow_html=True)
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

    # 3 Graphs in report
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
        for r in recs: st.info(r)


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
