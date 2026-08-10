import streamlit as st
import os
import time
import sqlite3
import json
import datetime
from pydantic import BaseModel, ValidationError, Field
from typing import List
from openai import OpenAI

# Ensure API key is loaded from .env if running locally without export
env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('DEEPSEEK_API_KEY='):
                os.environ["DEEPSEEK_API_KEY"] = line.strip().split('=', 1)[1]

# ====================================================================
# EXTRACTION LOGIC
# ====================================================================

class ClinicalInformation(BaseModel):
    diagnoses: List[str] = Field(default_factory=list)
    medication_changes: List[str] = Field(default_factory=list)
    allergies: List[str] = Field(default_factory=list)
    abnormal_findings: List[str] = Field(default_factory=list)
    follow_up_instructions: List[str] = Field(default_factory=list)

def get_deepseek_client():
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY environment variable is not set.")
    
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def extract_clinical_information(clinical_note: str) -> dict:
    client = get_deepseek_client()
    
    system_prompt = """
    You are a strict clinical information extraction engine. 
    Your job is to extract specific information from clinical notes and output it as a JSON object.
    
    EXTRACTION RULES:
    1. Extract only information explicitly present in the clinical note. Do NOT infer, diagnose, predict, or add medical information.
    2. Never hallucinate. If a category is not present, return an empty array [].
    3. Preserve the meaning of the source. Do not rewrite information in a way that changes its meaning.
    4. Extract ONLY these five categories: diagnoses, medication_changes, allergies, abnormal_findings, follow_up_instructions. Do not create additional categories.
    5. Medication changes: Only include medication actions explicitly stated in the note (started, initiated, stopped, discontinued, increased, decreased, changed). Do not assume a change merely because a medication is mentioned.
    6. Allergies: Only extract allergies explicitly stated or clearly documented in the note.
    7. Abnormal findings: Extract explicitly documented abnormal clinical findings (vital signs, labs, exams). Do not classify something as abnormal based on your own knowledge unless the note explicitly indicates it.
    8. Follow-up instructions: Only extract explicit instructions concerning follow-up, review, monitoring, referral, or return visits.
    9. Empty categories: Return [] if no information exists. Never use null or "Not found".
    
    Respond ONLY with a raw, valid JSON object matching this schema. Do not include markdown formatting or explanation.
    
    {
      "diagnoses": ["array of strings"],
      "medication_changes": ["array of strings"],
      "allergies": ["array of strings"],
      "abnormal_findings": ["array of strings"],
      "follow_up_instructions": ["array of strings"]
    }
    """
    
    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Clinical Note:\n{clinical_note}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        raw_json_str = response.choices[0].message.content
        parsed_data = json.loads(raw_json_str)
        validated_data = ClinicalInformation(**parsed_data)
        return validated_data.model_dump()
        
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON response from API: {e}")
    except ValidationError as e:
        raise RuntimeError(f"API response failed schema validation: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred during extraction: {e}")

# ====================================================================
# DATABASE LOGIC
# ====================================================================

DB_PATH = "clinical_extraction.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_database():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS Patients (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_code TEXT UNIQUE NOT NULL, name TEXT NOT NULL, date_of_birth TEXT NOT NULL, gender TEXT NOT NULL)''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ClinicalRecords (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER NOT NULL, record_date TEXT NOT NULL, record_type TEXT NOT NULL, clinical_note TEXT NOT NULL, FOREIGN KEY (patient_id) REFERENCES Patients(id))''')
    cursor.execute('''CREATE TABLE IF NOT EXISTS ExtractionResults (id INTEGER PRIMARY KEY AUTOINCREMENT, record_id INTEGER NOT NULL, diagnoses TEXT NOT NULL, medication_changes TEXT NOT NULL, allergies TEXT NOT NULL, abnormal_findings TEXT NOT NULL, follow_up_instructions TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY (record_id) REFERENCES ClinicalRecords(id))''')
    conn.commit()
    conn.close()

def create_patient(patient_code, name, date_of_birth, gender):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO Patients (patient_code, name, date_of_birth, gender) VALUES (?, ?, ?, ?)''', (patient_code, name, date_of_birth, gender))
    conn.commit()
    patient_id = cursor.lastrowid
    conn.close()
    return patient_id

def get_patients():
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Patients")
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_patient(patient_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Patients WHERE id = ?", (patient_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def create_clinical_record(patient_id, record_date, record_type, clinical_note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO ClinicalRecords (patient_id, record_date, record_type, clinical_note) VALUES (?, ?, ?, ?)''', (patient_id, record_date, record_type, clinical_note))
    conn.commit()
    record_id = cursor.lastrowid
    conn.close()
    return record_id

