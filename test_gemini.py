import os
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

load_dotenv()

try:
    llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash-exp")
    response = llm.invoke([HumanMessage(content="Hello")])
    print("Gemini response:", response.content)
except Exception as e:
    print("Gemini error:", e)
    print("Error type:", type(e))
