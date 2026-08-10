import os
import json
from pydantic import BaseModel, ValidationError, Field
from typing import List
from openai import OpenAI

# Define the exact output schema using Pydantic
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
    
    # Configure OpenAI client for DeepSeek API
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com"
    )

def extract_clinical_information(clinical_note: str) -> dict:
    """
    Extracts structured clinical information from a raw clinical note using the DeepSeek API.
    
    Args:
        clinical_note (str): The raw text of the clinical note.
        
    Returns:
        dict: A dictionary containing the structured extraction strictly following the required schema.
    """
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
        # Pydantic schema generation for JSON structured outputs (OpenAI structured outputs approach)
        # However, for broader compatibility with DeepSeek without assuming native structured output support, 
        # we ask for JSON in the prompt and use deepseek-chat.
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
        
        # Parse and validate the response
        parsed_data = json.loads(raw_json_str)
        validated_data = ClinicalInformation(**parsed_data)
        
        return validated_data.model_dump()
        
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Failed to parse JSON response from API: {e}")
    except ValidationError as e:
        raise RuntimeError(f"API response failed schema validation: {e}")
    except Exception as e:
        raise RuntimeError(f"An error occurred during extraction: {e}")
