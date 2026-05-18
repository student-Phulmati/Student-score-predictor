import streamlit as st
import joblib
import pandas as pd
import numpy as np
import hashlib
import json
import os
import base64
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch
import io

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

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)

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
# PDF REPORT
# =====================================
def generate_pdf_report(username, final_score, user_data, hours, attendance, previous, sleep, recommendations):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=24,
        textColor=colors.HexColor('#0077b6'), alignment=1, spaceAfter=30)
    heading_style = ParagraphStyle('CustomHeading', parent=styles['Heading2'], fontSize=16,
        textColor=colors.HexColor('#023e8a'), spaceAfter=12)
    normal_style = ParagraphStyle('CustomNormal', parent=styles['Normal'], fontSize=10, spaceAfter=6)

    story = []
    story.append(Paragraph("🎓 Student Score Predictor — Official Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Student Information", heading_style))
    story.append(Paragraph(f"Name: {user_data.get('full_name', username)}", normal_style))
    story.append(Paragraph(f"Username: {username}", normal_style))
    if st.session_state.user_role == "student":
        story.append(Paragraph(f"Grade: {user_data.get('grade', 'N/A')}", normal_style))
        story.append(Paragraph(f"School: {user_data.get('school', 'N/A')}", normal_style))
    else:
        story.append(Paragraph(f"Child Name: {user_data.get('child_name', 'N/A')}", normal_style))
        story.append(Paragraph(f"Child Grade: {user_data.get('child_grade', 'N/A')}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Prediction Results", heading_style))
    score_data = [["Metric", "Value"], ["Predicted Exam Score", f"{final_score}/100"]]
    score_table = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (1,0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0,0), (1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (1,0), 12),
        ('BOTTOMPADDING', (0,0), (1,0), 12),
        ('BACKGROUND', (0,1), (1,1), colors.HexColor('#caf0f8')),
        ('GRID', (0,0), (1,1), 1, colors.HexColor('#90e0ef'))
    ]))
    story.append(score_table)
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Input Details", heading_style))
    input_data = [
        ["Parameter", "Value"],
        ["Study Hours", f"{hours} hours"],
        ["Attendance", f"{attendance}%"],
        ["Previous Score", f"{previous}/100"],
        ["Sleep Hours", f"{sleep} hours"]
    ]
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
    story.append(Spacer(1, 0.2*inch))

    story.append(Paragraph("Performance Assessment", heading_style))
    if final_score >= 85:
        assessment = "🌟 EXCEPTIONAL PERFORMANCE — Outstanding results!"
    elif final_score >= 70:
        assessment = "📈 GOOD PERFORMANCE — Keep improving!"
    elif final_score >= 55:
        assessment = "📚 SATISFACTORY PERFORMANCE — Room for improvement"
    else:
        assessment = "⚠️ NEEDS IMPROVEMENT — Review recommendations below"
    story.append(Paragraph(assessment, normal_style))

    if recommendations:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", normal_style))

    story.append(Spacer(1, 0.3*inch))
    story.append(Paragraph(
        "Generated by Student Score Predictor — AI Powered Academic Tool",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)
    ))
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================
# SESSION STATE
# =====================================
for k, v in [('logged_in', False), ('username', ''), ('user_role', ''),
              ('auth_mode', 'login'), ('signup_role', 'student'), ('theme', 'dark'),
              ('show_profile_edit', False), ('last_pdf', None), ('last_score', None),
              ('last_recs', []), ('last_inputs', {})]:
    if k not in st.session_state:
        st.session_state[k] = v

all_history = load_history()

