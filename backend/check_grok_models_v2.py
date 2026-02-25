import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("GROK_API_KEY")
print(f"Key: {api_key[:10]}...")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

try:
    print("Listing models...")
    models = client.models.list()
    print(models)
except Exception as e:
    print(f"Error: {e}")
