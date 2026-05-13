import os
from typing import List, Dict, Any
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import tool
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.tools.tavily_search import TavilySearchResults

# Load environment variables
load_dotenv()

# Setup Embeddings (must match ingest.py)
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# Initialize ChromaDB connection (read-only)
vectorstore = Chroma(
    persist_directory="./chroma_db",
    embedding_function=embeddings,
    collection_name="university_catalog"
)

# --- Pydantic Schemas for Tool Validation ---

class RetrieveInput(BaseModel):
    query: str = Field(description="The user's query to search the university knowledge base")
    k: int = Field(default=4, description="Number of document chunks to retrieve")

class WebSearchInput(BaseModel):
    query: str = Field(description="The search query to run on the web when knowledge base fails")

# --- Tool Definitions ---

@tool("retrieve_documents", args_schema=RetrieveInput)
def retrieve_documents(query: str, k: int = 4) -> List[Dict[str, Any]]:
    """
    Searches the university catalog vector database for documents 
    relevant to the given query. Returns content and metadata (source, department, page).
    Use this for any questions about courses, policies, faculty, or fees.
    """
    results = vectorstore.similarity_search(query, k=k)
    
    serialized_results = []
    for doc in results:
        serialized_results.append({
            "content": doc.page_content,
            "metadata": doc.metadata
        })
    return serialized_results

@tool("web_search", args_schema=WebSearchInput)
def web_search(query: str) -> str:
    """
    Performs a web search using Tavily to find information not present 
    in the university catalog. Use this as a fallback only when 
    knowledge base results are irrelevant.
    """
    search = TavilySearchResults(max_results=3)
    results = search.invoke(query)
    
    # Format the results into a readable string
    if isinstance(results, list):
        formatted_results = "\n\n".join([
            f"Source: {res.get('url', 'Unknown')}\nContent: {res.get('content', str(res))}" 
            if isinstance(res, dict) else str(res)
            for res in results
        ])
    else:
        formatted_results = str(results)
        
    return formatted_results
