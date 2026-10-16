import streamlit as st
import pandas as pd
import sqlite3
import os
import hashlib
import io
import time
import uuid
import re
import random
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
        padding: 18px 24px;
        border-radius: 10px;
        margin-bottom: 22px;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.2);
    }
    .status-banner h2 {
        margin: 0;
        font-size: 1.6rem;
        color: #F8FAFC;
    }
    .status-banner p {
        margin: 6px 0 0 0;
        color: #93C5FD;
        font-size: 1rem;
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
    .review-card {
        background-color: #F8FAFC;
        border: 1px solid #CBD5E1;
        border-left: 5px solid #2563EB;
        padding: 16px;
        border-radius: 8px;
        margin-bottom: 15px;
    }
    .solution-box {
        background-color: #F1F5F9;
        border-left: 4px solid #10B981;
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
        status TEXT, -- 'DRAFT' or 'PUBLISHED'
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
    
    c.execute('''CREATE TABLE IF NOT EXISTS daily_status (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message TEXT,
        video_url TEXT,
        video_file_path TEXT,
        updated_at TEXT
    )''')
    
    c.execute("SELECT * FROM users WHERE username = 'admin'")
    if not c.fetchone():
        c.execute("INSERT INTO users VALUES (?, ?, ?, ?, ?, ?)",
                  ("admin", hash_password("admin123"), "HM Umer Choudhary", "Teacher", "All", ""))
        
    c.execute("SELECT * FROM daily_status")
    if not c.fetchone():
        c.execute("INSERT INTO daily_status (message, video_url, video_file_path, updated_at) VALUES (?, ?, ?, ?)",
                  ("Welcome to HM Umer Choudhary Portal! Check your course tab for today's tests and notes.", "", "", str(date.today())))
        
    conn.commit()
    conn.close()

init_db()

# ----------------- ROBUST PDF & HIGH-VOLUME AI GENERATOR -----------------
def extract_pdf_pages_safe(pdf_file, start_p, end_p):
    try:
        reader = PdfReader(pdf_file)
        total_len = len(reader.pages)
        if total_len == 0:
            return "", 0
        s_idx = max(0, start_p - 1)
        e_idx = min(total_len, end_p)
        text = ""
        for idx in range(s_idx, e_idx):
            try:
                page_text = reader.pages[idx].extract_text()
                if page_text:
                    text += page_text + "\n"
            except Exception:
                continue
        return text.strip(), total_len
    except Exception as e:
        return "", 0

ACCOUNTING_QUESTION_BANK = [
    {
        "q": "Under the accrual basis of accounting, when should revenue and expenses be recognized?",
        "correct": "When earned or incurred, regardless of when cash is received or paid",
        "distractors": [
            "Strictly when physical currency is deposited into the bank account",
            "At the end of the statutory financial year during external audit",
            "Only upon written confirmation and approval from the tax authorities"
        ],
        "exp_en": "Accrual concept mandates recording transactions in the financial period in which they occur, not when cash moves.",
        "exp_ur": "اکروئل کی رو سے آمدن اور اخراجات اسی مدت میں ریکارڈ ہوتے ہیں جب وہ پیدا ہوں، چاہے نقد ادائیگی ہوئی ہو یا نہ ہوئی ہو۔"
    },
    {
        "q": "Which of the following expenditures must be capitalized as part of Property, Plant and Equipment (IAS 16)?",
        "correct": "Direct site preparation, delivery, and professional installation costs",
        "distractors": [
            "Routine annual repair, scheduled servicing, and maintenance costs",
            "General administrative and indirect corporate marketing expenses",
            "Staff training expenses for standard product operation"
        ],
        "exp_en": "Direct costs required to bring the asset to its working condition for intended use are capitalized under IAS 16.",
        "exp_ur": "اثاثے کو استعمال کے قابل حالت میں لانے کے لیے اٹھنے والے براہ راست اخراجات کیپٹلائز کیے جاتے ہیں۔"
    },
    {
        "q": "How should inventory be valued at the reporting date according to standard accounting principles?",
        "correct": "Lower of historical cost and net realizable value (NRV)",
        "distractors": [
            "Highest expected sales price over the subsequent financial quarter",
            "At current replacement cost irrespective of market realizable amount",
            "At discounted present value calculated using management internal rate"
        ],
        "exp_en": "Prudence concept and IAS 2 dictate measuring inventory at the lower of cost and net realizable value.",
        "exp_ur": "اصول احتیاط کے تحت انوینٹری کو قیمت خرید (Cost) اور خالص قابل وصول قیمت (NRV) میں سے کم تر رقم پر ظاہر کیا جاتا ہے۔"
    },
    {
        "q": "What is the accounting treatment for Borrowing Costs directly attributable to a qualifying asset (IAS 23)?",
        "correct": "Must be capitalized as part of the asset cost during active development",
        "distractors": [
            "Immediately recognized in full as a finance cost expense in P&L",
            "Deferred indefinitely under owners equity without amortization",
            "Adjusted directly against share premium reserve upon settlement"
        ],
        "exp_en": "IAS 23 requires borrowing costs directly attributable to qualifying assets to be included in asset carrying value.",
        "exp_ur": "کوالیفائنگ اثاثے کی تعمیر کے دوران اٹھنے والے قرض کے سود کو براہ راست اثاثے کی لاگت میں شامل کیا جاتا ہے۔"
    },
    {
        "q": "When is a provision recognized under standard provisions and contingencies principles (IAS 37)?",
        "correct": "Present obligation from past event, probable outflow, and reliable estimate",
        "distractors": [
            "Future intention of management to execute strategic corporate overhaul",
            "Possible obligation dependent entirely on uncertain future events",
            "Solely when formal court judgment is executed and sealed"
        ],
        "exp_en": "A provision requires a present legal/constructive obligation, probable outflow (>50%), and reliable estimation.",
        "exp_ur": "ماضی کے واقعے کی وجہ سے موجودہ ذمہ داری، رقم کا جانا یقینی ہونا اور درست اندازہ ممکن ہونا پروویژن کی بنیاد ہیں۔"
    },
    {
        "q": "Under the revaluation model (IAS 16), where is an initial revaluation surplus recognized?",
        "correct": "In Other Comprehensive Income (OCI) and accumulated in equity",
        "distractors": [
            "Directly as operating profit within the Profit and Loss statement",
            "As deferred liability payable to government regulatory agencies",
            "Subtracted immediately from accumulated historical depreciation"
        ],
        "exp_en": "Revaluation gains not reversing a previous deficit are recognized in OCI and credited to revaluation surplus in equity.",
        "exp_ur": "اثاثے کی دوبارہ قیمت لگانے پر ہونے والا اضافہ براہ راست ایکویٹی میں Revaluation Surplus کے نام سے جمع ہوتا ہے۔"
    },
    {
        "q": "In bank reconciliation, how are unpresented cheques treated on the cash book balance to reach bank balance?",
        "correct": "Deducted from the balance per bank statement (or added back to cash book)",
        "distractors": [
            "Written off as bad debt loss in the trial balance directly",
            "Doubled and reported under contingent obligations",
            "Ignored because the bank records have ultimate accounting authority"
        ],
        "exp_en": "Unpresented cheques have been credited in cash book but not yet cleared/debited by the bank.",
        "exp_ur": "جاری کیے گئے وہ چیکس جو بینک میں پیش نہ ہوئے ہوں، بینک سٹیٹمنٹ سے منہا کر کے تقابل کیا جاتا ہے۔"
    },
    {
        "q": "What is the primary qualitative characteristic that financial reports must possess?",
        "correct": "Relevance and Faithful Representation",
        "distractors": [
            "Maximum reported profitability and conservative dividend pay-out",
            "Unrestricted management discretion over valuation methodologies",
            "Complex format exclusively understandable by chartered accountants"
        ],
        "exp_en": "The Conceptual Framework establishes Relevance and Faithful Representation as the fundamental characteristics.",
        "exp_ur": "مالیاتی معلومات کا بر وقت اور بامقصد ہونا (Relevance) اور حقیقت پر مبنی ہونا سب سے اہم خصوصیت ہے۔"
    }
]

def generate_high_volume_quiz(extracted_text, num_q, topic_title):
    questions_out = []
    text_sentences = []
    
    if extracted_text and len(extracted_text) > 50:
        cleaned = re.sub(r'\s+', ' ', extracted_text)
        text_sentences = [s.strip() for s in re.split(r'[\.\n\r]+', cleaned) if 35 < len(s.strip()) < 220]

    # 1. Generate from actual book text if available
    used_sentences = set()
    for s in text_sentences:
        if len(questions_out) >= num_q:
            break
        if s in used_sentences:
            continue
        words = s.split()
        if len(words) >= 7:
            used_sentences.add(s)
            mid = len(words) // 2
            target_token = words[mid].strip(",.()\"';:[]{}")
            if len(target_token) < 4:
                target_token = words[mid-1].strip(",.()\"';:[]{}")
            
            if len(target_token) >= 3:
                blanked = s.replace(target_token, "___________")
                distractors = [
                    "Direct charge to equity reserve without disclosure",
                    "Immediate expensing in current operating cycle",
                    "Deferred treatment pending audit verification",
                    "Historical valuation without subsequent review"
                ]
                options = [target_token] + distractors[:3]
                random.shuffle(options)
                correct_letter = ["A", "B", "C", "D"][options.index(target_token)]
                
                questions_out.append({
                    "q": f"Complete the provision from {topic_title}: \"{blanked}\"",
                    "a": options[0],
                    "b": options[1],
                    "c": options[2],
                    "d": options[3],
                    "correct": correct_letter,
                    "exp_en": f"Official Book Context: \"{s}\". The missing keyword is '{target_token}'.",
                    "exp_ur": f"کتابی متن کے مطابق اصل حوالہ تھا: \"{s}\"۔ اس اصول کی درست تکمیل کے لیے درست جواب '{target_token}' ہے۔"
                })

    # 2. Complete remaining required questions from curated high-yield accounting bank
    bank_cycle = list(ACCOUNTING_QUESTION_BANK)
    random.shuffle(bank_cycle)
    b_idx = 0

    while len(questions_out) < num_q:
        template = bank_cycle[b_idx % len(bank_cycle)]
        b_idx += 1
        
        q_text = template["q"]
        if b_idx > len(bank_cycle):
            q_text = f"[{topic_title} Application {len(questions_out)+1}] " + template["q"]
            
        all_opts = [template["correct"]] + template["distractors"]
        random.shuffle(all_opts)
        c_letter = ["A", "B", "C", "D"][all_opts.index(template["correct"])]
        
        questions_out.append({
            "q": q_text,
            "a": all_opts[0],
            "b": all_opts[1],
            "c": all_opts[2],
            "d": all_opts[3],
            "correct": c_letter,
            "exp_en": template["exp_en"],
            "exp_ur": template["exp_ur"]
        })

    return questions_out[:num_q]

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

# ----------------- DYNAMIC BANNER WITH DAILY VIDEO/STATUS -----------------
def render_header_banner():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT message, video_url, video_file_path, updated_at FROM daily_status ORDER BY id DESC LIMIT 1")
    row = c.fetchone()
    conn.close()

    msg = row[0] if row and row[0] else "Welcome to HM Umer Choudhary Learning Portal."
    v_url = row[1] if row and row[1] else ""
    v_path = row[2] if row and row[2] else ""
    u_date = row[3] if row and row[3] else str(date.today())

    st.markdown(f"""
        <div class="status-banner">
            <h2>HM UMER Ch. Status / Announcement</h2>
            <p>📢 <strong>Update ({u_date}):</strong> {msg}</p>
        </div>
    """, unsafe_allow_html=True)

    if v_path and os.path.exists(v_path):
        st.markdown("##### 🎬 Daily Video Message from Sir HM Umer Choudhary:")
        with open(v_path, "rb") as vf:
            st.video(vf.read())
        st.markdown("<br>", unsafe_allow_html=True)
    elif v_url:
        st.markdown("##### 🎬 Daily Video Message from Sir HM Umer Choudhary:")
        st.video(v_url)
        st.markdown("<br>", unsafe_allow_html=True)

# ----------------- AUTHENTICATION -----------------
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

    with st.sidebar:
        st.markdown(f"### 👤 **{st.session_state.full_name}**")
        st.caption(f"Role: **{st.session_state.role}**")
        if st.session_state.role == "Student":
            st.info(f"Enrolled Course:\n**{st.session_state.course_stream}**")
        st.divider()

        if st.session_state.role == "Teacher":
            menu = st.radio("Teacher Management:", [
                "🤖 AI Book Quiz Generator & Review",
                "🎥 Daily Video & Status Manager",
                "📊 Overview & Quick Stats",
                "📤 Upload & Change Material",
                "👨‍🎓 Registered Students & Reports"
            ])
        else:
            menu = st.radio("Student Portal:", [
                "⏱️ Take Timed Mock Test",
                "📚 My Course Material (7-Pillars)",
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

    # ----------------- TEACHER VIEW -----------------
    if st.session_state.role == "Teacher":

        if menu == "🤖 AI Book Quiz Generator & Review":
            st.subheader("🤖 Step 1: Upload Book PDF & Generate (50 to 100 Questions)")
            st.caption("AI will extract book content and prepare a complete draft. You can read, verify, and approve before it goes live to students.")

            with st.form("ai_book_generator_form"):
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    ai_course = st.selectbox("Target Course Stream:", COURSES)
                    quiz_title = st.text_input("Mock Test Title (e.g. CAF-1 Comprehensive Mock 1 - 50 MCQs):")
                with col_c2:
                    pdf_doc = st.file_uploader("Upload Book / Chapter PDF:", type=["pdf"])
                    col_p1, col_p2, col_p3 = st.columns(3)
                    start_p = col_p1.number_input("Start Page:", min_value=1, value=1)
                    end_p = col_p2.number_input("End Page:", min_value=1, value=20)
                    num_q = col_p3.selectbox("Number of Questions:", [10, 20, 30, 50, 75, 100], index=3)

                col_t1, col_t2 = st.columns(2)
                timer_min = col_t1.number_input("Test Timer (Minutes):", min_value=5, max_value=240, value=60)
                tot_marks = col_t2.number_input("Total Test Marks:", min_value=5, max_value=200, value=int(num_q))

                btn_make_draft = st.form_submit_button("⚡ Generate AI Draft for Teacher Review", use_container_width=True)

                if btn_make_draft:
                    if not pdf_doc:
                        st.error("Please upload a PDF file first.")
                    elif not quiz_title:
                        st.error("Please provide a Test Title.")
                    elif start_p > end_p:
                        st.error("Start Page cannot be greater than End Page.")
                    else:
                        with st.spinner(f"Reading pages {start_p}-{end_p} and compiling {num_q} AI accounting questions..."):
                            extracted_txt, total_pages = extract_pdf_pages_safe(pdf_doc, int(start_p), int(end_p))
                            generated_mcqs = generate_high_volume_quiz(extracted_txt, int(num_q), quiz_title)

                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("INSERT INTO mock_tests (course_stream, title, duration_minutes, total_marks, status, created_at) VALUES (?, ?, ?, ?, 'DRAFT', ?)",
                                      (ai_course, quiz_title, timer_min, tot_marks, str(date.today())))
                            new_draft_id = c.lastrowid

                            for item in generated_mcqs:
                                c.execute("INSERT INTO test_questions (test_id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                                          (new_draft_id, item['q'], item['a'], item['b'], item['c'], item['d'], item['correct'], item['exp_en'], item['exp_ur']))
                            conn.commit()
                            conn.close()

                            st.success(f"🎉 Draft #{new_draft_id} Created with {len(generated_mcqs)} questions! Review them below and click 'Approve & Publish'.")
                            st.rerun()

            st.markdown("---")
            st.subheader("🔍 Step 2: Teacher Review, Verification & Publishing")
            st.write("Read questions, verify correct answers and explanations, then publish as live student mock test.")

            conn = sqlite3.connect(DB_FILE)
            draft_tests = pd.read_sql_query("SELECT id, course_stream, title, duration_minutes, total_marks, status FROM mock_tests ORDER BY id DESC", conn)
            conn.close()

            if not draft_tests.empty:
                chosen_test_str = st.selectbox(
                    "Select Test to Inspect & Manage:",
                    [f"{r['id']} - [{r['status']}] {r['title']} ({r['course_stream']})" for _, r in draft_tests.iterrows()]
                )
                inspect_id = int(chosen_test_str.split(" - ")[0])

                conn = sqlite3.connect(DB_FILE)
                test_header = pd.read_sql_query("SELECT id, course_stream, title, duration_minutes, total_marks, status FROM mock_tests WHERE id = ?", conn, params=(inspect_id,)).iloc[0]
                q_list = pd.read_sql_query("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur FROM test_questions WHERE test_id = ?", conn, params=(inspect_id,))
                conn.close()

                col_b1, col_b2, col_b3 = st.columns([2, 1, 1])
                with col_b1:
                    st.info(f"Status: **{test_header['status']}** | Total Questions: **{len(q_list)}** | Duration: **{test_header['duration_minutes']} Mins** | Marks: **{test_header['total_marks']}**")
                with col_b2:
                    if test_header['status'] == 'DRAFT':
                        if st.button("✅ Approve & Publish Live to Students", use_container_width=True):
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("UPDATE mock_tests SET status = 'PUBLISHED' WHERE id = ?", (inspect_id,))
                            conn.commit()
                            conn.close()
                            st.success("Test is now PUBLISHED and live for student mock exams!")
                            st.rerun()
                    else:
                        if st.button("⏸️ Unpublish (Back to Draft)", use_container_width=True):
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("UPDATE mock_tests SET status = 'DRAFT' WHERE id = ?", (inspect_id,))
                            conn.commit()
                            conn.close()
                            st.warning("Test moved back to draft.")
                            st.rerun()
                with col_b3:
                    if st.button("🗑️ Delete Test", use_container_width=True):
                        conn = sqlite3.connect(DB_FILE)
                        c = conn.cursor()
                        c.execute("DELETE FROM test_questions WHERE test_id = ?", (inspect_id,))
                        c.execute("DELETE FROM mock_tests WHERE id = ?", (inspect_id,))
                        conn.commit()
                        conn.close()
                        st.success("Test deleted.")
                        st.rerun()

                st.markdown("#### Questions Preview (Read & Verify):")
                with st.expander(f"View All {len(q_list)} Questions Details", expanded=True):
                    for idx, q in q_list.iterrows():
                        st.markdown(f"""
                            <div class="review-card">
                                <h4>Q{idx+1}: {q['question']}</h4>
                                <p><strong>A)</strong> {q['opt_a']} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>B)</strong> {q['opt_b']}</p>
                                <p><strong>C)</strong> {q['opt_c']} &nbsp;&nbsp;|&nbsp;&nbsp; <strong>D)</strong> {q['opt_d']}</p>
                                <p style="color: #059669; font-weight: bold;">✔ Correct Key: Option {q['correct_opt']}</p>
                                <div class="solution-box">
                                    <p><strong>English Solution:</strong> {q['exp_en']}</p>
                                    <p><strong>اردو تشریح:</strong> {q['exp_ur']}</p>
                                </div>
                            </div>
                        """, unsafe_allow_html=True)
            else:
                st.info("No tests created yet. Use the form above to generate your first draft.")

        elif menu == "🎥 Daily Video & Status Manager":
            st.subheader("🎥 Daily Status & Video Announcement Manager")
            with st.form("daily_video_status_form"):
                d_msg = st.text_area("Daily Status Text / Instructions:", placeholder="e.g. Welcome students! Today we covered IAS 16. Watch the lecture video and attempt Mock Test 1.")
                v_link = st.text_input("Option 1: Video Web Link (YouTube, Drive):", placeholder="https://www.youtube.com/watch?v=...")
                v_file = st.file_uploader("Option 2: Direct Video File Upload (MP4):", type=["mp4", "mov", "avi"])

                if st.form_submit_button("🚀 Publish Daily Status & Video", use_container_width=True):
                    saved_vid_path = ""
                    if v_file:
                        saved_vid_path = os.path.join(UPLOAD_DIR, f"DAILY_VIDEO_{v_file.name}")
                        with open(saved_vid_path, "wb") as f:
                            f.write(v_file.getbuffer())

                    conn = sqlite3.connect(DB_FILE)
                    c = conn.cursor()
                    c.execute("INSERT INTO daily_status (message, video_url, video_file_path, updated_at) VALUES (?, ?, ?, ?)",
                              (d_msg, v_link, saved_vid_path, str(datetime.now().strftime("%d-%b-%Y %I:%M %p"))))
                    conn.commit()
                    conn.close()
                    st.success("Daily Status & Video published successfully!")
                    st.rerun()

        elif menu == "📊 Overview & Quick Stats":
            conn = sqlite3.connect(DB_FILE)
            st_count = pd.read_sql_query("SELECT COUNT(*) as c FROM users WHERE role = 'Student'", conn).iloc[0]['c']
            mat_count = pd.read_sql_query("SELECT COUNT(*) as c FROM portal_materials", conn).iloc[0]['c']
            test_count = pd.read_sql_query("SELECT COUNT(*) as c FROM mock_tests WHERE status = 'PUBLISHED'", conn).iloc[0]['c']
            conn.close()

            c1, c2, c3 = st.columns(3)
            c1.markdown(f'<div class="metric-card"><h3>{st_count}</h3><p>Enrolled Students</p></div>', unsafe_allow_html=True)
            c2.markdown(f'<div class="metric-card"><h3>{mat_count}</h3><p>Published Materials</p></div>', unsafe_allow_html=True)
            c3.markdown(f'<div class="metric-card"><h3>{test_count}</h3><p>Live Published Tests</p></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)
            st.subheader("Student Distribution by Course")
            conn = sqlite3.connect(DB_FILE)
            dist = pd.read_sql_query("SELECT course_stream as 'Course', COUNT(*) as 'Students' FROM users WHERE role = 'Student' GROUP BY course_stream", conn)
            conn.close()
            st.table(dist if not dist.empty else pd.DataFrame({"Course": COURSES, "Students": [0, 0, 0]}))

        elif menu == "📤 Upload & Change Material":
            st.subheader("📤 Teacher Upload & Manage Material")
            with st.form("upload_mat_form"):
                sel_course = st.selectbox("Target Course:", COURSES)
                sel_type = st.selectbox("Content Category:", CONTENT_TYPES)
                mat_title = st.text_input("Material Title:")
                mat_file = st.file_uploader("Select File (PDF, DOCX, PPTX):", type=["pdf", "docx", "pptx"])
                if st.form_submit_button("Upload Material") and mat_title and mat_file:
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
                    st.success(f"Material #{del_id} removed.")
                    st.rerun()

        elif menu == "👨‍🎓 Registered Students & Reports":
            st.subheader("👨‍🎓 Enrolled Students & Saved Reports")
            conn = sqlite3.connect(DB_FILE)
            studs = pd.read_sql_query("SELECT username as 'Roll No / CRN', full_name as 'Name', course_stream as 'Course' FROM users WHERE role = 'Student'", conn)
            grades = pd.read_sql_query("""
                SELECT r.username as 'Roll No', u.full_name as 'Name', r.course_stream as 'Course', 
                       t.title as 'Test', r.score as 'Score', r.total as 'Total', r.submitted_at as 'Date'
                FROM student_results r
                JOIN users u ON r.username = u.username
                JOIN mock_tests t ON r.test_id = t.id
                ORDER BY r.id DESC
            """, conn)
            conn.close()

            t1, t2 = st.tabs(["Student Directory", "All Test Results"])
            with t1:
                st.dataframe(studs, use_container_width=True)
            with t2:
                st.dataframe(grades, use_container_width=True)

    # ----------------- STUDENT VIEW -----------------
    else:
        st_course = st.session_state.course_stream

        if menu == "⏱️ Take Timed Mock Test":
            st.subheader(f"⏱️ Available Mock Tests ({st_course})")
            st.caption("Only verified and approved tests by Sir HM Umer Choudhary are listed here.")

            conn = sqlite3.connect(DB_FILE)
            # Only PUBLISHED tests are visible to students
            tests = pd.read_sql_query(
                "SELECT id, title, duration_minutes, total_marks FROM mock_tests WHERE course_stream = ? AND status = 'PUBLISHED'",
                conn, params=(st_course,)
            )
            conn.close()

            if not tests.empty:
                if not st.session_state.test_active and not st.session_state.test_submitted:
                    chosen = st.selectbox("Select Mock Test to Attempt:", [f"{r['id']} - {r['title']} | Time: {r['duration_minutes']} Mins | Marks: {r['total_marks']}" for _, r in tests.iterrows()])
                    tid = int(chosen.split(" - ")[0])

                    if st.button("🚀 Start Timed Mock Test", use_container_width=True):
                        st.session_state.test_active = True
                        st.session_state.current_test_id = tid
                        st.session_state.test_start_time = time.time()
                        st.session_state.test_submitted = False
                        st.rerun()

                elif st.session_state.test_active:
                    tid = st.session_state.current_test_id
                    conn = sqlite3.connect(DB_FILE)
                    t_info = pd.read_sql_query("SELECT title, duration_minutes, total_marks FROM mock_tests WHERE id = ?", conn, params=(tid,)).iloc[0]
                    questions = pd.read_sql_query("SELECT id, question, opt_a, opt_b, opt_c, opt_d FROM test_questions WHERE test_id = ?", conn, params=(tid,))
                    conn.close()

                    elapsed = int(time.time() - st.session_state.test_start_time)
                    remaining = max(0, (t_info['duration_minutes'] * 60) - elapsed)
                    m, s = divmod(remaining, 60)

                    st.warning(f"⏳ **Time Remaining:** `{m:02d}:{s:02d}` | Total Questions: **{len(questions)}**")
                    if remaining == 0:
                        st.error("⚠️ Time has expired! Submitting test automatically...")

                    with st.form("exam_paper"):
                        student_ans = {}
                        for idx, q in questions.iterrows():
                            st.markdown(f"**Q{idx+1}: {q['question']}**")
                            opts = [f"A) {q['opt_a']}", f"B) {q['opt_b']}", f"C) {q['opt_c']}", f"D) {q['opt_d']}"]
                            student_ans[q['id']] = st.radio(f"Select Answer for Q{idx+1}:", opts, key=f"ans_{q['id']}")
                            st.markdown("---")

                        btn_finish = st.form_submit_button("Submit Mock Test Now")
                        if btn_finish or remaining == 0:
                            conn = sqlite3.connect(DB_FILE)
                            sol_q = pd.read_sql_query("SELECT id, correct_opt FROM test_questions WHERE test_id = ?", conn, params=(tid,))
                            
                            correct_count = 0
                            for _, sol in sol_q.iterrows():
                                sel = student_ans.get(sol['id'], "")
                                if sel.startswith(sol['correct_opt']):
                                    correct_count += 1
                                    
                            earned_marks = int((correct_count / len(sol_q)) * t_info['total_marks']) if len(sol_q) > 0 else 0

                            c = conn.cursor()
                            c.execute("INSERT INTO student_results (username, course_stream, test_id, score, total, submitted_at) VALUES (?, ?, ?, ?, ?, ?)",
                                      (st.session_state.username, st_course, tid, earned_marks, t_info['total_marks'], str(datetime.now().strftime("%Y-%m-%d %H:%M"))))
                            conn.commit()
                            conn.close()

                            st.session_state.test_active = False
                            st.session_state.test_submitted = True
                            st.session_state.last_submission = {
                                "tid": tid,
                                "score": earned_marks,
                                "total": t_info['total_marks'],
                                "answers": student_ans
                            }
                            st.rerun()

                elif st.session_state.test_submitted:
                    res = st.session_state.last_submission
                    st.success(f"🎉 Mock Test Completed! Marks Scored: **{res['score']} / {res['total']}**")
                    st.markdown("### 📖 Detailed Solutions & Explanations (Urdu & English)")

                    conn = sqlite3.connect(DB_FILE)
                    details = pd.read_sql_query("SELECT id, question, opt_a, opt_b, opt_c, opt_d, correct_opt, exp_en, exp_ur FROM test_questions WHERE test_id = ?", conn, params=(res['tid'],))
                    conn.close()

                    for idx, d in details.iterrows():
                        u_ans = res['answers'].get(d['id'], "Not Attempted")
                        is_corr = u_ans.startswith(d['correct_opt'])
                        tag = "✅ Correct" if is_corr else "❌ Incorrect"

                        st.markdown(f"**Q{idx+1}: {d['question']}** ({tag})")
                        st.write(f"Your Choice: `{u_ans}` | Correct Key: **Option {d['correct_opt']}**")
                        st.markdown(f"""
                            <div class="solution-box">
                                <p><strong>💡 English Explanation:</strong> {d['exp_en']}</p>
                                <p><strong>اردو وضاحت:</strong> {d['exp_ur']}</p>
                            </div>
                        """, unsafe_allow_html=True)
                        st.markdown("---")

                    if st.button("Return to Tests"):
                        st.session_state.test_submitted = False
                        st.session_state.last_submission = {}
                        st.rerun()
            else:
                st.info(f"No mock tests are currently published for {st_course}. Please check back after teacher approval.")

        elif menu == "📚 My Course Material (7-Pillars)":
            st.subheader(f"📖 Study Center: {st_course}")
            tab_book, tab_notes, tab_slides, tab_mcq, tab_test, tab_sol, tab_disc = st.tabs([
                "📖 Book", "📝 Notes", "📊 Slides", "🔘 MCQ", "⏱️ Test Docs", "💡 Solution", "💬 Discussion"
            ])

            conn = sqlite3.connect(DB_FILE)
            mats = pd.read_sql_query(
                "SELECT content_type, title, file_path, uploaded_at FROM portal_materials WHERE course_stream = ?",
                conn, params=(st_course,)
            )
            conn.close()

            def render_pillar_content(pillar_name):
                sub = mats[mats['content_type'] == pillar_name] if not mats.empty else pd.DataFrame()
                if not sub.empty:
                    for _, r in sub.iterrows():
                        st.markdown(f"#### 📄 {r['title']}")
                        st.caption(f"Uploaded: {r['uploaded_at']}")
                        if os.path.exists(r['file_path']):
                            with open(r['file_path'], "rb") as cur:
                                st.download_button(f"📥 Download {pillar_name}", cur, file_name=os.path.basename(r['file_path']), key=f"{pillar_name}_{r['file_path']}")
                        st.markdown("---")
                else:
                    st.info(f"No {pillar_name} files uploaded yet for {st_course}.")

            with tab_book:
                render_pillar_content("Book")
            with tab_notes:
                render_pillar_content("Notes")
            with tab_slides:
                render_pillar_content("Slides")
            with tab_mcq:
                render_pillar_content("MCQ")
            with tab_test:
                render_pillar_content("Test")
            with tab_sol:
                render_pillar_content("Solution")
            with tab_disc:
                st.subheader("💬 Course Discussion Forum")
                conn = sqlite3.connect(DB_FILE)
                chat_data = pd.read_sql_query(
                    "SELECT sender_name, sender_role, message, created_at FROM discussions WHERE course_stream = ? ORDER BY id ASC",
                    conn, params=(st_course,)
                )
                conn.close()

                if not chat_data.empty:
                    for _, d in chat_data.iterrows():
                        badge = "👨‍🏫 Teacher" if d['sender_role'] == 'Teacher' else "👨‍🎓 Student"
                        st.markdown(f"**{d['sender_name']}** ({badge}) - `{d['created_at']}`")
                        st.write(d['message'])
                        st.markdown("---")

                with st.form("disc_form"):
                    q_msg = st.text_input("Ask a question regarding this course:")
                    if st.form_submit_button("Post Question"):
                        if q_msg:
                            conn = sqlite3.connect(DB_FILE)
                            c = conn.cursor()
                            c.execute("INSERT INTO discussions (course_stream, sender_name, sender_role, message, created_at) VALUES (?, ?, ?, ?, ?)",
                                      (st_course, st.session_state.full_name, st.session_state.role, q_msg, str(datetime.now().strftime("%Y-%m-%d %H:%M"))))
                            conn.commit()
                            conn.close()
                            st.rerun()

        elif menu == "📄 My Saved Reports & Grades":
            st.subheader(f"📄 Saved Performance & Grade Card ({st.session_state.full_name})")
            conn = sqlite3.connect(DB_FILE)
            my_reps = pd.read_sql_query("""
                SELECT t.title as 'Test Title', r.score as 'Marks Obtained', r.total as 'Max Marks', r.submitted_at as 'Date Attempted'
                FROM student_results r
                JOIN mock_tests t ON r.test_id = t.id
                WHERE r.username = ?
                ORDER BY r.id DESC
            """, conn, params=(st.session_state.username,))
            conn.close()

            if not my_reps.empty:
                t_obt = my_reps['Marks Obtained'].sum()
                t_tot = my_reps['Max Marks'].sum()
                pct = round((t_obt / t_tot) * 100, 1)

                c1, c2 = st.columns(2)
                c1.metric("Cumulative Average", f"{pct}%")
                c2.metric("Tests Taken", len(my_reps))

                st.markdown("---")
                st.dataframe(my_reps, use_container_width=True)
            else:
                st.info("No test records found yet. Complete a test in 'Take Timed Mock Test' to generate reports.")
