import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
# I'll let it use the real key if it's set in my environment, otherwise it will fail.
# Actually I'll just write the syntax.

from google import genai
from google.genai import types

def dummy_tool(x: int) -> str:
    """Returns the number as a string."""
    return f"Number is {x}"

try:
    client = genai.Client()
    chat = client.chats.create(
        model="gemini-2.5-flash",
        config=types.GenerateContentConfig(
            tools=[dummy_tool]
        )
    )
    print("Chat object created successfully:", type(chat))
except Exception as e:
    print("Error:", e)
