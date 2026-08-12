#!/usr/bin/env python3
"""
batch_process.py
================
Process all JD files in /JD/ folder against the candidate's base resume.
Saves per-JD output to /output/<jd_name>/ with:
  - resume.json
  - resume.pdf          (Issue 6)
  - cover_letter.json
  - email.json
  - linkedin.json
  - interview_prep.json (Issue 13)
  - ats_score.json      (Issue 14)

Usage:
    python batch_process.py
    python batch_process.py --resume-json output/c3/resume.json
    python batch_process.py --hide-low-gpa 7.0
    python batch_process.py --jd JD/c3.docx --jd JD/c4.docx
"""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

# ── Bootstrap: make the backend package importable ────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent
BACKEND   = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from dotenv import load_dotenv
load_dotenv(BACKEND / ".env", override=True)

from services.ai_service import (
    analyse_job_description,
    generate_cover_letter,
    generate_application_email,
    generate_linkedin_message,
    generate_interview_prep,
    rewrite_resume,
)
from services.ats_engine import compute_ats_score
from services.pdf_generator import generate_pdf_sync, generate_cover_letter_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
log = logging.getLogger("batch")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_docx_text(path: Path) -> str:
    """Extract plain text from a .docx file via python-docx."""
    try:
        from docx import Document
    except ImportError:
        log.error("python-docx not installed. Run: pip install python-docx")
        sys.exit(1)
    doc = Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs)


def _suppress_low_gpa(resume: dict, threshold: float) -> dict:
    """Issue 8: Remove GPA fields below the given threshold (normalised to /10)."""
    for edu in resume.get("education", []):
        gpa_raw = str(edu.get("gpa", "")).strip()
        if not gpa_raw:
            continue
        try:
            parts = gpa_raw.split("/")
            gpa_val = float(parts[0])
            scale   = float(parts[1]) if len(parts) > 1 else 10.0
            normalised = gpa_val * 10.0 / scale
            if normalised < threshold:
                edu["gpa"] = ""
                log.info("  GPA %.2f/%.0f suppressed (below threshold %.1f/10)",
                         gpa_val, scale, threshold)
        except (ValueError, IndexError):
            pass
    return resume


