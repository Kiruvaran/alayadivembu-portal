import streamlit as st
import sqlite3
import os
import hashlib
from datetime import datetime
import base64
import fitz
from PIL import Image
import io

# -------------------------
# CONFIG
# -------------------------
st.set_page_config(page_title="Alayadivembu M.P.C.S Ltd", layout="wide")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# THEME
# -------------------------
if "theme" not in st.session_state:
    st.session_state["theme"] = "light"

def toggle_theme():
    st.session_state["theme"] = "dark" if st.session_state["theme"] == "light" else "light"

# -------------------------
# DATABASE
# -------------------------
conn = sqlite3.connect("portal.db", check_same_thread=False)
c = conn.cursor()

c.execute("CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, role TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS files (filename TEXT, month TEXT, uploaded_by TEXT)")
c.execute("CREATE TABLE IF NOT EXISTS audit (username TEXT, filename TEXT, time TEXT)")
conn.commit()

# -------------------------
# SECURITY
# -------------------------
def hash_password(p):
    return hashlib.sha256(p.encode()).hexdigest()

# -------------------------
# DEFAULT USERS
# -------------------------
def create_users():
    users = [
        ("admin", "admin123", "admin"),
        ("staff", "staff123", "staff"),
        ("cdo", "cdo123", "cdo")
    ]
    for u in users:
        c.execute("SELECT * FROM users WHERE username=?", (u[0],))
        if not c.fetchone():
            c.execute("INSERT INTO users VALUES (?,?,?)",
                      (u[0], hash_password(u[1]), u[2]))
    conn.commit()

create_users()

# -------------------------
# MONTHS
# -------------------------
months = ["January","February","March","April","May","June",
          "July","August","September","October","November","December"]

def detect_month(name):
    for m in months:
        if m.lower() in name.lower():
            return m
    return "Unknown"

# -------------------------
# PDF
# -------------------------
def get_pdf_thumbnail(file_path):
    doc = fitz.open(file_path)
    page = doc.load_page(0)
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

def show_pdf(file_path):
    with open(file_path, "rb") as f:
        base64_pdf = base64.b64encode(f.read()).decode("utf-8")

    st.markdown(f"""
    <iframe src="data:application/pdf;base64,{base64_pdf}"
    width="100%" height="700px"></iframe>
    """, unsafe_allow_html=True)

# -------------------------
# LOGIN
# -------------------------
def login():
    st.title("🔐 Alayadivembu M.P.C.S Ltd")

    user = st.text_input("Username")
    pwd = st.text_input("Password", type="password")

    if st.button("Login"):
        c.execute("SELECT * FROM users WHERE username=? AND password=?",
                  (user, hash_password(pwd)))
        res = c.fetchone()

        if res:
            st.session_state["user"] = res[0]
            st.session_state["role"] = res[2]
            st.session_state["logged"] = True
            st.rerun()
        else:
            st.error("Invalid Login")

# -------------------------
# SESSION
# -------------------------
if "logged" not in st.session_state:
    st.session_state["logged"] = False

if not st.session_state["logged"]:
    login()
    st.stop()

# -------------------------
# SIDEBAR
# -------------------------
st.sidebar.button("🌗 Toggle Theme", on_click=toggle_theme)
st.sidebar.write(f"👤 {st.session_state['user']}")
st.sidebar.write(f"🔑 {st.session_state['role']}")

if st.sidebar.button("Logout"):
    st.session_state.clear()
    st.rerun()

# -------------------------
# ADMIN PANEL
# -------------------------
if st.session_state["role"] == "admin":
    st.sidebar.subheader("➕ Create User")
    nu = st.sidebar.text_input("Username")
    np = st.sidebar.text_input("Password", type="password")
    nr = st.sidebar.selectbox("Role", ["admin","staff","cdo"])

    if st.sidebar.button("Add User"):
        c.execute("INSERT INTO users VALUES (?,?,?)",
                  (nu, hash_password(np), nr))
        conn.commit()
        st.sidebar.success("User Created")

    if st.sidebar.button("📊 View Audit Logs"):
        logs = c.execute("SELECT * FROM audit ORDER BY time DESC").fetchall()
        st.write("### Audit Logs")
        st.table(logs)

# -------------------------
# UPLOAD
# -------------------------
if st.session_state["role"] in ["admin","staff"]:
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
search = st.text_input("🔍 Search Files")

# -------------------------
# FILE VIEW
# -------------------------
st.subheader("📂 Monthly Reports")

cols = st.columns(3)

for i, m in enumerate(months):
    with cols[i % 3]:

        st.markdown(f"### 📅 {m}")

        if search:
            c.execute("SELECT * FROM files WHERE filename LIKE ?", (f"%{search}%",))
        else:
            c.execute("SELECT * FROM files WHERE month=?", (m,))

        files = c.fetchall()

        for idx, fdata in enumerate(files):
            file_path = os.path.join(UPLOAD_FOLDER, fdata[0])

            col1, col2 = st.columns([1,2])

            with col1:
                try:
                    img = get_pdf_thumbnail(file_path)
                    st.image(img, width=80)
                except:
                    st.write("📄")

            with col2:
                st.write(fdata[0])

                view_key = f"view_{m}_{idx}_{fdata[0]}"
                download_key = f"down_{m}_{idx}_{fdata[0]}"
                delete_key = f"del_{m}_{idx}_{fdata[0]}"

                if st.button("👁 View", key=view_key):
                    st.session_state["pdf"] = file_path

                    c.execute("INSERT INTO audit VALUES (?,?,?)",
                              (st.session_state["user"], fdata[0], str(datetime.now())))
                    conn.commit()

                with open(file_path, "rb") as f:
                    st.download_button("⬇️ Download", f, fdata[0], key=download_key)

                if st.session_state["role"] == "admin":
                    if st.button("🗑️ Delete", key=delete_key):
                        try:
                            os.remove(file_path)
                        except:
                            pass

                        c.execute("DELETE FROM files WHERE filename=?", (fdata[0],))
                        conn.commit()
                        st.warning(f"{fdata[0]} deleted")
                        st.rerun()

# -------------------------
# PDF VIEW
# -------------------------
if "pdf" in st.session_state:
    st.markdown("---")
    with st.expander("📄 Document Preview", expanded=True):
        show_pdf(st.session_state["pdf"])

# -------------------------
# FOOTER
# -------------------------
st.markdown("""
---
<center>Created by <b>K. Kiruvaran</b></center>
""", unsafe_allow_html=True)