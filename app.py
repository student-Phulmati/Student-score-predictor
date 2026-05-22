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

# ─────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────
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

st.set_page_config(page_title=APP_NAME_PLAIN, page_icon="🎓",
                   layout="wide", initial_sidebar_state="collapsed")

# ─────────────────────────────────────────
# UTILS
# ─────────────────────────────────────────
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

def profile_pic_b64(username):
    path = os.path.join(PROFILE_PICS_DIR, f"{username}.jpg")
    if os.path.exists(path):
        with open(path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
        return f'<img src="data:image/jpeg;base64,{b64}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;" />'
    return None

def generate_otp():
    return str(random.randint(100000, 999999))

def store_otp(email, otp):
    data = load_json(OTP_FILE, {})
    data[email] = {"otp": otp, "timestamp": datetime.now().isoformat(), "verified": False}
    save_json(OTP_FILE, data)

def verify_otp(email, entered):
    data = load_json(OTP_FILE, {})
    if email not in data:
        return False, "OTP not found."
    saved = data[email]
    if (datetime.now() - datetime.fromisoformat(saved["timestamp"])).total_seconds() > 600:
        return False, "OTP expired."
    if saved["otp"] != entered:
        return False, "Invalid OTP."
    data[email]["verified"] = True
    save_json(OTP_FILE, data)
    return True, "OTP verified."

def send_otp_email(receiver, otp, name="User"):
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Your {APP_NAME_PLAIN} OTP"
        msg["From"] = EMAIL_SENDER
        msg["To"] = receiver
        html = f"""<div style='font-family:Arial;background:#0d1b2a;color:white;padding:26px;border-radius:18px'>
          <h2 style='color:#00d4ff'>{APP_NAME}</h2>
          <p>Hello <b>{name}</b>, your OTP is:</p>
          <div style='font-size:34px;letter-spacing:8px;font-weight:800;color:#00ffcc'>{otp}</div>
          <p>Valid for 10 minutes.</p></div>"""
        msg.attach(MIMEText(html, "html"))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_SENDER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_SENDER, receiver, msg.as_string())
        return True, "OTP sent."
    except Exception as e:
        return False, str(e)