# =====================================
# THEME CSS
# =====================================
# Palette: #03045e #0077b6 #00b4d8 #90e0ef #caf0f8

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
    background: #1E1E1E;
    border-radius: 24px;
    padding: 2rem 2.5rem;
    border: 1px solid #2F2F2F;
    box-shadow: 0 4px 20px rgba(0,0,0,0.35);
}
[data-testid="stSidebar"] {
    background: #181818;
    border-right: 1px solid rgba(0,180,216,0.2);
}
.stApp, .stApp * { color: #EAEAEA !important; }
h1,h2,h3 { color: #90e0ef !important; }

/* Inputs */
.stNumberInput input, .stTextInput input, .stDateInput input {
    background: rgba(0,20,60,0.6) !important;
    border: 1px solid rgba(0,180,216,0.35) !important;
    border-radius: 12px !important;
    padding: 0.5rem 0.9rem !important;
    color: #caf0f8 !important;
    transition: border-color 0.3s, box-shadow 0.3s !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #00b4d8 !important;
    box-shadow: 0 0 0 3px rgba(0,180,216,0.15) !important;
}
div[data-baseweb="select"] > div {
    background: rgba(0,20,60,0.6) !important;
    border: 1px solid rgba(0,180,216,0.35) !important;
    border-radius: 12px !important;
    transition: border-color 0.3s !important;
}
div[data-baseweb="select"] > div:hover { border-color: #00b4d8 !important; }
div[data-baseweb="popover"] div { background: #020a20 !important; border: 1px solid #0077b6 !important; }
li[role="option"] { color: #caf0f8 !important; }
li[role="option"]:hover { background: #0077b6 !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #4F8CFF 0%, #2563EB 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.5rem 1.4rem !important;
    font-weight: 600 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.3) !important;
    position: relative !important;
    overflow: hidden !important;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 8px 30px rgba(0,180,216,0.5) !important;
   background: linear-gradient(135deg, #6EA8FF 0%, #4F8CFF 100%) !important;
    color: #03045e !important;
}
.stButton > button:active { transform: translateY(-1px) scale(0.99) !important; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: rgba(0,180,216,0.12) !important;
    border: 1.5px solid #00b4d8 !important;
    color: #90e0ef !important;
    border-radius: 50px !important;
    padding: 0.35rem 1rem !important;
    font-size: 0.8rem !important;
    transition: all 0.3s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(0,180,216,0.25) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 20px rgba(0,180,216,0.3) !important;
}

/* Result Card */
.result-card {
    background: linear-gradient(135deg, rgba(3,4,94,0.9) 0%, rgba(0,20,60,0.95) 100%);
    border: 2px solid #00b4d8;
    border-radius: 20px;
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0;
    box-shadow: 0 0 40px rgba(0,180,216,0.2), inset 0 1px 0 rgba(0,180,216,0.2);
    position: relative;
    overflow: hidden;
}
.result-card::before {
    content: '';
    position: absolute; top: -50%; left: -50%; width: 200%; height: 200%;
    background: radial-gradient(circle at center, rgba(0,180,216,0.05) 0%, transparent 60%);
    pointer-events: none;
}
.result-score { color: #00b4d8 !important; font-weight: 800 !important; font-size: 3rem !important; font-family: 'Syne', sans-serif !important; text-shadow: 0 0 30px rgba(0,180,216,0.5); }
.result-label { color: #90e0ef !important; font-size: 0.65rem !important; letter-spacing: 3px !important; text-transform: uppercase; }

/* Theme toggle */
.top-theme-toggle { position: fixed; top: 0.8rem; right: 1rem; z-index: 999; }
.top-theme-toggle .stButton > button {
    background: rgba(0,180,216,0.1) !important;
    border: 1px solid rgba(0,180,216,0.4) !important;
    color: #90e0ef !important;
    padding: 0.2rem 0.8rem !important;
    font-size: 0.7rem !important;
    box-shadow: none !important;
}

/* Profile card */
.profile-card { text-align: center; padding: 0.8rem; }
.profile-name { font-size: 1rem; font-weight: 700; color: #caf0f8 !important; font-family: 'Syne', sans-serif !important; }
.profile-role {
    font-size: 0.62rem; padding: 0.2rem 0.7rem; border-radius: 50px;
    display: inline-block; background: rgba(0,180,216,0.12);
    border: 1px solid rgba(0,180,216,0.4); color: #90e0ef !important;
    letter-spacing: 1px; text-transform: uppercase;
}
.avatar-circle {
    width: 72px; height: 72px; border-radius: 50%;
    border: 2.5px solid #00b4d8;
    box-shadow: 0 0 20px rgba(0,180,216,0.3);
    margin: 0 auto 0.5rem;
    overflow: hidden; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0077b6, #00b4d8);
    font-size: 1.8rem;
}
.avatar-circle img { width: 100%; height: 100%; object-fit: cover; }

/* Stat cards */
.stat-card {
    background: rgba(0,20,60,0.5);
    border: 1px solid rgba(0,180,216,0.2);
    border-radius: 14px; padding: 0.8rem; text-align: center;
    transition: all 0.3s !important;
    box-shadow: 0 2px 12px rgba(0,180,216,0.05);
}
.stat-card:hover { border-color: #00b4d8 !important; transform: translateY(-2px); box-shadow: 0 6px 20px rgba(0,180,216,0.15) !important; }
.stat-value { font-size: 1.6rem; font-weight: 800; color: #00b4d8 !important; font-family: 'Syne', sans-serif !important; }
.stat-value-red { font-size: 1.6rem; font-weight: 800; color: #f87171 !important; font-family: 'Syne', sans-serif !important; }
.stat-label { font-size: 0.58rem; color: #90e0ef !important; letter-spacing: 1px; text-transform: uppercase; margin-top: 0.2rem; }

/* Alerts */
div[data-testid="stAlert"] { border-radius: 12px !important; border-left-width: 4px !important; }

/* Section headers */
.section-header {
    font-family: 'Syne', sans-serif;
    color: #90e0ef !important;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin: 1.2rem 0 0.6rem;
    display: flex; align-items: center; gap: 0.5rem;
}
.section-header::after {
    content: ''; flex: 1; height: 1px;
    background: linear-gradient(90deg, rgba(0,180,216,0.4), transparent);
    margin-left: 0.5rem;
}

/* File uploader */
[data-testid="stFileUploader"] {
    background: rgba(0,20,60,0.4) !important;
    border: 2px dashed rgba(0,180,216,0.3) !important;
    border-radius: 14px !important;
    transition: border-color 0.3s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #00b4d8 !important; }

hr { border-color: rgba(0,180,216,0.15) !important; margin: 1rem 0 !important; }
input::placeholder { color: rgba(144,224,239,0.4) !important; }

/* Number input buttons */
.stNumberInput button {
    background: rgba(0,40,100,0.5) !important;
    border: 1px solid rgba(0,180,216,0.3) !important;
    color: #90e0ef !important;
    transition: all 0.2s !important;
}
.stNumberInput button:hover { background: #0077b6 !important; color: white !important; transform: scale(1.1) !important; }

/* Share section */
.share-box {
    background: rgba(0,180,216,0.06);
    border: 1px solid rgba(0,180,216,0.25);
    border-radius: 16px;
    padding: 1rem;
    margin: 0.5rem 0;
}
</style>
"""

LIGHT_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

* { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Syne', sans-serif !important; }

.stApp {
    background: linear-gradient(145deg, #caf0f8 0%, #90e0ef 30%, #caf0f8 70%, #e0f7fa 100%);
}
.main .block-container {
    background: rgba(255,255,255,0.88);
    border-radius: 24px;
    padding: 2rem 2.5rem;
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

/* Inputs */
.stNumberInput input, .stTextInput input, .stDateInput input {
    background: rgba(202,240,248,0.4) !important;
    border: 1.5px solid rgba(0,119,182,0.3) !important;
    border-radius: 12px !important;
    color: #03045e !important;
    transition: all 0.3s !important;
}
.stNumberInput input:focus, .stTextInput input:focus {
    border-color: #0077b6 !important;
    box-shadow: 0 0 0 3px rgba(0,119,182,0.1) !important;
}
div[data-baseweb="select"] > div {
    background: rgba(202,240,248,0.4) !important;
    border: 1.5px solid rgba(0,119,182,0.3) !important;
    border-radius: 12px !important;
    transition: border-color 0.3s !important;
}
div[data-baseweb="select"] > div:hover { border-color: #0077b6 !important; }
div[data-baseweb="popover"] div { background: #f0faff !important; border: 1px solid #90e0ef !important; }
li[role="option"] { color: #03045e !important; }
li[role="option"]:hover { background: #0077b6 !important; color: white !important; }

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #0077b6 0%, #00b4d8 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.5rem 1.4rem !important;
    font-weight: 700 !important;
    font-family: 'Syne', sans-serif !important;
    letter-spacing: 0.5px !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.25) !important;
}
.stButton > button:hover {
    transform: translateY(-3px) scale(1.03) !important;
    box-shadow: 0 10px 30px rgba(0,119,182,0.4) !important;
    background: linear-gradient(135deg, #03045e 0%, #0077b6 100%) !important;
}
.stButton > button:active { transform: translateY(-1px) !important; }

/* Download button */
[data-testid="stDownloadButton"] button {
    background: rgba(0,119,182,0.08) !important;
    border: 1.5px solid #0077b6 !important;
    color: #0077b6 !important;
    border-radius: 50px !important;
    padding: 0.35rem 1rem !important;
    transition: all 0.3s !important;
}
[data-testid="stDownloadButton"] button:hover {
    background: rgba(0,119,182,0.18) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 4px 15px rgba(0,119,182,0.2) !important;
}

/* Result Card */
.result-card {
    background: linear-gradient(135deg, #03045e 0%, #0077b6 100%);
    border: 2px solid #00b4d8;
    border-radius: 20px;
    padding: 1.5rem;
    text-align: center;
    margin: 1rem 0;
    box-shadow: 0 8px 30px rgba(0,119,182,0.3);
}
.result-score { color: #caf0f8 !important; font-weight: 800 !important; font-size: 3rem !important; font-family: 'Syne', sans-serif !important; }
.result-label { color: #90e0ef !important; font-size: 0.65rem !important; letter-spacing: 3px !important; text-transform: uppercase; }

/* Theme toggle */
.top-theme-toggle { position: fixed; top: 0.8rem; right: 1rem; z-index: 999; }
.top-theme-toggle .stButton > button {
    background: rgba(0,119,182,0.1) !important;
    border: 1px solid rgba(0,119,182,0.4) !important;
    color: #0077b6 !important;
    padding: 0.2rem 0.8rem !important;
    font-size: 0.7rem !important;
    box-shadow: none !important;
}

/* Profile */
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
    border: 2.5px solid #0077b6;
    box-shadow: 0 4px 15px rgba(0,119,182,0.25);
    margin: 0 auto 0.5rem;
    overflow: hidden; display: flex; align-items: center; justify-content: center;
    background: linear-gradient(135deg, #0077b6, #00b4d8);
    font-size: 1.8rem;
}
.avatar-circle img { width: 100%; height: 100%; object-fit: cover; }

/* Stat cards */
.stat-card {
    background: linear-gradient(135deg, rgba(202,240,248,0.6), rgba(144,224,239,0.3));
    border: 1px solid rgba(0,119,182,0.2);
    border-radius: 14px; padding: 0.8rem; text-align: center;
    transition: all 0.3s !important;
    box-shadow: 0 2px 10px rgba(0,119,182,0.08);
}
.stat-card:hover { border-color: #0077b6 !important; transform: translateY(-3px); box-shadow: 0 8px 25px rgba(0,119,182,0.2) !important; }
.stat-value { font-size: 1.6rem; font-weight: 800; color: #0077b6 !important; font-family: 'Syne', sans-serif !important; }
.stat-value-red { font-size: 1.6rem; font-weight: 800; color: #dc2626 !important; font-family: 'Syne', sans-serif !important; }
.stat-label { font-size: 0.58rem; color: #03045e !important; letter-spacing: 1px; text-transform: uppercase; opacity: 0.7; margin-top: 0.2rem; }

.section-header {
    font-family: 'Syne', sans-serif;
    color: #03045e !important;
    font-size: 1.1rem;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin: 1.2rem 0 0.6rem;
    display: flex; align-items: center; gap: 0.5rem;
}

[data-testid="stFileUploader"] {
    background: rgba(202,240,248,0.4) !important;
    border: 2px dashed rgba(0,119,182,0.3) !important;
    border-radius: 14px !important;
    transition: border-color 0.3s !important;
}
[data-testid="stFileUploader"]:hover { border-color: #0077b6 !important; }

.stNumberInput button {
    background: rgba(202,240,248,0.7) !important;
    border: 1px solid rgba(0,119,182,0.3) !important;
    transition: all 0.2s !important;
}
.stNumberInput button:hover { background: #0077b6 !important; color: white !important; transform: scale(1.1) !important; }

.share-box {
    background: rgba(0,119,182,0.05);
    border: 1px solid rgba(0,119,182,0.2);
    border-radius: 16px;
    padding: 1rem;
    margin: 0.5rem 0;
}

hr { border-color: rgba(0,119,182,0.15) !important; margin: 1rem 0 !important; }
input::placeholder { color: rgba(3,4,94,0.35) !important; }
</style>
"""

def apply_theme():
    st.markdown(DARK_CSS if st.session_state.theme == "dark" else LIGHT_CSS, unsafe_allow_html=True)

def theme_toggle():
    icon = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(icon, key="theme_toggle"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# =====================================
# AUTH PAGE
# =====================================
def show_auth_page():
    apply_theme()
    st.markdown('<div class="top-theme-toggle">', unsafe_allow_html=True)
    theme_toggle()
    st.markdown('</div>', unsafe_allow_html=True)

    users = load_users()
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.5rem;">
            <div style="font-size:3rem;filter:drop-shadow(0 0 20px rgba(0,180,216,0.5));">🎓</div>
            <h1 style="font-size:1.6rem;margin:0.3rem 0;letter-spacing:-0.5px;">Student Score Predictor</h1>
            <p style="font-size:0.75rem;opacity:0.6;margin:0;">AI Powered Academic Tool</p>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.auth_mode == "login":
            username = st.text_input("Username", placeholder="Enter username", key="login_user", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Enter password", key="login_pass", label_visibility="collapsed")
            if username and username in users:
                role = users[username]["role"]
                ri = "🎓" if role == "student" else "👨‍👩‍👧"
                rt = "Student" if role == "student" else "Parent"
                st.markdown(f'<p style="text-align:center;font-size:0.7rem;margin-top:-0.3rem;opacity:0.7;">{ri} {rt}</p>', unsafe_allow_html=True)
            if st.button("Sign In →", use_container_width=True):
                if username and password:
                    if username in users and users[username]["password"] == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_role = users[username]["role"]
                        st.rerun()
                    else:
                        st.error("❌ Invalid credentials")
                else:
                    st.warning("Please fill all fields")
            st.markdown("<hr>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🎓 Student Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "student"
                    st.rerun()
            with col_b:
                if st.button("👨‍👩‍👧 Parent Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "parent"
                    st.rerun()
        else:
            role = st.session_state.signup_role
            st.markdown(f'<p style="text-align:center;margin-bottom:0.8rem;font-size:0.85rem;font-weight:600;">Create {role.capitalize()} Account</p>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("🎓 Student", use_container_width=True):
                    st.session_state.signup_role = "student"; st.rerun()
            with col_b:
                if st.button("👨‍👩‍👧 Parent", use_container_width=True):
                    st.session_state.signup_role = "parent"; st.rerun()
            st.markdown("---")
            username = st.text_input("Username", placeholder="Choose username", key="signup_user", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Password (min 4 chars)", key="signup_pass", label_visibility="collapsed")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm password", key="signup_confirm", label_visibility="collapsed")
            full_name = st.text_input("Full Name", placeholder="Your full name", key="signup_name", label_visibility="collapsed")
            if role == "student":
                dob = st.date_input("Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now())
                grade = st.selectbox("Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                school = st.text_input("School Name", placeholder="School/College name")
            else:
                child_name = st.text_input("Child's Name", placeholder="Child's full name")
                child_dob = st.date_input("Child's DOB", min_value=datetime(1990,1,1), max_value=datetime.now())
                child_grade = st.selectbox("Child's Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                relation = st.selectbox("Relationship", ["Father","Mother","Guardian"])
            if st.button("Create Account ✓", use_container_width=True):
                if not username or not password or not full_name:
                    st.warning("Fill all required fields")
                elif password != confirm:
                    st.error("Passwords don't match")
                elif len(password) < 4:
                    st.warning("Password minimum 4 characters")
                elif username in users:
                    st.error("Username already exists")
                else:
                    data = {"password": hash_password(password), "role": role,
                            "full_name": full_name, "created_at": str(pd.Timestamp.now())}
                    if role == "student":
                        data["dob"] = str(dob); data["age"] = calculate_age(dob)
                        data["grade"] = grade; data["school"] = school
                    else:
                        data["child_name"] = child_name; data["child_dob"] = str(child_dob)
                        data["child_age"] = calculate_age(child_dob)
                        data["child_grade"] = child_grade; data["relation"] = relation
                    users[username] = data
                    save_users(users)
                    st.success("✅ Account created! Please sign in.")
                    st.session_state.auth_mode = "login"
                    st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True):
                st.session_state.auth_mode = "login"; st.rerun()

        st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1rem;opacity:0.4;">🔒 Secure Portal · AI Powered</p>', unsafe_allow_html=True)

# =====================================
# LOAD MODEL
# =====================================
@st.cache_resource
def load_models():
    model = joblib.load("student_model.pkl")
    columns = joblib.load("model_columns.pkl")
    return model, columns

# =====================================
# SIDEBAR
# =====================================
def show_sidebar(user_data):
    with st.sidebar:
        # Profile picture
        pic_b64 = get_profile_pic_base64(st.session_state.username)
        role_text = "Student" if st.session_state.user_role == "student" else "Parent"
        role_icon = "🎓" if st.session_state.user_role == "student" else "👨‍👩‍👧"

        if pic_b64:
            avatar_html = f'<img src="data:image/jpeg;base64,{pic_b64}" />'
        else:
            avatar_html = role_icon

        st.markdown(f"""
        <div class="profile-card">
            <div class="avatar-circle">{avatar_html}</div>
            <div class="profile-name">{user_data.get('full_name', st.session_state.username)}</div>
            <div class="profile-role">{role_text}</div>
        </div>
        """, unsafe_allow_html=True)

        # Profile Edit Toggle
        if st.button("✏️ Edit Profile Picture", use_container_width=True, key="toggle_pic"):
            st.session_state.show_profile_edit = not st.session_state.show_profile_edit
            st.rerun()

        if st.session_state.show_profile_edit:
            uploaded_pic = st.file_uploader(
                "Upload Profile Picture", type=["jpg","jpeg","png"],
                key="pic_uploader", label_visibility="collapsed"
            )
            if uploaded_pic:
                save_profile_pic(st.session_state.username, uploaded_pic.read())
                st.success("✅ Picture updated!")
                st.session_state.show_profile_edit = False
                st.rerun()

        st.markdown("---")
        st.markdown("### 👤 Account")
        st.markdown(f"**User:** `{st.session_state.username}`")
        st.markdown(f"**Name:** {user_data.get('full_name', 'N/A')}")
        if st.session_state.user_role == "student":
            st.markdown(f"**Age:** {user_data.get('age', 'N/A')}")
            st.markdown(f"**Grade:** {user_data.get('grade', 'N/A')}")
            st.markdown(f"**School:** {user_data.get('school', 'N/A')}")
        else:
            st.markdown(f"**Child:** {user_data.get('child_name', 'N/A')}")
            st.markdown(f"**Child Grade:** {user_data.get('child_grade', 'N/A')}")
            st.markdown(f"**Relation:** {user_data.get('relation', 'N/A')}")

        st.markdown("---")
        theme_toggle()
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            for k in ['logged_in','username','user_role','show_profile_edit','last_pdf','last_score','last_recs','last_inputs']:
                if k in ['logged_in']:
                    st.session_state[k] = False
                elif k in ['username','user_role']:
                    st.session_state[k] = ''
                else:
                    st.session_state[k] = None if k == 'last_pdf' else ([] if k == 'last_recs' else {})
            st.rerun()

# =====================================
# MAIN APP
# =====================================
def show_main_app():
    apply_theme()
    users = load_users()
    user_data = users.get(st.session_state.username, {})
    show_sidebar(user_data)

    st.markdown("<h1 style='text-align:center;letter-spacing:-1px;'>🎓 Student Score Predictor</h1>", unsafe_allow_html=True)

    if st.session_state.user_role == "parent":
        child_name = user_data.get("child_name", "Child")
        st.info(f"👨‍👩‍👧 Predicting for: **{child_name}**")

    model, columns = load_models()

    st.markdown('<div class="section-header">📋 Input Parameters</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        hours = st.number_input("📖 Hours Studied", min_value=0.0, max_value=24.0, value=5.0, step=0.5)
        attendance = st.number_input("🏫 Attendance (%)", min_value=0.0, max_value=100.0, value=75.0, step=5.0)
        previous = st.number_input("📊 Previous Score", min_value=0.0, max_value=100.0, value=60.0, step=5.0)
        sleep = st.number_input("💤 Sleep Hours", min_value=0.0, max_value=12.0, value=7.0, step=0.5)
        motivation = st.selectbox("🔥 Motivation Level", ["Low", "Medium", "High"])
        teacher = st.selectbox("👩‍🏫 Teacher Quality", ["Poor", "Average", "Good"])
        school = st.selectbox("🏛️ School Type", ["Public", "Private"])
    with col2:
        internet = st.selectbox("🌐 Internet Access", ["Yes", "No"])
        income = st.selectbox("💰 Family Income", ["Low", "Medium", "High"])
        parent = st.selectbox("👨‍👩‍👦 Parental Involvement", ["Low", "Medium", "High"])
        education = st.selectbox("🎓 Parent Education", ["School", "College"])
        peer = st.selectbox("👥 Peer Influence", ["Negative", "Neutral", "Positive"])
        resources = st.selectbox("📚 Learning Resources", ["Low", "Medium", "High"])
        activities = st.selectbox("⚽ Extracurricular Activities", ["Yes", "No"])

    st.markdown("")
    predict_btn = st.button("🚀 Predict My Score", use_container_width=True)

    if predict_btn:
        data = {
            "Hours_Studied": hours, "Attendance": attendance, "Previous_Scores": previous,
            "Sleep_Hours": sleep, "Motivation_Level": motivation, "Teacher_Quality": teacher,
            "School_Type": school, "Internet_Access": internet, "Family_Income": income,
            "Parental_Involvement": parent, "Parental_Education_Level": education,
            "Peer_Influence": peer, "Learning_Resources": resources,
            "Extracurricular_Activities": activities
        }
        input_df = pd.DataFrame([data])
        input_df = pd.get_dummies(input_df)
        input_df = input_df.reindex(columns=columns, fill_value=0)
        prediction = model.predict(input_df)
        final_score = max(40, min(100, int(round(prediction[0]))))

        # Save history
        if st.session_state.username not in all_history:
            all_history[st.session_state.username] = []
        all_history[st.session_state.username].append(final_score)
        if len(all_history[st.session_state.username]) > 10:
            all_history[st.session_state.username] = all_history[st.session_state.username][-10:]
        save_history(all_history)

        recs = []
        if hours < 6: recs.append("Increase study hours to 6–8 daily")
        if attendance < 75: recs.append("Improve attendance to 80%+")
        if sleep < 7: recs.append("Get 7–9 hours of sleep daily")
        if motivation == "Low": recs.append("Set daily goals to boost motivation")
        if teacher == "Poor": recs.append("Seek additional tutoring support")
        if resources == "Low": recs.append("Utilize free online learning materials")
        if peer == "Negative": recs.append("Join positive study groups")

        # Store in session for share/download
        st.session_state.last_score = final_score
        st.session_state.last_recs = recs
        st.session_state.last_inputs = {"hours": hours, "attendance": attendance,
                                         "previous": previous, "sleep": sleep}
        pdf_buf = generate_pdf_report(st.session_state.username, final_score, user_data,
                                       hours, attendance, previous, sleep, recs)
        st.session_state.last_pdf = pdf_buf.read()

        # Result display
        st.markdown(f"""
        <div class="result-card">
            <div class="result-label">PREDICTED EXAM SCORE</div>
            <div class="result-score">{final_score}<span style="font-size:1.2rem;opacity:0.7"> / 100</span></div>
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

    # ── Show results section if we have a last prediction ──
    user_history = all_history.get(st.session_state.username, [])

    if st.session_state.last_score is not None:
        final_score = st.session_state.last_score
        recs = st.session_state.last_recs
        inp = st.session_state.last_inputs

        # ── Download & Share ──
        st.markdown('<div class="section-header">📤 Download & Share Report</div>', unsafe_allow_html=True)
        st.markdown('<div class="share-box">', unsafe_allow_html=True)
        col_dl, col_share = st.columns([1,1])
        with col_dl:
            if st.session_state.last_pdf:
                fname = f"score_report_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.pdf"
                st.download_button(
                    label="📄 Download PDF Report",
                    data=st.session_state.last_pdf,
                    file_name=fname,
                    mime="application/pdf",
                    use_container_width=True
                )
        with col_share:
            share_text = (
                f"🎓 My Predicted Score: {final_score}/100\n"
                f"📖 Study Hours: {inp.get('hours','N/A')}\n"
                f"🏫 Attendance: {inp.get('attendance','N/A')}%\n"
                f"📊 Previous Score: {inp.get('previous','N/A')}\n"
                f"Generated by Student Score Predictor"
            )
            st.download_button(
                label="📋 Download Score Summary (TXT)",
                data=share_text,
                file_name=f"score_summary_{st.session_state.username}.txt",
                mime="text/plain",
                use_container_width=True
            )
        # WhatsApp share link
        wa_text = f"🎓 My Predicted Exam Score: {final_score}/100! Generated by Student Score Predictor AI."
        wa_url = f"https://wa.me/?text={wa_text.replace(' ', '%20')}"
        email_subject = "My Predicted Exam Score"
        email_body = share_text.replace('\n', '%0A')
        email_url = f"mailto:?subject={email_subject}&body={email_body}"

        st.markdown(f"""
        <div style="display:flex;gap:0.8rem;margin-top:0.6rem;flex-wrap:wrap;">
            <a href="{wa_url}" target="_blank" style="text-decoration:none;">
                <button style="background:linear-gradient(135deg,#25d366,#128c7e);color:white;border:none;border-radius:50px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600;cursor:pointer;transition:all 0.3s;box-shadow:0 3px 12px rgba(37,211,102,0.3);">
                    📱 Share on WhatsApp
                </button>
            </a>
            <a href="{email_url}" target="_blank" style="text-decoration:none;">
                <button style="background:linear-gradient(135deg,#0077b6,#00b4d8);color:white;border:none;border-radius:50px;padding:0.35rem 1rem;font-size:0.78rem;font-weight:600;cursor:pointer;transition:all 0.3s;box-shadow:0 3px 12px rgba(0,119,182,0.3);">
                    📧 Share via Email
                </button>
            </a>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Performance Overview ──
    if len(user_history) >= 1:
        st.markdown('<div class="section-header">📊 Performance Overview</div>', unsafe_allow_html=True)

        passing = len([s for s in user_history if s >= 60])
        needs_imp = len([s for s in user_history if s < 60])
        avg_score = int(np.mean(user_history))
        pass_pct = (passing / len(user_history)) * 100
        best = max(user_history)
        last = user_history[-1]

        cols = st.columns(5)
        stats = [
            (cols[0], last, "Last Score", False),
            (cols[1], avg_score, "Average", False),
            (cols[2], best, "Best Score", False),
            (cols[3], passing, "Passed", False),
            (cols[4], needs_imp, "Need Improve", True),
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
        st.caption(f"✅ Success Rate: {pass_pct:.0f}% ({passing}/{len(user_history)} attempts passed)")

        # ── Score History Graph (with Plotly-style via Streamlit) ──
        st.markdown('<div class="section-header">📈 Score History</div>', unsafe_allow_html=True)

        attempts = [f"#{i}" for i in range(1, len(user_history)+1)]
        chart_df = pd.DataFrame({
            "Your Score": user_history,
            "Pass Line (60)": [60] * len(user_history),
            "Good Line (70)": [70] * len(user_history),
            "Excellent (85)": [85] * len(user_history),
        }, index=attempts)

        st.line_chart(chart_df, use_container_width=True, height=300)
        st.caption("📌 Blue = Your score | Benchmarks: Pass=60, Good=70, Excellent=85")

        st.markdown('<div class="section-header">📊 Score Comparison (Bar)</div>', unsafe_allow_html=True)
        bar_df = pd.DataFrame({"Score": user_history}, index=attempts)
        st.bar_chart(bar_df, use_container_width=True, height=220)

        # Score trend text
        if len(user_history) >= 2:
            trend = user_history[-1] - user_history[-2]
            if trend > 0:
                st.success(f"📈 Improving! +{trend} points from last attempt")
            elif trend < 0:
                st.warning(f"📉 Declined by {abs(trend)} points. Review recommendations!")
            else:
                st.info("➡️ Same as last attempt. Aim higher!")

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
    st.caption("🎓 Student Score Predictor · AI Powered Academic Tool · Built with ❤️")

# =====================================
# MAIN
# =====================================
if st.session_state.logged_in:
    show_main_app()
else:
    show_auth_page()
