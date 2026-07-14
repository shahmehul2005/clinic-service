from google import genai
import os

client = genai.Client()
print("Available models:")
for m in client.models.list():
    if "flash" in m.name:
        print(f" - {m.name}")
