"""
LAYER 1 — UNIT TESTS
Isolate each component and test happy paths, null/empty inputs, boundary conditions.
"""
import sys
import unittest
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.adaptive_gap import (
    classify_role_domain,
    build_capability_graph,
    adaptive_gap_diff,
    _normalise,
    _is_bridgeable,
)
from services.ats_engine import compute_ats_score, _extract_jd_keywords
from services.humanization_engine import compute_humanization_score, _find_buzzwords
from services.agent_orchestrator import _classify_missing_keywords, _keyword_placement_hint


class TestLayer1Unit(unittest.TestCase):
    
    # ── 1. JD CLASSIFIER ───────────────────────────────────────────────────────
    def test_jd_classifier_happy_path(self):
        jd = "Looking for Senior Backend Engineer with Python, FastAPI, PostgreSQL, AWS, and Distributed Systems experience."
        res = classify_role_domain(jd)
        self.assertIsInstance(res, dict)
        self.assertIn("domain", res)
        self.assertIn("seniority", res)
        self.assertIn("role_type", res)
        self.assertIn("industry", res)
        self.assertIn("explicit_skills", res)
        self.assertIn("implicit_expectations", res)
        self.assertIn("nice_to_haves", res)
        self.assertIn("red_flags_if_missing", res)
        self.assertIsInstance(res["explicit_skills"], list)

    def test_jd_classifier_empty_input(self):
        res = classify_role_domain("")
        self.assertIsInstance(res, dict)
        self.assertIn("domain", res)
        self.assertIn("explicit_skills", res)
        self.assertEqual(res["explicit_skills"], [])

    def test_jd_classifier_non_english(self):
        jd = "Recherche d'un ingénieur logiciel senior avec expertise en Python et Django."
        res = classify_role_domain(jd)
        self.assertIsInstance(res, dict)
        self.assertIn("domain", res)

    def test_jd_classifier_no_keywords(self):
        jd = "We are a happy company looking for great people to join our culture and thrive together."
        res = classify_role_domain(jd)
        self.assertIsInstance(res, dict)
        self.assertIn("domain", res)

    # ── 2. CAPABILITY GRAPH BUILDER ───────────────────────────────────────────
    def test_capability_graph_happy_path(self):
        resume = {
            "skills": {
                "languages": ["Python", "JavaScript", "SQL"],
                "frameworks": ["FastAPI", "React"],
                "tools": ["Docker", "Git"]
            },
            "experience": [
                {"title": "Backend Engineer", "company": "Tech Corp", "tech_stack": ["Python", "FastAPI", "PostgreSQL"], "bullets": ["Built high throughput REST APIs."]}
            ],
            "projects": [
                {"name": "SaaS Platform", "tech_stack": ["Docker", "React"], "bullets": ["Containerized deployment."]}
            ]
        }
        graph = build_capability_graph(resume)
        self.assertIsInstance(graph, dict)
        for skill, caps in graph.items():
            self.assertIsInstance(skill, str)
            self.assertIsInstance(caps, list)

    def test_capability_graph_empty_resume(self):
        graph = build_capability_graph({})
        self.assertIsInstance(graph, dict)

    def test_capability_graph_no_skills_section(self):
        resume = {
            "skills": {},
            "experience": [
                {"title": "Developer", "bullets": ["Engineered distributed pipelines in Python and Apache Spark."]}
            ]
        }
        graph = build_capability_graph(resume)
        self.assertIsInstance(graph, dict)

    def test_capability_graph_one_line_resume(self):
        resume = {"summary": "Junior programmer."}
        graph = build_capability_graph(resume)
        self.assertIsInstance(graph, dict)

    # ── 3. GAP DETECTION (ADAPTIVE GAP DIFF) ───────────────────────────────────
    def test_gap_detection_perfect_match(self):
        cap_graph = {
            "python": ["backend", "rest api", "scripting"],
            "fastapi": ["async", "microservices"],
            "postgresql": ["sql", "database design"]
        }
        domain_profile = {
            "explicit_skills": ["python", "fastapi", "postgresql"],
            "implicit_expectations": ["rest api"],
            "red_flags_if_missing": []
        }
        report = adaptive_gap_diff(cap_graph, domain_profile, ats_missing_keywords=[])
        self.assertIsInstance(report, dict)
        self.assertIn("critical", report)
        self.assertIn("bridgeable", report)
        self.assertEqual(len(report["critical"]), 0, "Perfect match should have 0 critical gaps")

    def test_gap_detection_zero_match(self):
        cap_graph = {
            "photoshop": ["graphic design", "photo editing"],
            "figma": ["ui ux", "wireframing"]
        }
        domain_profile = {
            "explicit_skills": ["Kubernetes", "Golang", "C++", "Terraform"],
            "implicit_expectations": ["Linux kernel"],
            "red_flags_if_missing": ["Golang"]
        }
        report = adaptive_gap_diff(cap_graph, domain_profile, ats_missing_keywords=["Kubernetes", "Golang", "C++", "Terraform"])
        self.assertGreater(len(report["critical"]) + len(report["true_unknowns"]), 0)
        self.assertIsInstance(report["bridgeable"], list)

    def test_gap_detection_bridgeable_match(self):
        cap_graph = {
            "postgresql": ["relational database", "sql", "acid", "query optimization"],
            "fastapi": ["python", "rest api design", "backend"]
        }
        domain_profile = {
            "explicit_skills": ["MySQL", "Django"],
            "implicit_expectations": ["REST API"],
            "red_flags_if_missing": []
        }
        report = adaptive_gap_diff(cap_graph, domain_profile, ats_missing_keywords=["MySQL", "Django"])
        self.assertIsInstance(report, dict)
        self.assertIn("bridgeable", report)
        self.assertGreater(len(report["bridgeable"]), 0)
        # Check bridge framing content
        self.assertTrue(any("postgresql" in b["bridge_framing"].lower() for b in report["bridgeable"]))

    # ── 4. BLUEPRINT / KEYWORD CLASSIFICATION ──────────────────────────────────
    def test_keyword_classification(self):
        missing = ["python", "docker", "agile", "leadership", "react", "communication"]
        classified = _classify_missing_keywords(missing)
        self.assertIn("skills", classified)
        self.assertIn("experience", classified)
        self.assertIn("summary", classified)
        self.assertIn("python", classified["skills"])
        self.assertIn("docker", classified["skills"])

    def test_keyword_placement_hint_empty(self):
        hint = _keyword_placement_hint({"skills": [], "experience": [], "summary": []})
        self.assertIsInstance(hint, str)
        self.assertIn("KEYWORD PLACEMENT GUIDANCE", hint)

    # ── 5. ATS SCORER ──────────────────────────────────────────────────────────
    def test_ats_scorer_happy_path(self):
        resume = {
            "personal_info": {"name": "Test User"},
            "summary": "Experienced Python Backend Engineer with FastAPI and PostgreSQL.",
            "skills": {"languages": ["Python", "SQL"], "frameworks": ["FastAPI"], "databases": ["PostgreSQL"]},
            "experience": [{"title": "Software Engineer", "company": "ABC", "bullets": ["Built Python REST services using FastAPI."]}],
            "education": [],
            "projects": []
        }
        jd_text = "Looking for a Python Backend Engineer proficient in FastAPI, SQL, PostgreSQL, and Docker."
        res = compute_ats_score(resume, jd_text)
        self.assertIn("score", res._fields)
        self.assertIn("matched_keywords", res._fields)
        self.assertIn("missing_keywords", res._fields)
        self.assertGreater(res.score, 0)
        self.assertIn("python", [k.lower() for k in res.matched_keywords])

    def test_ats_scorer_empty_resume(self):
        res = compute_ats_score({}, "Python Engineer with Django and AWS.")
        self.assertEqual(res.score, 0)
        self.assertEqual(len(res.matched_keywords), 0)

    def test_ats_scorer_no_jd_keywords(self):
        resume = {
            "summary": "Full stack developer.",
            "skills": {"languages": ["Python"]}
        }
        res = compute_ats_score(resume, "")
        self.assertEqual(res.total_keywords, 0)
        self.assertEqual(res.score, 0)

    # ── 6. HUMANIZATION ENGINE ─────────────────────────────────────────────────
    def test_humanization_score_clean_resume(self):
        resume = {
            "summary": "Built backend systems for payment processing handling 10k requests/sec.",
            "experience": [{"bullets": ["Engineered asynchronous data pipelines in Python decreasing latency by 25%."]}],
            "projects": []
        }
        res = compute_humanization_score(resume)
        self.assertIsInstance(res.score, int)
        self.assertGreaterEqual(res.score, 70)

    def test_humanization_score_buzzwordy_resume(self):
        resume = {
            "summary": "A passionate, cutting-edge rockstar guru who spearheaded, synergized, and leveraged best-in-class solutions.",
            "experience": [{"bullets": ["Orchestrated innovative paradigms seamlessly to revolutionize holistic frameworks."]}],
            "projects": []
        }
        res = compute_humanization_score(resume)
        buzzwords = _find_buzzwords(resume["summary"])
        self.assertLess(res.score, 70, "Buzzword-heavy resume should score lower on humanization")
        self.assertGreater(len(buzzwords), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
