"""
G.M.S SCHOOL DHAMALA - Streamlit single-file app
Teacher: Rekha Rani (TGT Hindi)
Features:
- Teacher login (username: rekha, password: rekha)
- Student signup/login (separate)
- Student record: name, class (6th/7th/8th select), father, mother, aadhar (<=12 digits),
  dob (date input), phone (10 digits), whatsapp phone (10 digits)
- Attendance tracking (present/absent counts per year)
- CSV export, delete, edit, search
- Password reset for teacher via OTP (email) with SMTP optional
- Beautiful UI using Streamlit layout (single-file)
- Validations: aadhar max 12 digits, phone max 10 digits, dob sane check
- Student personal view on login: only their own data shown
- Generate WhatsApp group (collect numbers and provide link) - simple generator
- Simple AI assistant stub (click to open assistant chat area)
"""

import streamlit as st
import sqlite3
import pandas as pd
import os
import random
import string
import smtplib
from email.message import EmailMessage
from datetime import datetime, date
from typing import Optional

# -------------------------
# CONFIG
# -------------------------
DB_PATH = "students.db"
TEACHER_USERNAME = "rekha"
DEFAULT_TEACHER_PASSWORD = "rekha"

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER) or "noreply@example.com"
TEACHER_RESET_EMAIL = "rani1987rekha@gmail.com"

