from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

try:
    print("Testing 2.0-flash with NEW library...")
    response = client.models.generate_content(
        model='gemini-2.0-flash',
        contents='Hi'
    )
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
