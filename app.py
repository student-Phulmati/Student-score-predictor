import streamlit as st
import joblib
import pandas as pd
import numpy as np
import hashlib
import json
import os
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
# USER DATABASE FILE
# =====================================
USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"

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

def generate_pdf_report(username, final_score, user_data, hours, attendance, previous, sleep, recommendations):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, topMargin=0.5*inch, bottomMargin=0.5*inch)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        textColor=colors.HexColor('#0077b6'),
        alignment=1,
        spaceAfter=30
    )
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        textColor=colors.HexColor('#023e8a'),
        spaceAfter=12
    )
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    story = []
    story.append(Paragraph("Student Score Predictor - Report", title_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Student Information", heading_style))
    story.append(Paragraph(f"Name: {user_data.get('full_name', username)}", normal_style))
    story.append(Paragraph(f"Username: {username}", normal_style))
    if st.session_state.user_role == "student":
        story.append(Paragraph(f"Grade: {user_data.get('grade', 'N/A')}", normal_style))
        story.append(Paragraph(f"School: {user_data.get('school', 'N/A')}", normal_style))
    else:
        story.append(Paragraph(f"Parent Name: {user_data.get('full_name', username)}", normal_style))
        story.append(Paragraph(f"Child Name: {user_data.get('child_name', 'N/A')}", normal_style))
        story.append(Paragraph(f"Child Grade: {user_data.get('child_grade', 'N/A')}", normal_style))
    story.append(Paragraph(f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", normal_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Prediction Results", heading_style))
    score_data = [["Metric", "Value"], ["Predicted Exam Score", f"{final_score}/100"]]
    score_table = Table(score_data, colWidths=[2.5*inch, 2.5*inch])
    score_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, 1), colors.HexColor('#e0f4ff')),
        ('GRID', (0, 0), (1, 1), 1, colors.HexColor('#90caf9'))
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
        ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#0077b6')),
        ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (1, 0), 12),
        ('BACKGROUND', (0, 1), (1, -1), colors.HexColor('#e0f4ff')),
        ('GRID', (0, 0), (1, -1), 1, colors.HexColor('#90caf9'))
    ]))
    story.append(input_table)
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Performance Assessment", heading_style))
    if final_score >= 85:
        assessment = "EXCEPTIONAL PERFORMANCE - Outstanding results!"
    elif final_score >= 70:
        assessment = "GOOD PERFORMANCE - Keep improving!"
    elif final_score >= 55:
        assessment = "SATISFACTORY PERFORMANCE - Room for improvement"
    else:
        assessment = "NEEDS IMPROVEMENT - Review recommendations"
    story.append(Paragraph(assessment, normal_style))
    story.append(Spacer(1, 0.1*inch))
    if recommendations:
        story.append(Paragraph("Recommendations", heading_style))
        for rec in recommendations:
            story.append(Paragraph(f"• {rec}", normal_style))
    else:
        story.append(Paragraph("Excellent study habits! Maintain your routine", normal_style))
    story.append(Spacer(1, 0.2*inch))
    story.append(Paragraph("Generated by Student Score Predictor - AI Powered Academic Tool",
                          ParagraphStyle('Footer', parent=styles['Normal'], fontSize=8, textColor=colors.grey, alignment=1)))
    doc.build(story)
    buffer.seek(0)
    return buffer

# =====================================
# SESSION STATE
# =====================================
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'user_role' not in st.session_state:
    st.session_state.user_role = ""
if 'auth_mode' not in st.session_state:
    st.session_state.auth_mode = "login"
if 'signup_role' not in st.session_state:
    st.session_state.signup_role = "student"
if 'theme' not in st.session_state:
    st.session_state.theme = "dark"

all_history = load_history()

