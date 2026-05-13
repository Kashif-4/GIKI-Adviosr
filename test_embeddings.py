from langchain_google_genai import GoogleGenerativeAIEmbeddings
import os
from dotenv import load_dotenv

load_dotenv()

models_to_test = [
    "models/text-embedding-004",
    "text-embedding-004",
    "models/embedding-001",
    "embedding-001",
    "models/gemini-embedding-001"
]

for m in models_to_test:
    try:
        print(f"Testing {m}...")
        embeddings = GoogleGenerativeAIEmbeddings(model=m)
        embeddings.embed_query("test")
        print(f"SUCCESS: {m} works!")
        break
    except Exception as e:
        print(f"FAILED: {m} - {str(e)[:100]}")
