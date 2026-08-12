"""Load, save, and validate user career profiles."""
from __future__ import annotations

import json
import uuid

from models.profile import UserProfile
from schemas.profile import CareerProfileSchema
from sqlalchemy.orm import Session


def _empty_profile() -> dict:
    return CareerProfileSchema().model_dump()


def get_or_create_profile(db: Session, user_id: int) -> UserProfile:
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    if not profile:
        profile = UserProfile(user_id=user_id, career_data=json.dumps(_empty_profile()))
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def load_career_data(profile: UserProfile) -> CareerProfileSchema:
    try:
        raw = json.loads(profile.career_data or "{}")
    except json.JSONDecodeError:
        raw = {}
    return CareerProfileSchema.model_validate(raw)


def save_career_data(db: Session, user_id: int, data: CareerProfileSchema) -> UserProfile:
    profile = get_or_create_profile(db, user_id)
    profile.career_data = json.dumps(data.model_dump())
    db.commit()
    db.refresh(profile)
    return profile


def profile_is_complete(data: CareerProfileSchema) -> bool:
    """Minimum bar: name + at least one experience or project with content."""
    has_name = bool(data.personal_info.name.strip())
    has_exp = any(
        e.title.strip() or e.company.strip() or any(b.strip() for b in e.bullets)
        for e in data.experience
    )
    has_project = any(
        p.name.strip() or p.problem.strip() or p.solution.strip() or any(b.strip() for b in p.bullets)
        for p in data.projects
    )
    return has_name and (has_exp or has_project)


def ensure_item_ids(data: CareerProfileSchema) -> CareerProfileSchema:
    """Assign stable ids to list items missing them."""
    for exp in data.experience:
        if not exp.id:
            exp.id = str(uuid.uuid4())[:8]
    for proj in data.projects:
        if not proj.id:
            proj.id = str(uuid.uuid4())[:8]
    for edu in data.education:
        if not edu.id:
            edu.id = str(uuid.uuid4())[:8]
    for cert in data.certifications:
        if not cert.id:
            cert.id = str(uuid.uuid4())[:8]
    return data
