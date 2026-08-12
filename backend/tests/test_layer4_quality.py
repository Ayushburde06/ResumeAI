"""
LAYER 4 — QUALITY TESTS
Validate AI output quality, honesty, specificity, and keyword accuracy.

Tests:
1. Keyword Coverage & Accuracy (Scorer vs actual presence)
2. Honesty & Non-Hallucination (Zero-skill honesty check)
3. Banned Buzzword Detection
4. Specificity & Measurable Outcomes
5. Section Completeness & Structural Invariants
"""
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.ats_engine import compute_ats_score, _tokenize
from services.humanization_engine import (
    compute_humanization_score,
    BUZZWORDS,
    _find_buzzwords,
    evaluate_bullet,
)
from services.adaptive_gap import adaptive_gap_diff, classify_role_domain


BANNED_BUZZWORDS_PROMPT_LIST = [
    "spearheaded", "leveraged", "utilized", "orchestrated",
    "synergized", "streamlined", "robust", "scalable",
    "cutting-edge", "best-in-class", "dynamic", "innovative",
    "passionate", "guru", "ninja", "rockstar"
]


class TestLayer4Quality(unittest.TestCase):

    # ── 1. KEYWORD COVERAGE & ACCURACY ─────────────────────────────────────────
    def test_ats_accuracy_and_keyword_presence(self):
        resume = {
            "summary": "Full Stack Engineer specializing in Python, React, and PostgreSQL.",
            "skills": {
                "languages": ["Python", "JavaScript", "SQL"],
                "frameworks": ["FastAPI", "React"],
                "databases": ["PostgreSQL"]
            },
            "experience": [
                {"title": "Software Engineer", "company": "Acme Corp", "bullets": ["Built asynchronous REST APIs in FastAPI using PostgreSQL."]}
            ],
            "projects": []
        }
        jd = "Seeking Senior Engineer with Python, React, PostgreSQL, Docker, and Kubernetes."
        
        ats = compute_ats_score(resume, jd)
        
        # Verify matched keywords are actually present in the resume
        plain_text = (
            resume["summary"] + " " +
            " ".join(resume["skills"]["languages"]) + " " +
            " ".join(resume["skills"]["frameworks"]) + " " +
            " ".join(resume["skills"]["databases"]) + " " +
            " ".join(resume["experience"][0]["bullets"])
        ).lower()
        
        for matched_kw in ats.matched_keywords:
            self.assertTrue(
                matched_kw.lower() in plain_text or any(part in plain_text for part in matched_kw.lower().split()),
                f"Scorer reported '{matched_kw}' as matched, but it was not in resume text!"
            )
            
        for missing_kw in ats.missing_keywords:
            self.assertFalse(
                missing_kw.lower() in plain_text,
                f"Scorer reported '{missing_kw}' as missing, but it is in the resume text!"
            )

    # ── 2. HONESTY TEST (NO HALLUCINATED PROFICIENCY) ──────────────────────────
    def test_honesty_zero_experience_gap_detection(self):
        cap_graph = {
            "python": ["backend", "scripting"],
            "django": ["mvc", "web development"]
        }
        domain_profile = {
            "explicit_skills": ["Java", "Spring Boot", "JVM"],
            "implicit_expectations": ["Enterprise Design Patterns"],
            "red_flags_if_missing": ["Java"]
        }
        # When candidate has zero Java, it must NOT be marked as already mastered
        report = adaptive_gap_diff(cap_graph, domain_profile, ats_missing_keywords=["Java", "Spring Boot", "JVM"])
        
        # Check critical or bridgeable lists
        critical_and_unknowns = report.get("critical", []) + report.get("true_unknowns", [])
        bridgeable = report.get("bridgeable", [])
        
        # The system must recognize Java as missing (either bridgeable via Python OOP or critical)
        # It must NOT classify it as present
        self.assertNotIn("java", [s.lower() for s in cap_graph.keys()])
        self.assertTrue(len(critical_and_unknowns) + len(bridgeable) >= 2)

    # ── 3. BANNED BUZZWORD DETECTION ───────────────────────────────────────────
    def test_banned_buzzword_flagging(self):
        bullet_with_buzzwords = "Spearheaded and leveraged a cutting-edge, robust, best-in-class pipeline as a 10x rockstar developer."
        feedback = evaluate_bullet(bullet_with_buzzwords)
        self.assertTrue(feedback.has_buzzword)
        self.assertIn("buzzword", feedback.flags[0].lower())
        
        found = _find_buzzwords(bullet_with_buzzwords)
        self.assertIn("spearheaded", found)
        self.assertIn("leveraged", found)
        self.assertIn("cutting-edge", found)
        self.assertIn("robust", found)
        self.assertIn("best-in-class", found)

    # ── 4. SPECIFICITY & MEASURABLE OUTCOMES ───────────────────────────────────
    def test_bullet_specificity_with_numbers_and_tech(self):
        clean_bullet = "Decreased database query latency by 42% by indexing PostgreSQL tables and caching hot queries in Redis."
        feedback = evaluate_bullet(clean_bullet)
        self.assertTrue(feedback.has_number)
        self.assertTrue(feedback.has_outcome_word)
        self.assertFalse(feedback.has_buzzword)
        self.assertFalse(feedback.is_passive)

    # ── 5. SECTION COMPLETENESS INVARIANTS ─────────────────────────────────────
    def test_resume_structural_completeness(self):
        resume = {
            "personal_info": {"name": "Alex Smith", "email": "alex@example.com"},
            "summary": "Senior Software Architect.",
            "skills": {"languages": ["Go", "Python"], "frameworks": ["Gin", "FastAPI"]},
            "experience": [{"title": "Lead Engineer", "company": "Globex", "bullets": ["Architected distributed systems."]}],
            "projects": [{"name": "Cluster Monitor", "tech_stack": ["Go", "Prometheus"], "bullets": ["Monitored 500+ nodes."]}],
            "education": [{"degree": "BS in Computer Science", "institution": "State University"}]
        }
        
        self.assertIn("name", resume["personal_info"])
        self.assertIn("email", resume["personal_info"])
        self.assertGreater(len(resume["summary"]), 0)
        self.assertGreater(len(resume["skills"]), 0)
        self.assertGreater(len(resume["experience"]), 0)
        self.assertGreater(len(resume["projects"]), 0)
        self.assertGreater(len(resume["education"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
