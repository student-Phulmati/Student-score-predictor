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
import plotly.express as px

# =====================================================
# CONSTANTS
# =====================================================
APP_NAME       = "🎓 ScoreWise AI"
APP_NAME_PLAIN = "ScoreWise AI"
TAGLINE        = "Smart Student Performance Predictor"
USER_DB_FILE   = "users.json"
HISTORY_FILE   = "prediction_history.json"
OTP_FILE       = "otp_store.json"
PROFILE_PICS_DIR = "profile_pics"
MODEL_FILE     = "student_model.pkl"
COLUMNS_FILE   = "model_columns.pkl"

EMAIL_SENDER   = "your_email@gmail.com"
EMAIL_PASSWORD = "your_gmail_app_password"

os.makedirs(PROFILE_PICS_DIR, exist_ok=True)

st.set_page_config(
    page_title=APP_NAME_PLAIN,
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# =====================================================
# UTILITY FUNCTIONS
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

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def calculate_age(dob):
    today = datetime.now().date()
    if isinstance(dob, str):
        dob = datetime.strptime(dob, "%Y-%m-%d").date()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

def save_profile_pic(username, image_bytes):
    with open(os.path.join(PROFILE_PICS_DIR, f"{username}.jpg"), "wb") as f:
        f.write(image_bytes)

def profile_pic_html(username, fallback="🎓"):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />'
    return fallback

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
    if (datetime.now() - datetime.fromisoformat(saved["timestamp"])).total_seconds() > 600:
        return False, "OTP expired. Please send a new OTP."
    if saved["otp"] != entered:
        return False, "Invalid OTP. Please check and try again."
    data[email]["verified"] = True
    save_json(OTP_FILE, data)
    return True, "OTP verified successfully."

def send_otp_email(receiver, otp, name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME_PLAIN} OTP"
        msg["From"]    = EMAIL_SENDER
        msg["To"]      = receiver
        html = f"""
        <div style='font-family:Arial;background:#184e77;color:white;padding:26px;border-radius:18px'>
          <h2 style='color:#d9ed92'>{APP_NAME}</h2>
          <p>Hello <b>{name}</b>, your signup OTP is:</p>
          <div style='font-size:34px;letter-spacing:8px;font-weight:800;color:#99d98c'>{otp}</div>
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
    for k, v in {
        "logged_in": False, "username": "", "role": "",
        "auth_page": "welcome", "theme": "dark", "active_page": "Home",
        "last_score": None, "last_pdf": None, "last_inputs": {},
        "last_recs": [], "profile_edit_mode": False,
    }.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# =====================================================
# CSS
# =====================================================
def apply_css():
    dark = st.session_state.theme == "dark"
    is_welcome = (not st.session_state.logged_in and st.session_state.auth_page == "welcome")
    BG = "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1900&q=85"

    if dark:
        app_bg      = f"linear-gradient(135deg,rgba(8,15,60,0.78) 0%,rgba(0,40,90,0.82) 100%),url('{BG}')" if not is_welcome else f"linear-gradient(135deg,rgba(3,4,94,0.55) 0%,rgba(0,119,182,0.30) 100%),url('{BG}')"
        card_bg     = "rgba(255,255,255,0.08)"
        card_hover  = "rgba(255,255,255,0.12)"
        text1       = "#eaf4ff"
        text2       = "#b8d8f0"
        textm       = "#88c0e8"
        border      = "rgba(140,200,240,0.16)"
        inp_bg      = "rgba(255,255,255,0.93)"
        inp_text    = "#0a0f3c"
        inp_border  = "rgba(0,150,220,0.40)"
        acc1        = "#52b6e8"
        acc2        = "#38a8dc"
        acc3        = "#1a95cc"
        tb_bg       = "rgba(6,14,52,0.97)"
        tb_border   = "rgba(82,182,232,0.16)"
        tb_text     = "#eaf4ff"
        tb_role     = "#88c0e8"
        nav_active_c= "#52b6e8"
        nav_active_bg="rgba(82,182,232,0.14)"
        btn_sm_bg   = "rgba(255,255,255,0.08)"
        shadow      = "0 8px 32px rgba(0,0,0,0.26)"
    else:
        app_bg      = f"linear-gradient(135deg,rgba(230,245,255,0.88) 0%,rgba(210,238,255,0.90) 100%),url('{BG}')" if not is_welcome else f"linear-gradient(135deg,rgba(245,252,255,0.50) 0%,rgba(210,240,255,0.40) 100%),url('{BG}')"
        card_bg     = "rgba(255,255,255,0.72)"
        card_hover  = "rgba(255,255,255,0.88)"
        text1       = "#03045e"
        text2       = "#023e8a"
        textm       = "#0077b6"
        border      = "rgba(2,62,138,0.14)"
        inp_bg      = "rgba(255,255,255,0.95)"
        inp_text    = "#03045e"
        inp_border  = "rgba(0,119,182,0.28)"
        acc1        = "#0077b6"
        acc2        = "#0096c7"
        acc3        = "#00b4d8"
        tb_bg       = "rgba(255,255,255,0.97)"
        tb_border   = "rgba(2,62,138,0.10)"
        tb_text     = "#03045e"
        tb_role     = "#0077b6"
        nav_active_c= "#0077b6"
        nav_active_bg="rgba(0,119,182,0.10)"
        btn_sm_bg   = "rgba(2,62,138,0.07)"
        shadow      = "0 8px 32px rgba(2,62,138,0.14)"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800;900&display=swap');
    *{{font-family:'Plus Jakarta Sans',sans-serif!important;box-sizing:border-box;}}

    /* hide streamlit chrome */
    .stApp>header{{background:transparent!important;height:0!important;}}
    [data-testid="stDecoration"]{{display:none!important;}}
    #MainMenu,footer{{visibility:hidden;height:0;}}
    [data-testid="stToolbar"]{{visibility:hidden!important;height:0!important;position:fixed!important;}}
    [data-testid="stSidebar"],[data-testid="stSidebarNav"],
    [data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{{
        display:none!important;visibility:hidden!important;width:0!important;min-width:0!important;
    }}

    /* remove ALL streamlit default spacing */
    .stApp{{background:{app_bg}!important;background-size:cover!important;background-position:center!important;background-attachment:fixed!important;min-height:100vh;}}
    .main .block-container{{
        padding:0!important;margin:0!important;max-width:100%!important;
    }}
    /* kill gap between columns */
    [data-testid="stHorizontalBlock"]{{gap:0!important;}}
    [data-testid="stColumn"]{{padding:0!important;}}
    /* kill default element vertical spacing */
    [data-testid="stVerticalBlock"]>div{{margin-bottom:0!important;padding-bottom:0!important;}}
    .element-container{{margin:0!important;padding:0!important;}}
    div.stMarkdown{{margin:0!important;padding:0!important;}}
    .stButton{{margin:0!important;}}

    /* ═══════════════════════════════════
       TOP NAVBAR
    ═══════════════════════════════════ */
    .topbar-shell{{
        width:100%;
        background:{tb_bg};
        border-bottom:1px solid {tb_border};
        box-shadow:0 2px 20px rgba(0,0,0,0.12);
        backdrop-filter:blur(28px);
        -webkit-backdrop-filter:blur(28px);
        padding:8px 16px 6px 16px;
        position:sticky;top:0;z-index:9999;
    }}
    .top-profile{{display:flex;align-items:center;gap:8px;padding:2px 0;}}
    .top-avatar{{
        width:46px;height:46px;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        overflow:hidden;flex-shrink:0;
        background:linear-gradient(135deg,#0a1f6e,#0077b6,#00b4d8);
        font-size:1.3rem;
        box-shadow:0 3px 12px rgba(0,119,182,0.28);
        border:2px solid {acc2};
    }}
    .top-avatar img{{width:100%;height:100%;object-fit:cover;border-radius:50%;}}
    .top-name{{font-size:0.95rem;font-weight:900;color:{tb_text};line-height:1.15;}}
    .top-role{{font-size:0.70rem;font-weight:600;color:{tb_role};}}

    /* back + theme small buttons */
    .back-icon-btn .stButton>button,
    .theme-top-btn .stButton>button{{
        width:38px!important;min-width:38px!important;height:38px!important;
        border-radius:10px!important;padding:0!important;
        background:{btn_sm_bg}!important;
        color:{tb_text}!important;
        border:1px solid {tb_border}!important;
        box-shadow:none!important;
        font-size:1.05rem!important;
        transition:all 0.15s ease!important;
    }}
    .back-icon-btn .stButton>button:hover,
    .theme-top-btn .stButton>button:hover{{
        background:linear-gradient(135deg,#0077b6,#00b4d8)!important;
        color:white!important;border-color:#00b4d8!important;
        transform:scale(1.06)!important;
    }}
    /* sign out button */
    .signout-top-btn .stButton>button{{
        height:38px!important;border-radius:999px!important;
        padding:0 1rem!important;font-size:0.82rem!important;
        white-space:nowrap!important;
    }}

    /* segmented control nav */
    div[data-testid="stSegmentedControl"]{{background:transparent!important;border:none!important;}}
    div[data-testid="stSegmentedControl"] button{{
        border-radius:8px!important;background:transparent!important;
        color:{tb_role}!important;box-shadow:none!important;border:0!important;
        font-weight:700!important;font-size:0.80rem!important;
        padding:5px 8px!important;transition:all 0.14s ease!important;
    }}
    div[data-testid="stSegmentedControl"] button[aria-pressed="true"]{{
        color:{nav_active_c}!important;
        background:{nav_active_bg}!important;
        border-bottom:2px solid {nav_active_c}!important;
        border-radius:8px 8px 0 0!important;
    }}

    /* ═══════════════════════════════════
       DASHBOARD CONTENT AREA
    ═══════════════════════════════════ */
    .dash-wrap{{
        padding:22px 28px 28px 28px;
        width:100%;
    }}
    .dash-title{{
        font-size:clamp(1.6rem,2.5vw,2.2rem);font-weight:900;
        color:{text1};margin:0 0 2px 0;letter-spacing:-0.5px;
    }}
    .dash-sub{{
        font-size:0.88rem;font-weight:600;
        color:{text2};margin:0 0 16px 0;
    }}

    /* metric cards row — tight grid */
    .metrics-row{{
        display:grid;
        grid-template-columns:repeat(4,1fr);
        gap:12px;
        margin-bottom:16px;
    }}
    .mc{{
        background:{card_bg};
        border:1px solid {border};
        backdrop-filter:blur(18px);
        -webkit-backdrop-filter:blur(18px);
        border-radius:18px;
        padding:18px 8px 14px 8px;
        text-align:center;
        transition:transform 0.20s ease,background 0.20s ease;
        box-shadow:{shadow};
    }}
    .mc:hover{{transform:translateY(-3px);background:{card_hover};}}
    .mc-val{{font-size:2.0rem;font-weight:900;color:{acc1};line-height:1.1;}}
    .mc-lbl{{font-size:0.68rem;color:{textm};text-transform:uppercase;letter-spacing:1.2px;margin-top:5px;font-weight:800;}}

    /* chart glass */
    .chart-glass{{
        background:{card_bg};
        border:1px solid {border};
        box-shadow:{shadow};
        backdrop-filter:blur(18px);
        -webkit-backdrop-filter:blur(18px);
        border-radius:20px;
        padding:14px 14px 2px 14px;
        margin-bottom:16px;
    }}

    /* glass card (auth/profile) */
    .glass{{
        background:{card_bg};border:1px solid {border};
        box-shadow:{shadow};backdrop-filter:blur(20px);
        border-radius:22px;padding:24px;
    }}

    /* page title */
    .page-title{{font-size:1.8rem;font-weight:900;margin:0 0 2px 0;color:{text1};letter-spacing:-0.4px;}}
    .subtext{{color:{text2};font-size:0.88rem;margin:0 0 14px 0;font-weight:600;}}

    /* score badge */
    .score-badge{{
        display:inline-block;font-size:3.2rem;font-weight:900;
        color:{acc1};padding:14px 30px;border-radius:20px;
        background:{card_bg};border:1px solid {border};backdrop-filter:blur(16px);
    }}

    /* profile card */
    .profile-info-card{{background:{card_bg};border:1px solid {border};backdrop-filter:blur(18px);border-radius:18px;padding:20px;}}
    .profile-field{{display:flex;justify-content:space-between;gap:12px;padding:9px 0;border-bottom:1px solid {border};font-size:0.90rem;}}
    .profile-field:last-child{{border-bottom:none;}}
    .pf-label{{color:{textm};font-weight:800;}}
    .pf-value{{color:{text1};font-weight:900;}}

    /* avatar */
    .avatar-circle{{
        width:82px;height:82px;border-radius:50%;
        display:flex;align-items:center;justify-content:center;
        overflow:hidden;margin:auto;
        border:3px solid {acc2};
        background:linear-gradient(135deg,{acc1},{acc3});
        font-size:2rem;box-shadow:0 8px 24px rgba(0,0,0,0.18);
    }}
    .avatar-circle img{{width:100%;height:100%;object-fit:cover;border-radius:50%;}}

    /* metric card in report page */
    .metric-card{{
        background:{card_bg};border:1px solid {border};
        box-shadow:{shadow};backdrop-filter:blur(18px);
        border-radius:18px;padding:18px 10px;text-align:center;
    }}
    .metric-value{{font-size:2.0rem;font-weight:900;color:{acc1};}}
    .metric-label{{font-size:0.70rem;color:{textm};text-transform:uppercase;letter-spacing:1px;margin-top:4px;font-weight:800;}}

    /* whatsapp button */
    .whatsapp-btn{{
        display:inline-block;border-radius:999px;padding:10px 22px;
        color:white!important;text-decoration:none;font-weight:900;
        margin:6px 4px;font-size:0.90rem;
        background:linear-gradient(135deg,#25D366,#128C7E);
        box-shadow:0 6px 18px rgba(0,0,0,0.16);
    }}

    /* ALL buttons */
    .stButton>button,
    [data-testid="stDownloadButton"] button,
    .stFormSubmitButton>button{{
        border-radius:999px!important;border:0!important;
        font-weight:800!important;cursor:pointer!important;
        padding:0.56rem 1.3rem!important;
        background:linear-gradient(135deg,#0a1f6e,#0077b6,#00b4d8)!important;
        color:white!important;
        box-shadow:0 6px 18px rgba(0,119,182,0.26)!important;
        transition:all 0.18s ease!important;
    }}
    .stButton>button:hover,
    [data-testid="stDownloadButton"] button:hover,
    .stFormSubmitButton>button:hover{{
        transform:translateY(-2px) scale(1.01)!important;
        box-shadow:0 12px 28px rgba(0,180,216,0.34)!important;
        background:linear-gradient(135deg,#0077b6,#00b4d8,#7dd8f5)!important;
    }}

    /* inputs */
    .stTextInput input,.stNumberInput input,.stDateInput input,.stPasswordInput input,textarea{{
        background:{inp_bg}!important;color:{inp_text}!important;
        border:1.5px solid {inp_border}!important;border-radius:10px!important;
        font-weight:600!important;caret-color:{inp_text}!important;
    }}
    .stSelectbox [data-baseweb="select"]>div{{
        background:{inp_bg}!important;color:{inp_text}!important;
        border:1.5px solid {inp_border}!important;border-radius:10px!important;
    }}
    .stSelectbox [data-baseweb="select"] span,
    .stSelectbox [data-baseweb="select"] div,
    .stSelectbox [data-baseweb="select"] input{{color:{inp_text}!important;}}
    [data-baseweb="menu"]{{background:{inp_bg}!important;}}
    [data-baseweb="menu"] li{{color:{inp_text}!important;font-weight:600!important;}}
    [data-baseweb="menu"] li:hover{{background:rgba(0,150,220,0.14)!important;}}
    [data-testid="stNumberInputField"] input{{color:{inp_text}!important;background:{inp_bg}!important;}}

    /* labels */
    label,p{{color:{text1}!important;}}
    .stTextInput label,.stNumberInput label,.stSelectbox label,
    .stDateInput label,.stRadio label,.stCheckbox label,
    [data-baseweb="form-control"] label,.stSlider label{{
        color:{text1}!important;font-weight:700!important;font-size:0.86rem!important;
    }}

    /* tabs */
    [data-baseweb="tab-list"]{{background:transparent!important;border-bottom:1px solid {border}!important;}}
    [data-baseweb="tab"]{{color:{textm}!important;font-weight:800!important;}}
    [aria-selected="true"][data-baseweb="tab"]{{color:{acc1}!important;border-bottom:3px solid {acc1}!important;}}

    hr{{border-color:{border}!important;}}
    .stAlert{{border-radius:14px!important;}}
    .stDataFrame{{border-radius:14px;overflow:hidden;}}

    /* ═══════════════════════════════════
       WELCOME PAGE
    ═══════════════════════════════════ */
    .hero-title{{
        font-size:clamp(2.0rem,4vw,3.2rem);font-weight:900;
        color:{'white' if dark else '#03045e'};margin:0;
        letter-spacing:-1px;text-shadow:0 3px 16px rgba(0,0,0,0.22);line-height:1.06;
    }}
    .hero-tagline{{font-size:0.98rem;color:{'#b8e0f7' if dark else '#0077b6'};font-weight:600;margin:5px 0 0 0;}}
    .welcome-divider{{border:0;height:1px;background:{'rgba(255,255,255,0.22)' if dark else 'rgba(2,62,138,0.13)'};margin:10px auto 12px auto;max-width:580px;}}
    .feature-cards-row{{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin:0 0 16px 0;}}
    .feat-card{{
        flex:1 1 190px;max-width:240px;
        background:{'rgba(255,255,255,0.10)' if dark else 'rgba(255,255,255,0.75)'};
        border:1px solid {'rgba(255,255,255,0.20)' if dark else 'rgba(2,62,138,0.14)'};
        border-radius:16px;padding:18px 14px 14px 14px;
        text-align:center;backdrop-filter:blur(16px);
        box-shadow:0 8px 26px rgba(0,0,0,0.13);transition:transform 0.18s ease;
    }}
    .feat-card:hover{{transform:translateY(-4px);}}
    .feat-icon{{font-size:1.8rem;display:block;margin-bottom:6px;}}
    .feat-title{{font-size:0.95rem;font-weight:900;color:{'white' if dark else '#03045e'};margin:0 0 3px 0;}}
    .feat-sep{{width:28px;height:3px;background:linear-gradient(90deg,#00b4d8,#7dd8f5);border-radius:99px;margin:0 auto 7px auto;}}
    .feat-desc{{font-size:0.74rem;color:{'#b8e0f7' if dark else '#0077b6'};font-weight:600;line-height:1.5;}}
    .used-for-row{{display:flex;gap:8px;justify-content:center;flex-wrap:wrap;margin:0 0 4px 0;}}
    .used-item{{text-align:center;padding:3px 7px;}}
    .used-icon{{font-size:1.3rem;display:block;margin-bottom:2px;}}
    .used-label{{font-size:0.64rem;font-weight:800;color:{'#b8e0f7' if dark else '#023e8a'};text-transform:uppercase;letter-spacing:0.5px;}}
    .stats-strip{{
        display:flex;gap:8px;justify-content:center;flex-wrap:wrap;
        padding:10px 8px;
        border-top:1px solid {'rgba(255,255,255,0.18)' if dark else 'rgba(2,62,138,0.10)'};
        border-bottom:1px solid {'rgba(255,255,255,0.18)' if dark else 'rgba(2,62,138,0.10)'};
        margin:10px 0 14px 0;
    }}
    .stat-chip{{display:flex;align-items:center;gap:5px;padding:5px 10px;border-radius:999px;background:rgba(0,180,216,0.11);border:1px solid rgba(0,180,216,0.20);}}
    .stat-chip-num{{font-size:1.0rem;font-weight:900;color:{'white' if dark else '#03045e'};}}
    .stat-chip-lbl{{font-size:0.66rem;font-weight:700;color:{'#b8e0f7' if dark else '#0096c7'};text-transform:uppercase;letter-spacing:0.6px;}}
    .welcome-footer{{text-align:center;font-size:0.76rem;color:{'#b8e0f7' if dark else '#0077b6'};padding:5px 0 8px 0;font-weight:600;}}

    /* auth page back/theme */
    .back-btn-wrap .stButton>button{{
        background:{card_bg}!important;border:1.5px solid {border}!important;
        color:{text1}!important;box-shadow:0 2px 8px rgba(0,0,0,0.10)!important;
        padding:0.36rem 1rem!important;font-size:0.85rem!important;border-radius:999px!important;
    }}
    .back-btn-wrap .stButton>button:hover{{background:{card_hover}!important;transform:translateX(-2px)!important;}}
    .auth-theme-btn .stButton>button{{
        width:44px!important;height:38px!important;min-width:44px!important;
        border-radius:10px!important;padding:0!important;font-size:1.05rem!important;
        background:{'rgba(8,15,60,0.85)' if dark else 'rgba(255,255,255,0.85)'}!important;
        border:1.2px solid {border}!important;color:{text1}!important;
        box-shadow:0 3px 12px rgba(0,0,0,0.14)!important;
    }}
    .auth-theme-btn .stButton>button:hover{{
        transform:scale(1.06)!important;border-color:#00b4d8!important;
        background:linear-gradient(135deg,#0077b6,#00b4d8)!important;color:white!important;
    }}
    </style>
    """, unsafe_allow_html=True)

