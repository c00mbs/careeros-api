"""Become landing page and CareerOS workspace backed by the authenticated API."""

from __future__ import annotations

import os
from html import escape
from collections import Counter
from datetime import date
from typing import Any
from urllib.parse import urlencode

import httpx
import streamlit as st
from resume_analysis import extract_resume_text, find_skill_evidence, rank_jobs_by_resume

API_URL = os.getenv("CAREEROS_API_URL", "http://127.0.0.1:8000").rstrip("/")
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
.career-table-wrap{overflow-x:auto;border:1px solid var(--line);border-radius:12px;margin:.5rem 0 1rem}
.career-table{width:100%;border-collapse:collapse;background:#101111;font-size:.92rem}
.career-table th{text-align:left;color:#e6c47f;background:#171715;font-weight:600;white-space:nowrap}
.career-table th,.career-table td{padding:.75rem .9rem;border-bottom:1px solid rgba(217,173,98,.12)}
.career-table td{color:#e8e2d7}.career-table tr:last-child td{border-bottom:0}
.chart-title{color:#d4c7af;font-size:.82rem;margin:.6rem 0}
.chart-row{display:grid;grid-template-columns:minmax(90px,1fr) minmax(90px,2fr) 36px;align-items:center;gap:.65rem;margin:.55rem 0}
.chart-label{color:#e2dbcf;font-size:.83rem}.chart-track{height:9px;border-radius:99px;background:#28251e;overflow:hidden}
.chart-fill{height:100%;border-radius:99px;background:linear-gradient(90deg,#a87936,#f0cb80);min-width:0}
.chart-value{color:#e8c780;text-align:right;font-size:.82rem;font-variant-numeric:tabular-nums}
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


def render_data_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> None:
    """Render records without Streamlit's pandas-backed dataframe machinery."""
    headings = "".join(f"<th>{escape(label)}</th>" for _, label in columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row.get(key) if row.get(key) is not None else '—'))}</td>" for key, _ in columns) + "</tr>"
        for row in rows
    )
    st.markdown(f'<div class="career-table-wrap"><table class="career-table"><thead><tr>{headings}</tr></thead><tbody>{body}</tbody></table></div>', unsafe_allow_html=True)


def render_bar_chart(title: str, values: dict[str, int | float]) -> None:
    """Render compact horizontal bars without importing pandas or chart DLLs."""
    maximum = max((max(0.0, float(value)) for value in values.values()), default=0.0)
    rows = []
    for label, value in values.items():
        numeric = max(0.0, float(value))
        width = numeric / maximum * 100 if maximum else 0
        shown = f"{numeric:g}"
        rows.append(
            f'<div class="chart-row"><div class="chart-label">{escape(str(label))}</div>'
            f'<div class="chart-track"><div class="chart-fill" style="width:{width:.2f}%"></div></div>'
            f'<div class="chart-value">{escape(shown)}</div></div>'
        )
    st.markdown(f'<div class="chart-title">{escape(title)}</div>{"".join(rows)}', unsafe_allow_html=True)


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
        render_data_table(applications, [("company", "Company"), ("job_title", "Role"), ("status", "Status"), ("applied_date", "Applied")])
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
        render_bar_chart("Roles by stage", {status: counts[status] for status in statuses})
        if applications:
            render_data_table(applications[:5], [("company", "Company"), ("job_title", "Role"), ("status", "Status")])
        else:
            st.caption("Your account has no saved roles yet. Add one to begin building your pipeline.")
    with right:
        st.markdown('<div class="section-heading">Skill intelligence</div>', unsafe_allow_html=True)
        if skills:
            ordered = sorted(skills, key=lambda item: int(item.get("proficiency", 0) or 0), reverse=True)[:6]
            chart = {str(item.get("skill_name", "Skill")): int(item.get("proficiency", 0) or 0) for item in ordered}
            render_bar_chart("Self-rated proficiency (1–5)", chart)
            st.caption(f"{active_skills} skill(s) are currently self-rated 4 or higher.")
        else:
            st.info("Add skills to start your profile.")
        if dna:
            st.caption("Career DNA is an exploratory profile based on your saved skills.")
    st.markdown('<div class="surface" style="text-align:center;color:#e8c780;font-family:Playfair Display,serif;font-size:1.2rem">Your career is the greatest project you’ll ever lead.</div>', unsafe_allow_html=True)


def resume_analysis_page() -> None:
    st.markdown('<div class="section-heading">Résumé & role intelligence</div>', unsafe_allow_html=True)
    st.markdown('<div class="surface"><div class="surface-title">See where your experience meets a role</div><p>Upload a résumé and paste a job description. CareerOS highlights matching skills and the text that supports each one.</p><p class="small-note">Your file is read in this session only. It is not uploaded to the API or saved to your account.</p></div>', unsafe_allow_html=True)
    resume_file = st.file_uploader("Upload your résumé", type=["pdf", "txt"], key="career_resume_upload")
    role_description = st.text_area("Paste the target job description", height=190, key="career_role_description")
    if not resume_file:
        st.info("Choose a PDF with selectable text or a plain text résumé to begin.")
        return

    try:
        resume_text = extract_resume_text(resume_file)
    except Exception as exc:
        st.error(f"CareerOS could not read that file: {exc}")
        return
    if not resume_text:
        st.warning("No selectable text was found. Scanned image-only PDFs are not supported in this workspace yet. Try an exported text PDF or TXT file.")
        return

    st.session_state["resume_match_text"] = resume_text

    resume_evidence = find_skill_evidence(resume_text)
    if not resume_evidence:
        st.warning("No skills from the current CareerOS skill list were found. You can still inspect the extracted text below.")
    else:
        st.markdown('<div class="section-heading">Review résumé evidence</div>', unsafe_allow_html=True)
        st.caption("Select the skills you want to compare. Each item shows the sentence that triggered the match.")
    resume_selected: set[str] = set()
    columns = st.columns(2)
    for index, (skill, evidence) in enumerate(resume_evidence.items()):
        with columns[index % 2]:
            if st.checkbox(skill, value=True, key=f"resume_evidence_{skill}"):
                resume_selected.add(skill)
            st.caption(evidence)

    if role_description.strip():
        role_evidence = find_skill_evidence(role_description)
        st.markdown('<div class="section-heading">Review role requirements</div>', unsafe_allow_html=True)
        if not role_evidence:
            st.warning("No skills from the current CareerOS skill list were detected in this description.")
        role_selected: set[str] = set()
        role_columns = st.columns(2)
        for index, (skill, evidence) in enumerate(role_evidence.items()):
            with role_columns[index % 2]:
                if st.checkbox(skill, value=True, key=f"role_evidence_{skill}"):
                    role_selected.add(skill)
                st.caption(evidence)
        st.markdown('<div class="section-heading">Role comparison</div>', unsafe_allow_html=True)
        st.caption("‘Not found’ means no supporting phrase was detected in the résumé text. It does not mean you lack the skill. This is not a hiring score.")
        found, not_detected = st.columns(2)
        with found:
            st.markdown('<div class="surface-title">Evidence found in both</div>', unsafe_allow_html=True)
            st.write(", ".join(sorted(resume_selected & role_selected)) or "No overlap detected yet.")
        with not_detected:
            st.markdown('<div class="surface-title">Role skills not detected</div>', unsafe_allow_html=True)
            st.write(", ".join(sorted(role_selected - resume_selected)) or "All selected role skills have matching résumé evidence.")

    with st.expander("Show extracted résumé text"):
        st.text(resume_text[:12000])


def format_job_salary(job: dict[str, Any]) -> str:
    low, high = job.get("min_salary"), job.get("max_salary")
    if low is None and high is None:
        return "Compensation not listed"
    currency = str(job.get("currency") or "")
    period = str(job.get("salary_period") or "annual").replace("fortnightly", "per two weeks")
    if low is not None and high is not None:
        amount = f"{low:,.0f}–{high:,.0f}"
    else:
        amount = f"{(low if low is not None else high):,.0f}+"
    return f"{currency} {amount} / {period}".strip()


def explore_careers_page() -> None:
    st.markdown('<div class="section-heading">Find your next opportunity</div>', unsafe_allow_html=True)
    st.markdown('<div class="surface"><div class="surface-title">Remote roles from across the market</div><p>Search current openings by role, location, seniority, and employment type. Listings are sourced from Himalayas, refreshed daily, and link to the original posting and application page.</p><span class="small-note">Results cover remote roles only; availability may change before each listing expires.</span></div>', unsafe_allow_html=True)

    st.markdown("### Match roles to your résumé")
    st.caption("Upload a résumé here, or use one you already analyzed. CareerOS compares recognized skills with each listing on your device; your résumé is not sent to the job provider or saved to your account.")
    match_file = st.file_uploader("Résumé for job matching", type=["pdf", "txt"], key="career_match_resume_upload")
    if match_file:
        try:
            st.session_state["resume_match_text"] = extract_resume_text(match_file)
        except Exception as exc:
            st.error(f"CareerOS could not read that file: {exc}")
    match_text = str(st.session_state.get("resume_match_text", ""))
    match_skills = find_skill_evidence(match_text) if match_text else {}
    if match_text and match_skills:
        st.success(f"Résumé ready · {len(match_skills)} recognized skills available for matching.")
    elif match_text:
        st.warning("CareerOS could not detect any skills from its current skill list in this résumé. Try another résumé or add role keywords to search.")
    else:
        st.info("Upload a PDF with selectable text or a TXT résumé to prioritize roles by your experience.")

    filters = st.session_state.get("job_search_filters", {"q": "", "country": "Any location", "seniority": "Any level", "employment": "Any type", "sort": "Most recent"})
    with st.form("remote_job_search"):
        query = st.text_input("Role or keywords", value=filters["q"], placeholder="e.g. Project Manager, data analyst")
        col_location, col_seniority, col_type, col_sort = st.columns(4)
        with col_location:
            country = st.selectbox("Location", ["Any location", "United States", "Canada", "United Kingdom", "Australia", "India"], index=["Any location", "United States", "Canada", "United Kingdom", "Australia", "India"].index(filters["country"]))
        with col_seniority:
            seniority = st.selectbox("Seniority", ["Any level", "Entry-level", "Mid-level", "Senior", "Manager", "Director", "Executive"], index=["Any level", "Entry-level", "Mid-level", "Senior", "Manager", "Director", "Executive"].index(filters["seniority"]))
        with col_type:
            employment = st.selectbox("Employment", ["Any type", "Full Time", "Part Time", "Contractor", "Temporary", "Intern"], index=["Any type", "Full Time", "Part Time", "Contractor", "Temporary", "Intern"].index(filters["employment"]))
        with col_sort:
            sort_label = st.selectbox("Sort by", ["Most recent", "Best match", "Highest salary", "Lowest salary"], index=["Most recent", "Best match", "Highest salary", "Lowest salary"].index(filters["sort"]))
        search_clicked = st.form_submit_button("Search remote roles", use_container_width=True)

    if search_clicked:
        st.session_state.job_search_filters = {"q": query.strip(), "country": country, "seniority": seniority, "employment": employment, "sort": sort_label}
        st.session_state.job_search_page = 1
        filters = st.session_state.job_search_filters

    params: dict[str, str] = {"page": str(st.session_state.get("job_search_page", 1))}
    if filters["q"]:
        params["q"] = filters["q"]
    country_codes = {"United States": "US", "Canada": "CA", "United Kingdom": "GB", "Australia": "AU", "India": "IN"}
    if filters["country"] in country_codes:
        params["country"] = country_codes[filters["country"]]
    if filters["seniority"] != "Any level":
        params["seniority"] = filters["seniority"]
    if filters["employment"] != "Any type":
        params["employment_type"] = filters["employment"]
    params["sort"] = {"Most recent": "recent", "Best match": "relevant", "Highest salary": "salaryDesc", "Lowest salary": "salaryAsc"}[filters["sort"]]

    results = load_data(f"/jobs/search?{urlencode(params)}", "Job listings could not be loaded")
    if results is None:
        st.info("Search again in a moment. Your saved applications and profile data are unchanged.")
        return

    st.caption(f"{results.get('total_count', 0):,} matching remote role(s) · refreshed {str(results.get('refreshed_at') or 'date unavailable')[:10]} · Source: Himalayas")
    applications = load_data("/applications", "Your saved applications could not be loaded") or []
    saved_roles = {(str(item.get("company", "")).casefold(), str(item.get("job_title", "")).casefold()) for item in applications}
    jobs = results.get("jobs", [])
    if match_skills:
        st.session_state.setdefault("prioritize_resume_matches", True)
        prioritize_matches = st.checkbox("Prioritize roles that mention my résumé skills", key="prioritize_resume_matches")
        if prioritize_matches:
            jobs = rank_jobs_by_resume(jobs, match_skills.keys())
            overlap_count = sum(bool(job["resume_match_count"]) for job in jobs)
            st.caption(f"Ranked within these {len(jobs)} listings · {overlap_count} mention at least one recognized résumé skill. Matches use listing text and may miss skills not shown in the excerpt.")
    if not jobs:
        st.info("No remote roles matched those filters. Try a broader title, another location, or Any level.")
    for job in jobs:
        with st.container(border=True):
            top, action = st.columns([4, 1.25], vertical_alignment="center")
            with top:
                st.markdown(f"### {escape(str(job.get('title') or 'Untitled role'))}")
                st.markdown(f"**{escape(str(job.get('company') or 'Company not listed'))}**　·　{escape(str(job.get('employment_type') or 'Remote'))}")
            with action:
                st.link_button("Apply on Himalayas", str(job["apply_url"]), use_container_width=True)
            details = [format_job_salary(job)]
            if job.get("locations"):
                details.append("Location: " + ", ".join(str(item) for item in job["locations"]))
            if job.get("seniority"):
                details.append(" · ".join(str(item) for item in job["seniority"]))
            st.caption("　|　".join(details))
            if "resume_match_count" in job:
                if job["resume_matched_skills"]:
                    st.caption("Résumé skills mentioned: " + ", ".join(job["resume_matched_skills"]))
                else:
                    st.caption("No recognized résumé skills found in this listing excerpt.")
            st.write(str(job.get("excerpt") or "Open the listing for role details."))
            company_key, role_key = str(job.get("company") or "").casefold(), str(job.get("title") or "").casefold()
            if (company_key, role_key) in saved_roles:
                st.caption("Already in your Applications pipeline.")
            elif st.button("Save to Applications", key=f"save_job_{job['id']}"):
                try:
                    api_request("POST", "/applications", {"company": job.get("company") or "Company not listed", "job_title": job.get("title") or "Untitled role", "status": "Saved"})
                    st.success("Saved to your Applications pipeline.")
                    st.rerun()
                except (RuntimeError, ValueError) as exc:
                    st.error(str(exc))
            st.markdown(f'[View original listing · Himalayas]({job["source_url"]})', unsafe_allow_html=False)

    previous, page_label, next_page = st.columns([1, 2, 1])
    current_page = int(results.get("page", 1))
    with previous:
        if current_page > 1 and st.button("← Previous", use_container_width=True):
            st.session_state.job_search_page = current_page - 1
            st.rerun()
    with page_label:
        st.caption(f"Page {current_page} · listings update daily")
    with next_page:
        if jobs and st.button("Next →", use_container_width=True):
            st.session_state.job_search_page = current_page + 1
            st.rerun()


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
    if page == "Analyze Résumé":
        resume_analysis_page()
        return
    if page == "Applications":
        st.markdown('<div class="section-heading">Your application pipeline</div>', unsafe_allow_html=True)
        create_application_form()
        applications = load_data("/applications", "Applications could not be loaded")
        if applications is not None:
            render_applications(applications)
        return
    if page == "Skills":
        st.markdown('<div class="section-heading">Your strengths, made visible</div>', unsafe_allow_html=True)
        st.markdown('<p class="small-note">Build a grounded picture of the skills you bring and the experiences behind them.</p>', unsafe_allow_html=True)
        skills = load_data("/skills", "Skills could not be loaded")
        events = load_data("/career-timeline", "Timeline could not be loaded")
        if skills is None or events is None:
            return
        advanced_skills = sum(1 for item in skills if int(item.get("proficiency", 0) or 0) >= 4)
        average_rating = sum(int(item.get("proficiency", 0) or 0) for item in skills) / len(skills) if skills else 0
        metrics = st.columns(4)
        metrics[0].metric("Skills recorded", len(skills))
        metrics[1].metric("Rated 4–5", advanced_skills)
        metrics[2].metric("Average rating", f"{average_rating:.1f} / 5" if skills else "—")
        metrics[3].metric("Career milestones", len(events))
        skill_tab, timeline_tab = st.tabs(["Skills", "Career timeline"])
        with skill_tab:
            st.markdown('<div class="section-heading">Skill intelligence</div>', unsafe_allow_html=True)
            if skills:
                ordered_skills = sorted(skills, key=lambda item: int(item.get("proficiency", 0) or 0), reverse=True)
                render_bar_chart("Self-rated proficiency · 1 to 5", {str(item.get("skill_name", "Skill")): int(item.get("proficiency", 0) or 0) for item in ordered_skills})
            else:
                st.markdown('<div class="surface"><div class="surface-title">Start with the strengths you use</div><p>Add skills you have practiced in work, study, or personal projects. Rate your current confidence to make the profile more useful.</p><span class="small-note">Your ratings are personal reference points, not an assessment.</span></div>', unsafe_allow_html=True)
            with st.expander("＋ Add a skill", expanded=not skills):
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
            if skills:
                st.markdown('<div class="section-heading">Your recorded skills</div>', unsafe_allow_html=True)
                render_data_table(ordered_skills, [("skill_name", "Skill"), ("proficiency", "Self-rating · 1 to 5")])
        with timeline_tab:
            st.markdown('<div class="section-heading">Career timeline</div>', unsafe_allow_html=True)
            st.caption("Capture the roles, projects, education, and milestones that shape your experience.")
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
            if events:
                render_data_table(events, [("type", "Type"), ("title", "Milestone"), ("description", "Details"), ("date", "Date")])
            else:
                st.markdown('<div class="surface"><div class="surface-title">Your story starts here</div><p>Add a role, project, course, or achievement. Your timeline helps connect what you have done with where you want to go.</p></div>', unsafe_allow_html=True)
        return

    summary = load_data("/career-summary", "Career summary could not be loaded") or {}
    applications = load_data("/applications", "Applications could not be loaded") or []
    skills = load_data("/skills", "Skills could not be loaded") or []
    events = load_data("/career-timeline", "Timeline could not be loaded") or []
    dna = load_data("/career-dna", "Career DNA could not be loaded") or {}

    if page == "Dashboard":
        dashboard_home(summary, applications, skills, dna, events)
    elif page == "Explore Careers":
        explore_careers_page()
    elif page == "Career Plan":
        st.markdown('<div class="section-heading">Your career plan</div>', unsafe_allow_html=True)
        st.caption("A practical starting plan shaped by the records in your account.")
        for index, (title, detail) in enumerate(career_plan(applications, skills, events), 1):
            st.markdown(f'<div class="surface"><span class="landing-kicker">STEP {index}</span><div class="surface-title">{title}</div><span class="small-note">{detail}</span></div>', unsafe_allow_html=True)
    elif page == "Career DNA":
        st.markdown('<div class="section-heading">Your Career DNA</div>', unsafe_allow_html=True)
        st.caption("Exploratory, fixed-rule indicators computed from your saved skills. This is not a validated assessment or a hiring prediction.")
        if dna:
            render_bar_chart("Career DNA · exploratory indicators", {str(key).replace("_", " ").title(): value for key, value in dna.items()})
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



