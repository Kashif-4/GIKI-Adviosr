import json
import operator
import re
from typing import Annotated, Dict, List, TypedDict, Union

from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph

from tools import retrieve_documents, web_search
from planner_logic import DegreePlanner

# Load environment variables
load_dotenv()

# Initialize LLM
llm = ChatGoogleGenerativeAI(model="gemini-3.1-flash-lite", temperature=0)

# --- State Definition ---

class AgentState(TypedDict):
    query: str
    needs_retrieval: bool
    requires_planning: bool
    requires_clarification: bool
    student_passed_courses: List[str]
    student_failed_courses: List[str]
    current_semester: str
    degree_program: str
    cgpa: float
    wants_summer: bool
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
    """Supervisor Node: Decides if the query needs planning, retrieval, or direct answer."""
    print(f"\n[TRACE] Node: Adaptive Retrieval (Supervisor)")
    query = state["query"]
    
    # Check if this is a structured input from the interactive UI
    if query.startswith("[PLAN_INPUT]"):
        try:
            # Format: [PLAN_INPUT] {"failed": ["CS112"], "passed": ["CS101"], "sem": "2", "summer": true}
            data_str = query.replace("[PLAN_INPUT]", "").strip()
            data = json.loads(data_str)
            return {
                "requires_planning": True,
                "requires_clarification": False,
                "needs_retrieval": False,
                "student_failed_courses": data.get("failed", []),
                "student_passed_courses": data.get("passed", []),
                "current_semester": str(data.get("sem", "1")),
                "degree_program": data.get("degree", "BSCS"),
                "cgpa": float(data.get("cgpa", 3.0)),
                "wants_summer": data.get("summer", True)
            }
        except Exception as e:
            print(f"[TRACE] Failed to parse PLAN_INPUT: {e}")
            pass
            
    prompt = f"""You are the Supervisor Agent for a University Advisory System.
    Analyze the user's query and classify it into ONE of three categories:
    
    1. PLANNING: The user is explicitly asking to generate a new degree plan, fix a schedule after failing a course, or calculate graduation timelines. Do NOT use this if they are just asking what semester a course is offered or who teaches it.
    2. RETRIEVAL: The user is asking about university policies, fees, specific course contents, who teaches a course, what semester a course is in, or faculty rules.
    3. DIRECT: The user is making small talk (e.g., "hi", "thanks") or asking general knowledge questions that don't require the university catalog.
    
    If the category is PLANNING, check if the user provided all necessary details:
    - Did they mention exactly which courses they failed?
    - Did they mention their current semester?
    - Did they mention if they want summer classes?
    If ANY of this is missing, set "needs_clarification" to true.
    
    Query: {query}
    
    Return JSON format EXACTLY like this:
    {{
        "category": "PLANNING" or "RETRIEVAL" or "DIRECT",
        "reason": "short explanation",
        "needs_clarification": true/false
    }}"""
    
    response = llm.invoke(prompt)
    content = response.content
    
    if isinstance(content, list):
        content = content[0].get("text", str(content))
    
    try:
        clean_content = content.replace("```json", "").replace("```", "").strip()
        result = json.loads(clean_content)
    except:
        result = {
            "category": "RETRIEVAL", 
            "reason": "Fallback to retrieval due to parsing error",
            "needs_clarification": False
        }
        
    cat = result.get("category", "RETRIEVAL")
    needs_retrieval = (cat == "RETRIEVAL")
    requires_planning = (cat == "PLANNING")
    requires_clarification = result.get("needs_clarification", False)
    
    print(f"[TRACE] Category: {cat}")
    print(f"[TRACE] Reason: {result.get('reason', '')}")
    
    return {
        "needs_retrieval": needs_retrieval,
        "requires_planning": requires_planning,
        "requires_clarification": requires_clarification,
        "retrieval_reason": result.get("reason", "")
    }

