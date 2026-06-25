import os
import shutil
import subprocess
import threading
from dotenv import load_dotenv

load_dotenv()

# ── Security: validate all secrets before anything else starts ────────────────
from startup_check import run as _check_secrets
_check_secrets()

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from database import Base, engine
from limiter import limiter          # shared instance — also used in auth.py
from routers import analyze, jobs, auth, history, agent
import models.user    # noqa: F401
import models.history # noqa: F401
import models.stats   # noqa: F401

Base.metadata.create_all(bind=engine)

# Auto-migration: check and add the application_email column if it is missing
try:
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "resume_history" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("resume_history")]
        if "application_email" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resume_history ADD COLUMN application_email TEXT;"))
        if "quality_report" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resume_history ADD COLUMN quality_report TEXT;"))
except Exception as e:
    print(f"Migration error: {e}")

app = FastAPI(
    title="ResumeAI API",
    description="AI-powered resume tailoring — rewrites resumes for ATS and job-description match.",
    version="2.0.0",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Set ALLOWED_ORIGINS in .env as comma-separated URLs.
# Dev default: http://localhost:5173
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Security Headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    # Only set CSP on HTML responses, not API JSON
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data:;"
        )
    return response

app.include_router(analyze.router, prefix="/api")
app.include_router(jobs.router,    prefix="/api")
app.include_router(auth.router,    prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(agent.router,   prefix="/api")


@app.on_event("startup")
async def _warmup_rag():
    """Pre-load the RAG knowledge store on startup so first request is fast."""
    try:
        from services.rag_service import get_store_stats
        stats = get_store_stats()
        print(f"[RAG] Knowledge store loaded: {stats}")
    except Exception as e:
        print(f"[RAG] Warmup skipped: {e}")


# ── Persistent Puppeteer PDF server lifecycle ─────────────────────────────────

_pdf_server_proc: subprocess.Popen | None = None


def _start_pdf_server() -> None:
    """Launch pdf_server.cjs in the background and wait for its READY signal."""
    global _pdf_server_proc
    node_path = shutil.which("node")
    if not node_path:
        print("[PDF] Node.js not found — PDF server not started. Fallback to subprocess.")
        return

    from pathlib import Path
    server_script = Path(__file__).parent / "services" / "pdf_server.cjs"
    if not server_script.exists():
        print(f"[PDF] pdf_server.cjs not found at {server_script} — PDF server not started.")
        return

    port = os.environ.get("PDF_SERVER_PORT", "9009")
    env  = {**os.environ, "PDF_SERVER_PORT": port}

    try:
        proc = subprocess.Popen(
            [node_path, str(server_script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,   # merge stderr into stdout
            env=env,
            text=True,
            bufsize=1,
        )
        _pdf_server_proc = proc

        # Wait up to 20s for the READY signal
        ready = False
        for _ in range(200):  # 200 × 100 ms = 20 s
            line = proc.stdout.readline()
            if not line:
                break
            line = line.rstrip()
            print(f"[PDF-server] {line}")
            if line.startswith("READY:"):
                ready = True
                break

        if ready:
            print(f"[PDF] Persistent browser server ready on port {port}")
        else:
            print("[PDF] Server did not signal READY — will use subprocess fallback")

        # Drain remaining stdout in background thread so process doesn't block
        def _drain():
            for line in proc.stdout:
                print(f"[PDF-server] {line.rstrip()}")
        threading.Thread(target=_drain, daemon=True).start()

    except Exception as e:
        print(f"[PDF] Could not start pdf_server.cjs: {e}")


@app.on_event("startup")
async def _start_pdf_browser_server():
    """Start the persistent Puppeteer browser server in a background thread."""
    threading.Thread(target=_start_pdf_server, daemon=True).start()


@app.on_event("shutdown")
async def _stop_pdf_browser_server():
    """Gracefully terminate the PDF server process."""
    global _pdf_server_proc
    if _pdf_server_proc and _pdf_server_proc.poll() is None:
        _pdf_server_proc.terminate()
        try:
            _pdf_server_proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _pdf_server_proc.kill()
        print("[PDF] Browser server stopped")
        _pdf_server_proc = None



@app.get("/health")
async def health():
    return {"status": "ok"}




