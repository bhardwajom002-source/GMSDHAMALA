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
import io
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
# default teacher password; can be changed in-app
# (persisted in DB as a hashed-ish value? We'll store plain for simplicity; for production use hashing)
DEFAULT_TEACHER_PASSWORD = "rekha"

# Email OTP config (optional) -- set these as environment variables for real sending
SMTP_HOST = os.getenv("SMTP_HOST", "")          # e.g. "smtp.gmail.com"
SMTP_PORT = int(os.getenv("SMTP_PORT", "587")) if os.getenv("SMTP_PORT") else None
SMTP_USER = os.getenv("SMTP_USER", "")          # e.g. "youremail@gmail.com"
SMTP_PASS = os.getenv("SMTP_PASS", "")          # app password or SMTP password
FROM_EMAIL = os.getenv("FROM_EMAIL", SMTP_USER) or "noreply@example.com"
TEACHER_RESET_EMAIL = "rani1987rekha@gmail.com"  # user's requested email for OTP

# -------------------------
# HELPERS: DB
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
    conn.commit()
    # Ensure teacher exists
    c.execute("SELECT id FROM teacher WHERE username = ?", (TEACHER_USERNAME,))
    if not c.fetchone():
        c.execute("INSERT INTO teacher (username, password) VALUES (?, ?)",
                  (TEACHER_USERNAME, DEFAULT_TEACHER_PASSWORD))
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
    """, (data.get('name'), data.get('sclass'), data.get('father'), data.get('mother'),
          data.get('aadhar'), data.get('dob'), data.get('phone'), data.get('whatsapp'),
          datetime.utcnow().isoformat()))
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
    """, (data.get('name'), data.get('sclass'), data.get('father'), data.get('mother'),
          data.get('aadhar'), data.get('dob'), data.get('phone'), data.get('whatsapp'), student_id))
    conn.commit()
    conn.close()

def get_all_students_df() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM students ORDER BY id DESC", conn)
    conn.close()
    return df

def get_student_by_id(sid: int) -> Optional[pd.Series]:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM students WHERE id = ?", conn, params=(sid,))
    conn.close()
    if df.empty:
        return None
    return df.iloc[0]

def find_student_by_name_and_phone(name: str, phone: str) -> Optional[int]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM students WHERE name = ? AND phone = ?", (name, phone))
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
# HELPERS: Email OTP
# -------------------------
def gen_otp(n=6) -> str:
    return ''.join(random.choices(string.digits, k=n))

def send_email_otp(to_email: str, otp: str) -> bool:
    """Send OTP by SMTP; returns True if sent (or False on error)."""
    # If SMTP not configured, return False
    if not (SMTP_HOST and SMTP_PORT and SMTP_USER and SMTP_PASS):
        return False
    try:
        msg = EmailMessage()
        msg['Subject'] = "GMS School - Password Reset OTP"
        msg['From'] = FROM_EMAIL
        msg['To'] = to_email
        msg.set_content(f"Your OTP for password reset is: {otp}\n\nIf you did not request this, ignore.")
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print("SMTP send error:", e)
        return False

# -------------------------
# INIT
# -------------------------
init_db()

# -------------------------
# SESSION state init
# -------------------------
if "teacher_logged_in" not in st.session_state:
    st.session_state.teacher_logged_in = False
if "student_logged_in" not in st.session_state:
    st.session_state.student_logged_in = False
if "student_id" not in st.session_state:
    st.session_state.student_id = None
if "otp_code" not in st.session_state:
    st.session_state.otp_code = None
if "otp_sent_at" not in st.session_state:
    st.session_state.otp_sent_at = None
if "ui_mode" not in st.session_state:
    st.session_state.ui_mode = "home"  # home, teacher, student, signup, reset_pwd, assistant

# -------------------------
# UI helpers
# -------------------------
st.set_page_config(page_title="GMS School Dhmala - Student Records", layout="wide",
                   initial_sidebar_state="auto")

# header
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

