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
    page_title="EduPredict AI",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =====================================
# FILE PATHS
# =====================================
USER_DB_FILE   = "users.json"
HISTORY_FILE   = "prediction_history.json"
PROFILE_PICS_DIR = "profile_pics"
OTP_FILE       = "otp_store.json"

if not os.path.exists(PROFILE_PICS_DIR):
    os.makedirs(PROFILE_PICS_DIR)

# =====================================
# EMAIL CONFIG — apna Gmail set karo
# =====================================
EMAIL_SENDER   = "your_email@gmail.com"
EMAIL_PASSWORD = "your_app_password_here"

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
        msg["Subject"] = "🎓 EduPredict AI — Your OTP Code"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = receiver_email
        html_body = f"""
        <html><body style="font-family:'Segoe UI',Arial,sans-serif;background:#050d1a;padding:40px 20px;">
        <div style="max-width:460px;margin:0 auto;background:linear-gradient(135deg,#0a1628,#0d2137);
            border-radius:20px;padding:36px;border:1px solid rgba(0,212,255,0.3);
            box-shadow:0 0 40px rgba(0,212,255,0.1);">
            <div style="text-align:center;margin-bottom:24px;">
                <div style="font-size:3rem;">🎓</div>
                <h2 style="color:#00d4ff;margin:8px 0;font-size:1.5rem;letter-spacing:-0.5px;">EduPredict AI</h2>
                <p style="color:#6b8fa3;font-size:0.8rem;margin:0;">Academic Intelligence Platform</p>
            </div>
            <p style="color:#c8dde8;font-size:0.95rem;">Hello <strong style="color:#fff;">{full_name}</strong>,</p>
            <p style="color:#c8dde8;">Your one-time verification code:</p>
            <div style="text-align:center;margin:28px 0;">
                <div style="background:linear-gradient(135deg,rgba(0,212,255,0.15),rgba(0,212,255,0.05));
                    border:2px solid rgba(0,212,255,0.5);border-radius:16px;padding:20px 32px;display:inline-block;">
                    <span style="font-size:2.8rem;font-weight:900;color:#00d4ff;letter-spacing:16px;font-family:monospace;">
                        {otp_code}
                    </span>
                </div>
            </div>
            <p style="color:#6b8fa3;font-size:0.82rem;text-align:center;">
                ⏱️ Valid for <strong style="color:#00d4ff;">10 minutes</strong> · Do not share with anyone
            </p>
            <hr style="border-color:rgba(0,212,255,0.1);margin:20px 0;">
            <p style="color:#4a6172;font-size:0.72rem;text-align:center;margin:0;">
                If you didn't request this, safely ignore this email.
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
# PDF REPORT GENERATOR
# =====================================
def generate_pdf_report(username, final_score, user_data, hours, attendance, previous, sleep, recommendations):
    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.6*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()

    title_style   = ParagraphStyle('T', parent=styles['Heading1'], fontSize=22,
        textColor=colors.HexColor('#0077b6'), alignment=1, spaceAfter=16)
    heading_style = ParagraphStyle('H', parent=styles['Heading2'], fontSize=13,
        textColor=colors.HexColor('#023e8a'), spaceAfter=8, spaceBefore=14)
    normal_style  = ParagraphStyle('N', parent=styles['Normal'], fontSize=10, spaceAfter=4)
    footer_style  = ParagraphStyle('F', parent=styles['Normal'], fontSize=8,
        textColor=colors.grey, alignment=1)

    tbl_header = colors.HexColor('#0077b6')
    tbl_row    = colors.HexColor('#e0f4ff')

    story = []
    story.append(Paragraph("🎓 EduPredict AI — Official Score Report", title_style))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Student Information", heading_style))
    story.append(Paragraph(f"Name:        {user_data.get('full_name', username)}", normal_style))
    story.append(Paragraph(f"Username:    {username}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%d %B %Y  %H:%M')}", normal_style))
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Prediction Result", heading_style))
    score_tbl = Table([["Metric","Value"],["Predicted Exam Score", f"{final_score} / 100"]],
                      colWidths=[2.8*inch, 2.8*inch])
    score_tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0), tbl_header), ('TEXTCOLOR',(0,0),(1,0), colors.whitesmoke),
        ('ALIGN',(0,0),(1,-1),'CENTER'), ('FONTNAME',(0,0),(1,0),'Helvetica-Bold'),
        ('BOTTOMPADDING',(0,0),(1,0),10), ('BACKGROUND',(0,1),(1,1), tbl_row),
        ('GRID',(0,0),(1,1),1, colors.HexColor('#90e0ef')),
        ('FONTSIZE',(0,1),(1,1),13), ('FONTNAME',(0,1),(1,1),'Helvetica-Bold'),
    ]))
    story.append(score_tbl)
    story.append(Spacer(1, 0.1*inch))

    story.append(Paragraph("Input Parameters", heading_style))
    input_data = [["Parameter","Value"],
        ["Study Hours / Day", f"{hours} hrs"],
        ["Attendance",        f"{attendance} %"],
        ["Previous Score",    f"{previous} / 100"],
        ["Sleep Hours / Night", f"{sleep} hrs"]]
    inp_tbl = Table(input_data, colWidths=[2.8*inch, 2.8*inch])
    inp_tbl.setStyle(TableStyle([
        ('BACKGROUND',(0,0),(1,0), tbl_header), ('TEXTCOLOR',(0,0),(1,0), colors.whitesmoke),
        ('ALIGN',(0,0),(1,-1),'CENTER'), ('FONTNAME',(0,0),(1,0),'Helvetica-Bold'),
        ('BOTTOMPADDING',(0,0),(1,0),10), ('BACKGROUND',(0,1),(1,-1), tbl_row),
        ('ROWBACKGROUNDS',(0,1),(1,-1),[tbl_row, colors.white]),
        ('GRID',(0,0),(1,-1),1, colors.HexColor('#90e0ef')),
    ]))
    story.append(inp_tbl)

    if recommendations:
        story.append(Spacer(1, 0.1*inch))
        story.append(Paragraph("Personalised Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"  →  {rec}", normal_style))

    story.append(Spacer(1, 0.25*inch))
    story.append(Paragraph("Generated by EduPredict AI · AI-Powered Academic Performance Tool",
                            footer_style))
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================
# SESSION STATE
# =====================================
defaults = {
    'logged_in': False, 'username': '', 'user_role': '',
    'page': 'home',           # 'home' | 'auth' | 'app'
    'auth_tab': 'login',      # 'login' | 'signup'
    'signup_role': 'student',
    'theme': 'dark',
    'show_profile_edit': False,
    'last_pdf': None, 'last_score': None, 'last_recs': [], 'last_inputs': {},
    'otp_email': '', 'otp_verified': False, 'otp_sent': False,
    'study_hours_history': [], 'attendance_history': [],
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

all_history = load_history()

# =====================================
# GLOBAL CSS  (dark + light)
# =====================================
def inject_css():
    is_dark = st.session_state.theme == "dark"
    bg_main    = "radial-gradient(ellipse at 15% 10%, #0a1628 0%, #050d1a 55%, #020810 100%)" if is_dark else "linear-gradient(145deg,#dff6fd 0%,#b0e8f7 40%,#e0f7ff 100%)"
    bg_card    = "rgba(10,22,40,0.75)" if is_dark else "rgba(255,255,255,0.85)"
    border_clr = "rgba(0,212,255,0.2)" if is_dark else "rgba(0,119,182,0.2)"
    text_main  = "#e8f4f8" if is_dark else "#03045e"
    text_sub   = "#6b8fa3" if is_dark else "#0077b6"
    sidebar_bg = "linear-gradient(180deg,#080f1e 0%,#050d1a 100%)" if is_dark else "linear-gradient(180deg,rgba(255,255,255,0.97) 0%,rgba(202,240,248,0.95) 100%)"
    input_bg   = "rgba(5,15,30,0.8)" if is_dark else "rgba(202,240,248,0.5)"
    accent     = "#00d4ff"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');

*, *::before, *::after {{ box-sizing: border-box; }}
* {{ font-family: 'Space Grotesk', sans-serif !important; }}

/* ── APP BACKGROUND ── */
.stApp {{
    background: {bg_main} !important;
    min-height: 100vh;
}}
.main .block-container {{
    background: {bg_card};
    border-radius: 20px;
    padding: 2rem 2.5rem;
    border: 1px solid {border_clr};
    backdrop-filter: blur(20px);
    box-shadow: 0 8px 60px rgba(0,0,0,0.3), inset 0 1px 0 rgba(255,255,255,0.05);
    max-width: 1400px;
}}

/* ── SIDEBAR ── */
[data-testid="stSidebar"] {{
    background: {sidebar_bg} !important;
    border-right: 1px solid {border_clr} !important;
}}

/* ── TEXT COLORS ── */
.stApp, .stApp p, .stApp span, .stApp div, .stApp label {{ color: {text_main} !important; }}
.stApp h1,.stApp h2,.stApp h3 {{ color: {accent} !important; }}
[data-testid="stSidebar"] * {{ color: {text_main} !important; }}
.stCaption, [data-testid="stCaptionContainer"] {{ color: {text_sub} !important; }}
.stAlert p,.stAlert div {{ color: {text_main} !important; }}

/* ── INPUTS ── */
.stNumberInput input, .stTextInput input,
.stDateInput input, .stTextAreaInput textarea {{
    background: {input_bg} !important;
    border: 1.5px solid {border_clr} !important;
    border-radius: 10px !important;
    color: {text_main} !important;
    transition: border-color 0.25s, box-shadow 0.25s !important;
    font-family: 'Space Grotesk', sans-serif !important;
}}
.stNumberInput input:focus, .stTextInput input:focus {{
    border-color: {accent} !important;
    box-shadow: 0 0 0 3px rgba(0,212,255,0.15) !important;
}}
div[data-baseweb="select"] > div {{
    background: {input_bg} !important;
    border: 1.5px solid {border_clr} !important;
    border-radius: 10px !important;
    color: {text_main} !important;
}}
div[data-baseweb="select"] span {{ color: {text_main} !important; }}
div[data-baseweb="popover"] div {{ background: #080f20 !important; border:1px solid #00d4ff !important; }}
li[role="option"] {{ color: {text_main} !important; }}
li[role="option"]:hover {{ background: rgba(0,212,255,0.2) !important; }}

/* ── MAIN BUTTONS ── */
.stButton > button {{
    background: linear-gradient(135deg, #0066cc 0%, #00d4ff 100%) !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 50px !important;
    padding: 0.55rem 1.6rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.3s cubic-bezier(0.34,1.56,0.64,1) !important;
    box-shadow: 0 4px 20px rgba(0,212,255,0.25) !important;
}}
.stButton > button:hover {{
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 10px 35px rgba(0,212,255,0.45) !important;
}}
.stButton > button:active {{ transform: translateY(-1px) scale(0.99) !important; }}

/* ── DOWNLOAD BUTTON ── */
[data-testid="stDownloadButton"] button {{
    background: rgba(0,212,255,0.1) !important;
    border: 1.5px solid {accent} !important;
    color: {text_main} !important;
    border-radius: 50px !important;
    padding: 0.4rem 1.1rem !important;
    font-size: 0.83rem !important;
    transition: all 0.25s !important;
}}
[data-testid="stDownloadButton"] button:hover {{
    background: rgba(0,212,255,0.22) !important;
}}

/* ── CUSTOM COMPONENTS ── */
.metric-card {{
    background: linear-gradient(135deg,rgba(0,212,255,0.08),rgba(0,102,204,0.05));
    border: 1px solid {border_clr};
    border-radius: 16px;
    padding: 1rem;
    text-align: center;
    transition: all 0.3s;
    cursor: default;
}}
.metric-card:hover {{
    border-color: {accent};
    transform: translateY(-4px);
    box-shadow: 0 12px 30px rgba(0,212,255,0.12);
}}
.metric-val   {{ font-size:1.7rem; font-weight:800; color:{accent} !important; font-family:'JetBrains Mono',monospace !important; }}
.metric-val-r {{ font-size:1.7rem; font-weight:800; color:#f87171 !important; font-family:'JetBrains Mono',monospace !important; }}
.metric-label {{ font-size:0.57rem; color:{text_sub} !important; letter-spacing:1.5px; text-transform:uppercase; margin-top:2px; }}

.result-card {{
    background: linear-gradient(135deg,#03245e,#004a8f);
    border: 2px solid {accent};
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    margin: 1.2rem 0;
    box-shadow: 0 0 60px rgba(0,212,255,0.2);
    position: relative;
    overflow: hidden;
}}
.result-card::before {{
    content:'';
    position:absolute;top:-60px;right:-60px;
    width:180px;height:180px;
    background:radial-gradient(circle,rgba(0,212,255,0.15),transparent 70%);
    border-radius:50%;
}}
.result-score {{ font-size:3.8rem; font-weight:900; color:#00d4ff !important; font-family:'JetBrains Mono',monospace !important; line-height:1; }}
.result-label {{ font-size:0.65rem; letter-spacing:4px; text-transform:uppercase; color:rgba(0,212,255,0.7) !important; margin-bottom:0.5rem; }}

.section-hdr {{
    font-size:0.65rem; letter-spacing:3px; text-transform:uppercase;
    color:{text_sub} !important; margin:1.8rem 0 0.8rem;
    display:flex; align-items:center; gap:8px;
}}
.section-hdr::after {{
    content:''; flex:1; height:1px;
    background:linear-gradient(90deg,{border_clr},transparent);
}}

.share-panel {{
    background: rgba(0,212,255,0.04);
    border: 1px solid {border_clr};
    border-radius: 16px;
    padding: 1.2rem;
    margin: 0.6rem 0;
}}
.otp-panel {{
    background: rgba(0,212,255,0.06);
    border: 1.5px solid {border_clr};
    border-radius: 14px;
    padding: 1.4rem;
    margin: 0.8rem 0;
}}
.profile-card {{ text-align:center; padding:0.8rem 0; }}
.profile-name {{
    font-size:1rem; font-weight:700;
    color:{text_main} !important;
    margin: 0.3rem 0 0.2rem;
}}
.profile-badge {{
    font-size:0.6rem; padding:0.25rem 0.8rem; border-radius:50px;
    background:rgba(0,212,255,0.1); border:1px solid {border_clr};
    color:{accent} !important; letter-spacing:1.5px; text-transform:uppercase;
    display:inline-block;
}}
.avatar {{
    width:72px;height:72px;border-radius:50%;
    border:2.5px solid {accent};
    box-shadow:0 0 20px rgba(0,212,255,0.3);
    margin:0 auto 0.4rem;overflow:hidden;
    display:flex;align-items:center;justify-content:center;
    background:linear-gradient(135deg,#0066cc,#00d4ff);
    font-size:1.8rem;
}}
.avatar img {{ width:100%;height:100%;object-fit:cover; }}

.feature-pill {{
    display:inline-flex;align-items:center;gap:8px;
    background:rgba(0,212,255,0.08);
    border:1px solid {border_clr};
    border-radius:50px; padding:0.4rem 1rem;
    font-size:0.78rem; color:{text_main} !important;
    margin:4px; transition:all 0.2s;
}}
.feature-pill:hover {{
    background:rgba(0,212,255,0.18);
    border-color:{accent};
}}

.form-section {{
    background: rgba(0,212,255,0.04);
    border: 1px solid {border_clr};
    border-radius: 14px;
    padding: 1.2rem 1.4rem;
    margin-bottom: 1rem;
}}

.wa-btn {{
    display:inline-flex;align-items:center;gap:8px;
    background:linear-gradient(135deg,#25d366,#128c7e);
    color:white !important;border:none;border-radius:50px;
    padding:0.5rem 1.2rem;font-size:0.83rem;font-weight:700;
    cursor:pointer;text-decoration:none;transition:all 0.25s;
    box-shadow:0 4px 15px rgba(37,211,102,0.3);
}}
.wa-btn:hover {{ transform:translateY(-2px); box-shadow:0 8px 25px rgba(37,211,102,0.45); }}

.email-btn {{
    display:inline-flex;align-items:center;gap:8px;
    background:linear-gradient(135deg,#0066cc,#00d4ff);
    color:white !important;border:none;border-radius:50px;
    padding:0.5rem 1.2rem;font-size:0.83rem;font-weight:700;
    cursor:pointer;text-decoration:none;transition:all 0.25s;
    box-shadow:0 4px 15px rgba(0,212,255,0.3);
}}
.email-btn:hover {{ transform:translateY(-2px); box-shadow:0 8px 25px rgba(0,212,255,0.45); }}

/* Slider, checkbox, radio */
.stSlider > div {{ color: {text_main} !important; }}
.stCheckbox label {{ color: {text_main} !important; }}
[data-testid="stFileUploader"] {{
    background: {input_bg} !important;
    border: 2px dashed {border_clr} !important;
    border-radius: 12px !important;
}}
hr {{ border-color: {border_clr} !important; margin:0.8rem 0 !important; }}
</style>
""", unsafe_allow_html=True)


