import os
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    print("No GEMINI_API_KEY found in .env")
    exit(1)

client = genai.Client(api_key=api_key)
print("Available models:")
for m in client.models.list():
    if "flash" in m.name:
        print(f" - {m.name}")
