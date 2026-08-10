import streamlit as st
import os
import time

# Ensure API key is loaded from .env if running locally without export
env_path = ".env"
if os.path.exists(env_path):
    with open(env_path, 'r') as f:
        for line in f:
            if line.startswith('DEEPSEEK_API_KEY='):
                os.environ["DEEPSEEK_API_KEY"] = line.strip().split('=', 1)[1]

import database
from extraction import extract_clinical_information

# Page configuration
st.set_page_config(
    page_title="CLINEX - Clinical Information Extraction System",
    page_icon="⚕️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for CLINEX system
st.markdown("""
<style>
    /* Hide Streamlit elements */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* Global Typography */
    body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Branding */
    .brand-title {
        font-weight: 800;
        font-size: 1.8rem;
        color: #1E3A8A;
        letter-spacing: 1px;
        margin-bottom: -10px;
    }
    .brand-subtitle {
        font-size: 0.9rem;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        margin-bottom: 30px;
    }
    
    /* Status indicators */
    .status-online { color: #10B981; font-weight: bold; }
    .status-pending { color: #F59E0B; font-weight: bold; }
    .status-completed { color: #3B82F6; font-weight: bold; }
    
    /* Cards and Containers */
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 1.5rem;
        text-align: center;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: 700;
        color: #111827;
    }
    .metric-label {
        font-size: 0.75rem;
        font-weight: 600;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    .data-card {
        background-color: #ffffff;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 1rem;
        margin-bottom: 1rem;
        transition: box-shadow 0.2s;
    }
    .data-card:hover {
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        border-color: #D1D5DB;
    }
    
    /* Results Interface */
    .result-section {
        background-color: #ffffff;
        border: 1px solid #E5E7EB;
        border-left: 4px solid #1E3A8A;
        border-radius: 4px;
        padding: 1.2rem;
        margin-bottom: 1.2rem;
    }
    .result-header {
        font-size: 0.75rem;
        font-weight: 700;
        color: #6B7280;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-bottom: 0.5rem;
    }
    .result-content {
        font-size: 1rem;
        color: #111827;
        font-weight: 500;
    }
    .empty-result {
        color: #9CA3AF;
        font-style: italic;
        font-size: 0.9rem;
    }
    
    /* Workstation */
    .workstation-note {
        background-color: #F9FAFB;
        border: 1px solid #E5E7EB;
        border-radius: 6px;
        padding: 1.5rem;
        font-family: monospace;
        font-size: 0.95rem;
        line-height: 1.6;
        color: #374151;
        white-space: pre-wrap;
    }
    
    /* Breadcrumbs & Metadata */
    .breadcrumbs {
        font-size: 0.85rem;
        color: #6B7280;
        margin-bottom: 1.5rem;
    }
    .metadata-block {
        background-color: #F3F4F6;
        border-radius: 4px;
        padding: 1rem;
        margin-top: 2rem;
        font-size: 0.85rem;
        color: #4B5563;
    }
    
    /* Sidebar */
    [data-testid="stSidebar"] {
        background-color: #F9FAFB;
        border-right: 1px solid #E5E7EB;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# STATE MANAGEMENT
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# SCREEN 1 - LOGIN
# ---------------------------------------------------------
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

# ---------------------------------------------------------
# APP SHELL & SIDEBAR
# ---------------------------------------------------------
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
        # Default to patients if no record selected
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

# ---------------------------------------------------------
# SCREEN 2 - OVERVIEW DASHBOARD
# ---------------------------------------------------------
def show_overview():
    st.markdown("<div class='brand-subtitle'>OVERVIEW</div>", unsafe_allow_html=True)
    st.markdown("## Clinical Information Extraction System")
    
    try:
        patients = database.get_patients()
        num_patients = len(patients)
        
        # Calculate totals
        conn = database.get_connection()
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM ClinicalRecords")
        num_records = c.fetchone()[0]
        c.execute("SELECT COUNT(*) FROM ExtractionResults")
        num_extractions = c.fetchone()[0]
        conn.close()
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return

    # Metrics Layout
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
        conn = database.get_connection()
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
                # Mock time ago for prototype presentation
                st.markdown(f"""
                <div style="border-left: 2px solid #D1D5DB; padding-left: 1rem; margin-bottom: 1rem;">
                    <strong>Extraction completed</strong><br>
                    <span style="color: #4B5563;">{act['name']} - {act['record_type']}</span><br>
                    <span style="color: #9CA3AF; font-size: 0.8rem;">Recently saved</span>
                </div>
                """, unsafe_allow_html=True)
    except Exception:
        pass

# ---------------------------------------------------------
# SCREEN 3 - PATIENTS MODULE
# ---------------------------------------------------------
def show_patients():
    st.markdown("<div class='brand-subtitle'>PATIENTS</div>", unsafe_allow_html=True)
    st.markdown("## Manage and review registered patient records.")
    
    st.text_input("Search patients...", placeholder="Enter name or ID...")
    
    try:
        patients = database.get_patients()
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
        
    if not patients:
        st.info("No patients found.")
        return
        
    st.markdown("<hr>", unsafe_allow_html=True)
    
    # Header row
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

# ---------------------------------------------------------
# SCREEN 4 - PATIENT WORKSPACE
# ---------------------------------------------------------
import sqlite3

def show_workspace():
    p_id = st.session_state.get("selected_patient_id")
    if not p_id:
        navigate("patients")
        
    try:
        patient = database.get_patient(p_id)
        records = database.get_patient_records(p_id)
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return
        
    st.markdown(f"<div class='breadcrumbs'>Patients / {patient['name']}</div>", unsafe_allow_html=True)
    st.markdown("<div class='brand-subtitle'>PATIENT WORKSPACE</div>", unsafe_allow_html=True)
    st.markdown(f"## {patient['name']}")
    st.markdown(f"#### {patient['patient_code']}")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style="border: 1px solid #E5E7EB; border-radius: 6px; padding: 1.5rem; background-color: #F9FAFB; margin-bottom: 2rem;">
        <h4 style="margin-top: 0; color: #4B5563; font-size: 0.9rem; letter-spacing: 1px;">PATIENT INFORMATION</h4>
        <strong>Date of Birth:</strong> {dob}<br>
        <strong>Gender:</strong> {gender}<br>
        <strong>Clinical Records:</strong> {count}
    </div>
    """.format(dob=patient['date_of_birth'], gender=patient['gender'], count=len(records)), unsafe_allow_html=True)
    
    st.markdown("### CLINICAL RECORDS")
    
    if not records:
        st.info("No clinical records available for this patient.")
        return
        
    # Display cards
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

# ---------------------------------------------------------
# SCREEN 5 - CLINICAL RECORD MODULE
# ---------------------------------------------------------
def show_clinical_record():
    r_id = st.session_state.get("selected_record_id")
    p_id = st.session_state.get("selected_patient_id")
    if not r_id:
        navigate("patients")
        
    try:
        record = database.get_clinical_record(r_id)
        if not record:
            st.error("The selected clinical record could not be found.")
            return
        patient = database.get_patient(record['patient_id'])
        existing_extraction = database.get_extraction_result(r_id)
    except Exception:
        st.error("Unable to connect to the clinical records database.")
        return

    st.markdown(f"<div class='breadcrumbs'>{patient['name']} / Clinical Record {record['id']}</div>", unsafe_allow_html=True)
    
    # Header
    st.markdown(f"""
    <div style="border-bottom: 2px solid #E5E7EB; padding-bottom: 1rem; margin-bottom: 2rem;">
        <div style="display: flex; justify-content: space-between; align-items: flex-end;">
            <div>
                <div style="font-weight: bold; font-size: 1.5rem; color: #111827;">RECORD CR-{record['id']:03d}</div>
                <div style="color: #4B5563;">{patient['name']} · {record['record_type']}</div>
            </div>
            <div style="font-weight: bold; color: #4B5563;">{record['record_date']}</div>
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
            
            # Simulated Processing State
            if st.session_state.get("extracting_record_id") == r_id:
                st.markdown("**PROCESSING CLINICAL RECORD**")
                
                # Simple pipeline visualization
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
                    database.save_extraction_result(r_id, result)
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

# ---------------------------------------------------------
# SCREEN 6 - RESULTS INTERFACE
# ---------------------------------------------------------
def show_results():
    r_id = st.session_state.get("selected_record_id")
    p_id = st.session_state.get("selected_patient_id")
    if not r_id:
        navigate("patients")
        
    try:
        record = database.get_clinical_record(r_id)
        patient = database.get_patient(record['patient_id'])
        result = database.get_extraction_result(r_id)
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
        
    # Metadata and Source Traceability
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

# ---------------------------------------------------------
# SCREEN 7 - EXTRACTIONS MODULE
# ---------------------------------------------------------
def show_extractions():
    st.markdown("<div class='brand-subtitle'>EXTRACTIONS</div>", unsafe_allow_html=True)
    st.markdown("## System Extraction Log")
    
    try:
        conn = database.get_connection()
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
                st.session_state["selected_patient_id"] = database.get_clinical_record(ex['rec_id'])['patient_id']
                navigate("results")

# ---------------------------------------------------------
# MAIN ROUTING
# ---------------------------------------------------------
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
