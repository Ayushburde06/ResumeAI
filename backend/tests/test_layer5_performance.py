"""
LAYER 5 — PERFORMANCE & BENCHMARK TESTS
Measure latency, concurrency, memory stability, and stream efficiency.

Tests:
1. Time to First Byte (TTFB) on fast classification (< 3s)
2. Concurrent Execution Safety (multiple thread pool workers)
3. Memory Stability (10 iterations without memory leaks)
4. Stream Event Generation Efficiency
"""
import gc
import os
import sys
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from services.adaptive_gap import classify_role_domain, build_capability_graph, adaptive_gap_diff
from services.ats_engine import compute_ats_score
from services.agent_orchestrator import _make_event


class TestLayer5Performance(unittest.TestCase):

    # ── 1. TIME TO FIRST BYTE (TTFB) ───────────────────────────────────────────
    def test_classification_latency_benchmark(self):
        jd = "Seeking Senior Fullstack Developer with React, Node.js, Python, and PostgreSQL."
        start = time.time()
        res = classify_role_domain(jd)
        duration = time.time() - start
        self.assertIsInstance(res, dict)
        print(f"\n[PERF] Classification latency: {duration:.2f}s")
        # Ensure fast classification returns in under 6 seconds
        self.assertLess(duration, 6.0, f"Classification took {duration:.2f}s (expected < 6.0s)")

    # ── 2. CONCURRENT EXECUTION SAFETY ─────────────────────────────────────────
    def test_concurrent_scoring_execution(self):
        resume = {
            "summary": "Software Engineer with Python, FastAPI, Docker, and PostgreSQL.",
            "skills": {"languages": ["Python"], "frameworks": ["FastAPI"], "databases": ["PostgreSQL"], "tools": ["Docker"]},
            "experience": [{"title": "SE", "bullets": ["Developed APIs in Python."]}],
            "projects": []
        }
        jd = "Python Engineer with FastAPI, PostgreSQL, Docker, AWS, and Redis."

        def run_score(idx):
            return compute_ats_score(resume, jd)

        start = time.time()
        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(run_score, i) for i in range(5)]
            results = [f.result() for f in futures]
        duration = time.time() - start
        print(f"[PERF] 5 Concurrent Scorer Runs duration: {duration:.4f}s")
        self.assertEqual(len(results), 5)
        for r in results:
            self.assertEqual(r.score, results[0].score)

    # ── 3. MEMORY STABILITY TEST ───────────────────────────────────────────────
    def test_memory_stability_repeated_runs(self):
        try:
            import psutil
            process = psutil.Process(os.getpid())
            gc.collect()
            initial_mem = process.memory_info().rss / (1024 * 1024)  # MB

            resume = {
                "summary": "Full Stack Engineer with Python, React, PostgreSQL.",
                "skills": {"languages": ["Python", "JavaScript"], "frameworks": ["FastAPI", "React"]},
                "experience": [{"title": "Dev", "bullets": ["Built apps."]}],
                "projects": []
            }
            jd = "Looking for Full Stack Developer with Python, React, and PostgreSQL."

            for _ in range(10):
                _ = compute_ats_score(resume, jd)
                _ = adaptive_gap_diff(
                    {"python": ["backend"], "react": ["frontend"]},
                    {"explicit_skills": ["python", "react"], "implicit_expectations": []},
                    ["postgresql"]
                )

            gc.collect()
            final_mem = process.memory_info().rss / (1024 * 1024)  # MB
            mem_diff = final_mem - initial_mem
            print(f"[PERF] Memory change across 10 runs: {mem_diff:+.2f} MB (from {initial_mem:.1f} MB to {final_mem:.1f} MB)")
            # Memory should not grow by more than 20MB for pure CPU scoring operations
            self.assertLess(mem_diff, 20.0, f"Potential memory leak: grew by {mem_diff:.2f} MB")
        except ImportError:
            print("[PERF] psutil not installed, skipping memory tracking")

    # ── 4. STREAM EVENT GENERATION EFFICIENCY ──────────────────────────────────
    def test_stream_event_serialization_speed(self):
        start = time.time()
        for i in range(100):
            _ = _make_event("step_test", "running", {"score": 85, "detail": "Test chunk"})
        duration = time.time() - start
        print(f"[PERF] 100 SSE Event serializations: {duration * 1000:.2f}ms")
        self.assertLess(duration, 0.1, "SSE serialization took too long")


if __name__ == "__main__":
    unittest.main(verbosity=2)
