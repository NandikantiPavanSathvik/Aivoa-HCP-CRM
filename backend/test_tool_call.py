"""
Quick diagnostic: test if Groq tool calling works standalone.
Run: python test_tool_call.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from groq import Groq

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

tools = [{
    "type": "function",
    "function": {
        "name": "search_hcp",
        "description": "Search for healthcare professionals by name, specialty, or clinic.",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "The search term (e.g. doctor name)."}
            },
            "required": ["query"]
        }
    }
}]

messages = [
    {"role": "user", "content": "I met Dr. Jenkins today, discussed CardioSphere-10mg."}
]

print("Testing Groq tool calling with llama-3.3-70b-versatile...")
try:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    msg = response.choices[0].message
    print("SUCCESS!")
    print("Content:", msg.content)
    print("Tool calls:", msg.tool_calls)
except Exception as e:
    print(f"FAILED: {e}")

print("\nTesting with llama-3.1-70b-versatile...")
try:
    response = client.chat.completions.create(
        model="llama-3.1-70b-versatile",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    msg = response.choices[0].message
    print("SUCCESS!")
    print("Content:", msg.content)
    print("Tool calls:", msg.tool_calls)
except Exception as e:
    print(f"FAILED: {e}")
