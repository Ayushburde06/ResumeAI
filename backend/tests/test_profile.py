"""Tests for profile service, assembler, and loop engine."""

from schemas.profile import (
    CareerProfileSchema,
    ExperienceSchema,
    PersonalInfoSchema,
    ProjectSchema,
)
from services.loop_engine import run_quality_loop
from services.profile_assembler import (
    profile_to_source_text,
    profile_to_tailored_resume,
    rank_projects,
)
from services.profile_service import profile_is_complete
from services.script_generator import (
    generate_from_profile_script,
    trim_resume_for_one_page,
)


def _sample_profile() -> CareerProfileSchema:
    return CareerProfileSchema(
        personal_info=PersonalInfoSchema(name="Jane Doe", email="jane@example.com"),
        summary="Backend engineer with Python experience.",
        experience=[
            ExperienceSchema(
                title="Software Engineer",
                company="Acme",
                bullets=["Built REST APIs with FastAPI", "Deployed on AWS"],
                tech_stack=["Python", "FastAPI", "AWS"],
            )
        ],
        projects=[
            ProjectSchema(
                name="Task API",
                problem="Needed scalable task management",
                solution="Built FastAPI microservice with PostgreSQL",
                tech_stack=["Python", "FastAPI", "PostgreSQL", "Docker"],
                impact_metrics=["Handled 10k requests/day"],
                bullets=["Designed REST API with FastAPI"],
            )
        ],
        skills={"languages": ["Python"], "frameworks": ["FastAPI"], "databases": ["PostgreSQL"]},
    )


def test_profile_is_complete():
    complete = _sample_profile()
    assert profile_is_complete(complete) is True
    incomplete = CareerProfileSchema(personal_info=PersonalInfoSchema(name="Only Name"))
    assert profile_is_complete(incomplete) is False


def test_profile_to_tailored_resume():
    profile = _sample_profile()
    jd = "Looking for Python FastAPI PostgreSQL Docker backend engineer"
    resume = profile_to_tailored_resume(profile, jd_text=jd)
    assert resume["personal_info"]["name"] == "Jane Doe"
    assert len(resume["experience"]) >= 1
    assert len(resume["projects"]) >= 1
    assert "Python" in resume["skills"]["languages"]


def test_script_generator():
    profile = _sample_profile()
    jd = "Python FastAPI PostgreSQL Docker AWS backend"
    resume = generate_from_profile_script(profile, jd)
    assert resume["personal_info"]["name"] == "Jane Doe"


def test_trim_resume_for_one_page():
    profile = _sample_profile()
    resume = profile_to_tailored_resume(profile)
    resume["experience"] = [
        {"title": f"Role {i}", "company": "Co", "location": "", "start_date": "2020", "end_date": "2021", "bullets": ["a", "b", "c", "d"]}
        for i in range(6)
    ]
    trimmed = trim_resume_for_one_page(resume)
    assert len(trimmed["experience"]) <= 3


def test_profile_to_source_text():
    profile = _sample_profile()
    text = profile_to_source_text(profile)
    assert "Jane Doe" in text or "Task API" in text
    assert "FastAPI" in text


def test_rank_projects_by_jd():
    profile = _sample_profile()
    profile.projects.append(ProjectSchema(name="Mobile App", problem="iOS app", tech_stack=["Swift"]))
    ranked = rank_projects(profile.projects, "Python FastAPI PostgreSQL backend")
    assert ranked[0].name == "Task API"


def test_loop_engine_runs_without_error():
    profile = _sample_profile()
    draft = generate_from_profile_script(profile, "Python FastAPI PostgreSQL Docker")
    source = profile_to_source_text(profile)
    result = run_quality_loop(
        draft=draft,
        jd_text="Python FastAPI PostgreSQL Docker backend engineer REST API",
        source_text=source,
        job_analysis={"job_title": "Backend Engineer", "required_skills": ["Python", "FastAPI"]},
        max_iterations=2,
        improve_fn=None,
    )
    assert result.resume is not None
    assert result.iterations >= 1
    assert isinstance(result.ats_score, int)
