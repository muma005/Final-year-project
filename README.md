# Clinical Information Extraction Engine

This is Part 1 and Part 2 of the Clinical Information Extraction System final year project. 
It provides a minimal, robust Python module that extracts structured clinical information from raw clinical notes using the DeepSeek API, and stores those results in a local SQLite database.

## Features (Part 1 & 2)
- **Extraction Engine**: Extracts 5 specific categories (diagnoses, medication changes, allergies, abnormal findings, follow-up instructions) using DeepSeek API with strict schema enforcement.
- **Database Storage**: A local SQLite database (`clinical_extraction.db`) storing Patients, Clinical Records, and Extraction Results.
- **Integration**: Fetches notes directly from the database, extracts structured information, and saves the verified JSON output back into the database.

## Installation

1. Create a virtual environment (recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variable Setup

The application uses the DeepSeek API which requires an API key.

1. Rename the `.env.example` file to `.env` or simply set the variable in your environment:
   ```bash
   # On Windows PowerShell:
   $env:DEEPSEEK_API_KEY="your_api_key_here"
   
   # On Linux/macOS:
   export DEEPSEEK_API_KEY="your_api_key_here"
   ```

## Database Setup and Seeding

Run the seed script to initialize the database and populate it with synthetic test data:
```bash
python seed_database.py
```

## Running the Tests

The project includes mocked test suites that do not require an active API key to run.

Run extraction unit tests:
```bash
python -m unittest test_extraction.py
```

Run database integration tests:
```bash
python -m unittest test_database.py
```

## Usage Flow (Integration)
The workflow follows: `Database -> Clinical Note -> Extraction Engine -> Database`

```python
import os
import database
from extraction import extract_clinical_information

# 1. Get patients
patients = database.get_patients()
patient_id = patients[0]['id']

# 2. Get clinical records
records = database.get_patient_records(patient_id)
record = records[0]

# 3. Extract information from the note
# Ensure DEEPSEEK_API_KEY is set in your environment
result = extract_clinical_information(record['clinical_note'])

# 4. Save the extraction result
extraction_id = database.save_extraction_result(record['id'], result)

# 5. Retrieve the saved result
saved_result = database.get_extraction_result(record['id'])
print(saved_result['diagnoses'])
```
