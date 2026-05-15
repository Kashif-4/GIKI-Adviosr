from google import genai
import os
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

print("--- Detailed Generation Models ---")
for m in client.models.list():
    if 'generateContent' in m.supported_generation_methods:
        print(f"Name: {m.name} | Version: {m.version} | Description: {m.description[:50]}...")
