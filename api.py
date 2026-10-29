"""CareerOS API: authenticated career profile and job-search data."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import (
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pwdlib import PasswordHash
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from modules.career_dna import build_career_dna
from modules.database import Base, engine, get_db
from modules.models import APPLICATION_STATUSES, Application, CareerEvent, Skill, User
from modules.resumes import (
    RESUME_MIME,
    Resume,
    delete_resume_file,
    ensure_resume_dir,
    resume_path,
    save_resume_upload,
)

APP_ENV = os.getenv("APP_ENV", "local")

# Fail closed: never sign tokens with a published default outside local dev.
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if APP_ENV != "local":
        raise RuntimeError(
            "SECRET_KEY must be set outside local development. Generate one with: "
            'python -c "import secrets; print(secrets.token_urlsafe(48))"'
        )
    SECRET_KEY = "local-development-only-change-me"

JWT_ALGORITHM = "HS256"

try:
    ACCESS_TOKEN_MINUTES = int(os.getenv("ACCESS_TOKEN_MINUTES", "30"))
except ValueError:
    raise RuntimeError("ACCESS_TOKEN_MINUTES must be an integer")
if ACCESS_TOKEN_MINUTES <= 0:
    raise RuntimeError("ACCESS_TOKEN_MINUTES must be positive")

ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]

password_hasher = PasswordHash.recommended()
bearer = HTTPBearer(auto_error=False)
limiter = Limiter(key_func=get_remote_address)


def create_tables() -> None:
    """Additive schema creation; preserves existing database rows."""
    Base.metadata.create_all(bind=engine)
    # create_all does not add columns to an existing SQLite table.
    if engine.dialect.name == "sqlite":
        from sqlalchemy import inspect, text

        columns = {column["name"] for column in inspect(engine).get_columns("users")}
        if "password_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(
                    text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)")
                )


@asynccontextmanager
async def lifespan(application: FastAPI):
    create_tables()
    ensure_resume_dir()
    yield


app = FastAPI(
    title="CareerOS API",
    description="Private, user-scoped career profiles, job tracking, timelines, and Career DNA.",
    version="1.1.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)


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
    description: str | None = Field(default=None, max_length=5000)
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


class ResumeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_filename: str
    content_label: str
    size_bytes: int
    uploaded_at: datetime


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
PageLimit = Annotated[int, Query(ge=1, le=200)]
PageOffset = Annotated[int, Query(ge=0)]


def _career_dna_for(user: User, db: Session) -> dict[str, int]:
    """Single source of truth for the Career DNA calculation."""
    db.refresh(user, attribute_names=["skills"])
    return build_career_dna(user)


def _current_resume(db: Session, user_id: int) -> Resume:
    resume = db.scalar(select(Resume).where(Resume.user_id == user_id))
    if resume is None:
        raise HTTPException(status_code=404, detail="No resume uploaded")
    return resume


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "CareerOS API", "docs": "/docs"}


@app.get("/health")
def health(db: Database) -> dict[str, str]:
    """Public liveness check: database AND storage must be usable.

    A missing disk makes SQLite silently create an empty database, so a plain
    `select(1)` is not enough — query a real table and verify the upload
    directory, or a broken volume would still report healthy.
    """
    try:
        db.scalar(select(func.count()).select_from(User))
        ensure_resume_dir()
    except Exception:
        raise HTTPException(status_code=503, detail="database or storage unavailable")
    return {"status": "ok"}


@app.post("/auth/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(request: Request, payload: RegisterRequest, db: Database) -> User:
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
@limiter.limit("10/minute")
def login(request: Request, payload: LoginRequest, db: Database) -> TokenResponse:
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


@app.post("/resume", response_model=ResumeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("10/hour")
def upload_resume(
    request: Request,
    user: CurrentUser,
    db: Database,
    file: Annotated[UploadFile, File(description="PDF, DOCX, or TXT resume")],
) -> Resume:
    # New file lands on disk first; only then is the old one replaced, so a
    # failed upload never destroys the user's existing resume.
    new_resume = save_resume_upload(user.id, file)
    existing = db.scalar(select(Resume).where(Resume.user_id == user.id))
    if existing:
        delete_resume_file(existing.stored_filename)
        db.delete(existing)
    db.add(new_resume)
    try:
        db.commit()
        db.refresh(new_resume)
    except IntegrityError:
        db.rollback()
        delete_resume_file(new_resume.stored_filename)
        raise HTTPException(status_code=409, detail="A resume already exists for this account")
    return new_resume


@app.get("/resume", response_model=ResumeResponse)
def get_resume(user: CurrentUser, db: Database) -> Resume:
    return _current_resume(db, user.id)


@app.get("/resume/download")
def download_resume(user: CurrentUser, db: Database) -> FileResponse:
    resume = _current_resume(db, user.id)
    path = resume_path(resume.stored_filename)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Resume file is missing from storage")
    return FileResponse(
        path,
        media_type=RESUME_MIME[resume.content_label],
        filename=resume.original_filename,
    )


@app.delete("/resume", status_code=status.HTTP_204_NO_CONTENT)
def delete_resume(user: CurrentUser, db: Database) -> None:
    resume = _current_resume(db, user.id)
    delete_resume_file(resume.stored_filename)
    db.delete(resume)
    db.commit()


@app.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    user: CurrentUser, db: Database, limit: PageLimit = 50, offset: PageOffset = 0
) -> list[Application]:
    return list(
        db.scalars(
            select(Application)
            .where(Application.user_id == user.id)
            .order_by(Application.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@app.post("/applications", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, user: CurrentUser, db: Database) -> Application:
    company, title = payload.company.strip(), payload.job_title.strip()
    if not company or not title:
        raise HTTPException(status_code=422, detail="Company and job title cannot be blank")
    if payload.status not in APPLICATION_STATUSES:
        raise HTTPException(
            status_code=422,
            detail=f"Status must be one of: {', '.join(APPLICATION_STATUSES)}",
        )
    item = Application(
        user_id=user.id,
        company=company,
        job_title=title,
        status=payload.status,
        applied_date=payload.applied_date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/career-timeline", response_model=list[CareerEventResponse])
def career_timeline(
    user: CurrentUser, db: Database, limit: PageLimit = 50, offset: PageOffset = 0
) -> list[CareerEvent]:
    return list(
        db.scalars(
            select(CareerEvent)
            .where(CareerEvent.user_id == user.id)
            .order_by(CareerEvent.date.desc(), CareerEvent.id.desc())
            .limit(limit)
            .offset(offset)
        )
    )


@app.post("/career-timeline", response_model=CareerEventResponse, status_code=status.HTTP_201_CREATED)
def add_career_event(payload: CareerEventCreate, user: CurrentUser, db: Database) -> CareerEvent:
    event_type, title = payload.type.strip(), payload.title.strip()
    if not event_type or not title:
        raise HTTPException(status_code=422, detail="Event type and title cannot be blank")
    item = CareerEvent(
        user_id=user.id,
        type=event_type,
        title=title,
        description=payload.description,
        date=payload.date,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@app.get("/skills", response_model=list[SkillResponse])
def list_skills(
    user: CurrentUser, db: Database, limit: PageLimit = 200, offset: PageOffset = 0
) -> list[Skill]:
    return list(
        db.scalars(
            select(Skill)
            .where(Skill.user_id == user.id)
            .order_by(Skill.skill_name)
            .limit(limit)
            .offset(offset)
        )
    )


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
    return _career_dna_for(user, db)


@app.get("/career-summary")
def career_summary(user: CurrentUser, db: Database) -> dict[str, object]:
    applications = db.scalar(
        select(func.count()).select_from(Application).where(Application.user_id == user.id)
    ) or 0
    events = db.scalar(
        select(func.count()).select_from(CareerEvent).where(CareerEvent.user_id == user.id)
    ) or 0
    skills = db.scalar(
        select(func.count()).select_from(Skill).where(Skill.user_id == user.id)
    ) or 0
    return {
        "user": {"id": user.id, "name": user.name},
        "counts": {"applications": applications, "career_events": events, "skills": skills},
        "career_dna": _career_dna_for(user, db),
    }

"""CareerOS API: authenticated career profile and job-search data."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
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

def create_tables() -> None:
    # Additive schema creation; preserve existing database rows.
    Base.metadata.create_all(bind=engine)
    # create_all does not add columns to an existing SQLite table.
    if engine.dialect.name == "sqlite":
        from sqlalchemy import inspect, text
        columns = {column["name"] for column in inspect(engine).get_columns("users")}
        if "password_hash" not in columns:
            with engine.begin() as connection:
                connection.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))


@asynccontextmanager
async def lifespan(application: FastAPI):
    create_tables()
    yield


app = FastAPI(
    title="CareerOS API",
    description="Private, user-scoped career profiles, job tracking, timelines, and Career DNA.",
    version="1.0.0",
    lifespan=lifespan,
)


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
