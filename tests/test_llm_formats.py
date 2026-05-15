from langchain_google_genai import ChatGoogleGenerativeAI
import os
from dotenv import load_dotenv

load_dotenv()

# Test different model string formats and versions
formats = [
    {"model": "gemini-1.5-flash"},
    {"model": "models/gemini-1.5-flash"},
    {"model": "gemini-1.5-flash-latest"},
]

for fmt in formats:
    try:
        print(f"Testing {fmt}...")
        llm = ChatGoogleGenerativeAI(**fmt)
        res = llm.invoke("Hi")
        print(f"SUCCESS: {fmt} -> {res.content}")
        break
    except Exception as e:
        print(f"FAILED: {fmt} -> {str(e)[:150]}")
