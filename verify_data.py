import os
from langchain_community.document_loaders import PyPDFLoader

pdf_configs = [
    "data/CS_Department_Catalog.pdf",
    "data/EE_Department_Catalog.pdf",
    "data/BBA_Department_Catalog (1).pdf",
    "data/University_Academic_Policies.pdf",
    "data/Faculty_Directory.pdf",
]

print("--- Data Density Check ---")
for path in pdf_configs:
    if os.path.exists(path):
        loader = PyPDFLoader(path)
        pages = loader.load()
        text_len = sum(len(p.page_content) for p in pages)
        print(f"File: {os.path.basename(path)} | Pages: {len(pages)} | Characters: {text_len}")
    else:
        print(f"MISSING: {path}")
