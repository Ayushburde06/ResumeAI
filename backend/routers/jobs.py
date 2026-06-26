from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field, field_validator

from limiter import limiter
from models.user import User
from routers.auth import require_user
from services.job_service import JOB_TYPES, SUPPORTED_SITES, format_job_description, search_jobs_async

router = APIRouter()


class JobSearchRequest(BaseModel):
    search_term: str = Field(..., min_length=2, max_length=200)
    location: str | None = Field(None, max_length=200)
    site_name: list[str] | None = None
    results_wanted: int = Field(20, ge=1, le=50)
    hours_old: int | None = Field(None, ge=1, le=720)
    job_type: str | None = None
    is_remote: bool | None = None
    country_indeed: str = "USA"
    distance: int = Field(50, ge=1, le=200)
    linkedin_fetch_description: bool = True
    google_search_term: str | None = Field(None, max_length=300)

    @field_validator("site_name")
    @classmethod
    def validate_sites(cls, sites: list[str] | None) -> list[str] | None:
        if sites is None:
            return None
        normalized = [s.strip().lower() for s in sites if s.strip()]
        invalid = [s for s in normalized if s not in SUPPORTED_SITES]
        if invalid:
            raise ValueError(f"Unsupported site(s): {', '.join(invalid)}")
        return normalized or None

    @field_validator("job_type")
    @classmethod
    def validate_job_type(cls, job_type: str | None) -> str | None:
        if job_type is None:
            return None
        normalized = job_type.strip().lower()
        if normalized not in JOB_TYPES:
            raise ValueError(f"job_type must be one of: {', '.join(JOB_TYPES)}")
        return normalized


class JobListing(BaseModel):
    id: str
    site: str | None = None
    title: str | None = None
    company: str | None = None
    location: str | None = None
    is_remote: bool | None = None
    job_type: str | None = None
    date_posted: str | None = None
    salary: str | None = None
    job_url: str | None = None
    description: str = ""


class JobSearchResponse(BaseModel):
    jobs: list[JobListing]
    total: int


@router.post("/jobs/search", response_model=JobSearchResponse)
@limiter.limit("30/minute")
async def search_jobs_endpoint(
    request: Request,
    body: JobSearchRequest,
    _user: User = Depends(require_user),
):
    try:
        jobs = await search_jobs_async(**body.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=502, detail="Job search is temporarily unavailable. Please try again.")

    listings = [JobListing(**job) for job in jobs]
    return JobSearchResponse(jobs=listings, total=len(listings))


@router.post("/jobs/format-description")
@limiter.limit("30/minute")
async def format_description(
    request: Request,
    job: JobListing,
    _user: User = Depends(require_user),
):
    text = format_job_description(job.model_dump())
    if len(text) < 50:
        raise HTTPException(
            status_code=422,
            detail="Selected job has too little description text. Try another listing or paste the JD manually.",
        )
    return {"job_description": text}
