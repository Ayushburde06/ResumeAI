"""Contract tests that keep resume tailoring on the agentic path."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from schemas.profile import GenerateFromProfileRequest


def test_profile_generation_defaults_to_agent_mode():
    request = GenerateFromProfileRequest(job_description="Build backend services with Python and FastAPI.")
    assert request.mode == "agent"


def test_profile_script_mode_is_rejected():
    with pytest.raises(ValidationError):
        GenerateFromProfileRequest(
            job_description="Build backend services with Python and FastAPI.",
            mode="script",
        )


def test_legacy_resume_rewrite_routes_are_not_available():
    source = (Path(__file__).parents[1] / "routers" / "analyze.py").read_text(encoding="utf-8")
    assert "Direct resume analysis is disabled" in source
    assert "@router.post(\"/improve-ats\"" not in source


def test_profile_generation_has_only_streaming_agent_route():
    source = (Path(__file__).parents[1] / "routers" / "profile.py").read_text(encoding="utf-8")
    assert '@router.post("/agent-generate")' in source
    assert '@router.post("/generate")' not in source
