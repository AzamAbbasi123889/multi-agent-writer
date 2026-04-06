import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_tavily import TavilySearch
from langchain_core.messages import HumanMessage, SystemMessage

load_dotenv()

class MultiLLM:
    def __init__(self, primary, fallback):
        self.primary = primary
        self.fallback = fallback

    def invoke(self, messages, **kwargs):
        try:
            print(f"[LLM] Using {self.primary.__class__.__name__} ({self.primary.model_name if hasattr(self.primary, 'model_name') else self.primary.model})...")
            return self.primary.invoke(messages, **kwargs)
        except Exception as e:
            error_str = str(e).lower()
            # Catch common quota / rate limit errors for fallback
            exhaustion_keywords = ["429", "resource_exhausted", "quota", "limit exceeded", "rate_limit", "overloaded", "exhausted"]
            if any(kw in error_str for kw in exhaustion_keywords):
                print(f"[LLM] Primary model limit issues detected. Switching to fallback {self.fallback.__class__.__name__} ({self.fallback.model_name if hasattr(self.fallback, 'model_name') else self.fallback.model})...")
                try:
                    return self.fallback.invoke(messages, **kwargs)
                except Exception as fallback_err:
                    print(f"[LLM] Fallback also failed: {fallback_err}")
                    raise fallback_err
            print(f"[LLM] Non-quota error in Primary: {e}")
            raise e

# Initializing both LLMs
gemini_llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp", temperature=0.3)
groq_llm = ChatGroq(model="llama-3.3-70b-versatile", temperature=0.3)

# Groq is now PRIMARY, Gemini is SECONDARY
llm = MultiLLM(primary=groq_llm, fallback=gemini_llm)

# Shared Tavily search tool (from langchain-tavily)
search_tool = TavilySearch(max_results=3)


def researcher_agent(state: dict) -> dict:
    topic = state["topic"]
    print(f"\n[Researcher] Starting research on: {topic}")

    try:
        results = search_tool.invoke(topic)
    except Exception as e:
        print(f"[Researcher] Search error: {e}")
        results = []

    if not results:
        research_summary = "No search results found. Please write based on general knowledge."
        print("[Researcher] Done. No sources found, using fallback.")
    else:
        # Some versions of TavilySearch return a string, older or configured ones return a list
        if isinstance(results, str):
            context = results
        elif isinstance(results, list):
            context_list = []
            for r in results:
                if isinstance(r, dict):
                    context_list.append(f"Source: {r.get('url', 'Unknown')}\nContent: {r.get('content', '')}")
                else:
                    context_list.append(str(r))
            context = "\n\n".join(context_list)
        else:
            context = str(results)

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
        print(f"[Researcher] Done. Summarized {len(results)} sources.")

    updated_messages = state["messages"] + [{"role": "researcher", "content": research_summary}]

    return {
        **state,
        "research": research_summary,
        "messages": updated_messages,
    }


def writer_agent(state: dict) -> dict:
    print("\n[Writer] Writing article...")

    topic = state["topic"]
    research = state["research"]
    revision_notes = state["revision_notes"]
    revision_count = state["revision_count"]

    revision_instruction = ""
    if revision_notes:
        revision_instruction = (
            f"IMPORTANT: The reviewer rejected the previous draft. "
            f"You MUST address these specific issues in your rewrite: {revision_notes}"
        )

    system_prompt = (
        "You are a professional content writer. Write a clear, engaging, well-structured article for a general audience. "
        "The article must have: a compelling title, an introduction paragraph, exactly 3 main sections each with a bold header, "
        "and a conclusion paragraph. Total length must be between 400 and 600 words. Use simple language. Do not use jargon."
    )

    user_message = f"Topic: {topic}\n\nResearch Summary:\n{research}"
    if revision_instruction:
        user_message += f"\n\n{revision_instruction}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])

    draft = response.content
    print(f"[Writer] Draft complete. (Round {revision_count + 1})")

    updated_messages = state["messages"] + [{"role": "writer", "content": draft}]

    return {
        **state,
        "draft": draft,
        "revision_notes": "",
        "messages": updated_messages,
    }


def reviewer_agent(state: dict) -> dict:
    print("\n[Reviewer] Reviewing draft...")

    topic = state["topic"]
    draft = state["draft"]

    system_prompt = (
        "You are a strict but fair content editor. Review the article draft below. "
        "You must respond in EXACTLY this format with no extra text before or after:\n\n"
        "VERDICT: APPROVED\nNOTES: Looks good!\n\nOR\n\n"
        "VERDICT: NEEDS_REVISION\nNOTES: [List specific issues here, numbered, be detailed]"
    )

    user_message = f"Topic: {topic}\n\nArticle Draft:\n{draft}"

    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message)
    ])

    full_response = response.content

    if "VERDICT: APPROVED" in full_response:
        approved = True
        revision_notes = ""
        print("[Reviewer] Verdict: APPROVED")
    else:
        approved = False
        if "NOTES:" in full_response:
            notes = full_response.split("NOTES:", 1)[1].strip()
        else:
            notes = full_response.strip()
        revision_notes = notes
        print("[Reviewer] Verdict: NEEDS REVISION")
        print(f"[Reviewer] Issues found: {notes}")

    updated_messages = state["messages"] + [{"role": "reviewer", "content": full_response}]

    return {
        **state,
        "approved": approved,
        "revision_notes": revision_notes,
        "messages": updated_messages,
    }
