# CareerOS Corporate Dashboard — Design and Implementation Plan

## Product direction
**Design:** corporate analytics, executive-clean, top navigation. Use a restrained navy/charcoal base, warm neutral surfaces, accessible contrast, concise labels, clear data hierarchy, and responsive layouts. Avoid decorative clutter and avoid implying exploratory indicators predict hiring outcomes.

**Product promise:** “Who are you becoming?” CareerOS connects career history, skills, target roles, and job-search activity in one career intelligence workspace.

## Dashboard information architecture
1. **Overview** — account-specific application, career-event, and skill counts; Career DNA indicators; suggested next actions.
2. **Applications** — add and review company, role, status, and applied date.
3. **Skills & timeline** — maintain skills and proficiency; record education, roles, projects, certifications, and achievements; inspect Career DNA.
4. **Résumé & roles** — résumé upload and job-description comparison, with visible evidence and user review.
5. **Account access** — create account, sign in, sign out; API calls use the authenticated bearer token.

## Existing implementation inspected
- `api.py` provides FastAPI registration/login, JWT authentication, `/me`, `/applications`, `/career-timeline`, `/skills`, `/career-dna`, `/career-summary`, and `/health`.
- `prototype_ui.py` is the existing résumé-to-role comparison prototype. It uses phrase/fuzzy matching and optional OCR and currently runs as a separate Streamlit app.
- `render.yaml` now contains a separate `careeros-dashboard` web-service definition alongside the API. Render still needs to sync/deploy the Blueprint and the resulting URL must be verified.
- `requirements.txt` already includes Streamlit. The dashboard uses httpx for API requests; keep explicit dependency declarations aligned before production rollout.

## Implementation phases

### Phase 1 — dashboard shell and API-backed MVP
- Add `dashboard.py` as a separate Streamlit frontend; keep `api.py` and the legacy prototype intact.
- Use horizontal top navigation and responsive metric cards.
- Add sign-in/registration, application creation/listing, skill creation/listing, career-event creation/listing, Career DNA chart, and account-specific overview.
- Clearly label résumé comparison as a prototype until it is integrated.
- Configure `CAREEROS_API_URL` via deployment environment, defaulting to the current API URL for local convenience.

### Phase 2 — test and usability hardening
- Add tests for request handling and navigation-critical flows where practical.
- Run `pytest -q`, verify startup with `streamlit run dashboard.py`, and exercise registration/login plus authenticated reads/writes against a test API/database.
- Check mobile layout, form validation, expired-token handling, empty states, and API-unavailable messaging.
- Do not test against or modify production user records during verification.

### Phase 3 — connect résumé intelligence
- Extract matching logic from `prototype_ui.py` into a reusable, side-effect-free module.
- Support upload parsing, evidence snippets, role-skill selection, comparison, and corrections in the dashboard.
- Keep matches explainable; no fabricated fit score, hiring probability, or automatic claims that a missing keyword means a user lacks the skill.

### Phase 4 — deployment
- Deploy the API and dashboard as separate services. `render.yaml` now defines both services; sync the Render Blueprint, confirm the dashboard service is created, and verify its assigned public URL.
- Set `CAREEROS_API_URL` to the verified API URL.
- Protect secrets and never log bearer tokens.
- Verify the live dashboard URL and test an end-to-end account flow before calling it deployed.

## Release status
- **Design preview:** concept shown in chat; not a deployed page.
- **Repository implementation:** `dashboard.py` and the separate Render service definition are in the feature branch, pending review and CI.
- **Production dashboard:** not deployed or verified; Blueprint sync and live smoke tests remain.
- **Current limitations:** API token is held in Streamlit session state; expired sessions require sign-in again. Résumé matching remains separate until Phase 3.
