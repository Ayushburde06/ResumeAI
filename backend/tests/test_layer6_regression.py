"""
LAYER 6 — REGRESSION LOCK SUITE
Prevent fixed bugs and regressions from returning in future deployments.

Regression Locks:
1. test_null_jd_returns_fallback_not_crash
2. test_zero_match_ats_returns_zero_not_boost
3. test_buzzword_penalty_enforced
4. test_stream_event_sse_contract_compliance
5. test_bridge_map_coverage_and_invariants
"""
import json
import sys
import unittest
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.adaptive_gap import classify_role_domain, adaptive_gap_diff, _BRIDGE_MAP
from services.ats_engine import compute_ats_score
from services.humanization_engine import compute_humanization_score
from services.agent_orchestrator import _make_event


class TestLayer6Regression(unittest.TestCase):

    # ── LOCK 1: NULL / EMPTY JD FALLBACK ──────────────────────────────────────
    def test_null_jd_returns_fallback_not_crash(self):
        for bad_input in ["", "   ", "\n\n"]:
            res = classify_role_domain(bad_input)
            self.assertIsInstance(res, dict)
            self.assertIn("domain", res)
            self.assertIn("explicit_skills", res)
            self.assertEqual(res["explicit_skills"], [], "Empty JD must not hallucinate default skills")

    # ── LOCK 2: HONEST ZERO-MATCH ATS SCORING ─────────────────────────────────
    def test_zero_match_ats_returns_zero_not_boost(self):
        # Empty resume vs real JD
        ats_res = compute_ats_score({}, "Looking for Python, Docker, and Kubernetes.")
        self.assertEqual(ats_res.score, 0, "Zero-keyword match must return 0 ATS score, never an unearned boost")
        self.assertEqual(len(ats_res.matched_keywords), 0)

    # ── LOCK 3: BUZZWORD PENALIZATION INTEGRITY ────────────────────────────────
    def test_buzzword_penalty_enforced(self):
        resume = {
            "summary": "A results-driven, passionate rockstar developer who spearheaded, leveraged, and synergized cutting-edge best-in-class paradigms.",
            "experience": [{"bullets": ["Orchestrated dynamic, revolutionary, game-changing holistic methodologies."]}],
            "projects": []
        }
        res = compute_humanization_score(resume)
        self.assertLess(res.score, 70, f"Buzzword-heavy resume scored {res.score}, expected < 70")
        self.assertGreater(len(res.buzzwords_found), 3)

    # ── LOCK 4: SSE FORMAT CONTRACT ───────────────────────────────────────────
    def test_stream_event_sse_contract_compliance(self):
        event_str = _make_event("jd_analysis", "running", {"detail": "Parsing JD", "domain": "Backend"})
        self.assertTrue(event_str.startswith("data: "))
        self.assertTrue(event_str.endswith("\n\n"))
        
        # Parse payload
        raw_json = event_str[len("data: "):-2]
        payload = json.loads(raw_json)
        self.assertEqual(payload["step"], "jd_analysis")
        self.assertEqual(payload["status"], "running")
        self.assertEqual(payload["domain"], "Backend")

    # ── LOCK 5: BRIDGE MAP INVARIANTS ─────────────────────────────────────────
    def test_bridge_map_coverage_and_invariants(self):
        self.assertIsInstance(_BRIDGE_MAP, dict)
        self.assertGreater(len(_BRIDGE_MAP), 10, "Bridge map must contain core tech domains")
        
        # Verify common adjacent stacks exist
        expected_bridges = ["django", "mysql", "react", "kubernetes", "fastapi"]
        for tech in expected_bridges:
            self.assertTrue(
                tech in _BRIDGE_MAP or any(tech in k for k in _BRIDGE_MAP),
                f"Missing bridge map entry for common tech: {tech}"
            )


if __name__ == "__main__":
    unittest.main(verbosity=2)
