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
USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"
PROFILE_PICS_DIR = "profile_pics"
OTP_FILE = "otp_store.json"

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)

# =====================================
# EMAIL CONFIG — Change these!
# =====================================
EMAIL_SENDER = "your_email@gmail.com"       # ← Your Gmail address
EMAIL_PASSWORD = "your_app_password_here"   # ← Gmail App Password (not your login password)
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
    """Send OTP via Gmail SMTP. Configure EMAIL_SENDER and EMAIL_PASSWORD above."""
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "🎓 Your OTP — Student Score Predictor"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver_email

        html_body = f"""
        <html><body style="font-family:Arial,sans-serif;background:#000814;color:#caf0f8;padding:30px;">
        <div style="max-width:420px;margin:0 auto;background:linear-gradient(135deg,#03045e,#0077b6);
            border-radius:16px;padding:30px;border:1px solid #00b4d8;">
            <h2 style="color:#90e0ef;text-align:center;">🎓 Student Score Predictor</h2>
            <p style="color:#caf0f8;">Hello <strong>{full_name}</strong>,</p>
            <p style="color:#caf0f8;">Your OTP verification code is:</p>
            <div style="text-align:center;margin:20px 0;">
                <span style="font-size:2.5rem;font-weight:900;color:#00b4d8;
                    letter-spacing:12px;background:rgba(0,180,216,0.1);
                    padding:12px 24px;border-radius:12px;border:2px solid #00b4d8;">
                    {otp_code}
                </span>
            </div>
            <p style="color:#90e0ef;font-size:0.85rem;">This OTP is valid for <strong>10 minutes</strong>.</p>
            <p style="color:#90e0ef;font-size:0.75rem;text-align:center;opacity:0.6;">
                If you didn't request this, please ignore this email.
            </p>
        </div>
        </body></html>
        """
        msg.attach(MIMEText(html_body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())
        return True, "OTP sent successfully!"
    except Exception as e:
        return False, f"Email error: {str(e)}"

def store_otp(email, otp):
    store = load_otp_store()
    store[email] = {
        "otp": otp,
        "timestamp": str(datetime.now()),
        "verified": False
    }
    save_otp_store(store)

def verify_otp(email, entered_otp):
    store = load_otp_store()
    if email not in store:
        return False, "No OTP found. Please request again."
    record = store[email]
    stored_time = datetime.fromisoformat(record["timestamp"])
    elapsed = (datetime.now() - stored_time).total_seconds()
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
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('T', parent=styles['Heading1'], fontSize=22,
        textColor=colors.HexColor('#0077b6'), alignment=1, spaceAfter=20)
    heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontSize=14,
        textColor=colors.HexColor('#023e8a'), spaceAfter=10)
    normal_style = ParagraphStyle('N', parent=styles['Normal'], fontSize=10, spaceAfter=5)

    story = []
    story.append(Paragraph("🎓 Student Score Predictor — Official Report", title_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Student Information", heading_style))
    story.append(Paragraph(f"Name: {user_data.get('full_name', username)}", normal_style))
    story.append(Paragraph(f"Username: {username}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Prediction Results", heading_style))
    score_data = [["Metric", "Value"], ["Predicted Exam Score", f"{final_score}/100"]]
    score_table = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (1,1), colors.HexColor('#caf0f8')),
        ('GRID', (0,0), (1,1), 1, colors.HexColor('#90e0ef'))
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.15*inch))
    story.append(Paragraph("Input Details", heading_style))
    input_data = [["Parameter","Value"],
        ["Study Hours", f"{hours} hours"], ["Attendance", f"{attendance}%"],
        ["Previous Score", f"{previous}/100"], ["Sleep Hours", f"{sleep} hours"]]
    input_table = Table(input_data, colWidths=[2.5*inch, 2.5*inch])
    input_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (1,-1), colors.HexColor('#caf0f8')),
        ('GRID', (0,0), (1,-1), 1, colors.HexColor('#90e0ef'))
    ]))
    story.append(input_table)
    story.append(Spacer(1, 0.15*inch))
    if recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Generated by Student Score Predictor — AI Powered Academic Tool",
        ParagraphStyle('F', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================
# SESSION STATE
# =====================================
defaults = {
    'logged_in': False, 'username': '', 'user_role': '',
    'auth_mode': 'home',  # 'home', 'login', 'signup', 'otp_verify'
    'signup_role': 'student', 'theme': 'dark',
    'show_profile_edit': False, 'last_pdf': None, 'last_score': None,
    'last_recs': [], 'last_inputs': {},
    'pending_signup_data': {},   # store signup form data before OTP
    'otp_email': '',             # email waiting for OTP verify
    'otp_verified': False,
    'study_hours_history': [],   # parallel list for graph
    'attendance_history': [],    # parallel list for graph
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

all_history = load_history()

# =====================================
# THEME CSS
# =====================================
DARK_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
* { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

.stApp {
    background: radial-gradient(ellipse at 20% 0%, #03045e 0%, #0a0a1a 40%, #000814 100%);
    min-height: 100vh;
}
.main .block-container {
    background: rgba(3,4,94,0.18);
    border-radius: 24px;
    padding: 2rem 2.5rem;
    border: 1px solid rgba(0,180,216,0.2);
    backdrop-filter: blur(12px);
    box-shadow: 0 0 60px rgba(0,119,182,0.12), inset 0 1px 0 rgba(0,180,216,0.1);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(3,4,94,0.95) 0%, rgba(0,8,20,0.98) 100%);
    border-right: 1px solid rgba(0,180,216,0.2);
}

/* ===== FORCE WHITE TEXT IN DARK MODE ===== */
.stApp { color: #ffffff !important; }
.stApp p, .stApp span, .stApp div, .stApp label { color: #ffffff !important; }
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp h5 { color: #90e0ef !important; }
.stApp .stMarkdown p { color: #ffffff !important; }
[data-testid="stSidebar"] * { color: #ffffff !important; }
[data-testid="stSidebar"] h1,[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 { color: #90e0ef !important; }
.stCaption, [data-testid="stCaptionContainer"] { color: #c0e8f8 !important; }
.stAlert p, .stAlert div { color: #ffffff !important; }

/* Inputs */
.stNumberInput input, .stTextInput input, .stDateInput input, .stTextAreaInput textarea {
    background: rgba(0,20,60,0.7) !important;
    border: 1px solid rgba(0,180,216,0.4) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #00b4d8 !important;
    box-shadow: 0 0 0 3px rgba(0,180,216,0.2) !important;
}
div[data-baseweb="select"] > div {
    background: rgba(0,20,60,0.7) !important;
    border: 1px solid rgba(0,180,216,0.4) !important;
    border-radius: 12px !important;
    color: #ffffff !important;
}
div[data-baseweb="select"] span { color: #ffffff !important; }
div[data-baseweb="popover"] div { background: #020a20 !important; border: 1px solid #0077b6 !important; }
li[role="option"] { color: #ffffff !important; }
li[role="option"]:hover { background: #0077b6 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.5rem 1.4rem !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.3) !important;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 8px 30px rgba(0,180,216,0.5) !important;
    background: linear-gradient(135deg, #00b4d8 0%, #90e0ef 100%) !important;
    color: #03045e !important;
}
.stButton > button:active { transform: translateY(-1px) scale(0.99) !important; }

[data-testid="stDownloadButton"] button {
    background: rgba(0,180,216,0.12) !important;
    border: 1.5px solid #00b4d8 !important;
    color: #ffffff !important;
    border-radius: 50px !important;
    padding: 0.35rem 1rem !important;
    font-size: 0.82rem !important;
    transition: all 0.3s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(0,180,216,0.28) !important;
    transform: translateY(-2px) !important;
}

/* Cards */
.result-card {
    background: linear-gradient(135deg, rgba(3,4,94,0.9) 0%, rgba(0,20,60,0.95) 100%);
    border: 2px solid #00b4d8;
    border-radius: 20px;
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0;
    box-shadow: 0 0 40px rgba(0,180,216,0.2);
}
.result-score { color: #00b4d8 !important; font-weight: 800 !important; font-size: 3rem !important; font-family: 'Syne', sans-serif !important; }
.result-label { color: #ffffff !important; font-size: 0.65rem !important; letter-spacing: 3px !important; text-transform: uppercase; }

.stat-card {
    background: rgba(0,20,60,0.55);
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 14px; padding: 0.8rem; text-align: center;
    transition: all 0.3s !important;
}
.stat-card:hover { border-color: #00b4d8 !important; transform: translateY(-2px); }
.stat-value { font-size: 1.6rem; font-weight: 800; color: #00b4d8 !important; font-family: 'Syne', sans-serif !important; }
.stat-value-red { font-size: 1.6rem; font-weight: 800; color: #f87171 !important; font-family: 'Syne', sans-serif !important; }
.stat-label { font-size: 0.58rem; color: #ffffff !important; letter-spacing: 1px; text-transform: uppercase; margin-top: 0.2rem; }

.section-header {
    font-family: 'Syne', sans-serif;
    color: #90e0ef !important;
    font-size: 1.1rem; font-weight: 700; letter-spacing: 0.5px;
    margin: 1.2rem 0 0.6rem;
}

.profile-card { text-align: center; padding: 0.8rem; }
.profile-name { font-size: 1rem; font-weight: 700; color: #ffffff !important; font-family: 'Syne', sans-serif !important; }
.profile-role {
    font-size: 0.62rem; padding: 0.2rem 0.7rem; border-radius: 50px;
    display: inline-block; background: rgba(0,180,216,0.12);
    border: 1px solid rgba(0,180,216,0.4); color: #ffffff !important;
    letter-spacing: 1px; text-transform: uppercase;
}
.avatar-circle {
    width: 72px; height: 72px; border-radius: 50%;
    border: 2.5px solid #00b4d8;
    box-shadow: 0 0 20px rgba(0,180,216,0.35);
    margin: 0 auto 0.5rem;
    overflow: hidden; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0077b6, #00b4d8);
    font-size: 1.8rem;
}
.avatar-circle img { width: 100%; height: 100%; object-fit: cover; }

.home-hero {
    text-align: center; padding: 3rem 1rem;
    background: linear-gradient(135deg, rgba(3,4,94,0.6), rgba(0,20,60,0.8));
    border-radius: 24px; border: 1px solid rgba(0,180,216,0.25);
    margin-bottom: 2rem;
}
.home-hero h1 { font-size: 2.8rem !important; color: #ffffff !important; }
.home-hero p { color: #c8eef8 !important; font-size: 1.05rem; }

.feature-card {
    background: rgba(0,20,60,0.5);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 16px; padding: 1.2rem; text-align: center;
    transition: all 0.3s;
}
.feature-card:hover { border-color: #00b4d8; transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,180,216,0.15); }
.feature-card h3 { color: #90e0ef !important; font-size: 1rem !important; }
.feature-card p { color: #ffffff !important; font-size: 0.82rem; }
.feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }

.otp-box {
    background: rgba(0,20,60,0.6);
    border: 1.5px solid rgba(0,180,216,0.35);
    border-radius: 16px; padding: 1.5rem;
    margin: 0.5rem 0;
}
.share-box {
    background: rgba(0,180,216,0.07);
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 16px; padding: 1rem; margin: 0.5rem 0;
}
hr { border-color: rgba(0,180,216,0.18) !important; margin: 1rem 0 !important; }
input::placeholder { color: rgba(200,238,248,0.45) !important; }
.stNumberInput button { background: rgba(0,40,100,0.5) !important; border: 1px solid rgba(0,180,216,0.3) !important; color: #ffffff !important; }
.stNumberInput button:hover { background: #0077b6 !important; color: white !important; }
.stCheckbox label { color: #ffffff !important; }
[data-testid="stFileUploader"] { background: rgba(0,20,60,0.4) !important; border: 2px dashed rgba(0,180,216,0.3) !important; border-radius: 14px !important; }
</style>
"""

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');
* { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

.stApp { background: linear-gradient(145deg, #caf0f8 0%, #90e0ef 30%, #caf0f8 70%, #e0f7fa 100%); }
.main .block-container {
    background: rgba(255,255,255,0.88);
    border-radius: 24px; padding: 2rem 2.5rem;
    border: 1px solid rgba(0,119,182,0.2);
    backdrop-filter: blur(10px);
    box-shadow: 0 4px 30px rgba(0,119,182,0.1);
}
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(202,240,248,0.95) 100%);
    border-right: 1px solid rgba(0,180,216,0.25);
}
.stApp, .stApp * { color: #03045e !important; }
h1,h2,h3 { color: #03045e !important; }

.stNumberInput input, .stTextInput input, .stDateInput input {
    background: rgba(202,240,248,0.5) !important;
    border: 1.5px solid rgba(0,119,182,0.3) !important;
    border-radius: 12px !important; color: #03045e !important;
}
div[data-baseweb="select"] > div {
    background: rgba(202,240,248,0.5) !important;
    border: 1.5px solid rgba(0,119,182,0.3) !important;
    border-radius: 12px !important; color: #03045e !important;
}
div[data-baseweb="popover"] div { background: #f0faff !important; border: 1px solid #90e0ef !important; }
li[role="option"] { color: #03045e !important; }
li[role="option"]:hover { background: #0077b6 !important; color: white !important; }

.stButton > button {
    background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%) !important;
    color: white !important; border: none !important;
    border-radius: 50px !important; padding: 0.5rem 1.4rem !important;
    font-weight: 700 !important; font-family: 'Syne', sans-serif !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.03) !important;
    box-shadow: 0 10px 30px rgba(0,119,182,0.4) !important;
    background: linear-gradient(135deg, #03045e 0%, #0077b6 100%) !important;
}
[data-testid="stDownloadButton"] button {
    background: rgba(0,119,182,0.08) !important;
    border: 1.5px solid #0077b6 !important; color: #0077b6 !important;
    border-radius: 50px !important; padding: 0.35rem 1rem !important; transition: all 0.3s !important;
}

.result-card {
    background: linear-gradient(135deg, #03045e 0%, #0077b6 100%);
    border: 2px solid #00b4d8; border-radius: 20px; padding: 1.5rem; text-align: center; margin: 1rem 0;
    box-shadow: 0 8px 30px rgba(0,119,182,0.3);
}
.result-score { color: #caf0f8 !important; font-weight: 800 !important; font-size: 3rem !important; font-family: 'Syne', sans-serif !important; }
.result-label { color: #90e0ef !important; font-size: 0.65rem !important; letter-spacing: 3px !important; text-transform: uppercase; }

.stat-card {
    background: linear-gradient(135deg, rgba(202,240,248,0.6), rgba(144,224,239,0.3));
    border: 1px solid rgba(0,119,182,0.2); border-radius: 14px; padding: 0.8rem; text-align: center; transition: all 0.3s !important;
}
.stat-card:hover { border-color: #0077b6 !important; transform: translateY(-3px); }
.stat-value { font-size: 1.6rem; font-weight: 800; color: #0077b6 !important; font-family: 'Syne', sans-serif !important; }
.stat-value-red { font-size: 1.6rem; font-weight: 800; color: #dc2626 !important; font-family: 'Syne', sans-serif !important; }
.stat-label { font-size: 0.58rem; color: #03045e !important; letter-spacing: 1px; text-transform: uppercase; }

.section-header { font-family: 'Syne', sans-serif; color: #03045e !important; font-size: 1.1rem; font-weight: 700; margin: 1.2rem 0 0.6rem; }
.profile-card { text-align: center; padding: 0.8rem; }
.profile-name { font-size: 1rem; font-weight: 700; color: #03045e !important; font-family: 'Syne', sans-serif !important; }
.profile-role {
    font-size: 0.62rem; padding: 0.2rem 0.7rem; border-radius: 50px;
    display: inline-block; background: rgba(0,119,182,0.1);
    border: 1px solid rgba(0,119,182,0.4); color: #0077b6 !important;
    letter-spacing: 1px; text-transform: uppercase;
}
.avatar-circle {
    width: 72px; height: 72px; border-radius: 50%;
    border: 2.5px solid #0077b6; box-shadow: 0 4px 15px rgba(0,119,182,0.25);
    margin: 0 auto 0.5rem; overflow: hidden;
    display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0077b6, #00b4d8); font-size: 1.8rem;
}
.avatar-circle img { width: 100%; height: 100%; object-fit: cover; }

.home-hero {
    text-align: center; padding: 3rem 1rem;
    background: linear-gradient(135deg, rgba(3,4,94,0.85), rgba(0,119,182,0.9));
    border-radius: 24px; margin-bottom: 2rem; color: white !important;
}
.home-hero h1 { font-size: 2.8rem !important; color: #ffffff !important; }
.home-hero p { color: #caf0f8 !important; font-size: 1.05rem; }

.feature-card {
    background: rgba(255,255,255,0.75); border: 1px solid rgba(0,119,182,0.2);
    border-radius: 16px; padding: 1.2rem; text-align: center; transition: all 0.3s;
}
.feature-card:hover { border-color: #0077b6; transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,119,182,0.15); }
.feature-card h3 { color: #03045e !important; font-size: 1rem !important; }
.feature-card p { color: #03045e !important; font-size: 0.82rem; }
.feature-icon { font-size: 2rem; margin-bottom: 0.5rem; }

.otp-box {
    background: rgba(202,240,248,0.5); border: 1.5px solid rgba(0,119,182,0.3);
    border-radius: 16px; padding: 1.5rem; margin: 0.5rem 0;
}
.share-box { background: rgba(0,119,182,0.05); border: 1px solid rgba(0,119,182,0.2); border-radius: 16px; padding: 1rem; margin: 0.5rem 0; }
hr { border-color: rgba(0,119,182,0.15) !important; margin: 1rem 0 !important; }
[data-testid="stFileUploader"] { background: rgba(202,240,248,0.4) !important; border: 2px dashed rgba(0,119,182,0.3) !important; border-radius: 14px !important; }
</style>
"""

def apply_theme():
    st.markdown(DARK_CSS if st.session_state.theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)

def theme_toggle():
    icon = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(icon, key="theme_toggle_btn"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# =====================================
# HOME PAGE
# =====================================
def show_home_page():
    apply_theme()
    col_hdr, col_thm = st.columns([9,1])
    with col_thm:
        theme_toggle()

    st.markdown("""
    <div class="home-hero">
        <div style="font-size:4rem;margin-bottom:0.5rem;">🎓</div>
        <h1>Student Score Predictor</h1>
        <p>AI-Powered Academic Performance Analysis</p>
        <p style="font-size:0.8rem;opacity:0.75;margin-top:0.5rem;">
            Predict your exam score, track progress, and get personalised recommendations
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Features Section
    st.markdown('<div class="section-header">✨ Key Features</div>', unsafe_allow_html=True)
    f1, f2, f3, f4 = st.columns(4)
    features = [
        ("🤖", "AI Prediction", "Machine learning model predicts your exam score based on study habits and academic data"),
        ("📊", "Progress Tracking", "Visual charts track your score history, study hours impact, and attendance correlation"),
        ("💡", "Smart Recommendations", "Get personalised tips to improve attendance, sleep, study hours and more"),
        ("📄", "PDF Reports", "Download official prediction reports and share results via WhatsApp or Email"),
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

    st.markdown("---")

    # About Section
    st.markdown('<div class="section-header">📖 About the Project</div>', unsafe_allow_html=True)
    c1, c2 = st.columns([3,2])
    with c1:
        st.markdown("""
        **Student Score Predictor** is an AI-powered academic tool built for students and parents
        to understand and improve academic performance.

        **How It Works:**
        - Enter your study hours, attendance %, previous scores, sleep hours and other factors
        - Our trained Machine Learning model analyses these inputs
        - Get an instant predicted exam score (0–100)
        - View trends over time with interactive charts
        - Download a professional PDF report

        **Who Is It For?**
        - 🎓 **Students** (Class 8–12 and College) who want to improve grades
        - 👨‍👩‍👧 **Parents** who want to monitor their child's academic trends

        **Technology Stack:**
        Python · Streamlit · Scikit-Learn · Plotly · ReportLab
        """)
    with c2:
        st.markdown("""
        <div style="background:rgba(0,119,182,0.12);border:1px solid rgba(0,180,216,0.3);
            border-radius:16px;padding:1.2rem;">
            <h4 style="color:#00b4d8 !important;margin-bottom:0.8rem;">📈 What We Analyse</h4>
            <ul style="list-style:none;padding:0;margin:0;">
                <li>📖 Study Hours per Day</li>
                <li>🏫 Attendance Percentage</li>
                <li>📊 Previous Exam Scores</li>
                <li>💤 Sleep Hours</li>
                <li>🔥 Motivation Level</li>
                <li>👩‍🏫 Teacher Quality</li>
                <li>🌐 Internet Access</li>
                <li>💰 Family Income Level</li>
                <li>👥 Peer Influence</li>
                <li>📚 Learning Resources</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="section-header">📊 Sample Performance Insights</div>', unsafe_allow_html=True)
    # Demo graphs on home page
    sample_scores = [58, 63, 67, 71, 74, 78, 82]
    sample_hours  = [3, 4, 5, 5.5, 6, 7, 8]
    sample_att    = [65, 68, 72, 75, 78, 82, 88]
    attempts_demo = [f"#{i}" for i in range(1, 8)]

    fig_demo = go.Figure()
    fig_demo.add_trace(go.Scatter(x=attempts_demo, y=sample_scores, mode='lines+markers',
        name='Score', line=dict(color='#00b4d8', width=3),
        marker=dict(size=8, color='#00b4d8', line=dict(color='white', width=2))))
    fig_demo.add_hline(y=60, line_dash="dash", line_color="#f87171", annotation_text="Pass", annotation_font_color="#f87171")
    fig_demo.add_hline(y=85, line_dash="dash", line_color="#34d399", annotation_text="Excellent", annotation_font_color="#34d399")
    is_dark = st.session_state.theme == "dark"
    bg_col = "rgba(3,4,94,0.0)" if is_dark else "rgba(255,255,255,0.0)"
    txt_col = "#ffffff" if is_dark else "#03045e"
    grid_col = "rgba(0,180,216,0.15)" if is_dark else "rgba(0,119,182,0.15)"
    fig_demo.update_layout(
        title=dict(text="Sample Score Progress", font=dict(color=txt_col)),
        paper_bgcolor=bg_col, plot_bgcolor=bg_col,
        font=dict(color=txt_col), height=250, margin=dict(l=0,r=0,t=40,b=0),
        showlegend=False,
        xaxis=dict(gridcolor=grid_col, color=txt_col),
        yaxis=dict(gridcolor=grid_col, color=txt_col, range=[40,100]),
    )
    st.plotly_chart(fig_demo, use_container_width=True)

    st.markdown("---")
    col_a, col_b, col_c = st.columns([1,2,1])
    with col_b:
        if st.button("🎓 Get Started — Sign Up / Login", use_container_width=True):
            st.session_state.auth_mode = "login"
            st.rerun()

    st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1rem;opacity:0.5;">🔒 Secure · AI Powered · Student Score Predictor v2.0</p>', unsafe_allow_html=True)

# =====================================
# AUTH PAGE
# =====================================
def show_auth_page():
    apply_theme()
    users = load_users()

    col_back, col_thm = st.columns([9,1])
    with col_back:
        if st.button("← Home", key="back_home_btn"):
            st.session_state.auth_mode = "home"
            st.rerun()
    with col_thm:
        theme_toggle()

    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.5rem;">
            <div style="font-size:2.8rem;">🎓</div>
            <h2 style="margin:0.2rem 0;letter-spacing:-0.5px;">Student Score Predictor</h2>
            <p style="font-size:0.75rem;opacity:0.6;margin:0;">AI Powered Academic Tool</p>
        </div>
        """, unsafe_allow_html=True)

        # ── LOGIN ──
        if st.session_state.auth_mode == "login":
            st.markdown("**Sign In to Your Account**")
            username = st.text_input("Username", placeholder="Enter username", key="login_user")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass")
            if st.button("Sign In →", use_container_width=True, key="login_btn"):
                if username and password:
                    if username in users and users[username]["password"] == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_role = users[username]["role"]
                        # load saved graph history
                        h = all_history.get(username, {})
                        if isinstance(h, dict):
                            st.session_state.study_hours_history = h.get("study_hours", [])
                            st.session_state.attendance_history = h.get("attendance", [])
                        st.rerun()
                    else:
                        st.error("❌ Invalid username or password")
                else:
                    st.warning("Please fill all fields")
            st.markdown("<hr>", unsafe_allow_html=True)
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🎓 Student Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "student"
                    st.rerun()
            with c2:
                if st.button("👨‍👩‍👧 Parent Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "parent"
                    st.rerun()

        # ── SIGNUP ──
        elif st.session_state.auth_mode == "signup":
            role = st.session_state.signup_role
            st.markdown(f"**Create {role.capitalize()} Account**")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("🎓 Student", use_container_width=True):
                    st.session_state.signup_role = "student"; st.rerun()
            with c2:
                if st.button("👨‍👩‍👧 Parent", use_container_width=True):
                    st.session_state.signup_role = "parent"; st.rerun()
            st.markdown("---")
            username  = st.text_input("Username", placeholder="Choose a username", key="su_user")
            email     = st.text_input("Email Address", placeholder="your@email.com (for OTP)", key="su_email")
            password  = st.text_input("Password", type="password", placeholder="Min 4 characters", key="su_pass")
            confirm   = st.text_input("Confirm Password", type="password", placeholder="Repeat password", key="su_confirm")
            full_name = st.text_input("Full Name", placeholder="Your full name", key="su_name")
            if role == "student":
                dob   = st.date_input("Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_dob")
                grade = st.selectbox("Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_grade")
                school= st.text_input("School / College Name", placeholder="Institution name", key="su_school")
            else:
                child_name  = st.text_input("Child's Name", placeholder="Child's full name", key="su_child")
                child_dob   = st.date_input("Child's DOB", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_cdob")
                child_grade = st.selectbox("Child's Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_cgrade")
                relation    = st.selectbox("Relationship", ["Father","Mother","Guardian"], key="su_relation")

            st.markdown('<div class="otp-box">', unsafe_allow_html=True)
            st.markdown("**📧 Email OTP Verification**")
            st.caption("An OTP will be sent to your email to verify your account.")
            if st.button("📨 Send OTP to Email", use_container_width=True, key="send_otp_btn"):
                if not email:
                    st.warning("Please enter your email first.")
                else:
                    otp = generate_otp()
                    store_otp(email, otp)
                    success, msg = send_otp_email(email, otp, full_name or "User")
                    if success:
                        st.success(f"✅ OTP sent to {email}! Check your inbox.")
                        st.session_state.otp_email = email
                    else:
                        # For testing when email not configured — show OTP in warning
                        st.warning(f"⚠️ Email not configured. For testing, your OTP is: **{otp}**")
                        st.caption("Configure EMAIL_SENDER and EMAIL_PASSWORD in app.py to enable real email OTP.")
                        st.session_state.otp_email = email

            entered_otp = st.text_input("Enter OTP", placeholder="6-digit code from your email", key="otp_input", max_chars=6)
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✅ Verify OTP & Create Account", use_container_width=True, key="create_acc_btn"):
                # Validations
                if not username or not password or not full_name or not email:
                    st.warning("Please fill all required fields.")
                elif password != confirm:
                    st.error("Passwords don't match.")
                elif len(password) < 4:
                    st.warning("Password must be at least 4 characters.")
                elif username in users:
                    st.error("Username already taken. Choose another.")
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
                            data["dob"] = str(dob)
                            data["age"] = calculate_age(dob)
                            data["grade"] = grade
                            data["school"] = school
                        else:
                            data["child_name"] = child_name
                            data["child_dob"] = str(child_dob)
                            data["child_age"] = calculate_age(child_dob)
                            data["child_grade"] = child_grade
                            data["relation"] = relation
                        users[username] = data
                        save_users(users)
                        st.success("🎉 Account created! Please sign in.")
                        st.session_state.auth_mode = "login"
                        st.rerun()

            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True, key="back_login_btn"):
                st.session_state.auth_mode = "login"; st.rerun()

        st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1rem;opacity:0.4;">🔒 Secure Portal · AI Powered</p>', unsafe_allow_html=True)

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
        pic_b64    = get_profile_pic_base64(st.session_state.username)
        role_text  = "Student" if st.session_state.user_role == "student" else "Parent"
        role_icon  = "🎓" if st.session_state.user_role == "student" else "👨‍👩‍👧"
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
        theme_toggle()
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()

# =====================================
# PLOTLY GRAPH HELPERS
# =====================================
def plotly_layout(title_txt, xtitle, ytitle, yrange=None):
    is_dark = st.session_state.theme == "dark"
    bg  = "rgba(0,0,0,0)"
    txt = "#ffffff" if is_dark else "#03045e"
    grd = "rgba(0,180,216,0.12)" if is_dark else "rgba(0,119,182,0.12)"
    layout = dict(
        title=dict(text=title_txt, font=dict(color=txt, size=14)),
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
    """Graph 1: Score History Line Graph"""
    attempts = [f"#{i}" for i in range(1, len(scores)+1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=attempts, y=scores, mode='lines+markers', name='Your Score',
        line=dict(color='#00b4d8', width=3),
        marker=dict(size=9, color='#00b4d8', line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(0,180,216,0.08)'
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#f87171",
                  annotation_text="Pass (60)", annotation_font_color="#f87171")
    fig.add_hline(y=70, line_dash="dot", line_color="#fbbf24",
                  annotation_text="Good (70)", annotation_font_color="#fbbf24")
    fig.add_hline(y=85, line_dash="dash", line_color="#34d399",
                  annotation_text="Excellent (85)", annotation_font_color="#34d399")
    fig.update_layout(**plotly_layout("📈 Score History", "Attempt", "Score", [30, 105]))
    return fig

def graph_hours_vs_score(hours_list, scores):
    """Graph 2: Hours Studied vs Score — Scatter"""
    if len(hours_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours_list, y=scores, mode='markers',
        name='Attempts',
        marker=dict(size=11, color='#00b4d8',
                    line=dict(color='white', width=2),
                    symbol='circle'),
        text=[f"Attempt #{i+1}<br>Hours: {h}h<br>Score: {s}" for i,(h,s) in enumerate(zip(hours_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    # Trend line
    if len(hours_list) >= 3:
        z = np.polyfit(hours_list, scores, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(hours_list), max(hours_list), 100)
        fig.add_trace(go.Scatter(
            x=x_line.tolist(), y=p(x_line).tolist(),
            mode='lines', name='Trend',
            line=dict(color='#90e0ef', width=2, dash='dash')
        ))
    fig.update_layout(**plotly_layout("📖 Hours Studied vs Score", "Study Hours / Day", "Score", [30, 105]))
    return fig

def graph_attendance_vs_score(att_list, scores):
    """Graph 3: Attendance vs Score — Scatter"""
    if len(att_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=att_list, y=scores, mode='markers',
        name='Attempts',
        marker=dict(size=11, color='#0077b6',
                    line=dict(color='white', width=2),
                    symbol='diamond'),
        text=[f"Attempt #{i+1}<br>Attendance: {a}%<br>Score: {s}" for i,(a,s) in enumerate(zip(att_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    # Trend line
    if len(att_list) >= 3:
        z = np.polyfit(att_list, scores, 1)
        p = np.poly1d(z)
        x_line = np.linspace(min(att_list), max(att_list), 100)
        fig.add_trace(go.Scatter(
            x=x_line.tolist(), y=p(x_line).tolist(),
            mode='lines', name='Trend',
            line=dict(color='#90e0ef', width=2, dash='dash')
        ))
    fig.update_layout(**plotly_layout("🏫 Attendance vs Score", "Attendance (%)", "Score", [30, 105]))
    return fig

# =====================================
# MAIN APP
# =====================================
def show_main_app():
    apply_theme()
    users     = load_users()
    user_data = users.get(st.session_state.username, {})
    show_sidebar(user_data)

    st.markdown("<h1 style='text-align:center;letter-spacing:-1px;'>🎓 Student Score Predictor</h1>", unsafe_allow_html=True)

    if st.session_state.user_role == "parent":
        child_name = user_data.get("child_name", "Child")
        st.info(f"👨‍👩‍👧 Predicting for: **{child_name}**")

    model, columns = load_models()

    # ── Input Parameters ──
    st.markdown('<div class="section-header">📋 Input Parameters</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        hours      = st.number_input("📖 Hours Studied", min_value=0.0, max_value=24.0, value=5.0, step=0.5)
        attendance = st.number_input("🏫 Attendance (%)", min_value=0.0, max_value=100.0, value=75.0, step=5.0)
        previous   = st.number_input("📊 Previous Score", min_value=0.0, max_value=100.0, value=60.0, step=5.0)
        sleep      = st.number_input("💤 Sleep Hours", min_value=0.0, max_value=12.0, value=7.0, step=0.5)
        motivation = st.selectbox("🔥 Motivation Level", ["Low", "Medium", "High"])
        teacher    = st.selectbox("👩‍🏫 Teacher Quality", ["Poor", "Average", "Good"])
        school_t   = st.selectbox("🏛️ School Type", ["Public", "Private"])
    with col2:
        internet   = st.selectbox("🌐 Internet Access", ["Yes", "No"])
        income     = st.selectbox("💰 Family Income", ["Low", "Medium", "High"])
        parent_inv = st.selectbox("👨‍👩‍👦 Parental Involvement", ["Low", "Medium", "High"])
        education  = st.selectbox("🎓 Parent Education", ["School", "College"])
        peer       = st.selectbox("👥 Peer Influence", ["Negative", "Neutral", "Positive"])
        resources  = st.selectbox("📚 Learning Resources", ["Low", "Medium", "High"])
        activities = st.selectbox("⚽ Extracurricular Activities", ["Yes", "No"])

    st.markdown("")
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
        prediction = model.predict(input_df)
        final_score = max(40, min(100, int(round(prediction[0]))))

        # Update parallel history lists
        uname = st.session_state.username
        if uname not in all_history:
            all_history[uname] = {"scores": [], "study_hours": [], "attendance": []}
        # Support both old list format and new dict format
        if isinstance(all_history[uname], list):
            old_scores = all_history[uname]
            all_history[uname] = {"scores": old_scores, "study_hours": [], "attendance": []}

        all_history[uname]["scores"].append(final_score)
        all_history[uname]["study_hours"].append(float(hours))
        all_history[uname]["attendance"].append(float(attendance))

        # Keep last 15 entries
        for key in ["scores","study_hours","attendance"]:
            if len(all_history[uname][key]) > 15:
                all_history[uname][key] = all_history[uname][key][-15:]

        save_history(all_history)
        st.session_state.study_hours_history = all_history[uname]["study_hours"]
        st.session_state.attendance_history  = all_history[uname]["attendance"]

        # Recommendations
        recs = []
        if hours < 6:        recs.append("Increase study hours to 6–8 daily for better results")
        if attendance < 75:  recs.append("Improve attendance to at least 80%")
        if sleep < 7:        recs.append("Get 7–9 hours of quality sleep daily")
        if motivation == "Low": recs.append("Set clear daily goals to boost motivation")
        if teacher == "Poor":   recs.append("Seek additional tutoring or online resources")
        if resources == "Low":  recs.append("Utilise free online learning platforms (Khan Academy, YouTube)")
        if peer == "Negative":  recs.append("Join positive study groups or study with high achievers")

        st.session_state.last_score  = final_score
        st.session_state.last_recs   = recs
        st.session_state.last_inputs = {"hours": hours, "attendance": attendance,
                                         "previous": previous, "sleep": sleep}
        pdf_buf = generate_pdf_report(st.session_state.username, final_score, user_data,
                                       hours, attendance, previous, sleep, recs)
        st.session_state.last_pdf = pdf_buf.read()

        st.markdown(f"""
        <div class="result-card">
            <div class="result-label">PREDICTED EXAM SCORE</div>
            <div class="result-score">{final_score}<span style="font-size:1.2rem;opacity:0.6;"> / 100</span></div>
        </div>
        """, unsafe_allow_html=True)

        if final_score >= 85:
            st.success("🌟 Exceptional Performance! Outstanding!"); st.balloons()
        elif final_score >= 70:
            st.success("📈 Good Performance! Keep it up!")
        elif final_score >= 55:
            st.info("📚 Satisfactory — room for improvement")
        else:
            st.warning("⚠️ Needs Improvement — check recommendations below")

    # ── Download & Share ──
    uname = st.session_state.username
    user_hist = all_history.get(uname, {})
    if isinstance(user_hist, list):
        scores_list = user_hist
        hours_list  = st.session_state.study_hours_history
        att_list    = st.session_state.attendance_history
    else:
        scores_list = user_hist.get("scores", [])
        hours_list  = user_hist.get("study_hours", [])
        att_list    = user_hist.get("attendance", [])

    if st.session_state.last_score is not None:
        final_score = st.session_state.last_score
        inp = st.session_state.last_inputs

        st.markdown('<div class="section-header">📤 Download & Share</div>', unsafe_allow_html=True)
        st.markdown('<div class="share-box">', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            if st.session_state.last_pdf:
                fname = f"score_report_{uname}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button("📄 Download PDF Report", data=st.session_state.last_pdf,
                    file_name=fname, mime="application/pdf", use_container_width=True)
        with c2:
            share_text = (
                f"🎓 My Predicted Score: {final_score}/100\n"
                f"📖 Study Hours: {inp.get('hours','N/A')}\n"
                f"🏫 Attendance: {inp.get('attendance','N/A')}%\n"
                f"📊 Previous Score: {inp.get('previous','N/A')}\n"
                f"Generated by Student Score Predictor"
            )
            st.download_button("📋 Score Summary (TXT)", data=share_text,
                file_name=f"score_{uname}.txt", mime="text/plain", use_container_width=True)

        wa_text = f"🎓 My Predicted Exam Score: {final_score}/100! via Student Score Predictor AI."
        wa_url  = f"https://wa.me/?text={wa_text.replace(' ','%20')}"
        email_url = f"mailto:?subject=My%20Predicted%20Score&body={share_text.replace(chr(10),'%0A')}"
        st.markdown(f"""
        <div style="display:flex;gap:0.8rem;margin-top:0.7rem;flex-wrap:wrap;">
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <button style="background:linear-gradient(135deg,#25d366,#128c7e);color:white;border:none;
                    border-radius:50px;padding:0.4rem 1.1rem;font-size:0.8rem;font-weight:600;cursor:pointer;">
                    📱 Share on WhatsApp
                </button>
            </a>
            <a href="{email_url}" style="text-decoration:none;">
                <button style="background:linear-gradient(135deg,#0077b6,#00b4d8);color:white;border:none;
                    border-radius:50px;padding:0.4rem 1.1rem;font-size:0.8rem;font-weight:600;cursor:pointer;">
                    📧 Share via Email
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Performance Overview ──
    if len(scores_list) >= 1:
        st.markdown('<div class="section-header">📊 Performance Overview</div>', unsafe_allow_html=True)
        passing  = len([s for s in scores_list if s >= 60])
        needs_imp= len([s for s in scores_list if s < 60])
        avg_score= int(np.mean(scores_list))
        pass_pct = (passing / len(scores_list)) * 100
        best     = max(scores_list)
        last_s   = scores_list[-1]

        cols = st.columns(5)
        stats = [(cols[0],last_s,"Last Score",False),(cols[1],avg_score,"Average",False),
                 (cols[2],best,"Best Score",False),(cols[3],passing,"Passed",False),
                 (cols[4],needs_imp,"Need Improve",True)]
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

    # ==========================================
    # ✅ THE 3 REQUESTED GRAPHS (PLOTLY)
    # ==========================================

    # GRAPH 1 — Score History Line Graph
    if len(scores_list) >= 1:
        st.markdown('<div class="section-header">📈 Graph 1 — Score History</div>', unsafe_allow_html=True)
        st.caption("Track your predicted score across all attempts. Benchmarks: Pass=60, Good=70, Excellent=85")
        st.plotly_chart(graph_score_history(scores_list), use_container_width=True)

    # GRAPH 2 — Hours Studied vs Score
    if len(hours_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-header">📖 Graph 2 — Hours Studied vs Score</div>', unsafe_allow_html=True)
        st.caption("Educational insight: Does studying more hours lead to higher scores? Trend line included.")
        fig2 = graph_hours_vs_score(hours_list[:len(scores_list)], scores_list)
        if fig2:
            st.plotly_chart(fig2, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-header">📖 Graph 2 — Hours Studied vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Hours vs Score chart will appear after 2+ predictions")

    # GRAPH 3 — Attendance vs Score
    if len(att_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-header">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.caption("Academic analysis: How does attendance % correlate with your predicted score?")
        fig3 = graph_attendance_vs_score(att_list[:len(scores_list)], scores_list)
        if fig3:
            st.plotly_chart(fig3, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-header">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Attendance vs Score chart will appear after 2+ predictions")

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
    st.caption("🎓 Student Score Predictor v2.0 · AI Powered Academic Tool · Built with ❤️")

# =====================================
# MAIN ROUTER
# =====================================
if st.session_state.logged_in:
    show_main_app()
elif st.session_state.auth_mode == "home":
    show_home_page()
else:
    show_auth_page()
