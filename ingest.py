import os
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_google_genai import GoogleGenerativeAIEmbeddings

# Load environment variables
load_dotenv()

def ingest_docs():
    # 1. Define the PDF files and their metadata
    pdf_configs = [
        {"path": "data/UG-Prospectus-2022.pdf",          "dept": "ALL", "type": "prospectus"},
        {"path": "data/CS_Department_Catalog.pdf",        "dept": "CS",  "type": "course_catalog"},
        {"path": "data/EE_Department_Catalog.pdf",        "dept": "EE",  "type": "course_catalog"},
        {"path": "data/BBA_Department_Catalog (1).pdf",   "dept": "BBA", "type": "course_catalog"},
        {"path": "data/University_Academic_Policies.pdf", "dept": "ALL", "type": "academic_policy"},
        {"path": "data/Faculty_Directory.pdf",            "dept": "ALL", "type": "faculty_directory"},
    ]

    all_docs = []
    
    print("--- Phase 1: Loading PDFs ---")
    for config in pdf_configs:
        if not os.path.exists(config["path"]):
            print(f"Warning: File not found {config['path']}")
            continue
            
        print(f"Loading: {config['path']}...")
        loader = PyPDFLoader(config["path"])
        docs = loader.load()
        
        # Add metadata to each page document
        for doc in docs:
            doc.metadata.update({
                "department": config["dept"],
                "doc_type": config["type"],
                "source": os.path.basename(config["path"])
            })
        all_docs.extend(docs)

    # 2. Smart Chunking Strategy
    print("\n--- Phase 2: Splitting into chunks ---")
    # chunk_size=800 is large enough for a full course description
    # separators hierarchy: paragraph -> sentence -> word
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = text_splitter.split_documents(all_docs)
    print(f"Created {len(chunks)} chunks from {len(all_docs)} pages.")

    # 3. Create Vector Store
    print("\n--- Phase 3: Building Vector Store (ChromaDB) ---")
    embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
    
    # Persist directory for the vector store
    persist_dir = "./chroma_db"
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=persist_dir,
        collection_name="university_catalog"
    )
    
    print(f"Success! Vector store created and saved to '{persist_dir}'.")

if __name__ == "__main__":
    ingest_docs()
