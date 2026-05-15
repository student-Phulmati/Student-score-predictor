# ==========================================
# IMPORT LIBRARIES
# ==========================================
import streamlit as st
import joblib
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime

# ==========================================
# PAGE CONFIG
# ==========================================
st.set_page_config(
    page_title="Student Performance Predictor",
    page_icon="🎓",
    layout="wide"
)

# ==========================================
# CUSTOM CSS
# ==========================================
st.markdown(
    """
    <style>
    .main {
        background-color: #f5f7fa;
    }

    .title {
        text-align: center;
        font-size: 40px;
        color: #1f77b4;
        font-weight: bold;
    }

    .subtitle {
        text-align: center;
        font-size: 18px;
        color: gray;
        margin-bottom: 30px;
    }

    .stButton>button {
        width: 100%;
        background-color: #1f77b4;
        color: white;
        font-size: 18px;
        border-radius: 10px;
        height: 50px;
    }

    .report-box {
        background-color: white;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0px 0px 10px rgba(0,0,0,0.1);
    }
    </style>
    """,
    unsafe_allow_html=True
)

# ==========================================
# LOAD MODEL
# ==========================================
model = joblib.load("student_model.pkl")
columns = joblib.load("model_columns.pkl")

# ==========================================
# LOGIN PAGE
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

if not st.session_state.logged_in:

    st.markdown("<div class='title'>🎓 Student Performance Predictor</div>", unsafe_allow_html=True)
    st.markdown("<div class='subtitle'>AI Based Exam Score Prediction System</div>", unsafe_allow_html=True)

    role = st.selectbox(
        "Login As",
        ["Student", "Parent"]
    )

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username != "" and password != "":
            st.session_state.logged_in = True
            st.session_state.role = role
            st.success(f"Welcome {username} ({role})")
            st.rerun()
        else:
            st.error("Please enter username and password")

# ==========================================
# MAIN APP
# ==========================================
else:

    # HEADER
    st.markdown("<div class='title'>📊 Student Score Predictor Dashboard</div>", unsafe_allow_html=True)

    st.write(f"### Logged in as: {st.session_state.role}")

    # ==========================================
    # SIDEBAR
    # ==========================================
    st.sidebar.title("📌 Navigation")

    menu = st.sidebar.radio(
        "Go To",
        ["Prediction", "About Project"]
    )

    if menu == "About Project":
        st.header("📖 About Project")
        st.write(
            """
            This AI-based application predicts student exam scores
            using Machine Learning.

            Features Included:
            - Student & Parent Login
            - Score Prediction
            - Performance Graph
            - Downloadable Report
            - Suggestions & Improvement Tips
            """
        )

    elif menu == "Prediction":

        # ==========================================
        # STUDENT DETAILS
        # ==========================================
        st.subheader("👤 Student Information")

        col1, col2 = st.columns(2)

        with col1:
            student_name = st.text_input("Student Name")
            student_class = st.text_input("Class")
            school_name = st.text_input("School Name")

        with col2:
            age = st.number_input("Age", 5, 30)
            gender = st.selectbox("Gender", ["Male", "Female"])
            roll_no = st.text_input("Roll Number")

        st.divider()

        # ==========================================
        # INPUT SECTION
        # ==========================================
        st.subheader("📚 Academic Details")

        col1, col2 = st.columns(2)

        with col1:
            hours = st.slider("Hours Studied", 0.0, 24.0, 5.0)
            attendance = st.slider("Attendance (%)", 0.0, 100.0, 75.0)
            previous = st.slider("Previous Score", 0.0, 100.0, 60.0)
            sleep = st.slider("Sleep Hours", 0.0, 12.0, 7.0)

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

        # ==========================================
        # PREDICTION BUTTON
        # ==========================================
        if st.button("🎯 Predict Score"):

            # ==========================================
            # CREATE INPUT DATA
            # ==========================================
            data = {
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

            # Convert to DataFrame
            input_df = pd.DataFrame([data])

            # Encoding
            input_df = pd.get_dummies(input_df)

            # Match columns
            input_df = input_df.reindex(columns=columns, fill_value=0)

            # ==========================================
            # PREDICTION
            # ==========================================
            prediction = model.predict(input_df)

            final_score = max(40, min(100, prediction[0]))
            final_score = int(round(final_score))

            # ==========================================
            # RESULT SECTION
            # ==========================================
            st.success(f"🎉 Predicted Exam Score: {final_score}")

            # ==========================================
            # PERFORMANCE LEVEL
            # ==========================================
            if final_score >= 85:
                performance = "Excellent"
                suggestion = "Outstanding performance! Keep maintaining consistency."

            elif final_score >= 70:
                performance = "Very Good"
                suggestion = "Good work! Focus more on revision and practice."

            elif final_score >= 50:
                performance = "Average"
                suggestion = "Need improvement in study hours and consistency."

            else:
                performance = "Poor"
                suggestion = "Focus on daily study routine and guidance from teachers."

            # ==========================================
            # REPORT CARD
            # ==========================================
            st.subheader("📋 Student Report")

            st.markdown("<div class='report-box'>", unsafe_allow_html=True)

            st.write(f"### 👤 Name: {student_name}")
            st.write(f"### 🏫 School: {school_name}")
            st.write(f"### 🎯 Predicted Score: {final_score}")
            st.write(f"### 📈 Performance: {performance}")
            st.write(f"### 💡 Suggestion: {suggestion}")

            st.markdown("</div>", unsafe_allow_html=True)

            # ==========================================
            # GRAPH
            # ==========================================
            st.subheader("📊 Performance Analysis")

            chart_data = {
                "Study Factors": [
                    "Hours Studied",
                    "Attendance",
                    "Previous Score",
                    "Sleep Hours",
                    "Predicted Score"
                ],
                "Values": [
                    hours,
                    attendance,
                    previous,
                    sleep * 10,
                    final_score
                ]
            }

            chart_df = pd.DataFrame(chart_data)

            fig, ax = plt.subplots(figsize=(8, 4))
            ax.bar(chart_df["Study Factors"], chart_df["Values"])
            plt.xticks(rotation=10)
            st.pyplot(fig)

            # ==========================================
            # DOWNLOAD REPORT
            # ==========================================
            report = f"""
            STUDENT PERFORMANCE REPORT
            ==================================

            Date: {datetime.now()}

            Student Name: {student_name}
            Roll Number: {roll_no}
            Class: {student_class}
            School Name: {school_name}

            Predicted Score: {final_score}
            Performance Level: {performance}

            Suggestion:
            {suggestion}

            STUDY DETAILS
            -----------------------------
            Hours Studied: {hours}
            Attendance: {attendance}
            Previous Score: {previous}
            Sleep Hours: {sleep}
            Motivation Level: {motivation}
            Teacher Quality: {teacher}
            Internet Access: {internet}
            Learning Resources: {resources}
            """

            st.download_button(
                label="📥 Download Report",
                data=report,
                file_name="student_report.txt",
                mime="text/plain"
            )

    # ==========================================
    # LOGOUT BUTTON
    # ==========================================
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()