# ─────────────────────────────────────────
# SESSION STATE
# ─────────────────────────────────────────
def init_state():
    defaults = {
        "logged_in": False, "username": "", "role": "",
        "auth_page": "welcome", "theme": "dark", "active_page": "Home",
        "last_score": None, "last_pdf": None, "last_inputs": {},
        "last_recs": [], "profile_edit_mode": False,
        "pending_save": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

init_state()

# ─────────────────────────────────────────
# CSS
# ─────────────────────────────────────────
def apply_css():
    dark = st.session_state.theme == "dark"
    is_auth = (not st.session_state.logged_in)

    STUDENT_BG = "https://images.unsplash.com/photo-1523240795612-9a054b0db644?auto=format&fit=crop&w=1920&q=80"
    WELCOME_BG = "https://images.unsplash.com/photo-1521587760476-6c12a4b040da?auto=format&fit=crop&w=1920&q=80"

    bg_url = WELCOME_BG if is_auth else STUDENT_BG

    if dark:
        overlay    = "linear-gradient(180deg,rgba(5,10,40,0.80) 0%,rgba(0,20,55,0.75) 100%)"
        card_bg    = "rgba(255,255,255,0.07)"
        card_hover = "rgba(255,255,255,0.12)"
        border_c   = "rgba(0,212,255,0.20)"
        text1      = "#e8f4ff"
        text2      = "#8ec8e8"
        textm      = "#4aaccc"
        acc        = "#00d4ff"
        acc2       = "#00ffcc"
        tb_bg      = "rgba(4,8,32,0.97)"
        tb_border  = "rgba(0,212,255,0.15)"
        tb_text    = "#e8f4ff"
        tb_sub     = "#4aaccc"
        nav_ac     = "#00d4ff"
        nav_abg    = "rgba(0,212,255,0.13)"
        inp_bg     = "rgba(8,18,52,0.93)"
        inp_text   = "#e0f4ff"
        inp_bd     = "rgba(0,212,255,0.28)"
        btn_g      = "linear-gradient(135deg,#0a1f6e,#0077b6,#00d4ff)"
        btn_h      = "linear-gradient(135deg,#0077b6,#00d4ff,#00ffcc)"
        shadow     = "0 8px 40px rgba(0,0,0,0.40)"
        score_c    = "#00ffcc"
    else:
        overlay    = "linear-gradient(180deg,rgba(230,245,255,0.84) 0%,rgba(210,238,255,0.82) 100%)"
        card_bg    = "rgba(255,255,255,0.78)"
        card_hover = "rgba(255,255,255,0.94)"
        border_c   = "rgba(0,119,182,0.22)"
        text1      = "#02314e"
        text2      = "#024f7a"
        textm      = "#0077b6"
        acc        = "#0077b6"
        acc2       = "#00b4d8"
        tb_bg      = "rgba(255,255,255,0.97)"
        tb_border  = "rgba(0,119,182,0.15)"
        tb_text    = "#02314e"
        tb_sub     = "#0077b6"
        nav_ac     = "#0077b6"
        nav_abg    = "rgba(0,119,182,0.10)"
        inp_bg     = "rgba(255,255,255,0.96)"
        inp_text   = "#02314e"
        inp_bd     = "rgba(0,119,182,0.26)"
        btn_g      = "linear-gradient(135deg,#023e8a,#0077b6,#00b4d8)"
        btn_h      = "linear-gradient(135deg,#0077b6,#00b4d8,#48cae4)"
        shadow     = "0 8px 40px rgba(0,80,140,0.18)"
        score_c    = "#0077b6"

    st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Syne:wght@600;700;800&family=DM+Sans:wght@400;500;600;700&display=swap');

*  {{ font-family:'DM Sans',sans-serif!important; box-sizing:border-box; }}
h1,h2,h3,.dash-title,.page-title,.hero-title,.top-name,.mc-val,.score-badge,.metric-value {{
    font-family:'Syne',sans-serif!important;
}}

/* ── hide streamlit chrome ── */
.stApp>header{{background:transparent!important;height:0!important;}}
[data-testid="stDecoration"]{{display:none!important;}}
#MainMenu,footer{{visibility:hidden;height:0;}}
[data-testid="stToolbar"]{{visibility:hidden!important;height:0!important;position:fixed!important;}}
[data-testid="stSidebar"],[data-testid="stSidebarNav"],
[data-testid="stSidebarCollapseButton"],[data-testid="collapsedControl"]{{
    display:none!important;visibility:hidden!important;width:0!important;min-width:0!important;
}}

/* ── full-bleed photo background ── */
.stApp{{
    background:{overlay}, url('{bg_url}') center/cover fixed !important;
    min-height:100vh;
}}
.main .block-container{{padding:0!important;margin:0!important;max-width:100%!important;}}
[data-testid="stHorizontalBlock"]{{gap:0!important;}}
[data-testid="stColumn"]{{padding:0!important;}}
[data-testid="stVerticalBlock"]>div{{margin-bottom:0!important;padding-bottom:0!important;}}
.element-container{{margin:0!important;padding:0!important;}}
div.stMarkdown{{margin:0!important;padding:0!important;}}
.stButton{{margin:0!important;}}

/* ════════════════════════════════════
   TOPBAR  — matches Image 2 exactly
════════════════════════════════════ */
.topbar-shell{{
    position:sticky;top:0;z-index:9999;
    width:100%;
    background:{tb_bg};
    border-bottom:1px solid {tb_border};
    box-shadow:0 2px 24px rgba(0,0,0,0.18);
    backdrop-filter:blur(28px) saturate(180%);
    -webkit-backdrop-filter:blur(28px) saturate(180%);
    padding:8px 20px 7px 14px;
    display:flex;align-items:center;gap:0;
}}

/* back chevron */
.back-icon-btn .stButton>button{{
    width:40px!important;min-width:40px!important;height:40px!important;
    border-radius:12px!important;padding:0!important;
    background:{'rgba(255,255,255,0.07)' if dark else 'rgba(0,80,140,0.07)'}!important;
    color:{tb_text}!important;border:1px solid {tb_border}!important;
    box-shadow:none!important;font-size:1.2rem!important;
    transition:all 0.15s!important;
}}
.back-icon-btn .stButton>button:hover{{
    background:{btn_g}!important;color:#fff!important;
    border-color:{acc}!important;transform:scale(1.07)!important;
}}

/* avatar */
.tb-avatar{{
    width:46px;height:46px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;overflow:hidden;
    background:linear-gradient(135deg,#1a237e,#0077b6,{acc});
    border:2.5px solid {acc}88;
    box-shadow:0 0 0 3px {acc}22;
    font-size:1.4rem;flex-shrink:0;
}}
.tb-avatar img{{width:100%;height:100%;object-fit:cover;border-radius:50%;}}
.tb-name{{font-size:0.94rem;font-weight:800;color:{tb_text};line-height:1.2;letter-spacing:-0.2px;}}
.tb-role{{font-size:0.68rem;font-weight:600;color:{tb_sub};text-transform:uppercase;letter-spacing:0.6px;}}

/* nav segmented */
div[data-testid="stSegmentedControl"]{{background:transparent!important;border:none!important;}}
div[data-testid="stSegmentedControl"] button{{
    border-radius:8px!important;background:transparent!important;
    color:{tb_sub}!important;box-shadow:none!important;border:0!important;
    font-weight:700!important;font-size:0.80rem!important;
    padding:6px 10px!important;transition:all 0.14s!important;
}}
div[data-testid="stSegmentedControl"] button[aria-pressed="true"]{{
    color:{nav_ac}!important;
    background:{nav_abg}!important;
    border-bottom:2.5px solid {nav_ac}!important;
    border-radius:8px 8px 0 0!important;
}}

/* sign out */
.signout-btn .stButton>button{{
    height:40px!important;border-radius:999px!important;
    padding:0 1.2rem!important;font-size:0.82rem!important;
    white-space:nowrap!important;
    background:{btn_g}!important;
    box-shadow:0 4px 16px {acc}33!important;
}}

/* theme toggle */
.theme-btn .stButton>button{{
    width:40px!important;min-width:40px!important;height:40px!important;
    border-radius:12px!important;padding:0!important;font-size:1.1rem!important;
    background:{'rgba(255,255,255,0.07)' if dark else 'rgba(0,80,140,0.07)'}!important;
    border:1px solid {tb_border}!important;color:{tb_text}!important;
    box-shadow:none!important;transition:all 0.15s!important;
}}
.theme-btn .stButton>button:hover{{
    background:{btn_g}!important;color:#fff!important;transform:scale(1.08)!important;
}}

/* ════════════════════════════════════
   CONTENT WRAPPER — zero top gap
════════════════════════════════════ */
.dash-wrap{{padding:22px 28px 28px 28px;width:100%;}}

.dash-title{{font-size:clamp(1.7rem,2.8vw,2.4rem);font-weight:800;color:{text1};
    margin:0 0 3px 0;letter-spacing:-0.8px;
    text-shadow:0 2px 16px rgba(0,0,0,0.15);}}
.dash-sub{{font-size:0.88rem;font-weight:500;color:{text2};margin:0 0 18px 0;}}
.page-title{{font-size:1.85rem;font-weight:800;margin:0 0 2px 0;color:{text1};letter-spacing:-0.5px;}}
.subtext{{color:{text2};font-size:0.88rem;margin:0 0 14px 0;font-weight:500;}}
.accent-line{{height:2px;background:linear-gradient(90deg,{acc}88,{acc2}55,transparent);
    border:none;border-radius:2px;margin:2px 0 16px 0;}}

/* ── metric cards ── */
.metrics-row{{display:grid;grid-template-columns:repeat(4,1fr);gap:14px;margin-bottom:18px;}}
.mc{{
    position:relative;overflow:hidden;
    background:{card_bg};border:1px solid {border_c};
    backdrop-filter:blur(22px) saturate(160%);
    -webkit-backdrop-filter:blur(22px) saturate(160%);
    border-radius:22px;padding:22px 10px 16px 10px;
    text-align:center;transition:transform 0.20s,box-shadow 0.20s;
    box-shadow:{shadow};
}}
.mc::before{{content:'';position:absolute;inset:0;
    background:linear-gradient(135deg,{acc}10 0%,transparent 65%);
    border-radius:22px;pointer-events:none;}}
.mc:hover{{transform:translateY(-4px) scale(1.01);
    box-shadow:0 20px 55px rgba(0,0,0,0.28),0 0 0 1px {acc}33;}}
.mc-icon{{font-size:1.6rem;display:block;margin-bottom:6px;}}
.mc-val{{font-size:2.5rem;font-weight:800;color:{acc};line-height:1.0;
    text-shadow:0 0 24px {acc}55;}}
.mc-lbl{{font-size:0.63rem;color:{textm};text-transform:uppercase;letter-spacing:1.6px;
    margin-top:5px;font-weight:700;}}

/* ── chart glass ── */
.chart-glass{{
    background:{card_bg};border:1px solid {border_c};
    box-shadow:{shadow};backdrop-filter:blur(22px) saturate(160%);
    border-radius:22px;padding:14px 14px 4px 14px;margin-bottom:16px;
    position:relative;overflow:hidden;
}}
.chart-glass::before{{content:'';position:absolute;top:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,{acc},{acc2},transparent);
    border-radius:22px 22px 0 0;}}

/* ── glass card (auth / welcome) ── */
.glass{{
    background:{card_bg};border:1px solid {border_c};
    box-shadow:{shadow};backdrop-filter:blur(26px) saturate(170%);
    border-radius:26px;padding:26px;
}}

/* ── score badge ── */
.score-badge{{
    display:inline-block;font-size:3.6rem;font-weight:800;
    color:{score_c};padding:16px 36px;border-radius:22px;
    background:{card_bg};border:1px solid {border_c};
    backdrop-filter:blur(18px);
    box-shadow:{shadow},inset 0 1px 0 rgba(255,255,255,0.08);
    text-shadow:0 0 28px {acc}77;
}}

/* ── metric card (report) ── */
.metric-card{{background:{card_bg};border:1px solid {border_c};
    box-shadow:{shadow};backdrop-filter:blur(18px);
    border-radius:20px;padding:20px 12px;text-align:center;}}
.metric-value{{font-size:2.2rem;font-weight:800;color:{score_c};
    text-shadow:0 0 20px {acc}55;}}
.metric-label{{font-size:0.68rem;color:{textm};text-transform:uppercase;
    letter-spacing:1.5px;margin-top:5px;font-weight:700;}}

/* ── profile ── */
.profile-info-card{{background:{card_bg};border:1px solid {border_c};
    backdrop-filter:blur(18px);border-radius:20px;padding:20px;box-shadow:{shadow};}}
.profile-field{{display:flex;justify-content:space-between;gap:12px;
    padding:9px 0;border-bottom:1px solid {border_c};font-size:0.89rem;}}
.profile-field:last-child{{border-bottom:none;}}
.pf-label{{color:{textm};font-weight:700;}}
.pf-value{{color:{text1};font-weight:600;}}
.avatar-circle{{width:86px;height:86px;border-radius:50%;
    display:flex;align-items:center;justify-content:center;overflow:hidden;margin:auto;
    border:3px solid {acc};
    background:linear-gradient(135deg,{acc},{acc2});
    font-size:2.2rem;
    box-shadow:0 0 0 5px {acc}22,0 8px 28px rgba(0,0,0,0.20);}}
.avatar-circle img{{width:100%;height:100%;object-fit:cover;border-radius:50%;}}

/* ── whatsapp ── */
.whatsapp-btn{{display:inline-block;border-radius:999px;padding:11px 26px;
    color:white!important;text-decoration:none;font-weight:700;margin:6px 4px;
    font-size:0.92rem;background:linear-gradient(135deg,#25D366,#128C7E);
    box-shadow:0 8px 24px rgba(0,0,0,0.18);transition:transform 0.18s;}}
.whatsapp-btn:hover{{transform:translateY(-2px);}}

/* ── ALL buttons ── */
.stButton>button,
[data-testid="stDownloadButton"] button,
.stFormSubmitButton>button{{
    border-radius:999px!important;border:0!important;font-weight:700!important;
    cursor:pointer!important;padding:0.58rem 1.4rem!important;
    background:{btn_g}!important;color:white!important;
    box-shadow:0 6px 20px {acc}28!important;transition:all 0.18s!important;
}}
.stButton>button:hover,
[data-testid="stDownloadButton"] button:hover,
.stFormSubmitButton>button:hover{{
    transform:translateY(-2px) scale(1.02)!important;
    box-shadow:0 14px 34px {acc}40!important;
    background:{btn_h}!important;
}}

/* ── inputs ── */
.stTextInput input,.stNumberInput input,.stDateInput input,
.stPasswordInput input,textarea{{
    background:{inp_bg}!important;color:{inp_text}!important;
    border:1.5px solid {inp_bd}!important;border-radius:12px!important;
    font-weight:500!important;caret-color:{inp_text}!important;
}}
.stSelectbox [data-baseweb="select"]>div{{
    background:{inp_bg}!important;color:{inp_text}!important;
    border:1.5px solid {inp_bd}!important;border-radius:12px!important;
}}
.stSelectbox [data-baseweb="select"] span,
.stSelectbox [data-baseweb="select"] div,
.stSelectbox [data-baseweb="select"] input{{color:{inp_text}!important;}}
[data-baseweb="menu"]{{background:{inp_bg}!important;}}
[data-baseweb="menu"] li{{color:{inp_text}!important;font-weight:500!important;}}
[data-baseweb="menu"] li:hover{{background:{acc}22!important;}}
[data-testid="stNumberInputField"] input{{color:{inp_text}!important;background:{inp_bg}!important;}}

/* labels */
label,p{{color:{text1}!important;}}
.stTextInput label,.stNumberInput label,.stSelectbox label,
.stDateInput label,.stRadio label,.stCheckbox label,
[data-baseweb="form-control"] label,.stSlider label{{
    color:{text1}!important;font-weight:600!important;font-size:0.85rem!important;
}}

/* tabs */
[data-baseweb="tab-list"]{{background:transparent!important;border-bottom:1px solid {border_c}!important;}}
[data-baseweb="tab"]{{color:{textm}!important;font-weight:700!important;}}
[aria-selected="true"][data-baseweb="tab"]{{color:{acc}!important;border-bottom:3px solid {acc}!important;}}

hr{{border-color:{border_c}!important;}}
.stAlert{{border-radius:16px!important;}}
.stDataFrame{{border-radius:16px;overflow:hidden;}}

/* ════════════════════════════════════
   WELCOME / AUTH PAGES
════════════════════════════════════ */
.hero-photo-card{{
    background:{card_bg};border:1px solid {border_c};
    backdrop-filter:blur(26px) saturate(160%);
    border-radius:30px;padding:34px 38px;
    max-width:820px;width:100%;box-shadow:{shadow};
    position:relative;overflow:hidden;
}}
.hero-photo-card::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;
    background:linear-gradient(90deg,{acc},{acc2},{acc});}}
