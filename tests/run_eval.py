import json
from graph import app

test_cases = [
    {
        "id": 1,
        "name": "No Retrieval Needed",
        "query": "Hi! What does GPA stand for?",
        "expected": "Adaptive retrieval should skip the vector store."
    },
    {
        "id": 2,
        "name": "Retrieval & Relevant",
        "query": "What are the prerequisites for CS-102?",
        "expected": "Retrieval should find CS-102 and confirm CS-101 as prerequisite."
    },
    {
        "id": 3,
        "name": "Retrieval & Irrelevant (Web Fallback)",
        "query": "What is the capital of France?",
        "expected": "Retrieval will fail (irrelevant docs) and trigger web search."
    },
    {
        "id": 4,
        "name": "Hallucination Check & Correction",
        "query": "Tell me about the Quantum Physics Lab fee of 5000 dollars.",
        "expected": "If context doesn't mention 5000, agent should check grounding."
    },
    {
        "id": 5,
        "name": "Complex University Query",
        "query": "Who is the contact for CS courses and what is the late withdrawal policy?",
        "expected": "Should retrieve from both Faculty Directory and Academic Policies."
    }
]

def run_evaluation():
    with open("evaluation_results.md", "w") as f:
        f.write("# Self-RAG Agent Evaluation Results\n\n")
        
        for case in test_cases:
            import time
            time.sleep(3)
            print(f"\n--- Running Test Case {case['id']}: {case['name']} ---")
            f.write(f"## Test Case {case['id']}: {case['name']}\n")
            f.write(f"**Query:** {case['query']}\n\n")
            f.write(f"**Expected Behavior:** {case['expected']}\n\n")
            
            try:
                # Run the agent
                inputs = {"query": case['query'], "retry_count": 0, "relevant_docs": [], "used_web_search": False}
                result = app.invoke(inputs)
                
                # Format results
                answer = result.get("final_answer") or result.get("generation")
                
                f.write("### Actual Behavior (Execution Trace Highlights)\n")
                f.write(f"- **Needs Retrieval:** {result.get('needs_retrieval')}\n")
                f.write(f"- **Used Web Search:** {result.get('used_web_search', False)}\n")
                f.write(f"- **Relevant Docs Found:** {len(result.get('relevant_docs', []))}\n")
                f.write(f"- **Hallucination Check Passed:** {not result.get('hallucination_flag', False)}\n\n")
                
                f.write("### Final Agent Response\n")
                f.write(f"> {answer}\n\n")
            except Exception as e:
                f.write(f"### ERROR during test execution\n")
                f.write(f"```\n{str(e)}\n```\n\n")
                
            f.write("---\n\n")
            
    print("\nEvaluation complete! results saved to evaluation_results.md")

if __name__ == "__main__":
    run_evaluation()
