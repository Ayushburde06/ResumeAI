"""Per-endpoint concurrency caps for heavy endpoints.

Each semaphore limits how many simultaneous requests can be in-flight
for that specific operation.  This prevents one slow user from eating
all available connections / memory / CPU cores.
"""
import asyncio
import os

# ── AI pipeline (analyze, improve-ats, suggest-job-search) ─────────────────
# These call external LLMs, parse JSON, and run RAG.
_AI_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_AI", "4"))
ai_semaphore = asyncio.Semaphore(_AI_CONCURRENT)

# ── PDF export (WeasyPrint — ~50MB RAM, pure Python, no browser) ────────
_PDF_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_PDF", "4"))
pdf_semaphore = asyncio.Semaphore(_PDF_CONCURRENT)

# ── LaTeX export ──────────────────────────────────────────────────────────
# pdflatex is CPU-bound.
_LATEX_CONCURRENT = int(os.environ.get("MAX_CONCURRENT_LATEX", "2"))
latex_semaphore = asyncio.Semaphore(_LATEX_CONCURRENT)