# =====================================
# CSS — IMPROVED LIGHT THEME (soft blue-white palette)
# =====================================
light_theme_css = """
<style>
    /* ---- Backgrounds ---- */
    .stApp {
        background: linear-gradient(145deg, #e8f4fd 0%, #dbeafe 50%, #e0f2fe 100%);
    }
    .main .block-container {
        background: rgba(255,255,255,0.92);
        border-radius: 20px;
        padding: 1.5rem;
        border: 1px solid #bfdbfe;
        box-shadow: 0 4px 24px rgba(14,116,189,0.08);
    }
    [data-testid="stSidebar"] {
        background: rgba(255,255,255,0.95);
        border-right: 1px solid #bfdbfe;
    }

    /* ---- Typography ---- */
    .stApp, .stApp * { color: #1e3a5f !important; }
    h1, h2, h3 { color: #0c2d6b !important; }

    /* ---- Inputs ---- */
    .stNumberInput input, .stTextInput input {
        background: #f0f7ff !important;
        border: 1px solid #93c5fd !important;
        border-radius: 10px !important;
        padding: 0.4rem 0.8rem !important;
        color: #1e3a5f !important;
    }
    div[data-baseweb="select"] > div {
        background: #f0f7ff !important;
        border: 1px solid #93c5fd !important;
        border-radius: 10px !important;
        min-height: 38px !important;
    }
    .stNumberInput button {
        background: #dbeafe !important;
        border: 1px solid #93c5fd !important;
    }
    .stNumberInput button:hover { background: #0077b6 !important; }
    div[data-baseweb="popover"] div {
        background: #f0f7ff !important;
        border: 1px solid #93c5fd !important;
    }
    li[role="option"] { color: #1e3a5f !important; }
    li[role="option"]:hover { background: #0077b6 !important; color: white !important; }

    /* ---- Buttons ---- */
    .stButton > button {
        background: linear-gradient(135deg, #0077b6, #0096c7) !important;
        color: white !important;
        border: none !important;
        border-radius: 50px !important;
        padding: 0.4rem 1rem !important;
        font-weight: 600 !important;
        box-shadow: 0 3px 12px rgba(0,119,182,0.25);
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 18px rgba(0,119,182,0.35) !important;
    }

    /* ---- Result Card ---- */
    .result-card {
        background: linear-gradient(135deg, #023e8a, #0077b6);
        border: 2px solid #90e0ef;
        border-radius: 16px;
        padding: 1.2rem;
        text-align: center;
        margin: 1rem 0;
        box-shadow: 0 6px 24px rgba(0,119,182,0.2);
    }
    .result-card .result-score {
        color: #90e0ef !important;
        font-weight: 800 !important;
        font-size: 2.4rem !important;
    }
    .result-card .result-label {
        color: #caf0f8 !important;
        font-size: 0.7rem !important;
        letter-spacing: 2px !important;
    }

    /* ---- Download button ---- */
    .download-btn-left { text-align: left; margin: 0.5rem 0; }
    .download-btn-left button {
        background: rgba(0,119,182,0.1) !important;
        border: 1px solid #0077b6 !important;
        color: #0077b6 !important;
        padding: 0.2rem 0.8rem !important;
        font-size: 0.75rem !important;
        font-weight: 500 !important;
        width: auto !important;
    }
    .download-btn-left button:hover {
        background: rgba(0,119,182,0.2) !important;
        transform: translateY(-2px);
    }

    /* ---- Theme toggle ---- */
    .top-theme-toggle {
        position: fixed; top: 0.8rem; right: 1rem; z-index: 999;
    }
    .top-theme-toggle button {
        background: rgba(0,119,182,0.12) !important;
        border: 1px solid #0077b6 !important;
        border-radius: 50px !important;
        padding: 0.2rem 0.7rem !important;
        font-size: 0.7rem !important;
        color: #0077b6 !important;
    }

    /* ---- Profile ---- */
    .profile-card { text-align: center; padding: 0.5rem; }
    .profile-name { font-size: 1rem; font-weight: 700; color: #0c2d6b !important; }
    .profile-role {
        font-size: 0.65rem; padding: 0.2rem 0.6rem; border-radius: 50px;
        display: inline-block; background: rgba(0,119,182,0.12);
        border: 1px solid #0077b6; color: #0077b6 !important;
    }

    /* ---- Alerts ---- */
    .stInfo { background-color: rgba(0,119,182,0.08) !important; border-left: 4px solid #0077b6 !important; }
    .stSuccess { background-color: rgba(0,168,107,0.08) !important; border-left: 4px solid #00a86b !important; }
    .stWarning { background-color: rgba(255,165,0,0.08) !important; border-left: 4px solid #ffa500 !important; }

    /* ---- Stat Cards ---- */
    .stat-card {
        background: linear-gradient(135deg, #eff6ff, #dbeafe);
        border: 1px solid #bfdbfe;
        border-radius: 12px;
        padding: 0.6rem;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,119,182,0.08);
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #0077b6 !important; }
    .stat-value-red { font-size: 1.4rem; font-weight: 700; color: #dc2626 !important; }
    .stat-label { font-size: 0.6rem; color: #64748b !important; }

    input::placeholder { color: #94a3b8 !important; }
    hr { margin: 0.8rem 0; border-color: #bfdbfe; }
</style>
"""

