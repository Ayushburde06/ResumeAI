"""
test_pdf_generator.py — Unit tests for PDF generation service and single-page typography scaling.
"""

import pytest
from services.layout_engine import (
    choose_typography as _choose_typography,
)
from services.layout_engine import (
    count_resume_words as _count_resume_words,
)
from services.pdf_generator import (
    VALID_TEMPLATES,
    BrowserManager,
    _adaptive_layout,
    generate_pdf,
)

SAMPLE_RESUME = {
    "personal_info": {
        "name": "Ayush Burde",
        "email": "ayush@example.com",
        "phone": "+1 555-0199",
        "linkedin": "linkedin.com/in/ayush",
        "github": "github.com/ayush",
        "location": "San Francisco, CA",
    },
    "summary": "Experienced Full-Stack Software Engineer specializing in high-throughput cloud architectures, web applications, and artificial intelligence integration.",
    "experience": [
        {
            "company": "Tech Corp",
            "title": "Senior Software Engineer",
            "location": "San Francisco, CA",
            "start_date": "2022",
            "end_date": "Present",
            "bullets": [
                "Architected distributed microservices backend handling 10M+ daily events using Python and FastAPI.",
                "Optimized database performance by implementing Redis cache layer, reducing query latency by 45%.",
                "Led cross-functional team of 6 engineers in rebuilding the core authentication infrastructure.",
            ],
        },
        {
            "company": "Data Solutions",
            "title": "Software Engineer",
            "location": "Seattle, WA",
            "start_date": "2020",
            "end_date": "2022",
            "bullets": [
                "Built interactive analytics dashboards with Next.js and React serving 50k active monthly users.",
                "Automated CI/CD deployment pipelines on AWS ECS, reducing deployment cycle times by 60%.",
            ],
        },
    ],
    "projects": [
        {
            "name": "Resume AI Platform",
            "tech_stack": ["Python", "FastAPI", "React", "Docker"],
            "description": "AI-powered resume optimization platform delivering ATS scoring and tailored pdf generation.",
            "link": "github.com/ayush/resume-ai",
        },
    ],
    "skills": {
        "languages": ["Python", "TypeScript", "SQL", "Go"],
        "frameworks": ["FastAPI", "React", "Next.js", "Django"],
        "databases": ["PostgreSQL", "Redis", "MongoDB"],
        "tools": ["Docker", "Kubernetes", "AWS", "Git"],
        "concepts": ["Microservices", "REST APIs", "CI/CD", "Distributed Systems"],
    },
    "education": [
        {
            "institution": "University of Technology",
            "degree": "B.S. Computer Science",
            "graduation_year": "2020",
            "location": "Seattle, WA",
            "gpa": "3.9",
        }
    ],
    "certifications": [
        {"name": "AWS Certified Solutions Architect", "issuer": "Amazon Web Services", "year": "2021"}
    ],
}


def test_count_resume_words_counts_all_visible_text():
    words = _count_resume_words(SAMPLE_RESUME)
    assert words > 150
    assert words < 500


def test_choose_typography_scales_down_for_dense_content():
    sparse_spec = _choose_typography(100)
    medium_spec = _choose_typography(300)
    dense_spec = _choose_typography(800)

    assert sparse_spec["font_size"] > medium_spec["font_size"]
    assert medium_spec["font_size"] > dense_spec["font_size"]
    assert sparse_spec["body_padding"] >= dense_spec["body_padding"]
    assert dense_spec["font_size"] <= 7.5


def test_adaptive_layout_scales_smoothly_for_resume_density():
    short_resume = {"summary": "A concise summary."}
    medium_resume = SAMPLE_RESUME
    long_resume = {
        "summary": " ".join(["Experienced engineer"] * 80),
        "experience": [
            {
                "company": "Example",
                "title": "Engineer",
                "bullets": ["Delivered measurable improvements across a complex production system."] * 30,
            }
        ],
        "projects": [{"name": "Project", "description": "A detailed project description."} for _ in range(5)],
        "skills": {"languages": ["Python", "SQL", "Go", "TypeScript"]},
    }

    short_layout = _adaptive_layout(short_resume)
    medium_layout = _adaptive_layout(medium_resume)
    long_layout = _adaptive_layout(long_resume)

    assert short_layout["font_size"] > medium_layout["font_size"] > long_layout["font_size"]
    assert short_layout["section_gap"] > medium_layout["section_gap"] > long_layout["section_gap"]
    assert long_layout["font_size"] >= 7.75
    assert long_layout["line_height"] >= 1.20

@pytest.mark.asyncio
@pytest.mark.parametrize("template_name", list(VALID_TEMPLATES))
async def test_generate_pdf_produces_valid_pdf_bytes(template_name):
    try:
        pdf_bytes = await generate_pdf(SAMPLE_RESUME, template_name=template_name)
        assert isinstance(pdf_bytes, bytes)
        assert pdf_bytes.startswith(b"%PDF")
    finally:
        await BrowserManager.close_all()


@pytest.mark.asyncio
async def test_pdf_page_count_single_page_guarantee():
    try:
        import pypdf
        reader_cls = pypdf.PdfReader
    except ImportError:
        try:
            import PyPDF2
            reader_cls = PyPDF2.PdfReader
        except ImportError:
            pytest.skip("Neither pypdf nor PyPDF2 installed for page count inspection")

    import io
    try:
        for template_name in VALID_TEMPLATES:
            pdf_bytes = await generate_pdf(SAMPLE_RESUME, template_name=template_name)
            reader = reader_cls(io.BytesIO(pdf_bytes))
            assert len(reader.pages) == 1, f"Template '{template_name}' generated {len(reader.pages)} pages, expected 1"
    finally:
        await BrowserManager.close_all()
