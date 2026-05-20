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
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Line, String

import plotly.graph_objects as go

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

# Gmail OTP setup: use Gmail App Password, not normal Gmail password.
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
        <div style='font-family:Arial;background:#0f172a;color:white;padding:26px;border-radius:18px'>
          <h2>{APP_NAME}</h2>
          <p>Hello <b>{name}</b>, your signup OTP is:</p>
          <div style='font-size:34px;letter-spacing:8px;font-weight:800;color:#67e8f9'>{otp}</div>
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
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# CSS
# =====================================================
def apply_css():
    dark = st.session_state.theme == "dark"
    bg = "#07111f" if dark else "#eef7ff"
    card = "rgba(15,23,42,.78)" if dark else "rgba(255,255,255,.88)"
    text = "#f8fafc" if dark else "#0f172a"
    muted = "#cbd5e1" if dark else "#475569"
    border = "rgba(103,232,249,.25)" if dark else "rgba(14,165,233,.25)"
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * {{font-family:Inter, sans-serif;}}
    .stApp {{
        background:
        linear-gradient(rgba(7,17,31,.80), rgba(7,17,31,.86)),
        url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1800&q=80');
        background-size:cover;background-attachment:fixed;background-position:center;
        color:{text};
    }}
    .main .block-container {{padding-top:1.6rem; max-width:1200px;}}
    [data-testid="stSidebar"] {{background:{card}; border-right:1px solid {border}; backdrop-filter:blur(18px);}}
    .glass {{background:{card};border:1px solid {border};border-radius:26px;padding:26px;box-shadow:0 20px 60px rgba(0,0,0,.22);backdrop-filter:blur(16px);}}
    .hero {{min-height:70vh;display:flex;align-items:center;justify-content:center;text-align:center;}}
    .hero-box {{max-width:760px;background:rgba(15,23,42,.62);border:1px solid rgba(103,232,249,.30);border-radius:34px;padding:54px 32px;box-shadow:0 30px 90px rgba(0,0,0,.35);}}
    .app-title {{font-size:4.2rem;font-weight:900;line-height:1;color:white;margin:0;text-shadow:0 8px 30px rgba(0,0,0,.45);}}
    .tagline {{font-size:1.08rem;color:#dbeafe;margin-top:14px;margin-bottom:26px;}}
    .feature-mini {{display:inline-block;margin:6px;padding:10px 14px;border-radius:999px;background:rgba(103,232,249,.12);color:#e0f2fe;border:1px solid rgba(103,232,249,.22);font-weight:600;font-size:.88rem;}}
    .page-title {{font-size:2rem;font-weight:850;margin-bottom:4px;color:{text};}}
    .subtext {{color:{muted};font-size:.95rem;}}
    .metric-card {{background:{card};border:1px solid {border};border-radius:22px;padding:20px;text-align:center;}}
    .metric-value {{font-size:2.1rem;font-weight:900;color:#22d3ee;}}
    .metric-label {{font-size:.78rem;color:{muted};text-transform:uppercase;letter-spacing:.8px;}}
    .avatar-circle {{width:84px;height:84px;border-radius:50%;display:flex;align-items:center;justify-content:center;overflow:hidden;margin:auto;border:3px solid #22d3ee;background:linear-gradient(135deg,#2563eb,#06b6d4);font-size:2rem;}}
    .avatar-circle img {{width:100%;height:100%;object-fit:cover;}}
    .stButton>button, [data-testid="stDownloadButton"] button {{border-radius:999px!important;border:0!important;font-weight:800!important;cursor:pointer!important;padding:.65rem 1.2rem!important;background:linear-gradient(135deg,#2563eb,#06b6d4)!important;color:white!important;box-shadow:0 10px 24px rgba(6,182,212,.22)!important;}}
    .stButton>button:hover, [data-testid="stDownloadButton"] button:hover {{transform:translateY(-2px);box-shadow:0 14px 34px rgba(6,182,212,.36)!important;}}
    input, textarea, [data-baseweb="select"]>div {{border-radius:14px!important;}}
    .stNumberInput input, .stTextInput input, .stDateInput input {{background:{'rgba(15,23,42,.75)' if dark else 'white'}!important;color:{text}!important;border:1px solid {border}!important;}}
    label, p, span, div {{color:{text};}}
    .whatsapp-btn {{display:inline-block;border-radius:999px;padding:11px 18px;background:linear-gradient(135deg,#25D366,#128C7E);color:white!important;text-decoration:none;font-weight:800;margin-top:4px;}}
    .email-btn {{display:inline-block;border-radius:999px;padding:11px 18px;background:linear-gradient(135deg,#6366f1,#0ea5e9);color:white!important;text-decoration:none;font-weight:800;margin-top:4px;margin-left:8px;}}
    hr {{border-color:{border}!important;}}
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
        # Safe fallback formula so app still runs while model files are missing.
        pred = (
            data["Previous_Scores"] * 0.38 + data["Attendance"] * 0.22 +
            min(data["Hours_Studied"] * 7, 45) * 0.55 + data["Sleep_Hours"] * 2.2
        )
        bonus = {"Low": -4, "Medium": 2, "High": 6}.get(data["Motivation_Level"], 0)
        pred += bonus
    return int(max(0, min(100, round(pred))))


def get_recommendations(d):
    recs = []
    if d["Hours_Studied"] < 6: recs.append("Study hours ko 6–8 hours daily tak improve karein.")
    if d["Attendance"] < 80: recs.append("Attendance ko 80%+ rakhna score ke liye important hai.")
    if d["Sleep_Hours"] < 7: recs.append("Daily 7–8 hours sleep rakhein, concentration improve hota hai.")
    if d["Motivation_Level"] == "Low": recs.append("Daily small goals set karein aur progress track karein.")
    if d["Internet_Access"] == "No": recs.append("Offline notes, library aur teacher support ka use karein.")
    if d["Learning_Resources"] == "Low": recs.append("Free resources jaise YouTube lectures aur PDFs use karein.")
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
    drawing.add(String(10, 145, "Score History Graph", fontSize=12, fillColor=colors.HexColor("#0f172a")))
    drawing.add(Line(35, 30, 410, 30, strokeColor=colors.grey))
    drawing.add(Line(35, 30, 35, 130, strokeColor=colors.grey))
    for y, lab in [(30, "0"), (80, "50"), (130, "100")]:
        drawing.add(String(8, y-4, lab, fontSize=7, fillColor=colors.grey))
        drawing.add(Line(35, y, 410, y, strokeColor=colors.lightgrey, strokeWidth=.4))
    if len(scores) >= 1:
        xs = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        pts = [(float(x), 30 + (float(s) / 100) * 100) for x, s in zip(xs, scores)]
        for i in range(len(pts)-1):
            drawing.add(Line(pts[i][0], pts[i][1], pts[i+1][0], pts[i+1][1], strokeColor=colors.HexColor("#0891b2"), strokeWidth=2))
        for i, (x, y) in enumerate(pts):
            drawing.add(String(x-5, y+6, str(scores[i]), fontSize=7, fillColor=colors.HexColor("#0f172a")))
    return drawing


def generate_pdf(username, user_data, score, inputs, recs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=.45*inch, bottomMargin=.45*inch)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("TitleX", parent=styles["Heading1"], alignment=1, fontSize=22, textColor=colors.HexColor("#0891b2"), spaceAfter=16)
    head = ParagraphStyle("HeadX", parent=styles["Heading2"], fontSize=14, textColor=colors.HexColor("#0f172a"), spaceAfter=8)
    normal = ParagraphStyle("NormX", parent=styles["Normal"], fontSize=10, leading=14)
    story = []
    story.append(Paragraph(f"{APP_NAME} — Official Prediction Report", title))
    story.append(Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", normal))
    story.append(Spacer(1, 10))
    student_name = user_data.get("full_name") or user_data.get("child_name") or username
    info = [["Name", student_name], ["Username", username], ["Email", user_data.get("email", "N/A")], ["Role", user_data.get("role", "N/A").title()]]
    story.append(Paragraph("Student / User Details", head))
    t = Table(info, colWidths=[2.1*inch, 4.2*inch])
    t.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(0,-1),colors.HexColor('#e0f2fe')),('FONTNAME',(0,0),(0,-1),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),8)]))
    story.append(t); story.append(Spacer(1, 12))
    result = [["Predicted Score", f"{score}/100"], ["Status", "Excellent" if score>=85 else "Good" if score>=70 else "Needs Improvement"]]
    story.append(Paragraph("Prediction Result", head))
    rt = Table(result, colWidths=[2.1*inch, 4.2*inch])
    rt.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0891b2')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),8)]))
    story.append(rt); story.append(Spacer(1, 12))
    story.append(Paragraph("Input Details", head))
    input_rows = [["Field", "Value"]] + [[k.replace('_',' '), str(v)] for k, v in inputs.items()]
    it = Table(input_rows, colWidths=[2.7*inch, 3.6*inch])
    it.setStyle(TableStyle([('GRID',(0,0),(-1,-1),.5,colors.lightgrey),('BACKGROUND',(0,0),(-1,0),colors.HexColor('#0f172a')),('TEXTCOLOR',(0,0),(-1,0),colors.white),('FONTNAME',(0,0),(-1,0),'Helvetica-Bold'),('PADDING',(0,0),(-1,-1),7)]))
    story.append(it); story.append(Spacer(1, 12))
    scores = [r.get("score", 0) for r in user_history(username)] + [score]
    story.append(simple_pdf_graph(scores[-10:]))
    story.append(Spacer(1, 12))
    story.append(Paragraph("Recommendations", head))
    if recs:
        for r in recs:
            story.append(Paragraph("• " + r, normal))
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
    label = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(label, key=key):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()


def score_chart(records):
    scores = [r["score"] for r in records]
    dates = [r.get("date", f"#{i+1}") for i, r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=scores, mode="lines+markers", name="Score", line=dict(width=4), marker=dict(size=10)))
    fig.add_hline(y=60, line_dash="dash", annotation_text="Pass")
    fig.add_hline(y=85, line_dash="dot", annotation_text="Excellent")
    fig.update_layout(height=330, margin=dict(l=10,r=10,t=30,b=10), paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    return fig

# =====================================================
# WELCOME + AUTH
# =====================================================
def welcome_page():
    c1, c2, c3 = st.columns([1,1,1])
    with c3: toggle_theme_button("theme_welcome")
    st.markdown(f"""
    <div class='hero'>
      <div class='hero-box'>
        <div style='font-size:4.4rem'>🎓</div>
        <h1 class='app-title'>{APP_NAME}</h1>
        <p class='tagline'>{TAGLINE}</p>
        <div>
          <span class='feature-mini'>OTP Signup</span>
          <span class='feature-mini'>PDF Report</span>
          <span class='feature-mini'>WhatsApp Share</span>
          <span class='feature-mini'>Smart Graphs</span>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,1.2,1])
    with col2:
        if st.button("Get Started", use_container_width=True):
            st.session_state.auth_page = "login"
            st.rerun()


def auth_page():
    users = load_json(USER_DB_FILE, {})
    col1, col2 = st.columns([8,1])
    with col1:
        if st.button("← Welcome"):
            st.session_state.auth_page = "welcome"; st.rerun()
    with col2: toggle_theme_button("theme_auth")
    st.markdown("<div class='glass'>", unsafe_allow_html=True)
    st.markdown(f"<h2 style='text-align:center'>{APP_NAME}</h2><p class='subtext' style='text-align:center'>Secure Login / OTP Signup</p>", unsafe_allow_html=True)
    tab_login, tab_signup = st.tabs(["Login", "Sign Up"])
    with tab_login:
        username = st.text_input("Username", key="login_user")
        password = st.text_input("Password", type="password", key="login_pass")
        if st.button("Login", use_container_width=True):
            if username in users and users[username]["password"] == hash_password(password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.role = users[username].get("role", "student")
                st.session_state.active_page = "Home"
                st.rerun()
            else:
                st.error("Invalid username or password.")
    with tab_signup:
        role = st.selectbox("Account Type", ["student", "parent"], format_func=lambda x: x.title())
        username = st.text_input("Create Username", key="su_user")
        email = st.text_input("Email for OTP", key="su_email")
        full_name = st.text_input("Full Name", key="su_name")
        password = st.text_input("Password", type="password", key="su_pass")
        confirm = st.text_input("Confirm Password", type="password", key="su_confirm")
        if role == "student":
            dob = st.date_input("Date of Birth", key="su_dob", min_value=datetime(1990,1,1), max_value=datetime.now())
            grade = st.selectbox("Class / Course", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
            school = st.text_input("School / College")
        else:
            child_name = st.text_input("Child Name")
            grade = st.selectbox("Child Class / Course", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
            relation = st.selectbox("Relation", ["Father", "Mother", "Guardian"])
        if st.button("Send OTP", use_container_width=True):
            if not email:
                st.warning("Email required.")
            else:
                otp = generate_otp(); store_otp(email, otp)
                ok, msg = send_otp_email(email, otp, full_name or "User")
                if ok:
                    st.success("OTP sent. Check email inbox.")
                else:
                    st.warning(f"Email not configured. Testing OTP: {otp}")
        otp_entered = st.text_input("Enter OTP", max_chars=6)
        if st.button("Verify OTP & Create Account", use_container_width=True):
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
                    st.success("Account created. Now login.")
    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# MAIN APP PAGES
# =====================================================
def sidebar(user):
    with st.sidebar:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(st.session_state.username, icon)}</div>", unsafe_allow_html=True)
        st.markdown(f"<h3 style='text-align:center;margin-bottom:0'>{user.get('full_name', st.session_state.username)}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p class='subtext' style='text-align:center'>{user.get('role','student').title()} Account</p>", unsafe_allow_html=True)
        pages = ["Home", "Prediction", "Report & Share", "History", "Profile"]
        st.session_state.active_page = st.radio("Navigation", pages, index=pages.index(st.session_state.active_page))
        st.markdown("---")
        toggle_theme_button("theme_sidebar")
        if st.button("Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.auth_page = "welcome"
            st.rerun()


def home_page(user):
    records = user_history(st.session_state.username)
    st.markdown(f"<div class='page-title'>Welcome to {APP_NAME}</div><p class='subtext'>Your academic dashboard is ready.</p>", unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    scores = [r["score"] for r in records]
    metrics = [("Attempts", len(records)), ("Best Score", max(scores) if scores else 0), ("Average", int(np.mean(scores)) if scores else 0), ("Last Score", scores[-1] if scores else 0)]
    for col, (label, val) in zip([c1,c2,c3,c4], metrics):
        with col:
            st.markdown(f"<div class='metric-card'><div class='metric-value'>{val}</div><div class='metric-label'>{label}</div></div>", unsafe_allow_html=True)
    st.markdown("---")
    if records:
        st.plotly_chart(score_chart(records), use_container_width=True)
    else:
        st.info("Prediction page me jaakar first score generate karein.")


def prediction_page(user):
    st.markdown("<div class='page-title'>Score Prediction</div><p class='subtext'>All numeric inputs are integer-based.</p>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        hours = st.number_input("Hours Studied", 0, 24, 5, 1)
        attendance = st.number_input("Attendance (%)", 0, 100, 75, 1)
        previous = st.number_input("Previous Score", 0, 100, 60, 1)
        sleep = st.number_input("Sleep Hours", 0, 12, 7, 1)
        motivation = st.selectbox("Motivation Level", ["Low", "Medium", "High"])
        teacher = st.selectbox("Teacher Quality", ["Poor", "Average", "Good"])
        school_type = st.selectbox("School Type", ["Public", "Private"])
    with col2:
        internet = st.selectbox("Internet Access", ["Yes", "No"])
        income = st.selectbox("Family Income", ["Low", "Medium", "High"])
        parental = st.selectbox("Parental Involvement", ["Low", "Medium", "High"])
        education = st.selectbox("Parent Education", ["School", "College"])
        peer = st.selectbox("Peer Influence", ["Negative", "Neutral", "Positive"])
        resources = st.selectbox("Learning Resources", ["Low", "Medium", "High"])
        activities = st.selectbox("Extracurricular Activities", ["Yes", "No"])
    if st.button("Predict Score", use_container_width=True):
        data = {
            "Hours_Studied": int(hours), "Attendance": int(attendance), "Previous_Scores": int(previous), "Sleep_Hours": int(sleep),
            "Motivation_Level": motivation, "Teacher_Quality": teacher, "School_Type": school_type,
            "Internet_Access": internet, "Family_Income": income, "Parental_Involvement": parental,
            "Parental_Education_Level": education, "Peer_Influence": peer, "Learning_Resources": resources,
            "Extracurricular_Activities": activities,
        }
        score = predict_score(data)
        recs = get_recommendations(data)
        record = {"date": datetime.now().strftime("%d-%m-%Y %H:%M"), "score": score, "inputs": data, "recommendations": recs}
        save_prediction(st.session_state.username, record)
        st.session_state.last_score = score
        st.session_state.last_inputs = data
        st.session_state.last_recs = recs
        st.session_state.last_pdf = generate_pdf(st.session_state.username, user, score, data, recs)
        st.success(f"Predicted Score: {score}/100")
        st.session_state.active_page = "Report & Share"
        st.rerun()


def report_page(user):
    st.markdown("<div class='page-title'>Report & Share</div><p class='subtext'>Download PDF report and share result on WhatsApp or email.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Pehle Prediction page se score generate karein.")
        return
    latest = records[-1] if records else {"score": st.session_state.last_score, "inputs": st.session_state.last_inputs, "recommendations": st.session_state.last_recs}
    score, inputs, recs = latest["score"], latest["inputs"], latest.get("recommendations", [])
    pdf = st.session_state.last_pdf or generate_pdf(st.session_state.username, user, score, inputs, recs)
    st.markdown(f"<div class='metric-card'><div class='metric-label'>Predicted Score</div><div class='metric-value'>{score}/100</div></div>", unsafe_allow_html=True)
    st.download_button("Download Full PDF Report", data=pdf, file_name=f"{APP_NAME.replace(' ','_')}_Report_{st.session_state.username}.pdf", mime="application/pdf", use_container_width=True)
    share_text = f"{APP_NAME} Report%0APredicted Score: {score}/100%0AHours Studied: {inputs.get('Hours_Studied')}%0AAttendance: {inputs.get('Attendance')}%25%0APDF report downloaded from app."
    wa_url = "https://wa.me/?text=" + share_text
    email_url = "mailto:?subject=" + urllib.parse.quote(f"{APP_NAME} Prediction Report") + "&body=" + share_text
    st.markdown(f"<a class='whatsapp-btn' target='_blank' href='{wa_url}'>Share on WhatsApp</a><a class='email-btn' href='{email_url}'>Share via Email</a>", unsafe_allow_html=True)
    st.caption("Note: Browser/Streamlit direct WhatsApp me PDF attach nahi kar sakta. Pehle PDF download karein, phir WhatsApp chat me attach karein. Button result text direct open karta hai.")
    if records:
        st.plotly_chart(score_chart(records), use_container_width=True)
    if recs:
        st.subheader("Recommendations")
        for r in recs: st.info(r)


def history_page(user):
    st.markdown("<div class='page-title'>Prediction History</div><p class='subtext'>All previous predictions in one place.</p>", unsafe_allow_html=True)
    records = user_history(st.session_state.username)
    if not records:
        st.info("No prediction history yet.")
        return
    df = pd.DataFrame([{"Date": r["date"], "Score": r["score"], "Hours": r["inputs"].get("Hours_Studied"), "Attendance": r["inputs"].get("Attendance"), "Previous": r["inputs"].get("Previous_Scores")} for r in records])
    st.dataframe(df, use_container_width=True)
    st.plotly_chart(score_chart(records), use_container_width=True)


def profile_page(user):
    st.markdown("<div class='page-title'>Profile</div><p class='subtext'>Account and profile picture details.</p>", unsafe_allow_html=True)
    col1, col2 = st.columns([1,2])
    with col1:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(st.session_state.username, icon)}</div>", unsafe_allow_html=True)
        upload = st.file_uploader("Upload Profile Picture", type=["jpg","jpeg","png"])
        if upload and st.button("Save Profile Picture", use_container_width=True):
            save_profile_pic(st.session_state.username, upload.read())
            st.success("Profile picture updated.")
            st.rerun()
    with col2:
        st.write("**Username:**", st.session_state.username)
        st.write("**Name:**", user.get("full_name", "N/A"))
        st.write("**Email:**", user.get("email", "N/A"))
        st.write("**Role:**", user.get("role", "N/A").title())
        if user.get("role") == "student":
            st.write("**Age:**", user.get("age", "N/A"))
            st.write("**Grade:**", user.get("grade", "N/A"))
            st.write("**School/College:**", user.get("school", "N/A"))
        else:
            st.write("**Child Name:**", user.get("child_name", "N/A"))
            st.write("**Child Grade:**", user.get("child_grade", "N/A"))
            st.write("**Relation:**", user.get("relation", "N/A"))


def main_app():
    users = load_json(USER_DB_FILE, {})
    user = users.get(st.session_state.username, {})
    sidebar(user)
    page = st.session_state.active_page
    if page == "Home": home_page(user)
    elif page == "Prediction": prediction_page(user)
    elif page == "Report & Share": report_page(user)
    elif page == "History": history_page(user)
    elif page == "Profile": profile_page(user)

# =====================================================
# ROUTER
# =====================================================
if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()