dark_theme_css = """
<style>
    .stApp { background: linear-gradient(135deg, #0f0c29, #302b63, #24243e); }
    .main .block-container { background: rgba(18,18,30,0.95); border-radius: 20px; padding: 1.5rem; border: 1px solid #2a2a4a; }
    [data-testid="stSidebar"] { background: rgba(18,18,30,0.95); border-right: 1px solid #2a2a4a; }
    h1, h2, h3, p, label, .stMarkdown, .stCaption { color: #ffffff !important; }
    .result-card .result-label { color: #888 !important; font-size: 0.7rem !important; letter-spacing: 2px !important; }
    .result-card .result-score { color: #00adb5 !important; font-weight: 800 !important; font-size: 2.2rem !important; }
    .stNumberInput input, .stTextInput input {
        background: #1e1e2e !important; border: 1px solid #3a3a5a !important;
        border-radius: 10px !important; padding: 0.4rem 0.8rem !important; color: #ffffff !important;
    }
    div[data-baseweb="select"] > div {
        background: #1e1e2e !important; border: 1px solid #3a3a5a !important;
        border-radius: 10px !important; min-height: 38px !important;
    }
    div[data-baseweb="select"] input { color: #ffffff !important; }
    .stNumberInput button { background: #2d2d44 !important; border: 1px solid #3a3a5a !important; color: #ffffff !important; }
    .stNumberInput button:hover { background: #00adb5 !important; }
    div[data-baseweb="popover"] div { background: #1e1e2e !important; border: 1px solid #3a3a5a !important; }
    li[role="option"] { color: #ffffff !important; }
    li[role="option"]:hover { background: #00adb5 !important; }
    .result-card {
        background: linear-gradient(135deg, #1a1a2e, #16213e);
        border: 2px solid #00adb5; border-radius: 16px; padding: 1rem; text-align: center; margin: 1rem 0;
    }
    .stButton > button {
        background: #00adb5 !important; color: white !important; border: none !important;
        border-radius: 50px !important; padding: 0.4rem 1rem !important; font-weight: 600 !important;
    }
    .stButton > button:hover { transform: translateY(-2px); box-shadow: 0 5px 15px rgba(0,173,181,0.4); }
    .download-btn-left { text-align: left; margin: 0.5rem 0; }
    .download-btn-left button {
        background: rgba(0,173,181,0.15) !important; border: 1px solid #00adb5 !important;
        color: #00adb5 !important; padding: 0.2rem 0.8rem !important;
        font-size: 0.75rem !important; font-weight: 500 !important; width: auto !important;
    }
    .download-btn-left button:hover { background: rgba(0,173,181,0.3) !important; transform: translateY(-2px); }
    .top-theme-toggle { position: fixed; top: 0.8rem; right: 1rem; z-index: 999; }
    .top-theme-toggle button {
        background: rgba(0,173,181,0.15) !important; border: 1px solid #00adb5 !important;
        border-radius: 50px !important; padding: 0.2rem 0.7rem !important;
        font-size: 0.7rem !important; color: white !important;
    }
    .profile-card { text-align: center; padding: 0.5rem; }
    .profile-name { font-size: 1rem; font-weight: 700; color: white !important; }
    .profile-role {
        font-size: 0.65rem; padding: 0.2rem 0.6rem; border-radius: 50px;
        display: inline-block; background: #00adb520; border: 1px solid #00adb5; color: white !important;
    }
    .stat-card {
        background: rgba(0,173,181,0.08); border: 1px solid #2a2a4a;
        border-radius: 12px; padding: 0.6rem; text-align: center;
    }
    .stat-value { font-size: 1.4rem; font-weight: 700; color: #00adb5 !important; }
    .stat-value-red { font-size: 1.4rem; font-weight: 700; color: #f44336 !important; }
    .stat-label { font-size: 0.6rem; color: #888 !important; }
    .stInfo, .stSuccess, .stWarning { background-color: rgba(0,173,181,0.2) !important; color: #ffffff !important; }
    hr { margin: 0.8rem 0; border-color: #3a3a5a; }
    input::placeholder { color: #888 !important; }
</style>
"""

