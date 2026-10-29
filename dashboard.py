"""Become landing page and CareerOS workspace backed by the authenticated API."""

from __future__ import annotations

import os
from collections import Counter
from datetime import date
from typing import Any

import httpx
import streamlit as st

API_URL = os.getenv("CAREEROS_API_URL", "https://careeros-api-yadv.onrender.com").rstrip("/")
TIMEOUT = 15.0
GOLD = "#d9ad62"

st.set_page_config(page_title="Become · CareerOS", page_icon="✦", layout="wide", initial_sidebar_state="collapsed")
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Playfair+Display:ital,wght@0,500;0,600;1,500;1,600&display=swap');
:root{--bg:#080909;--panel:#101111;--panel2:#151513;--gold:#d9ad62;--muted:#a09a8e;--line:rgba(217,173,98,.22)}
.stApp{background:radial-gradient(ellipse at 50% 0%,#17130d 0%,#090909 48%,#070808 100%);color:#f4f0e8;font-family:'DM Sans',sans-serif}
[data-testid="stHeader"]{background:transparent}.block-container{max-width:1480px;padding:1rem 2rem 3rem}
h1,h2,h3{font-family:'Playfair Display',Georgia,serif!important;color:#f6f1e8!important;letter-spacing:-.025em}
p, label, [data-testid="stMarkdownContainer"]{color:#eee9df}
div[data-testid="stMetric"]{background:linear-gradient(145deg,#171715,#101111);border:1px solid var(--line);border-radius:15px;padding:1.1rem 1.3rem;min-height:116px}
div[data-testid="stMetricLabel"]{color:#c7bda9}div[data-testid="stMetricValue"]{color:#f4d396;font-family:'Playfair Display',serif}
div[data-testid="stForm"]{background:#111211;border:1px solid var(--line);padding:1.2rem;border-radius:16px}
div[data-testid="stExpander"]{border:1px solid var(--line);border-radius:14px;background:#101111}
div[data-testid="stDataFrame"]{border:1px solid var(--line);border-radius:14px;overflow:hidden}
div.stButton>button,div.stFormSubmitButton>button{border:1px solid #bd914c;background:linear-gradient(120deg,#e8c780,#bd8c40);color:#17120a;border-radius:9px;font-weight:700;min-height:2.7rem}
div.stButton>button:hover,div.stFormSubmitButton>button:hover{border-color:#f2d99f;color:#090909;box-shadow:0 0 24px #d9ad6230}
div[data-baseweb="tab-list"]{gap:.35rem;border-bottom:1px solid var(--line)}button[data-baseweb="tab"]{color:#d0c7b6}
.landing-nav{display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);padding:.5rem .3rem 1.1rem;margin-bottom:1rem}
.become-mark{font-family:'Playfair Display',serif;color:#e2bc74;font-size:2.2rem;letter-spacing:-.06em}
.become-mark span{font:500 .58rem 'DM Sans',sans-serif;color:#e2bc74;vertical-align:top;margin-left:.1rem}
.st-key-landing_sign_in button{background:transparent!important;color:#e2bc74!important;border:1px solid #bd914c!important;font-weight:500!important}
.landing-hero{min-height:74vh;display:flex;align-items:center;justify-content:center;text-align:center;position:relative;overflow:hidden;margin:0 -2rem;padding:5rem 1rem 9rem;background:radial-gradient(ellipse at 50% 92%,#b1782c40 0%,#6b481b20 13%,transparent 37%),linear-gradient(180deg,transparent 55%,#16110b 86%,#090909 100%)}
.landing-hero:after{content:'';position:absolute;bottom:13%;left:-5%;width:110%;height:1px;background:linear-gradient(90deg,transparent,#b27a34 20%,#ffe2a0 49%,#fff3cc 50%,#e0ad59 55%,#a36b26 82%,transparent);box-shadow:0 0 12px 3px #e3a84a66,0 0 76px 22px #b7762440;transform:rotate(-1.2deg)}
.landing-copy{position:relative;z-index:1;margin-top:-3rem}.landing-kicker,.eyebrow{color:#d2ad70;text-transform:uppercase;letter-spacing:.22em;font-size:.72rem;font-weight:600}
.landing-copy h1{font-size:clamp(3.3rem,8vw,7.5rem)!important;line-height:1.05!important;color:#e9c681!important;text-shadow:0 0 38px #c28c4440;margin:1.2rem auto;max-width:1050px}
.landing-copy h1 em{font-weight:500}.landing-copy p{color:#d6c8ad;font-size:1.06rem;letter-spacing:.04em}
.surface{background:linear-gradient(145deg,#151614,#0d0e0e);border:1px solid var(--line);border-radius:17px;padding:1.2rem 1.35rem;margin:.3rem 0 1rem}
.surface-title{font:500 1.35rem 'Playfair Display',serif;color:#efd398}.small-note{color:#aaa293;font-size:.86rem}
.section-heading{font:500 1.6rem 'Playfair Display',serif;color:#efd398;margin:.6rem 0}
.quote-card{background:linear-gradient(140deg,#191713,#101111);border:1px solid var(--line);border-radius:16px;padding:1.2rem;height:100%}
.gold-rule{height:1px;background:linear-gradient(90deg,#d9ad6280,transparent);margin:.8rem 0}
.plan-step{border-left:2px solid #bd914c;padding:.2rem .8rem;margin:.7rem 0}
.stRadio label{color:#e4ddcf!important}
@media(max-width:760px){.block-container{padding:.7rem 1rem 2rem}.landing-hero{margin:0 -1rem;min-height:62vh}.landing-hero:after{bottom:16%}}
</style>
""", unsafe_allow_html=True)

for key, default in {"token": "", "user": None, "auth_mode": "Sign in", "show_auth": False, "workspace_page": "Dashboard"}.items():
    if key not in st.session_state:
        st.session_state[key] = default


def api_request(method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
    headers = {"Authorization": f"Bearer {st.session_state.token}"} if st.session_state.token else {}
    try:
        response = httpx.request(method, f"{API_URL}{path}", json=payload, headers=headers, timeout=TIMEOUT)
    except httpx.HTTPError as exc:
        raise RuntimeError(f"CareerOS could not reach its API. Check the service and CAREEROS_API_URL. Details: {exc}") from exc
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"{response.status_code}: {detail}")
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


def load_data(path: str, label: str) -> Any:
    try:
        return api_request("GET", path)
    except (RuntimeError, ValueError) as exc:
        st.error(f"{label}: {exc}")
        return None


def sign_out() -> None:
    st.session_state.token = ""
    st.session_state.user = None
    st.session_state.show_auth = False
    st.rerun()


def render_auth_form() -> None:
    st.markdown('<div class="section-heading">Your next chapter starts here.</div>', unsafe_allow_html=True)
    left, right = st.columns([1, 1.15], gap="large")
    with left:
        st.markdown('<div class="surface"><div class="surface-title">A clearer way forward</div><p>Bring your experience, skills, applications, and next steps into one private workspace.</p><div class="gold-rule"></div><span class="small-note">Your career records remain attached to your account.</span></div>', unsafe_allow_html=True)
    with right:
        st.session_state.auth_mode = st.radio("Account", ["Sign in", "Create account"], horizontal=True, label_visibility="collapsed", index=0 if st.session_state.auth_mode == "Sign in" else 1)
        with st.form("auth_form"):
            name = st.text_input("Full name") if st.session_state.auth_mode == "Create account" else ""
            email = st.text_input("Email address")
            password = st.text_input("Password", type="password", help="Use at least 12 characters when creating an account.")
            submitted = st.form_submit_button("Sign in" if st.session_state.auth_mode == "Sign in" else "Create account", use_container_width=True)
        if submitted:
            if st.session_state.auth_mode == "Create account":
                try:
                    api_request("POST", "/auth/register", {"name": name, "email": email, "password": password})
                    st.success("Account created. Sign in with your new credentials.")
                    st.session_state.auth_mode = "Sign in"
                    st.rerun()
                except (RuntimeError, ValueError) as exc:
                    st.error(str(exc))
            else:
                try:
                    result = api_request("POST", "/auth/login", {"email": email, "password": password})
                    st.session_state.token = result["access_token"]
                    st.session_state.user = api_request("GET", "/me")
                    st.session_state.show_auth = False
                    st.rerun()
                except (RuntimeError, ValueError, KeyError) as exc:
                    st.session_state.token = ""
                    st.session_state.user = None
                    st.error(str(exc))


def landing_page() -> None:
    brand, navigation, sign_in = st.columns([1.35, 4.8, 1.1], vertical_alignment="center")
    with brand:
        st.markdown('<div class="become-mark">Become.<span>♛</span></div>', unsafe_allow_html=True)
    with navigation:
        st.markdown('<div class="landing-kicker" style="text-align:center;padding:.8rem 0">Platform　 ·　 About　 ·　 Vision　 ·　 Resources　 ·　 Support</div>', unsafe_allow_html=True)
    with sign_in:
        if st.button("Close" if st.session_state.show_auth else "Sign In　♙", key="landing_sign_in", use_container_width=True):
            st.session_state.show_auth = not st.session_state.show_auth
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)
    st.markdown('<section class="landing-hero"><div class="landing-copy"><h1>Who are you<br><em>becoming?</em></h1></div></section>', unsafe_allow_html=True)
    if st.session_state.show_auth:
        render_auth_form()


def create_application_form() -> None:
    with st.expander("＋ Add an application", expanded=False):
        with st.form("new_application"):
            company = st.text_input("Company")
            title = st.text_input("Job title")
            status = st.selectbox("Status", ["Saved", "Interested", "Applied", "Interviewing", "Offer", "Closed"])
            applied = st.date_input("Applied date (optional)", value=None)
            submitted = st.form_submit_button("Save application")
        if submitted:
            if not company.strip() or not title.strip():
                st.error("Add a company and job title to save this application.")
                return
            payload: dict[str, Any] = {"company": company, "job_title": title, "status": status}
            if applied:
                payload["applied_date"] = applied.isoformat()
            try:
                api_request("POST", "/applications", payload)
                st.success("Application saved to your account.")
                st.rerun()
            except (RuntimeError, ValueError) as exc:
                st.error(str(exc))


def render_applications(applications: list[dict[str, Any]]) -> None:
    statuses = ["Saved", "Interested", "Applied", "Interviewing", "Offer", "Closed"]
    counts = Counter(str(item.get("status", "")) for item in applications)
    cols = st.columns(len(statuses))
    for col, status in zip(cols, statuses):
        col.metric(status, counts[status])
    if applications:
        st.dataframe(applications, use_container_width=True, hide_index=True)
    else:
        st.info("Your pipeline is ready when you are. Add a role you want to keep in view.")


def career_plan(applications: list[dict[str, Any]], skills: list[dict[str, Any]], events: list[dict[str, Any]]) -> list[tuple[str, str]]:
    steps: list[tuple[str, str]] = []
    if not applications:
        steps.append(("Choose a direction", "Save a role that reflects where you want your career to go."))
    elif not any(item.get("status") in {"Applied", "Interviewing", "Offer"} for item in applications):
        steps.append(("Move one opportunity forward", "Review a saved role and update its status when you take the next step."))
    if not skills:
        steps.append(("Capture your strengths", "Add a few skills so your Career DNA can reflect your experience."))
    elif len(skills) < 5:
        steps.append(("Round out your skills profile", "Add more of the strengths you use in the roles you are targeting."))
    if not events:
        steps.append(("Build your career story", "Add an education, project, role, or milestone to your timeline."))
    else:
        steps.append(("Keep your story current", "Add your latest project or milestone when something changes."))
    steps.append(("Review what is working", "Use your applications and skill profile to decide on one focused action this week."))
    return steps[:4]


def dashboard_home(summary: dict[str, Any], applications: list[dict[str, Any]], skills: list[dict[str, Any]], dna: dict[str, Any], events: list[dict[str, Any]]) -> None:
    user = st.session_state.user or {}
    name = str(user.get("name", "there")).split()[0]
    applications_count = len(applications)
    open_count = sum(1 for item in applications if item.get("status") in {"Applied", "Interviewing", "Offer"})
    active_skills = sum(1 for item in skills if int(item.get("proficiency", 0) or 0) >= 4)
    st.markdown(f'<div class="surface"><div class="landing-kicker">YOUR CAREER, IN YOUR HANDS</div><h1 style="font-size:2.5rem">Welcome back, {name}.<br><span style="color:#e4bc75">Let’s build your future.</span></h1><p class="small-note">Your experience, opportunities, and next move—connected.</p></div>', unsafe_allow_html=True)
    m = st.columns(5)
    m[0].metric("Applications", applications_count, help="Roles saved in your private pipeline")
    m[1].metric("Active opportunities", open_count)
    m[2].metric("Skills identified", len(skills))
    m[3].metric("Next steps", len(career_plan(applications, skills, events)))
    m[4].metric("Career milestones", len(events))
    left, middle, right = st.columns([.9, 1.45, 1.15], gap="medium")
    with left:
        st.markdown('<div class="section-heading">Today’s focus</div>', unsafe_allow_html=True)
        for title, detail in career_plan(applications, skills, events)[:3]:
            st.markdown(f'<div class="surface"><strong style="color:#f1d293">✦　{title}</strong><br><span class="small-note">{detail}</span></div>', unsafe_allow_html=True)
    with middle:
        st.markdown('<div class="section-heading">Applications pipeline</div>', unsafe_allow_html=True)
        statuses = ["Saved", "Interested", "Applied", "Interviewing", "Offer", "Closed"]
        counts = Counter(str(item.get("status", "")) for item in applications)
        st.bar_chart({"Roles": {status: counts[status] for status in statuses}}, color=GOLD, height=230)
        if applications:
            st.dataframe(applications[:5], use_container_width=True, hide_index=True)
        else:
            st.caption("Your account has no saved roles yet. Add one to begin building your pipeline.")
    with right:
        st.markdown('<div class="section-heading">Skill intelligence</div>', unsafe_allow_html=True)
        if skills:
            ordered = sorted(skills, key=lambda item: int(item.get("proficiency", 0) or 0), reverse=True)[:6]
            chart = {str(item.get("skill_name", "Skill")): int(item.get("proficiency", 0) or 0) for item in ordered}
            st.bar_chart({"Self-rated proficiency (1–5)": chart}, color=GOLD, height=230)
            st.caption(f"{active_skills} skill(s) are currently self-rated 4 or higher.")
        else:
            st.info("Add skills to start your profile.")
        if dna:
            st.caption("Career DNA is an exploratory profile based on your saved skills.")
    st.markdown('<div class="surface" style="text-align:center;color:#e8c780;font-family:Playfair Display,serif;font-size:1.2rem">Your career is the greatest project you’ll ever lead.</div>', unsafe_allow_html=True)


def render_workspace() -> None:
    pages = ["Dashboard", "Explore Careers", "Analyze Résumé", "Applications", "Skills", "Career Plan", "Career DNA", "Insights"]
    user = st.session_state.user or {}
    brand, nav, profile = st.columns([1.05, 5.3, 1.2], vertical_alignment="center")
    with brand:
        st.markdown('<div class="become-mark" style="font-size:1.55rem">CareerOS<span>WHO ARE YOU BECOMING?</span></div>', unsafe_allow_html=True)
    with nav:
        st.session_state.workspace_page = st.radio("CareerOS navigation", pages, horizontal=True, label_visibility="collapsed", index=pages.index(st.session_state.workspace_page) if st.session_state.workspace_page in pages else 0)
    with profile:
        st.caption(str(user.get("name", "Member")))
        if st.button("Sign out", key="workspace_signout", use_container_width=True):
            sign_out()
    st.markdown('<div class="gold-rule"></div>', unsafe_allow_html=True)

    page = st.session_state.workspace_page
    if page == "Applications":
        st.markdown('<div class="section-heading">Your application pipeline</div>', unsafe_allow_html=True)
        create_application_form()
        applications = load_data("/applications", "Applications could not be loaded")
        if applications is not None:
            render_applications(applications)
        return
    if page == "Skills":
        st.markdown('<div class="section-heading">Skills & career timeline</div>', unsafe_allow_html=True)
        skill_tab, timeline_tab = st.tabs(["Skills", "Career timeline"])
        with skill_tab:
            with st.expander("＋ Add a skill"):
                with st.form("new_skill"):
                    skill_name = st.text_input("Skill name", placeholder="e.g. Stakeholder management")
                    proficiency = st.slider("Your proficiency", 1, 5, 3)
                    submitted = st.form_submit_button("Save skill")
                if submitted:
                    try:
                        api_request("POST", "/skills", {"skill_name": skill_name, "proficiency": proficiency})
                        st.success("Skill saved to your account.")
                        st.rerun()
                    except (RuntimeError, ValueError) as exc:
                        st.error(str(exc))
            skills = load_data("/skills", "Skills could not be loaded")
            if skills is not None:
                st.dataframe(skills, use_container_width=True, hide_index=True) if skills else st.info("No skills recorded yet.")
        with timeline_tab:
            with st.expander("＋ Add a milestone"):
                with st.form("new_event"):
                    event_type = st.selectbox("Milestone type", ["Education", "Role", "Project", "Certification", "Achievement", "Other"])
                    event_title = st.text_input("Title")
                    event_description = st.text_area("Details (optional)")
                    event_date = st.date_input("Date", value=date.today())
                    submitted = st.form_submit_button("Save milestone")
                if submitted:
                    try:
                        api_request("POST", "/career-timeline", {"type": event_type, "title": event_title, "description": event_description or None, "date": event_date.isoformat()})
                        st.success("Milestone saved to your account.")
                        st.rerun()
                    except (RuntimeError, ValueError) as exc:
                        st.error(str(exc))
            events = load_data("/career-timeline", "Timeline could not be loaded")
            if events is not None:
                st.dataframe(events, use_container_width=True, hide_index=True) if events else st.info("Your timeline is ready for education, projects, and milestones.")
        return

    summary = load_data("/career-summary", "Career summary could not be loaded") or {}
    applications = load_data("/applications", "Applications could not be loaded") or []
    skills = load_data("/skills", "Skills could not be loaded") or []
    events = load_data("/career-timeline", "Timeline could not be loaded") or []
    dna = load_data("/career-dna", "Career DNA could not be loaded") or {}

    if page == "Dashboard":
        dashboard_home(summary, applications, skills, dna, events)
    elif page == "Explore Careers":
        st.markdown('<div class="section-heading">Explore your next direction</div>', unsafe_allow_html=True)
        st.markdown('<div class="surface"><div class="surface-title">Start with what you know</div><p>CareerOS currently connects your saved applications, skills, and career timeline. A live job discovery feed is not available in the existing API yet.</p></div>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        c1.metric("Skills to bring forward", len(skills))
        c2.metric("Roles already in view", len(applications))
        st.info("Add target roles in Applications and record your strengths in Skills to build a useful starting point for career exploration.")
    elif page == "Analyze Résumé":
        st.markdown('<div class="section-heading">Résumé & role intelligence</div>', unsafe_allow_html=True)
        st.markdown('<div class="surface"><div class="surface-title">A transparent prototype is available</div><p>The existing résumé comparison remains in its preserved prototype. It uses phrase matching and optional OCR and is not yet connected to this authenticated workspace.</p></div>', unsafe_allow_html=True)
        st.markdown("- Upload a résumé PDF or TXT file in the prototype.\n- Paste a target job description.\n- Review detected skill evidence and inspect extracted text when a match looks wrong.")
        st.link_button("Open résumé comparison prototype source", "https://github.com/c00mbs/careeros-api/blob/main/prototype_ui.py")
        st.caption("Keyword overlap is not a hiring score. Results need human review.")
    elif page == "Career Plan":
        st.markdown('<div class="section-heading">Your career plan</div>', unsafe_allow_html=True)
        st.caption("A practical starting plan shaped by the records in your account.")
        for index, (title, detail) in enumerate(career_plan(applications, skills, events), 1):
            st.markdown(f'<div class="surface"><span class="landing-kicker">STEP {index}</span><div class="surface-title">{title}</div><span class="small-note">{detail}</span></div>', unsafe_allow_html=True)
    elif page == "Career DNA":
        st.markdown('<div class="section-heading">Your Career DNA</div>', unsafe_allow_html=True)
        st.caption("Exploratory, fixed-rule indicators computed from your saved skills. This is not a validated assessment or a hiring prediction.")
        if dna:
            st.bar_chart({"Profile": {str(key).replace("_", " ").title(): value for key, value in dna.items()}}, color=GOLD, height=360)
        else:
            st.info("Add skills in your profile to start building your Career DNA view.")
    else:
        st.markdown('<div class="section-heading">Insights from your career profile</div>', unsafe_allow_html=True)
        active = sum(1 for item in applications if item.get("status") in {"Applied", "Interviewing", "Offer"})
        advanced_skills = sum(1 for item in skills if int(item.get("proficiency", 0) or 0) >= 4)
        actions = career_plan(applications, skills, events)
        c1, c2, c3 = st.columns(3)
        c1.metric("Active opportunities", active)
        c2.metric("Career milestones", len(events))
        c3.metric("Self-rated strengths", advanced_skills)
        l, r = st.columns(2)
        with l:
            st.markdown('<div class="section-heading">What your profile shows</div>', unsafe_allow_html=True)
            st.write(f"You have {len(applications)} role(s) in your pipeline, {len(skills)} saved skill(s), and {len(events)} career milestone(s).")
            st.caption("These figures come from your authenticated CareerOS account.")
        with r:
            st.markdown('<div class="section-heading">One next step</div>', unsafe_allow_html=True)
            title, detail = actions[0]
            st.markdown(f'<div class="quote-card"><div class="landing-kicker">A SUGGESTED FOCUS</div><div class="surface-title">{title}</div><p>{detail}</p></div>', unsafe_allow_html=True)
    st.markdown('<div class="surface" style="text-align:center;color:#e8c780;font-family:Playfair Display,serif">Keep becoming.　 CareerOS</div>', unsafe_allow_html=True)


def main() -> None:
    if not st.session_state.token:
        landing_page()
    else:
        render_workspace()


if __name__ == "__main__":
    main()