def _save(path: Path, data: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    log.info("  Saved %s", path.name)


# ── Core per-JD pipeline ──────────────────────────────────────────────────────

def process_one(
    jd_path: Path,
    base_resume_text: str,
    out_dir: Path,
    hide_low_gpa: float | None = None,
    pdf_template: str = "modern",
):
    jd_name = jd_path.stem
    log.info("\n── Processing JD: %s ──", jd_name)
    subfolder = out_dir / jd_name
    subfolder.mkdir(parents=True, exist_ok=True)

    # Step 1: Read JD
    if jd_path.suffix.lower() == ".docx":
        jd_text = _read_docx_text(jd_path)
    else:
        jd_text = jd_path.read_text(encoding="utf-8", errors="ignore")

    # Step 2: Analyse JD
    log.info("  Analysing JD...")
    job_analysis = analyse_job_description(jd_text)
    job_title    = job_analysis.get("job_title", jd_name)
    log.info("  Job title: %s", job_title)

    # Step 3: Rewrite resume
    log.info("  Rewriting resume...")
    tailored = rewrite_resume(
        resume_text=base_resume_text,
        jd_text=jd_text,
        job_analysis=job_analysis,
    )

    # Step 4: GPA suppression (Issue 8)
    if hide_low_gpa is not None:
        tailored = _suppress_low_gpa(tailored, hide_low_gpa)

    _save(subfolder / "resume.json", tailored)

    # Step 5: ATS score (Issue 14)
    log.info("  Computing ATS score...")
    resume_text_flat = json.dumps(tailored)
    ats_result = compute_ats_score(resume_text_flat, jd_text, job_analysis)
    ats_payload = {
        "score":            ats_result.score,
        "matched_keywords": ats_result.matched_keywords[:30],
        "missing_keywords": ats_result.missing_keywords[:20],
        "total_keywords":   ats_result.total_keywords,
    }
    _save(subfolder / "ats_score.json", ats_payload)
    log.info("  ATS score: %d%%", ats_result.score)

    # Step 6: Cover letter
    log.info("  Generating cover letter...")
    cover_letter = generate_cover_letter(tailored, job_analysis, jd_text=jd_text)
    _save(subfolder / "cover_letter.json", cover_letter)

    # Step 7: Application email
    log.info("  Generating application email...")
    email = generate_application_email(tailored, job_analysis, jd_text=jd_text)
    _save(subfolder / "email.json", email)

    # Step 8: LinkedIn message
    log.info("  Generating LinkedIn note...")
    linkedin = generate_linkedin_message(tailored, job_analysis, jd_text=jd_text)
    _save(subfolder / "linkedin.json", linkedin)

    # Step 9: Interview prep (Issue 13)
    log.info("  Generating interview prep...")
    interview_prep = generate_interview_prep(tailored, job_analysis)
    _save(subfolder / "interview_prep.json", interview_prep)

    # Step 10: PDF (Issue 6)
    log.info("  Generating PDF...")
    try:
        pdf_bytes = generate_pdf_sync(tailored, template=pdf_template)
        pdf_path  = subfolder / "resume.pdf"
        pdf_path.write_bytes(pdf_bytes)
        log.info("  Saved resume.pdf (%d KB)", len(pdf_bytes) // 1024)
    except Exception as exc:
        log.warning("  Resume PDF failed: %s", exc)

    # Cover letter PDF (Issue 7)
    log.info("  Generating cover letter PDF...")
    try:
        cl_pdf_bytes = generate_cover_letter_pdf(cover_letter, tailored)
        cl_pdf_path  = subfolder / "cover_letter.pdf"
        cl_pdf_path.write_bytes(cl_pdf_bytes)
        log.info("  Saved cover_letter.pdf (%d KB)", len(cl_pdf_bytes) // 1024)
    except Exception as exc:
        log.warning("  Cover letter PDF failed: %s", exc)

    log.info("  Done: %s", subfolder)
    return tailored


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Batch resume generation for all JDs.")
    parser.add_argument(
        "--resume-json",
        default=None,
        help="Path to an existing resume.json to use as input (skips DOCX parsing).",
    )
    parser.add_argument(
        "--resume-docx",
        default=str(REPO_ROOT / "ayush_resume.docx"),
        help="Path to candidate's raw resume DOCX (default: ayush_resume.docx).",
    )
    parser.add_argument(
        "--jd",
        action="append",
        dest="jd_files",
        default=None,
        help="Specific JD file(s) to process. Repeat for multiple. Default: all in /JD/.",
    )
    parser.add_argument(
        "--out",
        default=str(REPO_ROOT / "output"),
        help="Output root directory (default: output/).",
    )
    parser.add_argument(
        "--hide-low-gpa",
        type=float,
        default=None,
        metavar="THRESHOLD",
        help="Suppress GPA below THRESHOLD (normalised to /10). E.g. --hide-low-gpa 7.0",
    )
    parser.add_argument(
        "--template",
        default="modern",
        choices=["modern", "classic", "minimal", "executive", "split"],
        help="PDF resume template (default: modern).",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Load base resume text
    if args.resume_json:
        log.info("Loading base resume from JSON: %s", args.resume_json)
        base_resume_text = Path(args.resume_json).read_text(encoding="utf-8")
    else:
        docx_path = Path(args.resume_docx)
        if not docx_path.exists():
            log.error("Resume DOCX not found: %s", docx_path)
            sys.exit(1)
        log.info("Reading resume from DOCX: %s", docx_path.name)
        base_resume_text = _read_docx_text(docx_path)

    # Collect JD files
    jd_dir = REPO_ROOT / "JD"
    if args.jd_files:
        jd_paths = [Path(f) for f in args.jd_files]
    elif jd_dir.exists():
        jd_paths = sorted(jd_dir.glob("*.docx")) + sorted(jd_dir.glob("*.txt"))
    else:
        log.error("JD directory not found: %s", jd_dir)
        sys.exit(1)

    if not jd_paths:
        log.error("No JD files found.")
        sys.exit(1)

    log.info("Found %d JD file(s) to process.", len(jd_paths))

    # Run pipeline
    results = {}
    for jd_path in jd_paths:
        try:
            process_one(
                jd_path=jd_path,
                base_resume_text=base_resume_text,
                out_dir=out_dir,
                hide_low_gpa=args.hide_low_gpa,
                pdf_template=args.template,
            )
            results[jd_path.stem] = "success"
        except Exception as exc:
            log.error("  FAILED %s: %s", jd_path.stem, exc)
            results[jd_path.stem] = f"FAILED: {exc}"

    # Summary
    print("\n" + "=" * 60)
    print("BATCH COMPLETE")
    print("=" * 60)
    for name, status in results.items():
        icon = "✓" if "success" in status else "✗"
        print(f"  {icon}  {name:<20} {status}")
    print(f"\nOutput: {out_dir}")


if __name__ == "__main__":
    main()