.hero-title{{font-size:clamp(2.0rem,4vw,3.4rem);font-weight:800;color:{text1};
    margin:0 0 5px 0;letter-spacing:-1.2px;line-height:1.06;}}
.hero-tagline{{font-size:0.98rem;color:{text2};font-weight:500;margin:0 0 22px 0;}}
.feat-strip{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 18px 0;}}
.feat-card{{background:{'rgba(255,255,255,0.07)' if dark else 'rgba(255,255,255,0.68)'};
    border:1px solid {border_c};border-radius:16px;padding:18px 14px 14px 14px;
    text-align:center;transition:transform 0.18s,box-shadow 0.18s;position:relative;overflow:hidden;}}
.feat-card::after{{content:'';position:absolute;bottom:0;left:0;right:0;height:2px;
    background:linear-gradient(90deg,transparent,{acc},transparent);
    opacity:0;transition:opacity 0.18s;}}
.feat-card:hover{{transform:translateY(-4px);box-shadow:0 18px 44px rgba(0,0,0,0.20);}}
.feat-card:hover::after{{opacity:1;}}
.feat-icon{{font-size:1.9rem;display:block;margin-bottom:7px;}}
.feat-title{{font-size:0.98rem;font-weight:800;color:{text1};margin:0 0 5px 0;font-family:'Syne',sans-serif;}}
.feat-line{{width:30px;height:3px;background:linear-gradient(90deg,{acc},{acc2});
    border-radius:99px;margin:0 auto 7px auto;}}
