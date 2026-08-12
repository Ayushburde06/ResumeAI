"""Production launcher for ResumeAI — safe for AWS Free Tier (t2.micro: 1 vCPU / 1 GB).

Usage:
    python start_prod.py

Environment variables (all optional):
    PORT=8000
    WORKERS=1                          # never more than 1 on Free Tier
    TIER=free                          # 'free' or 'premium'
    LIMIT_CONCURRENCY=10               # max in-flight connections
    LIMIT_MAX_REQUESTS=200             # recycle worker after N requests
    MAX_CONCURRENT_AI=2                # max simultaneous AI calls
    MAX_CONCURRENT_PDF=0               # 0 = Playwright disabled (use LaTeX)
    MAX_CONCURRENT_LATEX=1             # max simultaneous LaTeX exports

Why 1 worker on Free Tier:
    - Python GIL limits CPU anyway
    - SQLite single-writer
    - 1 GB RAM can't handle fork() × N workers

Memory budget (t2.micro, 1 GB):
    - Python + uvicorn:            ~120 MB
    - SQLite WAL + connections:     ~50 MB
    - LaTeX (pdflatex):            ~100 MB per compile
    - Playwright Chromium:         ~400 MB (DISABLED on Free Tier)
    - Remaining for OS:            ~330 MB
"""
import os
import multiprocessing
import uvicorn

TIER = os.environ.get("TIER", "free").lower()
IS_FREE_TIER = TIER in ("free", "")

PORT = int(os.environ.get("PORT", "8000"))
HOST = os.environ.get("HOST", "0.0.0.0")

# ── Free Tier safe defaults ──────────────────────────────────────────────────
if IS_FREE_TIER:
    WORKERS = 1                                      # single process
    LIMIT_CONCURRENCY = int(os.environ.get("LIMIT_CONCURRENCY", "10"))
    LIMIT_MAX_REQUESTS = int(os.environ.get("LIMIT_MAX_REQUESTS", "200"))
    BACKLOG = int(os.environ.get("BACKLOG", "32"))
    # Set env vars so concurrency.py picks them up
    os.environ.setdefault("MAX_CONCURRENT_AI", "2")       # 2 simultaneous AI calls max
    os.environ.setdefault("MAX_CONCURRENT_PDF", "3")      # WeasyPrint ~50MB each, lightweight
    os.environ.setdefault("MAX_CONCURRENT_LATEX", "1")    # 1 LaTeX compile at a time
    os.environ.setdefault("MAX_CONCURRENT_REQUESTS", "10") # global semaphore
else:
    WORKERS = int(os.environ.get("WORKERS", "2"))
    LIMIT_CONCURRENCY = int(os.environ.get("LIMIT_CONCURRENCY", "50"))
    LIMIT_MAX_REQUESTS = int(os.environ.get("LIMIT_MAX_REQUESTS", "500"))
    BACKLOG = int(os.environ.get("BACKLOG", "128"))
    os.environ.setdefault("MAX_CONCURRENT_AI", "4")
    os.environ.setdefault("MAX_CONCURRENT_PDF", "1")
    os.environ.setdefault("MAX_CONCURRENT_LATEX", "2")
    os.environ.setdefault("MAX_CONCURRENT_REQUESTS", "50")

if __name__ == "__main__":
    print("=" * 60)
    print(f"ResumeAI starting | Tier: {TIER.upper()} | Port: {PORT}")
    print(f"  Workers:             {WORKERS}")
    print(f"  Limit concurrency:   {LIMIT_CONCURRENCY}")
    print(f"  Limit max requests:  {LIMIT_MAX_REQUESTS}")
    print(f"  Backlog:             {BACKLOG}")
    print(f"  Max concurrent AI:   {os.environ.get('MAX_CONCURRENT_AI')}")
    print(f"  Max concurrent PDF:  {os.environ.get('MAX_CONCURRENT_PDF')}")
    print(f"  Max concurrent LaTeX:{os.environ.get('MAX_CONCURRENT_LATEX')}")
    print(f"  Max total requests:  {os.environ.get('MAX_CONCURRENT_REQUESTS')}")
    if IS_FREE_TIER:
        print(f"  [Free Tier] Playwright PDF disabled, LaTeX only")
    print("=" * 60)

    uvicorn.run(
        "main:app",
        host=HOST,
        port=PORT,
        workers=WORKERS,
        limit_concurrency=LIMIT_CONCURRENCY,
        limit_max_requests=LIMIT_MAX_REQUESTS,
        backlog=BACKLOG,
        timeout_keep_alive=5,
        graceful_timeout=30,
        log_level="info",
        proxy_headers=True,
        forwarded_allow_ips="*",
    )