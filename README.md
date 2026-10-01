# CareerOS API

A FastAPI service for career profiles, application tracking, career timelines,
and Career DNA summaries. Data is stored in SQLAlchemy models backed by SQLite.

## Run locally

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn api:app --reload
```

The API listens at `http://127.0.0.1:8000`; interactive API docs are at `/docs`.

## Endpoints

- `GET /` — service welcome response.
- `GET /health` — deployment health check.
- `GET /applications` — sample application records.
- `GET /career-timeline?user_id=<id>` — saved events, newest first.
- `GET /career-dna?user_id=<id>` — saved-skill scores by category.
- `GET /career-summary?user_id=<id>` — counts and Career DNA scores.

Tables are initialized automatically at API startup. Set `DATABASE_URL` to
change the database URL; Render config mounts SQLite at `/var/data/careeros.db`.

## Deploy to Render

Create a Render Blueprint from this GitHub repository and choose `render.yaml`.
The Blueprint includes a persistent disk for SQLite. Persistent disks require a
paid Render web service and incur charges; review the current Render pricing
before deploying. Render will provide a public `onrender.com` address after
successful deployment.