def clarification_node(state: AgentState):
    """Generates an interactive form/chips response asking for missing details."""
    print(f"\n[TRACE] Node: Clarification")
    
    # We return a specific marker that the frontend can parse to show the interactive UI
    response_text = """I would love to help you build a new degree plan! To make sure it is mathematically correct and follows university policies, I need a few details. 
    
[INTERACTIVE_FORM_TRIGGER]
"""
    return {"final_answer": response_text}

def degree_planner_node(state: AgentState):
    """Executes the constraint logic to generate a degree plan."""
    print(f"\n[TRACE] Node: Degree Planner")
    failed        = list(state.get("student_failed_courses", []))
    passed        = list(state.get("student_passed_courses", []))
    wants_summer  = state.get("wants_summer", True)
    degree        = state.get("degree_program", "BSCS")
    cgpa          = float(state.get("cgpa", 3.0) or 3.0)
    
    try:
        current_sem = int(state.get("current_semester", "1"))
    except (ValueError, TypeError):
        current_sem = 1

    try:
        planner = DegreePlanner(data_path="data/prerequisites.json", degree=degree)

        # --- Resolve course NAMES to course CODES ---
        name_to_code = {
            details["name"].lower(): code
            for code, details in planner.graph.items()
        }

        resolve_notes = []   # Messages shown to the user about resolved names

        def resolve_course(entry: str):
            entry = entry.strip()
            upper = entry.upper()
            # 1. Exact code match
            if upper in planner.graph:
                return upper, None
            # 2. Exact name match
            entry_lower = entry.lower()
            if entry_lower in name_to_code:
                code = name_to_code[entry_lower]
                return code, f"'{entry}' → {code} ({planner.graph[code]['name']})"
            # 3. Weighted fuzzy: score = matched_word_count / max(words_in_query, words_in_name)
            best, best_score = None, 0.0
            words_entry = set(entry_lower.split())
            for name, code in name_to_code.items():
                words_name = set(name.split())
                overlap    = len(words_entry & words_name)
                # Jaccard-like: overlap / union — requires ≥ 50% of query words to match
                score = overlap / max(len(words_entry), len(words_name))
                if score > best_score:
                    best_score = score
                    best = code
            if best and best_score >= 0.4:
                cname = planner.graph[best]['name']
                return best, f"⚠️ '{entry}' not found exactly — matched to **{best}** ({cname}). Please verify this is the correct course."
            # 4. Nothing matched
            return upper, f"❌ '{entry}' could not be matched to any course in {degree} curriculum. Please use the exact course code."

        resolved_failed = []
        for f in failed:
            code, note = resolve_course(f)
            resolved_failed.append(code)
            if note:
                resolve_notes.append(note)

        failed = resolved_failed
        passed = [resolve_course(p)[0] for p in passed] if passed else passed

        # Infer passed courses from current_semester if not explicitly provided
        if not passed:
            for code, details in planner.graph.items():
                if details.get("semester", 99) < current_sem and code not in failed:
                    passed.append(code)

        # Remove failed courses from passed (in case of overlap)
        passed = [c for c in passed if c not in failed]

        print(f"[TRACE] Passed: {passed}, Failed: {failed}, Sem: {current_sem}, CGPA: {cgpa}, Summer: {wants_summer}")

        plan = planner.generate_plan(
            passed_courses=passed,
            failed_courses=failed,
            current_completed_sem=current_sem,
            use_summer=wants_summer,
            cgpa=cgpa
        )


        # --- Build HTML ---
        plan_type  = "Catch-up Plan (with Summer)" if wants_summer else "No-Summer Plan"
        gpa_notice = (
            f"<div class='alert-box probation'>🚨 <strong>Academic Probation Mode:</strong> "
            f"Your CGPA ({cgpa}) is below 2.0. University policy limits you to "
            f"<strong>12 credit hours</strong> per regular semester until your CGPA improves.</div>"
            if cgpa < 2.0 else ""
        )

        # Show course resolution warnings
        notes_html = ""
        if resolve_notes:
            notes_html = "<div class='alert-box info'><strong>📌 Course Resolution:</strong><ul style='margin:6px 0 0 0; padding-left:18px;'>"
            for n in resolve_notes:
                notes_html += f"<li style='font-size:13px; margin-bottom:4px;'>{n}</li>"
            notes_html += "</ul></div>"

        response_text = f"<div class='degree-plan-container'>{gpa_notice}{notes_html}"

        response_text += (
            f"<p>Here is your complete degree roadmap — <strong>{plan_type}</strong> "
            f"starting from <strong>Semester {current_sem + 1}</strong> "
            f"(all courses from previous semesters already accounted for). "
            f"Failed courses are marked <span style='color:#dc2626;'>⚠️ RETAKE</span>.</p>"
        )

        for term in plan:
            courses = term["courses"]
            warning = term.get("warning", "")
            credits = term.get("total_credits", 0)

            header_extra = f" · {credits} CH"
            response_text += (
                f"<div class='semester-table-wrapper'>"
                f"<div class='semester-header'>"
                f"<div class='semester-title'>{term['term_name']}</div>"
                f"<div class='semester-credits'>{header_extra}</div>"
                f"</div>"
            )

            if warning:
                response_text += f"<div class='term-warning'>{warning}</div>"

            response_text += (
                "<table class='prospectus-table'>"
                "<thead><tr>"
                "<th style='width:15%;'>Code</th>"
                "<th style='width:45%;'>Course Title</th>"
                "<th style='width:10%;'>CH</th>"
                "<th style='width:30%;'>Pre-req</th>"
                "</tr></thead><tbody>"
            )

            if courses:
                for c in courses:
                    is_retake = c.get("is_retake", False)
                    row_style = "style='background:#fff7f7;'" if is_retake else ""
                    code_display = f"<span style='color:#dc2626;font-weight:700;'>{c['code']}</span>" if is_retake else f"<strong>{c['code']}</strong>"
                    response_text += (
                        f"<tr {row_style}>"
                        f"<td>{code_display}</td>"
                        f"<td>{c['name']}</td>"
                        f"<td>{c['credits']}</td>"
                        f"<td>{c['prereqs']}</td>"
                        f"</tr>"
                    )
            else:
                response_text += "<tr><td colspan='4' style='text-align:center;color:#6b7280;'>No eligible courses this term</td></tr>"

            response_text += "</tbody></table></div>"

        total_terms = len(plan)
        response_text += (
            f"<p class='plan-note'><em>✅ Complete plan: {total_terms} terms remaining. "
            f"All prerequisite chains are mathematically satisfied. "
            f"Red rows are courses that must be retaken.</em></p></div>"
        )

    except Exception as e:
        import traceback
        traceback.print_exc()
        response_text = f"<p>Sorry, I encountered an error building the degree plan: <code>{str(e)}</code></p>"

    return {"final_answer": response_text}


def retrieve_node(state: AgentState):
    print(f"\n[TRACE] Node: Retrieve")
    docs = retrieve_documents.invoke({"query": state["query"], "k": 4})
    print(f"[TRACE] Retrieved {len(docs)} documents.")
    return {"retrieved_docs": docs}

def direct_answer_node(state: AgentState):
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
    print(f"\n[TRACE] Node: Web Search Fallback")
    results = web_search.invoke({"query": state["query"]})
    print(f"[TRACE] Web search results obtained.")
    return {"web_results": results, "used_web_search": True}

def generate_node(state: AgentState):
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

def route_after_supervisor(state: AgentState):
    if state.get("requires_planning"):
        if state.get("requires_clarification"):
            return "clarification"
        return "degree_planner"
    elif state.get("needs_retrieval"):
        return "retrieve"
    else:
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
workflow.add_node("clarification", clarification_node)
workflow.add_node("degree_planner", degree_planner_node)
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
    route_after_supervisor,
    {
        "clarification": "clarification",
        "degree_planner": "degree_planner",
        "retrieve": "retrieve", 
        "direct_answer": "direct_answer"
    }
)

workflow.add_edge("clarification", END)
workflow.add_edge("degree_planner", END)
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
