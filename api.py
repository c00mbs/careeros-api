"""CareerOS API: authenticated career profile and job-search data."""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone
from typing import Annotated, Generator

import jwt
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from modules.career_dna import build_career_dna
from modules.database import Base, engine, get_db
from modules.models import APPLICATION_STATUSES, Application, CareerEvent, Skill, User

SECRET_KEY = os.getenv("SECRET_KEY", "local-development-only-change-me")
JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)

app = FastAPI(
    title="CareerOS API",
    description="Private, user-scoped career profiles, job tracking, timelines, and Career DNA.",
    version="1.0.0",
)


@app.on_event("startup")
def create_tables() -> None:
    # create_all is additive and does not drop or rewrite existing SQLite data.
    Base.metadata.create_all(bind=engine)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    email: EmailStr
    password: str = Field(min_length=12, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    email: EmailStr


class ApplicationCreate(BaseModel):
    company: str = Field(min_length=1, max_length=200)
    job_title: str = Field(min_length=1, max_length=200)
    status: str = "Saved"
    applied_date: date | None = None


class ApplicationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    company: str
    job_title: str
    status: str
    applied_date: date | None


class CareerEventCreate(BaseModel):
    type: str = Field(min_length=1, max_length=50)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    date: date


class CareerEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    type: str
    title: str
    description: str | None
    date: date


class SkillCreate(BaseModel):
    skill_name: str = Field(min_length=1, max_length=100)
    proficiency: int = Field(ge=1, le=5)


class SkillResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    skill_name: str
    proficiency: int


def create_access_token(user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(minutes=ACCESS_TOKEN_MINUTES),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Valid bearer token required",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    try:
        payload = jwt.decode(
            credentials.credentials,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM],
            options={"require": ["exp", "iat", "sub"]},
        )
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, ValueError, TypeError, KeyError):
        raise unauthorized
    user = db.get(User, user_id)
    if user is None:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
Database = Annotated[Session, Depends(get_db)]


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "CareerOS API", "docs": "/docs"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest, db: Database) -> User:
    name = payload.name.strip()
    email = str(payload.email).strip().lower()
    if not name:
        raise HTTPException(status_code=422, detail="Name cannot be blank")
    existing = db.scalar(select(User).where(func.lower(User.email) == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    user = User(name=name, email=email, password_hash=password_hasher.hash(payload.password))
    db.add(user)
    try:
        db.commit()
        db.refresh(user)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    return user


@app.post("/auth/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Database) -> TokenResponse:
    email = str(payload.email).strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == email))
    if not user or not user.password_hash or not password_hasher.verify(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenResponse(
        access_token=create_access_token(user.id),
        expires_in=ACCESS_TOKEN_MINUTES * 60,
    )


@app.get("/me", response_model=UserResponse)
def me(user: CurrentUser) -> User:
    return user


@app.get("/applications", response_model=list[ApplicationResponse])
def list_applications(user: CurrentUser, db: Database) -> list[Application]:
    return list(db.scalars(select(Application).where(Application.user_id == user.id).order_by(Application.id.desc())))


@app.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, user: CurrentUser, db: Database) -> Application:
    company, title = payload.company.strip(), payload.job_title.strip()
    if not company or not title:
        raise HTTPException(status_code=422, detail="Company and job title cannot be blank")
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(status_code=422, detail=f"Status must be one of: {', '.join(APPLICATION_STATUSES)}")
    item = Application(
        user_id=user.id, company=company, job_title=title,
        status=payload.status, applied_date=payload.applied_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/career-timeline", response_model=list[CareerEventResponse])
def career_timeline(user: CurrentUser, db: Database) -> list[CareerEvent]:
    return list(db.scalars(select(CareerEvent).where(CareerEvent.user_id == user.id).order_by(CareerEvent.date.desc(), CareerEvent.id.desc())))


@app.post("/career-timeline", response_model=CareerEventResponse, status_code=status.HTTP_201_CREATED)
def add_career_event(payload: CareerEventCreate, user: CurrentUser, db: Database) -> CareerEvent:
    event_type, title = payload.type.strip(), payload.title.strip()
    if not event_type or not title:
        raise HTTPException(status_code=422, detail="Event type and title cannot be blank")
    item = CareerEvent(user_id=user.id, type=event_type, title=title, description=payload.description, date=payload.date)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/skills", response_model=list[SkillResponse])
def list_skills(user: CurrentUser, db: Database) -> list[Skill]:
    return list(db.scalars(select(Skill).where(Skill.user_id == user.id).order_by(Skill.skill_name)))


@app.post("/skills", response_model=SkillResponse, status_code=status.HTTP_201_CREATED)
def add_skill(payload: SkillCreate, user: CurrentUser, db: Database) -> Skill:
    skill_name = payload.skill_name.strip()
    if not skill_name:
        raise HTTPException(status_code=422, detail="Skill name cannot be blank")
    item = Skill(user_id=user.id, skill_name=skill_name, proficiency=payload.proficiency)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/career-dna")
def career_dna(user: CurrentUser, db: Database) -> dict[str, int]:
    # Build from only the authenticated user's saved skills.
    db.refresh(user, attribute_names=["skills"])
    return build_career_dna(user)


@app.get("/career-summary")
def career_summary(user: CurrentUser, db: Database) -> dict[str, object]:
    applications = db.scalar(select(func.count()).select_from(Application).where(Application.user_id == user.id)) or 0
    events = db.scalar(select(func.count()).select_from(CareerEvent).where(CareerEvent.user_id == user.id)) or 0
    skills = db.scalar(select(func.count()).select_from(Skill).where(Skill.user_id == user.id)) or 0
    return {
        "user": {"id": user.id, "name": user.name},
        "counts": {"applications": applications, "career_events": events, "skills": skills},
        "career_dna": career_dna(user, db),
    }
