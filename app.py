import streamlit as st
import joblib
import pandas as pd
import numpy as np
import hashlib
import json
import os
import base64
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io
import plotly.graph_objects as go
import plotly.express as px

# =====================================
# PAGE CONFIG
# =====================================
st.set_page_config(
    page_title="Student Score Predictor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================
# FILE PATHS
# =====================================
USER_DB_FILE    = "users.json"
HISTORY_FILE    = "prediction_history.json"
PROFILE_PICS_DIR= "profile_pics"
OTP_FILE        = "otp_store.json"

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)

# =====================================
# EMAIL CONFIG — Change these!
# =====================================
EMAIL_SENDER   = "your_email@gmail.com"       # ← Your Gmail address
EMAIL_PASSWORD = "your_app_password_here"     # ← Gmail App Password
# To get App Password: Google Account → Security → 2-Step Verification → App passwords

# =====================================
# DATA HELPERS
# =====================================
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, 'w') as f:
        json.dump(users, f, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, 'w') as f:
        json.dump(history, f, indent=2)

def load_otp_store():
    if os.path.exists(OTP_FILE):
        with open(OTP_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_otp_store(data):
    with open(OTP_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_age(birth_date):
    today = datetime.now()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age

def save_profile_pic(username, image_bytes):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    with open(path, 'wb') as f:
        f.write(image_bytes)

def get_profile_pic_base64(username):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, 'rb') as f:
            return base64.b64encode(f.read()).decode()
    return None

# =====================================
# OTP FUNCTIONS
# =====================================
def generate_otp():
    return str(random.randint(100000, 999999))

def send_otp_email(receiver_email, otp_code, full_name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎓 Your OTP — Student Score Predictor"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = receiver_email
        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;background:#000814;color:#caf0f8;padding:30px;">
        <div style="max-width:420px;margin:0 auto;background:linear-gradient(135deg,#03045e,#0077b6);
            border-radius:16px;padding:30px;border:1px solid #00b4d8;">
            <h2 style="color:#90e0ef;text-align:center;">🎓 Student Score Predictor</h2>
            <p>Hello <strong>{full_name}</strong>,</p>
            <p>Your OTP verification code is:</p>
            <div style="text-align:center;margin:20px 0;">
                <span style="font-size:2.5rem;font-weight:900;color:#00b4d8;
                    letter-spacing:12px;background:rgba(0,180,216,0.1);
                    padding:12px 24px;border-radius:12px;border:2px solid #00b4d8;">
                    {otp_code}
                </span>
            </div>
            <p style="font-size:0.85rem;">Valid for <strong>10 minutes</strong>.</p>
        </div></body></html>"""
        msg.attach(MIMEText(html_body, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        return True, "OTP sent successfully!"
    except Exception as e:
        return False, f"Email error: {str(e)}"

def store_otp(email, otp):
    store = load_otp_store()
    store[email] = {"otp": otp, "timestamp": str(datetime.now()), "verified": False}
    save_otp_store(store)

def verify_otp(email, entered_otp):
    store = load_otp_store()
    if email not in store:
        return False, "No OTP found. Please request again."
    record = store[email]
    elapsed = (datetime.now() - datetime.fromisoformat(record["timestamp"])).total_seconds()
    if elapsed > 600:
        return False, "OTP expired. Please request a new one."
    if record["otp"] == entered_otp:
        store[email]["verified"] = True
        save_otp_store(store)
        return True, "✅ OTP Verified!"
    return False, "❌ Invalid OTP. Try again."

# =====================================
# PDF REPORT
# =====================================
def generate_pdf_report(username, final_score, user_data, hours, attendance, previous, sleep, recommendations):
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style   = ParagraphStyle('T', parent=styles['Heading1'], fontSize=22,
        textColor=colors.HexColor('#0077b6'), alignment=1, spaceAfter=20)
    heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#023e8a'), spaceAfter=10)
    normal_style  = ParagraphStyle('N', parent=styles['Normal'], fontSize=10, spaceAfter=5)

    story = []
    story.append(Paragraph("🎓 Student Score Predictor — Official Report", title_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Student Information", heading_style))
    story.append(Paragraph(f"Name: {user_data.get('full_name', username)}", normal_style))
    story.append(Paragraph(f"Username: {username}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Prediction Results", heading_style))
    score_data  = [["Metric", "Value"], ["Predicted Exam Score", f"{final_score}/100"]]
    score_table = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR',  (0,0), (1,0), colors.whitesmoke),
        ('ALIGN',      (0,0), (1,-1), 'CENTER'),
        ('FONTNAME',   (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (1,1), colors.HexColor('#caf0f8')),
        ('GRID',       (0,0), (1,1), 1, colors.HexColor('#90e0ef'))
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Input Details", heading_style))
    input_data = [
        ["Parameter","Value"],
        ["Study Hours",    f"{hours} hours"],
        ["Attendance",     f"{attendance}%"],
        ["Previous Score", f"{previous}/100"],
        ["Sleep Hours",    f"{sleep} hours"]
    ]
    input_table = Table(input_data, colWidths=[2.5*inch, 2.5*inch])
    input_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR',  (0,0), (1,0), colors.whitesmoke),
        ('ALIGN',      (0,0), (1,-1), 'CENTER'),
        ('FONTNAME',   (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (1,-1), colors.HexColor('#caf0f8')),
        ('GRID',       (0,0), (1,-1), 1, colors.HexColor('#90e0ef'))
    ]))
    story.append(input_table)
    story.append(Spacer(1, 0.15*inch))
    if recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph(
        "Generated by Student Score Predictor — AI Powered Academic Tool",
        ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================
# SESSION STATE
# =====================================
defaults = {
    'logged_in': False, 'username': '', 'user_role': '',
    'auth_mode': 'home',
    'signup_role': 'student', 'theme': 'dark',
    'show_profile_edit': False, 'last_pdf': None, 'last_score': None,
    'last_recs': [], 'last_inputs': {},
    'pending_signup_data': {},
    'otp_email': '', 'otp_verified': False,
    'study_hours_history': [], 'attendance_history': [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

all_history = load_history()

# =====================================
# ✨ UPGRADED GLOBAL CSS
# =====================================
GLOBAL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

* { font-family: 'DM Sans', sans-serif; box-sizing: border-box; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

/* ── BACKGROUND ── */
.stApp {
    background:
        radial-gradient(ellipse at 15% 5%,  rgba(0,180,216,0.18) 0%, transparent 55%),
        radial-gradient(ellipse at 85% 90%, rgba(3,4,94,0.55)    0%, transparent 55%),
        linear-gradient(160deg, #000814 0%, #03045e 40%, #023e8a 70%, #000814 100%);
    min-height: 100vh;
}

/* animated floating dots in bg */
.stApp::before {
    content: '';
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background-image:
        radial-gradient(circle, rgba(0,180,216,0.06) 1px, transparent 1px),
        radial-gradient(circle, rgba(0,119,182,0.04) 1px, transparent 1px);
    background-size: 60px 60px, 120px 120px;
    pointer-events: none; z-index: 0;
}

.main .block-container {
    background: rgba(3,4,94,0.15);
    border-radius: 28px;
    padding: 2.5rem 3rem;
    border: 1px solid rgba(0,180,216,0.18);
    backdrop-filter: blur(18px);
    box-shadow:
        0 0 80px rgba(0,119,182,0.1),
        inset 0 1px 0 rgba(0,180,216,0.12),
        inset 0 -1px 0 rgba(0,180,216,0.05);
    position: relative; z-index: 1;
}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(2,3,60,0.98) 0%, rgba(0,8,20,0.99) 100%);
    border-right: 1px solid rgba(0,180,216,0.18);
}

/* ── TEXT ── */
.stApp { color: #e0f4ff !important; }
.stApp p, .stApp span, .stApp div, .stApp label { color: #e0f4ff !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4 { color: #90e0ef !important; }
[data-testid="stSidebar"] * { color: #e0f4ff !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #90e0ef !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #90e0ef !important; }
.stAlert p, .stAlert div { color: #ffffff !important; }

/* ── INPUTS ── */
.stNumberInput input, .stTextInput input, .stDateInput input,
.stTextAreaInput textarea, [data-baseweb="input"] input {
    background: rgba(0,20,60,0.65) !important;
    border: 1.5px solid rgba(0,180,216,0.35) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
    padding: 0.55rem 0.9rem !important;
    font-size: 0.88rem !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #00b4d8 !important;
    box-shadow: 0 0 0 3px rgba(0,180,216,0.2) !important;
    outline: none !important;
}
div[data-baseweb="select"] > div {
    background: rgba(0,20,60,0.65) !important;
    border: 1.5px solid rgba(0,180,216,0.35) !important;
    border-radius: 14px !important;
    color: #ffffff !important;
}
div[data-baseweb="select"] span { color: #ffffff !important; }
div[data-baseweb="popover"] div { background: #020a22 !important; border: 1px solid #0077b6 !important; }
li[role="option"] { color: #ffffff !important; }
li[role="option"]:hover { background: rgba(0,119,182,0.5) !important; }

/* ── BUTTONS ── */
.stButton > button {
    background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.55rem 1.6rem !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.3px !important;
    font-size: 0.88rem !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 18px rgba(0,119,182,0.35) !important;
    position: relative; overflow: hidden;
}
.stButton > button::after {
    content:''; position:absolute; top:50%; left:50%;
    width:0; height:0;
    background:rgba(255,255,255,0.15);
    border-radius:50%;
    transform:translate(-50%,-50%);
    transition: width 0.5s, height 0.5s;
}
.stButton > button:hover::after { width:300px; height:300px; }
.stButton > button:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 35px rgba(0,180,216,0.55) !important;
    background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%) !important;
    color: #03045e !important;
}
.stButton > button:active { transform: translateY(-1px) scale(0.99) !important; }

[data-testid="stDownloadButton"] button {
    background: rgba(0,180,216,0.1) !important;
    border: 1.5px solid #00b4d8 !important;
    color: #ffffff !important;
    border-radius: 50px !important;
    padding: 0.4rem 1.1rem !important;
    font-size: 0.82rem !important;
    transition: all 0.3s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(0,180,216,0.25) !important;
    transform: translateY(-2px) !important;
}

/* ── CARDS ── */
.glass-card {
    background: rgba(3,4,94,0.28);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 20px; padding: 1.4rem;
    backdrop-filter: blur(12px);
    transition: all 0.3s ease;
}
.glass-card:hover {
    border-color: rgba(0,180,216,0.45);
    transform: translateY(-3px);
    box-shadow: 0 12px 40px rgba(0,119,182,0.2);
}

.result-card {
    background: linear-gradient(135deg, rgba(3,4,94,0.85) 0%, rgba(0,119,182,0.8) 100%);
    border: 1.5px solid #00b4d8;
    border-radius: 24px; padding: 2rem; text-align: center; margin: 1rem 0;
    box-shadow: 0 10px 40px rgba(0,119,182,0.3), inset 0 1px 0 rgba(144,224,239,0.2);
    animation: resultPop 0.5s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes resultPop {
    from { opacity:0; transform:scale(0.85) translateY(20px); }
    to   { opacity:1; transform:scale(1) translateY(0); }
}
.result-score {
    color: #caf0f8 !important; font-weight: 900 !important;
    font-size: 3.5rem !important; font-family: 'Syne', sans-serif !important;
    line-height: 1;
}
.result-label {
    color: #90e0ef !important; font-size: 0.6rem !important;
    letter-spacing: 4px !important; text-transform: uppercase; margin-bottom: 0.5rem;
}

.stat-card {
    background: rgba(3,4,94,0.3);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 16px; padding: 0.9rem; text-align: center;
    transition: all 0.3s !important; backdrop-filter: blur(8px);
}
.stat-card:hover {
    border-color: #00b4d8 !important;
    transform: translateY(-4px);
    box-shadow: 0 8px 25px rgba(0,180,216,0.2);
}
.stat-value { font-size: 1.7rem; font-weight: 800; color: #00b4d8 !important; font-family: 'Syne', sans-serif !important; }
.stat-value-red { font-size: 1.7rem; font-weight: 800; color: #f87171 !important; font-family: 'Syne', sans-serif !important; }
.stat-label { font-size: 0.58rem; color: #90e0ef !important; letter-spacing: 1px; text-transform: uppercase; margin-top:0.2rem; }

.section-header {
    font-family: 'Syne', sans-serif;
    color: #90e0ef !important;
    font-size: 1.05rem; font-weight: 700;
    margin: 1.4rem 0 0.6rem;
    padding-left: 0.8rem;
    border-left: 3px solid #00b4d8;
}

/* ── PROFILE CARD ── */
.profile-card { text-align: center; padding: 0.8rem; }
.profile-name { font-size: 1rem; font-weight: 700; color: #ffffff !important; font-family: 'Syne', sans-serif !important; }
.profile-role {
    font-size: 0.6rem; padding: 0.2rem 0.8rem; border-radius: 50px;
    display: inline-block; background: rgba(0,180,216,0.12);
    border: 1px solid rgba(0,180,216,0.35); color: #90e0ef !important;
    letter-spacing: 1.5px; text-transform: uppercase;
}
.avatar-circle {
    width: 76px; height: 76px; border-radius: 50%;
    border: 2.5px solid #00b4d8;
    box-shadow: 0 0 20px rgba(0,180,216,0.4), 0 4px 15px rgba(0,119,182,0.3);
    margin: 0 auto 0.6rem; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0077b6, #00b4d8); font-size: 1.9rem;
}
.avatar-circle img { width: 100%; height: 100%; object-fit: cover; }

/* ── HOME HERO ── */
.home-hero {
    text-align: center;
    padding: 4rem 2rem 3.5rem;
    position: relative; overflow: hidden;
    border-radius: 28px; margin-bottom: 2rem;
}
.home-hero::before {
    content: '';
    position: absolute; inset: 0;
    background:
        radial-gradient(ellipse at 30% 30%, rgba(0,180,216,0.25) 0%, transparent 60%),
        radial-gradient(ellipse at 70% 70%, rgba(3,4,94,0.6) 0%, transparent 60%),
        linear-gradient(135deg, rgba(3,4,94,0.92), rgba(0,119,182,0.88));
    border-radius: 28px;
    border: 1px solid rgba(0,180,216,0.25);
    z-index: 0;
}
.home-hero > * { position: relative; z-index: 1; }
.home-hero h1 { font-size: 3rem !important; color: #ffffff !important; letter-spacing: -1px; margin: 0.5rem 0; }
.home-hero .sub { color: #caf0f8 !important; font-size: 1.05rem; opacity: 0.9; }
.home-hero .tag { color: #90e0ef !important; font-size: 0.75rem; opacity: 0.7; }
.hero-icon { font-size: 4.5rem; display: block; margin-bottom: 0.5rem; animation: float 3s ease-in-out infinite; }
@keyframes float { 0%,100%{transform:translateY(0)} 50%{transform:translateY(-10px)} }

.feature-card {
    background: rgba(3,4,94,0.3);
    border: 1px solid rgba(0,180,216,0.18);
    border-radius: 20px; padding: 1.4rem; text-align: center;
    transition: all 0.35s cubic-bezier(0.34,1.56,0.64,1);
    backdrop-filter: blur(10px); height: 100%;
}
.feature-card:hover {
    border-color: rgba(0,180,216,0.5);
    transform: translateY(-6px) scale(1.02);
    box-shadow: 0 16px 40px rgba(0,119,182,0.25);
    background: rgba(3,4,94,0.5);
}
.feature-card h3 { color: #90e0ef !important; font-size: 0.95rem !important; margin: 0.4rem 0; }
.feature-card p { color: #c0e0f0 !important; font-size: 0.78rem; line-height: 1.5; }
.feature-icon { font-size: 2.2rem; margin-bottom: 0.5rem; }

/* ── AUTH FORM ── */
.auth-container {
    background: rgba(3,4,94,0.35);
    border: 1px solid rgba(0,180,216,0.22);
    border-radius: 24px; padding: 2.2rem 2rem;
    backdrop-filter: blur(16px);
    box-shadow: 0 20px 60px rgba(0,0,0,0.3), inset 0 1px 0 rgba(0,180,216,0.15);
    animation: slideUp 0.4s cubic-bezier(0.34,1.56,0.64,1);
}
@keyframes slideUp {
    from { opacity:0; transform: translateY(30px); }
    to   { opacity:1; transform: translateY(0); }
}
.auth-title { font-size: 1.5rem; font-weight: 800; color: #ffffff !important; font-family: 'Syne', sans-serif !important; text-align: center; }
.auth-sub { color: #90e0ef !important; font-size: 0.78rem; text-align: center; margin-bottom: 1.4rem; }

/* OTP Box */
.otp-box {
    background: rgba(0,119,182,0.08);
    border: 1.5px solid rgba(0,180,216,0.3);
    border-radius: 18px; padding: 1.4rem; margin: 0.8rem 0;
    position: relative;
}
.otp-badge {
    display: inline-flex; align-items: center; gap: 0.4rem;
    background: rgba(0,180,216,0.12); border: 1px solid rgba(0,180,216,0.3);
    border-radius: 50px; padding: 0.25rem 0.8rem; font-size: 0.7rem;
    color: #90e0ef !important; letter-spacing: 1px; text-transform: uppercase;
    margin-bottom: 0.8rem;
}

/* Share Box */
.share-box {
    background: rgba(0,119,182,0.08);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 18px; padding: 1.2rem; margin: 0.8rem 0;
}

/* WhatsApp Button */
.wa-btn {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: linear-gradient(135deg, #25d366, #128c7e);
    color: white !important; border: none; border-radius: 50px;
    padding: 0.55rem 1.4rem; font-size: 0.85rem; font-weight: 700;
    cursor: pointer; text-decoration: none !important;
    transition: all 0.3s; box-shadow: 0 4px 15px rgba(37,211,102,0.35);
    font-family: 'Syne', sans-serif;
}
.wa-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(37,211,102,0.5); }

.email-btn {
    display: inline-flex; align-items: center; gap: 0.5rem;
    background: linear-gradient(135deg, #0077b6, #00b4d8);
    color: white !important; border: none; border-radius: 50px;
    padding: 0.55rem 1.4rem; font-size: 0.85rem; font-weight: 700;
    cursor: pointer; text-decoration: none !important;
    transition: all 0.3s; box-shadow: 0 4px 15px rgba(0,119,182,0.35);
    font-family: 'Syne', sans-serif;
}
.email-btn:hover { transform: translateY(-2px); box-shadow: 0 8px 25px rgba(0,180,216,0.5); }

/* Role Toggle */
.role-active {
    background: linear-gradient(135deg, #0077b6, #00b4d8) !important;
    color: white !important; border: none !important;
}

hr { border-color: rgba(0,180,216,0.12) !important; margin: 1rem 0 !important; }
[data-testid="stFileUploader"] {
    background: rgba(0,20,60,0.4) !important;
    border: 2px dashed rgba(0,180,216,0.3) !important;
    border-radius: 14px !important;
}
.stNumberInput button {
    background: rgba(0,20,60,0.6) !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
    color: #00b4d8 !important; border-radius: 8px !important;
}
.stNumberInput button:hover { background: #0077b6 !important; color: white !important; }
.stCheckbox label { color: #e0f4ff !important; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg, #0077b6, #00b4d8) !important; border-radius: 10px; }

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(0,180,216,0.3); border-radius: 6px; }
::-webkit-scrollbar-thumb:hover { background: rgba(0,180,216,0.6); }
</style>
"""

def apply_theme():
    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)

# =====================================
# HOME PAGE — UPGRADED
# =====================================
def show_home_page():
    apply_theme()

    # Minimal hero — big visual, small text
    st.markdown("""
    <div class="home-hero">
        <span class="hero-icon">🎓</span>
        <h1>Student Score Predictor</h1>
        <p class="sub">AI-Powered Academic Performance Analysis</p>
        <p class="tag" style="margin-top:0.6rem;font-size:0.72rem;letter-spacing:2px;text-transform:uppercase;">
            Predict · Track · Improve
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Feature cards — icons + short text
    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🤖", "AI Prediction",       "ML model estimates your exam score from study habits"),
        ("📊", "Visual Progress",     "Interactive charts track your score and attendance trends"),
        ("💡", "Smart Tips",          "Personalised recommendations to boost your performance"),
        ("📄", "PDF + WhatsApp",      "Download report & share directly on WhatsApp"),
    ]
    for col, (icon, title, desc) in zip([f1,f2,f3,f4], features):
        with col:
            st.markdown(f"""
            <div class="feature-card">
                <div class="feature-icon">{icon}</div>
                <h3>{title}</h3>
                <p>{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Demo graph on home
    is_dark      = True
    bg_col       = "rgba(0,0,0,0)"
    txt_col      = "#caf0f8"
    grid_col     = "rgba(0,180,216,0.12)"
    sample_scores= [58, 63, 67, 71, 74, 78, 82]
    attempts_demo= [f"#{i}" for i in range(1, 8)]
    fig_demo     = go.Figure()
    fig_demo.add_trace(go.Scatter(
        x=attempts_demo, y=sample_scores, mode='lines+markers',
        name='Score', line=dict(color='#00b4d8', width=3),
        marker=dict(size=8, color='#00b4d8', line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(0,180,216,0.06)'
    ))
    fig_demo.add_hline(y=60, line_dash="dash", line_color="#f87171",
                       annotation_text="Pass", annotation_font_color="#f87171")
    fig_demo.add_hline(y=85, line_dash="dash", line_color="#34d399",
                       annotation_text="Excellent", annotation_font_color="#34d399")
    fig_demo.update_layout(
        title=dict(text="Sample Score Progress (Demo)", font=dict(color=txt_col, size=13)),
        paper_bgcolor=bg_col, plot_bgcolor=bg_col,
        font=dict(color=txt_col), height=240,
        margin=dict(l=10,r=10,t=40,b=10), showlegend=False,
        xaxis=dict(gridcolor=grid_col, color=txt_col),
        yaxis=dict(gridcolor=grid_col, color=txt_col, range=[40,100]),
    )
    st.plotly_chart(fig_demo, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        if st.button("🚀 Get Started — Sign Up / Login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()

    st.markdown("""
    <p style="text-align:center;font-size:0.55rem;margin-top:1.2rem;opacity:0.4;letter-spacing:1px;">
        🔒 SECURE · AI POWERED · STUDENT SCORE PREDICTOR v3.0
    </p>
    """, unsafe_allow_html=True)

# =====================================
# AUTH PAGE — UPGRADED FORMS
# =====================================
def show_auth_page():
    apply_theme()
    users = load_users()

    if st.button("← Home", key="back_home_btn"):
        st.session_state.auth_mode = "home"
        st.rerun()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        # ── LOGIN PAGE ──
        if st.session_state.auth_mode == "login":
            st.markdown("""
            <div class="auth-container">
            """, unsafe_allow_html=True)
            st.markdown('<div class="auth-title">👋 Welcome Back</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Sign in to your account to continue</div>', unsafe_allow_html=True)

            username = st.text_input("👤 Username", placeholder="Enter your username", key="login_user")
            password = st.text_input("🔒 Password", type="password", placeholder="Enter your password", key="login_pass")

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True, key="login_btn"):
                if username and password:
                    if username in users and users[username]["password"] == hash_password(password):
                        st.session_state.logged_in  = True
                        st.session_state.username   = username
                        st.session_state.user_role  = users[username]["role"]
                        h = all_history.get(username, {})
                        if isinstance(h, dict):
                            st.session_state.study_hours_history = h.get("study_hours", [])
                            st.session_state.attendance_history  = h.get("attendance", [])
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("Please fill all fields")

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown('<p style="text-align:center;font-size:0.78rem;color:#90e0ef !important;">New here? Create your account</p>', unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🎓 Student Sign Up", use_container_width=True):
                    st.session_state.auth_mode  = "signup"
                    st.session_state.signup_role= "student"
                    st.rerun()
            with c2:
                if st.button("👨‍👩‍👧 Parent Sign Up", use_container_width=True):
                    st.session_state.auth_mode  = "signup"
                    st.session_state.signup_role= "parent"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        # ── SIGNUP PAGE ──
        elif st.session_state.auth_mode == "signup":
            role = st.session_state.signup_role

            st.markdown('<div class="auth-container">', unsafe_allow_html=True)
            st.markdown(f'<div class="auth-title">✨ Create Account</div>', unsafe_allow_html=True)
            st.markdown('<div class="auth-sub">Fill in your details to get started</div>', unsafe_allow_html=True)

            # Role selector
            st.markdown("**Account Type**")
            rc1, rc2 = st.columns(2)
            with rc1:
                if st.button("🎓 Student" + (" ✓" if role=="student" else ""), use_container_width=True):
                    st.session_state.signup_role = "student"; st.rerun()
            with rc2:
                if st.button("👨‍👩‍👧 Parent" + (" ✓" if role=="parent" else ""), use_container_width=True):
                    st.session_state.signup_role = "parent"; st.rerun()

            st.markdown("<hr>", unsafe_allow_html=True)
            st.markdown("**📝 Personal Information**")

            # Common fields
            full_name = st.text_input("Full Name *", placeholder="Your full name", key="su_name")
            username  = st.text_input("Username *", placeholder="Choose a unique username", key="su_user")

            col_p1, col_p2 = st.columns(2)
            with col_p1:
                password = st.text_input("Password *", type="password", placeholder="Min 4 characters", key="su_pass")
            with col_p2:
                confirm  = st.text_input("Confirm Password *", type="password", placeholder="Repeat password", key="su_confirm")

            st.markdown("<hr>", unsafe_allow_html=True)

            # Role-specific fields
            if role == "student":
                st.markdown("**🎓 Student Details**")
                c1, c2 = st.columns(2)
                with c1:
                    dob   = st.date_input("Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_dob")
                    grade = st.selectbox("Grade / Class", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_grade")
                with c2:
                    school= st.text_input("School / College Name", placeholder="Institution name", key="su_school")
            else:
                st.markdown("**👨‍👩‍👧 Parent Details**")
                c1, c2 = st.columns(2)
                with c1:
                    child_name  = st.text_input("Child's Full Name", placeholder="Child's name", key="su_child")
                    child_dob   = st.date_input("Child's DOB", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_cdob")
                with c2:
                    child_grade = st.selectbox("Child's Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_cgrade")
                    relation    = st.selectbox("Your Relationship", ["Father","Mother","Guardian"], key="su_relation")

            st.markdown("<hr>", unsafe_allow_html=True)

            # OTP Section
            st.markdown('<div class="otp-box">', unsafe_allow_html=True)
            st.markdown('<div class="otp-badge">🔐 Email OTP Verification</div>', unsafe_allow_html=True)
            st.markdown("**Email Address** (OTP will be sent here)")
            email = st.text_input("Email *", placeholder="your@email.com", key="su_email", label_visibility="collapsed")

            if st.button("📨 Send OTP to Email", use_container_width=True, key="send_otp_btn"):
                if not email:
                    st.warning("Please enter your email address first.")
                else:
                    otp = generate_otp()
                    store_otp(email, otp)
                    success, msg = send_otp_email(email, otp, full_name or "User")
                    if success:
                        st.success(f"✅ OTP sent to **{email}**! Check your inbox.")
                        st.session_state.otp_email = email
                    else:
                        st.warning(f"⚠️ Email not configured yet. For testing, your OTP is: **{otp}**")
                        st.caption("Set EMAIL_SENDER & EMAIL_PASSWORD in the code to enable real emails.")
                        st.session_state.otp_email = email

            entered_otp = st.text_input("Enter 6-digit OTP", placeholder="______", key="otp_input",
                                        max_chars=6, label_visibility="visible")
            st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("✅ Verify OTP & Create Account", use_container_width=True, key="create_acc_btn"):
                if not username or not password or not full_name or not email:
                    st.warning("Please fill all required fields (marked with *).")
                elif password != confirm:
                    st.error("❌ Passwords don't match.")
                elif len(password) < 4:
                    st.warning("Password must be at least 4 characters.")
                elif username in users:
                    st.error("❌ Username already taken. Choose another.")
                elif not entered_otp:
                    st.warning("Please enter the OTP sent to your email.")
                else:
                    ok, otp_msg = verify_otp(email, entered_otp)
                    if not ok:
                        st.error(otp_msg)
                    else:
                        data = {
                            "password": hash_password(password),
                            "role": role,
                            "full_name": full_name,
                            "email": email,
                            "created_at": str(pd.Timestamp.now())
                        }
                        if role == "student":
                            data["dob"]    = str(dob)
                            data["age"]    = calculate_age(dob)
                            data["grade"]  = grade
                            data["school"] = school
                        else:
                            data["child_name"]  = child_name
                            data["child_dob"]   = str(child_dob)
                            data["child_age"]   = calculate_age(child_dob)
                            data["child_grade"] = child_grade
                            data["relation"]    = relation
                        users[username] = data
                        save_users(users)
                        st.success("🎉 Account created successfully! Please sign in.")
                        st.session_state.auth_mode = "login"
                        st.rerun()

            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True, key="back_login_btn"):
                st.session_state.auth_mode = "login"; st.rerun()

            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1rem;opacity:0.35;letter-spacing:1px;">🔒 SECURE PORTAL · AI POWERED</p>', unsafe_allow_html=True)

# =====================================
# LOAD MODEL
# =====================================
@st.cache_resource
def load_models():
    model   = joblib.load("student_model.pkl")
    columns = joblib.load("model_columns.pkl")
    return model, columns

# =====================================
# SIDEBAR
# =====================================
def show_sidebar(user_data):
    with st.sidebar:
        pic_b64   = get_profile_pic_base64(st.session_state.username)
        role_text = "Student" if st.session_state.user_role == "student" else "Parent"
        role_icon = "🎓" if st.session_state.user_role == "student" else "👨‍👩‍👧"
        avatar_html = f'<img src="data:image/jpeg;base64,{pic_b64}" />' if pic_b64 else role_icon

        st.markdown(f"""
        <div class="profile-card">
            <div class="avatar-circle">{avatar_html}</div>
            <div class="profile-name">{user_data.get('full_name', st.session_state.username)}</div>
            <div class="profile-role">{role_text}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("✏️ Edit Profile Picture", use_container_width=True, key="toggle_pic_btn"):
            st.session_state.show_profile_edit = not st.session_state.show_profile_edit
            st.rerun()

        if st.session_state.show_profile_edit:
            up = st.file_uploader("Upload Profile Picture", type=["jpg","jpeg","png"],
                                  key="pic_up", label_visibility="collapsed")
            if up:
                save_profile_pic(st.session_state.username, up.read())
                st.success("✅ Updated!")
                st.session_state.show_profile_edit = False
                st.rerun()

        st.markdown("---")
        st.markdown("### 👤 Account")
        st.markdown(f"**User:** `{st.session_state.username}`")
        st.markdown(f"**Name:** {user_data.get('full_name','N/A')}")
        st.markdown(f"**Email:** {user_data.get('email','N/A')}")
        if st.session_state.user_role == "student":
            st.markdown(f"**Age:** {user_data.get('age','N/A')}")
            st.markdown(f"**Grade:** {user_data.get('grade','N/A')}")
            st.markdown(f"**School:** {user_data.get('school','N/A')}")
        else:
            st.markdown(f"**Child:** {user_data.get('child_name','N/A')}")
            st.markdown(f"**Child Grade:** {user_data.get('child_grade','N/A')}")
            st.markdown(f"**Relation:** {user_data.get('relation','N/A')}")

        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()

# =====================================
# PLOTLY GRAPH HELPERS
# =====================================
def plotly_layout(title_txt, xtitle, ytitle, yrange=None):
    bg  = "rgba(0,0,0,0)"
    txt = "#caf0f8"
    grd = "rgba(0,180,216,0.1)"
    layout = dict(
        title=dict(text=title_txt, font=dict(color=txt, size=13)),
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(color=txt), height=320,
        margin=dict(l=10, r=10, t=45, b=10),
        xaxis=dict(title=xtitle, gridcolor=grd, color=txt, showgrid=True),
        yaxis=dict(title=ytitle, gridcolor=grd, color=txt, showgrid=True),
        showlegend=True,
        legend=dict(font=dict(color=txt)),
    )
    if yrange:
        layout["yaxis"]["range"] = yrange
    return layout

def graph_score_history(scores):
    attempts = [f"#{i}" for i in range(1, len(scores)+1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=attempts, y=scores, mode='lines+markers', name='Your Score',
        line=dict(color='#00b4d8', width=3),
        marker=dict(size=9, color='#00b4d8', line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(0,180,216,0.07)'
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#f87171",
                  annotation_text="Pass (60)", annotation_font_color="#f87171")
    fig.add_hline(y=70, line_dash="dot", line_color="#fbbf24",
                  annotation_text="Good (70)", annotation_font_color="#fbbf24")
    fig.add_hline(y=85, line_dash="dash", line_color="#34d399",
                  annotation_text="Excellent (85)", annotation_font_color="#34d399")
    fig.update_layout(**plotly_layout("📈 Score History", "Attempt", "Score", [30,105]))
    return fig

def graph_hours_vs_score(hours_list, scores):
    if len(hours_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours_list, y=scores, mode='markers', name='Attempts',
        marker=dict(size=11, color='#00b4d8', line=dict(color='white', width=2), symbol='circle'),
        text=[f"Attempt #{i+1}<br>Hours: {h}h<br>Score: {s}" for i,(h,s) in enumerate(zip(hours_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    if len(hours_list) >= 3:
        z = np.polyfit(hours_list, scores, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(hours_list), max(hours_list), 100)
        fig.add_trace(go.Scatter(
            x=x_line.tolist(), y=p(x_line).tolist(),
            mode='lines', name='Trend',
            line=dict(color='#90e0ef', width=2, dash='dash')
        ))
    fig.update_layout(**plotly_layout("📖 Hours Studied vs Score", "Study Hours / Day", "Score", [30,105]))
    return fig

def graph_attendance_vs_score(att_list, scores):
    if len(att_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=att_list, y=scores, mode='markers', name='Attempts',
        marker=dict(size=11, color='#0077b6', line=dict(color='white', width=2), symbol='diamond'),
        text=[f"Attempt #{i+1}<br>Attendance: {a}%<br>Score: {s}" for i,(a,s) in enumerate(zip(att_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    if len(att_list) >= 3:
        z = np.polyfit(att_list, scores, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(att_list), max(att_list), 100)
        fig.add_trace(go.Scatter(
            x=x_line.tolist(), y=p(x_line).tolist(),
            mode='lines', name='Trend',
            line=dict(color='#90e0ef', width=2, dash='dash')
        ))
    fig.update_layout(**plotly_layout("🏫 Attendance vs Score", "Attendance (%)", "Score", [30,105]))
    return fig

# ✨ NEW: Radar / Spider Chart — Student Performance Profile
def graph_radar_performance(hours, attendance, previous, sleep, motivation, teacher, resources, peer):
    """NEW Graph 4 — Radar chart showing student's academic profile across all dimensions"""
    # Normalize all inputs to 0–100 scale
    hours_score    = min(hours / 10 * 100, 100)
    attendance_n   = attendance
    previous_n     = previous
    sleep_score    = min(sleep / 9 * 100, 100)
    motivation_map = {"Low": 30, "Medium": 65, "High": 95}
    teacher_map    = {"Poor": 25, "Average": 60, "Good": 90}
    resources_map  = {"Low": 25, "Medium": 60, "High": 90}
    peer_map       = {"Negative": 20, "Neutral": 55, "Positive": 90}

    categories = [
        "Study Hours", "Attendance", "Previous Score",
        "Sleep Quality", "Motivation", "Teacher Quality",
        "Resources", "Peer Influence"
    ]
    values = [
        round(hours_score, 1),
        round(attendance_n, 1),
        round(previous_n, 1),
        round(sleep_score, 1),
        motivation_map.get(motivation, 50),
        teacher_map.get(teacher, 50),
        resources_map.get(resources, 50),
        peer_map.get(peer, 50),
    ]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill='toself',
        fillcolor='rgba(0,180,216,0.12)',
        line=dict(color='#00b4d8', width=2.5),
        marker=dict(size=8, color='#00b4d8', line=dict(color='white', width=1.5)),
        name='Your Profile',
        hovertemplate='<b>%{theta}</b><br>Score: %{r:.0f}/100<extra></extra>'
    ))
    # Benchmark line (ideal student = 80 on all)
    ideal = [80] * len(categories)
    fig.add_trace(go.Scatterpolar(
        r=ideal + [ideal[0]],
        theta=categories + [categories[0]],
        mode='lines',
        line=dict(color='rgba(52,211,153,0.4)', width=1.5, dash='dot'),
        name='Target (80)',
        hoverinfo='skip'
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(3,4,94,0.2)',
            radialaxis=dict(
                visible=True, range=[0,100],
                color='#90e0ef', gridcolor='rgba(0,180,216,0.15)',
                tickfont=dict(color='#90e0ef', size=9),
                tickvals=[20,40,60,80,100]
            ),
            angularaxis=dict(
                color='#caf0f8',
                gridcolor='rgba(0,180,216,0.12)',
                tickfont=dict(color='#caf0f8', size=10)
            )
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#caf0f8'),
        height=380,
        margin=dict(l=40, r=40, t=50, b=40),
        showlegend=True,
        legend=dict(font=dict(color='#caf0f8'), bgcolor='rgba(3,4,94,0.4)', bordercolor='rgba(0,180,216,0.2)'),
        title=dict(text="🎯 Your Academic Performance Profile", font=dict(color='#90e0ef', size=13))
    )
    return fig, values, categories

# =====================================
# MAIN APP
# =====================================
def show_main_app():
    apply_theme()
    users     = load_users()
    user_data = users.get(st.session_state.username, {})
    show_sidebar(user_data)

    st.markdown("<h1 style='text-align:center;letter-spacing:-1px;font-size:2rem;'>🎓 Student Score Predictor</h1>", unsafe_allow_html=True)

    if st.session_state.user_role == "parent":
        child_name = user_data.get("child_name", "Child")
        st.info(f"👨‍👩‍👧 Predicting for: **{child_name}**")

    model, columns = load_models()

    # ── Input Form ──
    st.markdown('<div class="section-header">📋 Input Parameters</div>', unsafe_allow_html=True)

    with st.container():
        col1, col2 = st.columns(2)
        with col1:
            hours      = st.number_input("📖 Hours Studied / Day", min_value=0.0, max_value=24.0, value=5.0, step=0.5)
            attendance = st.number_input("🏫 Attendance (%)",       min_value=0.0, max_value=100.0, value=75.0, step=5.0)
            previous   = st.number_input("📊 Previous Score",       min_value=0.0, max_value=100.0, value=60.0, step=5.0)
            sleep      = st.number_input("💤 Sleep Hours / Night",  min_value=0.0, max_value=12.0,  value=7.0, step=0.5)
            motivation = st.selectbox("🔥 Motivation Level",  ["Low", "Medium", "High"])
            teacher    = st.selectbox("👩‍🏫 Teacher Quality",   ["Poor", "Average", "Good"])
            school_t   = st.selectbox("🏛️ School Type",        ["Public", "Private"])
        with col2:
            internet   = st.selectbox("🌐 Internet Access",          ["Yes", "No"])
            income     = st.selectbox("💰 Family Income",            ["Low", "Medium", "High"])
            parent_inv = st.selectbox("👨‍👩‍👦 Parental Involvement",  ["Low", "Medium", "High"])
            education  = st.selectbox("🎓 Parent Education",         ["School", "College"])
            peer       = st.selectbox("👥 Peer Influence",           ["Negative", "Neutral", "Positive"])
            resources  = st.selectbox("📚 Learning Resources",       ["Low", "Medium", "High"])
            activities = st.selectbox("⚽ Extracurricular Activities", ["Yes", "No"])

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Predict My Score", use_container_width=True, key="predict_btn"):
        data = {
            "Hours_Studied": hours, "Attendance": attendance, "Previous_Scores": previous,
            "Sleep_Hours": sleep, "Motivation_Level": motivation, "Teacher_Quality": teacher,
            "School_Type": school_t, "Internet_Access": internet, "Family_Income": income,
            "Parental_Involvement": parent_inv, "Parental_Education_Level": education,
            "Peer_Influence": peer, "Learning_Resources": resources,
            "Extracurricular_Activities": activities
        }
        input_df = pd.DataFrame([data])
        input_df = pd.get_dummies(input_df)
        input_df = input_df.reindex(columns=columns, fill_value=0)
        prediction  = model.predict(input_df)
        final_score = max(40, min(100, int(round(prediction[0]))))

        uname = st.session_state.username
        if uname not in all_history:
            all_history[uname] = {"scores": [], "study_hours": [], "attendance": []}
        if isinstance(all_history[uname], list):
            old_scores = all_history[uname]
            all_history[uname] = {"scores": old_scores, "study_hours": [], "attendance": []}

        all_history[uname]["scores"].append(final_score)
        all_history[uname]["study_hours"].append(float(hours))
        all_history[uname]["attendance"].append(float(attendance))

        for key in ["scores","study_hours","attendance"]:
            if len(all_history[uname][key]) > 15:
                all_history[uname][key] = all_history[uname][key][-15:]

        save_history(all_history)
        st.session_state.study_hours_history = all_history[uname]["study_hours"]
        st.session_state.attendance_history  = all_history[uname]["attendance"]

        # Recommendations
        recs = []
        if hours < 6:           recs.append("Increase study hours to 6–8 daily for better results")
        if attendance < 75:     recs.append("Improve attendance to at least 80%")
        if sleep < 7:           recs.append("Get 7–9 hours of quality sleep daily")
        if motivation == "Low": recs.append("Set clear daily goals to boost motivation")
        if teacher == "Poor":   recs.append("Seek additional tutoring or online resources")
        if resources == "Low":  recs.append("Utilise free platforms (Khan Academy, YouTube)")
        if peer == "Negative":  recs.append("Join positive study groups")

        st.session_state.last_score  = final_score
        st.session_state.last_recs   = recs
        st.session_state.last_inputs = {
            "hours": hours, "attendance": attendance,
            "previous": previous, "sleep": sleep,
            "motivation": motivation, "teacher": teacher,
            "resources": resources, "peer": peer
        }
        pdf_buf = generate_pdf_report(
            st.session_state.username, final_score, user_data,
            hours, attendance, previous, sleep, recs
        )
        st.session_state.last_pdf = pdf_buf.read()

        st.markdown(f"""
        <div class="result-card">
            <div class="result-label">PREDICTED EXAM SCORE</div>
            <div class="result-score">{final_score}<span style="font-size:1.1rem;opacity:0.55;"> / 100</span></div>
        </div>
        """, unsafe_allow_html=True)

        if final_score >= 85:
            st.success("🌟 Exceptional Performance! Outstanding!")
            st.balloons()
        elif final_score >= 70:
            st.success("📈 Good Performance! Keep it up!")
        elif final_score >= 55:
            st.info("📚 Satisfactory — room for improvement")
        else:
            st.warning("⚠️ Needs Improvement — check recommendations below")

    # ── Retrieve history ──
    uname     = st.session_state.username
    user_hist = all_history.get(uname, {})
    if isinstance(user_hist, list):
        scores_list = user_hist
        hours_list  = st.session_state.study_hours_history
        att_list    = st.session_state.attendance_history
    else:
        scores_list = user_hist.get("scores", [])
        hours_list  = user_hist.get("study_hours", [])
        att_list    = user_hist.get("attendance", [])

    # ── Download & Share ──
    if st.session_state.last_score is not None:
        final_score = st.session_state.last_score
        inp         = st.session_state.last_inputs

        st.markdown('<div class="section-header">📤 Download & Share</div>', unsafe_allow_html=True)
        st.markdown('<div class="share-box">', unsafe_allow_html=True)

        c1, c2 = st.columns(2)
        with c1:
            if st.session_state.last_pdf:
                fname = f"score_report_{uname}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    "📄 Download PDF Report",
                    data=st.session_state.last_pdf,
                    file_name=fname, mime="application/pdf",
                    use_container_width=True
                )
        with c2:
            share_text = (
                f"🎓 My Predicted Score: {final_score}/100\n"
                f"📖 Study Hours: {inp.get('hours','N/A')}\n"
                f"🏫 Attendance: {inp.get('attendance','N/A')}%\n"
                f"📊 Previous Score: {inp.get('previous','N/A')}\n"
                f"Generated by Student Score Predictor"
            )
            st.download_button(
                "📋 Score Summary (TXT)", data=share_text,
                file_name=f"score_{uname}.txt", mime="text/plain",
                use_container_width=True
            )

        # ── WhatsApp Share ──
        # WhatsApp can share text directly via wa.me; PDF must be downloaded first then shared
        wa_text = (
            f"🎓 *Student Score Predictor*\n\n"
            f"👤 Student: {user_data.get('full_name', uname)}\n"
            f"📊 *Predicted Score: {final_score}/100*\n"
            f"📖 Study Hours: {inp.get('hours','N/A')} hrs/day\n"
            f"🏫 Attendance: {inp.get('attendance','N/A')}%\n"
            f"📝 Previous Score: {inp.get('previous','N/A')}/100\n\n"
            f"_Generated by Student Score Predictor AI_"
        )
        import urllib.parse
        wa_encoded    = urllib.parse.quote(wa_text)
        email_encoded = urllib.parse.quote(share_text.replace("\n", "\n"))
        email_url     = f"mailto:?subject=My%20Predicted%20Score%20-%20{final_score}%2F100&body={urllib.parse.quote(share_text)}"

        st.markdown(f"""
        <div style="display:flex;gap:0.8rem;margin-top:0.9rem;flex-wrap:wrap;align-items:center;">
            <a href="https://wa.me/?text={wa_encoded}" target="_blank" style="text-decoration:none;">
                <button class="wa-btn">📱 Share on WhatsApp</button>
            </a>
            <a href="{email_url}" style="text-decoration:none;">
                <button class="email-btn">📧 Share via Email</button>
            </a>
        </div>
        <p style="font-size:0.7rem;color:#90e0ef;margin-top:0.5rem;opacity:0.8;">
            💡 Tip: To send the PDF on WhatsApp, download it first → open WhatsApp → attach the file in a chat.
        </p>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Performance Stats ──
    if len(scores_list) >= 1:
        st.markdown('<div class="section-header">📊 Performance Overview</div>', unsafe_allow_html=True)
        passing   = len([s for s in scores_list if s >= 60])
        needs_imp = len([s for s in scores_list if s < 60])
        avg_score = int(np.mean(scores_list))
        pass_pct  = (passing / len(scores_list)) * 100
        best      = max(scores_list)
        last_s    = scores_list[-1]

        cols = st.columns(5)
        stats = [
            (cols[0], last_s,    "Last Score",    False),
            (cols[1], avg_score, "Average",       False),
            (cols[2], best,      "Best Score",    False),
            (cols[3], passing,   "Passed",        False),
            (cols[4], needs_imp, "Need Improve",  True),
        ]
        for col, val, label, red in stats:
            cls = "stat-value-red" if red else "stat-value"
            with col:
                st.markdown(f"""
                <div class="stat-card">
                    <div class="{cls}">{val}</div>
                    <div class="stat-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")
        st.progress(pass_pct / 100)
        st.caption(f"✅ Success Rate: {pass_pct:.0f}% ({passing}/{len(scores_list)} attempts passed)")

        if len(scores_list) >= 2:
            trend = scores_list[-1] - scores_list[-2]
            if trend > 0:
                st.success(f"📈 Improving! +{trend} points from last attempt")
            elif trend < 0:
                st.warning(f"📉 Declined by {abs(trend)} points. Review recommendations!")
            else:
                st.info("➡️ Same as last attempt. Aim higher!")

    # =====================================
    # GRAPHS
    # =====================================

    # GRAPH 1 — Score History
    if len(scores_list) >= 1:
        st.markdown('<div class="section-header">📈 Graph 1 — Score History</div>', unsafe_allow_html=True)
        st.caption("Track your predicted score across all attempts")
        st.plotly_chart(graph_score_history(scores_list), use_container_width=True)

    # GRAPH 2 — Hours vs Score
    if len(hours_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-header">📖 Graph 2 — Study Hours vs Score</div>', unsafe_allow_html=True)
        st.caption("Does more study time lead to higher scores? Trend line included.")
        fig2 = graph_hours_vs_score(hours_list[:len(scores_list)], scores_list)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-header">📖 Graph 2 — Study Hours vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Appears after 2+ predictions")

    # GRAPH 3 — Attendance vs Score
    if len(att_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-header">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.caption("How does attendance % correlate with your predicted score?")
        fig3 = graph_attendance_vs_score(att_list[:len(scores_list)], scores_list)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-header">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Appears after 2+ predictions")

    # ✨ GRAPH 4 — Radar Chart (NEW & MOST USEFUL)
    if st.session_state.last_inputs:
        inp = st.session_state.last_inputs
        st.markdown('<div class="section-header">🎯 Graph 4 — Academic Profile Radar</div>', unsafe_allow_html=True)
        st.caption("Visual overview of all your academic factors vs the 80-point target benchmark")
        fig_radar, radar_vals, radar_cats = graph_radar_performance(
            hours      = inp.get("hours", 5),
            attendance = inp.get("attendance", 75),
            previous   = inp.get("previous", 60),
            sleep      = inp.get("sleep", 7),
            motivation = inp.get("motivation", "Medium"),
            teacher    = inp.get("teacher", "Average"),
            resources  = inp.get("resources", "Medium"),
            peer       = inp.get("peer", "Neutral"),
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        # Highlight weakest areas
        weak = [(cat, val) for cat, val in zip(radar_cats, radar_vals) if val < 60]
        if weak:
            st.markdown('<div class="section-header">⚠️ Areas Needing Attention</div>', unsafe_allow_html=True)
            weak_cols = st.columns(len(weak))
            for col, (cat, val) in zip(weak_cols, weak):
                with col:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="stat-value-red">{int(val)}</div>
                        <div class="stat-label">{cat}</div>
                    </div>
                    """, unsafe_allow_html=True)

    # ── Recommendations ──
    if st.session_state.last_recs is not None:
        recs = st.session_state.last_recs
        if recs:
            st.markdown('<div class="section-header">💡 Recommendations</div>', unsafe_allow_html=True)
            for r in recs:
                st.info(f"→ {r}")
        elif st.session_state.last_score:
            st.success("✅ Excellent habits! Maintain your current routine.")

    st.markdown("---")
    st.caption("🎓 Student Score Predictor v3.0 · AI Powered Academic Tool · Built with ❤️")

# =====================================
# MAIN ROUTER
# =====================================
if st.session_state.logged_in:
    show_main_app()
elif st.session_state.auth_mode == "home":
    show_home_page()
else:
    show_auth_page()
