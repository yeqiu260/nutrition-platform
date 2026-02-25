import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROK_API_KEY")

if not api_key:
    print("Error: GROK_API_KEY not found in environment variables")
    exit(1)

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

try:
    print(f"Checking models with key: {api_key[:10]}...")
    models = client.models.list()
    print("\nAvailable Models:")
    for model in models.data:
        print(f" - {model.id}")
except Exception as e:
    print(f"\nError listing models: {e}")