def apply_theme():
    if st.session_state.theme == "dark":
        st.markdown(dark_theme_css, unsafe_allow_html=True)
    else:
        st.markdown(light_theme_css, unsafe_allow_html=True)

def theme_toggle():
    mode_text = "Light" if st.session_state.theme == "dark" else "Dark"
    mode_icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    if st.button(f"{mode_icon} {mode_text}", key="theme_toggle"):
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
        <div style="text-align: center; margin-bottom: 1rem;">
            <div style="font-size: 2.5rem;">🎓</div>
            <h1 style="font-size: 1.5rem; margin: 0.2rem 0;">Student Score Predictor</h1>
        </div>
        """, unsafe_allow_html=True)
        if st.session_state.auth_mode == "login":
            st.markdown('<p style="text-align: center; margin-bottom: 1rem; font-size: 0.8rem;">Sign in to continue</p>', unsafe_allow_html=True)
            username = st.text_input("Username", placeholder="Username", key="login_user", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Password", key="login_pass", label_visibility="collapsed")
            if username and username in users:
                role = users[username]["role"]
                role_icon = "🎓" if role == "student" else "👨‍👩‍👧"
                role_text = "Student" if role == "student" else "Parent"
                st.markdown(f'<p style="text-align: center; font-size: 0.7rem; margin-top: -0.3rem;">{role_icon} {role_text}</p>', unsafe_allow_html=True)
            if st.button("Sign In", use_container_width=True):
                if username and password:
                    if username in users and users[username]["password"] == hash_password(password):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.session_state.user_role = users[username]["role"]
                        st.rerun()
                    else:
                        st.error("Invalid credentials")
                else:
                    st.warning("Enter username and password")
            st.markdown("<hr>", unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Student Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "student"
                    st.rerun()
            with col_b:
                if st.button("Parent Sign Up", use_container_width=True):
                    st.session_state.auth_mode = "signup"
                    st.session_state.signup_role = "parent"
                    st.rerun()
        else:
            role = st.session_state.signup_role
            st.markdown(f'<p style="text-align: center; margin-bottom: 0.8rem; font-size: 0.8rem;">Create {role} account</p>', unsafe_allow_html=True)
            col_a, col_b = st.columns(2)
            with col_a:
                if st.button("Student", use_container_width=True):
                    st.session_state.signup_role = "student"
                    st.rerun()
            with col_b:
                if st.button("Parent", use_container_width=True):
                    st.session_state.signup_role = "parent"
                    st.rerun()
            st.markdown("---")
            username = st.text_input("Username", placeholder="Username", key="signup_user", label_visibility="collapsed")
            password = st.text_input("Password", type="password", placeholder="Password", key="signup_pass", label_visibility="collapsed")
            confirm = st.text_input("Confirm Password", type="password", placeholder="Confirm", key="signup_confirm", label_visibility="collapsed")
            full_name = st.text_input("Full Name", placeholder="Full Name", key="signup_name", label_visibility="collapsed")
            if role == "student":
                dob = st.date_input("Date of Birth", min_value=datetime(1990,1,1), max_value=datetime.now())
                grade = st.selectbox("Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                school = st.text_input("School Name", placeholder="School Name")
            else:
                child_name = st.text_input("Child's Name", placeholder="Child's Name")
                child_dob = st.date_input("Child's DOB", min_value=datetime(1990,1,1), max_value=datetime.now())
                child_grade = st.selectbox("Child's Grade", ["Class 8","Class 9","Class 10","Class 11","Class 12","College"])
                relation = st.selectbox("Relationship", ["Father","Mother","Guardian"])
            if st.button("Create Account", use_container_width=True):
                if not username or not password or not full_name:
                    st.warning("Fill all fields")
                elif password != confirm:
                    st.error("Passwords don't match")
                elif len(password) < 4:
                    st.warning("Password min 4 chars")
                elif username in users:
                    st.error("Username exists")
                else:
                    data = {
                        "password": hash_password(password), "role": role,
                        "full_name": full_name, "created_at": str(pd.Timestamp.now())
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
                    st.success("Account created!")
                    st.session_state.auth_mode = "login"
                    st.rerun()
            st.markdown("<hr>", unsafe_allow_html=True)
            if st.button("← Back to Sign In", use_container_width=True):
                st.session_state.auth_mode = "login"
                st.rerun()
        st.markdown('<p style="text-align: center; font-size: 0.55rem; margin-top: 0.8rem;">Secure Portal</p>', unsafe_allow_html=True)

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
        st.markdown("---")
        role_text = "Student" if st.session_state.user_role == "student" else "Parent"
        role_icon = "🎓" if st.session_state.user_role == "student" else "👨‍👩‍👧"
        st.markdown(f"""
        <div class="profile-card">
            <div style="font-size: 1.8rem;">{role_icon}</div>
            <div class="profile-name">{user_data.get('full_name', st.session_state.username)}</div>
            <div class="profile-role">{role_text}</div>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("### Account")
        st.markdown(f"**User:** {st.session_state.username}")
        st.markdown(f"**Name:** {user_data.get('full_name', 'N/A')}")
        if st.session_state.user_role == "student":
            st.markdown(f"**Age:** {user_data.get('age', 'N/A')}")
            st.markdown(f"**Grade:** {user_data.get('grade', 'N/A')}")
        else:
            st.markdown(f"**Child:** {user_data.get('child_name', 'N/A')}")
            st.markdown(f"**Child Grade:** {user_data.get('child_grade', 'N/A')}")
        st.markdown("---")
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.user_role = ""
            st.rerun()

