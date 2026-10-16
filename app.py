import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import io
from datetime import date

# ----------------- CONFIG & STYLING -----------------
st.set_page_config(
    page_title="HM Umer Choudhary Learning Portal",
    page_icon="🎓",
    layout="wide"
)

st.markdown("""
    <style>
    .main-title {
        font-size: 2.1rem;
        color: #1E3A8A;
        font-weight: 700;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-title {
        font-size: 1rem;
        color: #4B5563;
        text-align: center;
        margin-bottom: 20px;
    }
    .metric-card {
        background-color: #F8FAFC;
        padding: 16px;
        border-radius: 8px;
        border-left: 5px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SECURITY UTILITY -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

# ----------------- REPORT GENERATION UTILITIES -----------------
def generate_excel_report(student_name, crn, level, marks_df, overall_pct, att_pct):
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        summary_data = {
            "Attribute": [
                "Student Name", "CRN / Roll No", "Study Level", 
                "Total Tests Taken", "Overall Percentage", "Attendance Percentage", 
                "Report Date"
            ],
            "Value": [
                student_name, crn, level, 
                len(marks_df), f"{overall_pct}%", f"{att_pct}%", 
                str(date.today())
            ]
        }
        pd.DataFrame(summary_data).to_excel(writer, sheet_name="Student Summary", index=False)
        
        if not marks_df.empty:
            export_df = marks_df[['Test', 'Obtained', 'Total', 'Percentage', 'Date']].copy()
            export_df.to_excel(writer, sheet_name="Test Results Log", index=False)
            
    return output.getvalue()

def generate_html_report(student_name, crn, level, marks_df, overall_pct, att_pct):
    rows_html = ""
    if not marks_df.empty:
        for _, row in marks_df.iterrows():
            rows_html += f"""
            <tr>
                <td style="padding: 10px; border: 1px solid #ddd;">{row['Test']}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row['Obtained']}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row['Total']}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{round(row['Percentage'], 1)}%</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{row['Date']}</td>
            </tr>
            """
    else:
        rows_html = "<tr><td colspan='5' style='text-align:center; padding:15px;'>No test records found.</td></tr>"

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>Report Card - {student_name}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
            .header {{ text-align: center; border-bottom: 3px solid #1E3A8A; padding-bottom: 15px; margin-bottom: 25px; }}
            .header h1 {{ margin: 0; color: #1E3A8A; font-size: 26px; }}
            .header p {{ margin: 5px 0 0 0; color: #555; font-size: 14px; }}
            .student-info {{ width: 100%; margin-bottom: 25px; border-collapse: collapse; }}
            .student-info td {{ padding: 8px 12px; font-size: 14px; }}
            .table {{ width: 100%; border-collapse: collapse; margin-top: 15px; }}
            .table th {{ background-color: #1E3A8A; color: white; padding: 10px; border: 1px solid #1E3A8A; }}
            .metric-box {{ display: inline-block; width: 45%; background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px; padding: 15px; text-align: center; margin: 10px 2%; }}
            .metric-box h3 {{ margin: 0; font-size: 24px; color: #1E3A8A; }}
            .footer {{ margin-top: 50px; text-align: center; font-size: 12px; color: #777; border-top: 1px solid #ddd; padding-top: 15px; }}
            @media print {{
                .no-print {{ display: none; }}
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>HM UMER CHOUDHARY LEARNING PORTAL</h1>
            <p>Chartered Accountancy & Commerce Academy | Student Performance Evaluation</p>
        </div>

        <table class="student-info">
            <tr>
                <td><strong>Student Name:</strong> {student_name}</td>
                <td><strong>CRN / Roll No:</strong> {crn}</td>
            </tr>
            <tr>
                <td><strong>Course / Level:</strong> {level}</td>
                <td><strong>Report Generated Date:</strong> {date.today()}</td>
            </tr>
        </table>

        <div style="text-align: center; margin-bottom: 20px;">
            <div class="metric-box">
                <p style="margin: 0; color: #64748B;">Overall Test Performance</p>
                <h3>{overall_pct}%</h3>
            </div>
            <div class="metric-box">
                <p style="margin: 0; color: #64748B;">Overall Attendance Record</p>
                <h3>{att_pct}%</h3>
            </div>
        </div>

        <h3>Detailed Test Performance</h3>
        <table class="table">
            <thead>
                <tr>
                    <th>Test / Subject Topic</th>
                    <th>Obtained Marks</th>
                    <th>Total Marks</th>
                    <th>Percentage</th>
                    <th>Date Held</th>
                </tr>
            </thead>
            <tbody>
                {rows_html}
            </tbody>
        </table>

        <div class="footer">
            <p>This is an authentic system-generated performance record from HM Umer Choudhary Learning Portal.</p>
            <p class="no-print"><em>To save as PDF: Press Ctrl+P (or Cmd+P on Mac) and select 'Save as PDF'.</em></p>
        </div>
    </body>
    </html>
    """
    return html_content

