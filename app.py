import streamlit as st
import joblib
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from fpdf import FPDF
import io
import os
from datetime import datetime

# ========================= PAGE CONFIG =========================
st.set_page_config(
    page_title="EduPredict Pro",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ========================= CUSTOM CSS =========================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@300;400;600;700;800&family=DM+Sans:wght@300;400;500&display=swap');

:root {
    --navy: #0D1B2A;
    --blue: #1B4FD8;
    --cyan: #00D4FF;
    --gold: #FFB800;
    --green: #00E676;
    --red: #FF4444;
    --card: #1A2744;
    --card2: #162038;
    --text: #E8EEF4;
    --muted: #8899AA;
}

* { font-family: 'Sora', sans-serif !important; }

html, body, [class*="css"] {
    background: var(--navy) !important;
    color: var(--text) !important;
}

/* Hide streamlit branding */
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; }

/* ---- HERO HEADER ---- */
.hero-header {
    background: linear-gradient(135deg, #0D1B2A 0%, #1B4FD8 50%, #00D4FF 100%);
    border-radius: 20px;
    padding: 2.5rem 2rem 2rem 2rem;
    margin-bottom: 2rem;
    text-align: center;
    border: 1px solid rgba(0,212,255,0.2);
    box-shadow: 0 0 60px rgba(27,79,216,0.3);
    position: relative;
    overflow: hidden;
}
.hero-header::before {
    content: '';
    position: absolute;
    top: -50%; left: -50%;
    width: 200%; height: 200%;
    background: radial-gradient(circle at 60% 40%, rgba(0,212,255,0.08) 0%, transparent 60%);
}
.hero-title {
    font-size: 2.8rem;
    font-weight: 800;
    color: white;
    letter-spacing: -1px;
    margin: 0;
}
.hero-sub {
    font-size: 1rem;
    color: rgba(255,255,255,0.7);
    margin-top: 0.5rem;
    font-weight: 300;
}

/* ---- LOGIN CARD ---- */
.login-wrap {
    max-width: 480px;
    margin: 0 auto;
}
.login-card {
    background: var(--card);
    border-radius: 20px;
    padding: 2.5rem;
    border: 1px solid rgba(0,212,255,0.15);
    box-shadow: 0 20px 60px rgba(0,0,0,0.4);
}
.role-pill {
    display: inline-block;
    padding: 0.4rem 1.2rem;
    border-radius: 999px;
    font-size: 0.85rem;
    font-weight: 600;
    margin: 0.3rem;
    cursor: pointer;
    border: 2px solid transparent;
}
.role-student { background: rgba(0,212,255,0.15); color: var(--cyan); border-color: var(--cyan); }
.role-parent  { background: rgba(255,184,0,0.15);  color: var(--gold); border-color: var(--gold); }

/* ---- SECTION LABELS ---- */
.section-label {
    font-size: 0.7rem;
    letter-spacing: 2px;
    text-transform: uppercase;
    color: var(--cyan);
    font-weight: 600;
    margin-bottom: 0.5rem;
}

/* ---- METRIC CARDS ---- */
.metric-row { display: flex; gap: 1rem; flex-wrap: wrap; margin-bottom: 1.5rem; }
.metric-card {
    flex: 1; min-width: 140px;
    background: var(--card);
    border-radius: 16px;
    padding: 1.3rem 1rem;
    text-align: center;
    border: 1px solid rgba(255,255,255,0.06);
    box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.metric-val { font-size: 2rem; font-weight: 800; }
.metric-lbl { font-size: 0.75rem; color: var(--muted); font-weight: 400; margin-top: 0.2rem; }
.c-cyan  { color: var(--cyan); }
.c-gold  { color: var(--gold); }
.c-green { color: var(--green); }
.c-red   { color: var(--red); }

/* ---- SCORE BADGE ---- */
.score-badge {
    background: linear-gradient(135deg, #1B4FD8, #00D4FF);
    border-radius: 20px;
    padding: 2rem;
    text-align: center;
    margin: 1.5rem 0;
    border: 1px solid rgba(0,212,255,0.3);
    box-shadow: 0 0 40px rgba(0,212,255,0.2);
}
.score-big { font-size: 5rem; font-weight: 800; color: white; line-height: 1; }
.score-lbl { font-size: 1rem; color: rgba(255,255,255,0.7); margin-top: 0.5rem; }

/* ---- INPUT STYLING ---- */
.stNumberInput input, .stSelectbox select, div[data-baseweb="input"] input {
    background: var(--card2) !important;
    color: var(--text) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 10px !important;
}
div[data-baseweb="select"] > div {
    background: var(--card2) !important;
    border: 1px solid rgba(0,212,255,0.2) !important;
    border-radius: 10px !important;
    color: var(--text) !important;
}

/* ---- BUTTONS ---- */
.stButton > button {
    background: linear-gradient(135deg, #1B4FD8, #00D4FF) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    font-weight: 700 !important;
    font-size: 1rem !important;
    padding: 0.7rem 2rem !important;
    letter-spacing: 0.5px !important;
    transition: all 0.2s !important;
    box-shadow: 0 4px 20px rgba(27,79,216,0.4) !important;
}
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 30px rgba(0,212,255,0.4) !important;
}

/* ---- SUGGESTION CARD ---- */
.sug-card {
    background: var(--card);
    border-left: 4px solid var(--cyan);
    border-radius: 0 12px 12px 0;
    padding: 1rem 1.2rem;
    margin-bottom: 0.8rem;
    font-size: 0.92rem;
}
.sug-card.warn { border-color: var(--gold); }
.sug-card.good { border-color: var(--green); }

/* ---- TABS ---- */
.stTabs [data-baseweb="tab-list"] {
    background: var(--card) !important;
    border-radius: 12px !important;
    padding: 4px !important;
}
.stTabs [data-baseweb="tab"] {
    color: var(--muted) !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(135deg, #1B4FD8, #00D4FF) !important;
    color: white !important;
}

/* ---- DOWNLOAD BTN ---- */
.dl-btn { margin-top: 1rem; }

/* Progress bar */
.stProgress > div > div { background: linear-gradient(90deg, #1B4FD8, #00D4FF) !important; }

/* Divider */
hr { border-color: rgba(0,212,255,0.1) !important; }

/* Radio buttons */
.stRadio label { color: var(--text) !important; }

</style>
""", unsafe_allow_html=True)

# ========================= SESSION STATE =========================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "role" not in st.session_state:
    st.session_state.role = "Student"
if "username" not in st.session_state:
    st.session_state.username = ""
if "prediction_done" not in st.session_state:
    st.session_state.prediction_done = False
if "final_score" not in st.session_state:
    st.session_state.final_score = 0
if "input_data" not in st.session_state:
    st.session_state.input_data = {}

# ========================= DEMO USERS =========================
USERS = {
    "student": {"password": "student123", "role": "Student", "name": "Rahul Kumar"},
    "parent":  {"password": "parent123",  "role": "Parent",  "name": "Mr. Sharma"},
    "demo":    {"password": "demo",        "role": "Student", "name": "Demo User"},
}

# ========================= LOAD MODEL (SAFE) =========================
@st.cache_resource
def load_model():
    try:
        model   = joblib.load("student_model.pkl")
        columns = joblib.load("model_columns.pkl")
        return model, columns, True
    except Exception:
        return None, None, False

model, columns, model_loaded = load_model()

# ========================= HELPER: GRADE =========================
def get_grade(score):
    if score >= 90: return "A+", "🏆", "#00E676"
    if score >= 80: return "A",  "⭐", "#00D4FF"
    if score >= 70: return "B",  "👍", "#1B4FD8"
    if score >= 60: return "C",  "📚", "#FFB800"
    if score >= 50: return "D",  "⚠️", "#FF8800"
    return "F", "❌", "#FF4444"

# ========================= HELPER: SUGGESTIONS =========================
def get_suggestions(data, score):
    tips = []
    if data.get("Hours_Studied", 0) < 5:
        tips.append(("warn", "📖 Roz kam se kam 5-6 ghante padhne ki koshish karo — consistency sabse zaroori hai."))
    if data.get("Attendance", 0) < 75:
        tips.append(("warn", "🏫 Attendance 75% se zyada rakhna bahut zaroori hai — class miss mat karo."))
    if data.get("Sleep_Hours", 0) < 6:
        tips.append(("warn", "😴 Neend 7-8 ghante honi chahiye — kam neend se focus aur memory kamzor hoti hai."))
    if data.get("Motivation_Level") == "Low":
        tips.append(("warn", "💪 Motivation badhao — apna goal likh lo aur har din thodi progress track karo."))
    if data.get("Internet_Access") == "No":
        tips.append(("warn", "🌐 Library ya school ke internet ka use karo — online resources bahut helpful hain."))
    if data.get("Peer_Influence") == "Negative":
        tips.append(("warn", "👥 Positive dosto ke saath waqt bitao — peer influence studies pe bahut asar dalta hai."))
    if data.get("Extracurricular_Activities") == "No":
        tips.append(("good", "🎨 Koi ek extracurricular activity join karo — creativity aur focus dono badhte hain."))
    if data.get("Learning_Resources") == "Low":
        tips.append(("warn", "📚 Better books, YouTube channels ya free online courses explore karo."))
    if score >= 80:
        tips.append(("good", "🌟 Excellent performance! Apna level maintain karo aur doosron ki bhi help karo."))
    elif score >= 60:
        tips.append(("good", "📈 Accha kar rahe ho! Thodi aur mehnat se aap top pe aa sakte ho."))
    else:
        tips.append(("warn", "🎯 Abhi mushkil lag raha hai — teacher se personally milkar doubts clear karo."))
    return tips

# ========================= PDF REPORT =========================
def generate_pdf(username, role, score, data):
    grade, emoji, _ = get_grade(score)
    tips = get_suggestions(data, score)
    
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_fill_color(13, 27, 42)
    pdf.rect(0, 0, 210, 40, 'F')
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(0, 15, "", ln=True)
    pdf.cell(0, 15, "  EduPredict Pro - Student Report", ln=True)
    pdf.set_text_color(0, 0, 0)
    
    # Info
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(50, 50, 80)
    pdf.cell(0, 10, f"Name: {username}   |   Role: {role}   |   Date: {datetime.now().strftime('%d %b %Y')}", ln=True)
    pdf.ln(5)
    
    # Score Box
    pdf.set_fill_color(27, 79, 216)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Helvetica", "B", 36)
    pdf.cell(0, 25, f"  Predicted Score: {score}/100   Grade: {grade}", fill=True, ln=True)
    pdf.ln(8)
    
    # Input Summary
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Student Profile Summary", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.set_fill_color(240, 244, 255)
    fields = [
        ("Hours Studied",          data.get("Hours_Studied", "-")),
        ("Attendance (%)",         data.get("Attendance", "-")),
        ("Previous Score",         data.get("Previous_Scores", "-")),
        ("Sleep Hours",            data.get("Sleep_Hours", "-")),
        ("Motivation Level",       data.get("Motivation_Level", "-")),
        ("Teacher Quality",        data.get("Teacher_Quality", "-")),
        ("School Type",            data.get("School_Type", "-")),
        ("Internet Access",        data.get("Internet_Access", "-")),
        ("Family Income",          data.get("Family_Income", "-")),
        ("Parental Involvement",   data.get("Parental_Involvement", "-")),
        ("Peer Influence",         data.get("Peer_Influence", "-")),
        ("Learning Resources",     data.get("Learning_Resources", "-")),
        ("Extracurricular",        data.get("Extracurricular_Activities", "-")),
    ]
    for i, (k, v) in enumerate(fields):
        fill = i % 2 == 0
        pdf.set_fill_color(240, 244, 255) if fill else pdf.set_fill_color(255, 255, 255)
        pdf.cell(95, 7, f"  {k}", border=0, fill=True)
        pdf.cell(95, 7, f"  {v}", border=0, fill=fill, ln=True)
    pdf.ln(8)
    
    # Suggestions
    pdf.set_font("Helvetica", "B", 13)
    pdf.cell(0, 8, "Personalized Suggestions", ln=True)
    pdf.set_font("Helvetica", "", 10)
    for kind, tip in tips:
        clean_tip = tip.encode('latin-1', 'replace').decode('latin-1')
        pdf.set_fill_color(230, 255, 240) if kind == "good" else pdf.set_fill_color(255, 248, 220)
        pdf.multi_cell(0, 7, f"  {clean_tip}", fill=True)
        pdf.ln(1)
    
    # Footer
    pdf.set_y(-20)
    pdf.set_font("Helvetica", "I", 9)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "EduPredict Pro | AI-Powered Student Analytics", align="C")
    
    return pdf.output(dest='S').encode('latin-1')

# ========================= MATPLOTLIB CHARTS =========================
def plot_radar(data, score):
    labels = ['Study Hours', 'Attendance', 'Sleep', 'Prev Score', 'Score']
    vals = [
        min(data.get("Hours_Studied", 0) / 10, 1) * 100,
        data.get("Attendance", 0),
        data.get("Sleep_Hours", 0) / 12 * 100,
        data.get("Previous_Scores", 0),
        score
    ]
    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    vals_plot = vals + [vals[0]]
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(5, 5), subplot_kw=dict(polar=True))
    fig.patch.set_facecolor('#1A2744')
    ax.set_facecolor('#0D1B2A')
    ax.plot(angles, vals_plot, 'o-', linewidth=2, color='#00D4FF')
    ax.fill(angles, vals_plot, alpha=0.25, color='#1B4FD8')
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels, color='#8899AA', fontsize=9)
    ax.set_ylim(0, 100)
    ax.tick_params(colors='#8899AA')
    ax.grid(color='#1B4FD8', alpha=0.3)
    ax.spines['polar'].set_color('#1B4FD8')
    ax.set_yticklabels(['20','40','60','80','100'], color='#8899AA', fontsize=7)
    ax.set_title("Performance Radar", color='white', fontsize=11, pad=15, fontweight='bold')
    plt.tight_layout()
    return fig

def plot_gauge(score):
    fig, ax = plt.subplots(figsize=(5, 3))
    fig.patch.set_facecolor('#1A2744')
    ax.set_facecolor('#1A2744')
    ax.set_xlim(0, 10); ax.set_ylim(0, 5)
    ax.axis('off')
    
    zones = [(0,40,'#FF4444'),(40,60,'#FF8800'),(60,75,'#FFB800'),(75,90,'#1B4FD8'),(90,100,'#00E676')]
    for lo, hi, col in zones:
        theta1 = 180 - (lo / 100 * 180)
        theta2 = 180 - (hi / 100 * 180)
        patch = mpatches.Wedge((5, 0.5), 3.5, theta2, theta1, width=1.2,
                                facecolor=col, alpha=0.85)
        ax.add_patch(patch)
    
    angle = np.radians(180 - (score / 100 * 180))
    ax.annotate('', xy=(5 + 3 * np.cos(angle), 0.5 + 3 * np.sin(angle)),
                xytext=(5, 0.5),
                arrowprops=dict(arrowstyle='->', color='white', lw=3))
    ax.text(5, 2.2, f"{score}", ha='center', fontsize=32, fontweight='bold', color='white')
    ax.text(5, 1.5, "Predicted Score", ha='center', fontsize=10, color='#8899AA')
    ax.set_title("Score Gauge", color='white', fontsize=11, fontweight='bold')
    plt.tight_layout()
    return fig

def plot_bar_comparison(score):
    fig, ax = plt.subplots(figsize=(5, 3.5))
    fig.patch.set_facecolor('#1A2744')
    ax.set_facecolor('#0D1B2A')
    categories = ['Class Avg\n(Estimated)', 'Your Score', 'Top Scorer\n(Estimated)']
    values = [62, score, 94]
    colors = ['#1B4FD8', '#00D4FF', '#FFB800']
    bars = ax.bar(categories, values, color=colors, width=0.5, edgecolor='none', zorder=3)
    for bar, val in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                str(val), ha='center', fontsize=12, color='white', fontweight='bold')
    ax.set_ylim(0, 110)
    ax.set_ylabel("Score", color='#8899AA', fontsize=9)
    ax.tick_params(colors='#8899AA', labelsize=9)
    ax.spines[:].set_color('#1B4FD8')
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)
    ax.grid(axis='y', color='#1B4FD8', alpha=0.2, zorder=0)
    ax.set_title("Score Comparison", color='white', fontsize=11, fontweight='bold')
    plt.tight_layout()
    return fig

# ========================= LOGIN PAGE =========================
def login_page():
    st.markdown("""
    <div class="hero-header">
        <div class="hero-title">🎓 EduPredict Pro</div>
        <div class="hero-sub">AI-Powered Student Performance Predictor & Analyzer</div>
    </div>
    """, unsafe_allow_html=True)
    
    _, col, _ = st.columns([1, 1.2, 1])
    with col:
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        st.markdown('<div class="section-label">Login Karein</div>', unsafe_allow_html=True)
        st.markdown("#### Apna Role Chunein")
        role = st.radio("", ["🎒 Student", "👨‍👩‍👧 Parent"], horizontal=True, label_visibility="collapsed")
        role_clean = "Student" if "Student" in role else "Parent"
        
        st.markdown("---")
        username = st.text_input("👤 Username", placeholder="student / parent / demo")
        password = st.text_input("🔑 Password", type="password", placeholder="Apna password dalein")
        
        st.markdown("")
        if st.button("🚀 Login Karein", use_container_width=True):
            if username in USERS and USERS[username]["password"] == password:
                st.session_state.logged_in = True
                st.session_state.role = role_clean
                st.session_state.username = USERS[username]["name"]
                st.rerun()
            else:
                st.error("❌ Galat username ya password!")
        
        st.markdown("---")
        st.markdown("""
        <div style='font-size:0.78rem; color:#8899AA; text-align:center;'>
        <b>Demo Credentials:</b><br>
        Student: <code>student</code> / <code>student123</code><br>
        Parent: <code>parent</code> / <code>parent123</code><br>
        Quick: <code>demo</code> / <code>demo</code>
        </div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# ========================= MAIN APP =========================
def main_app():
    # Top nav
    c1, c2, c3 = st.columns([3, 1, 0.5])
    with c1:
        st.markdown(f"""
        <div class="hero-header" style="padding:1.2rem 1.5rem; text-align:left; margin-bottom:1rem;">
            <span style="font-size:1.5rem; font-weight:800;">🎓 EduPredict Pro</span>
            <span style="margin-left:1rem; font-size:0.85rem; color:rgba(255,255,255,0.6);">
            {'🎒 Student' if st.session_state.role == 'Student' else '👨‍👩‍👧 Parent'} — {st.session_state.username}
            </span>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        if st.button("🚪 Logout"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    if not model_loaded:
        st.warning("⚠️ Model files (student_model.pkl, model_columns.pkl) nahi mile. Demo mode mein chal raha hai — random score generate hoga.", icon="⚠️")
    
    tab1, tab2 = st.tabs(["📝 Score Predict Karein", "📊 Report & Analysis"])
    
    # ===================== TAB 1: INPUT =====================
    with tab1:
        st.markdown('<div class="section-label">Student Information Fill Karein</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("##### 📊 Academic Details")
            hours      = st.number_input("⏰ Hours Studied (daily)", 0.0, 24.0, 5.0, 0.5)
            attendance = st.number_input("🏫 Attendance (%)", 0.0, 100.0, 80.0, 1.0)
            previous   = st.number_input("📜 Previous Score (0-100)", 0.0, 100.0, 65.0, 1.0)
            sleep      = st.number_input("😴 Sleep Hours", 0.0, 12.0, 7.0, 0.5)
            motivation = st.selectbox("💪 Motivation Level", ["Low", "Medium", "High"], index=1)
            teacher    = st.selectbox("👨‍🏫 Teacher Quality", ["Poor", "Average", "Good"], index=1)
            peer       = st.selectbox("👥 Peer Influence", ["Negative", "Neutral", "Positive"], index=1)
        
        with col2:
            st.markdown("##### 🏠 Background Details")
            school     = st.selectbox("🏫 School Type", ["Public", "Private"])
            internet   = st.selectbox("🌐 Internet Access", ["Yes", "No"])
            income     = st.selectbox("💰 Family Income", ["Low", "Medium", "High"], index=1)
            parent     = st.selectbox("👪 Parental Involvement", ["Low", "Medium", "High"], index=1)
            education  = st.selectbox("🎓 Parent Education Level", ["School", "College"])
            resources  = st.selectbox("📚 Learning Resources", ["Low", "Medium", "High"], index=1)
            activities = st.selectbox("⚽ Extracurricular Activities", ["Yes", "No"])
        
        st.markdown("---")
        if st.button("🔮 Score Predict Karein!", use_container_width=True):
            input_data = {
                "Hours_Studied": hours,
                "Attendance": attendance,
                "Previous_Scores": previous,
                "Sleep_Hours": sleep,
                "Motivation_Level": motivation,
                "Teacher_Quality": teacher,
                "School_Type": school,
                "Internet_Access": internet,
                "Family_Income": income,
                "Parental_Involvement": parent,
                "Parental_Education_Level": education,
                "Peer_Influence": peer,
                "Learning_Resources": resources,
                "Extracurricular_Activities": activities
            }
            
            with st.spinner("🧠 AI analyze kar raha hai..."):
                if model_loaded:
                    df = pd.DataFrame([input_data])
                    df = pd.get_dummies(df)
                    df = df.reindex(columns=columns, fill_value=0)
                    raw = model.predict(df)[0]
                    score = int(round(max(40, min(100, raw))))
                else:
                    # Demo mode
                    base = previous * 0.4 + hours * 3 + attendance * 0.2 + sleep * 1.5
                    score = int(round(max(40, min(100, base + np.random.randint(-3, 3)))))
            
            st.session_state.final_score   = score
            st.session_state.input_data    = input_data
            st.session_state.prediction_done = True
            
            grade, emoji, color = get_grade(score)
            st.markdown(f"""
            <div class="score-badge">
                <div class="score-big">{emoji} {score}</div>
                <div class="score-lbl">Predicted Exam Score — Grade {grade}</div>
            </div>
            """, unsafe_allow_html=True)
            
            # Quick metrics
            st.markdown('<div class="metric-row">', unsafe_allow_html=True)
            st.markdown(f"""
            <div class="metric-card"><div class="metric-val c-cyan">{score}</div><div class="metric-lbl">Predicted Score</div></div>
            <div class="metric-card"><div class="metric-val c-gold">{grade}</div><div class="metric-lbl">Grade</div></div>
            <div class="metric-card"><div class="metric-val c-green">{int(attendance)}%</div><div class="metric-lbl">Attendance</div></div>
            <div class="metric-card"><div class="metric-val c-{'green' if score>=60 else 'red'}">{int(hours)}h</div><div class="metric-lbl">Daily Study</div></div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            
            # Progress bar
            st.markdown("**Score Progress**")
            st.progress(score / 100)
            
            st.success("✅ Prediction complete! 'Report & Analysis' tab mein jaiye graphs aur suggestions ke liye.")
    
    # ===================== TAB 2: REPORT =====================
    with tab2:
        if not st.session_state.prediction_done:
            st.info("ℹ️ Pehle Tab 1 mein score predict karein, phir yahan aayein.")
            return
        
        score = st.session_state.final_score
        data  = st.session_state.input_data
        grade, emoji, color = get_grade(score)
        
        st.markdown(f"""
        <div class="score-badge">
            <div class="score-big">{emoji} {score}/100</div>
            <div class="score-lbl">Grade: {grade} — {st.session_state.username} ({st.session_state.role})</div>
        </div>
        """, unsafe_allow_html=True)
        
        # ---- CHARTS ----
        st.markdown('<div class="section-label">Visual Analytics</div>', unsafe_allow_html=True)
        g1, g2, g3 = st.columns(3)
        with g1:
            fig = plot_gauge(score)
            st.pyplot(fig, use_container_width=True)
            plt.close()
        with g2:
            fig = plot_radar(data, score)
            st.pyplot(fig, use_container_width=True)
            plt.close()
        with g3:
            fig = plot_bar_comparison(score)
            st.pyplot(fig, use_container_width=True)
            plt.close()
        
        # ---- SUGGESTIONS ----
        st.markdown("---")
        st.markdown('<div class="section-label">Personalized Suggestions</div>', unsafe_allow_html=True)
        tips = get_suggestions(data, score)
        for kind, tip in tips:
            css_class = "sug-card " + kind
            st.markdown(f'<div class="{css_class}">{tip}</div>', unsafe_allow_html=True)
        
        # ---- DOWNLOAD ----
        st.markdown("---")
        st.markdown('<div class="section-label">Report Download Karein</div>', unsafe_allow_html=True)
        
        dc1, dc2 = st.columns(2)
        with dc1:
            # CSV
            csv_data = {
                "Name": [st.session_state.username],
                "Role": [st.session_state.role],
                "Predicted Score": [score],
                "Grade": [grade],
                "Date": [datetime.now().strftime("%d %b %Y")],
                **{k: [v] for k, v in data.items()}
            }
            csv_df = pd.DataFrame(csv_data)
            csv_bytes = csv_df.to_csv(index=False).encode()
            st.download_button(
                "📥 CSV Report Download",
                data=csv_bytes,
                file_name=f"EduPredict_{st.session_state.username.replace(' ','_')}_{score}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with dc2:
            # PDF
            try:
                pdf_bytes = generate_pdf(st.session_state.username, st.session_state.role, score, data)
                st.download_button(
                    "📄 PDF Report Download",
                    data=pdf_bytes,
                    file_name=f"EduPredict_{st.session_state.username.replace(' ','_')}_{score}.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.info("PDF ke liye `pip install fpdf2` karein terminal mein.")

# ========================= ROUTING =========================
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