# =====================================
# MAIN APP
# =====================================
def show_main_app():
    apply_theme()
    st.markdown('<div class="top-theme-toggle">', unsafe_allow_html=True)
    theme_toggle()
    st.markdown('</div>', unsafe_allow_html=True)

    users = load_users()
    user_data = users.get(st.session_state.username, {})
    show_sidebar(user_data)

    st.markdown("<h1 style='text-align: center;'>🎓 Student Score Predictor</h1>", unsafe_allow_html=True)

    if st.session_state.user_role == "parent":
        child_name = user_data.get("child_name", "Child")
        st.info(f"👨‍👩‍👧 Predicting for: **{child_name}**")

    model, columns = load_models()

    col1, col2 = st.columns(2)
    with col1:
        hours = st.number_input("Hours Studied", min_value=0.0, max_value=24.0, value=5.0, step=0.5)
        attendance = st.number_input("Attendance (%)", min_value=0.0, max_value=100.0, value=75.0, step=5.0)
        previous = st.number_input("Previous Score", min_value=0.0, max_value=100.0, value=60.0, step=5.0)
        sleep = st.number_input("Sleep Hours", min_value=0.0, max_value=12.0, value=7.0, step=0.5)
        motivation = st.selectbox("Motivation Level", ["Low", "Medium", "High"])
        teacher = st.selectbox("Teacher Quality", ["Poor", "Average", "Good"])
        school = st.selectbox("School Type", ["Public", "Private"])
    with col2:
        internet = st.selectbox("Internet Access", ["Yes", "No"])
        income = st.selectbox("Family Income", ["Low", "Medium", "High"])
        parent = st.selectbox("Parental Involvement", ["Low", "Medium", "High"])
        education = st.selectbox("Parent Education", ["School", "College"])
        peer = st.selectbox("Peer Influence", ["Negative", "Neutral", "Positive"])
        resources = st.selectbox("Learning Resources", ["Low", "Medium", "High"])
        activities = st.selectbox("Extracurricular Activities", ["Yes", "No"])

    if st.button("Predict Score", use_container_width=True):
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
        final_score = max(40, min(100, prediction[0]))
        final_score = int(round(final_score))

        # Save to history
        if st.session_state.username not in all_history:
            all_history[st.session_state.username] = []
        all_history[st.session_state.username].append(final_score)
        if len(all_history[st.session_state.username]) > 10:
            all_history[st.session_state.username] = all_history[st.session_state.username][-10:]
        save_history(all_history)

        user_history = all_history.get(st.session_state.username, [])

        # Result Card
        st.markdown(f"""
        <div class="result-card">
            <div class="result-label">PREDICTED EXAM SCORE</div>
            <div class="result-score">{final_score}<span style="font-size: 1rem;"> / 100</span></div>
        </div>
        """, unsafe_allow_html=True)

        if final_score >= 85:
            st.success("🎉 Exceptional Performance!")
            st.balloons()
        elif final_score >= 70:
            st.success("📈 Good Performance!")
        elif final_score >= 55:
            st.info("📚 Satisfactory")
        else:
            st.warning("⚠️ Needs Improvement")

        recs = []
        if hours < 6: recs.append("Increase study hours to 6-8 daily")
        if attendance < 75: recs.append("Improve attendance to 80%+")
        if sleep < 7: recs.append("Get 7-9 hours of sleep")
        if motivation == "Low": recs.append("Set daily goals to boost motivation")
        if teacher == "Poor": recs.append("Seek additional tutoring")
        if resources == "Low": recs.append("Utilize free online learning materials")
        if peer == "Negative": recs.append("Join positive study groups")

        # Download Report
        st.markdown('<div class="download-btn-left">', unsafe_allow_html=True)
        pdf_buffer = generate_pdf_report(
            st.session_state.username, final_score, user_data,
            hours, attendance, previous, sleep, recs
        )
        st.download_button(
            label="📄 Download PDF Report",
            data=pdf_buffer,
            file_name=f"score_report_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
            mime="application/pdf"
        )
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Performance Overview ──
        if len(user_history) >= 1:
            st.markdown("### 📊 Performance Overview")

            passing = len([s for s in user_history if s >= 60])
            needs_improvement = len([s for s in user_history if s < 60])
            last_score = user_history[-1]
            avg_score = int(np.mean(user_history))
            pass_percent = (passing / len(user_history)) * 100

            col_a, col_b, col_c, col_d, col_e = st.columns(5)
            stats = [
                (col_a, last_score, "Last Score", False),
                (col_b, avg_score, "Average", False),
                (col_c, passing, "Passed", False),
                (col_d, needs_improvement, "Need Improve", True),
                (col_e, len(user_history), "Total", False),
            ]
            for col, val, label, red in stats:
                val_class = "stat-value-red" if red else "stat-value"
                with col:
                    st.markdown(f"""
                    <div class="stat-card">
                        <div class="{val_class}">{val}</div>
                        <div class="stat-label">{label}</div>
                    </div>
                    """, unsafe_allow_html=True)

            st.progress(pass_percent / 100)
            st.caption(f"Success Rate: {pass_percent:.0f}% ({passing}/{len(user_history)})")

            # ── Score History GRAPH ──
            st.markdown("### 📈 Score History Graph")

            # Build DataFrame for chart
            attempts = list(range(1, len(user_history) + 1))
            chart_df = pd.DataFrame({
                "Attempt": [f"#{i}" for i in attempts],
                "Score": user_history,
                "Pass Line": [60] * len(user_history),
                "Good Line": [70] * len(user_history),
            }).set_index("Attempt")

            # Line chart with all three series
            st.line_chart(chart_df, use_container_width=True, height=280)

            # Legend note
            st.caption("📌 Score = Predicted score per attempt | Pass Line = 60 | Good Line = 70")

            # Bar chart for quick visual comparison
            st.markdown("#### 📊 Score Comparison (Bar)")
            bar_df = pd.DataFrame({
                "Score": user_history
            }, index=[f"#{i}" for i in attempts])
            st.bar_chart(bar_df, use_container_width=True, height=200)

        # Recommendations
        if recs:
            st.markdown("### 💡 Recommendations")
            for r in recs:
                st.info(r)
        else:
            st.success("✅ Excellent habits! Keep going!")

    st.markdown("---")
    st.caption("Student Score Predictor | Powered by AI")

# =====================================
# MAIN
# =====================================
if st.session_state.logged_in:
    show_main_app()
else:
    show_auth_page()
