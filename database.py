import sqlite3
import json
import datetime
import os

DB_PATH = "clinical_extraction.db"

def get_connection():
    return sqlite3.connect(DB_PATH)

def initialize_database():
    """Initializes the SQLite database with the three required tables."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Create Patients table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS Patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            date_of_birth TEXT NOT NULL,
            gender TEXT NOT NULL
        )
    ''')
    
    # Create ClinicalRecords table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ClinicalRecords (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER NOT NULL,
            record_date TEXT NOT NULL,
            record_type TEXT NOT NULL,
            clinical_note TEXT NOT NULL,
            FOREIGN KEY (patient_id) REFERENCES Patients(id)
        )
    ''')
    
    # Create ExtractionResults table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ExtractionResults (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            diagnoses TEXT NOT NULL,
            medication_changes TEXT NOT NULL,
            allergies TEXT NOT NULL,
            abnormal_findings TEXT NOT NULL,
            follow_up_instructions TEXT NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (record_id) REFERENCES ClinicalRecords(id)
        )
    ''')
    
    conn.commit()
    conn.close()

# --- PATIENTS ---
def create_patient(patient_code, name, date_of_birth, gender):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO Patients (patient_code, name, date_of_birth, gender)
        VALUES (?, ?, ?, ?)
    ''', (patient_code, name, date_of_birth, gender))
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

# --- CLINICAL RECORDS ---
def create_clinical_record(patient_id, record_date, record_type, clinical_note):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO ClinicalRecords (patient_id, record_date, record_type, clinical_note)
        VALUES (?, ?, ?, ?)
    ''', (patient_id, record_date, record_type, clinical_note))
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

# --- EXTRACTION RESULTS ---
def save_extraction_result(record_id, result_dict):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Convert lists to JSON strings for storage
    diagnoses = json.dumps(result_dict.get("diagnoses", []))
    medication_changes = json.dumps(result_dict.get("medication_changes", []))
    allergies = json.dumps(result_dict.get("allergies", []))
    abnormal_findings = json.dumps(result_dict.get("abnormal_findings", []))
    follow_up_instructions = json.dumps(result_dict.get("follow_up_instructions", []))
    created_at = datetime.datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO ExtractionResults (
            record_id, diagnoses, medication_changes, allergies, 
            abnormal_findings, follow_up_instructions, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (
        record_id, diagnoses, medication_changes, allergies, 
        abnormal_findings, follow_up_instructions, created_at
    ))
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
    # Parse JSON strings back to lists
    result["diagnoses"] = json.loads(result["diagnoses"])
    result["medication_changes"] = json.loads(result["medication_changes"])
    result["allergies"] = json.loads(result["allergies"])
    result["abnormal_findings"] = json.loads(result["abnormal_findings"])
    result["follow_up_instructions"] = json.loads(result["follow_up_instructions"])
    
    return result
