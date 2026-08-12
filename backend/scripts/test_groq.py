#!/usr/bin/env python3
"""Quick test: generate resume with Groq."""
import json
import os
import sys
import time
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
os.chdir(BACKEND)
from dotenv import load_dotenv

load_dotenv(BACKEND / ".env", override=True)
from services.ai_service import MODEL_REGISTRY, analyse_job_description, rewrite_resume
from services.ats_engine import compute_ats_score
from services.humanization_engine import compute_humanization_score

print("Registry:", list(MODEL_REGISTRY.keys()))
print("Default:", os.environ.get("DEFAULT_MODEL_ID"))

RESUME = """Ayushkumar Burde
Email: ayushburde156@gmail.com | Mumbai, India

SUMMARY
Software Engineer with MCA degree. Proficient in Python, React, TypeScript, Node.js, Django. Built REST APIs, microservices, CI/CD pipelines.

EXPERIENCE
CrystalTech Services -- Software Engineer Intern | Jul 2024 - Dec 2024
- Built microservices with Node.js and Express.js; deployed on AWS
- Contributed to React.js frontend; integrated RESTful APIs; Agile/SCRUM

SKILLS
Python, JavaScript, TypeScript, React.js, Node.js, Express.js, Django, MongoDB, AWS, Docker, Git, CI/CD
"""

JD = "Backend Engineer with Python, FastAPI, PostgreSQL, Redis, Docker, AWS, microservices, CI/CD, JWT. Agile team."

t0 = time.time()
print("\nAnalyzing JD...", flush=True)
ja = analyse_job_description(JD, model_id="groq")
print(f"  Title: {ja.get('job_title','?')}")

print("Tailoring resume...", flush=True)
tailored = rewrite_resume(RESUME, JD, ja, model_id="groq")
elapsed = round(time.time() - t0, 2)

ats = compute_ats_score(json.dumps(tailored), JD)
human = compute_humanization_score(tailored)
human_score = getattr(human, "score", None) or (human.get("score") if isinstance(human, dict) else None)

print(f"\nElapsed: {elapsed}s")
print(f"ATS: {ats.score}  matched={len(ats.matched_keywords)}/{ats.total_keywords}")
print(f"Humanization: {human_score}")
print(f"\nSummary: {tailored.get('summary','')[:300]}")
print("\nExperience[0] bullets:")
for b in (tailored.get("experience") or [{}])[0].get("bullets", [])[:3]:
    print(f"  - {b[:120]}")
