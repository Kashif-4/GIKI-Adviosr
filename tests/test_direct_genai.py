import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

model = genai.GenerativeModel('gemini-1.5-flash')
try:
    print("Testing Direct GenAI Library...")
    response = model.generate_content("Hi")
    print(f"SUCCESS: {response.text}")
except Exception as e:
    print(f"FAILED: {e}")
