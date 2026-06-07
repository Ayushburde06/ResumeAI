import asyncio
from datetime import date, datetime
from typing import Any

import pandas as pd
from jobspy import scrape_jobs

SUPPORTED_SITES = ("indeed", "linkedin", "zip_recruiter", "google", "glassdoor")
JOB_TYPES = ("fulltime", "parttime", "internship", "contract")


def _clean(value: Any) -> Any:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, str):
        stripped = value.strip()
        return stripped or None
    return value


def _row_to_job(row: dict) -> dict:
    city = _clean(row.get("city"))
    state = _clean(row.get("state"))
    location_parts = [p for p in (city, state) if p]
    location = ", ".join(location_parts) if location_parts else _clean(row.get("location"))

    min_amount = _clean(row.get("min_amount"))
    max_amount = _clean(row.get("max_amount"))
    salary = None
    if min_amount is not None or max_amount is not None:
        interval = _clean(row.get("interval")) or "yearly"
        currency = _clean(row.get("currency")) or "USD"
        if min_amount is not None and max_amount is not None:
            salary = f"{currency} {min_amount:,.0f}–{max_amount:,.0f} / {interval}"
        elif min_amount is not None:
            salary = f"{currency} {min_amount:,.0f}+ / {interval}"
        elif max_amount is not None:
            salary = f"Up to {currency} {max_amount:,.0f} / {interval}"

    job_url = _clean(row.get("job_url"))
    return {
        "id": job_url or f"{_clean(row.get('site'))}-{_clean(row.get('title'))}-{_clean(row.get('company'))}",
        "site": _clean(row.get("site")),
        "title": _clean(row.get("title")),
        "company": _clean(row.get("company")),
        "location": location,
        "is_remote": bool(row.get("is_remote")) if _clean(row.get("is_remote")) is not None else None,
        "job_type": _clean(row.get("job_type")),
        "date_posted": _clean(row.get("date_posted")),
        "salary": salary,
        "job_url": job_url,
        "description": _clean(row.get("description")) or "",
    }


def format_job_description(job: dict) -> str:
    lines: list[str] = []
    if job.get("title"):
        lines.append(f"Job Title: {job['title']}")
    if job.get("company"):
        lines.append(f"Company: {job['company']}")
    if job.get("location"):
        lines.append(f"Location: {job['location']}")
    if job.get("is_remote"):
        lines.append("Work arrangement: Remote")
    if job.get("job_type"):
        lines.append(f"Employment type: {job['job_type']}")
    if job.get("salary"):
        lines.append(f"Compensation: {job['salary']}")
    if job.get("date_posted"):
        lines.append(f"Posted: {job['date_posted']}")
    if job.get("job_url"):
        lines.append(f"Apply: {job['job_url']}")
    if job.get("description"):
        lines.extend(["", job["description"]])
    return "\n".join(lines).strip()


def search_jobs(
    *,
    search_term: str,
    location: str | None = None,
    site_name: list[str] | None = None,
    results_wanted: int = 20,
    hours_old: int | None = None,
    job_type: str | None = None,
    is_remote: bool | None = None,
    country_indeed: str = "USA",
    distance: int = 50,
    linkedin_fetch_description: bool = True,
    google_search_term: str | None = None,
    verbose: int = 0,
) -> list[dict]:
    kwargs: dict[str, Any] = {
        "search_term": search_term.strip(),
        "results_wanted": results_wanted,
        "country_indeed": country_indeed,
        "distance": distance,
        "linkedin_fetch_description": linkedin_fetch_description,
        "verbose": verbose,
    }

    if site_name:
        kwargs["site_name"] = site_name
    if location:
        kwargs["location"] = location.strip()
    if hours_old is not None:
        kwargs["hours_old"] = hours_old
    if job_type:
        kwargs["job_type"] = job_type
    if is_remote is not None:
        kwargs["is_remote"] = is_remote
    if google_search_term:
        kwargs["google_search_term"] = google_search_term.strip()

    df = scrape_jobs(**kwargs)
    if df is None or df.empty:
        return []

    jobs: list[dict] = []
    for row in df.to_dict(orient="records"):
        job = _row_to_job(row)
        if job.get("title"):
            jobs.append(job)
    return jobs


async def search_jobs_async(**kwargs) -> list[dict]:
    return await asyncio.to_thread(search_jobs, **kwargs)
