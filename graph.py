import json
import operator
from typing import Annotated, Dict, List, TypedDict, Union

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from tools import retrieve_documents, web_search

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

# --- State Definition ---

class AgentState(TypedDict):
    query: str
    needs_retrieval: bool
    retrieval_reason: str
    retrieved_docs: List[Dict]
    relevant_docs: List[Dict]
    used_web_search: bool
    web_results: str
    generation: str
    hallucination_flag: bool
    hallucination_explanation: str
    retry_count: int
    final_answer: str

# --- Node Functions ---

def adaptive_retrieval_node(state: AgentState):
    """Decides if the query needs retrieval or can be answered directly."""
    print(f"\n[TRACE] Node: Adaptive Retrieval")
    query = state["query"]
    
    prompt = f"""You are a routing assistant for a University Course Advisory Agent.
    Decide if this query needs retrieval from the university catalog or if it's general/conversational.
    
    Categories that do NOT need retrieval:
    - Greetings ("hi", "hello")
    - General academic knowledge ("What does GPA stand for?", "What is a credit hour?")
    - Small talk
    
    Categories that DO need retrieval:
    - Specific course names, codes, or prerequisites
    - Semester schedules, fees, grading policies
    - Faculty names, offices, or specializations
    
    Query: {query}
    
    Return JSON: {{"needs_retrieval": true/false, "reason": "short explanation"}}"""
    
    response = llm.invoke(prompt)
    content = response.content
    
    # Handle structured content if present
    if isinstance(content, list):
        content = content[0].get("text", str(content))
    
    try:
        # Clean potential markdown from response
        clean_content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_content)
    except:
        # Strict fallback: if we can't parse, check if keywords exist
        if "true" in content.lower():
            result = {"needs_retrieval": True, "reason": "Keyword trigger"}
        else:
            result = {"needs_retrieval": False, "reason": "General query fallback"}
    
    print(f"[TRACE] Decision: {'Retrieval Needed' if result['needs_retrieval'] else 'Direct Answer'}")
    print(f"[TRACE] Reason: {result['reason']}")
    
    return {
        "needs_retrieval": result["needs_retrieval"],
        "retrieval_reason": result["reason"]
    }

def retrieve_node(state: AgentState):
    """Retrieves documents from the vector store."""
    print(f"\n[TRACE] Node: Retrieve")
    docs = retrieve_documents.invoke({"query": state["query"], "k": 4})
    print(f"[TRACE] Retrieved {len(docs)} documents.")
    return {"retrieved_docs": docs}

def direct_answer_node(state: AgentState):
    """Answers general questions directly without retrieval."""
    print(f"\n[TRACE] Node: Direct Answer")
    prompt = f"Answer this general query concisely using your own knowledge: {state['query']}"
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0].get("text", str(content))
    if not content:
        content = "I'm sorry, I don't have an answer for that."
    return {"final_answer": content}

def relevance_grading_node(state: AgentState):
    """Grades retrieved documents for relevance to the query."""
    print(f"\n[TRACE] Node: Relevance Grading")
    query = state["query"]
    docs = state["retrieved_docs"]
    relevant_docs = []
    
    doc_texts = "\n\n".join([f"Doc {i+1}: {doc.get('content', '')}" for i, doc in enumerate(docs)])
    
    prompt = f"""Evaluate the following document snippets for relevance to the user query.
    Query: {query}
    
    Documents:
    {doc_texts}
    
    Return JSON format: {{"relevant_indices": [1, 3]}} (list indices of relevant docs, 1-based)"""
    
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0].get("text", str(content))
        
    try:
        clean_content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_content)
        indices = result.get("relevant_indices", [])
        for idx in indices:
            if 1 <= idx <= len(docs):
                relevant_docs.append(docs[idx-1])
                source = docs[idx-1].get('metadata', {}).get('source', 'Unknown')
                print(f"[TRACE] Doc {idx} from {source}: RELEVANT")
    except Exception as e:
        print(f"[TRACE] Relevance grading failed ({e}), falling back to all docs.")
        relevant_docs = docs
            
    return {"relevant_docs": relevant_docs}

