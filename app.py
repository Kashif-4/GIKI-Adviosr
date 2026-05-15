import os
import json
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
from graph import app as agent_app
import asyncio

app = FastAPI(title="UniQuery AI Advisor")

if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

class ChatRequest(BaseModel):
    query: str

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    async def event_generator():
        try:
            inputs = {
                "query": request.query,
                "retry_count": 0,
                "relevant_docs": [],
                "used_web_search": False
            }
            
            status_map = {
                "adaptive_retrieval": "Analyzing query type...",
                "degree_planner": "Calculating constraints and timeline...",
                "retrieve": "Searching university catalogs...",
                "relevance_grading": "Evaluating document relevance...",
                "web_search": "Falling back to web search...",
                "generate": "Synthesizing answer...",
                "hallucination_check": "Verifying facts and grounding..."
            }
            
            final_answer = None
            
            for output in agent_app.stream(inputs):
                node_name = list(output.keys())[0]
                state = output[node_name]
                
                # Update final_answer if found
                if "final_answer" in state and state["final_answer"]:
                    final_answer = state["final_answer"]
                elif "generation" in state and state["generation"]:
                    final_answer = state["generation"]
                
                status = status_map.get(node_name, f"Processing {node_name}...")
                
                # Combine relevant reasoning for the current node
                active_reason = state.get("retrieval_reason") or state.get("hallucination_explanation") or ""
                
                # Immediate technical fallbacks
                if not active_reason:
                    if node_name == "retrieve": 
                        active_reason = f"Vector search query: '{request.query[:40]}...'"
                    elif node_name == "degree_planner":
                        active_reason = f"Running constraint satisfaction on transcript."
                    elif node_name == "relevance_grading":
                        active_reason = f"Scoring {len(state.get('retrieved_docs', []))} chunks."
                    elif node_name == "generate":
                        active_reason = "Executing grounded synthesis."
                    elif node_name == "web_search":
                        active_reason = f"Web search: '{request.query[:40]}...'"

                trace_content = f"{status} <br><small style='color:var(--text-muted); opacity:0.8;'>{active_reason}</small>" if active_reason else status
                
                yield f"data: {json.dumps({'type': 'trace', 'content': trace_content, 'node': node_name})}\n\n"
                
                if node_name == "relevance_grading" and "relevant_docs" in state:
                    unique_sources = {}
                    for doc in state["relevant_docs"]:
                        src_name = str(doc.get('metadata', {}).get('source', 'Unknown'))
                        if src_name not in unique_sources:
                            unique_sources[src_name] = doc.get('content', '')[:120]
                    
                    sources_list = [{"source": k, "content": v} for k, v in unique_sources.items()]
                    yield f"data: {json.dumps({'type': 'sources', 'content': sources_list})}\n\n"

            # Yield the final answer collected during streaming
            if final_answer:
                yield f"data: {json.dumps({'type': 'answer', 'content': final_answer})}\n\n"
            
            yield f"data: {json.dumps({'type': 'done'})}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
