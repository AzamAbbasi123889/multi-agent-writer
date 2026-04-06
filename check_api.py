import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

print("Starting Check API script...")
load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
print(f"API Key found: {api_key[:10]}...{api_key[-4:]}")

llm = ChatGroq(model_name="llama-3.3-70b-versatile", groq_api_key=api_key)
print("LLM Initialized. Invoking...")

try:
    response = llm.invoke([HumanMessage(content="Hello")])
    print("SUCCESS: Groq Response received.")
    print(f"Response: {response.content[:100]}...")
except Exception as e:
    print(f"FAILED: Groq Error: {e}")
