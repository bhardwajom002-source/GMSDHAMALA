# gms.py
import streamlit as st
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import json
from datetime import date
import os
import hashlib
import io

DB_FILE = "student.db"
TEACHER_USER = "rekha"
TEACHER_PASS = "rekha"

# ------------------ DB INIT ------------------
def init_db():
    create = not os.path.exists(DB_FILE)
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    c = conn.cursor()
    # Students table
    c.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        class TEXT,
        father TEXT,
        mother TEXT,
        aadhar TEXT,
        place TEXT,
        dob TEXT,
        phone TEXT,
        whatsapp TEXT,
        username TEXT UNIQUE,
        password TEXT,
        attendance TEXT DEFAULT '{}',
        marks TEXT DEFAULT '{}'
    )
    """)
    # Teachers table
    c.execute("""
    CREATE TABLE IF NOT EXISTS teachers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        email TEXT
    )
    """)
    # Messages table
    c.execute("""
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        student_username TEXT,
        message TEXT,
        response TEXT,
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()
    return create

# ------------------ DB HELPERS ------------------
def run_query(query, params=()):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute(query, params)
    conn.commit()
    rows = c.fetchall()
    conn.close()
    return rows

def fetch_df():
    conn = sqlite3.connect(DB_FILE)
    try:
        df = pd.read_sql_query("SELECT * FROM students", conn)
    except:
        df = pd.DataFrame()
    conn.close()
    required_cols = ['id','name','class','father','mother','aadhar','place',
                     'dob','phone','whatsapp','username','password','attendance','marks']
    for col in required_cols:
        if col not in df.columns:
            df[col] = "" if col not in ['attendance','marks'] else '{}'
    return df

def add_student_db(data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO students (name,class,father,mother,aadhar,place,dob,phone,whatsapp,username,password,attendance,marks)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
    ''', (
        data['name'], data['class'], data['father'], data['mother'],
        data['aadhar'], data['place'], data['dob'], data['phone'],
        data['whatsapp'], data['username'], data['password'],
        json.dumps(data.get('attendance', {})),
        json.dumps(data.get('marks', {}))
    ))
    conn.commit()
    conn.close()

def update_student_db(student_id, data):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE students SET name=?, class=?, father=?, mother=?, aadhar=?, place=?, dob=?, phone=?, whatsapp=?, username=?, password=?, attendance=?, marks=?
        WHERE id=?
    ''', (
        data['name'], data['class'], data['father'], data['mother'],
        data['aadhar'], data['place'], data['dob'], data['phone'],
        data['whatsapp'], data['username'], data['password'],
        json.dumps(data.get('attendance', {})),
        json.dumps(data.get('marks', {})),
        student_id
    ))
    conn.commit()
    conn.close()

def delete_student_db(student_id):
    run_query("DELETE FROM students WHERE id=?", (student_id,))

def get_student_by_username(username):
    rows = run_query("SELECT * FROM students WHERE username=?", (username,))
    return rows[0] if rows else None

def get_student_by_id(sid):
    rows = run_query("SELECT * FROM students WHERE id=?", (sid,))
    return rows[0] if rows else None

def is_valid_phone(p):
    return isinstance(p,str) and p.isdigit() and len(p)==10

def is_valid_aadhar(a):
    return isinstance(a,str) and a.isdigit() and 4<=len(a)<=12

def parse_att_json(att):
    if not att: return {}
    if isinstance(att,str):
        try:
            return json.loads(att)
        except: return {}
    if isinstance(att,dict): return att
    return {}

def hash_pwd(pwd):
    return hashlib.sha256(pwd.encode()).hexdigest()

# ------------------ STREAMLIT APP ------------------
st.set_page_config(page_title="GMS SCHOOL DHAMALA", layout="wide", page_icon="🎓")
init_db()

if 'role' not in st.session_state: st.session_state.role=None
if 'student_user' not in st.session_state: st.session_state.student_user=None

page = st.sidebar.radio("Navigate", ["Home","Teacher Login","Student Login/Signup","AI Assistant","About"])

# ------------------ HOME ------------------
if page=="Home":
    st.markdown("<h1 style='color:darkblue'>🎓 Welcome to GMS SCHOOL DHAMALA</h1>", unsafe_allow_html=True)
    st.markdown("Manage students, attendance, marks, messaging, AI assistant and reports easily.")

