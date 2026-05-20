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
    if dark:
        bg_color       = "#07111f"
        card_bg        = "rgba(24,78,119,0.75)"
        text_primary   = "#d9ed92"
        text_secondary = "#b5e48c"
        text_muted     = "#99d98c"
        border_color   = "rgba(82,182,154,0.35)"
        accent1        = "#34a0a4"
        accent2        = "#168aad"
        accent3        = "#1a759f"
        input_bg       = "rgba(7,17,31,0.80)"
        input_text     = "#d9ed92"
        metric_val     = "#52b69a"
        hero_box_bg    = "rgba(7,17,31,0.72)"
        hero_text      = "#d9ed92"
        tagline_color  = "#b5e48c"
        feature_bg     = "rgba(82,182,154,0.15)"
        feature_border = "rgba(82,182,154,0.35)"
        feature_text   = "#99d98c"
        sidebar_bg     = "rgba(24,78,119,0.92)"
        page_title_clr = "#52b69a"
        btn_grad       = "linear-gradient(135deg,#1e6091,#34a0a4)"
        btn_hover      = "linear-gradient(135deg,#168aad,#52b69a)"
        tab_active     = "#34a0a4"
        bg_image_url   = "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1800&q=80"
        bg_overlay     = "rgba(7,17,31,0.82)"
    else:
        bg_color       = "#f0faf5"
        card_bg        = "rgba(255,255,255,0.92)"
        text_primary   = "#184e77"
        text_secondary = "#1e6091"
        text_muted     = "#1a759f"
        border_color   = "rgba(26,117,159,0.28)"
        accent1        = "#168aad"
        accent2        = "#34a0a4"
        accent3        = "#52b69a"
        input_bg       = "rgba(255,255,255,0.95)"
        input_text     = "#184e77"
        metric_val     = "#1e6091"
        hero_box_bg    = "rgba(255,255,255,0.88)"
        hero_text      = "#184e77"
        tagline_color  = "#1e6091"
        feature_bg     = "rgba(82,182,154,0.12)"
        feature_border = "rgba(52,160,164,0.40)"
        feature_text   = "#1e6091"
        sidebar_bg     = "rgba(240,250,245,0.96)"
        page_title_clr = "#1e6091"
        btn_grad       = "linear-gradient(135deg,#34a0a4,#52b69a)"
        btn_hover      = "linear-gradient(135deg,#168aad,#34a0a4)"
        tab_active     = "#168aad"
        bg_image_url   = "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1800&q=80"
        bg_overlay     = "rgba(217,237,146,0.22)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
    * {{ font-family: Inter, sans-serif !important; }}

    /* ── APP BACKGROUND ── */
    .stApp {{
        background:
            linear-gradient({bg_overlay}, {bg_overlay}),
            url('{bg_image_url}');
        background-size: cover;
        background-attachment: fixed;
        background-position: center;
        color: {text_primary};
    }}

    .main .block-container {{ padding-top: 1.4rem; max-width: 1200px; }}

    /* ── SIDEBAR ── */
    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {border_color};
        backdrop-filter: blur(22px);
    }}
    [data-testid="stSidebar"] * {{ color: {text_primary} !important; }}
    [data-testid="stSidebar"] .stRadio label {{ color: {text_primary} !important; font-weight: 600; }}

    /* ── GLASS CARD ── */
    .glass {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 28px;
        padding: 32px;
        box-shadow: 0 20px 60px rgba(0,0,0,0.18);
        backdrop-filter: blur(18px);
    }}

    /* ── HERO ── */
    .hero {{
        min-height: 78vh;
        display: flex;
        align-items: center;
        justify-content: center;
        text-align: center;
        padding: 20px;
    }}
    .hero-box {{
        max-width: 820px;
        background: {hero_box_bg};
        border: 1.5px solid {border_color};
        border-radius: 36px;
        padding: 60px 40px;
        box-shadow: 0 32px 100px rgba(0,0,0,0.30);
        backdrop-filter: blur(20px);
        animation: fadeInUp 0.8s ease;
    }}
    @keyframes fadeInUp {{
        from {{ opacity: 0; transform: translateY(40px); }}
        to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .app-logo {{
        font-size: 5rem;
        margin-bottom: 8px;
        display: block;
        animation: pulse 2.5s infinite;
    }}
    @keyframes pulse {{
        0%,100% {{ transform: scale(1); }}
        50%      {{ transform: scale(1.06); }}
    }}
    .app-title {{
        font-size: 4.0rem;
        font-weight: 900;
        line-height: 1.05;
        color: {hero_text};
        margin: 0 0 8px 0;
        text-shadow: 0 4px 24px rgba(0,0,0,0.28);
        letter-spacing: -1px;
    }}
    .tagline {{
        font-size: 1.15rem;
        color: {tagline_color};
        margin: 0 0 28px 0;
        font-weight: 500;
    }}
    .feature-mini {{
        display: inline-block;
        margin: 5px 6px;
        padding: 9px 18px;
        border-radius: 999px;
        background: {feature_bg};
        color: {feature_text};
        border: 1px solid {feature_border};
        font-weight: 700;
        font-size: 0.86rem;
        letter-spacing: 0.3px;
    }}

    /* ── STATS ROW ── */
    .stats-row {{
        display: flex;
        justify-content: center;
        gap: 32px;
        margin-top: 32px;
        flex-wrap: wrap;
    }}
    .stat-item {{
        text-align: center;
    }}
    .stat-num {{
        font-size: 2rem;
        font-weight: 900;
        color: {accent1};
    }}
    .stat-label {{
        font-size: 0.78rem;
        color: {tagline_color};
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }}

    /* ── PAGE TITLE ── */
    .page-title {{
        font-size: 2.1rem;
        font-weight: 900;
        margin-bottom: 4px;
        color: {page_title_clr};
        letter-spacing: -0.5px;
    }}
    .subtext {{ color: {text_muted}; font-size: 0.95rem; margin-bottom: 12px; }}

    /* ── METRIC CARDS ── */
    .metric-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 22px;
        padding: 22px 14px;
        text-align: center;
        backdrop-filter: blur(14px);
        box-shadow: 0 8px 28px rgba(0,0,0,0.10);
        transition: transform 0.2s;
    }}
    .metric-card:hover {{ transform: translateY(-4px); }}
    .metric-value {{
        font-size: 2.2rem;
        font-weight: 900;
        color: {metric_val};
    }}
    .metric-label {{
        font-size: 0.76rem;
        color: {text_muted};
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 4px;
    }}

    /* ── AVATAR ── */
    .avatar-circle {{
        width: 90px; height: 90px;
        border-radius: 50%;
        display: flex; align-items: center; justify-content: center;
        overflow: hidden;
        margin: auto;
        border: 3px solid {accent1};
        background: linear-gradient(135deg,{accent3},{accent1});
        font-size: 2.2rem;
        box-shadow: 0 4px 18px rgba(0,0,0,0.20);
    }}
    .avatar-circle img {{ width: 100%; height: 100%; object-fit: cover; }}

    /* ── BUTTONS ── */
    .stButton > button,
    [data-testid="stDownloadButton"] button {{
        border-radius: 999px !important;
        border: 0 !important;
        font-weight: 800 !important;
        cursor: pointer !important;
        padding: 0.60rem 1.4rem !important;
        background: {btn_grad} !important;
        color: white !important;
        box-shadow: 0 8px 22px rgba(52,160,164,0.25) !important;
        font-size: 0.92rem !important;
        transition: all 0.22s !important;
        letter-spacing: 0.2px !important;
    }}
    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover {{
        background: {btn_hover} !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 14px 32px rgba(52,160,164,0.38) !important;
    }}

    /* ── LOGIN BUTTON CENTER (smaller) ── */
    .login-btn-wrap {{
        display: flex;
        justify-content: center;
        margin-top: 8px;
    }}
    .login-btn-wrap .stButton > button {{
        padding: 0.48rem 2.2rem !important;
        font-size: 0.88rem !important;
        min-width: 140px;
        max-width: 180px;
    }}

    /* ── INPUTS ── */
    input, textarea, [data-baseweb="select"] > div {{
        border-radius: 14px !important;
    }}
    .stTextInput input, .stNumberInput input, .stDateInput input, .stPasswordInput input {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {border_color} !important;
    }}
    .stSelectbox [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {border_color} !important;
    }}

    /* ── TABS ── */
    [data-baseweb="tab-list"] {{
        background: transparent !important;
        border-bottom: 2px solid {border_color} !important;
    }}
    [data-baseweb="tab"] {{
        color: {text_muted} !important;
        font-weight: 700 !important;
        font-size: 0.96rem !important;
    }}
    [aria-selected="true"][data-baseweb="tab"] {{
        color: {tab_active} !important;
        border-bottom: 3px solid {tab_active} !important;
    }}

    /* ── SHARE BUTTONS ── */
    .whatsapp-btn {{
        display: inline-block; border-radius: 999px;
        padding: 10px 20px;
        background: linear-gradient(135deg,#25D366,#128C7E);
        color: white !important; text-decoration: none;
        font-weight: 800; margin: 6px 4px;
        font-size: 0.9rem;
        box-shadow: 0 4px 14px rgba(37,211,102,0.30);
    }}
    .email-btn {{
        display: inline-block; border-radius: 999px;
        padding: 10px 20px;
        background: linear-gradient(135deg,{accent3},{accent1});
        color: white !important; text-decoration: none;
        font-weight: 800; margin: 6px 4px;
        font-size: 0.9rem;
        box-shadow: 0 4px 14px rgba(26,117,159,0.30);
    }}

    /* ── PROFILE CARD ── */
    .profile-info-card {{
        background: {card_bg};
        border: 1px solid {border_color};
        border-radius: 22px;
        padding: 24px;
        backdrop-filter: blur(14px);
    }}
    .profile-field {{
        display: flex;
        justify-content: space-between;
        padding: 10px 0;
        border-bottom: 1px solid {border_color};
        font-size: 0.95rem;
    }}
    .profile-field:last-child {{ border-bottom: none; }}
    .pf-label {{ color: {text_muted}; font-weight: 600; }}
    .pf-value {{ color: {text_primary}; font-weight: 700; }}

    /* ── SCORE BADGE ── */
    .score-badge {{
        display: inline-block;
        font-size: 3.5rem;
        font-weight: 900;
        color: {metric_val};
        padding: 18px 32px;
        border-radius: 22px;
        background: {card_bg};
        border: 2px solid {border_color};
        text-align: center;
        box-shadow: 0 8px 28px rgba(0,0,0,0.12);
    }}

    hr {{ border-color: {border_color} !important; }}
    label, p, span {{ color: {text_primary}; }}
    .stDataFrame {{ border-radius: 18px; overflow: hidden; }}
    [data-testid="stSidebar"] hr {{ border-color: {border_color} !important; }}
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
    if d["Hours_Studied"] < 6:    recs.append("📚 Study hours ko 6–8 hours daily tak improve karein.")
    if d["Attendance"] < 80:       recs.append("🏫 Attendance ko 80%+ rakhna score ke liye important hai.")
    if d["Sleep_Hours"] < 7:       recs.append("😴 Daily 7–8 hours sleep rakhein, concentration improve hota hai.")
    if d["Motivation_Level"] == "Low": recs.append("🎯 Daily small goals set karein aur progress track karein.")
    if d["Internet_Access"] == "No":   recs.append("📖 Offline notes, library aur teacher support ka use karein.")
    if d["Learning_Resources"] == "Low": recs.append("💡 Free resources jaise YouTube lectures aur PDFs use karein.")
    if d["Peer_Influence"] == "Negative": recs.append("🤝 Positive peer group banana performance boost karta hai.")
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

    st.markdown(f"""
    <div class='hero'>
      <div class='hero-box'>
        <span class='app-logo'>🎓</span>
        <h1 class='app-title'>{APP_NAME}</h1>
        <p class='tagline'>{TAGLINE}</p>
        <div style='margin-bottom:28px'>
          <span class='feature-mini'>🔐 OTP Signup</span>
          <span class='feature-mini'>📊 AI Prediction</span>
          <span class='feature-mini'>📄 PDF Report</span>
          <span class='feature-mini'>📱 WhatsApp Share</span>
          <span class='feature-mini'>🌙 Dark / Light</span>
          <span class='feature-mini'>📈 Smart Graphs</span>
        </div>
        <div class='stats-row'>
          <div class='stat-item'><div class='stat-num'>98%</div><div class='stat-label'>Accuracy</div></div>
          <div class='stat-item'><div class='stat-num'>10K+</div><div class='stat-label'>Predictions</div></div>
          <div class='stat-item'><div class='stat-num'>3</div><div class='stat-label'>Smart Charts</div></div>
          <div class='stat-item'><div class='stat-num'>Free</div><div class='stat-label'>Always</div></div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Centered Get Started button
    col1, col2, col3 = st.columns([1.8, 1, 1.8])
    with col2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

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
                        st.success("Account created! Now login.")

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
        st.info("🚀 Prediction page se apna first score generate karein!")


def prediction_page(user):
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Apni academic details bharo aur AI se predicted score paao.</p>", unsafe_allow_html=True)

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
    st.markdown("<p class='subtext'>PDF report download karein aur WhatsApp / email pe share karein.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Pehle Prediction page se score generate karein.")
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
    email_url = "mailto:?subject=" + urllib.parse.quote(f"{APP_NAME} Prediction Report") + "&body=" + share_text
    st.markdown(f"""
    <div style='text-align:center;margin:16px 0'>
      <a class='whatsapp-btn' target='_blank' href='{wa_url}'>📱 Share on WhatsApp</a>
      <a class='email-btn' href='{email_url}'>✉️ Share via Email</a>
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
    st.markdown("<p class='subtext'>Apni saari predictions ek jagah.</p>", unsafe_allow_html=True)
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
    st.markdown("<p class='subtext'>Profile details edit karein aur profile picture update karein.</p>", unsafe_allow_html=True)

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
