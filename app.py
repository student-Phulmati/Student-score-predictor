
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
from datetime import datetime, date
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.graphics.shapes import Drawing, Line, String

import plotly.graph_objects as go

# =========================================================
# APP CONFIGURATION
# =========================================================
APP_NAME = "AcadraIQ"
TAGLINE = "Smart Student Performance Predictor"

USER_DB_FILE = "users.json"
HISTORY_FILE = "prediction_history.json"
OTP_FILE = "otp_store.json"
PROFILE_PICS_DIR = "profile_pics"

MODEL_FILE = "student_model.pkl"
COLUMNS_FILE = "model_columns.pkl"

# For real email OTP:
# 1. Turn on 2-Step Verification in Gmail.
# 2. Generate a Gmail App Password.
# 3. Put your email and app password below.
EMAIL_SENDER = "your_email@gmail.com"
EMAIL_PASSWORD = "your_gmail_app_password"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# COOLORS PALETTE
# =========================================================
NAVY = "#03045E"
DARK_BLUE = "#023E8A"
BLUE = "#0077B6"
CYAN_DARK = "#0096C7"
CYAN = "#00B4D8"
SKY = "#48CAE4"
LIGHT_SKY = "#90E0EF"
PALE_SKY = "#ADE8F4"
ICE = "#CAF0F8"
WHITE = "#FFFFFF"

# =========================================================
# BASIC HELPERS
# =========================================================
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


def calculate_age(dob_value):
    today = datetime.now().date()
    if isinstance(dob_value, str):
        dob_value = datetime.strptime(dob_value, "%Y-%m-%d").date()
    return today.year - dob_value.year - ((today.month, today.day) < (dob_value.month, dob_value.day))


def save_profile_pic(username, image_bytes):
    with open(os.path.join(PROFILE_PICS_DIR, f"{username}.jpg"), "wb") as f:
        f.write(image_bytes)


def profile_pic_html(username, fallback="🎓"):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" />'
    return fallback


# =========================================================
# OTP FUNCTIONS
# =========================================================
def generate_otp():
    return str(random.randint(100000, 999999))


def store_otp(email, otp):
    data = load_json(OTP_FILE, {})
    data[email] = {
        "otp": otp,
        "timestamp": datetime.now().isoformat(),
        "verified": False
    }
    save_json(OTP_FILE, data)


def verify_otp(email, entered_otp):
    data = load_json(OTP_FILE, {})
    if email not in data:
        return False, "OTP not found. Please request a new OTP."

    record = data[email]
    elapsed = (datetime.now() - datetime.fromisoformat(record["timestamp"])).total_seconds()

    if elapsed > 600:
        return False, "OTP expired. Please request a new OTP."

    if record["otp"] != entered_otp:
        return False, "Invalid OTP. Please try again."

    data[email]["verified"] = True
    save_json(OTP_FILE, data)
    return True, "OTP verified successfully."


def send_otp_email(receiver_email, otp, name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME} OTP Verification Code"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver_email

        html = f"""
        <html>
        <body style="font-family:Arial;background:#03045E;color:white;padding:28px;">
            <div style="max-width:460px;margin:auto;background:#023E8A;border-radius:18px;padding:26px;">
                <h2 style="color:#90E0EF;text-align:center;">{APP_NAME}</h2>
                <p>Hello <b>{name}</b>,</p>
                <p>Your OTP verification code is:</p>
                <div style="font-size:36px;letter-spacing:8px;font-weight:800;color:#CAF0F8;text-align:center;padding:16px;">
                    {otp}
                </div>
                <p>This OTP is valid for 10 minutes.</p>
            </div>
        </body>
        </html>
        """
        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver_email, msg.as_string())

        return True, "OTP sent successfully."
    except Exception as e:
        return False, str(e)


# =========================================================
# SESSION STATE
# =========================================================
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
        "profile_edit_mode": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


init_state()