def web_search_node(state: AgentState):
    """Falls back to web search if no relevant documents found."""
    print(f"\n[TRACE] Node: Web Search Fallback")
    results = web_search.invoke({"query": state["query"]})
    print(f"[TRACE] Web search results obtained.")
    return {"web_results": results, "used_web_search": True}

def generate_node(state: AgentState):
    """Generates an answer based on the retrieved context or web results."""
    print(f"\n[TRACE] Node: Generate (Attempt {state.get('retry_count', 0) + 1})")
    
    if state.get("used_web_search", False):
        context = state["web_results"]
    else:
        context = "\n\n".join([d.get('content', '') for d in state["relevant_docs"]])
    
    prompt = f"""You are a University Course Advisory Agent. 
    Answer the query ONLY using the provided context. If the answer is not in the context, say you don't know.
    
    Context: {context}
    Query: {state['query']}
    
    Answer:"""
    
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0].get("text", str(content))
        
    return {
        "generation": content,
        "retry_count": state.get("retry_count", 0) + 1
    }

def hallucination_check_node(state: AgentState):
    """Checks if the generation is grounded in the provided context."""
    print(f"\n[TRACE] Node: Hallucination Check")
    
    if state.get("used_web_search", False):
        context = state["web_results"]
    else:
        context = "\n\n".join([d.get('content', '') for d in state["relevant_docs"]])
        
    prompt = f"""Does the following generated answer contain claims NOT supported by the context?
    
    Context: {context}
    Answer: {state['generation']}
    
    Return JSON: {{"hallucination": true/false, "explanation": "..."}}"""
    
    response = llm.invoke(prompt)
    content = response.content
    if isinstance(content, list):
        content = content[0].get("text", str(content))
        
    try:
        clean_content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_content)
    except Exception as e:
        result = {"hallucination": False, "explanation": f"Check failed: {str(e)}"}
        
    print(f"[TRACE] Hallucination detected: {result.get('hallucination', False)}")
    
    return {
        "hallucination_flag": result.get("hallucination", False),
        "hallucination_explanation": result.get("explanation", "No explanation provided.")
    }

# --- Routing Functions ---

def route_after_retrieval_decision(state: AgentState):
    if state["needs_retrieval"]:
        return "retrieve"
    return "direct_answer"

def route_after_grading(state: AgentState):
    if not state["relevant_docs"]:
        return "web_search"
    return "generate"

def route_after_hallucination_check(state: AgentState):
    if not state["hallucination_flag"]:
        return "finish"
    if state["retry_count"] >= 3:
        return "max_retries"
    return "generate"

# --- Graph Construction ---

workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("adaptive_retrieval", adaptive_retrieval_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("direct_answer", direct_answer_node)
workflow.add_node("relevance_grading", relevance_grading_node)
workflow.add_node("web_search", web_search_node)
workflow.add_node("generate", generate_node)
workflow.add_node("hallucination_check", hallucination_check_node)

# Set Entry Point
workflow.set_entry_point("adaptive_retrieval")

# Add Edges
workflow.add_conditional_edges(
    "adaptive_retrieval",
    route_after_retrieval_decision,
    {"retrieve": "retrieve", "direct_answer": "direct_answer"}
)

workflow.add_edge("direct_answer", END)
workflow.add_edge("retrieve", "relevance_grading")

workflow.add_conditional_edges(
    "relevance_grading",
    route_after_grading,
    {"web_search": "web_search", "generate": "generate"}
)

workflow.add_edge("web_search", "generate")
workflow.add_edge("generate", "hallucination_check")

workflow.add_conditional_edges(
    "hallucination_check",
    route_after_hallucination_check,
    {
        "generate": "generate", 
        "finish": END,
        "max_retries": END
    }
)

# Compile Graph
app = workflow.compile()
