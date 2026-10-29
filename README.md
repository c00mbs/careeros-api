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


## Corporate dashboard

A separate Streamlit dashboard entrypoint is available in `dashboard.py`. Run it locally after starting the API:

```bash
streamlit run dashboard.py
```

Set `CAREEROS_API_URL` if your API is hosted somewhere other than the default URL. The dashboard service is also defined separately in `render.yaml`; syncing the Render Blueprint is required to create/deploy that service. Do not treat a merged PR or a successful test run as proof that the live dashboard is deployed.