# =========================================================
# CSS THEME
# =========================================================
def apply_css():
    dark = st.session_state.theme == "dark"
    is_welcome = (not st.session_state.logged_in and st.session_state.auth_page == "welcome")

    if dark:
        app_bg = f"linear-gradient(135deg,{NAVY} 0%,{DARK_BLUE} 35%,{BLUE} 70%,{CYAN_DARK} 100%)"
        sidebar_bg = "rgba(3, 4, 94, 0.96)"
        card_bg = "rgba(255,255,255,0.09)"
        card_border = "rgba(144,224,239,0.28)"
        text_primary = ICE
        text_secondary = PALE_SKY
        muted = LIGHT_SKY
        input_bg = "rgba(3,4,94,0.72)"
        input_text = WHITE
        button_bg = f"linear-gradient(135deg,{BLUE},{CYAN})"
        button_hover = f"linear-gradient(135deg,{CYAN_DARK},{SKY})"
        title_color = ICE
        metric_color = SKY
        profile_bg = "rgba(2,62,138,0.42)"
        rec_bg = "rgba(0,180,216,0.10)"
    else:
        app_bg = f"linear-gradient(135deg,{ICE} 0%,{PALE_SKY} 45%,{LIGHT_SKY} 100%)"
        sidebar_bg = "rgba(255,255,255,0.94)"
        card_bg = "rgba(255,255,255,0.84)"
        card_border = "rgba(0,119,182,0.24)"
        text_primary = NAVY
        text_secondary = DARK_BLUE
        muted = BLUE
        input_bg = "rgba(255,255,255,0.96)"
        input_text = NAVY
        button_bg = f"linear-gradient(135deg,{DARK_BLUE},{BLUE})"
        button_hover = f"linear-gradient(135deg,{BLUE},{CYAN})"
        title_color = NAVY
        metric_color = DARK_BLUE
        profile_bg = "rgba(255,255,255,0.86)"
        rec_bg = "rgba(0,180,216,0.12)"

    welcome_bg = "url('https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1920&q=90') center center / cover fixed no-repeat"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    * {{
        font-family: 'Inter', sans-serif !important;
        box-sizing: border-box;
    }}

    .stApp {{
        background: {(welcome_bg if is_welcome else app_bg)} !important;
        min-height: 100vh;
        color: {text_primary};
    }}

    header[data-testid="stHeader"] {{
        background: transparent !important;
    }}

    .main .block-container {{
        padding-top: {("4rem" if is_welcome else "1.4rem")};
        max-width: {("1000px" if is_welcome else "1220px")};
    }}

    [data-testid="stSidebar"] {{
        background: {sidebar_bg} !important;
        border-right: 1px solid {card_border};
    }}

    [data-testid="stSidebar"] * {{
        color: {text_primary if dark else NAVY} !important;
    }}

    .welcome-card {{
        width: 100%;
        max-width: 880px;
        margin: 0 auto;
        padding: 48px 46px 38px;
        text-align: center;
        border-radius: 34px;
        background: rgba(255,255,255,0.84);
        border: 1px solid rgba(255,255,255,0.72);
        box-shadow: 0 28px 90px rgba(3,4,94,0.30);
        backdrop-filter: blur(14px);
        -webkit-backdrop-filter: blur(14px);
    }}

    .welcome-logo {{
        width: 92px;
        height: 92px;
        margin: 0 auto 14px;
        display: flex;
        align-items: center;
        justify-content: center;
        border-radius: 28px;
        background: linear-gradient(135deg,{BLUE},{CYAN});
        color: white;
        font-size: 3.1rem;
        box-shadow: 0 14px 34px rgba(0,119,182,0.32);
    }}

    .welcome-title {{
        color: {NAVY};
        font-size: 4rem;
        line-height: 1.05;
        font-weight: 900;
        margin: 0;
        letter-spacing: -2px;
    }}

    .welcome-title span {{
        color: {BLUE};
    }}

    .welcome-sub {{
        color: {DARK_BLUE};
        font-size: 1.08rem;
        font-weight: 700;
        margin: 12px 0 24px;
    }}

    .photo-strip {{
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
        margin: 22px 0 26px;
    }}

    .photo-tile {{
        height: 112px;
        border-radius: 22px;
        background-size: cover;
        background-position: center;
        box-shadow: inset 0 0 0 1px rgba(255,255,255,0.55), 0 10px 28px rgba(3,4,94,0.18);
    }}

    .mini-features {{
        display: flex;
        justify-content: center;
        gap: 10px;
        flex-wrap: wrap;
        margin: 18px 0 28px;
    }}

    .mini-chip {{
        background: rgba(0,119,182,0.10);
        color: {NAVY};
        border: 1px solid rgba(0,119,182,0.22);
        border-radius: 999px;
        padding: 8px 15px;
        font-size: 0.80rem;
        font-weight: 800;
    }}

    .welcome-btn-area .stButton > button {{
        max-width: 230px !important;
        margin: 0 auto !important;
        display: block !important;
        padding: 0.78rem 2.3rem !important;
        border-radius: 16px !important;
        font-size: 1rem !important;
        background: {button_bg} !important;
        color: white !important;
        box-shadow: 0 10px 30px rgba(0,119,182,0.35) !important;
    }}

    .glass, .section-card, .metric-card, .profile-info-card {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 24px;
        box-shadow: 0 16px 42px rgba(3,4,94,0.12);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
    }}

    .glass {{
        padding: 34px 30px;
    }}

    .section-card {{
        padding: 26px;
        margin-bottom: 20px;
    }}

    .page-title {{
        font-size: 2.05rem;
        font-weight: 900;
        color: {title_color};
        letter-spacing: -0.5px;
        margin-bottom: 2px;
    }}

    .subtext {{
        color: {muted};
        font-size: 0.92rem;
        margin-bottom: 14px;
        font-weight: 600;
    }}

    .metric-card {{
        padding: 22px 14px;
        text-align: center;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }}

    .metric-card:hover {{
        transform: translateY(-4px);
        box-shadow: 0 18px 42px rgba(0,119,182,0.18);
    }}

    .metric-value {{
        font-size: 2.2rem;
        font-weight: 900;
        color: {metric_color};
    }}

    .metric-label {{
        color: {muted};
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 1.1px;
        font-weight: 800;
        margin-top: 5px;
    }}

    .avatar-circle {{
        width: 90px;
        height: 90px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        overflow: hidden;
        margin: auto;
        border: 3px solid {CYAN};
        background: linear-gradient(135deg,{BLUE},{CYAN});
        font-size: 2.2rem;
        box-shadow: 0 8px 24px rgba(0,180,216,0.32);
    }}

    .avatar-circle img {{
        width: 100%;
        height: 100%;
        object-fit: cover;
    }}

    .stButton > button,
    [data-testid="stDownloadButton"] button {{
        background: {button_bg} !important;
        color: white !important;
        border: none !important;
        border-radius: 14px !important;
        font-weight: 800 !important;
        font-size: 0.93rem !important;
        padding: 0.62rem 1.45rem !important;
        box-shadow: 0 6px 18px rgba(0,119,182,0.28) !important;
        transition: all 0.18s ease !important;
        cursor: pointer !important;
        white-space: nowrap !important;
    }}

    .stButton > button:hover,
    [data-testid="stDownloadButton"] button:hover {{
        background: {button_hover} !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 10px 26px rgba(0,180,216,0.36) !important;
        color: white !important;
    }}

    .stButton > button p,
    [data-testid="stDownloadButton"] button p {{
        color: white !important;
        font-weight: 800 !important;
    }}

    .center-btn {{
        display: flex;
        justify-content: center;
        margin-top: 8px;
    }}

    .center-btn .stButton > button {{
        min-width: 150px;
        max-width: 220px;
        padding: 0.55rem 1.8rem !important;
    }}

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stPasswordInput input {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {card_border} !important;
        border-radius: 12px !important;
        font-weight: 600 !important;
    }}

    .stSelectbox [data-baseweb="select"] > div {{
        background: {input_bg} !important;
        color: {input_text} !important;
        border: 1.5px solid {card_border} !important;
        border-radius: 12px !important;
    }}

    [data-baseweb="popover"] li {{
        color: {NAVY} !important;
    }}

    [data-baseweb="tab-list"] {{
        background: transparent !important;
        border-bottom: 1.5px solid {card_border} !important;
        gap: 8px !important;
    }}

    [data-baseweb="tab"] {{
        color: {muted} !important;
        font-weight: 800 !important;
        border-radius: 10px 10px 0 0 !important;
        padding: 10px 20px !important;
    }}

    [aria-selected="true"][data-baseweb="tab"] {{
        color: {CYAN if dark else BLUE} !important;
        border-bottom: 3px solid {CYAN if dark else BLUE} !important;
        background: rgba(0,180,216,0.10) !important;
    }}

    .profile-info-card {{
        background: {profile_bg};
        padding: 24px;
    }}

    .profile-field {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 11px 0;
        border-bottom: 1px solid {card_border};
        font-size: 0.93rem;
    }}

    .profile-field:last-child {{
        border-bottom: none;
    }}

    .pf-label {{
        color: {muted};
        font-weight: 700;
    }}

    .pf-value {{
        color: {text_primary};
        font-weight: 800;
    }}

    .score-badge {{
        display: inline-block;
        font-size: 3.8rem;
        font-weight: 900;
        color: {CYAN if dark else BLUE};
        padding: 18px 40px;
        border-radius: 24px;
        background: rgba(0,180,216,0.12);
        border: 2px solid {card_border};
        text-align: center;
        box-shadow: 0 8px 30px rgba(0,180,216,0.18);
    }}

    .rec-box {{
        background: {rec_bg};
        border: 1px solid {card_border};
        border-left: 4px solid {CYAN if dark else BLUE};
        border-radius: 12px;
        padding: 13px 16px;
        margin: 8px 0;
        color: {text_primary};
        font-size: 0.93rem;
        font-weight: 600;
    }}

    .wa-btn, .em-btn {{
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 14px;
        padding: 11px 24px;
        color: white !important;
        text-decoration: none;
        font-weight: 900;
        margin: 6px 5px;
        font-size: 0.90rem;
        transition: transform 0.15s;
    }}

    .wa-btn {{
        background: #25D366;
        box-shadow: 0 4px 16px rgba(37,211,102,0.30);
    }}

    .em-btn {{
        background: {BLUE};
        box-shadow: 0 4px 16px rgba(0,119,182,0.30);
    }}

    .wa-btn:hover, .em-btn:hover {{
        transform: translateY(-2px);
    }}

    label, p, span {{
        color: {text_primary};
    }}

    h1, h2, h3, h4, h5 {{
        color: {title_color};
    }}

    hr {{
        border-color: {card_border} !important;
    }}

    [data-testid="stForm"] {{
        background: transparent !important;
    }}

    .stDataFrame {{
        border-radius: 18px;
        overflow: hidden;
    }}

    @media (max-width: 720px) {{
        .welcome-title {{
            font-size: 2.7rem;
        }}
        .welcome-card {{
            padding: 36px 22px 30px;
        }}
        .photo-strip {{
            grid-template-columns: 1fr;
        }}
        .photo-tile {{
            height: 88px;
        }}
    }}
    </style>
    """, unsafe_allow_html=True)


apply_css()


# =========================================================
# MODEL / PREDICTION
# =========================================================
@st.cache_resource
def load_model_files():
    if os.path.exists(MODEL_FILE) and os.path.exists(COLUMNS_FILE):
        try:
            return joblib.load(MODEL_FILE), joblib.load(COLUMNS_FILE)
        except Exception:
            return None, None
    return None, None


def predict_score(data):
    model, columns = load_model_files()

    if model is not None and columns is not None:
        df = pd.DataFrame([data])
        df = pd.get_dummies(df)
        df = df.reindex(columns=columns, fill_value=0)
        prediction = model.predict(df)[0]
    else:
        prediction = (
            data["Previous_Scores"] * 0.40
            + data["Attendance"] * 0.22
            + min(data["Hours_Studied"] * 7, 45) * 0.55
            + data["Sleep_Hours"] * 2.0
        )
        prediction += {"Low": -4, "Medium": 2, "High": 6}.get(data["Motivation_Level"], 0)
        prediction += {"Poor": -3, "Average": 1, "Good": 4}.get(data["Teacher_Quality"], 0)
        prediction += {"Negative": -4, "Neutral": 1, "Positive": 4}.get(data["Peer_Influence"], 0)

    return int(max(0, min(100, round(prediction))))


def get_recommendations(data):
    recs = []

    if data["Hours_Studied"] < 6:
        recs.append("📚 Increase daily study time to at least 6–8 hours with proper breaks.")
    if data["Attendance"] < 80:
        recs.append("🏫 Maintain attendance above 80% for better academic consistency.")
    if data["Sleep_Hours"] < 7:
        recs.append("😴 Sleep 7–8 hours daily to improve focus and memory.")
    if data["Motivation_Level"] == "Low":
        recs.append("🎯 Set small daily goals and track your progress every evening.")
    if data["Internet_Access"] == "No":
        recs.append("📖 Use offline notes, library books, and teacher support regularly.")
    if data["Learning_Resources"] == "Low":
        recs.append("💡 Use free learning resources such as YouTube lectures, PDFs, and practice sets.")
    if data["Peer_Influence"] == "Negative":
        recs.append("🤝 Try studying with a positive and disciplined peer group.")

    return recs


# =========================================================
# HISTORY / PDF
# =========================================================
def user_history(username):
    return load_json(HISTORY_FILE, {}).get(username, [])


def save_prediction(username, record):
    all_history = load_json(HISTORY_FILE, {})
    all_history.setdefault(username, [])
    all_history[username].append(record)
    all_history[username] = all_history[username][-20:]
    save_json(HISTORY_FILE, all_history)


def simple_pdf_graph(scores):
    drawing = Drawing(430, 160)
    drawing.add(String(10, 145, "Score History", fontSize=12, fillColor=colors.HexColor(DARK_BLUE)))
    drawing.add(Line(35, 30, 410, 30, strokeColor=colors.grey))
    drawing.add(Line(35, 30, 35, 130, strokeColor=colors.grey))

    for y, label in [(30, "0"), (80, "50"), (130, "100")]:
        drawing.add(String(8, y - 4, label, fontSize=7, fillColor=colors.grey))
        drawing.add(Line(35, y, 410, y, strokeColor=colors.lightgrey, strokeWidth=0.4))

    if scores:
        xs = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        points = [(float(x), 30 + (float(score) / 100) * 100) for x, score in zip(xs, scores)]

        for i in range(len(points) - 1):
            drawing.add(Line(
                points[i][0], points[i][1],
                points[i + 1][0], points[i + 1][1],
                strokeColor=colors.HexColor(BLUE),
                strokeWidth=2
            ))

        for i, (x, y) in enumerate(points):
            drawing.add(String(x - 5, y + 6, str(scores[i]), fontSize=7, fillColor=colors.HexColor(NAVY)))

    return drawing


def generate_pdf(username, user_data, score, inputs, recs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, topMargin=0.45 * inch, bottomMargin=0.45 * inch)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "TitleStyle",
        parent=styles["Heading1"],
        alignment=1,
        fontSize=22,
        textColor=colors.HexColor(BLUE),
        spaceAfter=14
    )
    heading_style = ParagraphStyle(
        "HeadingStyle",
        parent=styles["Heading2"],
        fontSize=13,
        textColor=colors.HexColor(DARK_BLUE),
        spaceAfter=7
    )
    normal_style = ParagraphStyle(
        "NormalStyle",
        parent=styles["Normal"],
        fontSize=10,
        leading=14
    )

    story = []
    story.append(Paragraph(f"{APP_NAME} — Official Prediction Report", title_style))
    story.append(Paragraph(f"Generated: {datetime.now().strftime('%d-%m-%Y %I:%M %p')}", normal_style))
    story.append(Spacer(1, 10))

    name = user_data.get("full_name") or user_data.get("child_name") or username
    info_rows = [
        ["Name", name],
        ["Username", username],
        ["Email", user_data.get("email", "N/A")],
        ["Role", user_data.get("role", "N/A").title()]
    ]

    story.append(Paragraph("Student Details", heading_style))
    info_table = Table(info_rows, colWidths=[2.1 * inch, 4.2 * inch])
    info_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor(PALE_SKY)),
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))
    story.append(info_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Prediction Result", heading_style))
    result_table = Table([
        ["Predicted Score", f"{score}/100"],
        ["Status", "Excellent" if score >= 85 else "Good" if score >= 70 else "Needs Improvement"]
    ], colWidths=[2.1 * inch, 4.2 * inch])
    result_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 8)
    ]))
    story.append(result_table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Input Details", heading_style))
    input_rows = [["Field", "Value"]] + [[key.replace("_", " "), str(value)] for key, value in inputs.items()]
    input_table = Table(input_rows, colWidths=[2.7 * inch, 3.6 * inch])
    input_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor(DARK_BLUE)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("PADDING", (0, 0), (-1, -1), 7)
    ]))
    story.append(input_table)
    story.append(Spacer(1, 10))

    scores = [record.get("score", 0) for record in user_history(username)] + [score]
    story.append(simple_pdf_graph(scores[-10:]))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Recommendations", heading_style))
    for rec in (recs or ["All academic inputs are strong. Maintain consistency."]):
        story.append(Paragraph("• " + rec, normal_style))

    story.append(Spacer(1, 18))
    story.append(Paragraph(f"Generated by {APP_NAME}. For academic guidance only.", normal_style))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()


# =========================================================
# CHART HELPERS
# =========================================================
def toggle_theme_button(key):
    label = "☀️ Light" if st.session_state.theme == "dark" else "🌙 Dark"
    if st.button(label, key=key):
        st.session_state.theme = "light" if st.session_state.theme == "dark" else "dark"
        st.rerun()


def chart_cfg():
    dark = st.session_state.theme == "dark"
    return {
        "paper": "rgba(0,0,0,0)",
        "plot": "rgba(0,0,0,0)",
        "line": CYAN if dark else BLUE,
        "marker": SKY if dark else DARK_BLUE,
        "text": ICE if dark else NAVY,
        "grid": "rgba(144,224,239,0.16)" if dark else "rgba(0,119,182,0.14)"
    }


def score_trend_chart(records):
    cc = chart_cfg()
    scores = [record["score"] for record in records]
    dates = [record.get("date", f"#{i + 1}") for i, record in enumerate(records)]

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates,
        y=scores,
        mode="lines+markers+text",
        text=scores,
        textposition="top center",
        line=dict(width=3, color=cc["line"]),
        marker=dict(size=9, color=cc["marker"], line=dict(width=2, color="white")),
        fill="tozeroy",
        fillcolor="rgba(0,180,216,0.09)"
    ))

    fig.add_hline(y=60, line_dash="dash", line_color=SKY, annotation_text="Pass")
    fig.add_hline(y=85, line_dash="dot", line_color=ICE, annotation_text="Excellent")

    fig.update_layout(
        title=dict(text="📈 Score Trend", font=dict(color=cc["text"], size=14)),
        height=320,
        margin=dict(l=10, r=10, t=44, b=10),
        paper_bgcolor=cc["paper"],
        plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0, 112]),
        showlegend=False
    )
    return fig


def radar_chart(inputs):
    cc = chart_cfg()
    categories = ["Study Hours", "Attendance", "Sleep", "Motivation", "Resources", "Peer Influence"]
    values = [
        min(inputs.get("Hours_Studied", 0) / 10 * 100, 100),
        inputs.get("Attendance", 0),
        min(inputs.get("Sleep_Hours", 0) / 9 * 100, 100),
        {"Low": 20, "Medium": 60, "High": 100}.get(inputs.get("Motivation_Level", "Medium"), 60),
        {"Low": 20, "Medium": 60, "High": 100}.get(inputs.get("Learning_Resources", "Medium"), 60),
        {"Negative": 10, "Neutral": 55, "Positive": 100}.get(inputs.get("Peer_Influence", "Neutral"), 55)
    ]

    fig = go.Figure(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor="rgba(0,180,216,0.15)",
        line=dict(color=cc["line"], width=2.5),
        marker=dict(color=cc["marker"], size=7)
    ))

    fig.update_layout(
        title=dict(text="🕸️ Academic Radar", font=dict(color=cc["text"], size=14)),
        polar=dict(
            bgcolor="rgba(0,0,0,0)",
            radialaxis=dict(visible=True, range=[0, 100], color=cc["text"], gridcolor=cc["grid"]),
            angularaxis=dict(color=cc["text"])
        ),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor=cc["paper"],
        showlegend=False
    )
    return fig


def factor_bar_chart(inputs):
    cc = chart_cfg()
    factors = {
        "Study Hours": min(inputs.get("Hours_Studied", 0) / 10 * 100, 100),
        "Attendance": inputs.get("Attendance", 0),
        "Previous Score": inputs.get("Previous_Scores", 0),
        "Sleep": min(inputs.get("Sleep_Hours", 0) / 9 * 100, 100),
        "Motivation": {"Low": 25, "Medium": 60, "High": 100}.get(inputs.get("Motivation_Level", "Medium"), 60),
        "Resources": {"Low": 25, "Medium": 60, "High": 100}.get(inputs.get("Learning_Resources", "Medium"), 60)
    }

    fig = go.Figure(go.Bar(
        x=list(factors.keys()),
        y=list(factors.values()),
        marker=dict(
            color=list(factors.values()),
            colorscale=[[0, NAVY], [0.35, DARK_BLUE], [0.65, BLUE], [1, CYAN]],
            showscale=False
        ),
        text=[f"{value:.0f}" for value in factors.values()],
        textposition="outside",
        textfont=dict(color=cc["text"], size=11)
    ))

    fig.update_layout(
        title=dict(text="📊 Performance Factors", font=dict(color=cc["text"], size=14)),
        height=320,
        margin=dict(l=10, r=10, t=48, b=10),
        paper_bgcolor=cc["paper"],
        plot_bgcolor=cc["plot"],
        xaxis=dict(gridcolor=cc["grid"], color=cc["text"]),
        yaxis=dict(gridcolor=cc["grid"], color=cc["text"], range=[0, 118]),
        showlegend=False
    )
    return fig


# =========================================================
# WELCOME PAGE
# =========================================================
def welcome_page():
    st.markdown(f"""
    <div class="welcome-card">
        <div class="welcome-logo">🎓</div>
        <h1 class="welcome-title">Acadra<span>IQ</span></h1>
        <p class="welcome-sub">{TAGLINE}</p>

        <div class="photo-strip">
            <div class="photo-tile" style="background-image:url('https://images.unsplash.com/photo-1503676260728-1c00da094a0b?auto=format&fit=crop&w=700&q=85');"></div>
            <div class="photo-tile" style="background-image:url('https://images.unsplash.com/photo-1522202176988-66273c2fd55f?auto=format&fit=crop&w=700&q=85');"></div>
            <div class="photo-tile" style="background-image:url('https://images.unsplash.com/photo-1516321318423-f06f85e504b3?auto=format&fit=crop&w=700&q=85');"></div>
        </div>

        <div class="mini-features">
            <span class="mini-chip">OTP Signup</span>
            <span class="mini-chip">AI Prediction</span>
            <span class="mini-chip">PDF Reports</span>
            <span class="mini-chip">WhatsApp Share</span>
            <span class="mini-chip">Smart Graphs</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div class='welcome-btn-area'>", unsafe_allow_html=True)
    if st.button("Launch App →", key="hero_start"):
        st.session_state.auth_page = "login"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# AUTH PAGE