# ==============================
# THEME TOGGLE
# ==============================
def theme_toggle():
    icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    if st.button(icon, key="theme_btn"):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()


# =========================================================
# PAGE 1 — HOME (Welcome / Landing)
# =========================================================
def show_home_page():
    inject_css()
    is_dark = st.session_state.theme == "dark"
    accent  = "#00d4ff"
    txt     = "#e8f4f8" if is_dark else "#03045e"

    # Header row
    c_logo, c_thm = st.columns([10,1])
    with c_thm:
        theme_toggle()

    # ── HERO SECTION ──
    st.markdown(f"""
    <div style="
        min-height:420px;
        background: linear-gradient(135deg,
            {'rgba(3,10,30,0.9)' if is_dark else 'rgba(2,40,80,0.88)'},
            {'rgba(0,40,80,0.95)' if is_dark else 'rgba(0,90,150,0.92)'});
        border: 1px solid rgba(0,212,255,0.25);
        border-radius: 24px;
        padding: 60px 40px;
        text-align: center;
        position: relative;
        overflow: hidden;
        margin-bottom: 2.5rem;
        box-shadow: 0 0 100px rgba(0,212,255,0.1), inset 0 1px 0 rgba(255,255,255,0.05);
    ">
        <!-- animated glow blobs -->
        <div style="position:absolute;top:-80px;left:-80px;width:300px;height:300px;
            background:radial-gradient(circle,rgba(0,212,255,0.12),transparent 65%);
            border-radius:50%;animation:pulse 4s ease-in-out infinite;"></div>
        <div style="position:absolute;bottom:-80px;right:-80px;width:280px;height:280px;
            background:radial-gradient(circle,rgba(0,102,204,0.15),transparent 65%);
            border-radius:50%;animation:pulse 5s ease-in-out infinite 1s;"></div>

        <div style="position:relative;z-index:2;">
            <div style="font-size:4.5rem;margin-bottom:16px;filter:drop-shadow(0 0 20px rgba(0,212,255,0.5));">🎓</div>
            <h1 style="font-size:3rem;font-weight:800;color:#ffffff;margin:0 0 10px;
                letter-spacing:-1.5px;line-height:1.1;">
                EduPredict <span style="color:{accent};">AI</span>
            </h1>
            <p style="font-size:1.05rem;color:rgba(200,221,232,0.85);margin:0 0 8px;">
                Academic Intelligence · Score Prediction · Progress Analytics
            </p>
            <p style="font-size:0.82rem;color:rgba(200,221,232,0.5);margin:0 0 36px;">
                Powered by Machine Learning · Built for Students &amp; Parents
            </p>

            <!-- Feature pills -->
            <div style="display:flex;flex-wrap:wrap;justify-content:center;gap:8px;margin-bottom:36px;">
                {''.join([f'<span style="display:inline-flex;align-items:center;gap:6px;background:rgba(0,212,255,0.12);border:1px solid rgba(0,212,255,0.3);border-radius:50px;padding:6px 16px;font-size:0.78rem;color:rgba(200,221,232,0.9);">{icon} {label}</span>'
                for icon, label in [
                    ("🤖","AI Prediction"), ("📊","Live Charts"), ("💡","Smart Tips"),
                    ("📄","PDF Report"), ("📱","WhatsApp Share"), ("🔐","OTP Verified")
                ]])}
            </div>
        </div>
    </div>

    <style>
    @keyframes pulse {{
        0%,100% {{ transform:scale(1); opacity:0.6; }}
        50%      {{ transform:scale(1.1); opacity:1; }}
    }}
    </style>
    """, unsafe_allow_html=True)

    # ── STATS ROW ──
    s1,s2,s3,s4 = st.columns(4)
    for col, val, label in [
        (s1,"ML Model","Prediction Engine"),
        (s2,"3 Charts","Visual Analytics"),
        (s3,"OTP Secure","Email Verified"),
        (s4,"PDF + WA","Instant Sharing"),
    ]:
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-val" style="font-size:1.1rem;letter-spacing:0;">{val}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown('<div style="margin:2rem 0 0.5rem;"></div>', unsafe_allow_html=True)

    # ── DEMO CHART ──
    st.markdown('<div class="section-hdr">📈 Sample Performance Trend</div>', unsafe_allow_html=True)
    demo_scores = [55, 61, 65, 70, 73, 78, 83]
    attempts_d  = [f"#{i}" for i in range(1,8)]

    fig_demo = go.Figure()
    fig_demo.add_trace(go.Scatter(
        x=attempts_d, y=demo_scores, mode='lines+markers',
        name='Score',
        line=dict(color='#00d4ff', width=3),
        marker=dict(size=9, color='#00d4ff', line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(0,212,255,0.06)'
    ))
    fig_demo.add_hline(y=60, line_dash="dash", line_color="#f87171",
                       annotation_text="Pass", annotation_font_color="#f87171")
    fig_demo.add_hline(y=85, line_dash="dash", line_color="#34d399",
                       annotation_text="Excellent", annotation_font_color="#34d399")
    bg_d = "rgba(0,0,0,0)"
    tc_d = "#e8f4f8" if is_dark else "#03045e"
    gc_d = "rgba(0,212,255,0.1)" if is_dark else "rgba(0,119,182,0.1)"
    fig_demo.update_layout(
        paper_bgcolor=bg_d, plot_bgcolor=bg_d,
        font=dict(color=tc_d), height=240, margin=dict(l=0,r=0,t=10,b=0),
        showlegend=False,
        xaxis=dict(gridcolor=gc_d, color=tc_d, title="Attempt"),
        yaxis=dict(gridcolor=gc_d, color=tc_d, range=[40,100], title="Score"),
    )
    st.plotly_chart(fig_demo, use_container_width=True)

    st.markdown("---")

    # ── CTA BUTTON ──
    _, cb, _ = st.columns([1,2,1])
    with cb:
        if st.button("🚀  Get Started — Sign Up / Login", use_container_width=True, key="home_cta"):
            st.session_state.page = "auth"
            st.session_state.auth_tab = "login"
            st.rerun()

    st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1.5rem;color:rgba(100,140,160,0.5);">🔒 Secure · AI Powered · EduPredict AI v3.0</p>', unsafe_allow_html=True)


# =========================================================
# PAGE 2 — AUTH (Login + Sign-Up — separate tabs)
# =========================================================
def show_auth_page():
    inject_css()
    users = load_users()

    cb1, cb2 = st.columns([9,1])
    with cb1:
        if st.button("← Back", key="auth_back"):
            st.session_state.page = "home"; st.rerun()
    with cb2:
        theme_toggle()

    _, col, _ = st.columns([1,2.2,1])
    with col:
        st.markdown("""
        <div style="text-align:center;margin-bottom:1.8rem;">
            <div style="font-size:2.5rem;margin-bottom:8px;filter:drop-shadow(0 0 16px rgba(0,212,255,0.4));">🎓</div>
            <h2 style="margin:0;letter-spacing:-0.5px;font-size:1.6rem;">EduPredict AI</h2>
            <p style="font-size:0.75rem;color:#6b8fa3;margin:4px 0 0;">Academic Intelligence Platform</p>
        </div>
        """, unsafe_allow_html=True)

        # ── TAB SWITCHER ──
        t1, t2 = st.columns(2)
        with t1:
            if st.button("🔑  Sign In", use_container_width=True,
                         key="tab_login",
                         type="primary" if st.session_state.auth_tab == "login" else "secondary"):
                st.session_state.auth_tab = "login"; st.rerun()
        with t2:
            if st.button("📝  Sign Up", use_container_width=True,
                         key="tab_signup",
                         type="primary" if st.session_state.auth_tab == "signup" else "secondary"):
                st.session_state.auth_tab = "signup"; st.rerun()

        st.markdown("<hr>", unsafe_allow_html=True)

        # ─────────────── LOGIN ───────────────
        if st.session_state.auth_tab == "login":
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            st.markdown("**Sign In to Your Account**")
            username = st.text_input("Username", placeholder="Enter your username", key="li_user")
            password = st.text_input("Password", type="password", placeholder="Enter your password", key="li_pass")
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("Sign In  →", use_container_width=True, key="login_btn"):
                if not username or not password:
                    st.warning("Please fill all fields.")
                elif username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in  = True
                    st.session_state.username   = username
                    st.session_state.user_role  = users[username]["role"]
                    st.session_state.page       = "app"
                    h = all_history.get(username, {})
                    if isinstance(h, dict):
                        st.session_state.study_hours_history = h.get("study_hours", [])
                        st.session_state.attendance_history  = h.get("attendance", [])
                    st.rerun()
                else:
                    st.error("❌ Invalid username or password")

            st.markdown('<p style="text-align:center;font-size:0.75rem;margin-top:0.8rem;color:#6b8fa3;">New here? Switch to Sign Up tab above.</p>', unsafe_allow_html=True)

        # ─────────────── SIGN-UP ───────────────
        elif st.session_state.auth_tab == "signup":
            # Role selector
            r1, r2 = st.columns(2)
            with r1:
                if st.button("🎓  Student", use_container_width=True, key="role_stu"):
                    st.session_state.signup_role = "student"; st.rerun()
            with r2:
                if st.button("👨‍👩‍👧  Parent", use_container_width=True, key="role_par"):
                    st.session_state.signup_role = "parent"; st.rerun()

            role = st.session_state.signup_role
            st.markdown(f'<p style="text-align:center;font-size:0.75rem;color:#00d4ff;margin:6px 0 10px;">Creating: <strong>{role.capitalize()}</strong> account</p>', unsafe_allow_html=True)

            # ── Account Fields ──
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            st.markdown("**Account Details**")
            su_user  = st.text_input("Username *", placeholder="Choose a unique username", key="su_user")
            su_email = st.text_input("Email Address *", placeholder="you@example.com (for OTP)", key="su_email")
            su_pass  = st.text_input("Password *", type="password", placeholder="Min 4 characters", key="su_pass")
            su_conf  = st.text_input("Confirm Password *", type="password", placeholder="Repeat password", key="su_conf")
            su_name  = st.text_input("Full Name *", placeholder="Your full name", key="su_name")
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Role-specific Fields ──
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            if role == "student":
                st.markdown("**Academic Information**")
                su_dob    = st.date_input("Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_dob")
                su_grade  = st.selectbox("Grade / Class", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_grade")
                su_school = st.text_input("School / College Name", placeholder="Your institution name", key="su_school")
            else:
                st.markdown("**Child's Information**")
                su_child  = st.text_input("Child's Full Name", placeholder="Child's full name", key="su_child")
                su_cdob   = st.date_input("Child's Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now(), key="su_cdob")
                su_cgrade = st.selectbox("Child's Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_cgrade")
                su_rel    = st.selectbox("Your Relationship", ["Father","Mother","Guardian"], key="su_rel")
            st.markdown('</div>', unsafe_allow_html=True)

            # ── OTP Verification ──
            st.markdown('<div class="otp-panel">', unsafe_allow_html=True)
            st.markdown("**🔐 Email OTP Verification**")
            st.caption("A 6-digit code will be sent to your email to verify your account.")

            otp_col1, otp_col2 = st.columns([2,1])
            with otp_col1:
                entered_otp = st.text_input("Enter OTP", placeholder="6-digit code", key="otp_inp", max_chars=6)
            with otp_col2:
                st.markdown('<div style="margin-top:28px;"></div>', unsafe_allow_html=True)
                if st.button("📨 Send OTP", use_container_width=True, key="send_otp_btn"):
                    if not su_email:
                        st.warning("Enter your email first.")
                    else:
                        otp = generate_otp()
                        store_otp(su_email, otp)
                        ok, msg = send_otp_email(su_email, otp, su_name or "User")
                        if ok:
                            st.success(f"✅ OTP sent to {su_email}")
                            st.session_state.otp_sent = True
                        else:
                            st.warning(f"📧 Email not configured. Test OTP: **{otp}**")
                            st.caption("Set EMAIL_SENDER + EMAIL_PASSWORD to enable real email.")
                            st.session_state.otp_sent = True
            st.markdown('</div>', unsafe_allow_html=True)

            if st.button("✅  Verify OTP & Create Account", use_container_width=True, key="create_acc"):
                err = None
                if not su_user or not su_pass or not su_name or not su_email:
                    err = "Please fill all required (*) fields."
                elif su_pass != su_conf:
                    err = "Passwords don't match."
                elif len(su_pass) < 4:
                    err = "Password must be at least 4 characters."
                elif su_user in users:
                    err = "Username already taken. Choose another."
                elif not entered_otp:
                    err = "Please enter the OTP sent to your email."

                if err:
                    st.error(err)
                else:
                    ok, otp_msg = verify_otp(su_email, entered_otp)
                    if not ok:
                        st.error(otp_msg)
                    else:
                        data = {
                            "password": hash_password(su_pass),
                            "role": role, "full_name": su_name,
                            "email": su_email,
                            "created_at": str(pd.Timestamp.now())
                        }
                        if role == "student":
                            data.update({"dob": str(su_dob), "age": calculate_age(su_dob),
                                         "grade": su_grade, "school": su_school})
                        else:
                            data.update({"child_name": su_child, "child_dob": str(su_cdob),
                                         "child_age": calculate_age(su_cdob),
                                         "child_grade": su_cgrade, "relation": su_rel})
                        users[su_user] = data
                        save_users(users)
                        st.success("🎉 Account created! Please sign in.")
                        st.session_state.auth_tab = "login"
                        st.rerun()

        st.markdown('<p style="text-align:center;font-size:0.55rem;margin-top:1rem;color:rgba(100,140,160,0.4);">🔒 Secure · AI Powered · EduPredict AI</p>', unsafe_allow_html=True)


# =========================================================
# PLOTLY HELPERS
# =========================================================
def _layout(title, xt, yt, yrange=None):
    is_dark = st.session_state.theme == "dark"
    bg  = "rgba(0,0,0,0)"
    tc  = "#e8f4f8" if is_dark else "#03045e"
    gc  = "rgba(0,212,255,0.1)" if is_dark else "rgba(0,119,182,0.1)"
    d   = dict(title=dict(text=title, font=dict(color=tc,size=13)),
               paper_bgcolor=bg, plot_bgcolor=bg,
               font=dict(color=tc), height=320,
               margin=dict(l=10,r=10,t=45,b=10),
               xaxis=dict(title=xt, gridcolor=gc, color=tc, showgrid=True),
               yaxis=dict(title=yt, gridcolor=gc, color=tc, showgrid=True),
               showlegend=True, legend=dict(font=dict(color=tc)))
    if yrange:
        d["yaxis"]["range"] = yrange
    return d

def graph_score_history(scores):
    attempts = [f"#{i}" for i in range(1, len(scores)+1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=attempts, y=scores, mode='lines+markers', name='Your Score',
        line=dict(color='#00d4ff', width=3),
        marker=dict(size=9, color='#00d4ff', line=dict(color='white', width=2)),
        fill='tozeroy', fillcolor='rgba(0,212,255,0.07)'
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#f87171",
                  annotation_text="Pass (60)", annotation_font_color="#f87171")
    fig.add_hline(y=70, line_dash="dot", line_color="#fbbf24",
                  annotation_text="Good (70)", annotation_font_color="#fbbf24")
    fig.add_hline(y=85, line_dash="dash", line_color="#34d399",
                  annotation_text="Excellent (85)", annotation_font_color="#34d399")
    fig.update_layout(**_layout("📈 Score History Trend", "Attempt", "Predicted Score", [30,105]))
    return fig

def graph_hours_vs_score(hours_list, scores):
    if len(hours_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=hours_list, y=scores, mode='markers', name='Attempts',
        marker=dict(size=11, color='#00d4ff', line=dict(color='white',width=2), symbol='circle'),
        text=[f"Attempt #{i+1}<br>Hours: {h}h<br>Score: {s}"
              for i,(h,s) in enumerate(zip(hours_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    if len(hours_list) >= 3:
        z = np.polyfit(hours_list, scores, 1)
        p = np.poly1d(z)
        xl = np.linspace(min(hours_list), max(hours_list), 100)
        fig.add_trace(go.Scatter(x=xl.tolist(), y=p(xl).tolist(),
            mode='lines', name='Trend', line=dict(color='#90e0ef',width=2,dash='dash')))
    fig.update_layout(**_layout("📖 Study Hours vs Score", "Study Hours / Day", "Score", [30,105]))
    return fig

def graph_attendance_vs_score(att_list, scores):
    if len(att_list) != len(scores) or len(scores) < 2:
        return None
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=att_list, y=scores, mode='markers', name='Attempts',
        marker=dict(size=11, color='#0077b6', line=dict(color='white',width=2), symbol='diamond'),
        text=[f"Attempt #{i+1}<br>Att: {a}%<br>Score: {s}"
              for i,(a,s) in enumerate(zip(att_list, scores))],
        hovertemplate="%{text}<extra></extra>"
    ))
    if len(att_list) >= 3:
        z = np.polyfit(att_list, scores, 1)
        p = np.poly1d(z)
        xl = np.linspace(min(att_list), max(att_list), 100)
        fig.add_trace(go.Scatter(x=xl.tolist(), y=p(xl).tolist(),
            mode='lines', name='Trend', line=dict(color='#90e0ef',width=2,dash='dash')))
    fig.update_layout(**_layout("🏫 Attendance vs Score", "Attendance (%)", "Score", [30,105]))
    return fig

def graph_radar_profile(hours, attendance, previous, sleep, motivation, teacher, resources):
    """NEW — Graph 4: Student Study Profile Radar Chart"""
    is_dark = st.session_state.theme == "dark"
    tc  = "#e8f4f8" if is_dark else "#03045e"
    bg  = "rgba(0,0,0,0)"

    # Normalize all factors 0–10
    h_norm   = min(hours / 12 * 10, 10)
    att_norm = attendance / 10
    prev_norm= previous / 10
    slp_norm = min(sleep / 9 * 10, 10)
    mot_map  = {"Low":3, "Medium":6.5, "High":10}
    tch_map  = {"Poor":3, "Average":6.5, "Good":10}
    res_map  = {"Low":3, "Medium":6.5, "High":10}
    mot_norm = mot_map.get(motivation, 6)
    tch_norm = tch_map.get(teacher, 6)
    res_norm = res_map.get(resources, 6)

    categories = ["Study Hours","Attendance","Prev Score","Sleep","Motivation","Teacher","Resources"]
    values     = [h_norm, att_norm, prev_norm, slp_norm, mot_norm, tch_norm, res_norm]
    values_closed = values + [values[0]]
    cats_closed   = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed, theta=cats_closed,
        fill='toself',
        name='Your Profile',
        fillcolor='rgba(0,212,255,0.12)',
        line=dict(color='#00d4ff', width=2.5)
    ))
    # Ideal benchmark line
    ideal = [8,8,8,8,8,8,8, 8]
    fig.add_trace(go.Scatterpolar(
        r=ideal, theta=cats_closed,
        fill='toself',
        name='Ideal Target',
        fillcolor='rgba(52,211,153,0.06)',
        line=dict(color='#34d399', width=1.5, dash='dot')
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, range=[0,10], color=tc,
                            gridcolor='rgba(0,212,255,0.15)', showticklabels=False),
            angularaxis=dict(color=tc, gridcolor='rgba(0,212,255,0.15)')
        ),
        paper_bgcolor=bg, plot_bgcolor=bg,
        font=dict(color=tc, size=11),
        title=dict(text="🕸️ Study Profile Radar", font=dict(color=tc,size=13)),
        showlegend=True, legend=dict(font=dict(color=tc)),
        height=360, margin=dict(l=30,r=30,t=50,b=30)
    )
    return fig


# =========================================================
# SIDEBAR
# =========================================================
def show_sidebar(user_data):
    with st.sidebar:
        pic_b64 = get_profile_pic_base64(st.session_state.username)
        role_icon = "🎓" if st.session_state.user_role == "student" else "👨‍👩‍👧"
        avatar_html = f'<img src="data:image/jpeg;base64,{pic_b64}" />' if pic_b64 else role_icon

        st.markdown(f"""
        <div class="profile-card">
            <div class="avatar">{avatar_html}</div>
            <div class="profile-name">{user_data.get('full_name', st.session_state.username)}</div>
            <div class="profile-badge">{"Student" if st.session_state.user_role == "student" else "Parent"}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.button("✏️ Edit Photo", use_container_width=True, key="edit_pic_btn"):
            st.session_state.show_profile_edit = not st.session_state.show_profile_edit
            st.rerun()

        if st.session_state.show_profile_edit:
            up = st.file_uploader("Upload Photo", type=["jpg","jpeg","png"],
                                  key="pic_up", label_visibility="collapsed")
            if up:
                save_profile_pic(st.session_state.username, up.read())
                st.success("✅ Updated!")
                st.session_state.show_profile_edit = False
                st.rerun()

        st.markdown("---")
        st.markdown("### 👤 Account Info")
        st.markdown(f"**User:** `{st.session_state.username}`")
        st.markdown(f"**Name:** {user_data.get('full_name','N/A')}")
        st.markdown(f"**Email:** {user_data.get('email','N/A')}")
        if st.session_state.user_role == "student":
            st.markdown(f"**Age:** {user_data.get('age','N/A')}")
            st.markdown(f"**Grade:** {user_data.get('grade','N/A')}")
            st.markdown(f"**School:** {user_data.get('school','N/A')}")
        else:
            st.markdown(f"**Child:** {user_data.get('child_name','N/A')}")
            st.markdown(f"**Grade:** {user_data.get('child_grade','N/A')}")
            st.markdown(f"**Relation:** {user_data.get('relation','N/A')}")

        st.markdown("---")
        theme_toggle()
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True, key="signout_btn"):
            for k,v in defaults.items():
                st.session_state[k] = v
            st.rerun()


# =========================================================
# LOAD MODEL
# =========================================================
@st.cache_resource
def load_models():
    model   = joblib.load("student_model.pkl")
    columns = joblib.load("model_columns.pkl")
    return model, columns


# =========================================================
# PAGE 3 — MAIN APP
# =========================================================
def show_main_app():
    inject_css()
    users     = load_users()
    user_data = users.get(st.session_state.username, {})
    show_sidebar(user_data)

    st.markdown("<h1 style='text-align:center;letter-spacing:-1.5px;font-size:2.2rem;'>🎓 EduPredict <span style='color:#00d4ff;'>AI</span></h1>", unsafe_allow_html=True)
    st.markdown('<p style="text-align:center;color:#6b8fa3;font-size:0.8rem;margin-top:-8px;">Academic Score Prediction & Analytics</p>', unsafe_allow_html=True)

    if st.session_state.user_role == "parent":
        child = user_data.get("child_name","Child")
        st.info(f"👨‍👩‍👧 Predicting for: **{child}**")

    model, columns = load_models()

    # ─── INPUT FORM ───
    st.markdown('<div class="section-hdr">📋 Input Parameters</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("**📚 Academic Factors**")
        hours      = st.number_input("📖 Study Hours / Day", 0.0, 24.0, 5.0, 0.5)
        attendance = st.number_input("🏫 Attendance (%)",    0.0, 100.0, 75.0, 5.0)
        previous   = st.number_input("📊 Previous Score",    0.0, 100.0, 60.0, 5.0)
        sleep      = st.number_input("💤 Sleep Hours / Night", 0.0, 12.0, 7.0, 0.5)
        motivation = st.selectbox("🔥 Motivation Level",    ["Low","Medium","High"])
        teacher    = st.selectbox("👩‍🏫 Teacher Quality",    ["Poor","Average","Good"])
        school_t   = st.selectbox("🏛️ School Type",         ["Public","Private"])
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="form-section">', unsafe_allow_html=True)
        st.markdown("**🌐 Social & Environmental Factors**")
        internet   = st.selectbox("🌐 Internet Access",          ["Yes","No"])
        income     = st.selectbox("💰 Family Income",            ["Low","Medium","High"])
        parent_inv = st.selectbox("👨‍👩‍👦 Parental Involvement",  ["Low","Medium","High"])
        education  = st.selectbox("🎓 Parent Education",         ["School","College"])
        peer       = st.selectbox("👥 Peer Influence",           ["Negative","Neutral","Positive"])
        resources  = st.selectbox("📚 Learning Resources",       ["Low","Medium","High"])
        activities = st.selectbox("⚽ Extracurricular",           ["Yes","No"])
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("")
    if st.button("🚀  Predict My Score", use_container_width=True, key="predict_btn"):
        data = {
            "Hours_Studied": hours, "Attendance": attendance,
            "Previous_Scores": previous, "Sleep_Hours": sleep,
            "Motivation_Level": motivation, "Teacher_Quality": teacher,
            "School_Type": school_t, "Internet_Access": internet,
            "Family_Income": income, "Parental_Involvement": parent_inv,
            "Parental_Education_Level": education, "Peer_Influence": peer,
            "Learning_Resources": resources, "Extracurricular_Activities": activities
        }
        input_df = pd.DataFrame([data])
        input_df = pd.get_dummies(input_df)
        input_df = input_df.reindex(columns=columns, fill_value=0)
        prediction = model.predict(input_df)
        final_score = max(40, min(100, int(round(prediction[0]))))

        uname = st.session_state.username
        if uname not in all_history:
            all_history[uname] = {"scores":[], "study_hours":[], "attendance":[]}
        if isinstance(all_history[uname], list):
            all_history[uname] = {"scores": all_history[uname], "study_hours":[], "attendance":[]}

        all_history[uname]["scores"].append(final_score)
        all_history[uname]["study_hours"].append(float(hours))
        all_history[uname]["attendance"].append(float(attendance))
        for key in ["scores","study_hours","attendance"]:
            if len(all_history[uname][key]) > 15:
                all_history[uname][key] = all_history[uname][key][-15:]
        save_history(all_history)
        st.session_state.study_hours_history = all_history[uname]["study_hours"]
        st.session_state.attendance_history  = all_history[uname]["attendance"]

        recs = []
        if hours < 6:          recs.append("Increase study hours to 6–8 daily for better results")
        if attendance < 75:    recs.append("Improve attendance to at least 80%")
        if sleep < 7:          recs.append("Get 7–9 hours of quality sleep daily")
        if motivation == "Low":recs.append("Set clear daily goals to boost motivation")
        if teacher == "Poor":  recs.append("Seek tutoring or online resources (Khan Academy)")
        if resources == "Low": recs.append("Utilise free platforms — Khan Academy, YouTube, NCERT")
        if peer == "Negative": recs.append("Join positive study groups or study with top performers")

        st.session_state.last_score  = final_score
        st.session_state.last_recs   = recs
        st.session_state.last_inputs = {"hours":hours, "attendance":attendance,
                                        "previous":previous, "sleep":sleep,
                                        "motivation":motivation, "teacher":teacher,
                                        "resources":resources}
        pdf_buf = generate_pdf_report(st.session_state.username, final_score, user_data,
                                      hours, attendance, previous, sleep, recs)
        st.session_state.last_pdf = pdf_buf.read()

        # RESULT CARD
        st.markdown(f"""
        <div class="result-card">
            <div class="result-label">Predicted Exam Score</div>
            <div class="result-score">{final_score}<span style="font-size:1.2rem;opacity:0.5;"> / 100</span></div>
        </div>
        """, unsafe_allow_html=True)

        if final_score >= 85:
            st.success("🌟 Outstanding! Exceptional performance!"); st.balloons()
        elif final_score >= 70:
            st.success("📈 Great performance! Keep it up!")
        elif final_score >= 55:
            st.info("📚 Satisfactory — room for improvement")
        else:
            st.warning("⚠️ Needs improvement — review recommendations below")

    # ─── HISTORY DATA ───
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

    # ─── DOWNLOAD & SHARE ───
    if st.session_state.last_score is not None:
        inp         = st.session_state.last_inputs
        final_score = st.session_state.last_score
        fname       = f"EduPredict_Report_{uname}_{datetime.now().strftime('%Y%m%d')}.pdf"

        st.markdown('<div class="section-hdr">📤 Download & Share Report</div>', unsafe_allow_html=True)
        st.markdown('<div class="share-panel">', unsafe_allow_html=True)

        dc1, dc2 = st.columns(2)
        with dc1:
            if st.session_state.last_pdf:
                st.download_button(
                    "📄 Download PDF Report",
                    data=st.session_state.last_pdf,
                    file_name=fname, mime="application/pdf",
                    use_container_width=True
                )
        with dc2:
            share_txt = (
                f"🎓 My Predicted Score: {final_score}/100\n"
                f"📖 Study Hours: {inp.get('hours','N/A')}\n"
                f"🏫 Attendance: {inp.get('attendance','N/A')}%\n"
                f"📊 Previous Score: {inp.get('previous','N/A')}\n"
                f"Generated by EduPredict AI"
            )
            st.download_button(
                "📋 Download Score Summary (TXT)",
                data=share_txt,
                file_name=f"score_{uname}.txt", mime="text/plain",
                use_container_width=True
            )

        # WhatsApp share — opens file picker then share
        wa_text  = f"🎓 My Predicted Exam Score: {final_score}/100! Check my full report via EduPredict AI."
        wa_url   = f"https://wa.me/?text={wa_text.replace(' ','%20')}"
        mail_url = f"mailto:?subject=My%20Predicted%20Score%20%7C%20EduPredict%20AI&body={share_txt.replace(chr(10),'%0A')}"

        st.markdown(f"""
        <div style="display:flex;flex-wrap:wrap;gap:10px;margin-top:12px;align-items:center;">
            <a href="{wa_url}" target="_blank" class="wa-btn">
                📱 Share on WhatsApp
            </a>
            <a href="{mail_url}" class="email-btn">
                📧 Share via Email
            </a>
            <span style="font-size:0.72rem;color:#6b8fa3;margin-left:4px;">
                💡 Tip: Download PDF first, then attach it in WhatsApp manually for document share.
            </span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

    # ─── PERFORMANCE OVERVIEW ───
    if len(scores_list) >= 1:
        st.markdown('<div class="section-hdr">📊 Performance Overview</div>', unsafe_allow_html=True)
        passing   = len([s for s in scores_list if s >= 60])
        needs_imp = len([s for s in scores_list if s < 60])
        avg_score = int(np.mean(scores_list))
        pass_pct  = (passing / len(scores_list)) * 100
        best      = max(scores_list)
        last_s    = scores_list[-1]

        cols5 = st.columns(5)
        stats = [(cols5[0],last_s,"Last Score",False),(cols5[1],avg_score,"Average",False),
                 (cols5[2],best,"Best Score",False),(cols5[3],passing,"Passed",False),
                 (cols5[4],needs_imp,"Need Improve",True)]
        for col,val,label,red in stats:
            cls = "metric-val-r" if red else "metric-val"
            with col:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="{cls}">{val}</div>
                    <div class="metric-label">{label}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("")
        st.progress(pass_pct/100)
        st.caption(f"✅ Success Rate: {pass_pct:.0f}%  ({passing}/{len(scores_list)} attempts passed)")

        if len(scores_list) >= 2:
            trend = scores_list[-1] - scores_list[-2]
            if trend > 0:   st.success(f"📈 Improving! +{trend} pts from last attempt")
            elif trend < 0: st.warning(f"📉 Declined by {abs(trend)} pts. Review recommendations!")
            else:           st.info("➡️ Same as last attempt. Aim higher!")

    # ─── GRAPH 1 — Score History ───
    if len(scores_list) >= 1:
        st.markdown('<div class="section-hdr">📈 Graph 1 — Score History Trend</div>', unsafe_allow_html=True)
        st.caption("Your predicted score across all attempts with benchmark lines.")
        st.plotly_chart(graph_score_history(scores_list), use_container_width=True)

    # ─── GRAPH 2 — Hours vs Score ───
    if len(hours_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-hdr">📖 Graph 2 — Study Hours vs Score</div>', unsafe_allow_html=True)
        st.caption("Does studying more hours lead to higher scores? Trend line included.")
        f2 = graph_hours_vs_score(hours_list[:len(scores_list)], scores_list)
        if f2: st.plotly_chart(f2, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-hdr">📖 Graph 2 — Study Hours vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Appears after 2+ predictions")

    # ─── GRAPH 3 — Attendance vs Score ───
    if len(att_list) >= 2 and len(scores_list) >= 2:
        st.markdown('<div class="section-hdr">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.caption("How attendance % correlates with your predicted score.")
        f3 = graph_attendance_vs_score(att_list[:len(scores_list)], scores_list)
        if f3: st.plotly_chart(f3, use_container_width=True)
    elif len(scores_list) >= 1:
        st.markdown('<div class="section-hdr">🏫 Graph 3 — Attendance vs Score</div>', unsafe_allow_html=True)
        st.info("📊 Appears after 2+ predictions")

    # ─── GRAPH 4 — Radar Chart (NEW) ───
    if st.session_state.last_inputs:
        st.markdown('<div class="section-hdr">🕸️ Graph 4 — Study Profile Radar</div>', unsafe_allow_html=True)
        st.caption("Your current study habits vs ideal benchmark — see which area needs improvement.")
        inp = st.session_state.last_inputs
        f4 = graph_radar_profile(
            inp.get("hours",5), inp.get("attendance",75),
            inp.get("previous",60), inp.get("sleep",7),
            inp.get("motivation","Medium"), inp.get("teacher","Average"),
            inp.get("resources","Medium")
        )
        st.plotly_chart(f4, use_container_width=True)

    # ─── RECOMMENDATIONS ───
    if st.session_state.last_recs is not None:
        recs = st.session_state.last_recs
        if recs:
            st.markdown('<div class="section-hdr">💡 Personalised Recommendations</div>', unsafe_allow_html=True)
            for r in recs:
                st.info(f"→  {r}")
        elif st.session_state.last_score:
            st.success("✅ Great habits! Maintain your current routine.")

    st.markdown("---")
    st.caption("🎓 EduPredict AI v3.0 · Academic Intelligence Platform · Built with ❤️")


# =========================================================
# MAIN ROUTER
# =========================================================
if st.session_state.logged_in:
    st.session_state.page = "app"

if st.session_state.page == "app":
    show_main_app()
elif st.session_state.page == "auth":
    show_auth_page()
else:
    show_home_page()
