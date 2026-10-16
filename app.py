import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import io
import time
import re
from datetime import date, datetime
from pypdf import PdfReader

# ----------------- PAGE CONFIGURATION & STYLING -----------------
st.set_page_config(
    page_title="HM Umer Choudhary Learning Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E3A8A 100%);
        padding: 24px;
        border-radius: 12px;
        color: white;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.15);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2.2rem;
        font-weight: 700;
        color: #FFFFFF;
        letter-spacing: 0.5px;
    }
    .main-header p {
        margin: 6px 0 0 0;
        font-size: 1rem;
        color: #93C5FD;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 10px;
        padding: 18px;
        text-align: center;
        border-top: 4px solid #1E3A8A;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
    }
    .metric-card h3 {
        margin: 0;
        font-size: 1.8rem;
        color: #1E3A8A;
        font-weight: 700;
    }
    .metric-card p {
        margin: 5px 0 0 0;
        font-size: 0.85rem;
        color: #64748B;
        font-weight: 600;
        text-transform: uppercase;
    }
    .course-badge {
        display: inline-block;
        background-color: #DBEAFE;
        color: #1E40AF;
        padding: 4px 10px;
        border-radius: 6px;
        font-size: 0.8rem;
        font-weight: 600;
    }
    .solution-box {
        background-color: #F8FAFC;
        border-left: 4px solid #3B82F6;
        padding: 15px;
        border-radius: 6px;
        margin-top: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- SECURITY & CONSTANTS -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

TEACHER_KEY = "HMUMER786"
DB_FILE = "portal_core.db"
UPLOAD_DIR = "academic_resources"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# ----------------- COURSE STRUCTURE -----------------
COURSES_DATA = {
    "PRC (CA Foundation)": [
        "PRC-1 Business Writing & Comprehension",
        "PRC-2 Quantitative Methods",
        "PRC-3 Principles of Economics",
        "PRC-4 Introduction to Accounting",
        "PRC-5 Business Law"
    ],
    "CAF Group A": [
        "CAF-1 Financial Accounting & Reporting 1 (FAR-1)",
        "CAF-2 Tax Practices",
        "CAF-3 Cost & Management Accounting",
        "CAF-4 Business Law"
    ],
    "CAF Group B": [
        "CAF-5 Financial Accounting & Reporting 2 (FAR-2)",
        "CAF-6 Managerial & Financial Analysis",
        "CAF-7 Company Law",
        "CAF-8 Audit & Assurance"
    ],
    "ACCA": [
        "FA1/FA2/FFA Financial Accounting",
        "MA1/MA2/FMA Management Accounting",
        "FR Financial Reporting",
        "AA Audit & Assurance",
        "PM Performance Management",
        "TX Taxation",
        "FM Financial Management"
    ]
}

# ----------------- DATABASE SCHEMA -----------------
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        full_name TEXT,
        role TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS students (
        crn TEXT PRIMARY KEY,
        name TEXT,
        course_stream TEXT,
        email TEXT,
        contact TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS attendance_sessions (
        session_id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        subject TEXT,
        pin TEXT,
        session_date TEXT,
        status TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS student_attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id INTEGER,
        crn TEXT,
        marked_at TEXT,
        FOREIGN KEY (session_id) REFERENCES attendance_sessions(session_id)
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS mock_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        subject TEXT,
        title TEXT,
        duration_minutes INTEGER,
        total_marks INTEGER,
        created_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS test_questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        test_id INTEGER,
        question TEXT,
        opt_a TEXT,
        opt_b TEXT,
        opt_c TEXT,
        opt_d TEXT,
        correct_opt TEXT,
        exp_en TEXT,
        exp_ur TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS student_test_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        crn TEXT,
        test_id INTEGER,
        score INTEGER,
        total INTEGER,
        submitted_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS study_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        subject TEXT,
        title TEXT,
        file_path TEXT,
        uploaded_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS video_lectures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        subject TEXT,
        title TEXT,
        video_url TEXT,
        added_at TEXT
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS notices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        message TEXT,
        posted_at TEXT
    )''')
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                  ("admin", hash_password("admin123"), "HM Umer Choudhary", "Teacher"))
    conn.commit()
    conn.close()

init_db()

# ----------------- PDF EXTRACTOR & MCQ GENERATOR -----------------
def extract_text_from_pdf(pdf_file, start_page, end_page):
    reader = PdfReader(pdf_file)
    total_pages = len(reader.pages)
    
    start_idx = max(0, start_page - 1)
    end_idx = min(total_pages, end_page)
    
    extracted_text = ""
    for p_no in range(start_idx, end_idx):
        page = reader.pages[p_no]
        txt = page.extract_text()
        if txt:
            extracted_text += txt + "\n"
            
    return extracted_text.strip(), total_pages

def generate_mcqs_from_extracted_text(text_content, num_questions, topic_title):
    # Split text into meaningful sentences
    sentences = [s.strip() for s in re.split(r'[\.\n\r]+', text_content) if len(s.strip()) > 35]
    mcqs = []
    
    distractor_pool = [
        "Historical cost adjusted for standard fair value",
        "Immediate derecognition and direct profit/loss write-off",
        "Discretionary management disclosure without audit",
        "Amortized over arbitrary management tenure",
        "Restrospective restatement prohibited by framework",
        "Contingent liability recognized without obligation",
        "Recorded exclusively on cash settlement basis"
    ]
    
    if not sentences:
        for i in range(num_questions):
            mcqs.append({
                "question": f"Q{i+1}: What is the statutory financial reporting requirement regarding {topic_title}?",
                "a": "Faithful representation and compliance with relevant IFRS/statutory framework",
                "b": "Total exemption from audit oversight",
                "c": "Arbitrary recognition without verification",
                "d": "Pure cash basis reporting only",
                "correct": "A",
                "exp_en": f"Standard rules for {topic_title} require faithful representation and compliance with applicable accounting and reporting frameworks.",
                "exp_ur": f"{topic_title} کے قواعد کے مطابق مالیاتی بیانات کی شفافیت اور متعلقہ اکاؤنٹنگ فریم ورک پر عمل درآمد لازمی ہے۔"
            })
        return mcqs

    step = max(1, len(sentences) // num_questions)
    selected_sentences = sentences[0::step][:num_questions]
    
    for idx, s in enumerate(selected_sentences):
        words = s.split()
        if len(words) >= 6:
            mid = len(words) // 2
            target_word = words[mid].strip(",.()\"':;")
            if len(target_word) < 4:
                target_word = words[mid-1].strip(",.()\"':;")
                
            prompt = s.replace(target_word, "________")
            distractors = [d for d in distractor_pool if d != target_word][:3]
            
            mcqs.append({
                "question": f"Q{idx+1}: Complete the statement from book ({topic_title}): \"{prompt}\"",
                "a": target_word,
                "b": distractors[0] if len(distractors) > 0 else "Optional disclosure",
                "c": distractors[1] if len(distractors) > 1 else "Direct expense debit",
                "d": distractors[2] if len(distractors) > 2 else "Non-current classification",
                "correct": "A",
                "exp_en": f"From the textbook text: \"{s}\". The missing technical component is '{target_word}'.",
                "exp_ur": f"کتابی متن کے مطابق اصل جملہ تھا: \"{s}\"۔ اس اصول کی مناسب تشریح کے لیے درست جواب '{target_word}' ہے۔"
            })
            
    # Fallback if fewer questions formed
    while len(mcqs) < num_questions:
        q_num = len(mcqs) + 1
        mcqs.append({
            "question": f"Q{q_num}: Which criterion is fundamental for {topic_title} evaluation?",
            "a": "Materiality and prudent recognition",
            "b": "Complete postponement of disclosures",
            "c": "Unilateral assessment without verification",
            "d": "Disregard of accrual accounting principle",
            "correct": "A",
            "exp_en": f"Prudence and materiality are core underlying assumptions applicable to {topic_title}.",
            "exp_ur": f"{topic_title} میں اصول احتیاط اور اہمیت (Materiality) پر عمل درآمد ضروری ہے۔"
        })
        
    return mcqs

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.full_name = ""
    st.session_state.role = ""
    st.session_state.course_stream = ""

if "test_active" not in st.session_state:
    st.session_state.test_active = False
    st.session_state.current_test_id = None
    st.session_state.test_start_time = None
    st.session_state.test_submitted = False
    st.session_state.last_submission = {}

# ----------------- AUTHENTICATION -----------------
if not st.session_state.logged_in:
    st.markdown("""
        <div class="main-header">
            <h1>HM UMER CHOUDHARY</h1>
            <p>Chartered Accountancy & Commerce Learning Management System</p>
        </div>
    """, unsafe_allow_html=True)

    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        auth_mode = st.radio("Choose Action:", ["Sign In", "Student Sign Up", "Faculty Sign Up"], horizontal=True)

        if auth_mode == "Sign In":
            st.markdown("### 🔐 Secure Sign In")
            with st.form("signin_form"):
                in_user = st.text_input("Username or CRN Roll No:")
                in_pass = st.text_input("Password:", type="password")
                btn_login = st.form_submit_button("Sign In", use_container_width=True)

                if btn_login:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT username, full_name, role FROM users WHERE username = ? AND password = ?",
                              (in_user, hash_password(in_pass)))
                    user_data = c.fetchone()
                    
                    if user_data:
                        st.session_state.logged_in = True
                        st.session_state.username = user_data[0]
                        st.session_state.full_name = user_data[1]
                        st.session_state.role = user_data[2]
                        
                        if user_data[2] == "Student":
                            c.execute("SELECT course_stream FROM students WHERE crn = ?", (user_data[0],))
                            st_res = c.fetchone()
                            st.session_state.course_stream = st_res[0] if st_res else "PRC (CA Foundation)"
                        conn.close()
                        st.success(f"Welcome, {user_data[1]}!")
                        st.rerun()
                    else:
                        conn.close()
                        st.error("Invalid Username or Password.")
            st.info("💡 Default Faculty Login: `admin` | Password: `admin123`")

        elif auth_mode == "Faculty Sign Up":
            st.markdown("### 👨‍🏫 Faculty Member Registration")
            with st.form("faculty_reg"):
                f_sec = st.text_input("Faculty Authorization Key:", type="password")
                f_user = st.text_input("Preferred Faculty Username:")
                f_name = st.text_input("Official Name:", value="HM Umer Choudhary")
                f_pwd1 = st.text_input("Password:", type="password")
                f_pwd2 = st.text_input("Confirm Password:", type="password")
                btn_f_reg = st.form_submit_button("Register Faculty Account", use_container_width=True)

                if btn_f_reg:
                    if f_sec != TEACHER_KEY:
                        st.error("Unauthorized: Incorrect security authorization key.")
                    elif not f_user or not f_pwd1:
                        st.warning("Please fill all required fields.")
                    elif f_pwd1 != f_pwd2:
                        st.error("Passwords do not match.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (f_user,))
                        if c.fetchone():
                            st.error("This username already exists.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                                      (f_user, hash_password(f_pwd1), f_name, "Teacher"))
                            conn.commit()
                            conn.close()
                            st.success(f"Faculty account created successfully for {f_name}. Switch to Sign In.")

        else:
            st.markdown("### 👨‍🎓 Student Registration")
            with st.form("student_reg"):
                s_crn = st.text_input("Student CRN / Roll Number (Login Username):")
                s_name = st.text_input("Full Legal Name:")
                s_stream = st.selectbox("Select Enrolled Course Program:", list(COURSES_DATA.keys()))
                s_email = st.text_input("Email Address:")
                s_phone = st.text_input("WhatsApp / Contact Number:")
                s_pwd1 = st.text_input("Password:", type="password")
                s_pwd2 = st.text_input("Confirm Password:", type="password")
                btn_s_reg = st.form_submit_button("Complete Student Enrollment", use_container_width=True)

                if btn_s_reg:
                    if not s_crn or not s_name or not s_pwd1:
                        st.warning("Please complete all essential fields.")
                    elif s_pwd1 != s_pwd2:
                        st.error("Passwords do not match.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (s_crn,))
                        if c.fetchone():
                            st.error("This CRN is already registered in the system.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?)",
                                      (s_crn, hash_password(s_pwd1), s_name, "Student"))
                            c.execute("INSERT INTO students VALUES (?, ?, ?, ?, ?)",
                                      (s_crn, s_name, s_stream, s_email, s_phone))
                            conn.commit()
                            conn.close()
                            st.success("Registration completed successfully! Please proceed to Sign In.")

# ----------------- MAIN CONSOLE -----------------
else:
    with st.sidebar:
        st.markdown(f"### 👤 **{st.session_state.full_name}**")
        st.markdown(f"<span class='course-badge'>{st.session_state.role}</span>", unsafe_allow_html=True)
        if st.session_state.role == "Student":
            st.caption(f"Stream: **{st.session_state.course_stream}**")
            st.caption(f"CRN: `{st.session_state.username}`")
        st.divider()

        if st.session_state.role == "Teacher":
            menu_choice = st.radio("Teacher Management:", [
                "📊 Faculty Dashboard",
                "📖 Book PDF to AI Quiz Generator",
                "👨‍🎓 Student Directory & Export",
                "📚 Notes & Study Text Center",
                "🎥 Video Lectures Manager",
                "🛡️ Anti-Cheat Attendance Desk",
                "📢 Notice Board"
            ])
        else:
            menu_choice = st.radio("Student Portal:", [
                "📈 My Performance & Overview",
                "⏱️ Take Timed Quiz / Test",
                "📚 My Study Materials",
                "🎥 My Video Lectures",
                "🛡️ Mark My Attendance",
                "📄 Academic Report Card"
            ])

        st.divider()
        if st.button("🚪 Sign Out", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.full_name = ""
            st.session_state.role = ""
            st.session_state.course_stream = ""
            st.session_state.test_active = False
            st.rerun()

    # ----------------- TEACHER INTERFACE -----------------
    if st.session_state.role == "Teacher":
        st.markdown(f"""
            <div class="main-header">
                <h1>HM UMER CHOUDHARY FACULTY DESK</h1>
                <p>Academic Program Control, Book PDF AI Quiz Engine & Student Monitoring</p>
            </div>
        """, unsafe_allow_html=True)

        if menu_choice == "📊 Faculty Dashboard":
            conn = sqlite3.connect(DB_FILE)
            tot_st = pd.read_sql_query("SELECT COUNT(*) as c FROM students", conn).iloc[0]['c']
            tot_ts = pd.read_sql_query("SELECT COUNT(*) as c FROM mock_tests", conn).iloc[0]['c']
            tot_fl = len(os.listdir(UPLOAD_DIR))
            tot_vd = pd.read_sql_query("SELECT COUNT(*) as c FROM video_lectures", conn).iloc[0]['c']
            conn.close()

            c1, c2, c3, c4 = st.columns(4)
            c1.markdown(f'<div class="metric-card"><h3>{tot_st}</h3><p>Enrolled Students</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><h3>{tot_ts}</h3><p>AI & Manual Tests</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><h3>{tot_fl}</h3><p>Uploaded Documents</p></div>', unsafe_allow_html=True)
            c4.markdown(f'<div class="metric-card"><h3>{tot_vd}</h3><p>Published Videos</p></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("📋 Student Distribution by Stream")
            conn = sqlite3.connect(DB_FILE)
            dist_df = pd.read_sql_query("SELECT course_stream as 'Course Program', COUNT(*) as 'Student Count' FROM students GROUP BY course_stream", conn)
            conn.close()
            if not dist_df.empty:
                st.table(dist_df)
            else:
                st.info("No students enrolled yet.")

        elif menu_choice == "📖 Book PDF to AI Quiz Generator":
            st.subheader("📖 Upload Book PDF & Generate Specific-Page AI Quiz")
            st.write("Upload a textbook or notes PDF, specify the page range (e.g., Page 15 to 20), set the number of questions, and the AI will generate questions directly from that text!")

            with st.form("pdf_ai_generator_form"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    ai_stream = st.selectbox("Target Course Stream:", list(COURSES_DATA.keys()))
                    ai_subject = st.selectbox("Target Subject:", COURSES_DATA[ai_stream])
                    quiz_title = st.text_input("Quiz Title (e.g., IAS 23 Borrowing Costs - Pages 45-50):")
                with col_c2:
                    pdf_doc = st.file_uploader("Upload Book / Chapter PDF:", type=["pdf"])
                    col_p1, col_p2, col_p3 = st.columns(3)
                    start_p = col_p1.number_input("Start Page:", min_value=1, value=1)
                    end_p = col_p2.number_input("End Page:", min_value=1, value=5)
                    num_q = col_p3.number_input("No. of Questions:", min_value=1, max_value=25, value=5)

                col_t1, col_t2 = st.columns(2)
                test_timer = col_t1.number_input("Test Timer (Minutes):", min_value=5, max_value=180, value=15)
                test_total_marks = col_t2.number_input("Total Test Marks:", min_value=5, max_value=200, value=15)

                btn_generate_from_pdf = st.form_submit_button("⚡ Generate AI Quiz From Selected Pages & Publish Test", use_container_width=True)

                if btn_generate_from_pdf:
                    if not pdf_doc:
                        st.error("Please upload a PDF file first.")
                    elif not quiz_title:
                        st.error("Please specify a Quiz Title.")
                    elif start_p > end_p:
                        st.error("Start Page cannot be greater than End Page.")
                    else:
                        with st.spinner("Reading PDF pages and generating AI questions..."):
                            extracted_text, total_p = extract_text_from_pdf(pdf_doc, int(start_p), int(end_p))
                            
                            if not extracted_text:
                                st.warning(f"Could not extract readable text from pages {start_p}-{end_p}. Please ensure the PDF has selectable text (not scanned images).")
                            else:
                                mcq_items = generate_mcqs_from_extracted_text(extracted_text, int(num_q), quiz_title)
                                
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("INSERT INTO mock_tests (course_stream, subject, title, duration_minutes, total_marks, created_at) VALUES (?, ?, ?, ?, ?, ?)",
                                          (ai_stream, ai_subject, f"[AI Book Test] {quiz_title}", test_timer, test_total_marks, str(date.today())))
                                test_id = c.lastrowid
                                
                                for item in mcq_items:
                                    c.execute("INSERT INTO test_questions (test_id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                              (test_id, item['question'], item['a'], item['b'], item['c'], item['d'], item['correct'], item['exp_en'], item['exp_ur']))
                                conn.commit()
                                conn.close()
                                
                                st.success(f"🎉 Success! Extracted text from pages {start_p}-{end_p} (Total Book Pages: {total_p}). Generated {len(mcq_items)} MCQs and published as live timed test for {ai_stream} students!")

            st.markdown("---")
            st.markdown("#### 📋 Published Timed Tests in Database")
            conn = sqlite3.connect(DB_FILE)
            t_published = pd.read_sql_query("SELECT id, course_stream, subject, title, duration_minutes, total_marks FROM mock_tests ORDER BY id DESC", conn)
            conn.close()
            if not t_published.empty:
                st.dataframe(t_published, use_container_width=True)

        elif menu_choice == "👨‍🎓 Student Directory & Export":
            st.subheader("👨‍🎓 Complete Student Directory")
            conn = sqlite3.connect(DB_FILE)
            s_all = pd.read_sql_query("SELECT crn as 'CRN / Roll No', name as 'Student Name', course_stream as 'Program', email as 'Email Address', contact as 'WhatsApp No' FROM students", conn)
            conn.close()

            if not s_all.empty:
                out = io.BytesIO()
                with pd.ExcelWriter(out, engine='openpyxl') as writer:
                    s_all.to_excel(writer, index=False, sheet_name="Students_List")
                
                col_d1, col_d2 = st.columns([3, 1])
                with col_d2:
                    st.download_button(
                        label="📥 Export to Excel (.xlsx)",
                        data=out.getvalue(),
                        file_name=f"Students_Directory_{date.today()}.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        use_container_width=True
                    )
                st.dataframe(s_all, use_container_width=True)
            else:
                st.info("Student directory is currently empty.")

        elif menu_choice == "📚 Notes & Study Text Center":
            st.subheader("📚 Upload Subject-Wise Books & Lecture Notes")
            u_stream = st.selectbox("Select Target Course Program:", list(COURSES_DATA.keys()))
            u_subject = st.selectbox("Select Subject:", COURSES_DATA[u_stream])
            u_title = st.text_input("Material Title (e.g. IAS 16 Comprehensive Summary Notes):")
            u_file = st.file_uploader("Select PDF or Document:", type=["pdf", "docx", "pptx", "xlsx"])

            if st.button("Upload Document", use_container_width=True):
                if u_file and u_title:
                    clean_name = f"[{u_stream.split()[0]}]_{u_file.name}"
                    save_path = os.path.join(UPLOAD_DIR, clean_name)
                    with open(save_path, "wb") as f:
                        f.write(u_file.getbuffer())
                    
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO study_materials (course_stream, subject, title, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                              (u_stream, u_subject, u_title, save_path, str(date.today())))
                    conn.commit()
                    conn.close()
                    st.success("Study material published to enrolled students successfully!")

        elif menu_choice == "🎥 Video Lectures Manager":
            st.subheader("🎥 Publish Video Lecture Links")
            v_stream = st.selectbox("Select Course Program:", list(COURSES_DATA.keys()))
            v_subject = st.selectbox("Select Subject:", COURSES_DATA[v_stream])
            v_title = st.text_input("Lecture Title (e.g. Sales Tax Computation Lecture 01):")
            v_url = st.text_input("Video Web Link (YouTube, Vimeo, Google Drive):")

            if st.button("Publish Video Lecture", use_container_width=True):
                if v_title and v_url:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO video_lectures (course_stream, subject, title, video_url, added_at) VALUES (?, ?, ?, ?, ?)",
                              (v_stream, v_subject, v_title, v_url, str(date.today())))
                    conn.commit()
                    conn.close()
                    st.success("Video lecture published!")

        elif menu_choice == "🛡️ Anti-Cheat Attendance Desk":
            st.subheader("🛡️ Secure Anti-Cheat Attendance Session Generator")
            col_att1, col_att2 = st.columns([1, 1])
            with col_att1:
                att_stream = st.selectbox("Course Program for Class:", list(COURSES_DATA.keys()))
                att_subject = st.selectbox("Class Subject:", COURSES_DATA[att_stream])
                att_pin = st.text_input("Set 4-Digit Secure PIN (e.g. 8492):", max_chars=4)
                
                if st.button("Start Live Attendance Session", use_container_width=True):
                    if len(att_pin) == 4:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO attendance_sessions (course_stream, subject, pin, session_date, status) VALUES (?, ?, ?, ?, 'OPEN')",
                                  (att_stream, att_subject, att_pin, str(date.today())))
                        conn.commit()
                        conn.close()
                        st.success(f"Live session initialized! Announce PIN '{att_pin}' to students.")
                    else:
                        st.error("PIN must be exactly 4 digits.")

            with col_att2:
                st.markdown("#### Active / Recent Sessions")
                conn = sqlite3.connect(DB_FILE)
                sessions_df = pd.read_sql_query("SELECT session_id, course_stream, subject, pin, session_date, status FROM attendance_sessions ORDER BY session_id DESC LIMIT 5", conn)
                conn.close()
                if not sessions_df.empty:
                    st.dataframe(sessions_df, use_container_width=True)
                else:
                    st.info("No active attendance sessions created yet.")

        elif menu_choice == "📢 Notice Board":
            st.subheader("📢 Publish Official Announcement")
            n_stream = st.selectbox("Target Stream (or All):", ["All Students"] + list(COURSES_DATA.keys()))
            n_msg = st.text_area("Announcement Message:")
            if st.button("Broadcast Notice", use_container_width=True):
                if n_msg:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO notices (course_stream, message, posted_at) VALUES (?, ?, ?)",
                              (n_stream, n_msg, str(date.today())))
                    conn.commit()
                    conn.close()
                    st.success("Notice broadcasted successfully!")

    # ----------------- STUDENT INTERFACE -----------------
    else:
        st.markdown(f"""
            <div class="main-header">
                <h1>HM UMER CHOUDHARY STUDENT WORKSPACE</h1>
                <p>Course Stream: {st.session_state.course_stream} | Roll Number: {st.session_state.username}</p>
            </div>
        """, unsafe_allow_html=True)

        if menu_choice == "📈 My Performance & Overview":
            conn = sqlite3.connect(DB_FILE)
            my_tests = pd.read_sql_query(
                "SELECT t.title, r.score, r.total, r.submitted_at FROM student_test_results r JOIN mock_tests t ON r.test_id = t.id WHERE r.crn = ?",
                conn, params=(st.session_state.username,)
            )
            my_att = pd.read_sql_query("SELECT COUNT(*) as c FROM student_attendance WHERE crn = ?", conn, params=(st.session_state.username,)).iloc[0]['c']
            conn.close()

            if not my_tests.empty:
                tot_score = my_tests['score'].sum()
                tot_max = my_tests['total'].sum()
                overall_avg = round((tot_score / tot_max) * 100, 1)
            else:
                overall_avg = 0.0

            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><h3>{overall_avg}%</h3><p>Cumulative Assessment Average</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><h3>{len(my_tests)}</h3><p>Tests Completed</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><h3>{my_att}</h3><p>Classes Attended</p></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            if not my_tests.empty:
                st.subheader("📊 Test History & Progress")
                my_tests['Percentage'] = (my_tests['score'] / my_tests['total']) * 100
                st.bar_chart(my_tests.set_index('title')[['Percentage']], color="#1E3A8A")
                st.dataframe(my_tests, use_container_width=True)
            else:
                st.info("You haven't attempted any tests yet. Head over to 'Take Timed Quiz / Test' to start practicing!")

        elif menu_choice == "⏱️ Take Timed Quiz / Test":
            st.subheader("⏱️ Timed Evaluation Tests (AI & Faculty Mock Tests)")
            
            conn = sqlite3.connect(DB_FILE)
            avail_tests = pd.read_sql_query(
                "SELECT id, subject, title, duration_minutes, total_marks FROM mock_tests WHERE course_stream = ?",
                conn, params=(st.session_state.course_stream,)
            )
            conn.close()

            if not avail_tests.empty:
                if not st.session_state.test_active and not st.session_state.test_submitted:
                    chosen_t = st.selectbox("Select Test to Attempt:", [f"{r['id']} - {r['title']} ({r['subject']}) | Time: {r['duration_minutes']} Mins" for _, r in avail_tests.iterrows()])
                    selected_tid = int(chosen_t.split(" - ")[0])
                    
                    if st.button("🚀 Start Timed Test", use_container_width=True):
                        st.session_state.test_active = True
                        st.session_state.current_test_id = selected_tid
                        st.session_state.test_start_time = time.time()
                        st.session_state.test_submitted = False
                        st.rerun()

                elif st.session_state.test_active:
                    tid = st.session_state.current_test_id
                    conn = sqlite3.connect(DB_FILE)
                    t_meta = pd.read_sql_query("SELECT title, subject, duration_minutes, total_marks FROM mock_tests WHERE id = ?", conn, params=(tid,)).iloc[0]
                    questions = pd.read_sql_query("SELECT id, question, opt_a, opt_b, opt_c, opt_d FROM test_questions WHERE test_id = ?", conn, params=(tid,))
                    conn.close()

                    elapsed_time = int(time.time() - st.session_state.test_start_time)
                    total_seconds = t_meta['duration_minutes'] * 60
                    remaining_seconds = max(0, total_seconds - elapsed_time)
                    mins, secs = divmod(remaining_seconds, 60)

                    st.warning(f"⏳ **Time Remaining:** `{mins:02d}:{secs:02d}` | Total Duration: {t_meta['duration_minutes']} Minutes")

                    if remaining_seconds == 0:
                        st.error("⚠️ Time is up! Submitting your test automatically...")

                    with st.form("exam_sheet"):
                        user_answers = {}
                        for idx, q in questions.iterrows():
                            st.markdown(f"**Q{idx+1}: {q['question']}**")
                            opts = [f"A) {q['opt_a']}", f"B) {q['opt_b']}", f"C) {q['opt_c']}", f"D) {q['opt_d']}"]
                            user_answers[q['id']] = st.radio(f"Select your answer for Q{idx+1}:", opts, key=f"ans_{q['id']}")
                            st.markdown("---")

                        btn_submit_exam = st.form_submit_button("Submit Assessment Now")
                        if btn_submit_exam or remaining_seconds == 0:
                            conn = sqlite3.connect(DB_FILE)
                            sol_df = pd.read_sql_query("SELECT id, correct_opt, exp_en, exp_ur FROM test_questions WHERE test_id = ?", conn, params=(tid,))
                            
                            score = 0
                            total_q = len(sol_df)
                            for _, s in sol_df.iterrows():
                                selected = user_answers.get(s['id'], "")
                                if selected.startswith(s['correct_opt']):
                                    score += 1

                            scaled_score = int((score / total_q) * t_meta['total_marks']) if total_q > 0 else 0
                            
                            c = conn.cursor()
                            c.execute("INSERT INTO student_test_results (crn, test_id, score, total, submitted_at) VALUES (?, ?, ?, ?, ?)",
                                      (st.session_state.username, tid, scaled_score, t_meta['total_marks'], str(datetime.now().strftime("%Y-%m-%d %H:%M"))))
                            conn.commit()
                            conn.close()

                            st.session_state.test_active = False
                            st.session_state.test_submitted = True
                            st.session_state.last_submission = {
                                "tid": tid,
                                "score": scaled_score,
                                "total": t_meta['total_marks'],
                                "user_answers": user_answers
                            }
                            st.rerun()

                elif st.session_state.test_submitted:
                    sub = st.session_state.last_submission
                    st.success(f"🎉 Test Finished! You Scored: **{sub['score']} / {sub['total']} Marks**")
                    st.markdown("### 📖 Detailed Solutions & Explanations (English & اردو)")

                    conn = sqlite3.connect(DB_FILE)
                    sol_details = pd.read_sql_query("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur FROM test_questions WHERE test_id = ?", conn, params=(sub['tid'],))
                    conn.close()

                    for idx, s in sol_details.iterrows():
                        u_pick = sub['user_answers'].get(s['id'], "Not Answered")
                        is_correct = u_pick.startswith(s['correct_opt'])
                        badge = "✅ Correct" if is_correct else "❌ Incorrect"
                        
                        st.markdown(f"**Q{idx+1}: {s['question']}** ({badge})")
                        st.write(f"Your Choice: `{u_pick}` | Correct Key: **Option {s['correct_opt']}**")
                        
                        st.markdown(f"""
                            <div class="solution-box">
                                <p><strong>💡 English Explanation:</strong> {s['exp_en'] if s['exp_en'] else 'Standard accounting principle applied.'}</p>
                                <p><strong>اردو تشریح:</strong> {s['exp_ur'] if s['exp_ur'] else 'اس سوال کے مطابق مطلوبہ اصول لاگو ہوتا ہے۔'}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown("---")

                    if st.button("Close and Return to Menu"):
                        st.session_state.test_submitted = False
                        st.session_state.last_submission = {}
                        st.rerun()
            else:
                st.info(f"No mock tests are currently scheduled for **{st.session_state.course_stream}**.")

        elif menu_choice == "📚 My Study Materials":
            st.subheader(f"📚 Course Study Texts & Notes ({st.session_state.course_stream})")
            conn = sqlite3.connect(DB_FILE)
            materials = pd.read_sql_query("SELECT subject, title, file_path, uploaded_at FROM study_materials WHERE course_stream = ?",
                                         conn, params=(st.session_state.course_stream,))
            conn.close()

            if not materials.empty:
                for _, m in materials.iterrows():
                    st.markdown(f"#### 📖 {m['title']}")
                    st.caption(f"Subject: **{m['subject']}** | Uploaded: {m['uploaded_at']}")
                    if os.path.exists(m['file_path']):
                        with open(m['file_path'], "rb") as f_data:
                            st.download_button(
                                label="📥 Download Material",
                                data=f_data,
                                file_name=os.path.basename(m['file_path']),
                                key=f"mat_{m['file_path']}"
                            )
                    st.markdown("---")
            else:
                st.info("No study notes or books uploaded for your course yet.")

        elif menu_choice == "🎥 My Video Lectures":
            st.subheader(f"🎥 Video Lectures Hub ({st.session_state.course_stream})")
            conn = sqlite3.connect(DB_FILE)
            videos = pd.read_sql_query("SELECT subject, title, video_url, added_at FROM video_lectures WHERE course_stream = ?",
                                      conn, params=(st.session_state.course_stream,))
            conn.close()

            if not videos.empty:
                for _, v in videos.iterrows():
                    st.markdown(f"#### 🎬 {v['title']}")
                    st.caption(f"Subject: **{v['subject']}** | Added Date: {v['added_at']}")
                    st.video(v['video_url'])
                    st.markdown("---")
            else:
                st.info("No video lectures published yet.")

        elif menu_choice == "🛡️ Mark My Attendance":
            st.subheader("🛡️ Mark Class Attendance")
            with st.form("att_verify_box"):
                st_pin = st.text_input("Enter 4-Digit Session PIN:", max_chars=4)
                btn_mark_att = st.form_submit_button("Verify & Mark Present", use_container_width=True)

                if btn_mark_att:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT session_id, subject FROM attendance_sessions WHERE course_stream = ? AND pin = ? AND session_date = ? AND status = 'OPEN'",
                              (st.session_state.course_stream, st_pin, str(date.today())))
                    valid_sess = c.fetchone()

                    if valid_sess:
                        sess_id = valid_sess[0]
                        c.execute("SELECT id FROM student_attendance WHERE session_id = ? AND crn = ?", (sess_id, st.session_state.username))
                        already_marked = c.fetchone()
                        
                        if already_marked:
                            st.warning("You have already marked your attendance for this session.")
                        else:
                            c.execute("INSERT INTO student_attendance (session_id, crn, marked_at) VALUES (?, ?, ?)",
                                      (sess_id, st.session_state.username, str(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))))
                            conn.commit()
                            st.success(f"Attendance verified! You are marked PRESENT for {valid_sess[1]}.")
                    else:
                        st.error("Invalid PIN or no active attendance session found for today.")
                    conn.close()

        elif menu_choice == "📄 Academic Report Card":
            st.subheader("📄 Official Academic Transcript")
            conn = sqlite3.connect(DB_FILE)
            st_tests = pd.read_sql_query(
                "SELECT t.title as 'Assessment Title', r.score as 'Marks Obtained', r.total as 'Maximum Marks', r.submitted_at as 'Date Attempted' FROM student_test_results r JOIN mock_tests t ON r.test_id = t.id WHERE r.crn = ?",
                conn, params=(st.session_state.username,)
            )
            my_att = pd.read_sql_query("SELECT COUNT(*) as c FROM student_attendance WHERE crn = ?", conn, params=(st.session_state.username,)).iloc[0]['c']
            conn.close()

            if not st_tests.empty:
                tot_o = st_tests['Marks Obtained'].sum()
                tot_m = st_tests['Maximum Marks'].sum()
                agg_pct = round((tot_o / tot_m) * 100, 1)
            else:
                agg_pct = 0.0

            out_rep = io.BytesIO()
            with pd.ExcelWriter(out_rep, engine='openpyxl') as writer:
                summary_data = {
                    "Field": ["Student Name", "CRN", "Enrolled Stream", "Tests Attempted", "Aggregate Score", "Sessions Attended", "Transcript Date"],
                    "Value": [st.session_state.full_name, st.session_state.username, st.session_state.course_stream, len(st_tests), f"{agg_pct}%", my_att, str(date.today())]
                }
                pd.DataFrame(summary_data).to_excel(writer, index=False, sheet_name="Student Summary")
                if not st_tests.empty:
                    st_tests.to_excel(writer, index=False, sheet_name="Test Results")

            st.download_button(
                label="📥 Download Official Report Card (Excel)",
                data=out_rep.getvalue(),
                file_name=f"ReportCard_{st.session_state.username}_{date.today()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            st.table(st_tests)
