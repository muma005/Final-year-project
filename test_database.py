import unittest
import os
import sqlite3
import database
from unittest.mock import patch, MagicMock
from extraction import extract_clinical_information

class TestDatabaseIntegration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        # Use an in-memory database for testing or a separate test db file
        database.DB_PATH = "test_clinical_extraction.db"
    
    def setUp(self):
        # Ensure clean state before each test
        if os.path.exists(database.DB_PATH):
            os.remove(database.DB_PATH)
        database.initialize_database()
        
    def tearDown(self):
        # Cleanup after each test
        if os.path.exists(database.DB_PATH):
            try:
                os.remove(database.DB_PATH)
            except PermissionError:
                pass

    def test_1_database_initialization(self):
        """Test 1 — Database initialization: Verify that the three tables exist."""
        conn = sqlite3.connect(database.DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = {row[0] for row in cursor.fetchall()}
        
        self.assertIn('Patients', tables)
        self.assertIn('ClinicalRecords', tables)
        self.assertIn('ExtractionResults', tables)
        conn.close()

    def test_2_patient_creation(self):
        """Test 2 — Patient creation: Create a patient and verify that it can be retrieved."""
        patient_id = database.create_patient("P100", "Test Patient", "1990-01-01", "Female")
        patient = database.get_patient(patient_id)
        
        self.assertIsNotNone(patient)
        self.assertEqual(patient["patient_code"], "P100")
        self.assertEqual(patient["name"], "Test Patient")
        
        patients = database.get_patients()
        self.assertEqual(len(patients), 1)

    def test_3_clinical_record(self):
        """Test 3 — Clinical record: Create a clinical record linked to a patient and verify that it can be retrieved."""
        patient_id = database.create_patient("P101", "Test Patient 2", "1980-05-15", "Male")
        
        record_id = database.create_clinical_record(
            patient_id, "2026-08-01", "Note", "Patient complains of headache."
        )
        
        record = database.get_clinical_record(record_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["patient_id"], patient_id)
        self.assertEqual(record["clinical_note"], "Patient complains of headache.")

    def test_4_patient_records(self):
        """Test 4 — Patient records: Verify that selecting a patient returns only that patient's records."""
        # Create two patients
        p1_id = database.create_patient("P1", "Pat 1", "2000-01-01", "Male")
        p2_id = database.create_patient("P2", "Pat 2", "2000-01-01", "Female")
        
        # Add 2 records to P1, 1 record to P2
        database.create_clinical_record(p1_id, "2026-08-01", "Note", "P1 Note 1")
        database.create_clinical_record(p1_id, "2026-08-02", "Note", "P1 Note 2")
        database.create_clinical_record(p2_id, "2026-08-03", "Note", "P2 Note 1")
        
        p1_records = database.get_patient_records(p1_id)
        p2_records = database.get_patient_records(p2_id)
        
        self.assertEqual(len(p1_records), 2)
        self.assertEqual(len(p2_records), 1)
        self.assertEqual(p1_records[0]["patient_id"], p1_id)
        self.assertEqual(p2_records[0]["patient_id"], p2_id)

    @patch('extraction.get_deepseek_client')
    def test_5_extraction_integration(self, mock_get_client):
        """Test 5 — Extraction integration: Retrieve a clinical note from the database and pass it to extract_clinical_information()."""
        # Setup mock for Part 1
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": ["Headache"],
          "medication_changes": [],
          "allergies": [],
          "abnormal_findings": [],
          "follow_up_instructions": []
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        # Database setup
        p_id = database.create_patient("P1", "Pat 1", "2000-01-01", "Male")
        r_id = database.create_clinical_record(p_id, "2026-08-01", "Note", "Patient has a headache.")
        
        # Integration logic
        record = database.get_clinical_record(r_id)
        note = record["clinical_note"]
        
        # Call existing Part 1
        result = extract_clinical_information(note)
        
        self.assertEqual(result["diagnoses"], ["Headache"])
        self.assertEqual(result["medication_changes"], [])

    def test_6_save_extraction(self):
        """Test 6 — Save extraction: Save the result to ExtractionResults. Verify that it can be retrieved."""
        p_id = database.create_patient("P1", "Pat 1", "2000-01-01", "Male")
        r_id = database.create_clinical_record(p_id, "2026-08-01", "Note", "Test note.")
        
        # Synthetic result matching Part 1 schema
        mock_result = {
            "diagnoses": ["Hypertension"],
            "medication_changes": ["Amlodipine started"],
            "allergies": [],
            "abnormal_findings": ["BP 160/95"],
            "follow_up_instructions": ["Return in 2 weeks"]
        }
        
        extraction_id = database.save_extraction_result(r_id, mock_result)
        
        # Retrieve it back
        saved_result = database.get_extraction_result(r_id)
        
        self.assertIsNotNone(saved_result)
        self.assertEqual(saved_result["record_id"], r_id)
        self.assertEqual(saved_result["diagnoses"], ["Hypertension"])
        self.assertEqual(saved_result["medication_changes"], ["Amlodipine started"])
        self.assertEqual(saved_result["allergies"], [])
        self.assertEqual(saved_result["abnormal_findings"], ["BP 160/95"])
        self.assertEqual(saved_result["follow_up_instructions"], ["Return in 2 weeks"])

if __name__ == '__main__':
    unittest.main()