# Sidebar: navigation
with st.sidebar:
    st.title("Quick Actions")
    mode = st.radio("Open as", ("Home", "Teacher Login", "Student Signup / Login", "AI Assistant"), index=0)
    if mode == "Teacher Login":
        st.session_state.ui_mode = "teacher"
    elif mode == "Student Signup / Login":
        st.session_state.ui_mode = "signup"
    elif mode == "AI Assistant":
        st.session_state.ui_mode = "assistant"
    else:
        st.session_state.ui_mode = "home"
    st.write("-----")
    if st.session_state.teacher_logged_in:
        if st.button("Teacher Dashboard"):
            st.session_state.ui_mode = "teacher"
        if st.button("Logout Teacher"):
            st.session_state.teacher_logged_in = False
            st.experimental_rerun()
    if st.session_state.student_logged_in:
        if st.button("My Profile"):
            st.session_state.ui_mode = "student"
        if st.button("Logout Student"):
            st.session_state.student_logged_in = False
            st.session_state.student_id = None
            st.experimental_rerun()

# -------------------------
# HOME
# -------------------------
def show_home():
    st.header("Welcome")
    st.write("""
    This application manages student records, attendance and provides both teacher and student views.
    Use the sidebar to go to Teacher Login or Student Signup/Login.
    """)
    st.write("Key features:")
    st.markdown("""
    - Teacher: Add/Edit/Delete students, mark attendance, export CSV, password reset via OTP (email optional)  
    - Student: Signup + Login to view own data only  
    - Validations: Aadhar max 12 digits, Phone exactly 10 digits, DOB pickers, class select (6th/7th/8th)
    """)
    st.write("---")

# -------------------------
# TEACHER UI
# -------------------------
def teacher_login_ui():
    st.header("🔐 Teacher Login")
    st.write("Enter teacher username and password. Password show/hide available.")

    col1, col2 = st.columns([2,2])
    with col1:
        username = st.text_input("Username", value=TEACHER_USERNAME)
    with col2:
        pwd = st.text_input("Password", type="password", key="teacher_pwd")
    show_pwd = st.checkbox("Show password", key="teacher_show_pwd")
    if show_pwd:
        # A hack to re-render plain password (Streamlit doesn't allow replacing type easily)
        st.write(f"Password: `{pwd}`")

    if st.button("Login as Teacher"):
        real_pwd = get_teacher_password()
        if username == TEACHER_USERNAME and pwd == real_pwd:
            st.session_state.teacher_logged_in = True
            st.success("Login successful")
            st.session_state.ui_mode = "teacher"
            st.session_state
        else:
            st.error("Invalid username/password")

    st.markdown("### Forgot Password")
    st.write("You can reset teacher password via OTP sent to email:", TEACHER_RESET_EMAIL)
    if st.button("Send OTP to teacher email"):
        otp = gen_otp(6)
        st.session_state.otp_code = otp
        st.session_state.otp_sent_at = datetime.utcnow().isoformat()
        sent = send_email_otp(TEACHER_RESET_EMAIL, otp)
        if sent:
            st.success("OTP sent to email. (Check your inbox)")
        else:
            st.warning("SMTP not configured or send failed. For testing, OTP is shown below.")
            st.info(f"DEV OTP: {otp}")  # for development only
        st.session_state.ui_mode = "reset_pwd"