# ------------------ TEACHER LOGIN ------------------
if page=="Teacher Login":
    st.header("Teacher Login")
    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")
    if st.button("Login as Teacher"):
        if user.strip().lower()==TEACHER_USER and pwd==TEACHER_PASS:
            st.session_state.role = "teacher"
            st.success("Teacher logged in")
        else:
            st.error("Invalid credentials")

    if st.session_state.role=="teacher":
        st.subheader("Teacher Dashboard")
        left, right = st.columns([1,2])

        # ------------------ Add Student ------------------
        with left:
            st.markdown("### Add Student")
            with st.form("add_form"):
                name = st.text_input("Name")
                cls = st.selectbox("Class", ["6th","7th","8th"])
                father = st.text_input("Father")
                mother = st.text_input("Mother")
                aadhar = st.text_input("Aadhaar", max_chars=12)
                place = st.text_input("Place")
                dob = st.date_input("DOB", max_value=date.today())
                phone = st.text_input("Phone (10 digits)")
                whatsapp = st.text_input("WhatsApp (10 digits)")
                uname = st.text_input("Username")
                pwd_s = st.text_input("Password")
                submitted = st.form_submit_button("Add Student")
                if submitted:
                    errs=[]
                    if not name.strip(): errs.append("Name required")
                    if not is_valid_aadhar(aadhar): errs.append("Aadhaar invalid")
                    if not is_valid_phone(phone): errs.append("Phone invalid")
                    if not is_valid_phone(whatsapp): errs.append("WhatsApp invalid")
                    if get_student_by_username(uname.strip()): errs.append("Username exists")
                    if errs:
                        for e in errs: st.error(e)
                    else:
                        add_student_db({
                            "name":name.strip(),"class":cls,"father":father.strip(),
                            "mother":mother.strip(),"aadhar":aadhar.strip(),"place":place.strip(),
                            "dob":dob.isoformat(),"phone":phone.strip(),"whatsapp":whatsapp.strip(),
                            "username":uname.strip(),"password":pwd_s.strip(),"attendance":{},"marks":{}
                        })
                        st.success(f"Added {name}")

        # ------------------ Right Dashboard ------------------
        with right:
            # Attendance Management
            st.subheader("📊 Attendance Management")
            df = fetch_df()
            if not df.empty:
                df['attendance_dict'] = df['attendance'].apply(parse_att_json)
                df['Total Present'] = df['attendance_dict'].apply(lambda d: sum(1 for v in d.values() if v=='P'))
                df['Total Absent'] = df['attendance_dict'].apply(lambda d: sum(1 for v in d.values() if v=='A'))
                st.dataframe(df[['name','class','Total Present','Total Absent']], height=200)

                # Bar Chart
                fig, ax = plt.subplots()
                ax.bar(df['name'], df['Total Present'], label='Present', color='green')
                ax.bar(df['name'], df['Total Absent'], bottom=df['Total Present'], label='Absent', color='red')
                plt.xticks(rotation=45)
                plt.ylabel("Days")
                plt.title("Attendance Chart")
                ax.legend()
                st.pyplot(fig)

                # Export Excel
                towrite = io.BytesIO()
                df[['name','class','Total Present','Total Absent']].to_excel(towrite, index=False, engine='openpyxl')
                st.download_button("Download Attendance Excel", towrite.getvalue(), file_name="attendance.xlsx")

            st.markdown("---")
            # Student Records
            st.markdown("### Student Records")
            display_cols=['id','name','class','father','mother','aadhar','place','dob','phone','whatsapp','username']
            if df.empty:
                st.info("No students yet")
            else:
                st.dataframe(df[display_cols], height=200)

            # Messaging
            st.markdown("### Student Messages")
            conn = sqlite3.connect(DB_FILE)
            df_msg = pd.read_sql_query("SELECT * FROM messages ORDER BY timestamp DESC", conn)
            conn.close()
            if not df_msg.empty:
                for i,row in df_msg.iterrows():
                    st.markdown(f"**{row['student_username']}**: {row['message']}")
                    reply_key = f"reply_{row['id']}"
                    reply_val = st.text_input(f"Reply to {row['student_username']}", key=reply_key)
                    if st.button(f"Send Reply {row['id']}"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("UPDATE messages SET response=? WHERE id=?", (reply_val,row['id']))
                        conn.commit()
                        conn.close()
                        st.success("Reply sent")

# ------------------ STUDENT LOGIN/SIGNUP ------------------
if page=="Student Login/Signup":
    st.header("Student Signup/Login")
    c1,c2 = st.columns(2)
    with c1:
        st.subheader("Signup")
        with st.form("signup"):
            name = st.text_input("Name")
            cls = st.selectbox("Class", ["6th","7th","8th"])
            phone = st.text_input("Phone")
            dob = st.date_input("DOB", max_value=date.today())
            uname = st.text_input("Username")
            pwd = st.text_input("Password", type="password")
            sub=st.form_submit_button("Signup")
            if sub:
                errs=[]
                if not name.strip(): errs.append("Name required")
                if not is_valid_phone(phone): errs.append("Phone invalid")
                if get_student_by_username(uname.strip()): errs.append("Username exists")
                if errs:
                    for e in errs: st.error(e)
                else:
                    add_student_db({"name":name.strip(),"class":cls,"father":"","mother":"",
                                    "aadhar":"","place":"","dob":dob.isoformat(),"phone":phone.strip(),
                                    "whatsapp":phone.strip(),"username":uname.strip(),"password":pwd.strip(),
                                    "attendance":{},"marks":{}})
                    st.success("Signup complete. Use login panel.")

    with c2:
        st.subheader("Login")
        uname_l = st.text_input("Username", key="stu_user")
        pwd_l = st.text_input("Password", type="password", key="stu_pwd")
        if st.button("Login as Student"):
            row = get_student_by_username(uname_l)
            if row and row[11]==pwd_l:
                st.session_state.role="student"
                st.session_state.student_user=uname_l
                st.success("Logged in")
            else:
                st.error("Invalid credentials")

    # Student dashboard
    if st.session_state.role=="student":
        row = get_student_by_username(st.session_state.student_user)
        if row:
            st.subheader("Your Record")
            st.write("Name:", row[1])
            st.write("Class:", row[2])
            st.write("Father:", row[3])
            st.write("Mother:", row[4])
            st.write("Aadhaar:", row[5])
            st.write("Place:", row[6])
            st.write("DOB:", row[7])
            st.write("Phone:", row[8])
            st.write("WhatsApp:", row[9])
            st.subheader("Your Messages / Responses")
            conn = sqlite3.connect(DB_FILE)
            df_msg = pd.read_sql_query("SELECT * FROM messages WHERE student_username=? ORDER BY timestamp DESC",
                                       conn, params=(st.session_state.student_user,))
            conn.close()
            if not df_msg.empty:
                st.dataframe(df_msg[['message','response','timestamp']])
            
            st.subheader("Send Message to Teacher")
            msg = st.text_area("Type your message here")
            if st.button("Send Message"):
                if msg.strip():
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO messages (student_username, message) VALUES (?,?)",
                              (st.session_state.student_user, msg.strip()))
                    conn.commit()
                    conn.close()
                    st.success("Message sent to teacher")