.feat-desc{{font-size:0.74rem;color:{text2};font-weight:500;line-height:1.6;}}
.stats-strip{{display:flex;gap:9px;justify-content:center;flex-wrap:wrap;
    padding:13px 0;border-top:1px solid {border_c};border-bottom:1px solid {border_c};
    margin:0 0 18px 0;}}
.stat-chip{{display:flex;align-items:center;gap:6px;padding:6px 13px;
    border-radius:999px;background:{'rgba(0,212,255,0.10)' if dark else 'rgba(0,119,182,0.08)'};
    border:1px solid {border_c};}}
.stat-num{{font-size:1.02rem;font-weight:800;color:{text1};font-family:'Syne',sans-serif;}}
.stat-lbl{{font-size:0.64rem;font-weight:700;color:{textm};text-transform:uppercase;letter-spacing:0.7px;}}
.used-row{{display:flex;gap:14px;justify-content:center;flex-wrap:wrap;margin:0 0 18px 0;}}
.used-item{{text-align:center;padding:4px 6px;}}
.used-icon{{font-size:1.4rem;display:block;margin-bottom:3px;}}
.used-label{{font-size:0.62rem;font-weight:800;color:{textm};text-transform:uppercase;letter-spacing:0.7px;}}
.welcome-footer{{text-align:center;font-size:0.75rem;color:{textm};padding:8px 0 0 0;font-weight:500;}}

.back-btn-wrap .stButton>button{{
    background:{card_bg}!important;border:1.5px solid {border_c}!important;
    color:{text1}!important;box-shadow:0 2px 10px rgba(0,0,0,0.12)!important;
    padding:0.36rem 1.0rem!important;font-size:0.83rem!important;border-radius:999px!important;
}}
.back-btn-wrap .stButton>button:hover{{transform:translateX(-2px)!important;}}
.auth-theme-btn .stButton>button{{
    width:42px!important;height:40px!important;min-width:42px!important;
    border-radius:12px!important;padding:0!important;font-size:1.05rem!important;
    background:{'rgba(8,18,52,0.85)' if dark else 'rgba(255,255,255,0.85)'}!important;
    border:1.5px solid {border_c}!important;color:{text1}!important;
    box-shadow:0 3px 12px rgba(0,0,0,0.14)!important;
}}
.auth-theme-btn .stButton>button:hover{{
    transform:scale(1.07)!important;background:{btn_g}!important;color:white!important;
}}

