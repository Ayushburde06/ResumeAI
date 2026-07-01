#!/usr/bin/env python3
"""
Run before git push to catch accidentally staged secrets.
Usage:  python scripts/check_secrets.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

# Patterns that look like real API keys / secrets (not placeholders)
_PATTERNS = [
    re.compile(r'ABSK[A-Za-z0-9+/=]{20,}'),   # AWS Bedrock-style key
    re.compile(r'sk-[a-f0-9]{20,}'),            # DeepSeek / OpenAI style
    re.compile(r'[A-Za-z0-9]{40,}'),            # any long random-looking string
]

_SAFE_PLACEHOLDER = re.compile(
    r'(YOUR_|CHANGE_THIS|example|placeholder|xxxx)',
    re.IGNORECASE
)

_CHECK_FILES = [
    ROOT / "backend" / ".env",
    ROOT / ".env",
]

found = False
for path in _CHECK_FILES:
    if not path.exists():
        continue
    for i, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip().startswith("#") or "=" not in line:
            continue
        _, _, value = line.partition("=")
        value = value.strip()
        if not value or _SAFE_PLACEHOLDER.search(value):
            continue
        for pat in _PATTERNS:
            if pat.search(value):
                print(f"[WARNING] Potential secret found in {path.name} line {i}: {line[:60]}...")
                found = True
                break

if found:
    print("\n[ERROR] Commit blocked — real API keys may be staged.")
    print("   Set secrets in your Railway/Render/Vercel dashboard instead.")
    sys.exit(1)
else:
    print("[OK] No secrets detected in .env files.")
