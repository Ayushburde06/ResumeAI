import pytest
from services.latex_generator import (
    _e,
    _e_url,
    _bold,
    _shorten,
    generate_latex,
)


def test_latex_escaping_special_chars():
    raw_text = "50% increase in revenue & sales #1 for $100k project {test_var}"
    escaped = _e(raw_text)

    assert r"\%" in escaped
    assert r"\&" in escaped
    assert r"\#" in escaped
    assert r"\$" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped
    assert r"\_" in escaped


def test_latex_url_escaping():
    url = "https://example.com/user_profile?query=100%20test"
    escaped = _e_url(url)
    assert r"\%" in escaped
    assert "_" in escaped  # Underscores should NOT be escaped in href URLs


def test_latex_bold_conversion():
    text_with_bold = "Lead developer on **FastAPI Microservice** with 99.9% uptime."
    rendered = _bold(text_with_bold)

    assert r"\textbf{FastAPI Microservice}" in rendered
    assert r"99.9\%" in rendered


def test_shorten_url():
    long_url = "https://www.linkedin.com/in/ayush-burde-super-long-profile-name"
    shortened = _shorten(long_url, maxlen=25)
    assert shortened.startswith("linkedin.com/in/ayush-")
    assert "https://" not in shortened


def test_generate_latex_complete_document():
    resume_payload = {
        "personal_info": {
            "name": "Ayush Burde",
            "email": "ayush@example.com",
            "phone": "+1 555-0199",
            "location": "San Francisco, CA",
            "github": "https://github.com/ayush",
            "linkedin": "https://linkedin.com/in/ayush",
        },
        "summary": "Full Stack Software Engineer with **5+ years** of experience.",
        "experience": [
            {
                "company": "Tech Corp",
                "title": "Senior Engineer",
                "location": "San Francisco, CA",
                "start_date": "Jan 2021",
                "end_date": "Present",
                "bullets": ["Architected RAG system with **98% precision**."],
            }
        ],
        "education": [
            {
                "institution": "University of Technology",
                "degree": "B.S. Computer Science",
                "location": "CA",
                "graduation_year": "2020",
                "gpa": "3.9",
            }
        ],
        "skills": {
            "technical": ["Python", "TypeScript", "FastAPI", "React"],
            "tools": ["Docker", "PostgreSQL", "AWS"],
        },
    }

    latex_doc = generate_latex(resume_payload)

    assert r"\documentclass[letterpaper,11pt]{article}" in latex_doc
    assert r"\textbf{\Huge Ayush Burde}" in latex_doc
    assert r"\section{EXPERIENCE}" in latex_doc
    assert r"\section{EDUCATION}" in latex_doc
    assert r"\section{SKILLS}" in latex_doc
    assert r"\end{document}" in latex_doc
