import os
import json
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from dotenv import load_dotenv

load_dotenv()

# We need the API key from environment
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize client
client = genai.Client(api_key=GEMINI_API_KEY)

class LLMServiceError(Exception):
    pass

@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type(Exception), 
    reraise=True
)
def generate_product_metadata(raw_name: str) -> dict:
    """
    Calls Google Gemini API to generate SEO description and category tags for a given product name.
    Expects a JSON response.
    """
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not set.")

    prompt = f"""
    You are an e-commerce data enrichment assistant.
    Given the raw product name: "{raw_name}"
    
    1. Write a catchy, SEO-optimized product description (2-3 sentences).
    2. Suggest 3-5 category tags for this product.

    Return the result strictly as a JSON object with the following keys:
    - "seo_description": string
    - "category_tags": a comma-separated string of tags
    """

    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
            ),
        )
        result = json.loads(response.text)
        return result
    except json.JSONDecodeError as e:
        raise LLMServiceError(f"Failed to parse JSON response from LLM: {e}")
    except Exception as e:
        raise Exception(f"Error calling Gemini API: {e}") # Let tenacity catch and retry
