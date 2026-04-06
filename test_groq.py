import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage

load_dotenv()

api_key = os.getenv("GROQ_API_KEY")
print(f"API Key found: {api_key[:10]}...")

try:
    llm = ChatGroq(model="llama3-70b-8192", groq_api_key=api_key)
    print("Invoking Groq...")
    response = llm.invoke([HumanMessage(content="Hello, are you Groq?")])
    print("Groq response:", response.content)
except Exception as e:
    print("Groq error:", e)