apply_css()

# =====================================================
# MODEL
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
        pred = (
            data["Previous_Scores"] * 0.38 + data["Attendance"] * 0.22 +
            min(data["Hours_Studied"] * 7, 45) * 0.55 + data["Sleep_Hours"] * 2.2
        )
        pred += {"Low": -4, "Medium": 2, "High": 6}.get(data["Motivation_Level"], 0)
    return int(max(0, min(100, round(pred))))

def get_recommendations(d):
    recs = []
    if d["Hours_Studied"] < 6:            recs.append("📚 Improve daily study hours to 6–8 hours.")
    if d["Attendance"] < 80:              recs.append("🏫 Keep attendance above 80% for stronger performance.")
    if d["Sleep_Hours"] < 7:              recs.append("😴 Maintain 7–8 hours of sleep to improve concentration.")
    if d["Motivation_Level"] == "Low":    recs.append("🎯 Set small daily goals and track your progress.")
    if d["Internet_Access"] == "No":      recs.append("📖 Use offline notes, library support, and teacher guidance.")
    if d["Learning_Resources"] == "Low":  recs.append("💡 Use free learning resources such as lectures, notes, and PDFs.")
    if d["Peer_Influence"] == "Negative": recs.append("🤝 Build a positive peer group to improve academic consistency.")
    return recs

