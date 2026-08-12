#!/usr/bin/env python3
"""
50-JD ATS battery — learns how resume generation behaves across diverse roles.

Runs rewrite_resume + compute_ats_score for each JD against a fixed source resume.
Saves incremental progress so it can resume if interrupted.
"""
from __future__ import annotations

import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# Ensure backend imports resolve when launched from repo root or backend/
BACKEND = Path(__file__).resolve().parent.parent
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

os.chdir(BACKEND)

from dotenv import load_dotenv

load_dotenv(BACKEND / ".env", override=True)

from services.ai_service import MODEL_REGISTRY, analyse_job_description, rewrite_resume
from services.ats_engine import compute_ats_score
from services.humanization_engine import compute_humanization_score
from services.quality_checks import assess_resume_quality

OUT_DIR = Path(__file__).resolve().parent / "ats_battery_out"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_PATH = OUT_DIR / "results.jsonl"
SUMMARY_PATH = OUT_DIR / "summary.json"

# Realistic source resume (plain text — mirrors ayush_resume.tex content)
RESUME_TEXT = """
Ayushkumar Burde
Email: ayushburde156@gmail.com | Phone: +91-8600820291 | Mumbai, India
LinkedIn | GitHub | Website

SUMMARY
Software Engineer with a Master's in Computer Applications and hands-on experience building AI-powered, cloud-based systems. Proficient in Python, React, TypeScript, and backend development with Node.js and Django. Comfortable working across RESTful APIs, NoSQL databases, and CI/CD pipelines in Agile environments.

EXPERIENCE
CrystalTech Services Pvt Ltd — Software Engineer Intern | Indore, India | Jul 2024 -- Dec 2024
- Built microservices with Node.js and Express.js; deployed on AWS to improve cloud infrastructure response time and service reliability
- Contributed to React.js and TypeScript frontend; integrated RESTful APIs and followed Agile/SCRUM workflows with Git for version control
- Worked with MongoDB and Elasticsearch for NoSQL data storage; supported CI/CD pipelines and debugging across distributed services

EDUCATION
Tulsiramji Gaikwad Patil College of Engineering and Technology — Master of Computer Applications | Nagpur, India | 2025
City Premier College — Bachelor of Computer Applications | Nagpur, India | 2022

SKILLS
Languages: Python, JavaScript, TypeScript, SQL
Frontend: React.js, HTML5, CSS3
Backend: Node.js, Express.js, Django, RESTful APIs, Microservices Architecture
Databases: MongoDB, SQLite, Elasticsearch, NoSQL
Cloud & DevOps: AWS, Azure, Google Cloud, CI/CD, Docker, Git, GitHub
Concepts: OOP, Agile/SCRUM, Version Control, Backend Development, AI-Driven Systems, Software Development

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

# 50 diverse dummy JDs spanning roles, seniority, and stacks
JDS: list[dict] = [
    {"id": 1, "role": "Backend Engineer", "seniority": "mid", "text": "We are hiring a Backend Engineer to build REST APIs with Python and FastAPI. You will work with PostgreSQL, Redis caching, Docker, and AWS. Experience with microservices, CI/CD, and JWT authentication is required. Agile team, remote-friendly."},
    {"id": 2, "role": "Frontend Engineer", "seniority": "mid", "text": "Frontend Engineer needed for a React and TypeScript product. Must know HTML5, CSS3, responsive design, state management, REST API integration, and Git. Bonus: Next.js, accessibility, and performance optimization."},
    {"id": 3, "role": "Full Stack Developer", "seniority": "mid", "text": "Full Stack Developer role using React, Node.js, Express.js, MongoDB, and AWS. Build end-to-end features, write RESTful APIs, implement JWT auth, and deploy via CI/CD pipelines. Strong JavaScript and TypeScript preferred."},
    {"id": 4, "role": "AI Engineer", "seniority": "junior", "text": "Junior AI Engineer to work on LLM applications, prompt engineering, RAG pipelines, embeddings, and vector databases. Python required. Experience with FastAPI, OpenAI APIs, and document retrieval systems is a plus."},
    {"id": 5, "role": "DevOps Engineer", "seniority": "mid", "text": "DevOps Engineer to own CI/CD, Docker, Kubernetes, AWS, Terraform, monitoring with Prometheus/Grafana, and GitHub Actions. Script automation in Python or Bash. Focus on reliability and deployment speed."},
    {"id": 6, "role": "Software Engineer Intern", "seniority": "intern", "text": "Software Engineer Intern opportunity. Learn to build web apps with React, Node.js, MongoDB, and Git. Exposure to Agile/SCRUM, REST APIs, and cloud basics on AWS. Strong fundamentals in JavaScript or Python required."},
    {"id": 7, "role": "Python Developer", "seniority": "mid", "text": "Python Developer for backend services using Django or FastAPI, SQL databases, REST APIs, unit testing, and Docker. Experience with AWS deployment and Git workflows expected. Clean code and OOP skills required."},
    {"id": 8, "role": "React Developer", "seniority": "mid", "text": "React Developer to ship UI features in React.js and TypeScript. Integrate RESTful APIs, write reusable components, optimize performance, and collaborate in Agile sprints. Familiarity with CSS3 and Git is mandatory."},
    {"id": 9, "role": "Node.js Developer", "seniority": "mid", "text": "Node.js Developer building microservices with Express.js, MongoDB, JWT, and REST APIs. Deploy on AWS, participate in CI/CD, and debug distributed services. TypeScript experience preferred."},
    {"id": 10, "role": "Cloud Engineer", "seniority": "mid", "text": "Cloud Engineer focused on AWS architecture, Docker containers, CI/CD pipelines, Infrastructure as Code, and monitoring. Python scripting and experience with Azure or GCP is advantageous."},
    {"id": 11, "role": "ML Engineer", "seniority": "mid", "text": "Machine Learning Engineer to train models, build data pipelines, use Python, PyTorch or TensorFlow, feature engineering, model evaluation, and deploy inference APIs with FastAPI on cloud."},
    {"id": 12, "role": "Data Engineer", "seniority": "mid", "text": "Data Engineer for ETL pipelines, SQL, Python, Spark, Airflow, data warehousing, and cloud storage on AWS/GCP. Experience with Elasticsearch or NoSQL a plus. Strong data modeling skills required."},
    {"id": 13, "role": "SRE", "seniority": "mid", "text": "Site Reliability Engineer to improve uptime, observability, incident response, Kubernetes, Docker, AWS, SLIs/SLOs, and automation. Python preferred. Experience with CI/CD and on-call rotations."},
    {"id": 14, "role": "Mobile Developer", "seniority": "mid", "text": "Mobile Developer for React Native apps with TypeScript, REST API integration, push notifications, and App Store releases. Understanding of native iOS/Android basics and Git workflows required."},
    {"id": 15, "role": "QA Automation Engineer", "seniority": "mid", "text": "QA Automation Engineer writing end-to-end tests with Playwright or Selenium, API testing, CI/CD integration, and test strategy. JavaScript or Python skills required. Agile collaboration expected."},
    {"id": 16, "role": "Security Engineer", "seniority": "mid", "text": "Application Security Engineer focusing on secure coding, JWT/OAuth, vulnerability scanning, OWASP, threat modeling, and cloud security on AWS. Python scripting and CI/CD security gates preferred."},
    {"id": 17, "role": "Platform Engineer", "seniority": "senior", "text": "Platform Engineer to build internal developer platforms with Kubernetes, Docker, Terraform, AWS, CI/CD, observability, and self-service tooling. Strong Python and systems design required."},
    {"id": 18, "role": "Solutions Architect", "seniority": "senior", "text": "Solutions Architect designing cloud architectures on AWS/Azure/GCP, microservices, REST APIs, data stores, and CI/CD. Communicate trade-offs with stakeholders. Hands-on prototyping with Python preferred."},
    {"id": 19, "role": "Product Engineer", "seniority": "mid", "text": "Product Engineer owning features end-to-end with React, TypeScript, Node.js, PostgreSQL, and AWS. Ship iteratively in Agile, measure impact, and collaborate with design and product."},
    {"id": 20, "role": "API Engineer", "seniority": "mid", "text": "API Engineer specializing in RESTful API design, OpenAPI/Swagger, authentication (JWT), rate limiting, Python FastAPI or Node Express, PostgreSQL, and API gateway patterns on AWS."},
    {"id": 21, "role": "Django Developer", "seniority": "mid", "text": "Django Developer to build web apps with Django, Python, SQLite/PostgreSQL, HTML/CSS templates, form validation, authentication, and PDF generation. Deploy on cloud and use Git."},
    {"id": 22, "role": "TypeScript Engineer", "seniority": "mid", "text": "TypeScript Engineer for frontend and backend services using React, Node.js, Express, strong typing, unit tests, and REST integrations. Experience with MongoDB and AWS deployment desired."},
    {"id": 23, "role": "GenAI Developer", "seniority": "mid", "text": "GenAI Developer building chatbots and assistants with LLMs, RAG, embeddings, vector DBs (Pinecone/Chroma), Python, FastAPI, and prompt evaluation. Knowledge of streaming responses is a plus."},
    {"id": 24, "role": "Backend Intern", "seniority": "intern", "text": "Backend Intern to learn Node.js, Express.js, MongoDB, REST APIs, Git, and basic AWS. Mentorship provided. Interest in microservices and CI/CD welcomed. Python familiarity helpful."},
    {"id": 25, "role": "Frontend Intern", "seniority": "intern", "text": "Frontend Intern working with React.js, HTML5, CSS3, JavaScript, and Git. Assist with UI bugs, API integration, and Agile ceremonies. Desire to learn TypeScript preferred."},
    {"id": 26, "role": "Full Stack Intern", "seniority": "intern", "text": "Full Stack Intern building small features across React and Node.js with MongoDB. Learn JWT auth, REST APIs, Git workflows, and deployment basics on AWS. Strong learning mindset required."},
    {"id": 27, "role": "Software Engineer", "seniority": "junior", "text": "Junior Software Engineer for a SaaS product. Stack: Python, FastAPI, React, PostgreSQL, Docker, AWS. Write clean code, review PRs, and participate in Agile sprints. CS fundamentals required."},
    {"id": 28, "role": "Software Engineer", "seniority": "senior", "text": "Senior Software Engineer to lead architecture for microservices using Python, FastAPI, React, TypeScript, PostgreSQL, Redis, Kubernetes, and AWS. Mentor juniors, drive CI/CD quality, and own reliability."},
    {"id": 29, "role": "NLP Engineer", "seniority": "mid", "text": "NLP Engineer working on text classification, information extraction, embeddings, RAG, Python, Hugging Face, and FastAPI serving. Experience with evaluation metrics and cloud GPUs preferred."},
    {"id": 30, "role": "Analytics Engineer", "seniority": "mid", "text": "Analytics Engineer building dashboards and data models with SQL, Python, dbt, warehouse tech, and BI tools. Collaborate with product on metrics. Cloud experience on GCP or AWS required."},
    {"id": 31, "role": "Integration Engineer", "seniority": "mid", "text": "Integration Engineer connecting third-party APIs, webhooks, OAuth, REST/JSON, Node.js or Python, retries/idempotency, and monitoring. Experience with AWS and Git required."},
    {"id": 32, "role": "Search Engineer", "seniority": "mid", "text": "Search Engineer optimizing Elasticsearch/OpenSearch relevance, indexing pipelines, Python services, query DSL, and ranking. Build APIs for search experiences and monitor latency."},
    {"id": 33, "role": "Automation Engineer", "seniority": "mid", "text": "Automation Engineer creating workflow automation with Python, APIs, scripting, CI/CD, and cloud functions on AWS/GCP. Improve operational efficiency and document runbooks."},
    {"id": 34, "role": "Technical Support Engineer", "seniority": "junior", "text": "Technical Support Engineer for a developer platform. Diagnose API issues, read logs, reproduce bugs with Postman, basic SQL, and escalate clearly. Familiarity with REST and Git helpful."},
    {"id": 35, "role": "Growth Engineer", "seniority": "mid", "text": "Growth Engineer shipping experiments in React, TypeScript, Node.js, analytics events, A/B testing, and AWS. Fast iteration and data-informed decisions. SQL familiarity preferred."},
    {"id": 36, "role": "Systems Engineer", "seniority": "mid", "text": "Systems Engineer managing Linux servers, networking basics, Docker, monitoring, backups, and automation scripts in Python/Bash. Cloud exposure (AWS) and CI/CD experience preferred."},
    {"id": 37, "role": "Database Developer", "seniority": "mid", "text": "Database Developer specializing in SQL, PostgreSQL/MySQL, query optimization, indexing, migrations, and data integrity. Python for tooling. Experience with MongoDB/NoSQL a plus."},
    {"id": 38, "role": "UI Engineer", "seniority": "mid", "text": "UI Engineer crafting polished interfaces with React, TypeScript, CSS3, design systems, accessibility (a11y), and performance. Collaborate with designers. Git and REST API skills required."},
    {"id": 39, "role": "BFF Engineer", "seniority": "mid", "text": "Backend-for-Frontend Engineer building GraphQL or REST aggregation layers in Node.js/TypeScript, caching, auth, and React client contracts. AWS deployment and observability expected."},
    {"id": 40, "role": "LLM Ops Engineer", "seniority": "mid", "text": "LLM Ops Engineer managing prompt versioning, evaluation harnesses, RAG quality, cost controls, FastAPI services, Python tooling, and monitoring of LLM latency/error rates on cloud."},
    {"id": 41, "role": "Startup Founding Engineer", "seniority": "mid", "text": "Founding Engineer at an early-stage startup. Wear many hats: React, FastAPI/Python, Postgres, Docker, AWS, CI/CD, and product sense. Ship fast, talk to users, and keep systems simple."},
    {"id": 42, "role": "Enterprise Java Developer", "seniority": "mid", "text": "Java Developer for enterprise services using Spring Boot, REST APIs, SQL databases, microservices, and CI/CD. Docker and AWS experience preferred. Note: Python/JS candidates may also apply if willing to learn Java."},
    {"id": 43, "role": "Go Backend Engineer", "seniority": "mid", "text": "Go Backend Engineer building high-performance services, gRPC/REST, PostgreSQL, Docker, Kubernetes, and AWS. Strong concurrency skills. Candidates with Python microservices experience considered."},
    {"id": 44, "role": "PHP Laravel Developer", "seniority": "mid", "text": "Laravel Developer for web apps with PHP, MySQL, Blade templates, REST APIs, and deployment on Linux/AWS. Candidates with Django/Python web experience may transition."},
    {"id": 45, "role": "Blockchain Engineer", "seniority": "mid", "text": "Blockchain Engineer for smart contracts and web3 backends. Solidity, ethers.js, Node.js, TypeScript, and security audits. Backend API experience with Node/Python valued."},
    {"id": 46, "role": "Game Backend Engineer", "seniority": "mid", "text": "Game Backend Engineer building realtime services, Node.js or Python, Redis, WebSockets, auth, matchmaking APIs, and AWS. Experience with scalable REST APIs required."},
    {"id": 47, "role": "Embedded Software Engineer", "seniority": "mid", "text": "Embedded Software Engineer with C/C++, RTOS, hardware interfaces, and debugging. Python scripting for tools. Cloud/web experience not primary but useful for device dashboards."},
    {"id": 48, "role": "Technical Writer Engineer", "seniority": "junior", "text": "Developer Advocate / Technical Writer who can also build demos in Python/JavaScript, document REST APIs, maintain docs sites (React/MDX), and use Git. Clear writing required."},
    {"id": 49, "role": "Remote Backend Contractor", "seniority": "mid", "text": "Contract Backend Developer (3 months) for FastAPI + PostgreSQL + Docker + AWS. Deliver JWT-secured REST APIs, write tests, and hand off CI/CD. Clear communication and Git discipline required. Stipend performance-based. Work from home / Remote. Monday syncs."},
    {"id": 50, "role": "AI Resume Product Engineer", "seniority": "mid", "text": "Engineer for an AI resume product: Python, FastAPI, React, TypeScript, Playwright PDF rendering, RAG keyword retrieval, ATS scoring, multi-agent loops, SSE streaming, Docker, and AWS. Truthful content rewriting without hallucinations is critical."},
]


def _loaded_ids() -> set[int]:
    done: set[int] = set()
    if not RESULTS_PATH.exists():
        return done
    with RESULTS_PATH.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                done.add(json.loads(line)["id"])
            except Exception:
                continue
    return done


def _validate_structure(resume: dict) -> dict:
    pi = resume.get("personal_info") or {}
    skills = resume.get("skills") or {}
    experience = resume.get("experience") or []
    projects = resume.get("projects") or []
    education = resume.get("education") or []

    issues = []
    if not (pi.get("name") or "").strip():
        issues.append("missing_name")
    if not (resume.get("summary") or "").strip():
        issues.append("empty_summary")
    if not experience:
        issues.append("no_experience")
    if not projects:
        issues.append("no_projects")
    if not education:
        issues.append("no_education")
    if not any(skills.get(k) for k in ("languages", "frameworks", "databases", "tools", "concepts") if isinstance(skills, dict)):
        # skills may be flat list in some outputs
        if not skills:
            issues.append("empty_skills")

    # Bullet sanity
    empty_bullets = 0
    long_bullets = 0
    for exp in experience:
        for b in exp.get("bullets") or []:
            if not str(b).strip():
                empty_bullets += 1
            if len(str(b)) > 220:
                long_bullets += 1
    for proj in projects:
        for b in proj.get("bullets") or []:
            if not str(b).strip():
                empty_bullets += 1
            if len(str(b)) > 220:
                long_bullets += 1
    if empty_bullets:
        issues.append(f"empty_bullets:{empty_bullets}")
    if long_bullets:
        issues.append(f"long_bullets:{long_bullets}")

    # Hallucination-ish signals vs source (very rough)
    invented = []
    resume_blob = json.dumps(resume).lower()
    for forbidden in ("kubernetes", "terraform", "pytorch", "tensorflow", "spring boot", "golang", "solidity", "php", "laravel"):
        if forbidden in resume_blob and forbidden not in RESUME_TEXT.lower():
            # only flag if skill-looking presence
            invented.append(forbidden)

    return {
        "ok": len(issues) == 0 and len(invented) == 0,
        "issues": issues,
        "possible_inventions": invented,
        "exp_count": len(experience),
        "project_count": len(projects),
        "summary_len": len(resume.get("summary") or ""),
    }


def run_one(jd: dict, model_id: str | None) -> dict:
    t0 = time.time()
    row = {
        "id": jd["id"],
        "role": jd["role"],
        "seniority": jd["seniority"],
        "model": model_id or os.environ.get("DEFAULT_MODEL_ID", "glm"),
        "ok": False,
        "error": None,
        "elapsed_s": 0,
    }
    try:
        job_analysis = analyse_job_description(jd["text"], model_id=model_id)
        tailored = rewrite_resume(RESUME_TEXT, jd["text"], job_analysis, model_id=model_id)
        ats = compute_ats_score(json.dumps(tailored), jd["text"])
        ats_payload = {
            "score": ats.score,
            "matched_keywords": ats.matched_keywords,
            "missing_keywords": ats.missing_keywords,
        }
        quality = assess_resume_quality(tailored, jd["text"], None, ats_payload)
        human = compute_humanization_score(tailored)
        structure = _validate_structure(tailored if isinstance(tailored, dict) else {})

        human_score = getattr(human, "score", None)
        if human_score is None and isinstance(human, dict):
            human_score = human.get("score")

        row.update(
            {
                "ok": True,
                "ats_score": ats.score,
                "matched": len(ats.matched_keywords or []),
                "missing": len(ats.missing_keywords or []),
                "missing_sample": (ats.missing_keywords or [])[:8],
                "matched_sample": (ats.matched_keywords or [])[:8],
                "job_title": (job_analysis or {}).get("job_title"),
                "humanization": human_score,
                "quality_signal": (quality or {}).get("final_signal") if isinstance(quality, dict) else None,
                "structure": structure,
                "summary_preview": (tailored.get("summary") or "")[:180] if isinstance(tailored, dict) else "",
            }
        )
        # Persist full resume for later inspection
        (OUT_DIR / f"resume_{jd['id']:02d}.json").write_text(
            json.dumps({"jd": jd, "job_analysis": job_analysis, "tailored_resume": tailored, "ats": {
                "score": ats.score,
                "matched_keywords": ats.matched_keywords,
                "missing_keywords": ats.missing_keywords,
            }}, indent=2),
            encoding="utf-8",
        )
    except Exception as e:
        row["error"] = f"{type(e).__name__}: {e}"
        row["traceback"] = traceback.format_exc()[-2000:]
    row["elapsed_s"] = round(time.time() - t0, 2)
    return row


def append_result(row: dict) -> None:
    with RESULTS_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
        f.flush()


def build_summary() -> dict:
    rows = []
    if RESULTS_PATH.exists():
        with RESULTS_PATH.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    rows.append(json.loads(line))
    ok_rows = [r for r in rows if r.get("ok")]
    fail_rows = [r for r in rows if not r.get("ok")]
    scores = [r["ats_score"] for r in ok_rows if "ats_score" in r]
    inventions = []
    structure_issues = []
    for r in ok_rows:
        st = r.get("structure") or {}
        for inv in st.get("possible_inventions") or []:
            inventions.append({"id": r["id"], "role": r["role"], "term": inv})
        for issue in st.get("issues") or []:
            structure_issues.append({"id": r["id"], "role": r["role"], "issue": issue})

    by_bucket = {"0-39": 0, "40-59": 0, "60-79": 0, "80-89": 0, "90-100": 0}
    for s in scores:
        if s < 40:
            by_bucket["0-39"] += 1
        elif s < 60:
            by_bucket["40-59"] += 1
        elif s < 80:
            by_bucket["60-79"] += 1
        elif s < 90:
            by_bucket["80-89"] += 1
        else:
            by_bucket["90-100"] += 1

    summary = {
        "total": len(rows),
        "ok": len(ok_rows),
        "failed": len(fail_rows),
        "avg_ats": round(sum(scores) / len(scores), 1) if scores else None,
        "min_ats": min(scores) if scores else None,
        "max_ats": max(scores) if scores else None,
        "score_buckets": by_bucket,
        "failures": [{"id": r["id"], "role": r["role"], "error": r.get("error")} for r in fail_rows],
        "lowest_scores": sorted(ok_rows, key=lambda r: r.get("ats_score", 0))[:10],
        "highest_scores": sorted(ok_rows, key=lambda r: r.get("ats_score", 0), reverse=True)[:10],
        "invention_flags": inventions,
        "structure_issue_counts": {},
        "avg_elapsed_s": round(sum(r.get("elapsed_s", 0) for r in rows) / len(rows), 1) if rows else None,
    }
    for item in structure_issues:
        key = item["issue"].split(":")[0]
        summary["structure_issue_counts"][key] = summary["structure_issue_counts"].get(key, 0) + 1

    SUMMARY_PATH.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")
    return summary


def main():
    model_id = os.environ.get("BATTERY_MODEL") or os.environ.get("DEFAULT_MODEL_ID") or "glm"
    workers = int(os.environ.get("BATTERY_WORKERS", "2"))

    print("=" * 60)
    print("50-JD ATS BATTERY")
    print(f"Model registry: {list(MODEL_REGISTRY.keys())}")
    print(f"Using model: {model_id}")
    print(f"Workers: {workers}")
    print(f"Output: {OUT_DIR}")
    print("=" * 60)

    if model_id not in MODEL_REGISTRY and MODEL_REGISTRY:
        model_id = next(iter(MODEL_REGISTRY))
        print(f"Fallback model: {model_id}")

    done = _loaded_ids()
    pending = [jd for jd in JDS if jd["id"] not in done]
    print(f"Already done: {len(done)} | Pending: {len(pending)}")

    if not pending:
        summary = build_summary()
        print(json.dumps(summary, indent=2, default=str)[:3000])
        return

    # Run sequentially first if workers=1, else small pool
    if workers <= 1:
        for jd in pending:
            print(f"\n>>> [{jd['id']:02d}/50] {jd['role']} ({jd['seniority']}) ...", flush=True)
            row = run_one(jd, model_id)
            append_result(row)
            if row["ok"]:
                print(
                    f"    ATS={row.get('ats_score')} matched={row.get('matched')} "
                    f"missing={row.get('missing')} issues={row.get('structure', {}).get('issues')} "
                    f"inventions={row.get('structure', {}).get('possible_inventions')} "
                    f"({row['elapsed_s']}s)",
                    flush=True,
                )
            else:
                print(f"    FAIL: {row.get('error')} ({row['elapsed_s']}s)", flush=True)
            build_summary()
    else:
        with ThreadPoolExecutor(max_workers=workers) as pool:
            futs = {pool.submit(run_one, jd, model_id): jd for jd in pending}
            for fut in as_completed(futs):
                jd = futs[fut]
                row = fut.result()
                append_result(row)
                if row["ok"]:
                    print(
                        f"[{row['id']:02d}/50] {row['role']}: ATS={row.get('ats_score')} "
                        f"miss={row.get('missing')} invent={row.get('structure', {}).get('possible_inventions')} "
                        f"({row['elapsed_s']}s)",
                        flush=True,
                    )
                else:
                    print(f"[{row['id']:02d}/50] {row['role']}: FAIL {row.get('error')}", flush=True)
                build_summary()

    summary = build_summary()
    print("\n" + "=" * 60)
    print("FINAL SUMMARY")
    print("=" * 60)
    print(json.dumps({k: summary[k] for k in (
        "total", "ok", "failed", "avg_ats", "min_ats", "max_ats", "score_buckets",
        "structure_issue_counts", "avg_elapsed_s",
    )}, indent=2))
    print(f"\nFailures: {len(summary['failures'])}")
    for f in summary["failures"][:10]:
        print(f"  - #{f['id']} {f['role']}: {f['error']}")
    print(f"Invention flags: {len(summary['invention_flags'])}")
    for inv in summary["invention_flags"][:15]:
        print(f"  - #{inv['id']} {inv['role']}: {inv['term']}")
    print(f"\nWrote {SUMMARY_PATH}")


if __name__ == "__main__":
    main()
