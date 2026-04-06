import os
from typing import TypedDict, List
from dotenv import load_dotenv
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, SystemMessage
from agents import researcher_agent, writer_agent, reviewer_agent, MultiLLM

load_dotenv()


class AgentState(TypedDict):
    topic: str
    research: str
    draft: str
    approved: bool
    revision_notes: str
    revision_count: int
    messages: List[dict]
    next: str


def supervisor(state: AgentState) -> AgentState:
    print("\n[Supervisor] Checking state and deciding next step...")

    # We use both models for fallback support (Groq primary, Gemini fallback)
    groq_sv = ChatGroq(model="llama-3.3-70b-versatile", temperature=0)
    gemini_sv = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0)
    supervisor_llm = MultiLLM(primary=groq_sv, fallback=gemini_sv)

    # Build current status report
    research_status = "exists" if state["research"] else "empty"
    draft_status = "exists" if state["draft"] else "empty"
    approved_status = str(state["approved"])
    revision_count = state["revision_count"]

    status_report = (
        f"Research: {research_status}\n"
        f"Draft: {draft_status}\n"
        f"Approved: {approved_status}\n"
        f"Revision Count: {revision_count}"
    )

    system_prompt = (
        "You are a supervisor managing a writing team. Based on the current project status below, "
        "decide which team member should act next. You must reply with EXACTLY ONE WORD and nothing else "
        "— no punctuation, no explanation, just one word. "
        "Your only valid responses are: researcher, writer, reviewer, finish. "
        "Follow these rules strictly: "
        "Rule 1 — if research is empty or missing, reply: researcher. "
        "Rule 2 — if research exists but draft is empty or missing, reply: writer. "
        "Rule 3 — if draft exists and approved is False and revision_count is less than 2, reply: reviewer. "
        "Rule 4 — if the draft was rejected (approved is False) and revision_count is less than 2, reply: writer. "
        "Rule 5 — if approved is True, reply: finish. "
        "Rule 6 — if revision_count is 2 or more, reply: finish regardless of approval."
    )

    response = supervisor_llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Current project status:\n{status_report}")
    ])

    decision = response.content.strip().lower()

    # Safety override to prevent infinite loops
    if state["revision_count"] >= 2:
        decision = "finish"

    print(f"[Supervisor] Decision -> {decision.upper()}")

    return {**state, "next": decision}


def writer_with_counter(state: AgentState) -> AgentState:
    result = writer_agent(state)
    result["revision_count"] = state["revision_count"] + 1
    return result


def route(state: AgentState) -> str:
    return state["next"]


def build_graph():
    builder = StateGraph(AgentState)

    builder.add_node("supervisor", supervisor)
    builder.add_node("researcher", researcher_agent)
    builder.add_node("writer", writer_with_counter)
    builder.add_node("reviewer", reviewer_agent)

    builder.set_entry_point("supervisor")

    builder.add_conditional_edges(
        "supervisor",
        route,
        {
            "researcher": "researcher",
            "writer": "writer",
            "reviewer": "reviewer",
            "finish": END,
        }
    )

    builder.add_edge("researcher", "supervisor")
    builder.add_edge("writer", "supervisor")
    builder.add_edge("reviewer", "supervisor")

    return builder.compile()
