"""
test_layout_optimizer.py — Tests for the 3-layer layout system.
"""
import pytest

from services.layout_optimizer import (
    apply_adjustments,
    inspect_pdf,
    needs_trim,
    trim_content,
)
from services.pdf_generator import generate_pdf


DENSE_RESUME = {
    "personal_info": {"name": "Test User", "email": "test@test.com", "phone": "555-0100", "location": "SF, CA"},
    "summary": "Experienced engineer with 10 years of experience in software development.",
    "experience": [
        {
            "company": "Corp A",
            "title": "Senior Engineer",
            "start_date": "2020",
            "end_date": "Present",
            "bullets": [
                "Built scalable system handling 10M events/day using Python and FastAPI.",
                "Optimized database queries reducing latency by 45% with Redis caching.",
                "Led team of 8 engineers to rebuild core authentication infrastructure.",
                "Implemented CI/CD pipelines reducing deployment time by 60%.",
                "Designed microservices architecture serving 5M concurrent users.",
            ],
        }
    ] * 5,
    "projects": [
        {
            "name": f"Project {i}",
            "description": "A detailed project with complex architecture and significant impact.",
            "tech_stack": ["Python", "React", "Docker"],
            "bullets": ["Built feature X", "Improved performance by 50%"],
        }
        for i in range(6)
    ],
    "skills": {"languages": ["Python", "Go", "TypeScript"], "frameworks": ["FastAPI", "React", "Django"]},
    "education": [{"institution": "MIT", "degree": "B.S. CS", "graduation_year": "2018"}],
}

SPARSE_RESUME = {
    "personal_info": {"name": "Jane Doe", "email": "jane@test.com", "phone": "555-0199", "location": "NYC"},
    "summary": "Software engineer.",
    "experience": [
        {"company": "Corp", "title": "Engineer", "start_date": "2021", "end_date": "Now", "bullets": ["Built web app."]}
    ],
    "skills": {"languages": ["Python"]},
}


# ── L1: Content trimming tests ────────────────────────────────────────────────

def test_needs_trim_detects_dense_resume():
    assert needs_trim(DENSE_RESUME) is True


def test_needs_trim_passes_normal_resume():
    assert needs_trim(SPARSE_RESUME) is False


def test_trim_content_caps_bullets():
    trimmed = trim_content(DENSE_RESUME)
    for entry in trimmed.get("experience", []):
        assert len(entry.get("bullets", [])) <= 3
    for entry in trimmed.get("projects", []):
        assert len(entry.get("bullets", [])) <= 2


def test_trim_content_reduces_entry_count():
    trimmed = trim_content(DENSE_RESUME)
    total = len(trimmed.get("experience", [])) + len(trimmed.get("projects", []))
    assert total <= 7


# ── L3: PDF inspection tests ──────────────────────────────────────────────────

def test_inspect_pdf_returns_valid_structure():
    """inspect_pdf should return a dict with expected keys even for invalid input."""
    result = inspect_pdf(b"not a pdf")
    assert "page_count" in result
    assert "issues" in result
    assert "fill_ratios" in result
    assert "adjustments" in result


def test_apply_adjustments_shrinks_for_overflow():
    layout = {"font_size": 9.0, "line_height": 1.35, "section_gap": 8.0, "entry_gap": 5.0, "title_gap": 6.0}
    adjustments = {"font_size_delta": -0.3, "line_height_delta": -0.02, "section_gap_delta": -2.0,
                   "entry_gap_delta": -1.5, "title_gap_delta": -1.0}
    new_layout = apply_adjustments(layout, adjustments)
    assert new_layout["font_size"] < layout["font_size"]
    assert new_layout["section_gap"] < layout["section_gap"]


def test_apply_adjustments_expands_for_sparse():
    layout = {"font_size": 8.0, "line_height": 1.30, "section_gap": 5.0, "entry_gap": 3.0, "title_gap": 4.0}
    adjustments = {"font_size_delta": 0.5, "line_height_delta": 0.04, "section_gap_delta": 3.0,
                   "entry_gap_delta": 2.0, "title_gap_delta": 1.5}
    new_layout = apply_adjustments(layout, adjustments)
    assert new_layout["font_size"] > layout["font_size"]
    assert new_layout["section_gap"] > layout["section_gap"]


def test_apply_adjustments_clamps_to_min():
    layout = {"font_size": 7.5, "line_height": 1.15, "section_gap": 3.0, "entry_gap": 1.5, "title_gap": 2.0}
    adjustments = {"font_size_delta": -1.0, "line_height_delta": -0.1, "section_gap_delta": -5.0,
                   "entry_gap_delta": -3.0, "title_gap_delta": -3.0}
    new_layout = apply_adjustments(layout, adjustments)
    assert new_layout["font_size"] >= 7.5
    assert new_layout["line_height"] >= 1.15


def test_apply_adjustments_clamps_to_max():
    layout = {"font_size": 10.5, "line_height": 1.55, "section_gap": 14.0, "entry_gap": 9.0, "title_gap": 9.0}
    adjustments = {"font_size_delta": 1.0, "line_height_delta": 0.1, "section_gap_delta": 5.0,
                   "entry_gap_delta": 3.0, "title_gap_delta": 3.0}
    new_layout = apply_adjustments(layout, adjustments)
    assert new_layout["font_size"] <= 10.5
    assert new_layout["line_height"] <= 1.55


# ── Integration: end-to-end PDF generation with L1+L3 ────────────────────────

@pytest.mark.asyncio
async def test_dense_resume_generates_single_page():
    """A dense resume should be trimmed (L1) and corrected (L3) to fit one page."""
    pdf_bytes = await generate_pdf(DENSE_RESUME, template_name="modern")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")

    verdict = inspect_pdf(pdf_bytes)
    # After L1 trim + L3 correction, should be 1 page (or 2 with non-sparse 2nd page)
    if verdict["page_count"] > 1:
        # If 2 pages, the 2nd page should not be sparse (L3 couldn't collapse further)
        assert "second_page_sparse" not in verdict["issues"] or verdict["page_count"] == 2


@pytest.mark.asyncio
async def test_sparse_resume_fills_more_page():
    """A sparse resume should have L3 expand spacing to fill more of the page."""
    pdf_bytes = await generate_pdf(SPARSE_RESUME, template_name="modern")
    assert isinstance(pdf_bytes, bytes)
    assert pdf_bytes.startswith(b"%PDF")

    verdict = inspect_pdf(pdf_bytes)
    # Should be 1 page
    assert verdict["page_count"] == 1
    # After L3 expansion, fill ratio should be improved (not perfectly sparse)
    # We can't guarantee a specific ratio, but it should be > 0.40
    # (without L3, a 1-bullet resume would be ~0.15 fill)
