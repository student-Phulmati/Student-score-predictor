# =========================================================
# 🎓 STUDENT SCORE PREDICTOR — PROFESSIONAL AI VERSION
# =========================================================

# =========================
# IMPORT LIBRARIES
# =========================
import streamlit as st
import pandas as pd
import numpy as np
import joblib
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import hashlib
import json
import os

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Student Score Predictor",
    page_icon="🎓",
    layout="wide"
)

# =========================
# CUSTOM CSS
# =========================
st.markdown("""
<style>

.main {
    background: linear-gradient(to right,#03045e,#0077b6);
}

h1,h2,h3 {
    color: white;
}

.stButton>button {
    background: linear-gradient(135deg,#00b4d8,#0077b6);
    color: white;
    border-radius: 10px;
    border: none;
    padding: 10px 20px;
    font-weight: bold;
}

.stButton>button:hover {
    transform: scale(1.03);
    transition: 0.3s;
}

.metric-card {
    background: rgba(255,255,255,0.1);
    padding: 20px;
    border-radius: 15px;
    text-align:center;
    color:white;
}

</style>
""", unsafe_allow_html=True)

# =========================
# LOAD MODEL
# =========================
@st.cache_resource
def load_model():
    model = joblib.load("student_model.pkl")
    columns = joblib.load("model_columns.pkl")
    return model, columns

model, columns = load_model()

# =========================
# SIDEBAR
# =========================
st.sidebar.title("🎓 Navigation")

menu = st.sidebar.radio(
    "Select Page",
    [
        "🏠 Home",
        "📊 Dashboard",
        "📈 Analytics",
        "📄 Reports",
        "💡 AI Suggestions"
    ]
)

# =========================
# HOME PAGE
# =========================
if menu == "🏠 Home":

    st.title("🎓 Student Score Predictor")

    st.markdown("""
    Predict student exam scores using Machine Learning.
    """)

    col1, col2 = st.columns(2)

    with col1:

        hours = st.slider(
            "📚 Hours Studied",
            0.0, 24.0, 5.0
        )

        attendance = st.slider(
            "🏫 Attendance %",
            0, 100, 75
        )

        previous = st.slider(
            "📊 Previous Score",
            0, 100, 60
        )

        sleep = st.slider(
            "😴 Sleep Hours",
            0.0, 12.0, 7.0
        )

    with col2:

        motivation = st.selectbox(
            "🔥 Motivation Level",
            ["Low","Medium","High"]
        )

        internet = st.selectbox(
            "🌐 Internet Access",
            ["Yes","No"]
        )

        parent = st.selectbox(
            "👨‍👩‍👧 Parent Involvement",
            ["Low","Medium","High"]
        )

        resources = st.selectbox(
            "📚 Learning Resources",
            ["Low","Medium","High"]
        )

    # =========================
    # PREDICT BUTTON
    # =========================
    if st.button("🚀 Predict Score"):

        data = {
            "Hours_Studied": hours,
            "Attendance": attendance,
            "Previous_Scores": previous,
            "Sleep_Hours": sleep,
            "Motivation_Level": motivation,
            "Internet_Access": internet,
            "Parental_Involvement": parent,
            "Learning_Resources": resources
        }

        input_df = pd.DataFrame([data])

        # Convert categorical
        input_df = pd.get_dummies(input_df)

        # Match columns
        input_df = input_df.reindex(
            columns=columns,
            fill_value=0
        )

        # Prediction
        prediction = model.predict(input_df)

        final_score = int(round(prediction[0]))

        final_score = max(0, min(100, final_score))

        st.session_state["score"] = final_score

        # =========================
        # RESULT CARD
        # =========================
        st.markdown(f"""
        <div class='metric-card'>
            <h2>Predicted Score</h2>
            <h1>{final_score}/100</h1>
        </div>
        """, unsafe_allow_html=True)

        # =========================
        # SUCCESS MESSAGE
        # =========================
        if final_score >= 85:
            st.success("🌟 Excellent Performance")
            st.balloons()

        elif final_score >= 70:
            st.info("📈 Good Performance")

        elif final_score >= 50:
            st.warning("📚 Average Performance")

        else:
            st.error("⚠️ Needs Improvement")

        # =========================
        # GAUGE CHART
        # =========================
        fig = go.Figure(go.Indicator(
            mode="gauge+number",
            value=final_score,
            title={'text': "Performance"},
            gauge={
                'axis': {'range': [0,100]},
                'bar': {'color': "cyan"},
                'steps': [
                    {'range':[0,50],'color':'red'},
                    {'range':[50,70],'color':'orange'},
                    {'range':[70,85],'color':'yellow'},
                    {'range':[85,100],'color':'green'}
                ]
            }
        ))

        st.plotly_chart(fig, use_container_width=True)

