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

TEACHER_ACCESS_KEY = "HMUMER786"

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
        auth_action = st.radio("Chunein:", ["Login", "Teacher Sign Up", "Student Sign Up"], horizontal=True)

        if auth_action == "Login":
            st.markdown("### 🔐 Login Portal")
            with st.form("login_form"):
                uname = st.text_input("Username / ID:")
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
            st.info("💡 Default Teacher Login: `admin` | Password: `admin123`")

        elif auth_action == "Teacher Sign Up":
            st.markdown("### 👨‍🏫 Teacher Registration (HM Umer Choudhary)")
            with st.form("teacher_signup_form"):
                t_key = st.text_input("Teacher Security Key (Secret):", type="password")
                t_uname = st.text_input("Teacher Username (e.g. hmumer):")
                t_name = st.text_input("Mukammal Naam:", value="HM Umer Choudhary")
                t_pwd = st.text_input("Naya Password banayein:", type="password")
                t_pwd_confirm = st.text_input("Password Confirm karein:", type="password")
                submit_t_reg = st.form_submit_button("Create Teacher Account")

                if submit_t_reg:
                    if t_key != TEACHER_ACCESS_KEY:
                        st.error("Ghalat Teacher Security Key! Sirf authorized teachers register ho sakte hain.")
                    elif not t_uname or not t_name or not t_pwd:
                        st.warning("Tamam khane pur karna lazmi hain.")
                    elif t_pwd != t_pwd_confirm:
                        st.error("Passwords aapas mein match nahi kar rahe.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (t_uname,))
                        if c.fetchone():
                            st.error("Ye Username pehle se maujood hai. Koi doosra username chunein.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)", (t_uname, hash_password(t_pwd), t_name, "Teacher"))
                            conn.commit()
                            conn.close()
                            st.success(f"Teacher account kamyabi se ban gaya! Ab 'Login' tab par ja kar username '{t_uname}' se login karein.")

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
                "Standard": ["IAS 1", "IAS 7", "IAS 16", "IAS 20", "IAS 23", "IAS 37"],
                "Topic": ["Presentation of FS", "Cash Flows", "PPE", "Govt Grants", "Borrowing Costs", "Provisions"],
                "Key Rule": ["Current vs Non-Current", "Operating/Investing/Financing", "Cost vs Revaluation", "Deferred Income Method", "Qualifying Assets only", "Reliable estimate & present obligation"]
            }
            st.table(pd.DataFrame(matrix_data))

    # ----------------- STUDENT VIEWS -----------------
    else:
        crn = st.session_state.username
        
        conn = sqlite3.connect(DB_FILE)
        st_info = pd.read_sql_query("SELECT name, level FROM students WHERE crn = ?", conn, params=(crn,))
        st_level = st_info.iloc[0]['level'] if not st_info.empty else "N/A"
        
        marks_df = pd.read_sql_query(
            "SELECT topic as 'Test', score as 'Obtained', total as 'Total', quiz_date as 'Date' FROM quiz_results WHERE crn = ? ORDER BY id ASC", 
            conn, params=(crn,)
        )
        att_df = pd.read_sql_query("SELECT status FROM attendance WHERE crn = ?", conn, params=(crn,))
        conn.close()

        if not marks_df.empty:
            total_obtained = marks_df['Obtained'].sum()
            total_marks = marks_df['Total'].sum()
            overall_pct = round((total_obtained / total_marks) * 100, 1)
            marks_df['Percentage'] = (marks_df['Obtained'] / marks_df['Total']) * 100
        else:
            overall_pct = 0.0

        if not att_df.empty:
            present_count = len(att_df[att_df['status'] == 'Present'])
            att_pct = round((present_count / len(att_df)) * 100, 1)
        else:
            att_pct = 0.0

        if menu == "📈 Performance Dashboard & Charts":
            st.subheader(f"📈 Performance Dashboard (CRN: {crn})")

            col_s1, col_s2, col_s3 = st.columns(3)
            with col_s1:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Overall Score", f"{overall_pct}%")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_s2:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Tests Completed", f"{len(marks_df)}")
                st.markdown('</div>', unsafe_allow_html=True)
            with col_s3:
                st.markdown('<div class="metric-card">', unsafe_allow_html=True)
                st.metric("Attendance Ratio", f"{att_pct}%")
                st.markdown('</div>', unsafe_allow_html=True)

            st.markdown("---")

            if not marks_df.empty:
                st.markdown("#### 🎯 Overall Progress Bar")
                bar_val = min(max(overall_pct / 100.0, 0.0), 1.0)
                st.progress(bar_val, text=f"Overall Score: {overall_pct}%")

                st.markdown("#### 📊 Test-wise Performance Trend")
                marks_df['Test_Label'] = marks_df['Test'] + " (" + marks_df['Date'] + ")"
                chart_df = marks_df.set_index('Test_Label')[['Percentage']]

                col_c1, col_c2 = st.columns([2, 1])
                with col_c1:
                    st.bar_chart(chart_df, color="#1E3A8A")
                with col_c2:
                    disp_df = marks_df[['Test', 'Obtained', 'Total', 'Percentage', 'Date']].copy()
                    disp_df['Percentage'] = disp_df['Percentage'].round(1).astype(str) + "%"
                    st.dataframe(disp_df, use_container_width=True)
            else:
                st.info("Abhi tak aapka koi test record maujood nahi hai.")

        elif menu == "📄 Download Official Report Card":
            st.subheader("📄 Official Student Report Card")
            col_down1, col_down2 = st.columns(2)

            with col_down1:
                st.markdown("#### 📗 Excel Report Card (.xlsx)")
                excel_bytes = generate_excel_report(
                    st.session_state.full_name, crn, st_level, marks_df, overall_pct, att_pct
                )
                st.download_button(
                    label="📥 Download Excel Report Card",
                    data=excel_bytes,
                    file_name=f"ReportCard_{crn}_{date.today()}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            with col_down2:
                st.markdown("#### 📕 PDF / Printable Card (.html / PDF)")
                html_bytes = generate_html_report(
                    st.session_state.full_name, crn, st_level, marks_df, overall_pct, att_pct
                )
                st.download_button(
                    label="📥 Download Print / PDF Card",
                    data=html_bytes,
                    file_name=f"ReportCard_{crn}_{date.today()}.html",
                    mime="text/html",
                    use_container_width=True
                )

            st.markdown("---")
            st.markdown("##### 🔍 Report Card Live Preview")
            st.components.v1.html(html_bytes, height=450, scrolling=True)

        elif menu == "📚 My Books & Notes":
            st.subheader("📚 Available Books & Study Material")
            files = [f for f in os.listdir(UPLOAD_DIR) if not f.startswith("[TEST]")]
            if files:
                for f in files:
                    f_path = os.path.join(UPLOAD_DIR, f)
                    st.markdown(f"📖 **{f}** `({round(os.path.getsize(f_path)/1024, 1)} KB)`")
                    with open(f_path, "rb") as cur_f:
                        st.download_button(label="Download Notes", data=cur_f, file_name=f, key=f"st_{f}")
                    st.markdown("---")
            else:
                st.info("Abhi koi notes upload nahi kiye gaye.")

        elif menu == "📝 Available Tests & Papers":
            st.subheader("📝 Scheduled Tests & Mock Papers")
            tests = [f for f in os.listdir(UPLOAD_DIR) if f.startswith("[TEST]")]
            if tests:
                for t in tests:
                    t_path = os.path.join(UPLOAD_DIR, t)
                    st.markdown(f"📝 **{t.replace('[TEST]', '').replace('.pdf', '')}**")
                    with open(t_path, "rb") as cur_t:
                        st.download_button(label="Download Paper", data=cur_t, file_name=t, key=f"tst_{t}")
                    st.markdown("---")
            else:
                st.info("Koi naya test schedule nahi hai.")

        elif menu == "🤖 Practice AI Quiz":
            st.subheader("🤖 Self Assessment Quiz")
            ans = st.radio("IAS 23 ke tehet capitalization kab suspend hoti hai?", [
                "Jab active development ka kaam abnormal lambe arse ke liye suspend ho",
                "Jab bank interest rate badha de",
                "Jab annual audit start ho"
            ])
            if st.button("Check Answer"):
                if ans == "Jab active development ka kaam abnormal lambe arse ke liye suspend ho":
                    st.success("Durust jawab! (IAS 23 Rule)")
                else:
                    st.error("Ghalat جواب. Durust rule: Active development abnormal suspend hone par.")

        elif menu == "📖 IFRS Revision Matrix":
            st.subheader("Accounting Standards Quick Matrix")
            matrix_data = {
                "Standard": ["IAS 1", "IAS 7", "IAS 16", "IAS 20", "IAS 23"],
                "Title": ["Presentation of FS", "Cash Flows", "Property, Plant & Equipment", "Government Grants", "Borrowing Costs"],
                "Key Rules": ["Current vs Non-Current", "Operating vs Investing vs Financing", "Cost vs Revaluation Model", "Deferred Income Method", "Qualifying Asset Capitalization"]
            }
            st.table(pd.DataFrame(matrix_data))