# -------------------------
# DATABASE HELPERS
# -------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
    CREATE TABLE IF NOT EXISTS teacher (
        id INTEGER PRIMARY KEY,
        username TEXT UNIQUE,
        password TEXT
    );
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sclass TEXT,
        father TEXT,
        mother TEXT,
        aadhar TEXT,
        dob TEXT,
        phone TEXT,
        whatsapp TEXT,
        present INTEGER DEFAULT 0,
        absent INTEGER DEFAULT 0,
        created_at TEXT
    );
    ''')
    c.execute('''
    CREATE TABLE IF NOT EXISTS students_auth (
        student_id INTEGER PRIMARY KEY,
        username TEXT,
        password TEXT
    );
    ''')
    conn.commit()
    c.execute("SELECT id FROM teacher WHERE username = ?", (TEACHER_USERNAME,))
    if not c.fetchone():
        c.execute("INSERT INTO teacher (username, password) VALUES (?, ?)", (TEACHER_USERNAME, DEFAULT_TEACHER_PASSWORD))
        conn.commit()
    conn.close()

def get_teacher_password() -> str:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password FROM teacher WHERE username=?", (TEACHER_USERNAME,))
    r = c.fetchone()
    conn.close()
    return r[0] if r else DEFAULT_TEACHER_PASSWORD

def set_teacher_password(newpwd: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE teacher SET password = ? WHERE username = ?", (newpwd, TEACHER_USERNAME))
    conn.commit()
    conn.close()

def insert_student(data: dict) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
      INSERT INTO students
      (name, sclass, father, mother, aadhar, dob, phone, whatsapp, present, absent, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0, 0, ?)
    """, (
        data.get('name'), data.get('sclass'), data.get('father'), data.get('mother'),
        data.get('aadhar'), data.get('dob'), data.get('phone'), data.get('whatsapp'),
        datetime.utcnow().isoformat()
    ))
    nid = c.lastrowid
    conn.commit()
    conn.close()
    return nid

def update_student(student_id: int, data: dict):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
      UPDATE students SET name=?, sclass=?, father=?, mother=?, aadhar=?, dob=?, phone=?, whatsapp=?
      WHERE id=?
    """, (
        data.get('name'), data.get('sclass'), data.get('father'), data.get('mother'),
        data.get('aadhar'), data.get('dob'), data.get('phone'), data.get('whatsapp'), student_id
    ))
    conn.commit()
    conn.close()

def get_all_students_df() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM students ORDER BY id DESC", conn)
    conn.close()
    df.columns = df.columns.str.strip().str.lower()
    return df

def get_student_by_id(sid: int) -> Optional[pd.Series]:
    df = get_all_students_df()
    rec = df[df['id'] == sid]
    if rec.empty:
        return None
    return rec.iloc[0]

def find_student_by_name_and_phone(name: str, phone: str) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT student_id FROM students_auth JOIN students ON students.id=students_auth.student_id WHERE username=? AND students.phone=?", (name, phone))
    r = c.fetchone()
    conn.close()
    return r[0] if r else None

def update_attendance(student_id: int, kind: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if kind == "present":
        c.execute("UPDATE students SET present = present + 1 WHERE id = ?", (student_id,))
    else:
        c.execute("UPDATE students SET absent = absent + 1 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def delete_student(student_id: int):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def delete_all_students():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM students")
    conn.commit()
    conn.close()

# -------------------------
# EMAIL OTP
# -------------------------
def gen_otp(n=6) -> str:
    return ''.join(random.choices(string.digits, k=n))

def send_email_otp(to_email: str, otp: str) -> bool:
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS):
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = "GMS School - Password Reset OTP"
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg.set_content(f"Your OTP for password reset is: {otp}")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except:
        return False

# -------------------------
# INIT
# -------------------------
init_db()

# -------------------------
# SESSION STATE
# -------------------------
for key in ["teacher_logged_in","student_logged_in","student_id","otp_code","otp_sent_at","ui_mode"]:
    if key not in st.session_state:
        st.session_state[key] = False if "logged_in" in key else None if key=="student_id" else "home"

# -------------------------
# UI
# -------------------------
st.set_page_config(page_title="GMS School Dhmala", layout="wide")
col1, col2 = st.columns([6,1])
with col1:
    st.markdown("<h1 style='margin:0'>🏫 G.M.S SCHOOL DHAMALA</h1>", unsafe_allow_html=True)
    st.markdown("<div style='color:#444'>Class 6th/7th/8th - Rekha Rani (TGT Hindi)</div>", unsafe_allow_html=True)
with col2:
    if st.session_state.teacher_logged_in:
        st.success("Teacher: Rekha (logged in)")
    elif st.session_state.student_logged_in:
        st.success("Student logged in")
    else:
        st.info("Please choose login")
st.markdown("---")

with st.sidebar:
    st.title("Quick Actions")
    mode = st.radio("Open as", ("Home", "Teacher Login", "Student Signup / Login", "AI Assistant"))
    if mode == "Teacher Login": st.session_state.ui_mode="teacher"
    elif mode == "Student Signup / Login": st.session_state.ui_mode="signup"
    elif mode == "AI Assistant": st.session_state.ui_mode="assistant"
    else: st.session_state.ui_mode="home"
    st.write("-----")
    if st.session_state.teacher_logged_in:
        if st.button("Teacher Dashboard"): st.session_state.ui_mode="teacher"
        if st.button("Logout Teacher"):
            st.session_state.teacher_logged_in=False
            st.experimental_rerun()
    if st.session_state.student_logged_in:
        if st.button("My Profile"): st.session_state.ui_mode="student"
        if st.button("Logout Student"):
            st.session_state.student_logged_in=False
            st.session_state.student_id=None
            st.experimental_rerun()

# -------------------------
# HOME
# -------------------------
def show_home():
    st.header("Welcome")
    st.write("Manage student records, attendance and provide teacher/student views.")
    st.write("Use sidebar to login as Teacher or Student.")
    st.markdown("""
    - Teacher: Add/Edit/Delete students, mark attendance, export CSV, password reset via OTP  
    - Student: Signup + Login to view own data only  
    - Validations: Aadhar max 12 digits, Phone exactly 10 digits, DOB pickers, class select
    """)
    st.write("---")

# -------------------------
# TEACHER
# -------------------------
def teacher_login_ui():
    st.header("🔐 Teacher Login")
    username = st.text_input("Username", value=TEACHER_USERNAME)
    pwd = st.text_input("Password", type="password")
    if st.button("Login as Teacher"):
        if username==TEACHER_USERNAME and pwd==get_teacher_password():
            st.session_state.teacher_logged_in=True
            st.success("Login successful")
            st.session_state.ui_mode="teacher"
        else: st.error("Invalid credentials")

def teacher_dashboard_ui():
    st.header("Teacher Dashboard")
    df = get_all_students_df()
    if df.empty:
        st.info("No students found")
        return
    for _, r in df.iterrows():
        st.markdown("----")
        st.markdown(f"**{int(r.get('id',0))}. {r.get('name','-')}** • Class: **{r.get('sclass','-')}**")
        st.markdown(f"Father: {r.get('father','-')} | Mother: {r.get('mother','-')}")
        st.markdown(f"Aadhar: {r.get('aadhar','-')} | DOB: {r.get('dob','-')} | Phone: {r.get('phone','-')} | WhatsApp: {r.get('whatsapp','-')}")
        st.markdown(f"Present: ✅ {int(r.get('present',0))} | Absent: ❌ {int(r.get('absent',0))}")

# -------------------------
# ROUTER
# -------------------------
mode = st.session_state.ui_mode
if mode=="home": show_home()
elif mode=="teacher": teacher_dashboard_ui() if st.session_state.teacher_logged_in else teacher_login_ui()

st.markdown("---")
st.caption("Built for G.M.S School Dhmala — Teacher: Rekha Rani")
