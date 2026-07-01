"""
Quick test script to verify Claude API key is working.
Run: python test_claude_api.py
"""

import os
import sys
from dotenv import load_dotenv

# Load .env from the same directory
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), ".env"))

CLAUDE_API_KEY = os.getenv("CLAUDE_4_6_API_KEY")
CLAUDE_ENDPOINT = os.getenv("CLAUDE_4_6_ENDPOINT")
CLAUDE_MODEL = os.getenv("CLAUDE_4_6_MODEL")

print("=" * 60)
print("  Claude API Key Test")
print("=" * 60)
print(f"  Endpoint : {CLAUDE_ENDPOINT}")
print(f"  Model    : {CLAUDE_MODEL}")
print(f"  API Key  : {CLAUDE_API_KEY[:20]}..." if CLAUDE_API_KEY else "  API Key  : NOT SET")
print("=" * 60)

if not CLAUDE_API_KEY:
    print("\n[FAIL]  CLAUDE_4_6_API_KEY is not set in .env")
    sys.exit(1)

# Try using openai-compatible client (endpoint is OpenAI-compatible)
try:
    from openai import OpenAI

    client = OpenAI(
        api_key=CLAUDE_API_KEY,
        base_url=CLAUDE_ENDPOINT,
    )

    print("\n[...] Sending test message to Claude...")
    response = client.chat.completions.create(
        model=CLAUDE_MODEL,
        messages=[
            {"role": "user", "content": "Say 'Claude API is working!' and nothing else."}
        ],
        max_tokens=50,
    )

    reply = response.choices[0].message.content.strip()
    print(f"\n[OK]  SUCCESS! Model replied:\n    {reply}")
    print(f"\n    Model used : {response.model}")
    print(f"    Tokens used: {response.usage.total_tokens}")

except Exception as e:
    print(f"\n[FAIL]  FAILED with error:\n    {type(e).__name__}: {e}")
    sys.exit(1)

print("\n" + "=" * 60)
print("  Claude API key is VALID and WORKING [OK]")
print("=" * 60)
