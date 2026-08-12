#!/usr/bin/env python3
"""Full end-to-end HTTP API test — hits every endpoint on the live server."""
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000/api"

RESUME_TEXT = """Ayushkumar Burde
Email: ayushburde156@gmail.com | Phone: +91-8600820291 | Mumbai, India

SUMMARY
Software Engineer with a Master's in Computer Applications and hands-on experience building AI-powered, cloud-based systems. Proficient in Python, React, TypeScript, and backend development with Node.js and Django. Comfortable working across RESTful APIs, NoSQL databases, and CI/CD pipelines in Agile environments.

EXPERIENCE
CrystalTech Services Pvt Ltd -- Software Engineer Intern | Indore, India | Jul 2024 -- Dec 2024
- Built microservices with Node.js and Express.js; deployed on AWS to improve cloud infrastructure response time and service reliability
- Contributed to React.js and TypeScript frontend; integrated RESTful APIs and followed Agile/SCRUM workflows with Git for version control
- Worked with MongoDB and Elasticsearch for NoSQL data storage; supported CI/CD pipelines and debugging across distributed services

EDUCATION
Tulsiramji Gaikwad Patil College of Engineering and Technology -- Master of Computer Applications | Nagpur, India | 2025
City Premier College -- Bachelor of Computer Applications | Nagpur, India | 2022

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frontend: React.js, HTML5, CSS3
Backend: Node.js, Express.js, Django, RESTful APIs, Microservices Architecture
Databases: MongoDB, SQLite, Elasticsearch, NoSQL
Cloud & DevOps: AWS, Azure, Google Cloud, CI/CD, Docker, Git, GitHub
Concepts: OOP, Agile/SCRUM, Version Control, Backend Development, AI-Driven Systems

PROJECTS
ResumeAI | React, FastAPI, Python, Playwright, AI | June 2026 -- Present
- Developed an AI-powered ATS Resume Builder with a multi-agent optimization loop, RAG-based keyword retrieval, and job description analysis for targeted resume tailoring
- Engineered a PDF export pipeline using Playwright and Jinja2 template rendering; integrated FastAPI backend with streaming SSE for real-time agent progress

NotesApp | React.js, Node.js, Express.js, MongoDB, JWT, AWS, Git
- Built a full-stack CRUD application using React, Node.js, and MongoDB; implemented JWT authentication, deployed on AWS, and served 2K+ users with reliable uptime

CV Generator | Python, Django, SQLite, HTML5, CSS3, ReportLab, Google Cloud
- Built a Django web application with PDF generation via ReportLab; implemented form validation, SQLite data persistence, and Google Cloud file storage

CERTIFICATIONS
AWS Cloud Practitioner Essentials
Google Cloud Digital Leader
""".strip()

JD = (
    "We are hiring a Backend Engineer to build REST APIs with Python and FastAPI. "
    "You will work with PostgreSQL, Redis caching, Docker, and AWS. "
    "Experience with microservices, CI/CD, and JWT authentication is required. "
    "Agile team, remote-friendly."
)

results = []
token = None
user_email = None


def log(step, ok, detail="", t=0):
    status = "OK" if ok else "FAIL"
    results.append({"step": step, "ok": ok, "detail": detail, "time": t})
    print(f"  [{'OK' if ok else 'FAIL'}] {step:35s} {t:>6.2f}s  {detail[:80]}")