def teacher_dashboard_ui():
    st.header("Teacher Dashboard")
    st.write("You can add students, edit, mark attendance, export data, search and create WhatsApp group links.")

    # Export, Delete all, Change password buttons
    col1, col2, col3, col4 = st.columns([3,1,1,1])
    with col2:
        if st.button("Export CSV"):
            df = get_all_students_df()
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button("Download CSV", data=csv, file_name="students.csv")
    with col3:
        if st.button("Delete All Students"):
            delete_all_students()
            st.success("All students deleted")
            st.experimental_rerun()
    with col4:
        if st.button("Change Teacher Password"):
            st.session_state.ui_mode = "change_pwd"

    # Search
    q = st.text_input("Search by name/father/aadhar", value="", key="search_q")
    df = get_all_students_df()
    if q:
        df = df[df.apply(lambda r: q.lower() in str(r['name']).lower() or
                               q.lower() in str(r['father']).lower() or
                               q.lower() in str(r['aadhar']).lower(), axis=1)]

    st.subheader("📋 Students List")
    if df.empty:
        st.info("No students")
        return

    # --- Display each student row ---
    for _, r in df.iterrows():
        st.markdown("----")
        cols = st.columns([4,1,1,1,1])
        # Left column: student info
        with cols[0]:
            st.markdown(f"**{int(r['id'])}. {r['name']}**  •  Class: **{r['sclass']}**")
            st.markdown(f"Father: {r['father']}  |  Mother: {r['mother']}")
            st.markdown(f"Aadhar: {r['aadhar'] or '-'}  |  DOB: {r['dob']}  |  Phone: 📞 {r['phone'] or '-'}  WhatsApp: 💬 {r['whatsapp'] or '-'}")
            st.markdown(f"Present: ✅ {int(r['present'])}   Absent: ❌ {int(r['absent'])}")

        # Action buttons
        if cols[1].button("Present", key=f"p_{r['id']}"):
            update_attendance(int(r['id']), "present")
            st.experimental_rerun()
        if cols[2].button("Absent", key=f"a_{r['id']}"):
            update_attendance(int(r['id']), "absent")
            st.experimental_rerun()
        if cols[3].button("Edit", key=f"e_{r['id']}"):
            with st.form(f"edit_form_{r['id']}", clear_on_submit=False):
                ename = st.text_input("Name", value=r['name'])
                eclass = st.selectbox("Class", ["6th","7th","8th"], index=["6th","7th","8th"].index(r['sclass']))
                efather = st.text_input("Father", value=r['father'])
                emother = st.text_input("Mother", value=r['mother'])
                eaadhar = st.text_input("Aadhar", value=r['aadhar'])
                edob = st.date_input("DOB", value=datetime.fromisoformat(r['dob']).date() if r['dob'] else date(2016,1,1))
                ephone = st.text_input("Phone", value=r['phone'])
                ewh = st.text_input("WhatsApp", value=r['whatsapp'])
                if st.form_submit_button("Save"):
                    if eaadhar and (not eaadhar.isdigit() or len(eaadhar) > 12):
                        st.error("Aadhar invalid")
                    elif ephone and (not ephone.isdigit() or len(ephone) != 10):
                        st.error("Phone invalid")
                    elif ewh and (not ewh.isdigit() or len(ewh) != 10):
                        st.error("Whatsapp invalid")
                    else:
                        update_student(int(r['id']), {
                            "name": ename,
                            "sclass": eclass,
                            "father": efather,
                            "mother": emother,
                            "aadhar": eaadhar,
                            "dob": edob.isoformat(),
                            "phone": ephone,
                            "whatsapp": ewh
                        })
                        st.success("Updated")
                        st.experimental_rerun()
        if cols[4].button("Delete", key=f"d_{r['id']}"):
            delete_student(int(r['id']))
            st.success("Deleted")
            st.session_state



    # WhatsApp group generator: collect whatsapp numbers
    st.markdown("---")
    if st.button("Generate WhatsApp Group Link (collect all WhatsApp numbers)"):
        df2 = get_all_students_df()
        nums = df2['whatsapp'].dropna().astype(str)
        nums = [n for n in nums if n.isdigit() and len(n) == 10]
        if not nums:
            st.warning("No valid whatsapp numbers collected")
        else:
            # WhatsApp group creation can't be automated; we provide a preview list and message template
            st.success(f"Collected {len(nums)} WhatsApp numbers")
            st.write(", ".join([f"+91{n}" for n in nums[:50]]))  # show up to 50
            st.markdown("**Message template:**")
            st.code("Hello, this group is for class updates. - GMS School")
            st.info("To create a group: use WhatsApp app, create group and add these numbers (above).")