/* ── save success banner ── */
.save-banner{{
    background:{'rgba(0,255,180,0.12)' if dark else 'rgba(0,180,120,0.10)'};
    border:1px solid {'rgba(0,255,180,0.30)' if dark else 'rgba(0,150,100,0.25)'};
    border-radius:14px;padding:12px 18px;
    display:flex;align-items:center;gap:10px;
    font-weight:700;font-size:0.95rem;color:{text1};
    margin-bottom:14px;backdrop-filter:blur(12px);
}}
</style>
""", unsafe_allow_html=True)

apply_css()

# ─────────────────────────────────────────
# MODEL
# ─────────────────────────────────────────
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

# ─────────────────────────────────────────
# HISTORY & PDF
# ─────────────────────────────────────────
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
    drawing.add(String(10, 145, "Score History", fontSize=12, fillColor=colors.HexColor("#0077b6")))
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
                             strokeColor=colors.HexColor("#0096c7"), strokeWidth=2))
        for i,(x,y) in enumerate(pts):
            drawing.add(String(x-5, y+6, str(scores[i]), fontSize=7, fillColor=colors.HexColor("#02314e")))
    return drawing

def generate_pdf(username, user_data, score, inputs, recs):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.6*inch, bottomMargin=0.6*inch,
                            leftMargin=0.7*inch, rightMargin=0.7*inch)
    sty = getSampleStyleSheet()
    TS = ParagraphStyle("T", parent=sty["Heading1"], alignment=1, fontSize=22,
                        textColor=colors.HexColor("#0077b6"), spaceAfter=4, fontName="Helvetica-Bold")
    SS = ParagraphStyle("S", parent=sty["Normal"], alignment=1, fontSize=10,
                        textColor=colors.HexColor("#0096c7"), spaceAfter=14, fontName="Helvetica")
    HS = ParagraphStyle("H", parent=sty["Heading2"], fontSize=13, textColor=colors.white,
                        spaceAfter=0, fontName="Helvetica-Bold",
                        backColor=colors.HexColor("#023e8a"), borderPadding=(8,10,8,10))
    NS = ParagraphStyle("N", parent=sty["Normal"], fontSize=10, leading=15, textColor=colors.HexColor("#02314e"))
    RS = ParagraphStyle("R", parent=sty["Normal"], fontSize=10, leading=15,
                        textColor=colors.HexColor("#023e8a"), leftIndent=10)
    story = [
        Paragraph(f"🎓 {APP_NAME_PLAIN}", TS),
        Paragraph("Official Student Performance Prediction Report", SS),
        Paragraph(f"Generated: {datetime.now().strftime('%d %B %Y  |  %I:%M %p')}", SS),
        Table([[""]], colWidths=[6.6*inch],
              style=[("LINEBELOW",(0,0),(-1,-1),1.2,colors.HexColor("#0096c7")),
                     ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]),
        Spacer(1,10)
    ]
    sname = user_data.get("full_name") or user_data.get("child_name") or username
    story.append(Paragraph("  Student Details", HS)); story.append(Spacer(1,4))
    info = [["Full Name",sname],["Username",username],["Email",user_data.get("email","N/A")],
            ["Role",user_data.get("role","N/A").title()]]
    if user_data.get("role") == "student":
        info += [["Grade",user_data.get("grade","N/A")],["School",user_data.get("school","N/A")],
                 ["DOB",user_data.get("dob","N/A")]]
    else:
        info += [["Child Name",user_data.get("child_name","N/A")],
                 ["Child Grade",user_data.get("child_grade","N/A")],
                 ["Relation",user_data.get("relation","N/A")]]
    t = Table([[Paragraph(f"<b>{r[0]}</b>",NS),Paragraph(r[1],NS)] for r in info],
              colWidths=[2.2*inch,4.4*inch])
    t.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#90e0ef")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),("FONTNAME",(1,0),(1,-1),"Helvetica")
    ]))
    story += [t, Spacer(1,14)]
    story.append(Paragraph("  Prediction Result", HS)); story.append(Spacer(1,4))
    stat = "Excellent!" if score>=85 else ("Good" if score>=70 else "Needs Improvement")
    sc = colors.HexColor("#0077b6") if score>=70 else colors.HexColor("#e85d04")
    tr = Table([[Paragraph("<b>Predicted Score</b>",NS),Paragraph(f"{score}/100",NS)],
                [Paragraph("<b>Status</b>",NS),Paragraph(stat,NS)]],
               colWidths=[2.2*inch,4.4*inch])
    tr.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#90e0ef")),
        ("BACKGROUND",(0,0),(0,-1),colors.HexColor("#e8f8fc")),
        ("BACKGROUND",(1,0),(1,0),colors.HexColor("#caf0f8")),
        ("FONTNAME",(0,0),(0,-1),"Helvetica-Bold"),
        ("FONTSIZE",(1,0),(1,0),13),("TEXTCOLOR",(1,0),(1,0),sc),("PADDING",(0,0),(-1,-1),9)
    ]))
    story += [tr, Spacer(1,14)]
    story.append(Paragraph("  Academic Inputs", HS)); story.append(Spacer(1,4))
    hdr  = [[Paragraph("<b>Factor</b>",NS),Paragraph("<b>Value</b>",NS)]]
    rows = [[Paragraph(k.replace("_"," "),NS),Paragraph(str(v),NS)] for k,v in inputs.items()]
    ti = Table(hdr+rows, colWidths=[2.9*inch,3.7*inch])
    ti.setStyle(TableStyle([
        ("GRID",(0,0),(-1,-1),.5,colors.HexColor("#90e0ef")),
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#023e8a")),
        ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),
        ("ROWBACKGROUNDS",(0,1),(-1,-1),[colors.white,colors.HexColor("#f0faff")]),
        ("PADDING",(0,0),(-1,-1),8)
    ]))
    story += [ti, Spacer(1,14)]
    sl = [r.get("score",0) for r in user_history(username)] + [score]
    if len(sl) > 1:
        story.append(Paragraph("  Score History Graph", HS)); story.append(Spacer(1,6))
        story += [simple_pdf_graph(sl[-10:]), Spacer(1,14)]
    story.append(Paragraph("  Recommendations", HS)); story.append(Spacer(1,6))
    if recs:
        for r in recs:
            clean = r
            for ch in ["📚","🏫","😴","🎯","📖","💡","🤝"," "]: clean = clean.lstrip(ch)
            story += [Paragraph("• "+clean.strip(), RS), Spacer(1,3)]
    else:
        story.append(Paragraph("Your inputs are strong. Keep up the great work!", RS))
    story += [
        Spacer(1,20),
        Table([[""]], colWidths=[6.6*inch],
              style=[("LINEABOVE",(0,0),(-1,-1),.8,colors.HexColor("#90e0ef")),
                     ("TOPPADDING",(0,0),(-1,-1),0),("BOTTOMPADDING",(0,0),(-1,-1),4)]),
        Paragraph(f"Generated by {APP_NAME_PLAIN}  |  {datetime.now().strftime('%d-%m-%Y')}  |  For academic guidance only.", SS)
    ]
    doc.build(story)
    buf.seek(0)
    return buf.read()

# ─────────────────────────────────────────
# CHARTS
# ─────────────────────────────────────────
def cc():
    dark = st.session_state.theme == "dark"
    return {
        "paper":"rgba(0,0,0,0)","plot":"rgba(0,0,0,0)",
        "line":  "#00d4ff" if dark else "#0077b6",
        "line2": "#00ffcc" if dark else "#00b4d8",
        "marker":"#00d4ff" if dark else "#0096c7",
        "text":  "#8ec8e8" if dark else "#02314e",
        "grid":  "rgba(0,212,255,0.09)" if dark else "rgba(0,119,182,0.08)",
        "fill":  "rgba(0,212,255,0.08)" if dark else "rgba(0,180,216,0.07)",
    }

def score_trend_chart(records):
    c = cc()
    scores = [r["score"] for r in records]
    labels = [r.get("date", f"#{i+1}") for i,r in enumerate(records)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=labels, y=scores, mode="lines+markers+text",
        text=scores, textposition="top center",
        textfont=dict(color=c["text"], size=11),
        line=dict(width=3, color=c["line"]),
        marker=dict(size=11, color=c["marker"], line=dict(width=2.5, color="white")),
        fill="tozeroy", fillcolor=c["fill"],
    ))
    fig.add_hline(y=60, line_dash="dash", line_color=c["line"],
                  annotation_text="Pass Line", annotation_font_color=c["line"])
    fig.add_hline(y=85, line_dash="dot", line_color=c["line2"],
                  annotation_text="Excellent", annotation_font_color=c["line2"])
    fig.update_layout(
        title=dict(text="📈 Score Trend Over Time", font=dict(color=c["text"], size=14)),
        height=290, margin=dict(l=10,r=10,t=42,b=10),
        paper_bgcolor=c["paper"], plot_bgcolor=c["plot"],
        xaxis=dict(gridcolor=c["grid"],color=c["text"]),
        yaxis=dict(gridcolor=c["grid"],color=c["text"],range=[0,115]),
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
        fillcolor=c["fill"], line=dict(color=c["line"], width=2.5),
        marker=dict(color=c["marker"], size=7),
    ))
    fig.update_layout(
        title=dict(text="🕸️ Academic Profile Radar", font=dict(color=c["text"], size=14)),
        polar=dict(bgcolor="rgba(0,0,0,0)",
                   radialaxis=dict(visible=True, range=[0,100], color=c["text"], gridcolor=c["grid"]),
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
        "Sleep":         min(inputs.get("Sleep_Hours",0)/9*100,100),
        "Motivation":    {"Low":25,"Medium":60,"High":100}.get(inputs.get("Motivation_Level","Medium"),60),
        "Resources":     {"Low":25,"Medium":60,"High":100}.get(inputs.get("Learning_Resources","Medium"),60),
    }
    fig = go.Figure(go.Bar(
        x=list(factors.keys()), y=list(factors.values()),
        marker=dict(color=list(factors.values()),
                    colorscale=[[0,"#023e8a"],[0.4,"#0077b6"],[0.7,"#00b4d8"],[1,"#00d4ff"]],
                    showscale=False),
        text=[f"{v:.0f}" for v in factors.values()],
        textposition="outside", textfont=dict(color=c["text"], size=11),
    ))
    fig.update_layout(
        title=dict(text="📊 Key Factors", font=dict(color=c["text"], size=14)),
        height=290, margin=dict(l=10,r=10,t=44,b=10),
        paper_bgcolor=c["paper"], plot_bgcolor=c["plot"],
        xaxis=dict(gridcolor=c["grid"],color=c["text"]),
        yaxis=dict(gridcolor=c["grid"],color=c["text"],range=[0,118]),
        showlegend=False,
    )
    return fig

# ─────────────────────────────────────────
# WELCOME PAGE
# ─────────────────────────────────────────
def welcome_page():
    dark  = st.session_state.theme == "dark"
    emoji = "☀️" if dark else "🌙"

    tc, ic = st.columns([13, 1])
    with ic:
        st.markdown("<div style='padding-top:16px'>", unsafe_allow_html=True)
        if st.button(emoji, key="theme_welcome"):
            st.session_state.theme = "light" if dark else "dark"; st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    _, cc2, _ = st.columns([1, 3.4, 1])
    with cc2:
        st.markdown(f"""
