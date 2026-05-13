from graph import app

def run_agent():
    print("==================================================")
    print("Welcome to XYZ National University Advisor Agent")
    print("Type 'exit' or 'quit' to end the session.")
    print("==================================================")

    while True:
        query = input("\nYou: ")
        if query.lower() in ["exit", "quit"]:
            break
        
        # Initial state
        inputs = {
            "query": query,
            "retry_count": 0,
            "relevant_docs": [],
            "used_web_search": False
        }
        
        # Run the graph
        final_state = app.invoke(inputs)
        
        # Determine the final output to show
        if "final_answer" in final_state and final_state["final_answer"]:
            answer = final_state["final_answer"]
        elif "generation" in final_state:
            answer = final_state["generation"]
            # Check if we hit max retries with hallucination
            if final_state.get("hallucination_flag", False) and final_state.get("retry_count", 0) >= 3:
                answer = "DISCLAIMER: I could not verify this information after multiple attempts. " + answer
        else:
            answer = "I apologize, but I encountered an error processing your request."

        print(f"\nAgent: {answer}")

if __name__ == "__main__":
    run_agent()
