import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

client = genai.Client(api_key=api_key)

try:
    print("Available Models:")
    models = client.models.list()
    for m in models:
        print(m.name)
except Exception as e:
    print(f"FAILED: {e}")