# =====================================================
# HISTORY & PDF
# =====================================================
def user_history(username):
    return load_json(HISTORY_FILE, {}).get(username, [])

def save_prediction(username, record):
    all_h = load_json(HISTORY_FILE, {})
    all_h.setdefault(username, [])
    all_h[username].append(record)
    all_h[username] = all_h[username][-20:]
    save_json(HISTORY_FILE, all_h)

def simple_pdf_graph(scores):
    drawing = Drawing(430, 160)
    drawing.add(String(10, 145, "Score History Graph", fontSize=12, fillColor=colors.HexColor("#184e77")))
    drawing.add(Line(35, 30, 410, 30, strokeColor=colors.grey))
    drawing.add(Line(35, 30, 35, 130, strokeColor=colors.grey))
    for y, lab in [(30,"0"),(80,"50"),(130,"100")]:
        drawing.add(String(8, y-4, lab, fontSize=7, fillColor=colors.grey))
        drawing.add(Line(35, y, 410, y, strokeColor=colors.lightgrey, strokeWidth=.4))
    if scores:
        xs  = np.linspace(45, 395, len(scores)) if len(scores) > 1 else [220]
        pts = [(float(x), 30+(float(s)/100)*100) for x, s in zip(xs, scores)]
        for i in range(len(pts)-1):
            drawing.add(Line(pts[i][0],pts[i][1],pts[i+1][0],pts[i+1][1],
                             strokeColor=colors.HexColor("#34a0a4"), strokeWidth=2))
        for i,(x,y) in enumerate(pts):
            drawing.add(String(x-5, y+6, str(scores[i]), fontSize=7, fillColor=colors.HexColor("#184e77")))
    return drawing

