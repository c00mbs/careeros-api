"""FastAPI entry point for the CareerOS API."""

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from modules.career_dna import build_career_dna
from modules.models import (
    Application,
    CareerEvent,
    Certification,
    Interview,
    Skill,
    User,
)
from modules.orm_database import SessionLocal, initialize_orm_database

sample_applications = [
    {"company": "Amazon", "title": "Area Manager II", "status": "Interview"},
    {"company": "Microsoft", "title": "Data Analyst", "status": "Applied"},
]


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_orm_database()
    yield


def get_db():
    with SessionLocal() as session:
        yield session


app = FastAPI(title="CareerOS API", lifespan=lifespan)


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "CareerOS API Running"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/applications")
def get_applications() -> list[dict[str, str]]:
    return sample_applications


@app.get("/career-timeline")
def get_career_timeline(
    user_id: int, db: Session = Depends(get_db)
) -> list[dict[str, str | int | None]]:
    events = db.scalars(
        select(CareerEvent)
        .where(CareerEvent.user_id == user_id)
        .order_by(CareerEvent.date.desc(), CareerEvent.id.desc())
    ).all()
    return [
        {
            "date": event.date.isoformat(),
            "type": event.type,
            "title": event.title,
        }
        for event in events
    ]


@app.get("/career-dna")
def get_career_dna(user_id: int, db: Session = Depends(get_db)) -> dict[str, int]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return build_career_dna(user)


@app.get("/career-summary")
def get_career_summary(
    user_id: int, db: Session = Depends(get_db)
) -> dict[str, int | dict[str, int]]:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    applications_count = db.scalar(
        select(func.count())
        .select_from(Application)
        .where(Application.user_id == user_id)
    )
    interviews_count = db.scalar(
        select(func.count())
        .select_from(Interview)
        .join(Application, Interview.application_id == Application.id)
        .where(Application.user_id == user_id)
    )
    certifications_count = db.scalar(
        select(func.count())
        .select_from(Certification)
        .where(Certification.user_id == user_id)
    )
    skills_count = db.scalar(
        select(func.count()).select_from(Skill).where(Skill.user_id == user_id)
    )
    career_events_count = db.scalar(
        select(func.count())
        .select_from(CareerEvent)
        .where(CareerEvent.user_id == user_id)
    )

    return {
        "skills": skills_count,
        "certifications": certifications_count,
        "applications": applications_count,
        "interviews": interviews_count,
        "career_events": career_events_count,
        "dna": build_career_dna(user),
    }
