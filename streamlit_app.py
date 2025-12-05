import streamlit as st
import sqlite3
import pandas as pd
import io
from datetime import datetime

DB_PATH = "students.db"

# ------------------- DB Setup -------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        father TEXT,
        mother TEXT,
        aadhar TEXT,
        dob TEXT,
        present INTEGER DEFAULT 0,
        absent INTEGER DEFAULT 0,
        created_at TEXT
    )''')
    conn.commit()
    conn.close()

init_db()

def insert_student(data):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""INSERT INTO students 
        (name, father, mother, aadhar, dob, present, absent, created_at)
        VALUES (?, ?, ?, ?, ?, 0, 0, ?)""",
        (data["name"], data["father"], data["mother"], data["aadhar"],
         data["dob"], datetime.utcnow().isoformat()))
    conn.commit()
    conn.close()

def get_students():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM students ORDER BY id DESC", conn)
    conn.close()
    return df

def update_attendance(student_id, field):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE students SET {field} = {field} + 1 WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

def delete_student(student_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM students WHERE id = ?", (student_id,))
    conn.commit()
    conn.close()

# ------------------- UI & Login -------------------
st.set_page_config(page_title="GMS School App", layout="wide")

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

USERNAME = "rekha"
PASSWORD = "rekha"

def login_page():
    st.title("🏫 Teacher Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        if user == USERNAME and pwd == PASSWORD:
            st.session_state.logged_in = True
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Wrong username/password")

if not st.session_state.logged_in:
    login_page()
    st.stop()

# ------------------- Main Student System -------------------
st.title("G.M.S SCHOOL DHAMALA FIROJPUR JHIRKA")
st.write("**Class 8th — Rekha Rani (TGT Hindi)**")
st.write("📌 Student Data Collection System")
st.write("---")

# Logout button
if st.button("Logout"):
    st.session_state.logged_in = False
    st.rerun()

col1, col2 = st.columns([1,2])

# ------- Add Student ------
with col1:
    st.subheader("➕ Add Student")

    name = st.text_input("Name*")
    father = st.text_input("Father Name")
    mother = st.text_input("Mother Name")
    aadhar = st.text_input("Aadhar (max 12 digits)")
    dob = st.text_input("DOB (YYYY-MM-DD)*")

    if st.button("Add"):
        if not name or not dob:
            st.error("Name and DOB Required")
        elif len(aadhar) > 12:
            st.error("Aadhar max 12 digits allowed")
        else:
            insert_student({
                "name": name,
                "father": father,
                "mother": mother,
                "aadhar": aadhar,
                "dob": dob
            })
            st.success("Student Added Successfully!")

# ------- Student Table ------
with col2:
    st.subheader("📋 Students List")

    df = get_students()

    if not df.empty:
        for i, row in df.iterrows():
            c1, c2, c3, c4 = st.columns([4,1,1,1])
            
            c1.write(f"{row['id']}. **{row['name']}** | {row['father']} | {row['mother']} | {row['aadhar']} | {row['dob']}")
            
            if c2.button("✔", key=f"p{row['id']}"):
                update_attendance(row['id'], "present")
                st.rerun()
                
            if c3.button("❌", key=f"a{row['id']}"):
                update_attendance(row['id'], "absent")
                st.rerun()

            if c4.button("🗑", key=f"d{row['id']}"):
                delete_student(row['id'])
                st.rerun()
    else:
        st.info("No students added yet.")

# ------- Export Data ------
st.write("---")
if st.button("📤 Export CSV"):
    students = get_students()
    csv_data = students.to_csv(index=False).encode('utf-8')
    st.download_button("Download CSV File", data=csv_data, file_name="students.csv")
