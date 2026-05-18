import streamlit as st
import joblib
import pandas as pd
import numpy as np
import hashlib
import json
import os
from datetime import datetime
import io

# PDF
from reportlab.lib.pagesizes import letter
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import inch

# =========================================
# PAGE CONFIG
# =========================================
st.set_page_config(
    page_title="Student Performance Analytics",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================
# DATABASE FILES
# =========================================
USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"

# =========================================
# DATABASE FUNCTIONS
# =========================================
def load_users():
    if os.path.exists(USER_DB_FILE):
        with open(USER_DB_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_DB_FILE, "w") as f:
        json.dump(users, f, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return {}

def save_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# =========================================
# UTILITY FUNCTIONS
# =========================================
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def calculate_age(birth_date):
    today = datetime.now()
    age = today.year - birth_date.year

    if (
        today.month < birth_date.month
        or (
            today.month == birth_date.month
            and today.day < birth_date.day
        )
    ):
        age -= 1

    return age

# =========================================
# PDF REPORT
# =========================================
def generate_pdf_report(
    username,
    final_score,
    user_data,
    hours,
    attendance,
    previous,
    sleep,
    recommendations
):

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        topMargin=0.5 * inch,
        bottomMargin=0.5 * inch
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Heading1"],
        fontSize=24,
        textColor=colors.HexColor("#2563eb"),
        alignment=1,
        spaceAfter=20
    )

    heading_style = ParagraphStyle(
        "Heading",
        parent=styles["Heading2"],
        fontSize=15,
        textColor=colors.HexColor("#1e3a8a"),
        spaceAfter=10
    )

    normal_style = ParagraphStyle(
        "Normal",
        parent=styles["BodyText"],
        fontSize=10,
        leading=18
    )

    story = []

    story.append(
        Paragraph(
            "Student Performance Analytics Report",
            title_style
        )
    )

    story.append(Spacer(1, 0.2 * inch))

    # Student Details
    story.append(Paragraph("Student Details", heading_style))

    details = [
        ["Field", "Value"],
        ["Name", user_data.get("full_name", username)],
        ["Username", username],
        ["Grade", user_data.get("grade", "N/A")],
        ["School", user_data.get("school", "N/A")],
        ["Generated On", datetime.now().strftime("%d-%m-%Y %H:%M")]
    ]

    table = Table(details, colWidths=[2.5 * inch, 3 * inch])

    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2563eb")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#eff6ff")),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#bfdbfe")),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
    ]))

    story.append(table)
    story.append(Spacer(1, 0.2 * inch))

    # Prediction
    story.append(Paragraph("Prediction Summary", heading_style))

    prediction_text = f"""
    Predicted Score: <b>{final_score}/100</b>
    """

    story.append(Paragraph(prediction_text, normal_style))
    story.append(Spacer(1, 0.15 * inch))

    # Inputs
    input_data = [
        ["Metric", "Value"],
        ["Study Hours", f"{hours} hrs"],
        ["Attendance", f"{attendance}%"],
        ["Previous Score", f"{previous}"],
        ["Sleep Hours", f"{sleep} hrs"],
    ]

    input_table = Table(input_data, colWidths=[2.5 * inch, 3 * inch])

    input_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
        ("GRID", (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
    ]))

    story.append(input_table)
    story.append(Spacer(1, 0.2 * inch))

    # Recommendations
    story.append(Paragraph("Recommendations", heading_style))

    if recommendations:
        for r in recommendations:
            story.append(Paragraph(f"• {r}", normal_style))
    else:
        story.append(
            Paragraph(
                "Excellent performance. Keep maintaining consistency.",
                normal_style
            )
        )

    doc.build(story)

    buffer.seek(0)

    return buffer

# =========================================
# SESSION STATE
# =========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if "username" not in st.session_state:
    st.session_state.username = ""

if "theme" not in st.session_state:
    st.session_state.theme = "dark"

# =========================================
# PROFESSIONAL CSS
# =========================================
light_css = """
<style>

.stApp {
    background: #f1f5f9;
    color: #0f172a;
}

.main .block-container {
    padding-top: 1.5rem;
}

[data-testid="stSidebar"] {
    background: white;
    border-right: 1px solid #e2e8f0;
}

.card {
    background: white;
    border-radius: 18px;
    padding: 1.2rem;
    border: 1px solid #e2e8f0;
    box-shadow: 0 4px 14px rgba(0,0,0,0.05);
}

.metric-card {
    background: linear-gradient(135deg,#2563eb,#1d4ed8);
    padding: 1rem;
    border-radius: 18px;
    text-align:center;
    color:white;
}

.metric-title {
    font-size: 0.8rem;
    opacity: 0.9;
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
}

.stButton>button {
    background: linear-gradient(135deg,#2563eb,#1d4ed8);
    color:white;
    border:none;
    border-radius:12px;
    font-weight:600;
    height:3rem;
}

.stButton>button:hover {
    background: linear-gradient(135deg,#1d4ed8,#1e40af);
    color:white;
}

.top-right {
    position: fixed;
    top: 10px;
    right: 15px;
    z-index: 999;
}

hr {
    margin-top: 1rem;
    margin-bottom: 1rem;
}

</style>
"""

