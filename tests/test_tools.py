from tools import retrieve_documents

print("--- Testing Tool: retrieve_documents ---")
query = "What computer science courses are offered?"
results = retrieve_documents.invoke({"query": query, "k": 2})

for i, res in enumerate(results):
    print(f"\nResult {i+1} (Source: {res['metadata']['source']}):")
    print(f"Content snippet: {res['content'][:100]}...")

print("\n--- Tool Test Complete ---")
