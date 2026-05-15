import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI

load_dotenv()
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash")

try:
    print("Testing Gemini Connection...")
    response = llm.invoke("Say 'Connection Successful'")
    print(f"Result: {response.content}")
except Exception as e:
    print(f"Connection Failed: {e}")