<div class="hero-photo-card">
  <div style="text-align:center;margin-bottom:20px;">
    <div style="font-size:3rem;margin-bottom:6px;">🎓</div>
    <h1 class="hero-title">{APP_NAME_PLAIN}</h1>
    <p class="hero-tagline">{TAGLINE} ✨</p>
  </div>
  <div class="feat-strip">
    <div class="feat-card"><span class="feat-icon">📊</span>
      <div class="feat-title">Smart Graphs</div><div class="feat-line"></div>
      <div class="feat-desc">Visualize academic trends with interactive charts</div></div>
    <div class="feat-card"><span class="feat-icon">🔮</span>
      <div class="feat-title">AI Prediction</div><div class="feat-line"></div>
      <div class="feat-desc">ML-powered score prediction — quick & accurate</div></div>
    <div class="feat-card"><span class="feat-icon">📄</span>
      <div class="feat-title">PDF Reports</div><div class="feat-line"></div>
      <div class="feat-desc">Download & share detailed report on WhatsApp</div></div>
  </div>
  <div class="stats-strip">
    <div class="stat-chip"><span class="stat-num">5000+</span><span class="stat-lbl">Students</span></div>
    <div class="stat-chip"><span class="stat-num">25K+</span><span class="stat-lbl">Predictions</span></div>
    <div class="stat-chip"><span class="stat-num">10K+</span><span class="stat-lbl">Reports</span></div>
    <div class="stat-chip"><span class="stat-num">99%</span><span class="stat-lbl">Accuracy</span></div>
  </div>
  <div class="used-row">
    <div class="used-item"><span class="used-icon">🎓</span><div class="used-label">Students</div></div>
    <div class="used-item"><span class="used-icon">👨‍👩‍👧</span><div class="used-label">Parents</div></div>
    <div class="used-item"><span class="used-icon">📖</span><div class="used-label">Teachers</div></div>
    <div class="used-item"><span class="used-icon">🏫</span><div class="used-label">Schools</div></div>
    <div class="used-item"><span class="used-icon">🧑‍💼</span><div class="used-label">Counselors</div></div>
  </div>
</div>
""", unsafe_allow_html=True)
        st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
        _, gb, _ = st.columns([1.2, 2, 1.2])
        with gb:
            if st.button("🚀  Get Started", use_container_width=True):
                st.session_state.auth_page = "login"; st.rerun()
        st.markdown("<div class='welcome-footer'>❤️ Made with love for Students · Empowering Education with AI</div>",
                    unsafe_allow_html=True)

# ─────────────────────────────────────────
# AUTH PAGE
# ─────────────────────────────────────────
def auth_page():
    users = load_json(USER_DB_FILE, {})
    dark  = st.session_state.theme == "dark"
    emoji = "☀️" if dark else "🌙"

    lc, _, rc = st.columns([2, 8, 1])
    with lc:
        st.markdown('<div class="back-btn-wrap">', unsafe_allow_html=True)
        if st.button("← Back", key="auth_back"):
            st.session_state.auth_page = "welcome"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with rc:
        st.markdown('<div class="auth-theme-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="theme_auth"):
            st.session_state.theme = "light" if dark else "dark"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    _, c2, _ = st.columns([1, 2.2, 1])
    with c2:
        st.markdown("<div class='glass'>", unsafe_allow_html=True)
        st.markdown(f"<h2 style='text-align:center;margin-bottom:2px'>{APP_NAME}</h2>", unsafe_allow_html=True)
        st.markdown("<p class='subtext' style='text-align:center;margin-bottom:12px'>Secure Login & OTP Signup</p>",
                    unsafe_allow_html=True)
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
                    ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_g")
                school = st.text_input("School/College", key="su_sc")
            else:
                cname  = st.text_input("Child Name", key="su_cn")
                grade  = st.selectbox("Child Class",
                    ["Class 8","Class 9","Class 10","Class 11","Class 12","College"], key="su_cg")
                rel    = st.selectbox("Relation", ["Father","Mother","Guardian"], key="su_rel")

            if st.button("📨 Send OTP to Email", key="send_otp_btn", use_container_width=True):
                if not email:
                    st.warning("Please enter email first.")
                else:
                    otp = generate_otp(); store_otp(email, otp)
                    ok, msg = send_otp_email(email, otp, fname or "User")
                    if ok:  st.success("✅ OTP sent!")
                    else:   st.warning(f"⚠️ Email not configured. Test OTP: **{otp}**")

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

# ─────────────────────────────────────────
# TOP NAVBAR  (matches Image 2 structure)
# ─────────────────────────────────────────
def top_navbar(user):
    name  = user.get("full_name", st.session_state.username)
    role  = user.get("role","student").title()
    icon  = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
    emoji = "☀️" if st.session_state.theme == "dark" else "🌙"
    pic   = profile_pic_b64(st.session_state.username)
    avatar_html = f'<img src="{pic}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;"/>' if pic else icon

    st.markdown('<div class="topbar-shell">', unsafe_allow_html=True)
    cb, cp, cn, cs, ct = st.columns([0.42, 2.0, 7.0, 1.05, 0.42], vertical_alignment="center")

    with cb:
        st.markdown('<div class="back-icon-btn">', unsafe_allow_html=True)
        if st.button("‹", key="top_back"):
            st.session_state.update({"logged_in":False,"username":"","role":"",
                                     "auth_page":"login","active_page":"Home"})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with cp:
        st.markdown(f"""
