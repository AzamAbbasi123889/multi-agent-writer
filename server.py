"""
Flask backend server for the Multi-Agent Writer System.
Exposes SSE (Server-Sent Events) endpoint for real-time pipeline streaming.
"""
import os
import sys
import json
import queue
import threading
import time
from flask import Flask, request, jsonify, Response
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

# ─── Patched agents module with event emitter ──────────────────────────────
# We monkey-patch print to also emit events over SSE during a run.

def build_pipeline_with_emitter(event_queue):
    """
    Wraps the real agent pipeline so that every agent print statement
    is also pushed as a structured SSE event.
    """
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_groq import ChatGroq
    from langchain_tavily import TavilySearch
    from langchain_core.messages import HumanMessage, SystemMessage
    from langgraph.graph import StateGraph, END
    from typing import TypedDict, List

    class AgentState(TypedDict):
        topic: str
        research: str
        draft: str
        approved: bool
        revision_notes: str
        revision_count: int
        messages: List[dict]
        next: str

    def emit(event_type, message, data=None):
        payload = {"type": event_type, "message": message}
        if data:
            payload["data"] = data
        event_queue.put(payload)

    class MultiLLM:
        def __init__(self, primary, fallback):
            self.primary = primary
            self.fallback = fallback

        def invoke(self, messages, **kwargs):
            p_name = self.primary.__class__.__name__
            p_model = getattr(self.primary, 'model_name', None) or getattr(self.primary, 'model', '?')
            try:
                emit("llm", f"Using {p_name} — {p_model}")
                return self.primary.invoke(messages, **kwargs)
            except Exception as e:
                error_str = str(e).lower()
                exhaustion_keywords = ["429", "resource_exhausted", "quota", "limit exceeded",
                                       "rate_limit", "overloaded", "exhausted"]
                if any(kw in error_str for kw in exhaustion_keywords):
                    f_name = self.fallback.__class__.__name__
                    f_model = getattr(self.fallback, 'model_name', None) or getattr(self.fallback, 'model', '?')
                    emit("warning", f"Primary limit hit. Switching to {f_name} — {f_model}")
                    try:
                        return self.fallback.invoke(messages, **kwargs)
                    except Exception as fe:
                        emit("error", f"Fallback also failed: {fe}")
                        raise fe
                emit("error", f"Non-quota error: {e}")
                raise e

    gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.3)
    groq_llm   = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)
    llm = MultiLLM(primary=groq_llm, fallback=gemini_llm)
    search_tool = TavilySearch(max_results=5)

    # ── Agent functions ────────────────────────────────────────────────────
    def researcher_agent(state):
        topic = state["topic"]
        emit("agent_start", "Researcher", {"agent": "researcher", "topic": topic})

        try:
            results = search_tool.invoke(topic)
        except Exception as e:
            emit("agent_log", f"Search error: {e}", {"agent": "researcher"})
            results = []

        if not results:
            research_summary = "No search results found. Writing from general knowledge."
            emit("agent_log", "No sources found, using general knowledge.", {"agent": "researcher"})
        else:
            if isinstance(results, str):
                context = results
            elif isinstance(results, list):
                context_list = []
                for r in results:
                    if isinstance(r, dict):
                        context_list.append(f"Source: {r.get('url','?')}\nContent: {r.get('content','')}")
                    else:
                        context_list.append(str(r))
                context = "\n\n".join(context_list)
            else:
                context = str(results)

            count = len(results) if isinstance(results, list) else 1
            emit("agent_log", f"Found {count} sources. Summarizing...", {"agent": "researcher"})

            system_prompt = (
                "You are a research assistant. Read the following web search results and extract the most important "
                "facts, statistics, recent developments, and key insights about the topic. "
                "Format your output as clear bullet points. Be factual and concise."
            )
            response = llm.invoke([
                SystemMessage(content=system_prompt),
                HumanMessage(content=f"Topic: {topic}\n\nSearch Results:\n{context}")
            ])
            research_summary = response.content
            emit("agent_done", f"Research complete. {count} sources summarized.", {
                "agent": "researcher", "content": research_summary
            })

        return {**state, "research": research_summary,
                "messages": state["messages"] + [{"role": "researcher", "content": research_summary}]}

    def writer_agent(state):
        emit("agent_start", "Writer is drafting the article...", {"agent": "writer"})
        topic          = state["topic"]
        research       = state["research"]
        revision_notes = state["revision_notes"]
        revision_count = state["revision_count"]

        revision_instruction = ""
        if revision_notes:
            revision_instruction = (
                f"IMPORTANT: The reviewer rejected the previous draft. "
                f"Address these issues: {revision_notes}"
            )
            emit("agent_log", f"Revising based on notes: {revision_notes[:100]}...", {"agent": "writer"})

        system_prompt = (
            "You are a professional content writer. Write a clear, engaging, well-structured article for a general audience. "
            "The article must have: a compelling title, an introduction paragraph, exactly 3 main sections each with a bold header, "
            "and a conclusion paragraph. Total length must be between 400 and 600 words. Use simple language. Do not use jargon."
        )
        user_message = f"Topic: {topic}\n\nResearch Summary:\n{research}"
        if revision_instruction:
            user_message += f"\n\n{revision_instruction}"

        response = llm.invoke([SystemMessage(content=system_prompt), HumanMessage(content=user_message)])
        draft = response.content
        emit("agent_done", f"Draft complete (Round {revision_count + 1})", {"agent": "writer", "content": draft})

        return {**state, "draft": draft, "revision_notes": "",
                "messages": state["messages"] + [{"role": "writer", "content": draft}]}

    def reviewer_agent(state):
        emit("agent_start", "Reviewer is evaluating the draft...", {"agent": "reviewer"})
        topic = state["topic"]
        draft = state["draft"]

        system_prompt = (
            "You are a strict but fair content editor. Review the article draft below. "
            "You must respond in EXACTLY this format with no extra text before or after:\n\n"
            "VERDICT: APPROVED\nNOTES: Looks good!\n\nOR\n\n"
            "VERDICT: NEEDS_REVISION\nNOTES: [List specific issues here, numbered, be detailed]"
        )
        response = llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Topic: {topic}\n\nArticle Draft:\n{draft}")
        ])
        full_response = response.content

        if "VERDICT: APPROVED" in full_response:
            approved = True
            revision_notes = ""
            emit("agent_done", "Verdict: APPROVED", {"agent": "reviewer", "verdict": "approved"})
        else:
            approved = False
            notes = full_response.split("NOTES:", 1)[1].strip() if "NOTES:" in full_response else full_response.strip()
            revision_notes = notes
            emit("agent_done", "Verdict: NEEDS REVISION", {"agent": "reviewer", "verdict": "revision", "notes": notes})

        return {**state, "approved": approved, "revision_notes": revision_notes,
                "messages": state["messages"] + [{"role": "reviewer", "content": full_response}]}

    def supervisor(state):
        emit("agent_start", "Supervisor is deciding the next step...", {"agent": "supervisor"})
        groq_sv   = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
        gemini_sv = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)
        sup_llm   = MultiLLM(primary=groq_sv, fallback=gemini_sv)

        research_status = "exists" if state["research"] else "empty"
        draft_status    = "exists" if state["draft"] else "empty"
        status_report = (
            f"Research: {research_status}\nDraft: {draft_status}\n"
            f"Approved: {state['approved']}\nRevision Count: {state['revision_count']}"
        )
        system_prompt = (
            "You are a supervisor managing a writing team. Based on the current project status below, "
            "decide which team member should act next. You must reply with EXACTLY ONE WORD and nothing else "
            "- no punctuation, no explanation, just one word. "
            "Your only valid responses are: researcher, writer, reviewer, finish. "
            "Rule 1: if research is empty - reply researcher. "
            "Rule 2: if research exists but draft is empty - reply writer. "
            "Rule 3: if draft exists and approved is False and revision_count < 2 - reply reviewer. "
            "Rule 4: if draft was rejected and revision_count < 2 - reply writer. "
            "Rule 5: if approved is True - reply finish. "
            "Rule 6: if revision_count >= 2 - reply finish."
        )
        response = sup_llm.invoke([
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Current project status:\n{status_report}")
        ])
        decision = response.content.strip().lower()
        if state["revision_count"] >= 2:
            decision = "finish"

        emit("supervisor", f"Decision: {decision.upper()}", {"decision": decision})
        return {**state, "next": decision}

    def writer_with_counter(state):
        result = writer_agent(state)
        result["revision_count"] = state["revision_count"] + 1
        return result

    def route(state):
        return state["next"]

    builder = StateGraph(AgentState)
    builder.add_node("supervisor",  supervisor)
    builder.add_node("researcher",  researcher_agent)
    builder.add_node("writer",      writer_with_counter)
    builder.add_node("reviewer",    reviewer_agent)
    builder.set_entry_point("supervisor")
    builder.add_conditional_edges("supervisor", route, {
        "researcher": "researcher",
        "writer":     "writer",
        "reviewer":   "reviewer",
        "finish":     END,
    })
    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer",     "supervisor")
    builder.add_edge("reviewer",   "supervisor")

    return builder.compile()


