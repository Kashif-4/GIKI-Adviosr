from graph import app

queries = [
    "Hello! How are you?",
    "What computer science courses are available?"
]

for q in queries:
    print(f"\n>>> TESTING QUERY: {q}")
    inputs = {"query": q, "retry_count": 0, "relevant_docs": [], "used_web_search": False}
    result = app.invoke(inputs)
    
    answer = result.get("final_answer") or result.get("generation")
    print(f"\n>>> FINAL AGENT RESPONSE: {answer}")
    print("-" * 50)