# =========================
# DASHBOARD
# =========================
elif menu == "📊 Dashboard":

    st.title("📊 Student Dashboard")

    data = {
        "Subjects": [
            "Math",
            "Science",
            "English",
            "Computer",
            "Physics"
        ],
        "Scores": [
            78,
            85,
            72,
            90,
            80
        ]
    }

    df = pd.DataFrame(data)

    # =========================
    # BAR CHART
    # =========================
    fig = px.bar(
        df,
        x="Subjects",
        y="Scores",
        title="Subject Wise Scores"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # PIE CHART
    # =========================
    fig2 = px.pie(
        df,
        names="Subjects",
        values="Scores",
        title="Score Distribution"
    )

    st.plotly_chart(fig2, use_container_width=True)

# =========================
# ANALYTICS
# =========================
elif menu == "📈 Analytics":

    st.title("📈 Advanced Analytics")

    np.random.seed(42)

    heat_data = pd.DataFrame(
        np.random.rand(5,5),
        columns=[
            "Hours",
            "Attendance",
            "Sleep",
            "Motivation",
            "Score"
        ]
    )

    # =========================
    # HEATMAP
    # =========================
    fig = px.imshow(
        heat_data.corr(),
        text_auto=True,
        aspect="auto",
        title="Correlation Heatmap"
    )

    st.plotly_chart(fig, use_container_width=True)

    # =========================
    # LINE CHART
    # =========================
    history = pd.DataFrame({
        "Attempt":[1,2,3,4,5],
        "Score":[55,65,72,80,88]
    })

    fig2 = px.line(
        history,
        x="Attempt",
        y="Score",
        markers=True,
        title="Score Improvement"
    )

    st.plotly_chart(fig2, use_container_width=True)

# =========================
# REPORT PAGE
# =========================
elif menu == "📄 Reports":

    st.title("📄 Performance Report")

    if "score" in st.session_state:

        score = st.session_state["score"]

        st.metric(
            "Latest Predicted Score",
            f"{score}/100"
        )

        report = pd.DataFrame({
            "Metric":[
                "Study Hours",
                "Attendance",
                "Sleep"
            ],
            "Value":[
                "6 Hours",
                "85%",
                "7 Hours"
            ]
        })

        st.table(report)

        csv = report.to_csv(index=False)

        st.download_button(
            "⬇️ Download Report",
            csv,
            "student_report.csv",
            "text/csv"
        )

    else:
        st.warning("⚠️ First predict a score")

# =========================
# AI SUGGESTIONS
# =========================
elif menu == "💡 AI Suggestions":

    st.title("💡 AI Study Suggestions")

    suggestions = [
        "📚 Study at least 6 hours daily",
        "😴 Sleep 7-8 hours regularly",
        "🏫 Maintain attendance above 80%",
        "🧠 Revise weak subjects daily",
        "📖 Solve previous year questions",
        "🔥 Stay motivated with small goals",
        "💻 Use online learning platforms",
        "👨‍🏫 Ask teachers when confused"
    ]

    for s in suggestions:
        st.info(s)

# =========================
# FOOTER
# =========================
st.markdown("---")

st.markdown("""
<center>
<h4 style='color:white'>
🎓 Student Score Predictor
</h4>

<p style='color:lightgray'>
Built with Streamlit + Machine Learning
</p>
</center>
""", unsafe_allow_html=True)