dark_css = """
<style>

.stApp {
    background: #020617;
    color: white;
}

[data-testid="stSidebar"] {
    background: #0f172a;
}

.card {
    background: #0f172a;
    border-radius: 18px;
    padding: 1.2rem;
    border: 1px solid #1e293b;
}

.metric-card {
    background: linear-gradient(135deg,#06b6d4,#2563eb);
    padding: 1rem;
    border-radius: 18px;
    text-align:center;
    color:white;
}

.metric-title {
    font-size: 0.8rem;
    opacity: 0.9;
}

.metric-value {
    font-size: 2rem;
    font-weight: bold;
}

.stButton>button {
    background: linear-gradient(135deg,#06b6d4,#2563eb);
    color:white;
    border:none;
    border-radius:12px;
    font-weight:600;
    height:3rem;
}

.stButton>button:hover {
    background: linear-gradient(135deg,#0891b2,#1d4ed8);
    color:white;
}

.top-right {
    position: fixed;
    top: 10px;
    right: 15px;
    z-index: 999;
}

</style>
"""

# =========================================
# APPLY THEME
# =========================================
def apply_theme():

    if st.session_state.theme == "dark":
        st.markdown(dark_css, unsafe_allow_html=True)
    else:
        st.markdown(light_css, unsafe_allow_html=True)

# =========================================
# THEME TOGGLE
# =========================================
def theme_toggle():

    st.markdown(
        '<div class="top-right">',
        unsafe_allow_html=True
    )

    icon = "☀️" if st.session_state.theme == "dark" else "🌙"
    text = "Light Mode" if st.session_state.theme == "dark" else "Dark Mode"

    if st.button(f"{icon} {text}"):

        if st.session_state.theme == "dark":
            st.session_state.theme = "light"
        else:
            st.session_state.theme = "dark"

        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =========================================
# LOAD MODEL
# =========================================
@st.cache_resource
def load_models():

    model = joblib.load("student_model.pkl")
    columns = joblib.load("model_columns.pkl")

    return model, columns

# =========================================
# AUTH PAGE
# =========================================
def show_auth_page():

    apply_theme()
    theme_toggle()

    users = load_users()

    st.markdown(
        """
        <div style="text-align:center;padding-top:30px;">
            <h1>🎓 Student Performance Analytics</h1>
            <p>Professional AI Based Score Prediction System</p>
        </div>
        """,
        unsafe_allow_html=True
    )

    col1, col2, col3 = st.columns([1,1.4,1])

    with col2:

        st.markdown('<div class="card">', unsafe_allow_html=True)

        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):

            if username in users and users[username]["password"] == hash_password(password):

                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()

            else:
                st.error("Invalid username or password")

        st.markdown("---")

        st.subheader("Create Account")

        new_user = st.text_input("Create Username")
        new_pass = st.text_input("Create Password", type="password")
        full_name = st.text_input("Full Name")
        grade = st.selectbox(
            "Grade",
            ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
        )
        school = st.text_input("School Name")

        if st.button("Create Account", use_container_width=True):

            if new_user in users:
                st.warning("Username already exists")

            else:

                users[new_user] = {
                    "password": hash_password(new_pass),
                    "full_name": full_name,
                    "grade": grade,
                    "school": school
                }

                save_users(users)

                st.success("Account Created Successfully")

        st.markdown('</div>', unsafe_allow_html=True)

