#!/usr/bin/env python3
"""Check GLM endpoint for available embedding models."""
import os
import sys
from pathlib import Path

import httpx

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from dotenv import load_dotenv

load_dotenv(BACKEND / ".env", override=True)

endpoint = os.environ["GLM_ENDPOINT"].rstrip("/")
key = os.environ["GLM_API_KEY"]
r = httpx.get(f"{endpoint}/models", headers={"Authorization": f"Bearer {key}"}, timeout=30)
print("Status:", r.status_code)
models = r.json().get("data", [])
print(f"Total models: {len(models)}")
for m in models:
    mid = m["id"]
    if any(x in mid.lower() for x in ["embed", "titan", "bge", "glm", "embedding"]):
        print(f"  EMBED? {mid}")

# Try common embedding model names on GLM
from services.ai_service import _get_client

client, _ = _get_client("glm")
for model_name in ["zai.glm-5", "amazon.titan-embed-text-v1", "amazon.titan-embed-text-v2:0",
                    "baai/bge-m3", "cohere.embed-english-v3", "zai.embedding-3"]:
    try:
        r = client.embeddings.create(input=["test"], model=model_name)
        print(f"  OK: {model_name} -> dim={len(r.data[0].embedding)}")
        break
    except Exception as e:
        err = str(e)[:80]
        print(f"  FAIL: {model_name} -> {err}")
