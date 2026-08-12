"""
LAYER 2 — INTEGRATION TESTS
Test handoffs between all pipeline modules and full API contracts.
"""
import json
import sys
import unittest
from pathlib import Path
from fastapi.testclient import TestClient

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from main import app
from routers.auth import require_user
from models.user import User
from services.adaptive_gap import (
    classify_role_domain,
    build_capability_graph,
    adaptive_gap_diff,
)
from services.ats_engine import compute_ats_score
from services.agent_orchestrator import _classify_missing_keywords, _keyword_placement_hint
from services.composite_score import compute_composite_score


# Mock test user for authenticated endpoints
def mock_require_user():
    return User(id=1, email="test@resumeai.test", name="Test QA Engineer")


class TestLayer2Integration(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)
        # Setup dependency override for auth testing
        app.dependency_overrides[require_user] = mock_require_user

    @classmethod
    def tearDownClass(cls):
        app.dependency_overrides.clear()

    # ── 1. HANDOFF: CLASSIFIER -> CAPABILITY GRAPH -> GAP DETECTION ───────────
    def test_handoff_classifier_to_gap_diff(self):
        sample_jd = """
        Senior Backend Engineer
        Requirements:
        - 4+ years of Python and FastAPI
        - Experience with PostgreSQL and Redis
        - Docker and Kubernetes in production
        - Nice to have: AWS Lambda
        """
        sample_resume = {
            "personal_info": {"name": "Candidate A", "email": "a@example.com"},
            "summary": "Backend developer with Python and PostgreSQL experience.",
            "skills": {
                "languages": ["Python", "SQL"],
                "frameworks": ["FastAPI"],
                "databases": ["PostgreSQL"]
            },
            "experience": [
                {"title": "Software Engineer", "company": "Co", "tech_stack": ["Python", "FastAPI", "PostgreSQL"], "bullets": ["Designed REST APIs."]}
            ],
            "projects": []
        }

        # Step 1: Classifier
        domain_profile = classify_role_domain(sample_jd)
        self.assertIn("explicit_skills", domain_profile)
        self.assertIn("implicit_expectations", domain_profile)

        # Step 2: Capability Graph
        cap_graph = build_capability_graph(sample_resume)
        self.assertIsInstance(cap_graph, dict)

        # Step 3: Baseline ATS Scan
        ats_res = compute_ats_score(sample_resume, sample_jd)
        self.assertIsInstance(ats_res.missing_keywords, list)

        # Step 4: Adaptive Gap Diff
        gap_report = adaptive_gap_diff(cap_graph, domain_profile, ats_res.missing_keywords)
        self.assertIn("critical", gap_report)
        self.assertIn("bridgeable", gap_report)
        self.assertIn("implicit", gap_report)

        # Step 5: Keyword Classification & Placement Hint
        classified = _classify_missing_keywords(ats_res.missing_keywords)
        hint = _keyword_placement_hint(classified, adaptive_report=gap_report)
        self.assertIsInstance(hint, str)
        self.assertIn("KEYWORD PLACEMENT GUIDANCE", hint)

    # ── 2. ATS SCORER DETERMINISM ──────────────────────────────────────────────
    def test_ats_scorer_is_deterministic(self):
        resume = {
            "summary": "Experienced Python Backend Engineer with FastAPI, PostgreSQL and Docker.",
            "skills": {"languages": ["Python"], "frameworks": ["FastAPI"], "databases": ["PostgreSQL"], "tools": ["Docker"]},
            "experience": [{"title": "Software Engineer", "bullets": ["Built Python microservices with FastAPI and Docker."]}],
            "projects": []
        }
        jd = "Seeking Python Engineer with FastAPI, PostgreSQL, Docker, AWS, and Kubernetes."
        
        score1 = compute_ats_score(resume, jd)
        score2 = compute_ats_score(resume, jd)
        score3 = compute_ats_score(resume, jd)
        
        self.assertEqual(score1.score, score2.score)
        self.assertEqual(score2.score, score3.score)
        self.assertEqual(score1.matched_keywords, score2.matched_keywords)
        self.assertEqual(score1.missing_keywords, score2.missing_keywords)

    # ── 3. COMPOSITE SCORE INTEGRATION ─────────────────────────────────────────
    def test_composite_score_computation(self):
        ats_score = 90
        quality_mock = {
            "hr_readability_score": 90,
            "hm_confidence_score": 90,
            "human_writing_score": 90,
            "evidence_credibility_score": 90
        }
        comp = compute_composite_score(ats_score, quality_mock)
        self.assertIsInstance(comp, float)
        self.assertAlmostEqual(comp, 0.90, places=2)

    # ── 4. API CONTRACT: GET /api/models ───────────────────────────────────────
    def test_api_models_endpoint(self):
        resp = self.client.get("/api/models")
        self.assertEqual(resp.status_code, 200)
        models = resp.json()
        self.assertIsInstance(models, list)
        self.assertGreater(len(models), 0)
        for m in models:
            self.assertIn("id", m)
            self.assertIn("display_name", m)
            self.assertIn("is_default", m)

    # ── 5. API CONTRACT: INVALID REQUEST HANDLING ──────────────────────────────
    def test_api_invalid_resume_upload(self):
        # Empty POST to agent-analyze should return 422 Unprocessable Entity (missing file & jd)
        resp = self.client.post("/api/agent-analyze")
        self.assertEqual(resp.status_code, 422)

    # ── 6. DIRECT /analyze ENDPOINT DISABLED (CONTRACT CHECK) ──────────────────
    def test_direct_analyze_endpoint_disabled(self):
        resp = self.client.post(
            "/api/analyze",
            files={"resume_file": ("resume.txt", b"Test resume content", "text/plain")},
            data={"job_description": "Test JD"}
        )
        # Should inform that direct endpoint is disabled with 410 Gone in favor of agent-analyze
        self.assertEqual(resp.status_code, 410)
        self.assertIn("Use the agentic /agent-analyze endpoint", resp.json()["detail"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
