import sys
from dotenv import load_dotenv
from graph import build_graph

load_dotenv()


if __name__ == "__main__":
    print("=" * 53)
    print(" MULTI-AGENT RESEARCH & WRITING SYSTEM")
    print("=" * 53)
    print()

    topic = input("Enter a topic to research and write about: ").strip()

    if not topic:
        print("Error: Topic cannot be empty. Please provide a valid topic.")
        sys.exit(1)

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
