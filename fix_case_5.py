from graph import app

query = "Who is the contact for CS courses and what is the late withdrawal policy?"
print(f"\n>>> RUNNING FINAL MISSING TEST CASE: {query}")

inputs = {"query": query, "retry_count": 0, "relevant_docs": [], "used_web_search": False}
try:
    result = app.invoke(inputs)
    answer = result.get("final_answer") or result.get("generation")
    print(f"\n>>> FINAL RESPONSE:\n{answer}")
    
    # Append to evaluation_results.md
    with open("evaluation_results.md", "a") as f:
        f.write(f"## Test Case 5: Complex University Query (MANUAL RE-RUN)\n")
        f.write(f"**Query:** {query}\n\n")
        f.write(f"### Actual Behavior\n")
        f.write(f"- **Needs Retrieval:** {result.get('needs_retrieval')}\n")
        f.write(f"- **Relevant Docs Found:** {len(result.get('relevant_docs', []))}\n")
        f.write(f"### Final Agent Response\n")
        f.write(f"> {answer}\n\n---\n")
except Exception as e:
    print(f"FAILED AGAIN: {e}")