# ─── SSE Route ────────────────────────────────────────────────────────────────

@app.route("/api/run", methods=["POST"])
def run_pipeline():
    data  = request.get_json()
    topic = (data or {}).get("topic", "").strip()
    if not topic:
        return jsonify({"error": "Topic is required"}), 400

    event_queue: queue.Queue = queue.Queue()

    def pipeline_thread():
        try:
            graph = build_pipeline_with_emitter(event_queue)
            initial_state = {
                "topic": topic, "research": "", "draft": "",
                "approved": False, "revision_notes": "",
                "revision_count": 0, "messages": [], "next": "",
            }
            event_queue.put({"type": "start", "message": f"Pipeline started for: {topic}"})
            final_state = graph.invoke(initial_state)
            event_queue.put({
                "type": "complete",
                "message": "Pipeline complete!",
                "data": {
                    "draft":         final_state["draft"],
                    "revision_count": final_state["revision_count"],
                    "messages":      final_state["messages"],
                }
            })
        except Exception as e:
            event_queue.put({"type": "error", "message": str(e)})
        finally:
            event_queue.put(None)  # sentinel

    thread = threading.Thread(target=pipeline_thread, daemon=True)
    thread.start()

    def generate():
        while True:
            item = event_queue.get()
            if item is None:
                break
            yield f"data: {json.dumps(item)}\n\n"

    return Response(generate(), mimetype="text/event-stream",
                    headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "models": {"primary": "llama-3.3-70b-versatile (Groq)", "fallback": "gemini-2.0-flash-exp"}})


if __name__ == "__main__":
    print("Starting Multi-Agent Writer API server on http://localhost:5000")
    app.run(debug=False, host="0.0.0.0", port=5000, threaded=True)
