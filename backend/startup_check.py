"""
Startup security check — runs before the FastAPI app boots.
Crashes immediately with a clear message if critical secrets are missing
or still set to placeholder values.
"""
import os
import sys

_PLACEHOLDERS = {
    "CHANGE_THIS_TO_A_RANDOM_64_CHAR_HEX_STRING",
    "YOUR_QWEN_API_KEY_HERE",
    "YOUR_GLM_API_KEY_HERE",
    "YOUR_GLM_FLASH_API_KEY_HERE",
    "YOUR_DEEPSEEK_API_KEY_HERE",
    "YOUR_KIMI_API_KEY_HERE",
    "YOUR_MINIMAX_API_KEY_HERE",
    "",
}

_REQUIRED = {
    "JWT_SECRET": "Generate with: python -c \"import secrets; print(secrets.token_hex(32))\"",
}

_AT_LEAST_ONE_MODEL = {
    "GLM_API_KEY":     "GLM-5 model",
    "KIMI_API_KEY":    "Kimi 2.5 model",
    "QWEN_API_KEY":    "Qwen3 Next 80B model",
    "MINIMAX_API_KEY": "MiniMax m2.5 model",
}


def run():
    errors = []

    # 1. Mandatory vars
    for var, hint in _REQUIRED.items():
        val = os.environ.get(var, "")
        if not val or val in _PLACEHOLDERS:
            errors.append(f"  ✗ {var} is missing or still a placeholder.\n    → {hint}")

    # 2. At least one AI model must be configured
    configured_models = [
        label for var, label in _AT_LEAST_ONE_MODEL.items()
        if os.environ.get(var, "") not in _PLACEHOLDERS
        and os.environ.get(var, "")
    ]
    if not configured_models:
        errors.append(
            "  ✗ No AI model API key found.\n"
            "    → Set at least one of: GLM_API_KEY, GPT_API_KEY, or KIMI_API_KEY"
        )

    if errors:
        print("\n" + "=" * 60, file=sys.stderr)
        print("  STARTUP FAILED — Missing or unsafe configuration:", file=sys.stderr)
        print("=" * 60, file=sys.stderr)
        for e in errors:
            print(e, file=sys.stderr)
        print("\n  In production: set these as environment variables in your", file=sys.stderr)
        print("  Railway / Render / Vercel dashboard — never in a committed file.", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)
        sys.exit(1)
