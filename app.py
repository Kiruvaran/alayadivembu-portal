import streamlit as st
import sqlite3
import os
import hashlib
import random
from datetime import datetime

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Alayadivembu M.P.C.S Ltd", layout="wide")

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# -------------------------
# DATABASE
# -------------------------
conn = sqlite3.connect("portal.db", check_same_thread=False)
c = conn.cursor()

c.execute("""CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT,
    role TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS files (
    filename TEXT,
    month TEXT,
    uploaded_by TEXT
)""")

c.execute("""CREATE TABLE IF NOT EXISTS logs (
    username TEXT,
    time TEXT
)""")

conn.commit()

# -------------------------
# HASH
# -------------------------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# -------------------------
# DEFAULT USERS
# -------------------------
def create_users():
    users = [
        ("admin", "Kiruvaran@1993", "admin"),
        ("staff", "staff2026@", "staff"),
        ("cdo", "cdo2026@", "cdo")
    ]

    for u in users:
        c.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES (?,?,?)",
                      (u[0], hash_password(u[1]), u[2]))
    conn.commit()

create_users()

# -------------------------
# LOGIN + OTP
# -------------------------
def login():
    st.title("🔐 Secure Login")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (user, hash_password(pwd)))
        result = c.fetchone()

        if result:
            otp = str(random.randint(100000, 999999))
            st.session_state["otp"] = otp
            st.session_state["temp_user"] = result

        else:
            st.error("Invalid login")

def verify_otp():
    st.subheader("Enter OTP")
    user_otp = st.text_input("OTP")

    if st.button("Verify"):
        if user_otp == st.session_state.get("otp"):
            user = st.session_state["temp_user"]

            st.session_state["user"] = user[0]
            st.session_state["role"] = user[2]
            st.session_state["logged"] = True

            c.execute("INSERT INTO logs VALUES (?,?)",
                      (user[0], str(datetime.now())))
            conn.commit()

            st.success("Login Success ✅")
        else:
            st.error("Wrong OTP")

# -------------------------
# SESSION
# -------------------------
if "logged" not in st.session_state:
    st.session_state["logged"] = False

if not st.session_state["logged"]:
    if "otp" not in st.session_state:
        login()
    else:
        verify_otp()
    st.stop()

# -------------------------
# HEADER
# -------------------------
st.markdown("""
<h1 style='text-align:center;color:#003366;'>
Alayadivembu M.P.C.S Ltd Accounts
</h1>
""", unsafe_allow_html=True)

st.sidebar.write(f"👤 {st.session_state['user']}")
st.sidebar.write(f"🔑 Role: {st.session_state['role']}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.experimental_rerun()

# -------------------------
# MONTH DETECT
# -------------------------
months = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def detect_month(name):
    for m in months:
        if m.lower() in name.lower():
            return m
    return "Unknown"

# -------------------------
# ADMIN PANEL
# -------------------------
if st.session_state["role"] == "admin":
    st.sidebar.subheader("➕ Add User")

    new_user = st.sidebar.text_input("Username")
    new_pass = st.sidebar.text_input("Password", type="password")
    role = st.sidebar.selectbox("Role", ["admin","staff","cdo"])

    if st.sidebar.button("Create"):
        c.execute("INSERT INTO users VALUES (?,?,?)",
                  (new_user, hash_password(new_pass), role))
        conn.commit()
        st.sidebar.success("User Added")

# -------------------------
# UPLOAD (Admin + Staff)
# -------------------------
if st.session_state["role"] in ["admin", "staff"]:
    st.header("📤 Upload PDF")

    file = st.file_uploader("Upload", type=["pdf"])

    if file:
        path = os.path.join(UPLOAD_FOLDER, file.name)

        with open(path, "wb") as f:
            f.write(file.getbuffer())

        month = detect_month(file.name)

        c.execute("INSERT INTO files VALUES (?,?,?)",
                  (file.name, month, st.session_state["user"]))
        conn.commit()

        st.success(f"Uploaded to {month}")

# -------------------------
# SEARCH
# -------------------------
search = st.text_input("🔍 Search")

# -------------------------
# VIEW (All roles)
# -------------------------
st.header("📂 Monthly Reports")

cols = st.columns(3)

for i, month in enumerate(months):
    with cols[i % 3]:
        with st.expander(month):

            if search:
                c.execute("SELECT * FROM files WHERE filename LIKE ?", (f"%{search}%",))
            else:
                c.execute("SELECT * FROM files WHERE month=?", (month,))

            data = c.fetchall()

            if data:
                for fdata in data:
                    file_path = os.path.join(UPLOAD_FOLDER, fdata[0])

                    st.write(fdata[0])

                    with open(file_path, "rb") as f:
                        st.download_button("⬇️ Download", f, fdata[0])

                    with open(file_path, "rb") as f:
                        st.download_button("📄 View", f, fdata[0])
            else:
                st.info("No files")

# -------------------------
# ADMIN LOGS
# -------------------------
if st.session_state["role"] == "admin":
    st.header("🧾 Login Logs")

    c.execute("SELECT * FROM logs")
    logs = c.fetchall()

    for log in logs:
        st.write(log)

# -------------------------
# FOOTER
# -------------------------
st.caption("© Alayadivembu M.P.C.S Ltd - Secure Portal")