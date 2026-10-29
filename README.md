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
$env:CAREEROS_API_URL = "http://127.0.0.1:8000"
streamlit run dashboard.py
```

The API runs at `http://127.0.0.1:8000`; its interactive documentation is at `/docs`. Local runs use a local SQLite database named `careeros.db` in the project directory. The deployed dashboard receives its API address through `CAREEROS_API_URL` in `render.yaml`. The signed-in CareerOS workspace includes résumé-to-role skill comparison. The original standalone prototype remains available with `streamlit run prototype_ui.py`.

## What is connected today

The dashboard uses the existing FastAPI authentication and account-scoped endpoints. A signed-in member can view and maintain:

- Applications and their status.
- Remote job discovery through the Himalayas public job-search feed, with role, country, seniority, and employment filters. Members can follow the original listing or save a role to their application pipeline.
- Self-rated skills.
- Education, roles, projects, and other career timeline events.
- Career DNA indicators computed from saved skills.
- Career-plan suggestions derived from the member's saved profile.

The database startup migration adds the password-hash column without dropping existing users or career records. Career data endpoints filter by the authenticated user.

## Honest product limits

- Career DNA uses fixed rules. It is exploratory and is not a validated assessment or hiring prediction.
- Job discovery currently searches remote roles from Himalayas. Its listings refresh daily, so they are not a real-time feed and may close before the listed expiration date. Each result links to its source and original application URL.
- Résumé analysis supports PDF files with selectable text and TXT files. In Explore Careers, detected résumé skills can prioritize remote listings by mentions in their title and excerpt; comparison happens in the Streamlit session, and résumé text is not sent to the job provider or saved to the account. The match is a listing-text hint, not a hiring or suitability score. The Analyze Résumé page also compares detected skills with a pasted job description.
- Career plans and insights use saved account data. They do not produce a match percentage, hiring probability, or fabricated activity.
- Scanned image-only PDFs are not supported in the signed-in analyzer yet. The current skill list is curated, so results can miss relevant wording and must be reviewed by the user.
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


