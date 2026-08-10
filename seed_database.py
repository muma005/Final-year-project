import database
import os

def reset_and_seed():
    db_path = database.DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)
    
    database.initialize_database()
    print("Database initialized.")

    # Synthetic Patients
    patients = [
        ("P001", "John Kamau", "1985-04-12", "Male"),
        ("P002", "Mary Wanjiku", "1992-08-24", "Female"),
        ("P003", "Peter Otieno", "1978-11-05", "Male"),
        ("P004", "Amina Hassan", "1989-02-17", "Female"),
        ("P005", "Daniel Mwangi", "1965-09-30", "Male"),
        ("P006", "Grace Njeri", "1995-12-11", "Female"),
        ("P007", "Brian Ochieng", "1982-07-22", "Male"),
        ("P008", "Faith Wambui", "2001-03-08", "Female")
    ]
    
    p_ids = []
    for p in patients:
        p_ids.append(database.create_patient(p[0], p[1], p[2], p[3]))
        
    print(f"Seeded {len(patients)} synthetic patients.")

    # Clinical Scenarios
    
    # Scenario A: Respiratory Complaint (Primary Demo - John Kamau)
    note_a = """Patient presented with a persistent cough for approximately two weeks accompanied by intermittent fever. 
The patient reports increased fatigue and mild shortness of breath. On examination, temperature was elevated (38.8°C) and respiratory examination revealed abnormal breath sounds with mild wheezing in the lower lobes. 
The clinician assessed the patient with an acute lower respiratory tract infection. 
Initiated Amoxicillin 500mg TDS for 7 days and Salbutamol inhaler PRN.
Follow-up was recommended after seven days, or sooner if symptoms worsen."""
    
    # Scenario B: Medication / Chronic Condition (Mary Wanjiku)
    note_b = """Routine review for Type 2 Diabetes Mellitus and Hypertension.
Patient reports feeling generally well, though home blood glucose readings have been running slightly high in the mornings.
Current medications: Metformin 1g BD, Amlodipine 5mg OD.
Blood pressure today is 145/90 mmHg. HbA1c is 8.2%.
Assessment: Suboptimal glycemic control and mildly elevated blood pressure.
Plan: Increase Amlodipine to 10mg OD. Continue Metformin. 
Review in 1 month with fasting lipid profile."""
    
    # Scenario C: Allergy / Adverse Reaction (Peter Otieno)
    note_c = """Urgent consultation. Patient presents with an erythematous, highly pruritic maculopapular rash across the torso and arms.
Symptoms began 24 hours after starting Cephalexin for a skin infection.
No respiratory distress, wheezing, or facial swelling. Heart rate is 92 bpm, BP 120/80.
Assessment: Allergic reaction to Cephalexin (delayed hypersensitivity).
Plan: Discontinue Cephalexin immediately. Patient is instructed to avoid all Cephalosporins in the future (Allergy added to file).
Prescribed Loratadine 10mg OD for 5 days. Substituted antibiotic with Azithromycin 500mg for 3 days.
Advised to return immediately if any difficulty breathing occurs."""
    
    # Scenario D: Follow-up / Investigation (Amina Hassan)
    note_d = """Follow-up visit to review recent abdominal ultrasound and blood work for right upper quadrant pain.
Ultrasound shows multiple mobile gallstones without gallbladder wall thickening. CBD is clear.
Liver function tests: ALT 45 U/L (mildly elevated), AST 32 U/L, Bilirubin normal.
Diagnosis: Symptomatic cholelithiasis.
Patient is currently managing pain with over-the-counter Paracetamol.
Plan: Referred to general surgery for elective laparoscopic cholecystectomy.
Advised to stick to a low-fat diet. Review in surgical outpatient clinic."""

    # Assign records
    database.create_clinical_record(p_ids[0], "2026-08-01", "Consultation", note_a) # P001 John Kamau
    database.create_clinical_record(p_ids[0], "2026-06-15", "Follow-up", "Routine checkup. No acute issues. Vitals stable.")
    
    database.create_clinical_record(p_ids[1], "2026-07-28", "Chronic Review", note_b) # P002 Mary Wanjiku
    
    database.create_clinical_record(p_ids[2], "2026-07-30", "Urgent Care", note_c) # P003 Peter Otieno
    database.create_clinical_record(p_ids[2], "2026-07-28", "Consultation", "Presented with cellulitis on left calf. Prescribed Cephalexin 500mg QID.")
    
    database.create_clinical_record(p_ids[3], "2026-08-05", "Results Review", note_d) # P004 Amina Hassan
    
    # Add dummy records for the rest so they aren't empty
    database.create_clinical_record(p_ids[4], "2026-05-11", "Consultation", "Patient complains of lower back pain after lifting heavy boxes. Prescribed Ibuprofen. Rest recommended.")
    database.create_clinical_record(p_ids[5], "2026-07-10", "Follow-up", "Blood pressure checks normal. Continue current regimen.")
    database.create_clinical_record(p_ids[6], "2026-08-08", "Consultation", "Mild tension headache. No red flags. Hydration and rest advised.")
    database.create_clinical_record(p_ids[7], "2026-02-22", "Consultation", "Annual physical. All systems normal.")

    print("Seeded clinical records.")
    print("Database seeding complete and presentation ready.")

if __name__ == "__main__":
    reset_and_seed()
