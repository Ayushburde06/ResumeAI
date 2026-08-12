import pytest
from services.adaptive_gap import (
    adaptive_gap_diff
)

def test_adaptive_gap_diff_direct_match():
    # If the missing keyword is exactly in the capability graph, it should not be in critical
    capability_graph = {
        "python": {"type": "language", "context": ["backend"]},
        "react": {"type": "framework", "context": ["frontend"]}
    }
    domain_profile = {
        "domain": "Fullstack Engineer",
        "seniority": "mid",
        "role_type": "fullstack",
        "industry": "tech",
        "explicit_skills": ["python", "react"],
        "implicit_expectations": [],
        "nice_to_haves": [],
        "red_flags_if_missing": []
    }
    missing_keywords = ["python"] # Should technically be caught by initial ATS, but let's test safety
    
    report = adaptive_gap_diff(capability_graph, domain_profile, missing_keywords)
    
    # Python is already in capabilities, shouldn't be a critical gap or true unknown
    assert "python" not in report["critical"]
    assert "python" not in report["true_unknowns"]

def test_adaptive_gap_diff_bridged_skill():
    # Test bridging: if "aws" is missing but "gcp" is in capabilities
    capability_graph = {
        "gcp": {"type": "cloud", "context": ["deployed apps"]},
    }
    domain_profile = {
        "domain": "Cloud Engineer",
        "seniority": "mid",
        "role_type": "backend",
        "industry": "tech",
        "explicit_skills": ["aws"],
        "implicit_expectations": [],
        "nice_to_haves": [],
        "red_flags_if_missing": []
    }
    missing_keywords = ["aws"]
    
    report = adaptive_gap_diff(capability_graph, domain_profile, missing_keywords)
    
    assert len(report["bridgeable"]) == 1
    assert report["bridgeable"][0]["jd_needs"] == "aws"
    assert "gcp" in report["bridgeable"][0]["candidate_has"]
    assert "aws" not in report["true_unknowns"]

def test_adaptive_gap_diff_true_unknown():
    # Test when a skill is missing and cannot be bridged
    capability_graph = {
        "html": {"type": "language", "context": ["frontend"]},
    }
    domain_profile = {
        "domain": "Data Scientist",
        "seniority": "mid",
        "role_type": "data",
        "industry": "tech",
        "explicit_skills": ["pytorch"],
        "implicit_expectations": [],
        "nice_to_haves": [],
        "red_flags_if_missing": ["pytorch"]
    }
    missing_keywords = ["pytorch"]
    
    report = adaptive_gap_diff(capability_graph, domain_profile, missing_keywords)
    
    assert "pytorch" not in report["true_unknowns"]
    assert "pytorch" in report["critical"]
    assert "pytorch" not in report["bridgeable"]

def test_adaptive_gap_diff_implicit_expectations():
    # Test that implicit expectations not in capabilities are caught
    capability_graph = {
        "python": {"type": "language", "context": ["backend"]},
    }
    domain_profile = {
        "domain": "Backend Engineer",
        "seniority": "senior",
        "role_type": "backend",
        "industry": "tech",
        "explicit_skills": ["python"],
        "implicit_expectations": ["system design", "ci/cd"],
        "nice_to_haves": [],
        "red_flags_if_missing": []
    }
    missing_keywords = [] # ATS caught everything explicit
    
    report = adaptive_gap_diff(capability_graph, domain_profile, missing_keywords)
    
    assert "system design" in report["implicit"]
    assert "ci/cd" in report["implicit"]