<div style="display:flex;align-items:center;gap:10px;padding:2px 0;">
  <div class="tb-avatar">{avatar_html}</div>
  <div>
    <div class="tb-name">{name}</div>
    <div class="tb-role">{role} Account</div>
  </div>
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
        st.markdown('<div class="signout-btn">', unsafe_allow_html=True)
        if st.button("🚪 Sign Out", key="signout", use_container_width=True):
            st.session_state.update({"logged_in":False,"username":"","auth_page":"welcome"})
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with ct:
        st.markdown('<div class="theme-btn">', unsafe_allow_html=True)
        if st.button(emoji, key="top_theme"):
            st.session_state.theme = "light" if st.session_state.theme=="dark" else "dark"; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

# ─────────────────────────────────────────
# PAGE: HOME
# ─────────────────────────────────────────
def home_page(user):
    records = user_history(st.session_state.username)
    name    = user.get("full_name", st.session_state.username)
    scores  = [r["score"] for r in records]
    hr      = datetime.now().hour
    greet   = "Good Morning" if hr < 12 else ("Good Evening" if hr >= 17 else "Good Afternoon")

    st.markdown(f"""
<div class='dash-wrap'>
  <div class='dash-title'>👋 {greet}, {name}!</div>
  <p class='dash-sub'>Your academic performance dashboard — all insights in one place.</p>
  <hr class="accent-line"/>
  <div class='metrics-row'>
    <div class='mc'><span class='mc-icon'>🎯</span>
      <div class='mc-val'>{len(records)}</div><div class='mc-lbl'>Attempts</div></div>
    <div class='mc'><span class='mc-icon'>🏆</span>
      <div class='mc-val'>{max(scores) if scores else 0}</div><div class='mc-lbl'>Best Score</div></div>
    <div class='mc'><span class='mc-icon'>📊</span>
      <div class='mc-val'>{int(np.mean(scores)) if scores else 0}</div><div class='mc-lbl'>Average</div></div>
    <div class='mc'><span class='mc-icon'>🕐</span>
      <div class='mc-val'>{scores[-1] if scores else 0}</div><div class='mc-lbl'>Last Score</div></div>
  </div>
</div>""", unsafe_allow_html=True)

    if records:
        st.markdown("<div style='padding:0 28px 24px 28px;'>", unsafe_allow_html=True)
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
        st.markdown("</div></div>", unsafe_allow_html=True)
    else:
        st.markdown("<div style='padding:0 28px;'>", unsafe_allow_html=True)
        st.info("🚀 Go to **Prediction** page to get your first score!")
        st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# PAGE: PREDICTION  ← KEY CHANGES HERE
# ─────────────────────────────────────────
def prediction_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>🔮 Score Prediction</div>", unsafe_allow_html=True)
    st.markdown("<hr class='accent-line'/>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Fill in the details and click Predict — result will open in Report page.</p>",
                unsafe_allow_html=True)

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

        submitted = st.form_submit_button("🚀  Predict My Score", use_container_width=True)

    if submitted:
        data = {
            "Hours_Studied":int(hours),"Attendance":int(attendance),
            "Previous_Scores":int(previous),"Sleep_Hours":int(sleep),
            "Motivation_Level":motivation,"Teacher_Quality":teacher,"School_Type":stype,
            "Internet_Access":internet,"Family_Income":income,"Parental_Involvement":parental,
            "Parental_Education_Level":education,"Peer_Influence":peer,
            "Learning_Resources":resources,"Extracurricular_Activities":activities,
        }
        score = predict_score(data)
        recs  = get_recommendations(data)

        # Store in session — do NOT save to history yet (user must press Save)
        st.session_state.last_score  = score
        st.session_state.last_inputs = data
        st.session_state.last_recs   = recs
        st.session_state.last_pdf    = None          # will be generated lazily in report page
        st.session_state.pending_save = True         # flag: unsaved prediction

        # Redirect to Report & Share page
        st.session_state.active_page = "Report & Share"
        st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# PAGE: REPORT & SHARE  ← KEY CHANGES HERE
