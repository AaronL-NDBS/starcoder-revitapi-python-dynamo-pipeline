import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

print("--- Inspecting the first available model ---")
try:
    # Get the list of models
    models = list(client.models.list())
    if models:
        first_model = models[0]
        print(f"Direct Print of Model Object: {first_model}")
        print("\nAvailable Attributes/Methods:")
        print(dir(first_model))
    else:
        print("No models found. Check your API Key permissions.")
except Exception as e:
    print(f"Error: {e}")