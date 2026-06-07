import os
import sys
import argparse
import json
import requests


def get_args():
    p = argparse.ArgumentParser(description="Simple Deepseek (Azure OpenAI-style) CLI helper")
    p.add_argument("--endpoint", help="Deepseek endpoint URL (or set DEEPSEEK_ENDPOINT)")
    p.add_argument("--deployment", help="Deployment name (or set DEEPSEEK_DEPLOYMENT)")
    p.add_argument("--key", help="API key (or set DEEPSEEK_API_KEY)")
    p.add_argument("--prompt", help="Prompt to send. If omitted, reads from stdin interactively")
    p.add_argument("--max-tokens", type=int, default=800)
    p.add_argument("--temperature", type=float, default=0.2)
    return p.parse_args()


def build_url(endpoint: str, deployment: str) -> str:
    endpoint = endpoint.rstrip("/")
    # Azure-style chat completions endpoint (api-version required)
    return f"{endpoint}/deployments/{deployment}/chat/completions?api-version=2023-05-15"


def call_deepseek(endpoint: str, deployment: str, apikey: str, prompt: str, max_tokens: int, temperature: float):
    url = build_url(endpoint, deployment)
    headers = {"api-key": apikey, "Content-Type": "application/json"}
    payload = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=60)
    except Exception as e:
        print("Request error:", e, file=sys.stderr)
        return 2

    if not resp.ok:
        print(f"API error {resp.status_code}: {resp.text}", file=sys.stderr)
        return 3

    data = resp.json()
    # Azure response shape: { choices: [ { message: { role: 'assistant', content: '...' } } ] }
    try:
        choices = data.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content") or msg.get("content", "")
            # If content is an object with parts, try to stringify
            if isinstance(content, dict):
                content = json.dumps(content, indent=2)
            print(content)
            return 0
        # fallback plain text
        if "text" in data:
            print(data["text"]) 
            return 0
        print(json.dumps(data, indent=2))
        return 0
    except Exception as e:
        print("Response parse error:", e, file=sys.stderr)
        print(resp.text, file=sys.stderr)
        return 4


def main():
    args = get_args()

    endpoint = args.endpoint or os.getenv("DEEPSEEK_ENDPOINT")
    deployment = args.deployment or os.getenv("DEEPSEEK_DEPLOYMENT")
    apikey = args.key or os.getenv("DEEPSEEK_API_KEY")

    if not endpoint or not deployment or not apikey:
        print("Missing configuration. Set --endpoint, --deployment, and --key or the corresponding environment variables:")
        print("  DEEPSEEK_ENDPOINT, DEEPSEEK_DEPLOYMENT, DEEPSEEK_API_KEY")
        sys.exit(1)

    if args.prompt:
        prompt = args.prompt
    else:
        print("Enter prompt (end with Ctrl+D on a new line):")
        prompt = sys.stdin.read().strip()
        if not prompt:
            print("No prompt provided.")
            sys.exit(1)

    code = call_deepseek(endpoint, deployment, apikey, prompt, args.max_tokens, args.temperature)
    sys.exit(code)


if __name__ == "__main__":
    main()