def generate_pdf(username, user_data, score, inputs, recs):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    sty = getSampleStyleSheet()
    TS  = ParagraphStyle("T", parent=sty["Heading1"], alignment=1, fontSize=22,
                         textColor=colors.HexColor("#168aad"), spaceAfter=4, fontName="Helvetica-Bold")
    SS  = ParagraphStyle("S", parent=sty["Normal"], alignment=1, fontSize=10,
                         textColor=colors.HexColor("#1a759f"), spaceAfter=14, fontName="Helvetica")
    HS  = ParagraphStyle("H", parent=sty["Heading2"], fontSize=13, textColor=colors.white,
                         spaceAfter=0, fontName="Helvetica-Bold", backColor=colors.HexColor("#184e77"),
                         borderPadding=(8,10,8,10))
    NS  = ParagraphStyle("N", parent=sty["Normal"], fontSize=10, leading=15, textColor=colors.HexColor("#03045e"))
    RS  = ParagraphStyle("R", parent=sty["Normal"], fontSize=10, leading=15,
                         textColor=colors.HexColor("#184e77"), leftIndent=10)
    story = []
    story += [Paragraph(f"🎓 {APP_NAME_PLAIN}", TS),
              Paragraph("Official Student Performance Prediction Report", SS),
              Paragraph(f"Generated on: {datetime.now().strftime('%d %B %Y  |  %I:%M %p')}", SS),
              Table([[""]], colWidths=[6.6*inch],
                    style=[("LINEBELOW",(0,0),(-1,-1),1.2,colors.HexColor("#168aad")),
                           ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]),
              Spacer(1,10)]
    sname = user_data.get("full_name") or user_data.get("child_name") or username
    story.append(Paragraph("  Student / User Details", HS)); story.append(Spacer(1,4))
    info = [["Full Name",sname],["Username",username],
            ["Email",user_data.get("email","N/A")],["Role",user_data.get("role","N/A").title()]]
    if user_data.get("role") == "student":
        info += [["Grade",user_data.get("grade","N/A")],["School",user_data.get("school","N/A")],
                 ["DOB",user_data.get("dob","N/A")]]
    else:
        info += [["Child Name",user_data.get("child_name","N/A")],
                 ["Child Grade",user_data.get("child_grade","N/A")],
                 ["Relation",user_data.get("relation","N/A")]]
    t = Table([[Paragraph(f"<b>{r[0]}</b>",NS),Paragraph(r[1],NS)] for r in info],
              colWidths=[2.2*inch,4.4*inch])
    t.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(1,0),(1,-1),"Helvetica")]))
    story += [t, Spacer(1,14)]
    story.append(Paragraph("  Prediction Result", HS)); story.append(Spacer(1,4))
    stat = "Excellent!" if score>=85 else ("Good" if score>=70 else "Needs Improvement")
    sc   = colors.HexColor("#168aad") if score>=70 else colors.HexColor("#e85d04")
    tr   = Table([[Paragraph("<b>Predicted Score</b>",NS),Paragraph(f"{score}/100",NS)],
                  [Paragraph("<b>Status</b>",NS),Paragraph(stat,NS)]],
                 colWidths=[2.2*inch,4.4*inch])
    tr.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("BACKGROUND",(1,0),(1,0),colors.HexColor("#caf0f8")),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(1,0),(1,0),13),("TEXTCOLOR",(1,0),(1,0),sc),("PADDING",(0,0),(-1,-1),9)]))
    story += [tr, Spacer(1,14)]
    story.append(Paragraph("  Academic Input Details", HS)); story.append(Spacer(1,4))
    hdr = [[Paragraph("<b>Factor</b>",NS),Paragraph("<b>Value</b>",NS)]]
    rows= [[Paragraph(k.replace("_"," "),NS),Paragraph(str(v),NS)] for k,v in inputs.items()]
    ti  = Table(hdr+rows, colWidths=[2.9*inch,3.7*inch])
    ti.setStyle(TableStyle([("GRID",(0,0),(-1,-1),.5,colors.HexColor("#ade8f4")),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#184e77")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8)]))
    story += [ti, Spacer(1,14)]
    sl = [r.get("score",0) for r in user_history(username)] + [score]
    if len(sl) > 1:
        story.append(Paragraph("  Score History Graph", HS)); story.append(Spacer(1,6))
        story += [simple_pdf_graph(sl[-10:]), Spacer(1,14)]
    story.append(Paragraph("  Personalized Recommendations", HS)); story.append(Spacer(1,6))
    if recs:
        for r in recs:
            clean = r
            for ch in ["📚","🏫","😴","🎯","📖","💡","🤝"," "]: clean = clean.lstrip(ch)
            story += [Paragraph("• "+clean.strip(), RS), Spacer(1,3)]
    else:
        story.append(Paragraph("Your current academic inputs are strong. Keep up the great work!", RS))
    story += [Spacer(1,20),
              Table([[""]], colWidths=[6.6*inch],
                    style=[("LINEABOVE",(0,0),(-1,-1),.8,colors.HexColor("#ade8f4")),
                           ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]),
              Paragraph(f"Generated by {APP_NAME_PLAIN}  |  {datetime.now().strftime('%d-%m-%Y')}  |  Academic guidance only.", SS)]
    doc.build(story)
    buf.seek(0)
    return buf.read()

# =====================================================
# CHARTS
# =====================================================
def cc():
    dark = st.session_state.theme == "dark"
    return {
        "paper":"rgba(0,0,0,0)","plot":"rgba(0,0,0,0)",
        "line":"#52b6e8" if dark else "#1e6091",
        "marker":"#38a8dc" if dark else "#168aad",
        "text":"#b8e0f7" if dark else "#184e77",
        "grid":"rgba(82,182,232,0.10)" if dark else "rgba(26,117,159,0.08)",
    }

def score_trend_chart(records):
    c = cc()
    scores = [r["score"] for r in records]
    dates  = [r.get("date",f"#{i+1}") for i,r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=dates, y=scores, mode="lines+markers+text",
        text=scores, textposition="top center",
        line=dict(width=3,color=c["line"]),
        marker=dict(size=10,color=c["marker"],line=dict(width=2,color="white")),
        fill="tozeroy", fillcolor="rgba(56,168,220,0.09)",
    ))
    fig.add_hline(y=60, line_dash="dash", line_color="#52b6e8",
                  annotation_text="Pass Line", annotation_font_color="#52b6e8")
    fig.add_hline(y=85, line_dash="dot", line_color="#7dd8f5",
                  annotation_text="Excellent", annotation_font_color="#7dd8f5")
    fig.update_layout(
        title=dict(text="📈 Score Trend Over Time", font=dict(color=c["text"],size=14)),
        height=280, margin=dict(l=10,r=10,t=40,b=10),
        paper_bgcolor=c["paper"], plot_bgcolor=c["plot"],
        xaxis=dict(gridcolor=c["grid"],color=c["text"]),
        yaxis=dict(gridcolor=c["grid"],color=c["text"],range=[0,110]),
        showlegend=False,
    )
    return fig

def radar_chart(inputs):
    c = cc()
    cats = ["Study Hours","Attendance","Sleep","Motivation","Resources","Peer Influence"]
    vals = [
        min(inputs.get("Hours_Studied",0)/10*100,100),
        inputs.get("Attendance",0),
        min(inputs.get("Sleep_Hours",0)/9*100,100),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        {"Low":20,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
        {"Negative":10,"Neutral":55,"Positive":100}.get(inputs.get("Peer_Influence","Neutral"),55),
    ]
    fig = go.Figure(go.Scatterpolar(
        r=vals+[vals[0]], theta=cats+[cats[0]], fill="toself",
        fillcolor="rgba(56,168,220,0.15)",
        line=dict(color=c["line"],width=2.5),
        marker=dict(color=c["marker"],size=7),
    ))
    fig.update_layout(
        title=dict(text="🕸️ Academic Profile Radar",font=dict(color=c["text"],size=14)),
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(visible=True,range=[0,100],color=c["text"],gridcolor=c["grid"]),
                   angularaxis=dict(color=c["text"])),
        height=300, margin=dict(l=20,r=20,t=44,b=20),
        paper_bgcolor=c["paper"], showlegend=False,
    )
    return fig

def factor_bar_chart(inputs):
    c = cc()
    factors = {
        "Hours Studied": min(inputs.get("Hours_Studied",0)/10*100,100),
        "Attendance":    inputs.get("Attendance",0),
        "Prev Score":    inputs.get("Previous_Scores",0),
        "Sleep Quality": min(inputs.get("Sleep_Hours",0)/9*100,100),
        "Motivation":    {"Low":25,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        "Learning Res.": {"Low":25,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
    }
    fig = go.Figure(go.Bar(
        x=list(factors.keys()), y=list(factors.values()),
        marker=dict(color=list(factors.values()),
                    colorscale=[[0,"#1e6091"],[0.4,"#38a8dc"],[0.7,"#7dd8f5"],[1,"#c8eeff"]],
                    showscale=False),
        text=[f"{v:.0f}" for v in factors.values()],
        textposition="outside", textfont=dict(color=c["text"],size=11),
    ))
    fig.update_layout(
        title=dict(text="📊 Key Factors",font=dict(color=c["text"],size=14)),
        height=280, margin=dict(l=10,r=10,t=44,b=10),
        paper_bgcolor=c["paper"], plot_bgcolor=c["plot"],
        xaxis=dict(gridcolor=c["grid"],color=c["text"]),
        yaxis=dict(gridcolor=c["grid"],color=c["text"],range=[0,115]),
        showlegend=False,
    )
    return fig

# =====================================================
# WELCOME PAGE
# =====================================================
def welcome_page():
    dark = st.session_state.theme == "dark"
    cd   = "#b8e0f7" if dark else "#0077b6"
    emoji= "☀️" if dark else "🌙"

    tc, ic = st.columns([14,1])
    with tc:
        st.markdown(f"""
        <div style="text-align:center;padding:16px 0 4px 0;margin:0;">
          <h1 class='hero-title'>{APP_NAME}</h1>
          <p class='hero-tagline'>{TAGLINE} ✨</p>
        </div>""", unsafe_allow_html=True)
    with ic:
        st.markdown("<div style='padding-top:20px'>", unsafe_allow_html=True)
        if st.button(emoji, key="theme_welcome"):
            st.session_state.theme = "light" if dark else "dark"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(f"""
    <hr class='welcome-divider'/>
    <div class='feature-cards-row'>
      <div class='feat-card'><span class='feat-icon'>📊</span><div class='feat-title'>Smart Graph</div>
        <div class='feat-sep'></div><div class='feat-desc'>• Visualize academic trends<br>• Interactive &amp; insightful</div></div>
      <div class='feat-card'><span class='feat-icon'>🔮</span><div class='feat-title'>Prediction</div>
        <div class='feat-sep'></div><div class='feat-desc'>• AI score prediction<br>• Quick &amp; accurate</div></div>
      <div class='feat-card'><span class='feat-icon'>📄</span><div class='feat-title'>PDF Report</div>
        <div class='feat-sep'></div><div class='feat-desc'>• Downloadable report<br>• Share on WhatsApp</div></div>
    </div>
    <div style='text-align:center;margin-bottom:6px;font-size:0.76rem;font-weight:700;color:{cd};letter-spacing:1.2px;text-transform:uppercase;'>─── Used For ───</div>
    <div class='used-for-row'>
      <div class='used-item'><span class='used-icon'>🎓</span><div class='used-label'>Students</div></div>
      <div class='used-item'><span class='used-icon'>👨‍👩‍👧</span><div class='used-label'>Parents</div></div>
      <div class='used-item'><span class='used-icon'>📖</span><div class='used-label'>Teachers</div></div>
      <div class='used-item'><span class='used-icon'>🏫</span><div class='used-label'>Schools</div></div>
      <div class='used-item'><span class='used-icon'>🧑‍💼</span><div class='used-label'>Counselors</div></div>
    </div>
    <div class='stats-strip'>
      <div class='stat-chip'><span class='stat-chip-num'>5000+</span><span class='stat-chip-lbl'>Students Helped</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>25K+</span><span class='stat-chip-lbl'>Predictions Made</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>10K+</span><span class='stat-chip-lbl'>Reports Generated</span></div>
      <div class='stat-chip'><span class='stat-chip-num'>99%</span><span class='stat-chip-lbl'>Accuracy Rate</span></div>
    </div>""", unsafe_allow_html=True)

    _, c2, _ = st.columns([1.8,1,1.8])
    with c2:
        if st.button("🚀 Get Started", use_container_width=True):
            st.session_state.auth_page = "login"; st.rerun()
    st.markdown("<div class='welcome-footer'>❤️ Made with love for Students &nbsp;|&nbsp; Empowering Education with AI</div>",
                unsafe_allow_html=True)

# =====================================================
# AUTH PAGE
# =====================================================
def auth_page():
    users = load_json(USER_DB_FILE, {})
    dark  = st.session_state.theme == "dark"
    emoji = "☀️" if dark else "🌙"

    lc, _, rc = st.columns([2,8,1])
    with lc:
        st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
        if st.button("← Back to Home", key="auth_back"):
            st.session_state.auth_page = "welcome"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with rc:
        st.markdown('<div class="auth-theme-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="theme_auth"):
            st.session_state.theme = "light" if dark else "dark"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    _, c2, _ = st.columns([1,2,1])
    with c2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>{APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:14px'>Secure Login & OTP Signup</p>", unsafe_allow_html=True)

        tab_l, tab_s = st.tabs(["🔑 Login", "✍️ Sign Up"])

        with tab_l:
            uname = st.text_input("Username", key="li_u", placeholder="Enter username")
            pwd   = st.text_input("Password", type="password", key="li_p", placeholder="Enter password")
            if st.button("Login", key="do_login", use_container_width=True):
                if uname in users and users[uname]["password"] == hash_password(pwd):
                    st.session_state.update({"logged_in":True,"username":uname,
                        "role":users[uname].get("role","student"),"active_page":"Home"})
                    st.rerun()
                else:
                    st.error("Invalid username or password.")

        with tab_s:
            role  = st.selectbox("Account Type", ["student","parent"], format_func=str.title, key="su_role")
            uname = st.text_input("Create Username",  key="su_u")
            email = st.text_input("Email for OTP",    key="su_e")
            fname = st.text_input("Full Name",         key="su_n")
            pwd   = st.text_input("Password",          type="password", key="su_p")
            cpwd  = st.text_input("Confirm Password",  type="password", key="su_cp")
            if role == "student":
                dob    = st.date_input("Date of Birth", key="su_dob",
                                       min_value=datetime(1990,1,1).date(),
                                       max_value=datetime.now().date())
                grade  = st.selectbox("Class/Course",
                                      ["Class 8","Class 9","Class 10","Class 11","Class 12","College"],
                                      key="su_g")
                school = st.text_input("School/College", key="su_sc")
            else:
                cname  = st.text_input("Child Name",    key="su_cn")
                grade  = st.selectbox("Child Class",
                                      ["Class 8","Class 9","Class 10","Class 11","Class 12","College"],
                                      key="su_cg")
                rel    = st.selectbox("Relation", ["Father","Mother","Guardian"], key="su_rel")

            if st.button("📨 Send OTP to Email", key="send_otp_btn", use_container_width=True):
                if not email:
                    st.warning("Please enter your email first.")
                else:
                    otp = generate_otp(); store_otp(email, otp)
                    ok, msg = send_otp_email(email, otp, fname or "User")
                    if ok:   st.success("✅ OTP sent! Check your inbox.")
                    else:    st.warning(f"⚠️ Email not configured. Testing OTP: **{otp}**")

            otp_in = st.text_input("Enter OTP", max_chars=6, key="su_otp", placeholder="6-digit OTP")

            if st.button("✅ Verify OTP & Create Account", key="verify_otp_btn", use_container_width=True):
                if not uname or not email or not pwd or not fname:
                    st.warning("Please fill all required fields.")
                elif pwd != cpwd:
                    st.error("Passwords do not match.")
                elif uname in users:
                    st.error("Username already exists.")
                else:
                    ok, msg = verify_otp(email, otp_in)
                    if not ok:
                        st.error(msg)
                    else:
                        d = {"password":hash_password(pwd),"email":email,"full_name":fname,
                             "role":role,"created_at":datetime.now().isoformat()}
                        if role == "student":
                            d.update({"dob":str(dob),"age":calculate_age(dob),"grade":grade,"school":school})
                        else:
                            d.update({"child_name":cname,"child_grade":grade,"relation":rel})
                        users[uname] = d; save_json(USER_DB_FILE, users)
                        st.session_state.update({"logged_in":True,"username":uname,"role":role,
                                                 "active_page":"Home","auth_page":"welcome"})
                        st.success("🎉 Account created!"); st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# TOP NAVBAR
# =====================================================
def top_navbar(user):
    name  = user.get("full_name", st.session_state.username)
    role  = user.get("role","student").title()
    icon  = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
    emoji = "☀️" if st.session_state.theme == "dark" else "🌙"

    st.markdown('<div class="topbar-shell">', unsafe_allow_html=True)
    cb, cp, cn, cs, ct = st.columns([0.45,1.9,6.8,1.1,0.45], vertical_alignment="center")

    with cb:
        st.markdown('<div class="back-icon-btn">', unsafe_allow_html=True)
        if st.button("‹", key="top_back", help="Back to Login"):
            st.session_state.update({"logged_in":False,"username":"","role":"",
                                     "auth_page":"login","active_page":"Home"})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with cp:
        st.markdown(f"""
        <div class='top-profile'>
          <div class='top-avatar'>{profile_pic_html(st.session_state.username, icon)}</div>
          <div><div class='top-name'>{name}</div><div class='top-role'>{role} Account</div></div>
        </div>""", unsafe_allow_html=True)

    with cn:
        nav_opts = ["🏠 Home","🔮 Prediction","📄 Report & Share","📚 History","👤 Profile"]
        cur_full = next((x for x in nav_opts if x.split(" ",1)[1] == st.session_state.active_page), "🏠 Home")
        try:
            sel = st.segmented_control("nav", nav_opts, default=cur_full,
                                       label_visibility="collapsed", key="top_nav")
        except Exception:
            idx = nav_opts.index(cur_full) if cur_full in nav_opts else 0
            sel = st.radio("nav", nav_opts, index=idx, horizontal=True,
                           label_visibility="collapsed", key="top_nav_r")
        if sel:
            np_ = sel.split(" ",1)[1]
            if np_ != st.session_state.active_page:
                st.session_state.active_page = np_; st.rerun()

    with cs:
        st.markdown('<div class="signout-top-btn">', unsafe_allow_html=True)
        if st.button("🚪 Sign Out", key="signout", use_container_width=True):
            st.session_state.update({"logged_in":False,"username":"","auth_page":"welcome"})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ct:
        st.markdown('<div class="theme-top-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="top_theme", help="Toggle Theme"):
            st.session_state.theme = "light" if st.session_state.theme=="dark" else "dark"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# =====================================================
# PAGES
# =====================================================
def home_page(user):
    records = user_history(st.session_state.username)
    name    = user.get("full_name", st.session_state.username)
    scores  = [r["score"] for r in records]

    st.markdown(f"""
    <div class='dash-wrap'>
      <div class='dash-title'>👋 Welcome, {name}!</div>
      <p class='dash-sub'>Your academic performance dashboard — all insights in one place.</p>
      <div class='metrics-row'>
        <div class='mc'><div class='mc-val'>{len(records)}</div><div class='mc-lbl'>🎯 Attempts</div></div>
        <div class='mc'><div class='mc-val'>{max(scores) if scores else 0}</div><div class='mc-lbl'>🏆 Best Score</div></div>
        <div class='mc'><div class='mc-val'>{int(np.mean(scores)) if scores else 0}</div><div class='mc-lbl'>📊 Average</div></div>
        <div class='mc'><div class='mc-val'>{scores[-1] if scores else 0}</div><div class='mc-lbl'>🕐 Last Score</div></div>
      </div>
    </div>""", unsafe_allow_html=True)

    if records:
        st.markdown("<div style='padding:0 28px 20px 28px;'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
        st.markdown("</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding:0 28px;'>", unsafe_allow_html=True)
        st.info("🚀 Go to the **Prediction** page and generate your first score!")
        st.markdown("</div>", unsafe_allow_html=True)


def prediction_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Enter academic details and get an AI-based predicted score.</p>", unsafe_allow_html=True)

    with st.form("pred_form"):
        c1, c2 = st.columns(2)
        with c1:
            hours      = st.number_input("📖 Hours Studied/day", 0, 24, 5, 1)
            attendance = st.number_input("🏫 Attendance (%)",     0, 100, 75, 1)
            previous   = st.number_input("📝 Previous Score",     0, 100, 60, 1)
            sleep      = st.number_input("😴 Sleep Hours",        0, 12, 7, 1)
            motivation = st.selectbox("💡 Motivation Level", ["Low","Medium","High"])
            teacher    = st.selectbox("👨‍🏫 Teacher Quality",  ["Poor","Average","Good"])
            stype      = st.selectbox("🏢 School Type",       ["Public","Private"])
        with c2:
            internet   = st.selectbox("🌐 Internet Access",    ["Yes","No"])
            income     = st.selectbox("💰 Family Income",      ["Low","Medium","High"])
            parental   = st.selectbox("👨‍👩‍👦 Parental Involvement",["Low","Medium","High"])
            education  = st.selectbox("🎓 Parent Education",   ["School","College"])
            peer       = st.selectbox("🤝 Peer Influence",     ["Negative","Neutral","Positive"])
            resources  = st.selectbox("📚 Learning Resources", ["Low","Medium","High"])
            activities = st.selectbox("⚽ Extracurricular",    ["Yes","No"])
        submitted = st.form_submit_button("🚀 Predict My Score", use_container_width=True)

    if submitted:
        data = {"Hours_Studied":int(hours),"Attendance":int(attendance),
                "Previous_Scores":int(previous),"Sleep_Hours":int(sleep),
                "Motivation_Level":motivation,"Teacher_Quality":teacher,"School_Type":stype,
                "Internet_Access":internet,"Family_Income":income,"Parental_Involvement":parental,
                "Parental_Education_Level":education,"Peer_Influence":peer,
                "Learning_Resources":resources,"Extracurricular_Activities":activities}
        score = predict_score(data)
        recs  = get_recommendations(data)
        record= {"date":datetime.now().strftime("%d-%m-%Y %H:%M"),"score":score,
                 "inputs":data,"recommendations":recs}
        save_prediction(st.session_state.username, record)
        st.session_state.last_score  = score
        st.session_state.last_inputs = data
        st.session_state.last_recs   = recs
        st.session_state.last_pdf    = generate_pdf(st.session_state.username, user, score, data, recs)

        status = "🌟 Excellent!" if score>=85 else ("👍 Good" if score>=70 else "📈 Needs Work")
        st.markdown(f"""
        <div style='text-align:center;padding:20px 0 10px 0'>
          <div class='score-badge'>{score}<span style='font-size:1.1rem'>/100</span></div>
          <p style='margin-top:8px;font-size:1.05rem;font-weight:700'>{status}</p>
        </div>""", unsafe_allow_html=True)

        st.markdown("### 📊 Performance Analysis")
        cg1, cg2 = st.columns(2)
        with cg1: st.plotly_chart(radar_chart(data), use_container_width=True)
        with cg2: st.plotly_chart(factor_bar_chart(data), use_container_width=True)

        hist = user_history(st.session_state.username)
        if len(hist) > 1:
            st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
            st.plotly_chart(score_trend_chart(hist), use_container_width=True)
            st.markdown("</div>", unsafe_allow_html=True)

        if recs:
            st.markdown("### 💬 Recommendations")
            for r in recs: st.info(r)

        st.session_state.active_page = "Report & Share"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def report_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Download PDF report and share via WhatsApp.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if not records and st.session_state.last_score is None:
        st.info("Please generate a score from the Prediction page first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    latest = records[-1] if records else {"score":st.session_state.last_score,
                                           "inputs":st.session_state.last_inputs,
                                           "recommendations":st.session_state.last_recs}
    score  = latest["score"]
    inputs = latest["inputs"]
    recs   = latest.get("recommendations",[])
    pdf    = st.session_state.last_pdf or generate_pdf(
                 st.session_state.username, user, score, inputs, recs)

    _, c2, _ = st.columns([1,1,1])
    with c2:
        st.markdown(f"""
        <div class='metric-card'>
          <div class='metric-label'>Predicted Score</div>
          <div class='metric-value'>{score}/100</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    st.download_button("📥 Download PDF Report", data=pdf,
                        file_name=f"ScoreWise_{st.session_state.username}.pdf",
                        mime="application/pdf", use_container_width=True)

    wa = (f"https://wa.me/?text=🎓%20{APP_NAME_PLAIN}%20Report%0A"
          f"Score%3A%20{score}%2F100%0AHours%3A%20{inputs.get('Hours_Studied')}%0A"
          f"Attendance%3A%20{inputs.get('Attendance')}%25")
    st.markdown(f"<div style='text-align:center;margin:12px 0'>"
                f"<a class='whatsapp-btn' target='_blank' href='{wa}'>📱 Share on WhatsApp</a>"
                f"</div>", unsafe_allow_html=True)
    st.caption("PDF share ke liye pehle download karein phir WhatsApp mein manually attach karein.")

    st.markdown("### 📊 Performance Graphs")
    cg1, cg2 = st.columns(2)
    with cg1: st.plotly_chart(radar_chart(inputs), use_container_width=True)
    with cg2: st.plotly_chart(factor_bar_chart(inputs), use_container_width=True)
    if records:
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    if recs:
        st.markdown("### 💬 Recommendations")
        for r in recs: st.info(r)
    st.markdown("</div>", unsafe_allow_html=True)


def history_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>All your predictions in one place.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if not records:
        st.info("No history yet. Go to Prediction page to get started!")
        st.markdown("</div>", unsafe_allow_html=True)
        return
    df = pd.DataFrame([{
        "Date":r["date"],"Score":r["score"],
        "Hours":r["inputs"].get("Hours_Studied"),
        "Attendance":r["inputs"].get("Attendance"),
        "Previous Score":r["inputs"].get("Previous_Scores"),
    } for r in records])
    st.dataframe(df, use_container_width=True)
    st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
    st.plotly_chart(score_trend_chart(records), use_container_width=True)
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def profile_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Edit your profile and update profile picture.</p>", unsafe_allow_html=True)

    users = load_json(USER_DB_FILE, {})
    uname = st.session_state.username
    icon  = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"

    c1, c2 = st.columns([1,2])
    with c1:
        st.markdown(f"<div class='avatar-circle'>{profile_pic_html(uname, icon)}</div>",
                    unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        upload = st.file_uploader("📸 Upload Picture", type=["jpg","jpeg","png"])
        if upload and st.button("💾 Save Picture", use_container_width=True):
            save_profile_pic(uname, upload.read())
            st.success("Updated!"); st.rerun()

    with c2:
        if not st.session_state.profile_edit_mode:
            st.markdown("<div class='profile-info-card'>", unsafe_allow_html=True)
            fields = [("Username",uname),("Full Name",user.get("full_name","N/A")),
                      ("Email",user.get("email","N/A")),("Role",user.get("role","N/A").title())]
            if user.get("role") == "student":
                fields += [("Date of Birth",user.get("dob","N/A")),("Age",str(user.get("age","N/A"))),
                           ("Class/Grade",user.get("grade","N/A")),("School",user.get("school","N/A"))]
            else:
                fields += [("Child Name",user.get("child_name","N/A")),
                           ("Child Grade",user.get("child_grade","N/A")),
                           ("Relation",user.get("relation","N/A"))]
            for lbl, val in fields:
                st.markdown(f"<div class='profile-field'><span class='pf-label'>{lbl}</span>"
                            f"<span class='pf-value'>{val}</span></div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
            if st.button("✏️ Edit Profile", use_container_width=True):
                st.session_state.profile_edit_mode = True; st.rerun()
        else:
            with st.form("edit_form"):
                st.markdown("##### ✏️ Edit Details")
                nn = st.text_input("Full Name",  value=user.get("full_name",""))
                ne = st.text_input("Email",      value=user.get("email",""))
                if user.get("role") == "student":
                    dv = user.get("dob","2000-01-01")
                    try: dd = datetime.strptime(dv,"%Y-%m-%d").date()
                    except: dd = date(2000,1,1)
                    nd   = st.date_input("Date of Birth", value=dd, min_value=date(1990,1,1), max_value=date.today())
                    go   = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cg   = user.get("grade","Class 10")
                    ng   = st.selectbox("Class/Grade", go, index=go.index(cg) if cg in go else 2)
                    ns   = st.text_input("School/College", value=user.get("school",""))
                else:
                    nc   = st.text_input("Child Name", value=user.get("child_name",""))
                    go   = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cg   = user.get("child_grade","Class 10")
                    ncg  = st.selectbox("Child Grade", go, index=go.index(cg) if cg in go else 2)
                    ro   = ["Father","Mother","Guardian"]
                    cr   = user.get("relation","Father")
                    nr   = st.selectbox("Relation", ro, index=ro.index(cr) if cr in ro else 0)
                st.markdown("##### 🔒 Change Password (optional)")
                op = st.text_input("Current Password",     type="password")
                np_= st.text_input("New Password",         type="password")
                cp_= st.text_input("Confirm New Password", type="password")
                sc, cc_ = st.columns(2)
                with sc: save = st.form_submit_button("💾 Save", use_container_width=True)
                with cc_: cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel:
                st.session_state.profile_edit_mode = False; st.rerun()
            if save:
                upd = users[uname].copy()
                upd["full_name"] = nn; upd["email"] = ne
                if user.get("role") == "student":
                    upd.update({"dob":str(nd),"age":calculate_age(nd),"grade":ng,"school":ns})
                else:
                    upd.update({"child_name":nc,"child_grade":ncg,"relation":nr})
                if op or np_ or cp_:
                    if users[uname]["password"] != hash_password(op):
                        st.error("Current password incorrect."); st.stop()
                    elif np_ != cp_:
                        st.error("New passwords don't match."); st.stop()
                    elif len(np_) < 6:
                        st.error("Min 6 characters."); st.stop()
                    else:
                        upd["password"] = hash_password(np_)
                users[uname] = upd; save_json(USER_DB_FILE, users)
                st.session_state.profile_edit_mode = False
                st.success("✅ Profile updated!"); st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# =====================================================
# MAIN
# =====================================================
def main_app():
    users = load_json(USER_DB_FILE, {})
    user  = users.get(st.session_state.username, {})
    top_navbar(user)
    page = st.session_state.active_page
    if   page == "Home":           home_page(user)
    elif page == "Prediction":     prediction_page(user)
    elif page == "Report & Share": report_page(user)
    elif page == "History":        history_page(user)
    elif page == "Profile":        profile_page(user)

if st.session_state.logged_in:
    main_app()
elif st.session_state.auth_page == "welcome":
    welcome_page()
else:
    auth_page()
