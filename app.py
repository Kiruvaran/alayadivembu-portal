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
# THEME STATE
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

c.execute("""CREATE TABLE IF NOT EXISTS audit (
    username TEXT,
    filename TEXT,
    time TEXT
)""")

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
# PDF THUMBNAIL
# -------------------------
def get_pdf_thumbnail(file_path):
    doc = fitz.open(file_path)
    page = doc.load_page(0)
    pix = page.get_pixmap()
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return img

# -------------------------
# PDF VIEWER
# -------------------------
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

            c.execute("INSERT INTO logs VALUES (?,?)",
                      (res[0], str(datetime.now())))
            conn.commit()

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
# THEME CSS
# -------------------------
if st.session_state["theme"] == "light":
    bg = "#f5f9ff"
    card = "white"
    text = "#0a3d62"
else:
    bg = "#0f172a"
    card = "#1e293b"
    text = "#ffffff"

st.markdown(f"""
<style>
.main {{
    background-color:{bg};
}}

.title {{
    text-align:center;
    font-size:40px;
    color:{text};
    font-weight:bold;
}}

.subtitle {{
    text-align:center;
    font-size:18px;
    color:{text};
    opacity:0.8;
}}

.card {{
    background:{card};
    padding:15px;
    border-radius:15px;
    margin-bottom:10px;
}}

.footer {{
    text-align:center;
    margin-top:40px;
    font-size:14px;
    color:{text};
    opacity:0.6;
}}
</style>
""", unsafe_allow_html=True)

# -------------------------
# HEADER
# -------------------------
st.markdown('<div class="title">Alayadivembu M.P.C.S Ltd</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Secure Document Management Portal</div>', unsafe_allow_html=True)

# -------------------------
# ADMIN - CREATE USER
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
# MONTHLY VIEW
# -------------------------
st.subheader("📂 Monthly Reports")

cols = st.columns(3)

for i, m in enumerate(months):
    with cols[i % 3]:

        st.markdown(f"""
        <div class="card">
        <h3>📅 {m}</h3>
        </div>
        """, unsafe_allow_html=True)

        if search:
            c.execute("SELECT * FROM files WHERE filename LIKE ?", (f"%{search}%",))
        else:
            c.execute("SELECT * FROM files WHERE month=?", (m,))

        files = c.fetchall()

        for fdata in files:
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

                if st.button(f"👁 View", key=fdata[0]):
                    st.session_state["pdf"] = file_path

                    c.execute("INSERT INTO audit VALUES (?,?,?)",
                              (st.session_state["user"], fdata[0], str(datetime.now())))
                    conn.commit()

                with open(file_path, "rb") as f:
                    st.download_button("⬇️ Download", f, fdata[0])

# -------------------------
# PDF VIEWER
# -------------------------
if "pdf" in st.session_state:
    st.markdown("---")
    st.subheader("📄 Document Preview")
    show_pdf(st.session_state["pdf"])

# -------------------------
# FOOTER
# -------------------------
st.markdown("""
<div class="footer">
    Created by <b>K. Kiruvaran</b>
</div>
""", unsafe_allow_html=True)