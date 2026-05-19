import streamlit as st
import pandas as pd
import numpy as np
import joblib
import json
import os
import io
import base64
import hashlib
import random
import smtplib
import requests
from datetime import datetime, timedelta
from urllib.parse import quote
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

import plotly.graph_objects as go

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(
    page_title="Student Score Predictor",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# FILES
# =========================================================
USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"
OTP_FILE = "otp_store.json"
PROFILE_DIR = "profile_pics"

os.makedirs(PROFILE_DIR, exist_ok=True)

# =========================================================
# EMAIL CONFIG
# =========================================================
# Gmail App Password use karo, normal Gmail password nahi.
# Google Account > Security > 2-Step Verification > App passwords
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_16_digit_gmail_app_password"

# =========================================================
# WHATSAPP CLOUD API CONFIG
# =========================================================
# Direct PDF document WhatsApp par bhejne ke liye Meta WhatsApp Cloud API zaroori hai.
# Browser WhatsApp wa.me link local PDF auto attach nahi kar sakta.
WHATSAPP_TOKEN = "your_whatsapp_cloud_api_token"
WHATSAPP_PHONE_NUMBER_ID = "your_phone_number_id"

# =========================================================
# BACKGROUND IMAGE
# =========================================================
# Apni image lagani ho to internet image URL ya local file ka base64 use kar sakti ho.
WELCOME_BG_URL = "https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=1600&q=80"

# =========================================================
# HELPERS
# =========================================================
def load_json(path, default):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_otp():
    return str(random.randint(100000, 999999))

def clean_phone(phone):
    return phone.strip().replace("+", "").replace(" ", "").replace("-", "")

def calculate_age(dob):
    today = datetime.now().date()
    age = today.year - dob.year
    if (today.month, today.day) < (dob.month, dob.day):
        age -= 1
    return age

def save_profile_picture(username, file_bytes):
    path = os.path.join(PROFILE_DIR, f"{username}.jpg")
    with open(path, "wb") as f:
        f.write(file_bytes)

def get_profile_picture(username):
    path = os.path.join(PROFILE_DIR, f"{username}.jpg")
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def store_otp(email, otp):
    data = load_json(OTP_FILE, {})
    data[email] = {
        "otp": otp,
        "created_at": datetime.now().isoformat()
    }
    save_json(OTP_FILE, data)

def verify_otp(email, otp):
    data = load_json(OTP_FILE, {})
    if email not in data:
        return False, "OTP not found. Please send OTP again."
    record = data[email]
    created = datetime.fromisoformat(record["created_at"])
    if datetime.now() - created > timedelta(minutes=10):
        return False, "OTP expired. Please send a new OTP."
    if str(record["otp"]) != str(otp).strip():
        return False, "Invalid OTP. Please check again."
    return True, "OTP verified successfully."

# =========================================================
# EMAIL FUNCTIONS
# =========================================================
def is_email_configured():
    return (
        EMAIL_SENDER
        and EMAIL_PASSWORD
        and "your_email" not in EMAIL_SENDER
        and "your_16_digit" not in EMAIL_PASSWORD
        and "your_app_password" not in EMAIL_PASSWORD
    )

def send_otp_email(receiver_email, otp, name="User"):
    if not is_email_configured():
        return False, "Email not configured. For testing, OTP is shown in app."

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Your OTP - Student Score Predictor"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver_email

        html = f"""
        <div style="font-family:Arial;background:#000814;color:#ffffff;padding:30px;">
            <div style="max-width:500px;margin:auto;background:#03045e;padding:25px;border-radius:18px;border:1px solid #00b4d8;">
                <h2 style="color:#90e0ef;text-align:center;">Student Score Predictor</h2>
                <p>Hello <b>{name}</b>,</p>
                <p>Your verification OTP is:</p>
                <div style="font-size:32px;letter-spacing:10px;font-weight:bold;text-align:center;color:#00b4d8;padding:15px;">
                    {otp}
                </div>
                <p style="font-size:13px;color:#caf0f8;">This OTP is valid for 10 minutes.</p>
            </div>
        </div>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())

        return True, "OTP sent to your email."
    except Exception as e:
        return False, f"Email error: {e}"

def send_pdf_email(receiver_email, subject, body, pdf_bytes, filename):
    if not is_email_configured():
        return False, "Email sender is not configured. Add Gmail and App Password in app.py."

    try:
        msg = MIMEMultipart()
        msg["Subject"] = subject
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver_email
        msg.attach(MIMEText(body, "plain"))

        part = MIMEBase("application", "pdf")
        part.set_payload(pdf_bytes)
        encoders.encode_base64(part)
        part.add_header("Content-Disposition", f'attachment; filename="{filename}"')
        msg.attach(part)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())

        return True, "PDF report sent by email successfully."
    except Exception as e:
        return False, f"Email sending error: {e}"

# =========================================================
# WHATSAPP FUNCTIONS
# =========================================================
def is_whatsapp_configured():
    return (
        WHATSAPP_TOKEN
        and WHATSAPP_PHONE_NUMBER_ID
        and "your_whatsapp" not in WHATSAPP_TOKEN
        and "your_phone_number" not in WHATSAPP_PHONE_NUMBER_ID
    )

def send_pdf_whatsapp(receiver_phone, caption, pdf_bytes, filename):
    if not is_whatsapp_configured():
        return False, "WhatsApp Cloud API is not configured. Download PDF and use manual WhatsApp button."

    try:
        phone = clean_phone(receiver_phone)
        if len(phone) < 10:
            return False, "Enter phone number with country code. Example: 919876543210"

        upload_url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/media"
        headers = {"Authorization": f"Bearer {WHATSAPP_TOKEN}"}
        files = {"file": (filename, pdf_bytes, "application/pdf")}
        data = {"messaging_product": "whatsapp", "type": "application/pdf"}

        upload_res = requests.post(upload_url, headers=headers, files=files, data=data, timeout=30)
        if upload_res.status_code not in [200, 201]:
            return False, f"WhatsApp upload failed: {upload_res.text}"

        media_id = upload_res.json().get("id")
        if not media_id:
            return False, "WhatsApp media id not received."

        send_url = f"https://graph.facebook.com/v20.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "document",
            "document": {
                "id": media_id,
                "filename": filename,
                "caption": caption
            }
        }

        send_res = requests.post(
            send_url,
            headers={**headers, "Content-Type": "application/json"},
            json=payload,
            timeout=30
        )

        if send_res.status_code not in [200, 201]:
            return False, f"WhatsApp document send failed: {send_res.text}"

        return True, "PDF document sent on WhatsApp successfully."
    except Exception as e:
        return False, f"WhatsApp error: {e}"

# =========================================================
# MODEL LOADING
# =========================================================
@st.cache_resource
def load_model_files():
    try:
        model = joblib.load("student_model.pkl")
        columns = joblib.load("model_columns.pkl")
        return model, columns, None
    except Exception as e:
        return None, None, str(e)

def fallback_prediction(data):
    score = 0
    score += data["Hours_Studied"] * 5.2
    score += data["Attendance"] * 0.22
    score += data["Previous_Scores"] * 0.35
    score += data["Sleep_Hours"] * 1.2
    if data["Motivation_Level"] == "High":
        score += 7
    elif data["Motivation_Level"] == "Medium":
        score += 3
    if data["Internet_Access"] == "Yes":
        score += 3
    if data["Learning_Resources"] == "High":
        score += 4
    if data["Teacher_Quality"] == "Good":
        score += 4
    if data["Peer_Influence"] == "Positive":
        score += 3
    return int(max(35, min(100, round(score))))

# =========================================================
# PDF REPORT
# =========================================================
def make_pdf_report(username, user_data, result):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.55 * inch,
        leftMargin=0.55 * inch,
        topMargin=0.45 * inch,
        bottomMargin=0.45 * inch
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "TitleCustom",
        parent=styles["Title"],
        fontSize=22,
        textColor=colors.HexColor("#023e8a"),
        alignment=1,
        spaceAfter=16
    )
    heading = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor("#0077b6"),
        spaceBefore=10,
        spaceAfter=8
    )
    normal = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    story = []
    story.append(Paragraph("Student Score Predictor - Professional Report", title))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y, %I:%M %p')}", normal))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Student / User Information", heading))
    info_data = [
        ["Name", user_data.get("full_name", username)],
        ["Username", username],
        ["Role", user_data.get("role", "student").capitalize()],
        ["Email", user_data.get("email", "N/A")]
    ]
    if user_data.get("role") == "parent":
        info_data.extend([
            ["Child Name", user_data.get("child_name", "N/A")],
            ["Child Grade", user_data.get("child_grade", "N/A")]
        ])
    else:
        info_data.extend([
            ["Grade", user_data.get("grade", "N/A")],
            ["School / College", user_data.get("school", "N/A")]
        ])

    story.append(make_table(info_data, [2.2 * inch, 4.5 * inch]))

    story.append(Paragraph("Prediction Result", heading))
    score = result["score"]
    status = "Excellent" if score >= 85 else "Good" if score >= 70 else "Satisfactory" if score >= 55 else "Needs Improvement"
    result_data = [
        ["Predicted Exam Score", f"{score}/100"],
        ["Performance Status", status]
    ]
    story.append(make_table(result_data, [2.4 * inch, 4.3 * inch], header=False))

    story.append(Paragraph("Input Summary", heading))
    input_data = [["Parameter", "Value"]]
    for k, v in result["inputs"].items():
        input_data.append([k.replace("_", " "), str(v)])
    story.append(make_table(input_data, [3.0 * inch, 3.7 * inch], header=True))

    story.append(Paragraph("Recommendations", heading))
    recs = result.get("recommendations", [])
    if recs:
        for rec in recs:
            story.append(Paragraph(f"• {rec}", normal))
    else:
        story.append(Paragraph("Your current inputs look strong. Maintain consistency and keep tracking progress.", normal))

    story.append(Spacer(1, 16))
    story.append(Paragraph(
        "Note: This report is generated for academic guidance. Final performance depends on preparation quality, exam difficulty, and consistency.",
        ParagraphStyle("Footer", parent=normal, fontSize=8, textColor=colors.grey, alignment=1)
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()

def make_table(data, widths, header=False):
    table = Table(data, colWidths=widths)
    style = [
        ("GRID", (0, 0), (-1, -1), 0.7, colors.HexColor("#90e0ef")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#f1fbff")),
        ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#03045e")),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
    ]
    if header:
        style.extend([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0077b6")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ])
    table.setStyle(TableStyle(style))
    return table

# =========================================================
# THEME CSS
# =========================================================
def apply_theme():
    mode = st.session_state.get("theme", "dark")
    dark = mode == "dark"

    bg = "radial-gradient(circle at top left,#03045e 0%,#000814 45%,#00040a 100%)" if dark else "linear-gradient(135deg,#caf0f8 0%,#ffffff 50%,#e0fbff 100%)"
    card = "rgba(3,4,94,0.54)" if dark else "rgba(255,255,255,0.86)"
    text = "#ffffff" if dark else "#03045e"
    muted = "#caf0f8" if dark else "#075985"
    sidebar = "linear-gradient(180deg,#03045e,#000814)" if dark else "linear-gradient(180deg,#ffffff,#caf0f8)"
    border = "rgba(0,180,216,0.32)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500;700&display=swap');

    * {{ font-family:'DM Sans',sans-serif; }}
    h1,h2,h3,h4 {{ font-family:'Syne',sans-serif !important; }}

    .stApp {{
        background:{bg};
        color:{text};
    }}

    .main .block-container {{
        padding-top:1.3rem;
        padding-bottom:2rem;
    }}

    [data-testid="stSidebar"] {{
        background:{sidebar};
        border-right:1px solid {border};
    }}

    .stApp, .stApp p, .stApp label, .stApp span, .stApp div {{
        color:{text} !important;
    }}

    [data-testid="stSidebar"] * {{
        color:{text} !important;
    }}

    .app-card {{
        background:{card};
        border:1px solid {border};
        border-radius:24px;
        padding:1.3rem;
        box-shadow:0 14px 45px rgba(0,0,0,0.16);
        backdrop-filter:blur(14px);
        margin-bottom:1rem;
    }}

    .hero {{
        min-height:73vh;
        border-radius:30px;
        display:flex;
        align-items:center;
        padding:3rem;
        overflow:hidden;
        position:relative;
        background:
            linear-gradient(90deg,rgba(0,8,20,0.92),rgba(3,4,94,0.72),rgba(0,119,182,0.20)),
            url('{WELCOME_BG_URL}');
        background-size:cover;
        background-position:center;
        border:1px solid rgba(0,180,216,0.35);
        box-shadow:0 18px 70px rgba(0,0,0,0.28);
    }}

    .hero h1 {{
        font-size:3.2rem !important;
        line-height:1.02;
        color:#ffffff !important;
        margin-bottom:0.6rem;
    }}

    .hero p {{
        color:#caf0f8 !important;
        font-size:1.05rem;
        max-width:640px;
    }}

    .mini-feature {{
        background:rgba(255,255,255,0.10);
        border:1px solid rgba(144,224,239,0.35);
        border-radius:18px;
        padding:1rem;
        height:100%;
    }}

    .mini-feature b {{
        color:#90e0ef !important;
    }}

    .metric-card {{
        background:{card};
        border:1px solid {border};
        border-radius:20px;
        padding:1rem;
        text-align:center;
    }}

    .metric-value {{
        font-family:'Syne',sans-serif;
        font-size:2rem;
        font-weight:800;
        color:#00b4d8 !important;
    }}

    .metric-label {{
        color:{muted} !important;
        font-size:0.78rem;
    }}

    .result-box {{
        background:linear-gradient(135deg,#03045e,#0077b6);
        border:2px solid #00b4d8;
        border-radius:26px;
        padding:2rem;
        text-align:center;
        box-shadow:0 14px 50px rgba(0,180,216,0.22);
    }}

    .result-score {{
        color:#caf0f8 !important;
        font-size:4rem;
        font-weight:900;
        font-family:'Syne',sans-serif;
    }}

    .section-title {{
        font-family:'Syne',sans-serif;
        font-weight:800;
        color:#90e0ef !important;
        font-size:1.25rem;
        margin:0.5rem 0 1rem;
    }}

    .nav-pill {{
        background:rgba(0,180,216,0.10);
        border:1px solid rgba(0,180,216,0.28);
        border-radius:16px;
        padding:0.75rem;
        margin-bottom:0.6rem;
    }}

    .profile-name {{
        font-family:'Syne',sans-serif;
        font-weight:800;
        color:{text} !important;
        font-size:1.05rem;
    }}

    .profile-role {{
        display:inline-block;
        padding:0.2rem 0.7rem;
        border-radius:999px;
        background:rgba(0,180,216,0.16);
        border:1px solid rgba(0,180,216,0.45);
        font-size:0.72rem;
    }}

    .avatar {{
        width:82px;
        height:82px;
        border-radius:50%;
        background:linear-gradient(135deg,#0077b6,#00b4d8);
        border:3px solid #00b4d8;
        display:flex;
        align-items:center;
        justify-content:center;
        overflow:hidden;
        margin:auto;
        font-size:2.1rem;
    }}

    .avatar img {{
        width:100%;
        height:100%;
        object-fit:cover;
    }}

    .stTextInput input, .stNumberInput input, .stDateInput input, .stTextArea textarea {{
        background:{'rgba(0,20,60,0.75)' if dark else 'rgba(255,255,255,0.92)'} !important;
        color:{text} !important;
        border:1px solid rgba(0,180,216,0.42) !important;
        border-radius:14px !important;
    }}

    div[data-baseweb="select"] > div {{
        background:{'rgba(0,20,60,0.75)' if dark else 'rgba(255,255,255,0.92)'} !important;
        color:{text} !important;
        border:1px solid rgba(0,180,216,0.42) !important;
        border-radius:14px !important;
    }}

    div[data-baseweb="select"] span {{
        color:{text} !important;
    }}

    div[data-baseweb="popover"] div {{
        background:{'#001a35' if dark else '#ffffff'} !important;
        color:{text} !important;
    }}

    li[role="option"] {{
        color:{text} !important;
    }}

    .stButton > button, [data-testid="stDownloadButton"] button {{
        cursor:pointer !important;
        border-radius:999px !important;
        border:none !important;
        font-weight:900 !important;
        letter-spacing:0.2px !important;
        background:linear-gradient(135deg,#0077b6,#00b4d8) !important;
        color:white !important;
        transition:all 0.28s cubic-bezier(.2,.8,.2,1) !important;
        box-shadow:0 8px 24px rgba(0,119,182,0.25);
        min-height:2.75rem !important;
    }}

    .stButton > button:hover, [data-testid="stDownloadButton"] button:hover {{
        transform:translateY(-3px) scale(1.015);
        background:linear-gradient(135deg,#00b4d8,#90e0ef) !important;
        color:#03045e !important;
        box-shadow:0 16px 42px rgba(0,180,216,0.48);
    }}

    .stButton > button:active, [data-testid="stDownloadButton"] button:active {{
        transform:translateY(-1px) scale(0.99);
    }}

    .detail-grid {{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(220px,1fr));
        gap:0.85rem;
    }}

    .detail-item {{
        background:rgba(0,180,216,0.09);
        border:1px solid rgba(0,180,216,0.28);
        border-radius:18px;
        padding:0.85rem 1rem;
    }}

    .detail-label {{
        font-size:0.72rem;
        opacity:0.76;
        margin-bottom:0.22rem;
        text-transform:uppercase;
        letter-spacing:0.7px;
    }}

    .detail-value {{
        font-size:1rem;
        font-weight:800;
        color:{'#ffffff' if dark else '#03045e'} !important;
    }}

    button, a, label {{
        cursor:pointer !important;
    }}

    [data-testid="stFileUploader"] {{
        background:rgba(0,180,216,0.08) !important;
        border:2px dashed rgba(0,180,216,0.35) !important;
        border-radius:18px !important;
        padding:0.8rem !important;
    }}

    .success-note {{
        background:rgba(16,185,129,0.12);
        border:1px solid rgba(16,185,129,0.35);
        border-radius:16px;
        padding:0.9rem;
    }}

    .warn-note {{
        background:rgba(251,191,36,0.12);
        border:1px solid rgba(251,191,36,0.35);
        border-radius:16px;
        padding:0.9rem;
    }}

    hr {{
        border-color:rgba(0,180,216,0.20) !important;
    }}
    </style>
    """, unsafe_allow_html=True)

