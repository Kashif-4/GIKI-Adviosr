from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

try:
    print("Testing NEW google-genai Library...")
    response = client.models.generate_content(
        model='gemini-1.5-flash',
        contents='Hi'
    )
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
