import os
from dotenv import load_dotenv

load_dotenv()

# ── Security: validate all secrets before anything else starts ────────────────
from startup_check import run as _check_secrets
_check_secrets()

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from database import Base, engine
from limiter import limiter          # shared instance — also used in auth.py
from routers import analyze, jobs, auth, history, agent, feedback, admin
import models.user     # noqa: F401
import models.history  # noqa: F401
import models.stats    # noqa: F401
import models.learning # noqa: F401  (LearningExample + DeltaPattern)

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
        if "matched_keywords" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resume_history ADD COLUMN matched_keywords TEXT;"))
        if "missing_keywords" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resume_history ADD COLUMN missing_keywords TEXT;"))
        if "total_keywords" not in columns:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE resume_history ADD COLUMN total_keywords INTEGER;"))
    # Migrate learning_examples: add user_approved + history_id if missing
    if "learning_examples" in inspector.get_table_names():
        le_cols = [c["name"] for c in inspector.get_columns("learning_examples")]
        if "user_approved" not in le_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE learning_examples ADD COLUMN user_approved INTEGER;"))
        if "history_id" not in le_cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE learning_examples ADD COLUMN history_id INTEGER;"))
except Exception as e:
    print(f"Migration error: {e}")

_is_production = os.environ.get("ENV", "development").lower() == "production"

app = FastAPI(
    title="ResumeAI API",
    description="AI-powered resume tailoring — rewrites resumes for ATS and job-description match.",
    version="2.0.0",
    # Disable interactive docs in production to reduce attack surface
    docs_url=None if _is_production else "/docs",
    redoc_url=None if _is_production else "/redoc",
    openapi_url=None if _is_production else "/openapi.json",
)

# ── CORS ─────────────────────────────────────────────────────────────────────
# Set ALLOWED_ORIGINS in .env as comma-separated URLs.
# Dev default: http://localhost:5173
_raw_origins = os.environ.get("ALLOWED_ORIGINS", "http://localhost:5173")
ALLOWED_ORIGINS = [o.strip() for o in _raw_origins.split(",") if o.strip()]

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
# SlowAPIMiddleware enforces per-route limits and adds standard rate-limit headers
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# ── Request body size limiter (non-upload routes) ─────────────────────────────
_MAX_JSON_BODY = 512 * 1024  # 512 KB — enough for any resume JSON

@app.middleware("http")
async def limit_json_body_size(request: Request, call_next) -> Response:
    content_type = request.headers.get("content-type", "")
    # Only cap JSON bodies; file uploads are capped inside their own router
    if "multipart/form-data" not in content_type:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > _MAX_JSON_BODY:
            from fastapi.responses import JSONResponse
            return JSONResponse(
                status_code=413,
                content={"detail": "Request body too large."},
            )
    return await call_next(request)


# ── Security Headers ──────────────────────────────────────────────────────────
@app.middleware("http")
async def add_security_headers(request: Request, call_next) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()"
    response.headers["Cross-Origin-Opener-Policy"] = "same-origin"
    response.headers["Cross-Origin-Resource-Policy"] = "same-origin"
    if request.url.scheme == "https" or request.headers.get("x-forwarded-proto") == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    # Only set CSP on HTML responses, not API JSON
    if "text/html" in response.headers.get("content-type", ""):
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "frame-ancestors 'none'; "
            "object-src 'none'; "
            "script-src 'self' 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src 'self' https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self'; "
        )
    return response

app.include_router(analyze.router,  prefix="/api")
app.include_router(jobs.router,     prefix="/api")
app.include_router(auth.router,     prefix="/api")
app.include_router(history.router,  prefix="/api")
app.include_router(agent.router,    prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(admin.router,    prefix="/api")


@app.on_event("startup")
async def _warmup_rag():
    """Pre-load the RAG knowledge store on startup so first request is fast."""
    try:
        from services.rag_service import get_store_stats
        stats = get_store_stats()
        print(f"[RAG] Knowledge store loaded: {stats}")
    except Exception as e:
        print(f"[RAG] Warmup skipped: {e}")




@app.get("/health")
async def health():
    return {"status": "ok"}



