"""Shared SlowAPI rate limiter instance.

Import this module everywhere instead of creating a new Limiter()
so all decorators operate on the same in-memory store that is
registered with app.state.limiter in main.py.

Behind a reverse proxy (Nginx, Railway, Render), set TRUST_PROXY=true
in .env so the limiter keys on X-Forwarded-For instead of the proxy IP.
"""
import os

from slowapi import Limiter
from slowapi.util import get_remote_address


def _proxy_aware_key_func(request):
    """Use X-Forwarded-For when TRUST_PROXY is enabled, else raw client IP."""
    if os.environ.get("TRUST_PROXY", "").lower() in ("true", "1", "yes"):
        xff = request.headers.get("x-forwarded-for", "")
        if xff:
            # First IP in the chain is the real client
            return xff.split(",")[0].strip()
    return get_remote_address(request)


limiter = Limiter(key_func=_proxy_aware_key_func)
