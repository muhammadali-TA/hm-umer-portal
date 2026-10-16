import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import io
import time
import uuid
import re
from datetime import date, datetime
from pypdf import PdfReader

# ----------------- PAGE CONFIGURATION & STYLING -----------------
st.set_page_config(
    page_title="HM Umer Ch. Learning Portal",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .status-banner {
        background: linear-gradient(135deg, #1E3A8A 0%, #0F172A 100%);
        color: white;
        padding: 16px 20px;
        border-radius: 8px;
        margin-bottom: 20px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    .status-banner h2 {
        margin: 0;
        font-size: 1.6rem;
        color: #F8FAFC;
    }
    .status-banner p {
        margin: 5px 0 0 0;
        color: #93C5FD;
        font-size: 0.95rem;
    }
    .metric-card {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 15px;
        text-align: center;
        border-top: 4px solid #1E3A8A;
    }
    .metric-card h3 {
        margin: 0;
        color: #1E3A8A;
        font-size: 1.8rem;
    }
    .metric-card p {
        margin: 4px 0 0 0;
        color: #64748B;
        font-size: 0.85rem;
        font-weight: 600;
    }
    .solution-box {
        background-color: #F8FAFC;
        border-left: 4px solid #2563EB;
        padding: 12px 16px;
        border-radius: 6px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# ----------------- CONSTANTS & DATABASE SETUP -----------------
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

TEACHER_KEY = "HMUMER786"
DB_FILE = "hm_umer_portal.db"
UPLOAD_DIR = "academy_content"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Exact Subjects from handwritten spec
COURSES = [
    "PRC-1 Fundamental of Accounting",
    "CAF-1 Financial Accounting & Reporting 1",
    "F3 Financial Accounting (ACCA)"
]

CONTENT_TYPES = ["Book", "Notes", "Slides", "MCQ", "Test", "Solution"]

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        username TEXT PRIMARY KEY,
        password TEXT,
        full_name TEXT,
        role TEXT,
        course_stream TEXT,
        active_token TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS portal_materials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        content_type TEXT,
        title TEXT,
        file_path TEXT,
        uploaded_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS mock_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS student_results (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        course_stream TEXT,
        test_id INTEGER,
        score INTEGER,
        total INTEGER,
        submitted_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS discussions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        course_stream TEXT,
        sender_name TEXT,
        sender_role TEXT,
        message TEXT,
        created_at TEXT
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS announcements (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        updated_at TEXT
    )''')
    
    # Default Teacher Account
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                  ("admin", hash_password("admin123"), "HM Umer Choudhary", "Teacher", "All", ""))
        
    c.execute("SELECT * FROM announcements")
    if not c.fetchone():
        c.execute("INSERT INTO announcements (message, updated_at) VALUES (?, ?)",
                  ("Welcome to HM UMER Ch. Portal. Tests and lectures updated daily.", str(date.today())))
        
    conn.commit()
    conn.close()

init_db()

# ----------------- AI QUIZ GENERATOR HELPER -----------------
def extract_pdf_pages(pdf_file, start_p, end_p):
    reader = PdfReader(pdf_file)
    total_len = len(reader.pages)
    s_idx = max(0, start_p - 1)
    e_idx = min(total_len, end_p)
    text = ""
    for idx in range(s_idx, e_idx):
        extracted = reader.pages[idx].extract_text()
        if extracted:
            text += extracted + "\n"
    return text.strip(), total_len

def generate_ai_mcqs(text_passage, num_q, topic):
    sentences = [s.strip() for s in re.split(r'[\.\n\r]+', text_passage) if len(s.strip()) > 35]
    mcqs = []
    distractors = [
        "Direct charge to retained earnings",
        "Fair value through profit and loss valuation",
        "Discretionary adjustment at balance sheet date",
        "Deferred realization method over contract period",
        "Historical cost without subsequent impairment"
    ]
    
    if not sentences:
        for i in range(num_q):
            mcqs.append({
                "q": f"Q{i+1}: What is the fundamental compliance rule for {topic}?",
                "a": "Faithful representation in accordance with applicable framework",
                "b": "Discretionary recognition without documentation",
                "c": "Cash-basis realization only",
                "d": "Complete write-off upon purchase",
                "correct": "A",
                "exp_en": f"Under IAS/IFRS and statutory standards for {topic}, transactions must ensure faithful representation.",
                "exp_ur": f"{topic} کے اصولوں کے تحت تمام لین دین کی شفاف اور درست فریم ورک کے تحت نمائندگی لازمی ہے۔"
            })
        return mcqs

    step = max(1, len(sentences) // num_q)
    sample = sentences[0::step][:num_q]
    
    for idx, s in enumerate(sample):
        words = s.split()
        if len(words) >= 6:
            mid = len(words) // 2
            target = words[mid].strip(",.()\"';:")
            if len(target) < 4:
                target = words[mid - 1].strip(",.()\"';:")
            prompt = s.replace(target, "_______")
            dist = [d for d in distractors if d != target][:3]
            
            mcqs.append({
                "q": f"Q{idx+1} ({topic}): Complete the official statement: \"{prompt}\"",
                "a": target,
                "b": dist[0] if len(dist) > 0 else "Accrued cost liability",
                "c": dist[1] if len(dist) > 1 else "Non-operating provision",
                "d": dist[2] if len(dist) > 2 else "Unrealized capital gain",
                "correct": "A",
                "exp_en": f"Official Book Text: \"{s}\". The missing keyword is '{target}'.",
                "exp_ur": f"کتابی متن کے مطابق اصل جملہ تھا: \"{s}\"۔ اس اصول کی درست وضاحت کے لیے درست لفظ '{target}' ہے۔"
            })
            
    while len(mcqs) < num_q:
        i = len(mcqs) + 1
        mcqs.append({
            "q": f"Q{i}: How must transactions under {topic} be measured?",
            "a": "In line with substance over form and relevant IFRS",
            "b": "Arbitrary estimation by internal staff",
            "c": "Postponed indefinitely without disclosure",
            "d": "Only when approved by tax authority",
            "correct": "A",
            "exp_en": "Standard requires substance over form and adherence to relevant financial reporting standards.",
            "exp_ur": "اکاؤنٹنگ کا بنیادی اصول ہے کہ لین دین کو ظاہری شکل کے بجائے ان کی اصل حقیقت کے مطابق لکھا جائے۔"
        })
    return mcqs

# ----------------- SESSION STATE -----------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.full_name = ""
    st.session_state.role = ""
    st.session_state.course_stream = ""
    st.session_state.token = ""

if "test_active" not in st.session_state:
    st.session_state.test_active = False
    st.session_state.current_test_id = None
    st.session_state.test_start_time = None
    st.session_state.test_submitted = False
    st.session_state.last_submission = {}

# ----------------- ANNOUNCEMENT BANNER -----------------
def render_header_banner():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT message FROM announcements ORDER BY id DESC LIMIT 1")
    ann = c.fetchone()
    conn.close()
    msg = ann[0] if ann else "No current updates."
    
    st.markdown(f"""
        <div class="status-banner">
            <h2>HM UMER ch. Status / Announcement</h2>
            <p>📢 {msg}</p>
        </div>
    """, unsafe_allow_html=True)

# ----------------- AUTHENTICATION (NO DATA LEAK) -----------------
if not st.session_state.logged_in:
    render_header_banner()
    c1, c2, c3 = st.columns([1, 2, 1])
    with c2:
        auth_action = st.radio("Choose Portal Access:", ["Sign In", "Student Sign Up", "Teacher Sign Up"], horizontal=True)

        if auth_action == "Sign In":
            st.markdown("### 🔐 Secure Sign In")
            with st.form("signin_box"):
                u_in = st.text_input("Username / CRN:")
                p_in = st.text_input("Password:", type="password")
                btn_sub = st.form_submit_button("Sign In", use_container_width=True)

                if btn_sub:
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("SELECT username, full_name, role, course_stream, active_token FROM users WHERE username = ? AND password = ?",
                              (u_in, hash_password(p_in)))
                    user = c.fetchone()

                    if user:
                        # 1 Person 1 Device Security Token
                        new_device_token = str(uuid.uuid4())
                        c.execute("UPDATE users SET active_token = ? WHERE username = ?", (new_device_token, user[0]))
                        conn.commit()
                        conn.close()

                        st.session_state.logged_in = True
                        st.session_state.username = user[0]
                        st.session_state.full_name = user[1]
                        st.session_state.role = user[2]
                        st.session_state.course_stream = user[3]
                        st.session_state.token = new_device_token
                        st.success(f"Welcome {user[1]}!")
                        st.rerun()
                    else:
                        conn.close()
                        st.error("Invalid credentials entered.")
            st.info("💡 Default Faculty Login: `admin` | Password: `admin123`")

        elif auth_action == "Student Sign Up":
            st.markdown("### 👨‍🎓 Student Registration")
            st.caption("🔒 Security Enforcement: Minimum 8-character password. 1 Person can use only 1 Device.")
            with st.form("st_signup"):
                s_crn = st.text_input("Student CRN / Roll Number (Used as Login):")
                s_name = st.text_input("Full Name:")
                s_course = st.selectbox("Select Your Course:", COURSES)
                s_pwd1 = st.text_input("Create Password (Min 8 characters):", type="password")
                s_pwd2 = st.text_input("Confirm Password:", type="password")
                btn_st_reg = st.form_submit_button("Register Student", use_container_width=True)

                if btn_st_reg:
                    if len(s_pwd1) < 8:
                        st.error("Security Violation: Password must be at least 8 characters long.")
                    elif s_pwd1 != s_pwd2:
                        st.error("Passwords do not match.")
                    elif not s_crn or not s_name:
                        st.warning("Please fill all fields.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (s_crn,))
                        if c.fetchone():
                            st.error("This Roll No/CRN is already registered.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                                      (s_crn, hash_password(s_pwd1), s_name, "Student", s_course, ""))
                            conn.commit()
                            conn.close()
                            st.success("Registration complete! You can now Sign In.")

        elif auth_action == "Teacher Sign Up":
            st.markdown("### 👨‍🏫 Teacher Registration")
            st.caption("🔒 Protected by Teacher Security Key.")
            with st.form("t_signup"):
                t_sec = st.text_input("Teacher Authorization Key:", type="password")
                t_user = st.text_input("Preferred Username:")
                t_name = st.text_input("Full Name:", value="HM Umer Choudhary")
                t_pwd1 = st.text_input("Create Password (Min 8 characters):", type="password")
                t_pwd2 = st.text_input("Confirm Password:", type="password")
                btn_t_reg = st.form_submit_button("Create Teacher Account", use_container_width=True)

                if btn_t_reg:
                    if t_sec != TEACHER_KEY:
                        st.error("Unauthorized: Invalid Teacher Authorization Key.")
                    elif len(t_pwd1) < 8:
                        st.error("Security Violation: Password must be at least 8 characters.")
                    elif t_pwd1 != t_pwd2:
                        st.error("Passwords do not match.")
                    else:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("SELECT username FROM users WHERE username = ?", (t_user,))
                        if c.fetchone():
                            st.error("Username already taken.")
                            conn.close()
                        else:
                            c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                                      (t_user, hash_password(t_pwd1), t_name, "Teacher", "All", ""))
                            conn.commit()
                            conn.close()
                            st.success("Teacher account created! Please Sign In.")

# ----------------- AUTHENTICATED USER CONSOLE -----------------
else:
    # Verify Single Device Active Session Token
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT active_token FROM users WHERE username = ?", (st.session_state.username,))
    db_token = c.fetchone()
    conn.close()
    
    if db_token and db_token[0] != "" and db_token[0] != st.session_state.token:
        st.session_state.logged_in = False
        st.error("Security Alert: Your account was accessed from another device. Logged out automatically.")
        st.rerun()

    render_header_banner()

    # Sidebar
    with st.sidebar:
        st.markdown(f"### 👤 **{st.session_state.full_name}**")
        st.caption(f"Role: **{st.session_state.role}**")
        if st.session_state.role == "Student":
            st.info(f"Enrolled Course:\n**{st.session_state.course_stream}**")
        st.divider()

        if st.session_state.role == "Teacher":
            menu = st.radio("Teacher Management:", [
                "📊 Overview & Quick Stats",
                "📤 Upload & Change Material",
                "🤖 AI Book Quiz Generator",
                "📢 Update Announcement",
                "👨‍🎓 Registered Students & Reports"
            ])
        else:
            menu = st.radio("Student Portal:", [
                "📚 My Course Material (7-Pillars)",
                "⏱️ Take Timed Quiz & Test",
                "📄 My Saved Reports & Grades"
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

    # ----------------- TEACHER VIEW (FULL CONTROL) -----------------
    if st.session_state.role == "Teacher":

        if menu == "📊 Overview & Quick Stats":
            conn = sqlite3.connect(DB_FILE)
            st_count = pd.read_sql_query("SELECT COUNT(*) as c FROM users WHERE role = 'Student'", conn).iloc[0]['c']
            mat_count = pd.read_sql_query("SELECT COUNT(*) as c FROM portal_materials", conn).iloc[0]['c']
            test_count = pd.read_sql_query("SELECT COUNT(*) as c FROM mock_tests", conn).iloc[0]['c']
            conn.close()

            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><h3>{st_count}</h3><p>Enrolled Students</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><h3>{mat_count}</h3><p>Published Materials</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><h3>{test_count}</h3><p>Active Tests</p></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Student Distribution by Course")
            conn = sqlite3.connect(DB_FILE)
            dist = pd.read_sql_query("SELECT course_stream as 'Course', COUNT(*) as 'Students' FROM users WHERE role = 'Student' GROUP BY course_stream", conn)
            conn.close()
            st.table(dist if not dist.empty else pd.DataFrame({"Course": COURSES, "Students": [0, 0, 0]}))

        elif menu == "📤 Upload & Change Material":
            st.subheader("📤 Teacher Upload & Manage Material")
            st.caption("Upload relevant books, notes, slides, MCQs, tests, and solutions.")

            with st.form("upload_mat_form"):
                sel_course = st.selectbox("Target Course:", COURSES)
                sel_type = st.selectbox("Content Category:", CONTENT_TYPES)
                mat_title = st.text_input("Material Title (e.g., Chapter 1 Comprehensive Notes):")
                mat_file = st.file_uploader("Select File (PDF, DOCX, PPTX):", type=["pdf", "docx", "pptx"])
                btn_up = st.form_submit_button("Upload Material")

                if btn_up and mat_title and mat_file:
                    safe_name = f"[{sel_type}]_{mat_file.name}"
                    save_path = os.path.join(UPLOAD_DIR, safe_name)
                    with open(save_path, "wb") as f:
                        f.write(mat_file.getbuffer())

                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO portal_materials (course_stream, content_type, title, file_path, uploaded_at) VALUES (?, ?, ?, ?, ?)",
                              (sel_course, sel_type, mat_title, save_path, str(date.today())))
                    conn.commit()
                    conn.close()
                    st.success(f"{sel_type} '{mat_title}' uploaded for {sel_course}!")

            st.markdown("---")
            st.subheader("Manage & Delete Existing Materials")
            conn = sqlite3.connect(DB_FILE)
            all_mats = pd.read_sql_query("SELECT id, course_stream, content_type, title, uploaded_at FROM portal_materials ORDER BY id DESC", conn)
            conn.close()
            if not all_mats.empty:
                st.dataframe(all_mats, use_container_width=True)
                del_id = st.number_input("Enter Material ID to remove:", min_value=1, step=1)
                if st.button("Delete Selected Material"):
                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("DELETE FROM portal_materials WHERE id = ?", (del_id,))
                    conn.commit()
                    conn.close()
                    st.success(f"Material #{del_id} removed successfully.")
                    st.rerun()
            else:
                st.info("No materials published yet.")

        elif menu == "🤖 AI Book Quiz Generator":
            st.subheader("🤖 Upload Book PDF & AI Self-Made Quiz Generator")
            st.write("Upload any textbook PDF, set the page range, and let the AI generate a timed MCQ test with Urdu and English explanations.")

            with st.form("ai_book_quiz_form"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    ai_c = st.selectbox("Select Target Course:", COURSES)
                    ai_title = st.text_input("Quiz Title (e.g., IAS 16 Revaluation Test):")
                with col_a2:
                    pdf_input = st.file_uploader("Upload Book PDF:", type=["pdf"])
                    col_p1, col_p2, col_p3 = st.columns(3)
                    sp = col_p1.number_input("Start Page:", min_value=1, value=1)
                    ep = col_p2.number_input("End Page:", min_value=1, value=5)
                    nq = col_p3.number_input("No. of Questions:", min_value=1, max_value=25, value=5)

                col_t1, col_t2 = st.columns(2)
                t_timer = col_t1.number_input("Timer (Minutes):", min_value=5, max_value=180, value=15)
                t_marks = col_t2.number_input("Total Marks:", min_value=5, max_value=100, value=15)

                btn_gen = st.form_submit_button("⚡ AI Generate & Publish Timed Quiz", use_container_width=True)

                if btn_gen:
                    if not pdf_input or not ai_title:
                        st.error("Please provide both the PDF file and Quiz Title.")
                    elif sp > ep:
                        st.error("Start Page cannot be greater than End Page.")
                    else:
                        with st.spinner("Extracting text and generating AI MCQs..."):
                            extracted_txt, total_pages = extract_pdf_pages(pdf_input, int(sp), int(ep))
                            if not extracted_txt:
                                st.warning("No readable text found on those pages. Please ensure the PDF is text-based.")
                            else:
                                mcqs = generate_ai_mcqs(extracted_txt, int(nq), ai_title)
                                conn = sqlite3.connect(DB_FILE)
                                c = conn.cursor()
                                c.execute("INSERT INTO mock_tests (course_stream, title, duration_minutes, total_marks, created_at) VALUES (?, ?, ?, ?, ?)",
                                          (ai_c, f"[AI] {ai_title}", t_timer, t_marks, str(date.today())))
                                new_tid = c.lastrowid
                                for m in mcqs:
                                    c.execute("INSERT INTO test_questions (test_id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                              (new_tid, m['q'], m['a'], m['b'], m['c'], m['d'], m['correct'], m['exp_en'], m['exp_ur']))
                                conn.commit()
                                conn.close()
                                st.success(f"Generated {len(mcqs)} questions for {ai_c} from pages {sp}-{ep}! Live for enrolled students.")

        elif menu == "📢 Update Announcement":
            st.subheader("📢 Update Top Status / Announcement")
            with st.form("ann_form"):
                new_msg = st.text_area("Write Announcement for Students:")
                if st.form_submit_button("Update Status"):
                    if new_msg:
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("INSERT INTO announcements (message, updated_at) VALUES (?, ?)", (new_msg, str(date.today())))
                        conn.commit()
                        conn.close()
                        st.success("Announcement updated!")
                        st
