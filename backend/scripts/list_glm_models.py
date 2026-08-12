#!/usr/bin/env python3
"""List all GLM models and try embedding-3."""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from dotenv import load_dotenv

load_dotenv(BACKEND / ".env", override=True)
import httpx

endpoint = os.environ["GLM_ENDPOINT"].rstrip("/")
key = os.environ["GLM_API_KEY"]
r = httpx.get(f"{endpoint}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
models = r.json().get("data", [])
print("All models:")
for m in models:
    print(f"  {m['id']}")

# Try embedding-3 and glm-4-embedding
from services.ai_service import _get_client

client, _ = _get_client("glm")
for name in ["embedding-3", "embedding-2", "text-embedding-004", "zai.glm-4-embedding",
              "zai.glm-embedding-3", "BAAI/bge-m3", "baai.bge-m3",
              "amazon.titan-embed-text-v1:0", "amazon.nova-embed-text-v1:0"]:
    try:
        r = client.embeddings.create(input=["test embedding"], model=name)
        print(f"\n  OK: {name} -> dim={len(r.data[0].embedding)}")
        break
    except Exception as e:
        print(f"  FAIL: {name} -> {str(e)[:60]}")
