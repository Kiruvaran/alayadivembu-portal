import streamlit as st
import pandas as pd

# PDF
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, legal
from reportlab.lib.styles import getSampleStyleSheet

# -------------------------
# PAGE CONFIG
# -------------------------
st.set_page_config(
    page_title="Alayadivembu Payroll ERP",
    layout="wide"
)

# -------------------------
# STYLE
# -------------------------
st.markdown("""
<style>
body {background-color:#f4f7fb;}
h1,h2,h3 {color:#0d47a1;}

.stButton>button {
    background-color:#0d47a1;
    color:white;
    border-radius:8px;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# SESSION
# -------------------------
if "employees" not in st.session_state:
    st.session_state["employees"] = []

if "attendance" not in st.session_state:
    st.session_state["attendance"] = []

# -------------------------
# PDF FUNCTION
# -------------------------
def generate_pdf(data):

    file_path = "paysheet.pdf"

    doc = SimpleDocTemplate(
        file_path,
        pagesize=landscape(legal)
    )

    styles = getSampleStyleSheet()
    elements = []

    # Title
    elements.append(Paragraph(
        "<b>ALAYADIVEMBU M.P.C.S LTD - PAY SHEET</b>",
        styles["Title"]
    ))
    elements.append(Spacer(1, 20))

    # Table
    table_data = [list(data.columns)] + data.values.tolist()

    table = Table(table_data)

    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.darkblue),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 1, colors.black),
        ("ALIGN", (0,0), (-1,-1), "CENTER"),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold")
    ]))

    elements.append(table)
    elements.append(Spacer(1, 30))

    elements.append(Paragraph("Prepared By: ____________________", styles["Normal"]))
    elements.append(Paragraph("Approved By: ____________________", styles["Normal"]))

    doc.build(elements)

    return file_path

# -------------------------
# MENU
# -------------------------
st.sidebar.title("🏢 Payroll ERP")
menu = st.sidebar.radio("Menu", [
    "Dashboard",
    "Add Employee",
    "Attendance Payroll",
    "Pay Sheet",
    "Reports"
])

# ===================================================
# DASHBOARD
# ===================================================
if menu == "Dashboard":

    st.title("📊 Dashboard")

    df = pd.DataFrame(st.session_state["employees"])

    c1, c2, c3 = st.columns(3)

    c1.metric("Employees", len(df))
    c2.metric("Total Salary", int(df["Total Salary"].sum()) if not df.empty else 0)
    c3.metric("Net Salary", int(df["Net Salary"].sum()) if not df.empty else 0)

    if not df.empty:
        st.dataframe(df)

# ===================================================
# ADD EMPLOYEE
# ===================================================
if menu == "Add Employee":

    st.title("➕ Add Employee")

    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Name")
        designation = st.text_input("Designation")
        department = st.selectbox("Department", [
            "Head Office",
            "Fuel Filling Station",
            "Rural Bank"
        ])

    with col2:
        basic = st.number_input("Basic", 0)
        increment = st.number_input("Increment", 0)
        loan = st.number_input("Loan", 0)
        advance = st.number_input("Advance", 0)

    if st.button("Save Employee"):

        total = basic + increment
        epf8 = total * 0.08
        etf3 = basic * 0.03
        epf12 = basic * 0.12
        net = total - epf8 - loan - advance

        st.session_state["employees"].append({
            "Name": name,
            "Designation": designation,
            "Department": department,
            "Basic": basic,
            "Increment": increment,
            "Total Salary": total,
            "EPF 8%": epf8,
            "ETF 3%": etf3,
            "EPF 12%": epf12,
            "Loan": loan,
            "Advance": advance,
            "Net Salary": net
        })

        st.success("Saved ✅")

# ===================================================
# ATTENDANCE
# ===================================================
if menu == "Attendance Payroll":

    st.title("📅 Attendance → Salary")

    staff = st.session_state["employees"]

    if not staff:
        st.warning("Add employees first")
    else:

        for i, s in enumerate(staff):

            present = st.number_input(
                f"{s['Name']} Present Days",
                0, 30, key=f"a{i}"
            )

            st.session_state["attendance"].append({
                "Name": s["Name"],
                "Basic": s["Basic"],
                "Increment": s["Increment"],
                "Loan": s["Loan"],
                "Advance": s["Advance"],
                "Present": present
            })

        if st.button("Generate Payroll"):

            report = []

            for a in st.session_state["attendance"]:

                total = a["Basic"] + a["Increment"]
                daily = total / 30
                gross = daily * a["Present"]

                epf8 = gross * 0.08
                etf3 = a["Basic"] * 0.03
                epf12 = a["Basic"] * 0.12

                net = gross - epf8 - a["Loan"] - a["Advance"]

                report.append({
                    "Name": a["Name"],
                    "Present": a["Present"],
                    "Gross": round(gross),
                    "EPF 8%": round(epf8),
                    "ETF 3%": round(etf3),
                    "EPF 12%": round(epf12),
                    "Net": round(net)
                })

            st.session_state["report"] = pd.DataFrame(report)
            st.success("Payroll Generated ✅")

# ===================================================
# PAY SHEET
# ===================================================
if menu == "Pay Sheet":

    st.title("📄 Pay Sheet")

    if "report" in st.session_state:

        df = st.session_state["report"]

        st.dataframe(df)

        st.download_button("⬇️ CSV", df.to_csv(index=False))

        if st.button("📄 Generate Legal PDF"):

            path = generate_pdf(df)

            with open(path, "rb") as f:
                st.download_button("⬇️ Download PDF", f)

    else:
        st.info("Generate payroll first")

# ===================================================
# REPORTS
# ===================================================
if menu == "Reports":

    st.title("📊 Summary")

    if "report" in st.session_state:

        df = st.session_state["report"]

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("Salary", int(df["Gross"].sum()))
        c2.metric("EPF 8%", int(df["EPF 8%"].sum()))
        c3.metric("ETF 3%", int(df["ETF 3%"].sum()))
        c4.metric("EPF 12%", int(df["EPF 12%"].sum()))

        total_cost = df["Gross"].sum() + df["ETF 3%"].sum() + df["EPF 12%"].sum()

        st.success(f"TOTAL COST: {int(total_cost):,}")

    else:
        st.info("No data")