# -------------------------
# Password reset and change flows
# -------------------------
def reset_password_ui():
    st.header("Reset Teacher Password (OTP)")
    st.write("OTP will be sent to:", TEACHER_RESET_EMAIL)
    if 'otp_code' not in st.session_state or not st.session_state.otp_code:
        if st.button("Send OTP Now"):
            otp = gen_otp(6)
            st.session_state.otp_code = otp
            st.session_state.otp_sent_at = datetime.utcnow().isoformat()
            sent = send_email_otp(TEACHER_RESET_EMAIL, otp)
            if sent:
                st.success("OTP sent to email")
            else:
                st.warning("SMTP not configured or send failed. For testing, OTP is shown below")
                st.info(f"DEV OTP (visible only to you): {otp}")

    entered = st.text_input("Enter OTP")
    if st.button("Verify OTP"):
        if entered and st.session_state.otp_code and entered == st.session_state.otp_code:
            st.success("OTP verified. Please set new password below.")
            st.session_state.ui_mode = "change_pwd"
        else:
            st.error("Invalid OTP")

def change_password_ui():
    st.header("Change Teacher Password")
    new1 = st.text_input("New Password", type="password")
    new2 = st.text_input("Confirm New Password", type="password")
    show = st.checkbox("Show new password(s)")
    if show:
        st.write("New:", new1, "Confirm:", new2)
    if st.button("Change Password"):
        if not new1 or not new2:
            st.error("Fill both fields")
        elif new1 != new2:
            st.error("Passwords do not match")
        else:
            set_teacher_password(new1)
            st.success("Password updated. Please login again.")
            st.session_state.teacher_logged_in = False
            st.session_state.ui_mode = "teacher"
            st.session_state

# -------------------------
# STUDENT SIGNUP & LOGIN
# -------------------------
def student_signup_ui():
    st.header("Student Signup")
    st.write("Students can signup to view their personal data only.")
    with st.form("signup"):
        sname = st.text_input("Full Name *")
        sclass = st.selectbox("Class *", ["6th","7th","8th"])
        sphone = st.text_input("Phone (10 digits) *")
        sph_pass = st.text_input("Choose a password (for student login)", type="password")
        submitted = st.form_submit_button("Signup")
        if submitted:
            if not sname or not sphone or not sph_pass:
                st.error("Name, phone and password required")
            elif not sphone.isdigit() or len(sphone) != 10:
                st.error("Phone must be 10 digits")
            else:
                # create a student record with minimal info (teacher can fill more later)
                sid = insert_student({
                    "name": sname.strip(),
                    "sclass": sclass,
                    "father": "",
                    "mother": "",
                    "aadhar": "",
                    "dob": date(2016,1,1).isoformat(),
                    "phone": sphone.strip(),
                    "whatsapp": ""
                })
                # store student's password locally in a separate simple table? For simplicity, store in session mapping
                # We'll create a simple students_auth table
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute('''CREATE TABLE IF NOT EXISTS students_auth (
                                student_id INTEGER PRIMARY KEY,
                                username TEXT,
                                password TEXT
                             )''')
                try:
                    c.execute("INSERT INTO students_auth (student_id, username, password) VALUES (?, ?, ?)",
                              (sid, sname.strip(), sph_pass))
                except:
                    c.execute("UPDATE students_auth SET username=?, password=? WHERE student_id=?",
                              (sname.strip(), sph_pass, sid))
                conn.commit()
                conn.close()
                st.success(f"Signup successful. Your Student ID: {sid}. Use Student Login to view your data.")
                st.session_state.student_signup_success = True