# ----------------- DATABASE SETUP -----------------
DB_FILE = "portal_database.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password TEXT,
            full_name TEXT,
            role TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS students (
            crn TEXT PRIMARY KEY,
            name TEXT,
            level TEXT,
            email TEXT,
            contact TEXT
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crn TEXT,
            att_date TEXT,
            status TEXT,
            FOREIGN KEY (crn) REFERENCES students(crn)
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS quiz_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            crn TEXT,
            topic TEXT,
            score INTEGER,
            total INTEGER,
            quiz_date TEXT
        )
    ''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute(
            "INSERT INTO users VALUES (?, ?, ?, ?)",
            ("admin", hash_password("admin123"), "HM Umer Choudhary", "Teacher")
        )
    conn.commit()
    conn.close()

init_db()

UPLOAD_DIR = "uploaded_resources"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.full_name = ""
    st.session_state.role = ""

# ----------------- LOGIN / SIGNUP SCREEN -----------------
if not st.session_state.logged_in:
    st.markdown('<div class="main-title">HM UMER CHOUDHARY</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-title">Chartered Accountancy & Commerce Learning Management System</div>', unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        auth_action = st.radio("Chunein:", ["Login", "Student Sign Up"], horizontal=True)

        if auth_action == "Login":
            st.markdown("### 🔐 Login Portal")
            with st.form("login_form"):
                uname = st.text_input("Username / CRN:")
                pwd = st.text_input("Password:", type="password")
                submit_login = st.form_submit_button("Log In")

                if submit_login:
                    hashed_pwd = hash_password(pwd)
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT username, full_name, role FROM users WHERE username = ? AND password = ?", (uname, hashed_pwd))
                    user = c.fetchone()
                    conn.close()

                    if user:
                        st.session_state.logged_in = True
                        st.session_state.username = user[0]
                        st.session_state.full_name = user[1]
                        st.session_state.role = user[2]
                        st.success(f"Khushamdeed, {user[1]}!")
                        st.rerun()
                    else:
                        st.error("Galat username ya password darj kiya gaya hai.")
            st.info("💡 Default Teacher Account: `admin` | Password: `admin123`")

        else:
            st.markdown("### 📝 Student Sign Up")
            with st.form("signup_form"):
                reg_crn = st.text_input("CRN / Roll No (ye login username banega):")
                reg_name = st.text_input("Pura Naam:")
                reg_level = st.selectbox("Level:", ["PRC", "CAF-1 (FAR-1)", "CAF-2 (Tax)", "CAF-6 (FAR-2)", "CFAP"])
                reg_email = st.text_input("Email:")
                reg_contact = st.text_input("Phone / WhatsApp:")
                reg_pwd = st.text_input("Password banayein:", type="password")
                reg_pwd_confirm = st.text_input("Password confirm karein:", type="password")
                submit_reg = st.form_submit_button("Register")

                if submit_reg:
                    if not reg_crn or not reg_name or not reg_pwd:
                        st.warning("Tamam basic maloomat darj karna lazmi hai.")
                    elif reg_pwd != reg_pwd_confirm:
                        st.error("Passwords match nahi kar rahe.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (reg_crn,))
                        if c.fetchone():
                            st.error("Ye CRN pehle se registered hai.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (reg_crn, hash_password(reg_pwd), reg_name, "Student"))
                            c.execute("INSERT OR REPLACE INTO students VALUES (?, ?, ?, ?, ?)", (reg_crn, reg_name, reg_level, reg_email, reg_contact))
                            conn.commit()
                            conn.close()
                            st.success("Registration mukammal ho gayi! Ab Login karein.")

# ----------------- AUTHENTICATED PORTAL -----------------
else:
    with st.sidebar:
        st.markdown(f"### Khushamdeed, **{st.session_state.full_name}**")
        st.caption(f"Role: **{st.session_state.role}** | ID: `{st.session_state.username}`")
        st.divider()

        if st.session_state.role == "Teacher":
            menu_options = [
                "📊 Dashboard Overview",
                "📚 Books & Notes Portal",
                "📝 Test & Assessment Hub",
                "👨‍🎓 Student Directory",
                "📅 Smart Attendance Tracker",
                "📖 IFRS Revision Matrix"
            ]
        else:
            menu_options = [
                "📈 Performance Dashboard & Charts",
                "📄 Download Official Report Card",
                "📚 My Books & Notes",
                "📝 Available Tests & Papers",
                "🤖 Practice AI Quiz",
                "📖 IFRS Revision Matrix"
            ]

        menu = st.radio("Navigation Menu:", menu_options)
        st.divider()
        if st.button("🚪 Log Out"):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.full_name = ""
            st.session_state.role = ""
            st.rerun()

    # Title Banner
    st.markdown('<div class="main-title">HM UMER CHOUDHARY</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-title">Portal for {st.session_state.role}</div>', unsafe_allow_html=True)

    # ----------------- TEACHER VIEWS -----------------
    if st.session_state.role == "Teacher":

        if menu == "📊 Dashboard Overview":
            st.subheader("Portal Overview")
            conn = sqlite3.connect(DB_FILE)
            total_students = pd.read_sql_query("SELECT COUNT(*) as count FROM students", conn).iloc[0]['count']
            total_att = pd.read_sql_query("SELECT COUNT(*) as count FROM attendance", conn).iloc[0]['count']
            total_quizzes = pd.read_sql_query("SELECT COUNT(*) as count FROM quiz_results", conn).iloc[0]['count']
            conn.close()
            total_files = len(os.listdir(UPLOAD_DIR))

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Registered Students", f"{total_students}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Uploaded Material", f"{total_files}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Attendance Entries", f"{total_att}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col4:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Test Marks Entries", f"{total_quizzes}")
                st.markdown('</div>', unsafe_allow_html=True)

        elif menu == "📚 Books & Notes Portal":
            st.subheader("📚 Books, Study Text & Notes Upload Portal")
            col_up, col_list = st.columns([1, 1])
            with col_up:
                category = st.selectbox("Category:", ["Financial Accounting (CAF-1)", "Taxation (CAF-2)", "Business Law", "Cost Accounting", "Auditing", "Other Notes"])
                uploaded_file = st.file_uploader("Select File (PDF, DOCX, PPTX):", type=["pdf", "docx", "pptx"])
                if st.button("Upload Karein"):
                    if uploaded_file is not None:
                        save_path = os.path.join(UPLOAD_DIR, f"[{category}] {uploaded_file.name}")
                        with open(save_path, "wb") as f:
                            f.write(uploaded_file.getbuffer())
                        st.success(f"File '{uploaded_file.name}' save ho gayi!")
                    else:
                        st.warning("File chunein.")

            with col_list:
                st.markdown("#### Available Notes")
                files = os.listdir(UPLOAD_DIR)
                if files:
                    for f in files:
                        f_path = os.path.join(UPLOAD_DIR, f)
                        st.markdown(f"📄 **{f}** `({round(os.path.getsize(f_path)/1024, 1)} KB)`")
                        with open(f_path, "rb") as cur_f:
                            st.download_button(label="Download", data=cur_f, file_name=f, key=f)
                        st.markdown("---")
                else:
                    st.info("Abhi koi file maujood nahi hai.")

        elif menu == "📝 Test & Assessment Hub":
            st.subheader("📝 Test Schedule & Marks Management")
            t_tab1, t_tab2 = st.tabs(["Test Paper Post Karein", "Student Marks Darj Karein"])
            with t_tab1:
                test_title = st.text_input("Test Title (e.g. CAF-1 Test 2):")
                test_doc = st.file_uploader("Test Paper (PDF):", type=["pdf"], key="teach_tst")
                if st.button("Test Post Karein"):
                    if test_title and test_doc:
                        with open(os.path.join(UPLOAD_DIR, f"[TEST] {test_title}.pdf"), "wb") as f:
                            f.write(test_doc.getbuffer())
                        st.success("Test schedule ho gaya!")
            with t_tab2:
                conn = sqlite3.connect(DB_FILE)
                st_df = pd.read_sql_query("SELECT crn, name FROM students", conn)
                conn.close()
                if not st_df.empty:
                    st_pick = st.selectbox("Student Chunein:", [f"{r['crn']} - {r['name']}" for _, r in st_df.iterrows()])
                    t_subj = st.text_input("Test Ka Naam:")
                    s_score = st.number_input("Obtained Marks:", min_value=0, max_value=100, value=35)
                    s_total = st.number_input("Total Marks:", min_value=1, max_value=100, value=50)
                    t_date = st.date_input("Test Date:", date.today())
                    if st.button("Marks Save Karein"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO quiz_results (crn, topic, score, total, quiz_date) VALUES (?, ?, ?, ?, ?)",
                                  (st_pick.split(" - ")[0], t_subj, s_score, s_total, str(t_date)))
                        conn.commit()
                        conn.close()
                        st.success("Marks save ho gaye.")

        elif menu == "👨‍🎓 Student Directory":
            st.subheader("👨‍🎓 Registered Students Directory")
            conn = sqlite3.connect(DB_FILE)
            students_df = pd.read_sql_query("SELECT crn as 'CRN', name as 'Name', level as 'Level', email as 'Email', contact as 'Contact' FROM students", conn)
            conn.close()
            st.dataframe(students_df, use_container_width=True)

        elif menu == "📅 Smart Attendance Tracker":
            st.subheader("📅 Rozana Ki Class Attendance")
            conn = sqlite3.connect(DB_FILE)
            students_df = pd.read_sql_query("SELECT crn, name, level FROM students", conn)
            conn.close()
            if not students_df.empty:
                att_date = st.date_input("Date:", date.today())
                records = []
                with st.form("att_form"):
                    for _, r in students_df.iterrows():
                        c1, c2 = st.columns([3, 2])
                        c1.write(f"**{r['name']}** ({r['crn']})")
                        stat = c2.selectbox("Status:", ["Present", "Absent", "Leave"], key=f"att_{r['crn']}")
                        records.append((r['crn'], str(att_date), stat))
                    if st.form_submit_button("Attendance Save Karein"):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        for rec in records:
                            c.execute("INSERT INTO attendance (crn, att_date, status) VALUES (?, ?, ?)", rec)
                        conn.commit()
                        conn.close()
                        st.success("Attendance save ho gayi.")

        elif menu == "📖 IFRS Revision Matrix":
            st.subheader("Key Accounting Standards Matrix")
            matrix_data = {
                "Standard": ["IAS 1", "IAS 7", "IAS 16", "IAS 20", "IAS],
