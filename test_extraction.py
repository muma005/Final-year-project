import unittest
from unittest.mock import patch, MagicMock
from extraction import extract_clinical_information

class TestClinicalInformationExtraction(unittest.TestCase):
    
    @patch('extraction.get_deepseek_client')
    def test_all_five_categories(self, mock_get_client):
        # Setup mock
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": ["Acute respiratory infection"],
          "medication_changes": ["Amoxicillin 500mg — initiated"],
          "allergies": ["Penicillin"],
          "abnormal_findings": ["Temperature: 38.5°C"],
          "follow_up_instructions": ["Follow-up after seven days"]
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = """
        Patient presented with a persistent cough for two weeks.
        Temperature was 38.5°C. The patient was diagnosed with an
        acute respiratory infection. Amoxicillin 500mg was initiated.
        The patient reports a penicillin allergy. Follow-up was
        recommended after seven days.
        """
        
        result = extract_clinical_information(note)
        
        self.assertEqual(len(result["diagnoses"]), 1)
        self.assertEqual(len(result["medication_changes"]), 1)
        self.assertEqual(len(result["allergies"]), 1)
        self.assertEqual(len(result["abnormal_findings"]), 1)
        self.assertEqual(len(result["follow_up_instructions"]), 1)

    @patch('extraction.get_deepseek_client')
    def test_some_categories(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": ["Hypertension"],
          "medication_changes": [],
          "allergies": [],
          "abnormal_findings": ["Blood pressure 150/90"],
          "follow_up_instructions": []
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = "Patient has hypertension. BP today was 150/90."
        result = extract_clinical_information(note)
        
        self.assertEqual(result["diagnoses"], ["Hypertension"])
        self.assertEqual(result["abnormal_findings"], ["Blood pressure 150/90"])
        self.assertEqual(result["medication_changes"], [])
        self.assertEqual(result["allergies"], [])
        self.assertEqual(result["follow_up_instructions"], [])

    @patch('extraction.get_deepseek_client')
    def test_no_extractable_information(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": [],
          "medication_changes": [],
          "allergies": [],
          "abnormal_findings": [],
          "follow_up_instructions": []
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = "The patient arrived on time for their appointment and felt fine."
        result = extract_clinical_information(note)
        
        for key in ["diagnoses", "medication_changes", "allergies", "abnormal_findings", "follow_up_instructions"]:
            self.assertEqual(result[key], [])

    @patch('extraction.get_deepseek_client')
    def test_medication_mention_without_change(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": [],
          "medication_changes": [],
          "allergies": [],
          "abnormal_findings": [],
          "follow_up_instructions": []
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = "Patient continues taking their daily Aspirin 81mg as previously prescribed."
        result = extract_clinical_information(note)
        
        self.assertEqual(result["medication_changes"], [])

    @patch('extraction.get_deepseek_client')
    def test_malformed_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        # Invalid JSON (missing closing brace)
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": ["Hypertension"]
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = "Test note."
        with self.assertRaises(RuntimeError) as context:
            extract_clinical_information(note)
        
        self.assertIn("Failed to parse JSON response", str(context.exception))

    @patch('extraction.get_deepseek_client')
    def test_schema_violation_response(self, mock_get_client):
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client
        mock_response = MagicMock()
        # Valid JSON but missing required fields or having wrong types
        mock_response.choices[0].message.content = '''
        {
          "diagnoses": "Hypertension", 
          "allergies": []
        }
        '''
        mock_client.chat.completions.create.return_value = mock_response
        
        note = "Test note."
        with self.assertRaises(RuntimeError) as context:
            extract_clinical_information(note)
            
        self.assertIn("API response failed schema validation", str(context.exception))

if __name__ == '__main__':
    unittest.main()