def init_state():
    defaults = {
        "logged_in": False,
        "username": "",
        "theme": "dark",
        "auth_page": "welcome",
        "page": "Dashboard",
        "last_result": None,
        "last_pdf": None,
        "show_profile_upload": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def theme_button():
    label = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(label, use_container_width=True):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()

# =========================================================
# WELCOME PAGE
# =========================================================
def welcome_page():
    apply_theme()

    top1, top2 = st.columns([8, 1])
    with top2:
        theme_button()

    st.markdown("""
    <div class="hero">
        <div>
            <div style="font-size:3rem;margin-bottom:0.4rem;">🎓</div>
            <h1>Student Score<br>Predictor</h1>
            <p>Professional academic prediction web app with secure login, PDF reports, email sharing and WhatsApp document sharing.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    c1, c2, c3, c4 = st.columns(4)
    features = [
        ("AI Prediction", "Score prediction from academic inputs."),
        ("Multi Page App", "Dashboard, prediction, report and history."),
        ("PDF Report", "Printable professional document."),
        ("Share Report", "Send as email or WhatsApp document.")
    ]
    for col, (t, d) in zip([c1, c2, c3, c4], features):
        with col:
            st.markdown(f"""
            <div class="mini-feature">
                <b>{t}</b><br>
                <span style="font-size:0.84rem;color:#caf0f8 !important;">{d}</span>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    a, b, c = st.columns([1, 2, 1])
    with b:
        if st.button("Get Started", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()

# =========================================================
# AUTH PAGE
# =========================================================
def auth_page():
    apply_theme()

    users = load_json(USER_DB_FILE, {})

    col_back, col_theme = st.columns([8, 1])
    with col_back:
        if st.button("← Back to Welcome"):
            st.session_state.auth_page = "welcome"
            st.rerun()
    with col_theme:
        theme_button()

    st.write("")
    left, mid, right = st.columns([1, 1.25, 1])
    with mid:
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.markdown("<h2 style='text-align:center;'>🎓 Student Score Predictor</h2>", unsafe_allow_html=True)

        tab1, tab2 = st.tabs(["Login", "Sign Up"])

        with tab1:
            st.markdown('<div class="section-title">Sign In</div>', unsafe_allow_html=True)
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")

            if st.button("Login", use_container_width=True):
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.page = "Dashboard"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with tab2:
            st.markdown('<div class="section-title">Create Account</div>', unsafe_allow_html=True)
            role = st.selectbox("Role", ["student", "parent"], format_func=lambda x: x.capitalize())
            full_name = st.text_input("Full Name", key="signup_name")
            username = st.text_input("Username", key="signup_username")
            email = st.text_input("Email for OTP", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            confirm = st.text_input("Confirm Password", type="password", key="signup_confirm")

            if role == "student":
                dob = st.date_input("Date of Birth", min_value=datetime(1990, 1, 1), max_value=datetime.now())
                grade = st.selectbox("Grade", ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"])
                school = st.text_input("School / College")
            else:
                child_name = st.text_input("Child Name")
                child_grade = st.selectbox("Child Grade", ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"])
                relation = st.selectbox("Relationship", ["Father", "Mother", "Guardian"])

            st.markdown("---")
            st.markdown("**Email Verification**")
            otp_col1, otp_col2 = st.columns([1, 1])
            with otp_col1:
                if st.button("Send OTP", use_container_width=True):
                    if not email:
                        st.warning("Enter email first.")
                    else:
                        otp = generate_otp()
                        store_otp(email, otp)
                        ok, msg = send_otp_email(email, otp, full_name or "User")
                        if ok:
                            st.success(msg)
                        else:
                            st.warning(msg)
                            st.info(f"Testing OTP: {otp}")

            otp_input = st.text_input("Enter OTP", max_chars=6)

            with otp_col2:
                create = st.button("Create Account", use_container_width=True)

            if create:
                if not full_name or not username or not email or not password:
                    st.warning("Please fill all required fields.")
                elif username in users:
                    st.error("Username already exists.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 4:
                    st.error("Password must be at least 4 characters.")
                else:
                    verified, msg = verify_otp(email, otp_input)
                    if not verified:
                        st.error(msg)
                    else:
                        user = {
                            "full_name": full_name,
                            "username": username,
                            "email": email,
                            "password": hash_password(password),
                            "role": role,
                            "created_at": datetime.now().isoformat()
                        }
                        if role == "student":
                            user.update({
                                "dob": str(dob),
                                "age": calculate_age(dob),
                                "grade": grade,
                                "school": school
                            })
                        else:
                            user.update({
                                "child_name": child_name,
                                "child_grade": child_grade,
                                "relation": relation
                            })
                        users[username] = user
                        save_json(USER_DB_FILE, users)
                        st.success("Account created successfully. Please login now.")

        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SIDEBAR
# =========================================================
def sidebar(user):
    with st.sidebar:
        pic = get_profile_picture(st.session_state.username)
        avatar = f'<img src="data:image/jpeg;base64,{pic}">' if pic else "🎓"

        st.markdown(f"""
        <div style="text-align:center;margin-top:0.5rem;">
            <div class="avatar">{avatar}</div>
            <div class="profile-name">{user.get('full_name', st.session_state.username)}</div>
            <div class="profile-role">{user.get('role','student').capitalize()}</div>
        </div>
        """, unsafe_allow_html=True)

        st.write("")
        if st.button("Change Photo", use_container_width=True):
            st.session_state.show_profile_upload = not st.session_state.show_profile_upload
            st.rerun()

        if st.session_state.show_profile_upload:
            upload = st.file_uploader("Upload profile photo", type=["jpg", "jpeg", "png"])
            if upload:
                save_profile_picture(st.session_state.username, upload.read())
                st.session_state.show_profile_upload = False
                st.success("Profile photo updated.")
                st.rerun()

        st.markdown("---")
        st.markdown("### Account Details")
        st.markdown(f"**Email:** {user.get('email','N/A')}")
        if user.get("role") == "student":
            st.markdown(f"**Grade:** {user.get('grade','N/A')}")
            st.markdown(f"**School:** {user.get('school','N/A')}")
        else:
            st.markdown(f"**Child:** {user.get('child_name','N/A')}")
            st.markdown(f"**Child Grade:** {user.get('child_grade','N/A')}")

        st.markdown("---")
        pages = ["Dashboard", "Prediction", "Reports", "History", "Share"]
        for p in pages:
            if st.button(p, use_container_width=True, key=f"nav_{p}"):
                st.session_state.page = p
                st.rerun()

        st.markdown("---")
        theme_button()

        st.markdown("---")
        if st.button("Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.auth_page = "welcome"
            st.rerun()


# =========================================================
# USER DETAIL CARD + USEFUL GRAPHS
# =========================================================
def user_detail_card(user):
    role = user.get("role", "student")
    details = [
        ("Full Name", user.get("full_name", "N/A")),
        ("Username", st.session_state.username),
        ("Email", user.get("email", "N/A")),
        ("Role", role.capitalize()),
    ]

    if role == "student":
        details.extend([
            ("Age", user.get("age", "N/A")),
            ("Grade", user.get("grade", "N/A")),
            ("School / College", user.get("school", "N/A")),
        ])
    else:
        details.extend([
            ("Child Name", user.get("child_name", "N/A")),
            ("Child Grade", user.get("child_grade", "N/A")),
            ("Relation", user.get("relation", "N/A")),
        ])

    html = '<div class="app-card"><div class="section-title">Profile Details</div><div class="detail-grid">'
    for label, value in details:
        html += f"""
        <div class="detail-item">
            <div class="detail-label">{label}</div>
            <div class="detail-value">{value}</div>
        </div>
        """
    html += "</div></div>"
    st.markdown(html, unsafe_allow_html=True)

def input_trend_chart(records):
    if not records:
        return None

    x = [f"R{i}" for i in range(1, len(records) + 1)]
    hours = [r.get("inputs", {}).get("Hours_Studied", 0) for r in records]
    attendance = [r.get("inputs", {}).get("Attendance", 0) for r in records]
    previous = [r.get("inputs", {}).get("Previous_Scores", 0) for r in records]

    dark = st.session_state.get("theme", "dark") == "dark"
    txt = "#ffffff" if dark else "#03045e"
    grid = "rgba(0,180,216,0.15)"

    fig = go.Figure()
    fig.add_trace(go.Bar(x=x, y=hours, name="Study Hours", marker_color="#00b4d8"))
    fig.add_trace(go.Scatter(x=x, y=attendance, mode="lines+markers", name="Attendance %", line=dict(color="#90e0ef", width=3)))
    fig.add_trace(go.Scatter(x=x, y=previous, mode="lines+markers", name="Previous Score", line=dict(color="#fbbf24", width=3)))

    fig.update_layout(
        title="Study Hours, Attendance and Previous Score Overview",
        height=390,
        barmode="group",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=txt),
        xaxis=dict(gridcolor=grid),
        yaxis=dict(gridcolor=grid, rangemode="tozero"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig

def score_distribution_chart(scores):
    if not scores:
        return None

    labels = ["Needs Improvement", "Satisfactory", "Good", "Excellent"]
    counts = [
        len([s for s in scores if s < 55]),
        len([s for s in scores if 55 <= s < 70]),
        len([s for s in scores if 70 <= s < 85]),
        len([s for s in scores if s >= 85]),
    ]

    dark = st.session_state.get("theme", "dark") == "dark"
    txt = "#ffffff" if dark else "#03045e"

    fig = go.Figure(data=[go.Pie(
        labels=labels,
        values=counts,
        hole=0.55,
        textinfo="label+percent",
        marker=dict(colors=["#f87171", "#fbbf24", "#00b4d8", "#34d399"])
    )])
    fig.update_layout(
        title="Performance Category Distribution",
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color=txt),
        showlegend=True
    )
    return fig

def latest_input_bar(result):
    if not result:
        return None

    data = result.get("inputs", {})
    labels = ["Study Hours", "Attendance", "Previous Score", "Sleep Hours"]
    values = [
        data.get("Hours_Studied", 0),
        data.get("Attendance", 0),
        data.get("Previous_Scores", 0),
        data.get("Sleep_Hours", 0),
    ]

    dark = st.session_state.get("theme", "dark") == "dark"
    txt = "#ffffff" if dark else "#03045e"

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=labels,
        y=values,
        marker_color=["#00b4d8", "#90e0ef", "#fbbf24", "#34d399"],
        text=values,
        textposition="auto"
    ))
    fig.update_layout(
        title="Latest Report Input Snapshot",
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=txt),
        yaxis=dict(rangemode="tozero", gridcolor="rgba(0,180,216,0.15)")
    )
    return fig


# =========================================================
# DASHBOARD
# =========================================================
def dashboard(user):
    st.markdown("<h1>Dashboard</h1>", unsafe_allow_html=True)
    history = get_user_history(st.session_state.username)
    scores = history.get("scores", [])
    records = history.get("records", [])

    user_detail_card(user)

    c1, c2, c3, c4 = st.columns(4)
    avg_score = round(sum(scores) / len(scores), 1) if scores else "N/A"
    metrics = [
        ("Total Reports", len(scores)),
        ("Last Score", scores[-1] if scores else "N/A"),
        ("Average Score", avg_score),
        ("Best Score", max(scores) if scores else "N/A"),
    ]
    for col, (label, value) in zip([c1, c2, c3, c4], metrics):
        with col:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-value">{value}</div>
                <div class="metric-label">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.write("")
    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Useful Data Insights</div>', unsafe_allow_html=True)
    st.write("These graphs show score progress, study effort, attendance, previous marks and performance category in a clear way.")
    st.markdown("</div>", unsafe_allow_html=True)

    if scores:
        st.plotly_chart(score_chart(scores), use_container_width=True)

        g1, g2 = st.columns(2)
        with g1:
            fig = input_trend_chart(records)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
        with g2:
            fig = score_distribution_chart(scores)
            if fig:
                st.plotly_chart(fig, use_container_width=True)

        if st.session_state.last_result:
            fig = latest_input_bar(st.session_state.last_result)
            if fig:
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No prediction yet. Go to Prediction page and generate your first report.")

# =========================================================
# PREDICTION PAGE
# =========================================================
def prediction_page(user):
    st.markdown("<h1>Prediction</h1>", unsafe_allow_html=True)

    if user.get("role") == "parent":
        st.info(f"Predicting for child: {user.get('child_name', 'Child')}")

    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Academic Inputs</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        hours = st.number_input("Hours Studied per Day", 0.0, 24.0, 5.0, 0.5)
        attendance = st.number_input("Attendance (%)", 0.0, 100.0, 75.0, 1.0)
        previous = st.number_input("Previous Score", 0.0, 100.0, 65.0, 1.0)
        sleep = st.number_input("Sleep Hours", 0.0, 12.0, 7.0, 0.5)
        motivation = st.selectbox("Motivation Level", ["Low", "Medium", "High"])
        teacher = st.selectbox("Teacher Quality", ["Poor", "Average", "Good"])
        school_type = st.selectbox("School Type", ["Public", "Private"])

    with col2:
        internet = st.selectbox("Internet Access", ["Yes", "No"])
        income = st.selectbox("Family Income", ["Low", "Medium", "High"])
        parent_inv = st.selectbox("Parental Involvement", ["Low", "Medium", "High"])
        education = st.selectbox("Parental Education Level", ["School", "College"])
        peer = st.selectbox("Peer Influence", ["Negative", "Neutral", "Positive"])
        resources = st.selectbox("Learning Resources", ["Low", "Medium", "High"])
        activities = st.selectbox("Extracurricular Activities", ["Yes", "No"])

    st.markdown("</div>", unsafe_allow_html=True)

    if st.button("Predict Score & Generate PDF", use_container_width=True):
        data = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Previous_Scores": previous,
            "Sleep_Hours": sleep,
            "Motivation_Level": motivation,
            "Teacher_Quality": teacher,
            "School_Type": school_type,
            "Internet_Access": internet,
            "Family_Income": income,
            "Parental_Involvement": parent_inv,
            "Parental_Education_Level": education,
            "Peer_Influence": peer,
            "Learning_Resources": resources,
            "Extracurricular_Activities": activities
        }

        model, columns, err = load_model_files()
        if model is not None and columns is not None:
            input_df = pd.DataFrame([data])
            input_df = pd.get_dummies(input_df)
            input_df = input_df.reindex(columns=columns, fill_value=0)
            pred = model.predict(input_df)[0]
            score = int(max(35, min(100, round(pred))))
        else:
            score = fallback_prediction(data)
            st.warning("Model files not found. Fallback scoring formula is being used. Keep student_model.pkl and model_columns.pkl in same folder for ML prediction.")

        recs = make_recommendations(data)
        result = {
            "score": score,
            "inputs": data,
            "recommendations": recs,
            "created_at": datetime.now().strftime("%d %B %Y, %I:%M %p")
        }

        pdf_bytes = make_pdf_report(st.session_state.username, user, result)
        result["pdf_filename"] = f"student_score_report_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"

        st.session_state.last_result = result
        st.session_state.last_pdf = pdf_bytes
        append_history(st.session_state.username, result)

        st.success("Prediction completed and PDF report generated.")
        st.rerun()

    if st.session_state.last_result:
        show_result_block(st.session_state.last_result)

# =========================================================
# REPORTS PAGE
# =========================================================
def reports_page(user):
    st.markdown("<h1>Reports</h1>", unsafe_allow_html=True)

    if not st.session_state.last_result or not st.session_state.last_pdf:
        st.info("No active report. Generate a prediction first.")
        return

    result = st.session_state.last_result
    show_result_block(result)

    fig = latest_input_bar(result)
    if fig:
        st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="app-card">', unsafe_allow_html=True)
    st.markdown('<div class="section-title">Printable Document</div>', unsafe_allow_html=True)
    st.download_button(
        "Download PDF Report",
        data=st.session_state.last_pdf,
        file_name=result.get("pdf_filename", "student_score_report.pdf"),
        mime="application/pdf",
        use_container_width=True
    )
    st.write("This PDF contains user information, prediction score, input summary, and recommendations.")
    st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# SHARE PAGE
# =========================================================
def share_page(user):
    st.markdown("<h1>Share Report</h1>", unsafe_allow_html=True)

    if not st.session_state.last_result or not st.session_state.last_pdf:
        st.info("Generate a prediction first. Then share the PDF document.")
        return

    result = st.session_state.last_result
    score = result["score"]
    filename = result.get("pdf_filename", "student_score_report.pdf")
    caption = f"Student Score Predictor Report\nPredicted Score: {score}/100\nPlease find the PDF report attached."

    col1, col2 = st.columns(2)

    with col1:
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Email PDF Document</div>', unsafe_allow_html=True)
        receiver = st.text_input("Receiver Email", value=user.get("email", ""))
        body = st.text_area(
            "Email Message",
            value=f"Hello,\n\nPlease find attached the Student Score Predictor PDF report.\n\nPredicted Score: {score}/100\n\nRegards,\n{user.get('full_name', st.session_state.username)}"
        )
        if st.button("Send PDF by Email", use_container_width=True):
            if not receiver:
                st.warning("Enter receiver email.")
            else:
                ok, msg = send_pdf_email(
                    receiver,
                    "Student Score Predictor PDF Report",
                    body,
                    st.session_state.last_pdf,
                    filename
                )
                st.success(msg) if ok else st.error(msg)
        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">WhatsApp PDF Document</div>', unsafe_allow_html=True)
        phone = st.text_input("Receiver WhatsApp Number with Country Code", placeholder="Example: 919876543210")
        if st.button("Send PDF Directly on WhatsApp", use_container_width=True):
            if not phone:
                st.warning("Enter WhatsApp number.")
            else:
                ok, msg = send_pdf_whatsapp(phone, caption, st.session_state.last_pdf, filename)
                st.success(msg) if ok else st.error(msg)

        manual_url = f"https://wa.me/{clean_phone(phone)}?text={quote(caption)}" if phone else f"https://wa.me/?text={quote(caption)}"
        st.markdown(f"""
        <a href="{manual_url}" target="_blank" style="text-decoration:none;">
            <button style="width:100%;background:linear-gradient(135deg,#25D366,#128C7E);color:white;border:none;border-radius:999px;padding:0.65rem;font-weight:800;cursor:pointer;">
                Open WhatsApp Manually
            </button>
        </a>
        """, unsafe_allow_html=True)
        st.caption("Manual WhatsApp button opens chat with message. PDF auto-attach only works through WhatsApp Cloud API.")
        st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# HISTORY PAGE
# =========================================================
def history_page(user):
    st.markdown("<h1>History</h1>", unsafe_allow_html=True)
    history = get_user_history(st.session_state.username)
    scores = history.get("scores", [])
    records = history.get("records", [])

    if not records:
        st.info("No report history yet.")
        return

    st.plotly_chart(score_chart(scores), use_container_width=True)

    g1, g2 = st.columns(2)
    with g1:
        fig = input_trend_chart(records)
        if fig:
            st.plotly_chart(fig, use_container_width=True)
    with g2:
        fig = score_distribution_chart(scores)
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    table_rows = []
    for i, rec in enumerate(records, 1):
        table_rows.append({
            "No.": i,
            "Date": rec.get("created_at", ""),
            "Score": rec.get("score", ""),
            "Hours": rec.get("inputs", {}).get("Hours_Studied", ""),
            "Attendance": rec.get("inputs", {}).get("Attendance", ""),
            "Previous Score": rec.get("inputs", {}).get("Previous_Scores", "")
        })
    st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)

# =========================================================
# SHARED UI
# =========================================================
def show_result_block(result):
    score = result["score"]
    status = "Excellent" if score >= 85 else "Good" if score >= 70 else "Satisfactory" if score >= 55 else "Needs Improvement"

    st.markdown(f"""
    <div class="result-box">
        <div style="letter-spacing:3px;font-size:0.78rem;color:#90e0ef !important;">PREDICTED EXAM SCORE</div>
        <div class="result-score">{score}<span style="font-size:1.3rem;">/100</span></div>
        <div style="font-size:1rem;color:#caf0f8 !important;">{status}</div>
    </div>
    """, unsafe_allow_html=True)

    st.write("")
    if result.get("recommendations"):
        st.markdown('<div class="app-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Recommendations</div>', unsafe_allow_html=True)
        for rec in result["recommendations"]:
            st.write(f"• {rec}")
        st.markdown("</div>", unsafe_allow_html=True)

def make_recommendations(data):
    recs = []
    if data["Hours_Studied"] < 6:
        recs.append("Increase daily study time to 6-8 hours with short revision breaks.")
    if data["Attendance"] < 80:
        recs.append("Improve attendance because regular classes strongly support consistent marks.")
    if data["Sleep_Hours"] < 7:
        recs.append("Take 7-9 hours of sleep for better concentration and memory.")
    if data["Previous_Scores"] < 60:
        recs.append("Revise weak chapters and solve previous question papers weekly.")
    if data["Motivation_Level"] == "Low":
        recs.append("Set small daily targets and track them to improve motivation.")
    if data["Teacher_Quality"] == "Poor":
        recs.append("Use extra learning support such as online lectures or tutoring.")
    if data["Internet_Access"] == "No":
        recs.append("Use offline notes, library books, and downloaded study material.")
    if data["Learning_Resources"] == "Low":
        recs.append("Improve access to books, notes, practice sets, and learning videos.")
    if data["Peer_Influence"] == "Negative":
        recs.append("Prefer a positive study group and avoid distractions.")
    return recs

def get_user_history(username):
    history = load_json(HISTORY_FILE, {})
    return history.get(username, {"scores": [], "records": []})

def append_history(username, result):
    history = load_json(HISTORY_FILE, {})
    if username not in history:
        history[username] = {"scores": [], "records": []}

    history[username]["scores"].append(result["score"])
    history[username]["records"].append(result)

    history[username]["scores"] = history[username]["scores"][-20:]
    history[username]["records"] = history[username]["records"][-20:]

    save_json(HISTORY_FILE, history)

def score_chart(scores):
    x = [f"Report {i}" for i in range(1, len(scores) + 1)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=x,
        y=scores,
        mode="lines+markers",
        name="Score",
        line=dict(color="#00b4d8", width=3),
        marker=dict(size=9, color="#00b4d8", line=dict(color="white", width=2)),
        fill="tozeroy",
        fillcolor="rgba(0,180,216,0.10)"
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#f87171", annotation_text="Pass")
    fig.add_hline(y=85, line_dash="dash", line_color="#34d399", annotation_text="Excellent")

    dark = st.session_state.get("theme", "dark") == "dark"
    fig.update_layout(
        title="Score Progress",
        height=360,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ffffff" if dark else "#03045e"),
        xaxis=dict(gridcolor="rgba(0,180,216,0.15)"),
        yaxis=dict(gridcolor="rgba(0,180,216,0.15)", range=[30, 105])
    )
    return fig

# =========================================================
# MAIN ROUTER
# =========================================================
def main():
    init_state()

    if not st.session_state.logged_in:
        if st.session_state.auth_page == "welcome":
            welcome_page()
        else:
            auth_page()
        return

    apply_theme()
    users = load_json(USER_DB_FILE, {})
    user = users.get(st.session_state.username, {})
    sidebar(user)

    page = st.session_state.page
    if page == "Dashboard":
        dashboard(user)
    elif page == "Prediction":
        prediction_page(user)
    elif page == "Reports":
        reports_page(user)
    elif page == "History":
        history_page(user)
    elif page == "Share":
        share_page(user)

if __name__ == "__main__":
    main()