# ------------------ AI ASSISTANT ------------------
if page=="AI Assistant":
    st.header("🎓 AI Assistant - Rekha Rani")
    st.markdown("Hi! I am **Rekha Rani**, your AI assistant. How can I help you today?")
    user_query = st.text_area("Ask your question here:")
    if st.button("Get Response"):
        if user_query.strip():
            response = f"Hi! I am Rekha Rani, your AI assistant. You asked: {user_query}"
            st.success(response)
    st.markdown("---")
    st.markdown("**Contact Info:**")
    st.markdown("**Name:** Rekha Rani  \n**Phone:** 9896300467  \n**Email:** rani1987rekha@gmail.com")

# ------------------ ABOUT PAGE ------------------
if page=="About":
    st.title("📘 About GMS School Management System")
    st.markdown("""
    Welcome to **GMS School Dhamala** Student Management System.
    
    This app is designed to help teachers and students manage:
    - Student records (Add / Edit / Delete)
    - Attendance tracking
    - Marks / Report Cards
    - Messaging system
    - AI Assistant
    - Secure login
    """)
    st.markdown("---")
    st.subheader("Developer / In-Charge")
    st.markdown("""
    **Name:** Rekha Rani  
    **Class In-Charge:** 8th  
    **Contact:** 9896300467  
    **Email:** rani1987rekha@gmail.com  
    """)
    st.image("https://via.placeholder.com/300x150.png?text=GMS+School+Logo", width=300)