# =========================================
# MAIN APP
# =========================================
def show_main_app():

    apply_theme()
    theme_toggle()

    model, columns = load_models()

    users = load_users()
    user_data = users.get(st.session_state.username, {})

    history = load_history()

    # SIDEBAR
    with st.sidebar:

        st.title("👤 Profile")

        st.write(f"### {user_data.get('full_name')}")

        st.write(f"**Grade:** {user_data.get('grade')}")
        st.write(f"**School:** {user_data.get('school')}")

        st.markdown("---")

        if st.button("Logout", use_container_width=True):

            st.session_state.logged_in = False
            st.session_state.username = ""

            st.rerun()

    # TITLE
    st.title("🎓 Student Performance Analytics Dashboard")

    st.markdown(
        """
        Predict student exam performance using AI-powered analytics.
        """,
        unsafe_allow_html=True
    )

    # =========================================
    # INPUTS
    # =========================================
    col1, col2 = st.columns(2)

    with col1:

        hours = st.slider("Hours Studied", 0.0, 24.0, 5.0)

        attendance = st.slider("Attendance (%)", 0.0, 100.0, 75.0)

        previous = st.slider("Previous Score", 0.0, 100.0, 60.0)

        sleep = st.slider("Sleep Hours", 0.0, 12.0, 7.0)

    with col2:

        motivation = st.selectbox(
            "Motivation Level",
            ["Low", "Medium", "High"]
        )

        teacher = st.selectbox(
            "Teacher Quality",
            ["Poor", "Average", "Good"]
        )

        resources = st.selectbox(
            "Learning Resources",
            ["Low", "Medium", "High"]
        )

        internet = st.selectbox(
            "Internet Access",
            ["Yes", "No"]
        )

    # =========================================
    # PREDICTION
    # =========================================
    if st.button("Predict Student Score", use_container_width=True):

        data = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Previous_Scores": previous,
            "Sleep_Hours": sleep,
            "Motivation_Level": motivation,
            "Teacher_Quality": teacher,
            "Learning_Resources": resources,
            "Internet_Access": internet
        }

        input_df = pd.DataFrame([data])

        input_df = pd.get_dummies(input_df)

        input_df = input_df.reindex(
            columns=columns,
            fill_value=0
        )

        prediction = model.predict(input_df)

        final_score = int(round(prediction[0]))

        final_score = max(40, min(100, final_score))

        # SAVE HISTORY
        if st.session_state.username not in history:
            history[st.session_state.username] = []

        history[st.session_state.username].append(final_score)

        save_history(history)

        user_history = history[st.session_state.username]

        # =========================================
        # RESULT CARD
        # =========================================
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-title">
                    PREDICTED EXAM SCORE
                </div>

                <div class="metric-value">
                    {final_score}/100
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )

        # =========================================
        # STATUS
        # =========================================
        if final_score >= 85:
            st.success("🎉 Excellent Performance")

        elif final_score >= 70:
            st.info("📈 Good Performance")

        elif final_score >= 55:
            st.warning("⚠️ Average Performance")

        else:
            st.error("❌ Needs Improvement")

        # =========================================
        # ANALYTICS
        # =========================================
        st.markdown("## 📊 Performance Analytics")

        col_a, col_b, col_c, col_d = st.columns(4)

        avg_score = int(np.mean(user_history))
        highest = max(user_history)
        lowest = min(user_history)

        improvement = (
            user_history[-1] - user_history[0]
            if len(user_history) > 1
            else 0
        )

        metrics = [
            (col_a, avg_score, "Average"),
            (col_b, highest, "Highest"),
            (col_c, lowest, "Lowest"),
            (col_d, improvement, "Improvement"),
        ]

        for col, val, label in metrics:

            with col:

                st.markdown(
                    f"""
                    <div class="card">
                        <h2 style="text-align:center;">
                            {val}
                        </h2>

                        <p style="text-align:center;">
                            {label}
                        </p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )

        # =========================================
        # USEFUL GRAPHS
        # =========================================
        st.markdown("## 📈 Score Trend Analysis")

        chart_df = pd.DataFrame({
            "Attempt": list(range(1, len(user_history)+1)),
            "Score": user_history
        })

        st.line_chart(
            chart_df.set_index("Attempt"),
            use_container_width=True
        )

        st.markdown("## 📊 Score Distribution")

        distribution_df = pd.DataFrame({
            "Score": user_history
        })

        st.bar_chart(
            distribution_df,
            use_container_width=True
        )

        # =========================================
        # RECOMMENDATIONS
        # =========================================
        st.markdown("## 💡 Smart Recommendations")

        recs = []

        if hours < 6:
            recs.append("Increase study time to 6-8 hours daily.")

        if attendance < 75:
            recs.append("Improve attendance above 80%.")

        if sleep < 7:
            recs.append("Maintain proper sleep schedule.")

        if motivation == "Low":
            recs.append("Set small daily study goals.")

        if teacher == "Poor":
            recs.append("Take additional guidance or tutoring.")

        if resources == "Low":
            recs.append("Use online learning resources.")

        if recs:

            for r in recs:
                st.info(r)

        else:
            st.success("Excellent study habits detected.")

        # =========================================
        # PDF DOWNLOAD
        # =========================================
        pdf = generate_pdf_report(
            st.session_state.username,
            final_score,
            user_data,
            hours,
            attendance,
            previous,
            sleep,
            recs
        )

        st.download_button(
            "📄 Download Professional PDF Report",
            data=pdf,
            file_name="student_report.pdf",
            mime="application/pdf",
            use_container_width=True
        )

# =========================================
# MAIN
# =========================================
if st.session_state.logged_in:
    show_main_app()
else:
    show_auth_page()