# ─────────────────────────────────────────
def report_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📄 Report & Share</div>", unsafe_allow_html=True)
    st.markdown("<hr class='accent-line'/>", unsafe_allow_html=True)

    # ── nothing to show ──
    if st.session_state.last_score is None and not user_history(st.session_state.username):
        st.info("Please generate a score from the Prediction page first.")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    # Prefer unsaved session result; else use latest history
    if st.session_state.last_score is not None:
        score  = st.session_state.last_score
        inputs = st.session_state.last_inputs
        recs   = st.session_state.last_recs
    else:
        latest = user_history(st.session_state.username)[-1]
        score  = latest["score"]
        inputs = latest["inputs"]
        recs   = latest.get("recommendations",[])

    # Generate PDF once
    if st.session_state.last_pdf is None:
        st.session_state.last_pdf = generate_pdf(
            st.session_state.username, user, score, inputs, recs)
    pdf = st.session_state.last_pdf

    # ── SCORE DISPLAY ──
    status = "🌟 Excellent!" if score>=85 else ("👍 Good" if score>=70 else "📈 Needs Improvement")
    _, mid, _ = st.columns([1.2, 1, 1.2])
    with mid:
        st.markdown(f"""
<div style='text-align:center;padding:10px 0 18px 0;'>
  <div class='score-badge'>{score}<span style='font-size:1.1rem;opacity:0.65'>/100</span></div>
  <p style='margin-top:10px;font-size:1.05rem;font-weight:700'>{status}</p>
</div>""", unsafe_allow_html=True)

    # ── SAVE BUTTON (only if prediction is unsaved) ──
    if st.session_state.pending_save:
        st.markdown("<div style='max-width:460px;margin:0 auto 16px auto;'>", unsafe_allow_html=True)
        if st.button("💾  Save Result to History", use_container_width=True, key="save_result"):
            record = {
                "date":   datetime.now().strftime("%d-%m %H:%M"),
                "score":  score,
                "inputs": inputs,
                "recommendations": recs,
            }
            save_prediction(st.session_state.username, record)
            st.session_state.pending_save = False
            st.success("✅ Result saved to history!")
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("""<div class='save-banner'>✅ &nbsp;Result saved to history.</div>""",
                    unsafe_allow_html=True)

    # ── DOWNLOAD + WHATSAPP ──
    dl_col, wa_col = st.columns(2)
    with dl_col:
        st.download_button("📥 Download PDF Report", data=pdf,
                           file_name=f"ScoreWise_{st.session_state.username}.pdf",
                           mime="application/pdf", use_container_width=True)
    with wa_col:
        wa = (f"https://wa.me/?text=🎓%20{APP_NAME_PLAIN}%20Result%0A"
              f"Score%3A%20{score}%2F100%0AAttendance%3A%20{inputs.get('Attendance')}%25%0A"
              f"Hours%3A%20{inputs.get('Hours_Studied')}hrs%2Fday")
        st.markdown(f"<div style='padding-top:6px;text-align:center'>"
                    f"<a class='whatsapp-btn' target='_blank' href='{wa}'>📱 Share on WhatsApp</a>"
                    f"</div>", unsafe_allow_html=True)

    st.caption("PDF share ke liye pehle download karein, phir WhatsApp mein manually attach karein.")

    # ── GRAPHS ──
    st.markdown("### 📊 Performance Analysis")
    cg1, cg2 = st.columns(2)
    with cg1:
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(radar_chart(inputs), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    with cg2:
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(factor_bar_chart(inputs), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if len(records) > 1:
        st.markdown("<div class='chart-glass'>", unsafe_allow_html=True)
        st.plotly_chart(score_trend_chart(records), use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    if recs:
        st.markdown("### 💬 Recommendations")
        for r in recs: st.info(r)

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# PAGE: HISTORY
# ─────────────────────────────────────────
def history_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>📚 Prediction History</div>", unsafe_allow_html=True)
    st.markdown("<hr class='accent-line'/>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>All your saved predictions in one place.</p>", unsafe_allow_html=True)

    records = user_history(st.session_state.username)
    if not records:
        st.info("No history yet. Go to Prediction page and save a result!")
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

# ─────────────────────────────────────────
# PAGE: PROFILE
# ─────────────────────────────────────────
def profile_page(user):
    st.markdown("<div class='dash-wrap'>", unsafe_allow_html=True)
    st.markdown("<div class='page-title'>👤 My Profile</div>", unsafe_allow_html=True)
    st.markdown("<hr class='accent-line'/>", unsafe_allow_html=True)
    st.markdown("<p class='subtext'>Edit your profile and update profile picture.</p>", unsafe_allow_html=True)

    users = load_json(USER_DB_FILE, {})
    uname = st.session_state.username
    icon  = "🎓" if user.get("role") == "student" else "👨‍👩‍👧"
    pic   = profile_pic_b64(uname)
    av    = f'<img src="{pic}" style="width:100%;height:100%;object-fit:cover;border-radius:50%;"/>' if pic else icon

    c1, c2 = st.columns([1, 2])
    with c1:
        st.markdown(f"<div class='avatar-circle'>{av}</div>", unsafe_allow_html=True)
        st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)
        upload = st.file_uploader("📸 Upload Picture", type=["jpg","jpeg","png"])
        if upload and st.button("💾 Save Picture", use_container_width=True):
            save_profile_pic(uname, upload.read()); st.success("Updated!"); st.rerun()

    with c2:
        if not st.session_state.profile_edit_mode:
            st.markdown("<div class='profile-info-card'>", unsafe_allow_html=True)
            fields = [("Username",uname),("Full Name",user.get("full_name","N/A")),
                      ("Email",user.get("email","N/A")),("Role",user.get("role","N/A").title())]
            if user.get("role") == "student":
                fields += [("DOB",user.get("dob","N/A")),("Age",str(user.get("age","N/A"))),
                           ("Grade",user.get("grade","N/A")),("School",user.get("school","N/A"))]
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
                nn = st.text_input("Full Name", value=user.get("full_name",""))
                ne = st.text_input("Email",     value=user.get("email",""))
                if user.get("role") == "student":
                    dv = user.get("dob","2000-01-01")
                    try: dd = datetime.strptime(dv,"%Y-%m-%d").date()
                    except: dd = date(2000,1,1)
                    nd = st.date_input("DOB", value=dd, min_value=date(1990,1,1), max_value=date.today())
                    go = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cg = user.get("grade","Class 10")
                    ng = st.selectbox("Grade", go, index=go.index(cg) if cg in go else 2)
                    ns = st.text_input("School/College", value=user.get("school",""))
                else:
                    nc  = st.text_input("Child Name", value=user.get("child_name",""))
                    go  = ["Class 8","Class 9","Class 10","Class 11","Class 12","College"]
                    cg  = user.get("child_grade","Class 10")
                    ncg = st.selectbox("Child Grade", go, index=go.index(cg) if cg in go else 2)
                    ro  = ["Father","Mother","Guardian"]
                    cr  = user.get("relation","Father")
                    nr  = st.selectbox("Relation", ro, index=ro.index(cr) if cr in ro else 0)
                st.markdown("##### 🔒 Change Password (optional)")
                op  = st.text_input("Current Password",     type="password")
                np_ = st.text_input("New Password",         type="password")
                cp_ = st.text_input("Confirm New Password", type="password")
                sc_col, cc_col = st.columns(2)
                with sc_col:  save_btn   = st.form_submit_button("💾 Save",   use_container_width=True)
                with cc_col:  cancel_btn = st.form_submit_button("❌ Cancel", use_container_width=True)

            if cancel_btn:
                st.session_state.profile_edit_mode = False; st.rerun()
            if save_btn:
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
                        st.error("Passwords don't match."); st.stop()
                    elif len(np_) < 6:
                        st.error("Min 6 characters."); st.stop()
                    else:
                        upd["password"] = hash_password(np_)
                users[uname] = upd; save_json(USER_DB_FILE, users)
                st.session_state.profile_edit_mode = False
                st.success("✅ Profile updated!"); st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────
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
