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
DB_FILE = "hm_umer_portal_v3.db"
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
        status TEXT DEFAULT 'PUBLISHED',
        created_at TEXT
    )''')
    
    c.execute("PRAGMA table_info(mock_tests)")
    cols = [col[1] for col in c.fetchall()]
    if "status" not in cols:
        c.execute("ALTER TABLE mock_tests ADD COLUMN status TEXT DEFAULT 'PUBLISHED'")
    
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
    except Exception:
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
        "exp_ur": "Accrual ki roo se aamdani aur ikhrajat usi muddat mein record hotay hain jab woh waqia hon, chahay cash mila ho ya na mila ho."
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
        "exp_ur": "Asset ko usable condition mein laane ke direct ikhrajat ko capitalize kiya jata hai."
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
        "exp_ur": "Prudence concept ke tehat inventory ko cost aur NRV mein se lower value par likha jata hai."
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
        "exp_ur": "Qualifying asset ke loan interest ko direct asset ki cost mein add kiya jata hai."
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
        "exp_ur": "Past event ki present obligation, probable outflow aur reliable estimate provision ki bunyad hain."
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
        "exp_ur": "Asset revaluation surplus OCI mein jata hai aur equity mein jama hota hai."
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
        "exp_ur": "Unpresented cheques bank statement balance mein se deduct kiye jaate hain."
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
        "exp_ur": "Financial info ka relevant hona aur faithful representation sab se ahem khusoosiyat hain."
    }
]

def generate_high_volume_quiz(extracted_text, num_q, topic_title):
    questions_out = []
    text_sentences = []
    
    if extracted_text and len(extracted_text) > 50:
        cleaned = re.sub(r'\s+', ' ', extracted_text)
        text_sentences = [s.strip() for s in re.split(r'[\.\n\r]+', cleaned) if 35 < len(s.strip()) < 220]

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
                    "exp_ur": f"Kitabi matan ke mutabiq asal hawala tha: \"{s}\". Is usool ke tehat durust jawab '{target_token}' hai."
                })

    bank_cycle = list(ACCOUNTING_QUESTION_BANK)
    random.shuffle(bank_cycle)
    b_idx = 0

    while len(questions_out) < num_q:
        template = bank_cycle[b_idx % len(bank_cycle)]
        b_idx += 1
        
        q_text = template["q"]
        if b_idx > len(bank_cycle):
            q_text = f"[{topic_title} Part {len(questions_out)+1}] " + template["q"]
            
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
