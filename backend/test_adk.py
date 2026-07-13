import os
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "False"
os.environ["GEMINI_API_KEY"] = "mock-api-key"

from google.adk.agents import Agent

a = Agent(name="test", model="gemini-2.0-flash", instruction="say hi")

try:
    print("Trying a('hello')")
    a("hello")
    print("Success: a('hello')")
except Exception as e:
    print("Error:", type(e), str(e))

try:
    print("Trying a(user_input='hello')")
    a(user_input="hello")
    print("Success: a(user_input='hello')")
except Exception as e:
    print("Error:", type(e), str(e))

try:
    print("Trying a.run('hello')")
    a.run("hello")
    print("Success: a.run('hello')")
except Exception as e:
    print("Error:", type(e), str(e))

try:
    print("Trying a.run(user_input='hello')")
    a.run(user_input="hello")
    print("Success: a.run(user_input='hello')")
except Exception as e:
    print("Error:", type(e), str(e))