def main():
    print("=" * 70)
    print("  FULL E2E HTTP API TEST")
    print("=" * 70)

    # ── 1. Health check ──────────────────────────────────────────────────────
    print("\n  -- Health & System --")
    t0 = time.time()
    r = httpx.get(f"{BASE.replace('/api','')}/health", timeout=10)
    log("GET /health", r.status_code == 200, f"status={r.status_code}", time.time() - t0)

    t0 = time.time()
    r = httpx.get(f"{BASE.replace('/api','')}/", timeout=10)
    log("GET / (root)", r.status_code == 200, f"status={r.status_code}", time.time() - t0)

    # ── 2. Auth: Register ────────────────────────────────────────────────────
    print("\n  -- Auth --")
    test_email = f"test_{int(time.time())}@test.com"
    test_name = "Test User"
    test_password = "TestPass123!"

    t0 = time.time()
    r = httpx.post(f"{BASE}/auth/register", json={
        "name": test_name, "email": test_email, "password": test_password
    }, timeout=15)
    ok = r.status_code == 200 and "token" in r.json()
    if ok:
        token = r.json()["token"]
        user = r.json().get("user", {})
        log("POST /auth/register", True, f"email={test_email}, analyses_used={user.get('analyses_used')}", time.time() - t0)
    else:
        log("POST /auth/register", False, f"status={r.status_code}, body={r.text[:100]}", time.time() - t0)
        return

    # ── 3. Auth: Me ──────────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.get(f"{BASE}/auth/me", headers={"Authorization": f"Bearer {token}"}, timeout=10)
    ok = r.status_code == 200 and r.json().get("email") == test_email
    log("GET /auth/me", ok, f"analyses_used={r.json().get('analyses_used')}, limit={r.json().get('analyses_limit')}", time.time() - t0)

    # ── 4. Auth: Login ───────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/auth/login", json={"email": test_email, "password": test_password}, timeout=15)
    ok = r.status_code == 200 and "token" in r.json()
    if ok:
        token = r.json()["token"]  # refresh token
    log("POST /auth/login", ok, f"status={r.status_code}", time.time() - t0)

    headers = {"Authorization": f"Bearer {token}"}

    # ── 5. Models list ───────────────────────────────────────────────────────
    print("\n  -- Models --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/models", headers=headers, timeout=10)
    models = r.json() if r.status_code == 200 else []
    if isinstance(models, dict):
        models = models.get("models", [])
    log("GET /models", r.status_code == 200, f"models={[m.get('id') if isinstance(m, dict) else m for m in models]}", time.time() - t0)

    # ── 6. Analyze (the main pipeline) ───────────────────────────────────────
    print("\n  -- AI Pipeline --")
    # Use the pre-built test PDF
    pdf_path = Path(__file__).resolve().parent / "ats_quick_out" / "test_resume.pdf"
    resume_bytes = pdf_path.read_bytes()
    resume_file = ("test_resume.pdf", resume_bytes, "application/pdf")

    t0 = time.time()
    r = httpx.post(
        f"{BASE}/analyze",
        headers=headers,
        data={"job_description": JD, "model": ""},
        files={"resume_file": resume_file},
        timeout=120,
    )
    data = {}
    tailored = {}
    if r.status_code == 200:
        data = r.json()
        ats = data.get("ats_score", "?")
        tailored = data.get("tailored_resume", {})
        cover = data.get("cover_letter", "")
        email_body = data.get("application_email", "")
        analyses_used = data.get("analyses_used", "?")
        analyses_limit = data.get("analyses_limit", "?")
        log("POST /analyze", True,
            f"ATS={ats}, analyses_used={analyses_used}/{analyses_limit}, cover={len(str(cover))} chars, email={len(str(email_body))} chars",
            time.time() - t0)
    else:
        log("POST /analyze", False, f"status={r.status_code}, body={r.text[:150]}", time.time() - t0)

    # ── 7. Suggest job search ────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/suggest-job-search", headers=headers,
                   files={"resume_file": resume_file},
                   data={"job_description": JD, "model": ""},
                   timeout=60)
    ok = r.status_code == 200
    detail = f"search_term={r.json().get('search_term','?')}" if ok else f"status={r.status_code}"
    log("POST /suggest-job-search", ok, detail, time.time() - t0)

    # ── 8. Improve ATS ───────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/improve-ats", headers=headers, json={
        "tailored_resume": tailored,
        "job_description": JD,
        "job_analysis": data.get("job_analysis", {}),
        "missing_keywords": data.get("missing_keywords", []),
        "model": "",
    }, timeout=120)
    ok = r.status_code == 200
    detail = f"improved={len(str(r.json()))} chars" if ok else f"status={r.status_code}, body={r.text[:100]}"
    log("POST /improve-ats", ok, detail, time.time() - t0)

    # ── 9. Rescore ATS ───────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/rescore-ats", headers=headers, json={
        "tailored_resume": tailored, "job_description": JD,
    }, timeout=30)
    ok = r.status_code == 200
    detail = f"score={r.json().get('ats_score','?')}" if ok else f"status={r.status_code}"
    log("POST /rescore-ats", ok, detail, time.time() - t0)

    # ── 10. Export PDF ───────────────────────────────────────────────────────
    print("\n  -- Export --")
    # Build a structured resume dict (what the templates expect) from the AI result
    structured_resume = {
        "personal_info": tailored.get("personal_info", {"name": "Test User", "email": "test@example.com", "phone": "555-0100", "location": "San Francisco, CA"}),
        "summary": tailored.get("summary", tailored.get("raw_text", "Experienced software engineer")),
        "experience": tailored.get("experience", []),
        "education": tailored.get("education", []),
        "skills": tailored.get("skills", []),
        "projects": tailored.get("projects", []),
        "certifications": tailored.get("certifications", []),
    }
    t0 = time.time()
    r = httpx.post(f"{BASE}/export-pdf", headers=headers, json={
        "resume": structured_resume, "template": "modern", "jd_keywords": [],
    }, timeout=60)
    ok = r.status_code == 200 and r.headers.get("content-type", "").startswith("application/pdf")
    detail = f"size={len(r.content)} bytes, type={r.headers.get('content-type','?')}" if ok else f"status={r.status_code}, body={r.text[:100]}"
    log("POST /export-pdf", ok, detail, time.time() - t0)

    # ── 11. Export LaTeX ─────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/export-latex", headers=headers, json={
        "resume": structured_resume,
        "template": "harshibar",
    }, timeout=30)
    ok = r.status_code == 200
    detail = f"size={len(r.content)} bytes" if ok else f"status={r.status_code}, body={r.text[:80]}"
    log("POST /export-latex", ok, detail, time.time() - t0)

    # ── 12. Profile: Get (empty) ─────────────────────────────────────────────
    print("\n  -- Profile --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/profile", headers=headers, timeout=10)
    ok = r.status_code in (200, 404)
    detail = f"status={r.status_code}, has_data={bool(r.json()) if r.status_code == 200 else 'N/A'}"
    log("GET /profile", ok, detail, time.time() - t0)

    # ── 13. Profile: Save ────────────────────────────────────────────────────
    t0 = time.time()
    profile_data = {
        "personal_info": {"name": "Test User", "email": test_email, "phone": "+91-1234567890", "location": "Mumbai"},
        "summary": "Software Engineer with Python and React experience.",
        "experience": [{"title": "Software Engineer", "company": "TestCo", "start_date": "2024-01", "end_date": "present", "bullets": ["Built APIs"]}],
        "education": [{"degree": "MCA", "school": "Test College", "start_date": "2023", "end_date": "2025"}],
        "skills": {"languages": ["Python", "JavaScript"], "frameworks": ["React", "FastAPI"]},
    }
    r = httpx.put(f"{BASE}/profile", headers=headers, json=profile_data, timeout=10)
    ok = r.status_code == 200
    log("PUT /profile", ok, f"status={r.status_code}", time.time() - t0)

    # ── 14. Profile: Get (populated) ─────────────────────────────────────────
    t0 = time.time()
    r = httpx.get(f"{BASE}/profile", headers=headers, timeout=10)
    ok = r.status_code == 200 and r.json().get("career_data") is not None
    log("GET /profile (populated)", ok, f"status={r.status_code}", time.time() - t0)

    # ── 15. History: List ────────────────────────────────────────────────────
    print("\n  -- History --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/history", headers=headers, timeout=10)
    ok = r.status_code == 200
    entries = r.json() if ok else []
    detail = f"entries={len(entries) if isinstance(entries, list) else '?'}"
    log("GET /history", ok, detail, time.time() - t0)

    # ── 16. History: Save ────────────────────────────────────────────────────
    t0 = time.time()
    r = httpx.post(f"{BASE}/history/save", headers=headers, json={
        "job_title": "Backend Engineer", "ats_score": 98,
        "tailored_resume": tailored, "job_description": JD,
        "job_analysis": data.get("job_analysis", {}),
    }, timeout=10)
    ok = r.status_code == 200
    entry_id = r.json().get("id") if ok else None
    log("POST /history/save", ok, f"entry_id={entry_id}", time.time() - t0)

    # ── 17. History: Get entry ───────────────────────────────────────────────
    if entry_id:
        t0 = time.time()
        r = httpx.get(f"{BASE}/history/{entry_id}", headers=headers, timeout=10)
        ok = r.status_code == 200
        log("GET /history/{id}", ok, f"status={r.status_code}", time.time() - t0)

    # ── 18. Feedback ─────────────────────────────────────────────────────────
    print("\n  -- Feedback --")
    t0 = time.time()
    r = httpx.post(f"{BASE}/feedback", headers=headers, json={
        "history_id": entry_id, "rating": "up",
    }, timeout=10)
    ok = r.status_code == 200
    log("POST /feedback", ok, f"status={r.status_code}", time.time() - t0)

    # ── 19. Quota check: verify analyses_used incremented ────────────────────
    print("\n  -- Quota --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/auth/me", headers=headers, timeout=10)
    used = r.json().get("analyses_used", "?")
    limit = r.json().get("analyses_limit", "?")
    log("GET /auth/me (quota check)", r.status_code == 200, f"analyses_used={used}/{limit}", time.time() - t0)

    # ── 20. Unauthorized request (no token) ──────────────────────────────────
    print("\n  -- Security --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/auth/me", timeout=10)
    log("GET /auth/me (no token)", r.status_code == 401, f"status={r.status_code} (expected 401)", time.time() - t0)

    t0 = time.time()
    r = httpx.post(f"{BASE}/analyze", data={"job_description": JD}, files={"resume_file": resume_file}, timeout=10)
    log("POST /analyze (no token)", r.status_code == 401, f"status={r.status_code} (expected 401)", time.time() - t0)

    # ── 21. Agent RAG stats ──────────────────────────────────────────────────
    print("\n  -- Agent --")
    t0 = time.time()
    r = httpx.get(f"{BASE}/agent/rag-stats", headers=headers, timeout=10)
    ok = r.status_code == 200
    log("GET /agent/rag-stats", ok, f"status={r.status_code}", time.time() - t0)

    # ── Summary ──────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  E2E TEST SUMMARY")
    print("=" * 70)
    passed = sum(1 for r in results if r["ok"])
    failed = sum(1 for r in results if not r["ok"])
    total_time = sum(r["time"] for r in results)
    print(f"  Total: {len(results)}  |  Passed: {passed}  |  Failed: {failed}  |  Time: {total_time:.1f}s")
    print()
    for r in results:
        status = "OK" if r["ok"] else "FAIL"
        print(f"    [{status:4s}] {r['step']:35s} {r['time']:>6.2f}s  {r['detail'][:70]}")
    print("=" * 70)


if __name__ == "__main__":
    main()
