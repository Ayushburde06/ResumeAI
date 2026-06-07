Deepseek CLI helper
===================

This helper shows how to call a Deepseek model exposed via an Azure OpenAI-style endpoint.

Usage
-----

Set environment variables (PowerShell examples):

```powershell
$Env:DEEPSEEK_ENDPOINT = 'https://ambangare07-9241-resource.services.ai.azure.com/openai/v1'
$Env:DEEPSEEK_DEPLOYMENT = 'DeepSeek-V4-Flash'
$Env:DEEPSEEK_API_KEY = '<your_api_key_here>'
```

Run the CLI:

```powershell
python tools\deepseek_cli.py --prompt "Write a Python function that reverses a string"
```

Or pass flags directly (not recommended for long-term storage of keys):

```powershell
python tools\deepseek_cli.py --endpoint "https://.../openai/v1" --deployment "DeepSeek-V4-Flash" --key "${Env:DEEPSEEK_API_KEY}" --prompt "Explain X"
```

Notes
-----
- The script uses `requests`. Install it in the `backend` virtualenv:

```powershell
& backend\.venv\Scripts\Activate.ps1
pip install -r backend\requirements.txt
```

- Keep your API key secret. Prefer setting environment variables or using a secrets manager.
