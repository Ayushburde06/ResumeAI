#!/usr/bin/env python3
"""Check what's registered in MODEL_REGISTRY."""
import os
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from dotenv import load_dotenv

load_dotenv(BACKEND / ".env", override=True)
from services.ai_service import MODEL_REGISTRY

print("Registered models:")
for k, v in MODEL_REGISTRY.items():
    print(f"  {k}: model={v['model']}, embeddings={v.get('supports_embeddings', False)}")
print(f"\nDefault: {os.environ.get('DEFAULT_MODEL_ID', '?')}")
