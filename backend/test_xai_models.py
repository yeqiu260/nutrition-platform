"""测试 xAI Grok API 并列出可用模型"""
import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

api_key = os.getenv("GROK_API_KEY")
print(f"API Key: {api_key[:15]}...")

client = OpenAI(
    api_key=api_key,
    base_url="https://api.x.ai/v1"
)

# 列出可用模型
print("\n=== Listing available models ===")
try:
    models = client.models.list()
    print("Available models:")
    for m in models.data:
        print(f"  - {m.id}")
except Exception as e:
    print(f"Error listing models: {e}")

# 尝试不同的模型
test_models = ["grok-2", "grok-2-1212", "grok-beta", "grok-3-mini-fast-beta", "grok-3-fast-beta"]
print("\n=== Testing different models ===")
for model_name in test_models:
    try:
        print(f"\nTesting {model_name}...")
        response = client.chat.completions.create(
            model=model_name,
            messages=[{"role": "user", "content": "Say hi"}],
            max_tokens=10
        )
        print(f"  ✓ {model_name} works! Response: {response.choices[0].message.content}")
        break
    except Exception as e:
        print(f"  ✗ {model_name} failed: {str(e)[:100]}")
