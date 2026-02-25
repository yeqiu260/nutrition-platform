import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("GROK_API_KEY")
print(f"Key: {api_key[:10]}...")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

try:
    print("Fetching available models...")
    models = client.models.list()
    print(f"Found {len(models.data)} models:")
    for m in models.data:
        print(f" - {m.id}")
except Exception as e:
    print(f"Error: {e}")
