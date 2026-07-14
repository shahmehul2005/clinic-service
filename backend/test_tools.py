import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
from google import genai
from google.genai import types

def get_current_date() -> str:
    """Returns the current date in YYYY-MM-DD format."""
    return "2026-07-14"

client = genai.Client()

chat = client.chats.create(
    model="gemini-2.5-flash",
    config=types.GenerateContentConfig(
        tools=[get_current_date]
    )
)

print("Sending message...")
res = chat.send_message("What is the current date?")
print("Response text:", res.text)
if res.function_calls:
    print("Function calls:", [f.name for f in res.function_calls])
