# CareerOS

CareerOS is an early career-management MVP with a FastAPI backend and a preserved Streamlit resume-to-role comparison prototype.

## Run locally

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn api:app --reload
```

The API runs at `http://127.0.0.1:8000`; interactive docs are at `/docs`. The original Streamlit prototype is preserved in `prototype_ui.py` and can be run separately with `streamlit run prototype_ui.py`.

## Authentication

- `POST /auth/register` — create an account (minimum 12-character password).
- `POST /auth/login` — verify credentials and return a short-lived JWT bearer token.
- `GET /me` — return the authenticated account.

Send `Authorization: Bearer <access_token>` to private endpoints. Passwords are stored as Argon2 hashes; JWTs expire after 30 minutes by default. Set `SECRET_KEY` to a strong random secret in every non-local environment. Never commit production secrets.

## Private API endpoints

- `GET /applications` and `POST /applications`
- `GET /career-timeline` and `POST /career-timeline`
- `GET /skills` and `POST /skills`
- `GET /career-dna`
- `GET /resume` and `GET /resume/download` — inspect or download the authenticated user's uploaded resume.
- `POST /resume` and `DELETE /resume` — upload or delete the authenticated user's resume.
- `GET /career-summary`
- `GET /health` — public health check.

All career-data queries are scoped to the authenticated user. The initial Career DNA implementation is transparent fixed-rule scoring and should be treated as an exploratory indicator, not a validated assessment.

## Data and deployment

Set `DATABASE_URL` to configure SQLAlchemy. The Render Blueprint uses `sqlite:////var/data/careeros.db`, a persistent disk, and a generated `SECRET_KEY`. Set `ALLOWED_ORIGINS` on the Render service to the exact deployed frontend origin (for example, the Vercel production URL); the local default only permits `http://localhost:3000`. The startup routine creates missing tables and applies a narrow additive migration for the password-hash column without dropping existing rows. Editable resume text remains in the legacy `resumes` table; uploaded files use a separate `resume_uploads` table and are stored under `RESUME_DIR` (configured to `/var/data/resumes` in the Render Blueprint) so they survive deploys on the persistent disk. Back up the SQLite file before production migrations and deploys.

Render persistent disks require a paid service and are mounted only at runtime; review current Render pricing and database recommendations before deploying. For multi-instance or higher-traffic production use, prefer managed PostgreSQL.

## Tests

```bash
pytest -q
```

GitHub Actions runs `pytest -q` on pushes and pull requests. The suite currently passes 9 tests covering API startup/health, registration and login, password hashing, token expiry, unauthenticated access, duplicate accounts, per-user record isolation, legacy-user migration, and private resume upload/download.


## Frontend

The separate [Become-CareerOs](https://github.com/c00mbs/Become-CareerOs) repository contains the Next.js frontend. Registration, sign-in, authenticated profile reads, career timeline, skill creation, opportunity tracking, and Career DNA display are wired to this API. The frontend stores short-lived access tokens in browser session storage for this MVP. Production deployment, exact-origin CORS configuration, and browser-based end-to-end verification are still outstanding.
