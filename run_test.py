"""
Non-interactive test runner for the multi-agent system.
Automatically uses 'Future of electric vehicles' as the topic.
"""
import sys
from dotenv import load_dotenv
from graph import build_graph

load_dotenv()

print("=" * 53)
print(" MULTI-AGENT RESEARCH & WRITING SYSTEM")
print("=" * 53)
print()

topic = "Future of electric vehicles"
print(f"Topic: {topic}")

initial_state = {
    "topic": topic,
    "research": "",
    "draft": "",
    "approved": False,
    "revision_notes": "",
    "revision_count": 0,
    "messages": [],
    "next": "",
}

graph = build_graph()

print("\nStarting the multi-agent pipeline...\n")
print("-" * 53)

final_state = graph.invoke(initial_state)

print("\n" + "=" * 53)
print(" FINAL ARTICLE")
print("=" * 53)
print()
print(final_state["draft"])
print()
print(f"Pipeline complete. Article written in {final_state['revision_count']} round(s).")
print(f"Total agent messages exchanged: {len(final_state['messages'])}")
