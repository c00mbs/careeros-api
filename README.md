# Become · CareerOS

**Become** is the parent brand. **CareerOS** is its career intelligence workspace: a private place to organize applications, skills, career milestones, and next steps.

The product follows two connected visual directions:

- **Become:** a minimal black-and-gold public page, cinematic horizon light, generous negative space, an editorial serif headline, and sign-in in the top navigation.
- **CareerOS:** a dark, premium workspace with restrained gold accents, compact navigation, career analytics, applications, skills, Career DNA, a career plan, and insights.

## Run locally

Create a virtual environment and install the dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

Start the API in one terminal and the Become/CareerOS interface in another:

```powershell
uvicorn api:app --reload
```

```powershell
streamlit run dashboard.py
```

The API runs at `http://127.0.0.1:8000`; its interactive documentation is at `/docs`. Set `CAREEROS_API_URL` when the API runs at a different address. The original résumé comparison prototype remains available separately with `streamlit run prototype_ui.py`.

## What is connected today

The dashboard uses the existing FastAPI authentication and account-scoped endpoints. A signed-in member can view and maintain:

- Applications and their status.
- Self-rated skills.
- Education, roles, projects, and other career timeline events.
- Career DNA indicators computed from saved skills.
- Career-plan suggestions derived from the member's saved profile.

The database startup migration adds the password-hash column without dropping existing users or career records. Career data endpoints filter by the authenticated user.

## Honest product limits

- Career DNA uses fixed rules. It is exploratory and is not a validated assessment or hiring prediction.
- Live job discovery is not available in the current API.
- Résumé comparison remains a separate prototype and is not connected to the signed-in dashboard.
- Career plans and insights use saved account data. They do not produce a match percentage, hiring probability, or fabricated activity.
- Streamlit keeps the access token in session state; an expired token requires signing in again.

## Authentication and data

- `POST /auth/register` creates an account (minimum password length: 12 characters).
- `POST /auth/login` returns a short-lived JWT bearer token.
- Private endpoints require `Authorization: Bearer <access_token>`.
- Passwords are stored as Argon2 hashes. JWTs expire after 30 minutes by default.
- Configure a strong `SECRET_KEY` in every non-local environment. Do not commit production secrets.
- `DATABASE_URL` selects the SQLAlchemy database. The Render Blueprint uses a persistent SQLite disk and a generated secret key; review the deployment configuration and back up production data before migrations.

## Main API routes

| Route | Purpose |
| --- | --- |
| `GET /me` | Current signed-in account |
| `GET`, `POST /applications` | Account application pipeline |
| `GET`, `POST /skills` | Account skills and proficiency |
| `GET`, `POST /career-timeline` | Account career milestones |
| `GET /career-dna` | Exploratory profile from saved skills |
| `GET /career-summary` | Account-level counts and profile summary |
| `GET /health` | Public service health |

## Checks

```powershell
pytest -q
```

The dashboard and API are separate Render services in `render.yaml`. A successful test run does not confirm that the Blueprint has been synced or that the live sign-in flow has been verified.
