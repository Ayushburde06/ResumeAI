#!/usr/bin/env python3
"""Read and summarize all resume test scores."""
import json
from pathlib import Path

d = Path(__file__).resolve().parent / "ats_quick_out"
files = sorted(d.glob("resume_*.json"))
print(f"Files found: {len(files)}\n")
for f in files:
    if f.name == "resume_generated.json":
        continue
    data = json.loads(f.read_text(encoding="utf-8"))
    ats = data.get("ats_score", "?")
    jd = data.get("jd", {})
    role = jd.get("role", f.stem)
    tailored = data.get("tailored_resume", {})
    # Check buzzwords
    blob = json.dumps(tailored).lower()
    buzz = [w for w in ["dynamic", "orchestrated", "built and deployed", "leveraged", "utilized"] if w in blob]
    halluc = [w for w in ["kubernetes", "terraform", "pytorch", "tensorflow", "pinecone", "selenium", "spark", "airflow"] if w in blob]
    print(f"  {f.name}: {role:30s}  ATS={ats}  buzz={buzz or 'NONE'}  halluc={halluc or 'NONE'}")
