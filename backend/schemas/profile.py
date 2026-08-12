"""Pydantic schemas for user career profile."""
from typing import Literal

from pydantic import BaseModel, Field


class PersonalInfoSchema(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    linkedin: str = ""
    github: str = ""
    website: str = ""
    headline: str = ""


class ExperienceSchema(BaseModel):
    id: str = ""
    title: str = ""
    company: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    bullets: list[str] = Field(default_factory=list)
    tech_stack: list[str] = Field(default_factory=list)


class ProjectSchema(BaseModel):
    id: str = ""
    name: str = ""
    role: str = ""
    start_date: str = ""
    end_date: str = ""
    problem: str = ""
    solution: str = ""
    architecture: str = ""
    tech_stack: list[str] = Field(default_factory=list)
    impact_metrics: list[str] = Field(default_factory=list)
    challenges: str = ""
    team_size: str = ""
    link: str = ""
    live_link: str = ""
    bullets: list[str] = Field(default_factory=list)


class EducationSchema(BaseModel):
    id: str = ""
    degree: str = ""
    institution: str = ""
    location: str = ""
    graduation_year: str = ""
    gpa: str = ""
    honors: str = ""


class SkillsSchema(BaseModel):
    languages: list[str] = Field(default_factory=list)
    frameworks: list[str] = Field(default_factory=list)
    databases: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)
    concepts: list[str] = Field(default_factory=list)
    cloud: list[str] = Field(default_factory=list)
    devops: list[str] = Field(default_factory=list)


class CertificationSchema(BaseModel):
    id: str = ""
    name: str = ""
    issuer: str = ""
    year: str = ""
    credential_id: str = ""


class CareerProfileSchema(BaseModel):
    personal_info: PersonalInfoSchema = Field(default_factory=PersonalInfoSchema)
    summary: str = ""
    experience: list[ExperienceSchema] = Field(default_factory=list)
    projects: list[ProjectSchema] = Field(default_factory=list)
    education: list[EducationSchema] = Field(default_factory=list)
    skills: SkillsSchema = Field(default_factory=SkillsSchema)
    certifications: list[CertificationSchema] = Field(default_factory=list)


class ProfileResponse(BaseModel):
    career_data: CareerProfileSchema
    updated_at: str | None = None
    is_complete: bool = False


class GenerateFromProfileRequest(BaseModel):
    job_description: str
    mode: Literal["agent"] = "agent"
    model: str | None = None
