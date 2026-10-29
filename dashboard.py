"""CareerOS corporate dashboard — Streamlit frontend for the authenticated API."""

from __future__ import annotations

import os
from datetime import date
from typing import Any

import httpx
import streamlit as st

API_URL = os.getenv("CAREEROS_API_URL", "https://careeros-api-yadv.onrender.com").rstrip("/")
TIMEOUT = 15.0

st.set_page_config(page_title="CareerOS | Career Intelligence", page_icon="🧭", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
.block-container {max-width:1320px;padding-top:1.6rem;padding-bottom:3rem}
[data-testid="stHeader"] {background:transparent}
.hero {padding:1.4rem 1.6rem;border-radius:16px;background:linear-gradient(120deg,#17212b,#293d4c);color:white;margin-bottom:1.1rem}
.hero p {color:#d9e1e7;margin-bottom:0}
div[data-testid="stMetric"] {border:1px solid rgba(120,130,140,.25);padding:1rem;border-radius:14px;background:rgba(128,128,128,.035)}
.eyebrow {letter-spacing:.12em;text-transform:uppercase;font-size:.72rem;font-weight:700;opacity:.75}
</style>
""", unsafe_allow_html=True)

for key, default in {"token": "", "user": None, "auth_mode": "Sign in"}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def api_request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    try:
        response = httpx.request(method, f"{API_URL}{path}", json=payload, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"CareerOS API could not be reached at {API_URL}. Check deployment and CAREEROS_API_URL. Details: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{response.status_code}: {detail}")
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def show_error(action):
    try:
        return action()
    except (RuntimeError, ValueError) as exc:
        st.error(str(exc))
        return None


def sign_out() -> None:
    st.session_state.token = ""
    st.session_state.user = None
    st.rerun()


def auth_screen() -> None:
    st.markdown('<div class="hero"><div class="eyebrow">Career intelligence platform</div><h1>Who are you becoming?</h1><p>Build a clearer view of your experience, opportunities, and next move.</p></div>', unsafe_allow_html=True)
    left, right = st.columns([1.05, 1], gap="large")
    with left:
        st.subheader("One connected career workspace")
        st.write("Track applications, map your experience, build your career timeline, and review your skills in one place.")
        st.markdown("- **Career overview** — counts and Career DNA indicators\n- **Application pipeline** — record roles and track status\n- **Skills & timeline** — maintain your career profile")
        st.caption("Your career records are loaded from the authenticated CareerOS API.")
    with right:
        st.session_state.auth_mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.auth_mode == "Sign in" else 1)
        with st.form("auth_form"):
            name = st.text_input("Full name") if st.session_state.auth_mode == "Create account" else ""
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password", help="Use at least 12 characters when creating an account.")
            submitted = st.form_submit_button("Sign in" if st.session_state.auth_mode == "Sign in" else "Create account", type="primary", use_container_width=True)
        if submitted:
            if st.session_state.auth_mode == "Create account":
                created = show_error(lambda: api_request("POST", "/auth/register", {"name": name, "email": email, "password": password}))
                if created:
                    st.success("Account created. Sign in with your new credentials.")
                    st.session_state.auth_mode = "Sign in"
                    st.rerun()
            else:
                token = show_error(lambda: api_request("POST", "/auth/login", {"email": email, "password": password}))
                if token and token.get("access_token"):
                    st.session_state.token = token["access_token"]
                    user = show_error(lambda: api_request("GET", "/me"))
                    if user:
                        st.session_state.user = user
                        st.rerun()


def overview() -> None:
    st.subheader("Career overview")
    summary = show_error(lambda: api_request("GET", "/career-summary"))
    if not summary:
        st.info("Your overview will appear here once the API returns your career summary.")
        return
    counts = summary.get("counts", {})
    metrics = st.columns(4)
    metrics[0].metric("Applications", counts.get("applications", 0))
    metrics[1].metric("Career events", counts.get("career_events", 0))
    metrics[2].metric("Skills recorded", counts.get("skills", 0))
    dna = summary.get("career_dna", {})
    metrics[3].metric("Career DNA areas", len(dna))
    st.divider()
    left, right = st.columns([1.15, 1], gap="large")
    with left:
        st.markdown("#### Career DNA")
        st.caption("Exploratory fixed-rule indicators—not a validated assessment or hiring prediction.")
        if dna:
            st.bar_chart({str(key).replace("_", " ").title(): value for key, value in dna.items()})
        else:
            st.info("Add skills in Skills & timeline to start building your career profile.")
    with right:
        st.markdown("#### Next actions")
        st.markdown("- Add target roles to your application pipeline.\n- Record strengths and proficiency in Skills & timeline.\n- Add education, projects, and milestones to your timeline.\n- Review résumé skill evidence before relying on a match.")
        st.caption("Counts and indicators above come from your account, not sample dashboard data.")


def applications_page() -> None:
    st.subheader("Application pipeline")
    with st.expander("＋ Add an application", expanded=False):
        with st.form("new_application"):
            company = st.text_input("Company")
            title = st.text_input("Job title")
            status = st.selectbox("Status", ["Saved", "Applied", "Interviewing", "Offer", "Rejected", "Withdrawn"])
            applied = st.date_input("Applied date (optional)", value=None)
            submitted = st.form_submit_button("Save application", type="primary")
        if submitted:
            payload = {"company": company, "job_title": title, "status": status}
            if applied:
                payload["applied_date"] = applied.isoformat()
            created = show_error(lambda: api_request("POST", "/applications", payload))
            if created:
                st.success("Application saved.")
                st.rerun()
    items = show_error(lambda: api_request("GET", "/applications"))
    if items is not None:
        st.dataframe(items, use_container_width=True, hide_index=True) if items else st.info("No applications yet. Add your first target role above.")


def skills_timeline_page() -> None:
    st.subheader("Skills & career timeline")
    skill_tab, timeline_tab, dna_tab = st.tabs(["Skills", "Career timeline", "Career DNA"])
    with skill_tab:
        with st.expander("＋ Add a skill", expanded=False):
            with st.form("new_skill"):
                skill_name = st.text_input("Skill name", placeholder="e.g. Stakeholder management")
                proficiency = st.slider("Proficiency", 1, 5, 3, help="Your self-assessment; 5 is strongest.")
                submitted = st.form_submit_button("Save skill", type="primary")
            if submitted:
                created = show_error(lambda: api_request("POST", "/skills", {"skill_name": skill_name, "proficiency": proficiency}))
                if created:
                    st.success("Skill saved.")
                    st.rerun()
        skills = show_error(lambda: api_request("GET", "/skills"))
        if skills is not None:
            st.dataframe(skills, use_container_width=True, hide_index=True) if skills else st.info("No skills recorded yet.")
    with timeline_tab:
        with st.expander("＋ Add a milestone", expanded=False):
            with st.form("new_event"):
                event_type = st.selectbox("Milestone type", ["Education", "Role", "Project", "Certification", "Achievement", "Other"])
                event_title = st.text_input("Title")
                event_description = st.text_area("Details (optional)")
                event_date = st.date_input("Date", value=date.today())
                submitted = st.form_submit_button("Save milestone", type="primary")
            if submitted:
                created = show_error(lambda: api_request("POST", "/career-timeline", {"type": event_type, "title": event_title, "description": event_description or None, "date": event_date.isoformat()}))
                if created:
                    st.success("Milestone saved.")
                    st.rerun()
        events = show_error(lambda: api_request("GET", "/career-timeline"))
        if events is not None:
            st.dataframe(events, use_container_width=True, hide_index=True) if events else st.info("No milestones recorded yet.")
    with dna_tab:
        dna = show_error(lambda: api_request("GET", "/career-dna"))
        if dna is not None:
            st.caption("Exploratory indicator based on saved skills; not a validated psychometric test.")
            st.bar_chart({str(key).replace("_", " ").title(): value for key, value in dna.items()}) if dna else st.info("Add skills to build your Career DNA view.")


def resume_role_page() -> None:
    st.subheader("Résumé & role intelligence")
    st.info("The existing résumé-to-role comparison is an early prototype in prototype_ui.py. It uses transparent phrase matching and optional OCR; it is not yet connected to this authenticated dashboard.")
    st.markdown("**Current capabilities in the prototype**")
    st.markdown("- Upload a résumé PDF or TXT file.\n- Paste a target job description.\n- Review detected skill evidence and compare overlap.\n- Inspect extracted résumé text when matches look wrong.")
    st.link_button("View prototype source on GitHub", "https://github.com/c00mbs/careeros-api/blob/main/prototype_ui.py")
    st.warning("Next integration step: move matching logic into a reusable module, then add reviewed results and role comparisons here. Do not treat keyword overlap as a hiring score.")


def main() -> None:
    if not st.session_state.token:
        auth_screen()
        return
    user = st.session_state.user or {}
    st.markdown('<div class="hero"><div class="eyebrow">CareerOS · Career intelligence</div><h1>Who are you becoming?</h1><p>Your experience, opportunities, and next move—connected.</p></div>', unsafe_allow_html=True)
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.caption(f"Signed in as {user.get('name', 'CareerOS member')} · {user.get('email', '')}")
    with header_right:
        if st.button("Sign out", use_container_width=True):
            sign_out()
    page = st.radio("Workspace", ["Overview", "Applications", "Skills & timeline", "Résumé & roles"], horizontal=True, label_visibility="collapsed")
    st.divider()
    if page == "Overview":
        overview()
    elif page == "Applications":
        applications_page()
    elif page == "Skills & timeline":
        skills_timeline_page()
    else:
        resume_role_page()
    st.divider()
    st.caption("CareerOS MVP · API-backed records are private to the signed-in account. Always review automated skill evidence.")


if __name__ == "__main__":
    main()