def get_patient_records(patient_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ClinicalRecords WHERE patient_id = ?", (patient_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_clinical_record(record_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ClinicalRecords WHERE id = ?", (record_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def save_extraction_result(record_id, result_dict):
    conn = get_connection()
    cursor = conn.cursor()
    diagnoses = json.dumps(result_dict.get("diagnoses", []))
    medication_changes = json.dumps(result_dict.get("medication_changes", []))
    allergies = json.dumps(result_dict.get("allergies", []))
    abnormal_findings = json.dumps(result_dict.get("abnormal_findings", []))
    follow_up_instructions = json.dumps(result_dict.get("follow_up_instructions", []))
    created_at = datetime.datetime.now().isoformat()
    cursor.execute('''INSERT INTO ExtractionResults (record_id, diagnoses, medication_changes, allergies, abnormal_findings, follow_up_instructions, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)''', (record_id, diagnoses, medication_changes, allergies, abnormal_findings, follow_up_instructions, created_at))
    conn.commit()
    extraction_id = cursor.lastrowid
    conn.close()
    return extraction_id

def get_extraction_result(record_id):
    conn = get_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ExtractionResults WHERE record_id = ? ORDER BY created_at DESC LIMIT 1", (record_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    result = dict(row)
    result["diagnoses"] = json.loads(result["diagnoses"])
    result["medication_changes"] = json.loads(result["medication_changes"])
    result["allergies"] = json.loads(result["allergies"])
    result["abnormal_findings"] = json.loads(result["abnormal_findings"])
    result["follow_up_instructions"] = json.loads(result["follow_up_instructions"])
    return result

# ====================================================================
# STREAMLIT UI
# ====================================================================

st.set_page_config(page_title="CLINEX - Clinical Information Extraction System", page_icon="⚕️", layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&display=swap');
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global Typography & Background */
    body, .stApp { 
        font-family: 'Outfit', sans-serif; 
        background: linear-gradient(135deg, #020617 0%, #0f172a 100%);
        color: #f8fafc;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6, .markdown-text-container { font-family: 'Outfit', sans-serif; }
    
    /* Branding */
    .brand-title { font-weight: 800; font-size: 2rem; background: linear-gradient(to right, #38bdf8, #818cf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; letter-spacing: 1.5px; margin-bottom: -10px; }
    .brand-subtitle { font-size: 0.9rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1.5px; font-weight: 600; margin-bottom: 30px; }
    
    /* Status indicators */
    .status-online { color: #10b981; font-weight: 600; text-shadow: 0 0 10px rgba(16,185,129,0.5); }
    .status-pending { color: #f59e0b; font-weight: 600; }
    .status-completed { color: #38bdf8; font-weight: 600; text-shadow: 0 0 10px rgba(56,189,248,0.5); }
    
    /* Glassmorphism Cards */
    .metric-card { background-color: rgba(255,255,255,0.03); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 1.5rem; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.1); transition: transform 0.3s ease, border-color 0.3s ease; }
    .metric-card:hover { transform: translateY(-5px); border-color: rgba(56,189,248,0.4); }
    .metric-value { font-size: 2.5rem; font-weight: 800; color: #f8fafc; }
    .metric-label { font-size: 0.8rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }
    
    .data-card { background-color: rgba(255,255,255,0.02); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.08); border-radius: 8px; padding: 1.2rem; margin-bottom: 1rem; transition: all 0.3s ease; }
    .data-card:hover { border-color: rgba(56,189,248,0.5); background-color: rgba(255,255,255,0.05); transform: translateY(-2px); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3); }
    
    /* Results Interface */
    .result-section { background-color: rgba(15,23,42,0.6); backdrop-filter: blur(10px); border: 1px solid rgba(255,255,255,0.05); border-left: 4px solid #38bdf8; border-radius: 8px; padding: 1.2rem; margin-bottom: 1.2rem; }
    .result-header { font-size: 0.75rem; font-weight: 700; color: #cbd5e1; text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 0.5rem; }
    .result-content { font-size: 1rem; color: #f8fafc; font-weight: 400; }
    .empty-result { color: #64748b; font-style: italic; font-size: 0.9rem; }
    
    /* Workstation */
    .workstation-note { background-color: rgba(0,0,0,0.2); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 1.5rem; font-family: 'Outfit', sans-serif; font-size: 0.95rem; line-height: 1.6; color: #cbd5e1; white-space: pre-wrap; }
    
    /* Breadcrumbs & Metadata */
    .breadcrumbs { font-size: 0.85rem; color: #94a3b8; margin-bottom: 1.5rem; }
    .metadata-block { background-color: rgba(255,255,255,0.02); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 1rem; margin-top: 2rem; font-size: 0.85rem; color: #94a3b8; }
    
    /* Sidebar */
    [data-testid="stSidebar"] { background-color: rgba(15,23,42,0.9); backdrop-filter: blur(20px); border-right: 1px solid rgba(255,255,255,0.05); }
    
    /* Tables/Lists styling override */
    .stMarkdown p { color: #f8fafc !important; }
    strong { color: #f1f5f9; font-weight: 600; }

</style>
""", unsafe_allow_html=True)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "current_view" not in st.session_state:
    st.session_state["current_view"] = "login"
if "selected_patient_id" not in st.session_state:
    st.session_state["selected_patient_id"] = None
if "selected_record_id" not in st.session_state:
    st.session_state["selected_record_id"] = None
if "extracting_record_id" not in st.session_state:
    st.session_state["extracting_record_id"] = None

def navigate(view):
    st.session_state["current_view"] = view
    st.rerun()

def show_login():
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.2, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div class="brand-title">CLINEX</div>
            <div class="brand-subtitle">Clinical Information Extraction System</div>
            <div style="color: #6B7280; font-size: 0.9rem;">Structured information from clinical records</div>
        </div>
        """, unsafe_allow_html=True)
        with st.container(border=True):
            st.text_input("Email", placeholder="doctor@hospital.com")
            st.text_input("Password", type="password", placeholder="••••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("SIGN IN", type="primary", use_container_width=True):
                st.session_state["logged_in"] = True
                navigate("overview")
        st.markdown("<div style='text-align: center; color: #9CA3AF; font-size: 0.8rem; margin-top: 1rem;'>Prototype Environment</div>", unsafe_allow_html=True)

def render_sidebar():
    st.sidebar.markdown("""
    <div style="margin-bottom: 2rem;">
        <div class="brand-title" style="font-size: 1.5rem;">CLINEX</div>
        <div style="font-size: 0.75rem; color: #6B7280;">● System Online &nbsp;&nbsp;|&nbsp;&nbsp; User ▼</div>
    </div>
    """, unsafe_allow_html=True)
    if st.sidebar.button("▣ Overview", use_container_width=True, type="primary" if st.session_state["current_view"] == "overview" else "secondary"):
        navigate("overview")
    if st.sidebar.button("▣ Patients", use_container_width=True, type="primary" if st.session_state["current_view"] in ["patients", "workspace"] else "secondary"):
        navigate("patients")
    if st.sidebar.button("▣ Records", use_container_width=True, type="primary" if st.session_state["current_view"] in ["record", "results"] else "secondary"):
        if st.session_state["selected_record_id"]:
            navigate("record")
        elif st.session_state["selected_patient_id"]:
            navigate("workspace")
        else:
            navigate("patients")
    if st.sidebar.button("▣ Extractions", use_container_width=True, type="primary" if st.session_state["current_view"] == "extractions" else "secondary"):
        navigate("extractions")
    st.sidebar.markdown("<br><hr><br>", unsafe_allow_html=True)
    st.sidebar.markdown("<div style='font-size: 0.75rem; font-weight: bold; color: #9CA3AF; margin-bottom: 0.5rem;'>SYSTEM</div>", unsafe_allow_html=True)
    st.sidebar.button("⚙ Settings", use_container_width=True)
    st.sidebar.button("ℹ About", use_container_width=True)
    st.sidebar.markdown("<br><br>", unsafe_allow_html=True)
    st.sidebar.markdown("""
    <div style="font-size: 0.75rem; color: #6B7280;">
        Database &nbsp;&nbsp;&nbsp;&nbsp;<span class="status-online">● Connected</span><br>
        Extraction &nbsp;&nbsp;<span class="status-online">● Available</span><br>
        API &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<span class="status-online">● Connected</span>
    </div>
    """, unsafe_allow_html=True)

def show_overview():
    st.markdown("<div class='brand-subtitle'>OVERVIEW</div>", unsafe_allow_html=True)
    st.markdown("## Clinical Information Extraction System")
    try:
        patients = get_patients()
        num_patients = len(patients)
        conn = get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ClinicalRecords")
        num_records = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM ExtractionResults")
        num_extractions = c.fetchone()[0]
        conn.close()
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
    col1, col2, col3, col4 = st.columns(4)
    def metric_card(col, value, label):
        col.markdown(f"""
        <div class="metric-card">
            <div class="metric-value">{value:02d}</div>
            <div class="metric-label">{label}</div>
        </div>
        """, unsafe_allow_html=True)
    metric_card(col1, num_patients, "PATIENTS")
    metric_card(col2, num_records, "RECORDS")
    metric_card(col3, num_extractions, "EXTRACTIONS")
    metric_card(col4, num_extractions, "SAVED")
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("### RECENT ACTIVITY")
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT e.created_at, p.name, r.record_type 
            FROM ExtractionResults e
            JOIN ClinicalRecords r ON e.record_id = r.id
            JOIN Patients p ON r.patient_id = p.id
            ORDER BY e.created_at DESC LIMIT 5
        """)
        activities = c.fetchall()
        conn.close()
        if not activities:
            st.info("No recent extraction activity.")
        else:
            for act in activities:
                st.markdown(f"""
                <div style="border-left: 2px solid #D1D5DB; padding-left: 1rem; margin-bottom: 1rem;">
                    <strong>Extraction completed</strong><br>
                    <span style="color: #4B5563;">{act['name']} - {act['record_type']}</span><br>
                    <span style="color: #9CA3AF; font-size: 0.8rem;">Recently saved</span>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

def show_patients():
    st.markdown("<div class='brand-subtitle'>PATIENTS</div>", unsafe_allow_html=True)
    st.markdown("## Manage and review registered patient records.")
    st.text_input("Search patients...", placeholder="Enter name or ID...")
    try:
        patients = get_patients()
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
    if not patients:
        st.info("No patients found.")
        return
    st.markdown("<hr>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
    col1.markdown("**PATIENT ID**")
    col2.markdown("**PATIENT NAME**")
    col3.markdown("**GENDER**")
    col4.markdown("**ACTION**")
    st.markdown("<hr style='margin-top: 0;'>", unsafe_allow_html=True)
    for p in patients:
        col1, col2, col3, col4 = st.columns([1, 2, 1, 1])
        col1.write(p['patient_code'])
        col2.write(p['name'])
        col3.write(p['gender'])
        with col4:
            if st.button("Open Workspace", key=f"p_{p['id']}", type="secondary"):
                st.session_state["selected_patient_id"] = p['id']
                navigate("workspace")

def show_workspace():
    p_id = st.session_state.get("selected_patient_id")
    if not p_id:
        navigate("patients")
    try:
        patient = get_patient(p_id)
        records = get_patient_records(p_id)
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
    st.markdown(f"<div class='breadcrumbs'>Patients / {patient['name']}</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-subtitle'>PATIENT WORKSPACE</div>", unsafe_allow_html=True)
    st.markdown(f"## {patient['name']}")
    st.markdown(f"#### {patient['patient_code']}")
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; padding: 1.5rem; background-color: rgba(255,255,255,0.02); backdrop-filter: blur(10px); margin-bottom: 2rem;">
        <h4 style="margin-top: 0; color: #94a3b8; font-size: 0.9rem; letter-spacing: 1px;">PATIENT INFORMATION</h4>
        <strong>Date of Birth:</strong> {dob}<br>
        <strong>Gender:</strong> {gender}<br>
        <strong>Clinical Records:</strong> {count}
    </div>
    """.format(dob=patient['date_of_birth'], gender=patient['gender'], count=len(records)), unsafe_allow_html=True)
    st.markdown("### CLINICAL RECORDS")
    if not records:
        st.info("No clinical records available for this patient.")
        return
    for record in records:
        with st.container():
            st.markdown(f"""
            <div class="data-card">
                <div style="font-weight: bold; color: #111827;">{record['record_date']}</div>
                <div style="color: #4B5563; font-size: 0.9rem; margin-bottom: 0.5rem;">{record['record_type']}</div>
                <div style="color: #6B7280; font-size: 0.85rem; margin-bottom: 1rem;">{record['clinical_note'][:80]}...</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("VIEW RECORD →", key=f"vr_{record['id']}"):
                st.session_state["selected_record_id"] = record['id']
                navigate("record")

def show_clinical_record():
    r_id = st.session_state.get("selected_record_id")
    p_id = st.session_state.get("selected_patient_id")
    if not r_id:
        navigate("patients")
    try:
        record = get_clinical_record(r_id)
        if not record:
            st.error("The selected clinical record could not be found.")
            return
        patient = get_patient(record['patient_id'])
        existing_extraction = get_extraction_result(r_id)
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
    st.markdown(f"<div class='breadcrumbs'>{patient['name']} / Clinical Record {record['id']}</div>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 1rem; margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
                <div style="font-weight: 800; font-size: 1.5rem; color: #f8fafc; text-shadow: 0 0 15px rgba(56,189,248,0.3);">RECORD CR-{record['id']:03d}</div>
                <div style="color: #94a3b8;">{patient['name']} · {record['record_type']}</div>
            </div>
            <div style="font-weight: 600; color: #cbd5e1;">{record['record_date']}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    col_doc, col_ext = st.columns([1.5, 1])
    with col_doc:
        st.markdown("<div style='font-weight: bold; margin-bottom: 1rem; color: #374151;'>CLINICAL DOCUMENTATION</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='color: #6B7280; margin-bottom: 0.5rem; font-size: 0.9rem;'>{record['record_type']} Note</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='workstation-note'>{record['clinical_note']}</div>", unsafe_allow_html=True)
    with col_ext:
        st.markdown("<div style='font-weight: bold; margin-bottom: 1rem; color: #374151;'>EXTRACTION</div>", unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown("<div style='font-size: 0.8rem; font-weight: bold; color: #6B7280; margin-bottom: 0.5rem;'>Status</div>", unsafe_allow_html=True)
            if st.session_state.get("extracting_record_id") == r_id:
                st.markdown("**PROCESSING CLINICAL RECORD**")
                ph1 = st.empty()
                ph2 = st.empty()
                ph3 = st.empty()
                ph4 = st.empty()
                ph5 = st.empty()
                ph1.markdown("✓ Retrieve clinical documentation")
                time.sleep(0.5)
                ph2.markdown("● Extract critical information")
                try:
                    result = extract_clinical_information(record['clinical_note'])
                    ph2.markdown("✓ Extract critical information")
                    ph3.markdown("● Validate structured result")
                    time.sleep(0.3)
                    ph3.markdown("✓ Validate structured result")
                    ph4.markdown("● Save extraction")
                    save_extraction_result(r_id, result)
                    ph4.markdown("✓ Save extraction")
                    ph5.markdown("**EXTRACTION COMPLETE ✓**")
                    time.sleep(0.5)
                    st.session_state["extracting_record_id"] = None
                    navigate("results")
                except RuntimeError as e:
                    st.session_state["extracting_record_id"] = None
                    if "schema validation" in str(e) or "parse JSON" in str(e):
                        st.error("The extraction result could not be validated. Please try again.")
                    else:
                        st.error("Unable to extract information from this clinical record. Please try again.")
                except Exception:
                    st.session_state["extracting_record_id"] = None
                    st.error("Unable to extract information from this clinical record. Please try again.")
            else:
                if existing_extraction:
                    st.markdown("<div class='status-completed'>✓ Extraction completed</div><br>", unsafe_allow_html=True)
                    if st.button("View Results", type="primary"):
                        navigate("results")
                    if st.button("Extract Again", type="secondary"):
                        st.session_state["extracting_record_id"] = r_id
                        st.rerun()
                else:
                    st.markdown("<div class='status-online'>● Ready</div>", unsafe_allow_html=True)
                    st.markdown("<div style='color: #6B7280; font-size: 0.85rem; margin-bottom: 1.5rem;'>This record has not been processed.</div>", unsafe_allow_html=True)
                    if st.button("Extract Critical Information", type="primary"):
                        st.session_state["extracting_record_id"] = r_id
                        st.rerun()

def show_results():
    r_id = st.session_state.get("selected_record_id")
    p_id = st.session_state.get("selected_patient_id")
    if not r_id:
        navigate("patients")
    try:
        record = get_clinical_record(r_id)
        patient = get_patient(record['patient_id'])
        result = get_extraction_result(r_id)
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
    if not result:
        st.warning("No extraction result found.")
        return
    st.markdown(f"<div class='breadcrumbs'>{patient['name']} / Clinical Record CR-{record['id']:03d} / Extraction Result</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-subtitle'>EXTRACTION RESULT</div>", unsafe_allow_html=True)
    st.markdown(f"## CR-{record['id']:03d}")
    st.markdown(f"#### {patient['name']}")
    st.markdown(f"##### {record['record_date']}")
    st.markdown("<div class='status-completed' style='margin-bottom: 2rem;'>✓ Extraction completed</div>", unsafe_allow_html=True)
    st.markdown("### CRITICAL INFORMATION")
    st.markdown("<hr style='margin-top:0;'>", unsafe_allow_html=True)
    def render_cat(title, items):
        st.markdown(f"<div class='result-header'>{title}</div>", unsafe_allow_html=True)
        if not items:
            st.markdown("<div class='result-section empty-result'>No information identified</div>", unsafe_allow_html=True)
        else:
            content = "<br>".join([f"• {item}" for item in items])
            st.markdown(f"<div class='result-section result-content'>{content}</div>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        render_cat("DIAGNOSES", result.get("diagnoses", []))
        render_cat("ALLERGIES", result.get("allergies", []))
        render_cat("FOLLOW-UP INSTRUCTIONS", result.get("follow_up_instructions", []))
    with col2:
        render_cat("MEDICATION CHANGES", result.get("medication_changes", []))
        render_cat("ABNORMAL FINDINGS", result.get("abnormal_findings", []))
    st.markdown(f"""
    <div class="metadata-block">
        <strong style="color: #111827;">EXTRACTION DETAILS</strong><br>
        Extraction ID: EXT-{result['id']:03d}<br>
        Processed: {result.get('created_at', 'Unknown')[:10]}<br>
        Status: Completed<br><br>
        <strong style="color: #111827;">SOURCE</strong><br>
        Clinical Record: CR-{record['id']:03d}<br>
        Record Type: {record['record_type']}<br>
        Date: {record['record_date']}
    </div>
    """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("View Original Clinical Note"):
        navigate("record")

def show_extractions():
    st.markdown("<div class='brand-subtitle'>EXTRACTIONS</div>", unsafe_allow_html=True)
    st.markdown("## System Extraction Log")
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT e.id as ext_id, e.created_at, p.name, r.id as rec_id, r.record_date 
            FROM ExtractionResults e
            JOIN ClinicalRecords r ON e.record_id = r.id
            JOIN Patients p ON r.patient_id = p.id
            ORDER BY e.created_at DESC
        """)
        exts = c.fetchall()
        conn.close()
    except Exception:
        st.error("Unable to connect to the database.")
        return
    if not exts:
        st.info("No extractions found.")
        return
    st.markdown("<hr>", unsafe_allow_html=True)
    col1, col2, col3, col4, col5 = st.columns([1, 2, 1, 1, 1.5])
    col1.markdown("**EXTRACTION ID**")
    col2.markdown("**PATIENT**")
    col3.markdown("**RECORD**")
    col4.markdown("**DATE**")
    col5.markdown("**STATUS**")
    st.markdown("<hr style='margin-top: 0;'>", unsafe_allow_html=True)
    for ex in exts:
        c1, c2, c3, c4, c5 = st.columns([1, 2, 1, 1, 1.5])
        c1.write(f"EXT-{ex['ext_id']:03d}")
        c2.write(ex['name'])
        c3.write(f"CR-{ex['rec_id']:03d}")
        c4.write(ex['record_date'])
        with c5:
            if st.button("View Result", key=f"vr_{ex['ext_id']}"):
                st.session_state["selected_record_id"] = ex['rec_id']
                st.session_state["selected_patient_id"] = get_clinical_record(ex['rec_id'])['patient_id']
                navigate("results")

if not st.session_state["logged_in"]:
    show_login()
else:
    render_sidebar()
    view = st.session_state["current_view"]
    if view == "overview":
        show_overview()
    elif view == "patients":
        show_patients()
    elif view == "workspace":
        show_workspace()
    elif view == "record":
        show_clinical_record()
    elif view == "results":
        show_results()
    elif view == "extractions":
        show_extractions()
    else:
        show_overview()