# =========================================================
def auth_page():
    users = load_json(USER_DB_FILE, {})

    top_left, top_right = st.columns([9, 1])
    with top_left:
        if st.button("← Back", key="back_btn"):
            st.session_state.auth_page = "welcome"
            st.rerun()
    with top_right:
        toggle_theme_button("theme_auth")

    col1, col2, col3 = st.columns([1, 2.1, 1])
    with col2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>🎓 {APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:18px'>Secure Login & OTP Verification</p>", unsafe_allow_html=True)

        tab_login, tab_signup = st.tabs(["🔑 Login", "✍️ Sign Up"])

        with tab_login:
            username = st.text_input("Username", key="login_user", placeholder="Enter your username")
            password = st.text_input("Password", type="password", key="login_pass", placeholder="Enter your password")

            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("Login →", key="do_login"):
                if username in users and users[username]["password"] == hash_password(password):
                    st.session_state.logged_in = True
                    st.session_state.username = username
                    st.session_state.role = users[username].get("role", "student")
                    st.session_state.active_page = "Home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            st.markdown("</div>", unsafe_allow_html=True)

        with tab_signup:
            role = st.selectbox("Account Type", ["student", "parent"], format_func=str.title)
            username = st.text_input("Create Username", key="su_user")
            email = st.text_input("Email for OTP", key="su_email")
            full_name = st.text_input("Full Name", key="su_name")
            password = st.text_input("Password", type="password", key="su_pass")
            confirm = st.text_input("Confirm Password", type="password", key="su_confirm")

            if role == "student":
                dob = st.date_input("Date of Birth", key="su_dob", min_value=date(1990, 1, 1), max_value=date.today())
                grade = st.selectbox("Class / Course", ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"])
                school = st.text_input("School / College")
            else:
                child_name = st.text_input("Child Name")
                grade = st.selectbox("Child Class", ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"])
                relation = st.selectbox("Relation", ["Father", "Mother", "Guardian"])

            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("📧 Send OTP", key="send_otp_btn"):
                if not email:
                    st.warning("Email is required.")
                else:
                    otp = generate_otp()
                    store_otp(email, otp)
                    success, message = send_otp_email(email, otp, full_name or "User")

                    if success:
                        st.success("OTP sent successfully. Please check your inbox.")
                    else:
                        st.warning(f"Email is not configured. Test OTP: {otp}")
                        st.caption("To send a real email OTP, configure EMAIL_SENDER and EMAIL_PASSWORD at the top of the code.")
            st.markdown("</div>", unsafe_allow_html=True)

            otp_entered = st.text_input("Enter OTP", max_chars=6, placeholder="6-digit OTP")

            st.markdown("<div class='center-btn'>", unsafe_allow_html=True)
            if st.button("✅ Verify & Create Account", key="verify_otp_btn"):
                if not all([username, email, password, full_name]):
                    st.warning("Please fill all required fields.")
                elif password != confirm:
                    st.error("Passwords do not match.")
                elif len(password) < 4:
                    st.error("Password must contain at least 4 characters.")
                elif username in users:
                    st.error("Username already exists.")
                elif not otp_entered:
                    st.warning("Please enter the OTP.")
                else:
                    ok, msg = verify_otp(email, otp_entered)
                    if not ok:
                        st.error(msg)
                    else:
                        data = {
                            "password": hash_password(password),
                            "email": email,
                            "full_name": full_name,
                            "role": role,
                            "created_at": datetime.now().isoformat()
                        }

                        if role == "student":
                            data.update({
                                "dob": str(dob),
                                "age": calculate_age(dob),
                                "grade": grade,
                                "school": school
                            })
                        else:
                            data.update({
                                "child_name": child_name,
                                "child_grade": grade,
                                "relation": relation
                            })

                        users[username] = data
                        save_json(USER_DB_FILE, users)
                        st.success("Account created successfully. Please login.")
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# SIDEBAR
# =========================================================
def sidebar(user):
    with st.sidebar:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(
            f"<div class='avatar-circle'>{profile_pic_html(st.session_state.username, icon)}</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<h3 style='text-align:center;margin:10px 0 2px'>{user.get('full_name', st.session_state.username)}</h3>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<p class='subtext' style='text-align:center;margin-bottom:14px'>{user.get('role', 'student').title()} Account</p>",
            unsafe_allow_html=True
        )

        st.markdown("---")

        pages = ["🏠 Home", "🔮 Prediction", "📄 Report & Share", "📚 History", "👤 Profile"]
        labels = [page.split(" ", 1)[1] for page in pages]

        selected_index = 0
        for i, label in enumerate(labels):
            if st.session_state.active_page == label:
                selected_index = i

        selected = st.radio("Navigation", pages, index=selected_index)
        st.session_state.active_page = selected.split(" ", 1)[1]

        st.markdown("---")
        toggle_theme_button("theme_sidebar")

        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.auth_page = "welcome"
            st.rerun()


# =========================================================
# HOME PAGE
# =========================================================
def home_page(user):
    records = user_history(st.session_state.username)
    name = user.get("full_name", st.session_state.username)

    st.markdown(f"<div class='page-title'>👋 Welcome, {name}!</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Your academic performance dashboard — all insights in one place.</p>", unsafe_allow_html=True)

    scores = [record["score"] for record in records]

    cols = st.columns(4)
    metrics = [
        ("🎯 Attempts", len(records)),
        ("🏆 Best Score", max(scores) if scores else 0),
        ("📊 Average", int(np.mean(scores)) if scores else 0),
        ("🕐 Last Score", scores[-1] if scores else 0),
    ]

    for col, (label, value) in zip(cols, metrics):
        with col:
            st.markdown(
                f"<div class='metric-card'><div class='metric-value'>{value}</div><div class='metric-label'>{label}</div></div>",
                unsafe_allow_html=True
            )

    st.markdown("<br>", unsafe_allow_html=True)

    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
    else:
        st.info("Generate your first prediction from the Prediction page.")


# =========================================================
# PREDICTION PAGE
# =========================================================
def prediction_page(user):
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Enter academic details and get an AI-powered predicted score.</p>", unsafe_allow_html=True)

    with st.form("prediction_form"):
        col1, col2 = st.columns(2)

        with col1:
            hours = st.number_input("📖 Study Hours Per Day", 0, 24, 5, 1)
            attendance = st.number_input("🏫 Attendance (%)", 0, 100, 75, 1)
            previous = st.number_input("📝 Previous Score", 0, 100, 60, 1)
            sleep = st.number_input("😴 Sleep Hours", 0, 12, 7, 1)
            motivation = st.selectbox("💡 Motivation Level", ["Low", "Medium", "High"])
            teacher = st.selectbox("👨‍🏫 Teacher Quality", ["Poor", "Average", "Good"])
            school_type = st.selectbox("🏢 School Type", ["Public", "Private"])

        with col2:
            internet = st.selectbox("🌐 Internet Access", ["Yes", "No"])
            income = st.selectbox("💰 Family Income", ["Low", "Medium", "High"])
            parental = st.selectbox("👨‍👩‍👦 Parental Involvement", ["Low", "Medium", "High"])
            education = st.selectbox("🎓 Parent Education", ["School", "College"])
            peer = st.selectbox("🤝 Peer Influence", ["Negative", "Neutral", "Positive"])
            resources = st.selectbox("📚 Learning Resources", ["Low", "Medium", "High"])
            activities = st.selectbox("⚽ Extracurricular Activities", ["Yes", "No"])

        submitted = st.form_submit_button("🚀 Predict My Score", use_container_width=True)

    if submitted:
        data = {
            "Hours_Studied": int(hours),
            "Attendance": int(attendance),
            "Previous_Scores": int(previous),
            "Sleep_Hours": int(sleep),
            "Motivation_Level": motivation,
            "Teacher_Quality": teacher,
            "School_Type": school_type,
            "Internet_Access": internet,
            "Family_Income": income,
            "Parental_Involvement": parental,
            "Parental_Education_Level": education,
            "Peer_Influence": peer,
            "Learning_Resources": resources,
            "Extracurricular_Activities": activities,
        }

        score = predict_score(data)
        recs = get_recommendations(data)

        record = {
            "date": datetime.now().strftime("%d-%m-%Y %H:%M"),
            "score": score,
            "inputs": data,
            "recommendations": recs
        }

        save_prediction(st.session_state.username, record)

        st.session_state.last_score = score
        st.session_state.last_inputs = data
        st.session_state.last_recs = recs
        st.session_state.last_pdf = generate_pdf(st.session_state.username, user, score, data, recs)

        status = "🌟 Excellent!" if score >= 85 else "👍 Good" if score >= 70 else "📈 Needs Improvement"

        st.markdown(f"""
        <div style='text-align:center;padding:28px 0'>
          <div class='score-badge'>{score}<span style='font-size:1.3rem;opacity:.75'>/100</span></div>
          <p style='margin-top:12px;font-size:1.05rem;font-weight:800'>{status}</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📊 Performance Analysis")
        graph_col1, graph_col2 = st.columns(2)

        with graph_col1:
            st.plotly_chart(radar_chart(data), use_container_width=True)

        with graph_col2:
            st.plotly_chart(factor_bar_chart(data), use_container_width=True)

        records = user_history(st.session_state.username)
        if len(records) > 1:
            st.plotly_chart(score_trend_chart(records), use_container_width=True)

        if recs:
            st.markdown("### 💬 Personalized Recommendations")
            for rec in recs:
                st.markdown(f"<div class='rec-box'>{rec}</div>", unsafe_allow_html=True)


# =========================================================
# REPORT PAGE
# =========================================================
def report_page(user):
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Download your PDF report or share your result through WhatsApp and email.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)

    if not records and st.session_state.last_score is None:
        st.info("Generate a prediction first to view reports.")
        return

    latest = records[-1] if records else {
        "score": st.session_state.last_score,
        "inputs": st.session_state.last_inputs,
        "recommendations": st.session_state.last_recs
    }

    score = latest["score"]
    inputs = latest["inputs"]
    recs = latest.get("recommendations", [])

    pdf = st.session_state.last_pdf or generate_pdf(st.session_state.username, user, score, inputs, recs)

    center1, center2, center3 = st.columns([1, 1, 1])
    with center2:
        st.markdown(
            f"<div class='metric-card'><div class='metric-label'>Predicted Score</div><div class='metric-value'>{score}/100</div></div>",
            unsafe_allow_html=True
        )

    st.markdown("<br>", unsafe_allow_html=True)

    st.download_button(
        "📥 Download PDF Report",
        data=pdf,
        file_name=f"AcadraIQ_Report_{st.session_state.username}.pdf",
        mime="application/pdf",
        use_container_width=True
    )

    plain_share_text = (
        f"{APP_NAME} Report\n"
        f"Predicted Score: {score}/100\n"
        f"Study Hours: {inputs.get('Hours_Studied')}\n"
        f"Attendance: {inputs.get('Attendance')}%\n"
        f"Previous Score: {inputs.get('Previous_Scores')}\n"
        f"Sleep Hours: {inputs.get('Sleep_Hours')}"
    )

    wa_url = "https://wa.me/?text=" + urllib.parse.quote(plain_share_text)
    email_url = "mailto:?subject=" + urllib.parse.quote(f"{APP_NAME} Report") + "&body=" + urllib.parse.quote(plain_share_text)

    st.markdown(f"""
    <div style='text-align:center;margin:18px 0'>
      <a class='wa-btn' target='_blank' href='{wa_url}'>📱 Share on WhatsApp</a>
      <a class='em-btn' href='{email_url}'>✉️ Share via Email</a>
    </div>
    """, unsafe_allow_html=True)

    st.caption("Browsers do not allow direct PDF attachment to WhatsApp. First download the PDF, then attach it manually in WhatsApp.")

    st.markdown("### 📊 Performance Graphs")
    graph_col1, graph_col2 = st.columns(2)

    with graph_col1:
        st.plotly_chart(radar_chart(inputs), use_container_width=True)

    with graph_col2:
        st.plotly_chart(factor_bar_chart(inputs), use_container_width=True)

    if records:
        st.plotly_chart(score_trend_chart(records), use_container_width=True)

    if recs:
        st.markdown("### 💬 Recommendations")
        for rec in recs:
            st.markdown(f"<div class='rec-box'>{rec}</div>", unsafe_allow_html=True)


# =========================================================
# HISTORY PAGE
# =========================================================
def history_page(user):
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>View all your prediction records in one place.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)

    if not records:
        st.info("No prediction history yet. Make your first prediction.")
        return

    df = pd.DataFrame([{
        "Date": record["date"],
        "Score": record["score"],
        "Study Hours": record["inputs"].get("Hours_Studied"),
        "Attendance": record["inputs"].get("Attendance"),
        "Previous Score": record["inputs"].get("Previous_Scores"),
        "Sleep Hours": record["inputs"].get("Sleep_Hours"),
    } for record in records])

    st.dataframe(df, use_container_width=True)
    st.plotly_chart(score_trend_chart(records), use_container_width=True)


# =========================================================
# PROFILE PAGE
# =========================================================
def profile_page(user):
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Manage your profile details and picture.</p>", unsafe_allow_html=True)

    users = load_json(USER_DB_FILE, {})
    username = st.session_state.username

    col1, col2 = st.columns([1, 2.2])

    with col1:
        icon = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(username, icon)}</div>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<div class='section-card' style='padding:18px 16px'>", unsafe_allow_html=True)
        st.markdown("<p style='font-weight:800;font-size:0.88rem;margin-bottom:8px'>📸 Profile Picture</p>", unsafe_allow_html=True)
        upload = st.file_uploader("Choose image", type=["jpg", "jpeg", "png"], label_visibility="collapsed", key="pic_upload")

        if upload:
            if st.button("💾 Save Picture", use_container_width=True, key="save_pic_btn"):
                save_profile_pic(username, upload.read())
                st.success("Picture updated successfully.")
                st.rerun()
        else:
            st.caption("JPG and PNG files are supported.")

        st.markdown("</div>", unsafe_allow_html=True)

    with col2:
        edit_mode = st.session_state.profile_edit_mode

        if not edit_mode:
            st.markdown("<div class='profile-info-card'>", unsafe_allow_html=True)

            fields = [
                ("Username", username),
                ("Full Name", user.get("full_name", "N/A")),
                ("Email", user.get("email", "N/A")),
                ("Role", user.get("role", "N/A").title()),
            ]

            if user.get("role") == "student":
                fields += [
                    ("Date of Birth", user.get("dob", "N/A")),
                    ("Age", str(user.get("age", "N/A"))),
                    ("Class / Grade", user.get("grade", "N/A")),
                    ("School / College", user.get("school", "N/A")),
                ]
            else:
                fields += [
                    ("Child Name", user.get("child_name", "N/A")),
                    ("Child Grade", user.get("child_grade", "N/A")),
                    ("Relation", user.get("relation", "N/A")),
                ]

            for label, value in fields:
                st.markdown(
                    f"<div class='profile-field'><span class='pf-label'>{label}</span><span class='pf-value'>{value}</span></div>",
                    unsafe_allow_html=True
                )

            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)

            if st.button("✏️ Edit Profile", use_container_width=True):
                st.session_state.profile_edit_mode = True
                st.rerun()

        else:
            with st.form("edit_profile_form"):
                st.markdown("#### ✏️ Edit Profile")

                new_name = st.text_input("Full Name", value=user.get("full_name", ""))
                new_email = st.text_input("Email", value=user.get("email", ""))

                if user.get("role") == "student":
                    try:
                        dob_date = datetime.strptime(user.get("dob", "2000-01-01"), "%Y-%m-%d").date()
                    except Exception:
                        dob_date = date(2000, 1, 1)

                    new_dob = st.date_input("Date of Birth", value=dob_date, min_value=date(1990, 1, 1), max_value=date.today())
                    grade_options = ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"]
                    current_grade = user.get("grade", "Class 10")
                    new_grade = st.selectbox(
                        "Class / Grade",
                        grade_options,
                        index=grade_options.index(current_grade) if current_grade in grade_options else 2
                    )
                    new_school = st.text_input("School / College", value=user.get("school", ""))

                else:
                    new_child = st.text_input("Child Name", value=user.get("child_name", ""))
                    grade_options = ["Class 8", "Class 9", "Class 10", "Class 11", "Class 12", "College"]
                    current_grade = user.get("child_grade", "Class 10")
                    new_child_grade = st.selectbox(
                        "Child Grade",
                        grade_options,
                        index=grade_options.index(current_grade) if current_grade in grade_options else 2
                    )
                    relation_options = ["Father", "Mother", "Guardian"]
                    current_relation = user.get("relation", "Father")
                    new_relation = st.selectbox(
                        "Relation",
                        relation_options,
                        index=relation_options.index(current_relation) if current_relation in relation_options else 0
                    )

                st.markdown("---")
                st.markdown("##### 🔒 Change Password Optional")
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_password = st.text_input("Confirm New Password", type="password")

                save_col, cancel_col = st.columns(2)
                with save_col:
                    save_clicked = st.form_submit_button("💾 Save Changes", use_container_width=True)
                with cancel_col:
                    cancel_clicked = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel_clicked:
                st.session_state.profile_edit_mode = False
                st.rerun()

            if save_clicked:
                updated_user = users[username].copy()
                updated_user["full_name"] = new_name
                updated_user["email"] = new_email

                if user.get("role") == "student":
                    updated_user.update({
                        "dob": str(new_dob),
                        "age": calculate_age(new_dob),
                        "grade": new_grade,
                        "school": new_school
                    })
                else:
                    updated_user.update({
                        "child_name": new_child,
                        "child_grade": new_child_grade,
                        "relation": new_relation
                    })

                if old_password or new_password or confirm_password:
                    if users[username]["password"] != hash_password(old_password):
                        st.error("Current password is incorrect.")
                        st.stop()
                    elif new_password != confirm_password:
                        st.error("New passwords do not match.")
                        st.stop()
                    elif len(new_password) < 4:
                        st.error("Password must contain at least 4 characters.")
                        st.stop()
                    else:
                        updated_user["password"] = hash_password(new_password)

                users[username] = updated_user
                save_json(USER_DB_FILE, users)
                st.session_state.profile_edit_mode = False
                st.success("Profile updated successfully.")
                st.rerun()


# =========================================================
# MAIN ROUTER
# =========================================================
def main_app():
    users = load_json(USER_DB_FILE, {})
    user = users.get(st.session_state.username, {})

    sidebar(user)

    page = st.session_state.active_page

    if page == "Home":
        home_page(user)
    elif page == "Prediction":
        prediction_page(user)
    elif page == "Report & Share":
        report_page(user)
    elif page == "History":
        history_page(user)
    elif page == "Profile":
        profile_page(user)


if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()
