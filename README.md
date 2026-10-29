# CareerOS

Become is the parent brand for a family of tools that help people shape what comes next. CareerOS is its career intelligence workspace. This repository contains the FastAPI backend, the Streamlit CareerOS experience, and the preserved résumé-to-role comparison prototype.

## Run locally

```bash
python -m venv .venv
# macOS/Linux: source .venv/bin/activate
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn api:app --reload
```

The API runs at `http://127.0.0.1:8000`; interactive docs are at `/docs`. In a second terminal, run `streamlit run dashboard.py` for the Become landing page and CareerOS workspace. The résumé comparison prototype is preserved in `prototype_ui.py` and can be run separately with `streamlit run prototype_ui.py`.

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
- `GET /career-summary`
- `GET /health` — public health check.

All career-data queries are scoped to the authenticated user. The initial Career DNA implementation is transparent fixed-rule scoring and should be treated as an exploratory indicator, not a validated assessment.

## Data and deployment

Set `DATABASE_URL` to configure SQLAlchemy. The Render Blueprint uses `sqlite:////var/data/careeros.db`, a persistent disk, and a generated `SECRET_KEY`. The startup routine creates missing tables and applies a narrow additive migration for the password-hash column without dropping existing rows. Back up the SQLite file before production migrations and deploys.

Render persistent disks require a paid service and are mounted only at runtime; review current Render pricing and database recommendations before deploying. For multi-instance or higher-traffic production use, prefer managed PostgreSQL.

## Tests

```bash
pytest -q
```

Tests cover API startup/health, registration and login, password hashing, unauthenticated access, duplicate accounts, and per-user record isolation.


## Become and CareerOS experience

The visual direction follows the supplied prototypes: Become has an understated black-and-gold public landing page, cinematic horizon light, editorial serif typography, and a clear sign-in path. The signed-in CareerOS workspace carries that identity into a dark, gold-accented career dashboard.

The workspace reads and writes the signed-in user's existing API-backed applications, skills, and career timeline. Career DNA uses the existing exploratory fixed-rule API. Career-plan suggestions are assembled from saved profile data and are not predictions. The API does not yet provide a live job-discovery feed or résumé-analysis integration, so those views state their current limits rather than showing invented listings or scores.

Set `CAREEROS_API_URL` if your API is hosted somewhere other than the default URL. The dashboard service is defined separately in `render.yaml`; syncing the Render Blueprint is required to create and deploy that service. A merged PR or successful test run does not prove the live dashboard is deployed.