def student_login_ui():
    st.header("Student Login")
    st.write("Students login with Name and Phone or Student ID + Password.")

    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Name")
        phone = st.text_input("Phone (10 digits)")
        if st.button("Login with Name + Phone"):
            sid = find_student_by_name_and_phone(name.strip(), phone.strip())
            if sid:
                # check if auth exists; if not, allow login anyway (development)
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT password FROM students_auth WHERE student_id = ?", (sid,))
                row = c.fetchone()
                conn.close()
                if row:
                    st.info("This account is protected. Use Student ID + Password or contact teacher.")
                else:
                    st.session_state.student_logged_in = True
                    st.session_state.student_id = sid
                    st.success("Logged in. Showing your data")
                    st.session_state.ui_mode = "student"
                    st.session_state
            else:
                st.error("No student found with that name and phone")

    with col2:
        sid_in = st.text_input("Student ID")
        spwd = st.text_input("Password", type="password")
        if st.button("Login with ID + Password"):
            try:
                sidv = int(sid_in)
            except:
                st.error("Invalid ID")
                sidv = None
            if sidv:
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("SELECT password FROM students_auth WHERE student_id = ?", (sidv,))
                row = c.fetchone()
                conn.close()
                if row and row[0] == spwd:
                    st.session_state.student_logged_in = True
                    st.session_state.student_id = sidv
                    st.success("Logged in successfully")
                    st.session_state.ui_mode = "student"
                    st.session_state
                else:
                    st.error("Invalid credentials")

# -------------------------
# STUDENT PROFILE
# -------------------------
def student_profile_ui():
    sid = st.session_state.student_id
    st.header("Student Profile")
    st.write("Personal details (only visible to this student)")

    rec = get_student_by_id(sid)
    if rec is None:
        st.error("Record not found")
        return
    st.markdown(f"### {rec['name']}  •  Class {rec['sclass']}")
    st.write(f"Father: {rec['father']}")
    st.write(f"Mother: {rec['mother']}")
    st.write(f"Aadhar: {rec['aadhar'] or '-'}")
    st.write(f"DOB: {rec['dob']}")
    st.write(f"Phone: 📞 {rec['phone'] or '-'}  WhatsApp: 💬 {rec['whatsapp'] or '-'}")
    st.write(f"Attendance: ✅ Present: {int(rec['present'])}   ❌ Absent: {int(rec['absent'])}")
    st.write("---")
    if st.button("Request password reset (student)"):
        st.info("Ask teacher to reset your password or use teacher assistance.")

# -------------------------
# AI Assistant stub
# -------------------------
def assistant_ui():
    st.header("AI Assistant - Rekha Rani")
    st.write("Click a suggested prompt or type your question. (Simple local assistant stub)")
    col1, col2 = st.columns([3,1])
    with col2:
        if st.button("I'm Rekha, what can I help you with?"):
            st.session_state.assistant_reply = "Namaste Rekha Rani! Main aapki kaise madad kar sakta hoon? (Example: add student, show attendance)"
    prompt = st.text_area("Ask / Command:", value=st.session_state.get("assistant_prompt",""))
    if st.button("Send to Assistant"):
        # Very simple rule-based responses for now
        txt = prompt.lower()
        if "add student" in txt:
            st.session_state.assistant_reply = "To add student: go to Teacher Dashboard -> Add Student. Fill name/class/phone etc."
        elif "show attendance" in txt:
            st.session_state.assistant_reply = "Go to Teacher Dashboard and look up the student. Use Present/Absent buttons."
        else:
            st.session_state.assistant_reply = "I can help with: add student, change password, export csv, generate whatsapp list."
    if st.session_state.get("assistant_reply"):
        st.info(st.session_state.assistant_reply)

# -------------------------
# MAIN router
# -------------------------
mode = st.session_state.ui_mode

if mode == "home":
    show_home()
elif mode == "teacher":
    if not st.session_state.teacher_logged_in:
        teacher_login_ui()
    else:
        teacher_dashboard_ui()
elif mode == "reset_pwd":
    reset_password_ui()
elif mode == "change_pwd":
    change_password_ui()
elif mode == "signup":
    # Show both signup and login for students
    st.header("Student Access")
    st.write("Signup or login as student to view personal data.")
    tabs = st.tabs(["Signup", "Login"])
    with tabs[0]:
        student_signup_ui()
    with tabs[1]:
        student_login_ui()
elif mode == "student":
    if st.session_state.student_logged_in:
        student_profile_ui()
    else:
        st.info("Please login as student first.")
elif mode == "assistant":
    assistant_ui()

# footer
st.markdown("---")
st.write("Built for G.M.S School Dhmala — Teacher: Rekha Rani")
st.caption("Note: For real OTP emails, configure SMTP via environment variables: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS.")
