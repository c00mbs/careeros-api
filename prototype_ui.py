"""Early CareerOS resume-to-role comparison prototype."""
from __future__ import annotations

import re
from collections.abc import Iterable

import streamlit as st
from pypdf import PdfReader

SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Data analysis": ("data analysis", "data analytics", "analytical"),
    "Project management": ("project management", "project manager"),
    "Operations": ("operations", "operational"),
    "Customer service": ("customer service", "customer support"),
    "Communication": ("communication", "stakeholder communication"),
    "Leadership": ("leadership", "team lead", "managed a team"),
    "Forecasting": ("forecasting", "forecasted"),
    "Research": ("research", "market research"),
    "Training": ("training", "trained staff"),
    "Analytics": ("analytics", "analysis"),
    "Data visualization": ("data visualization", "dashboarding"),
    "Problem solving": ("problem solving", "problem-solving"),
    "Business analysis": ("business analysis", "business analyst"),
    "Stakeholder management": ("stakeholder management", "cross-functional"),
}


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", value.lower())).strip()


def find_skill_evidence(text: str, skills: Iterable[str] | None = None) -> dict[str, str]:
    """Find literal skill phrases and return the sentence that supports each match."""
    if not text or not text.strip():
        return {}
    names = list(skills) if skills is not None else list(SKILL_ALIASES)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    evidence: dict[str, str] = {}
    for skill in names:
        aliases = SKILL_ALIASES.get(skill, (skill.lower(),))
        for sentence in sentences:
            normalized = normalize_text(sentence)
            match = next((alias for alias in aliases if normalize_text(alias) in normalized), None)
            if match:
                evidence[skill] = re.sub(r"\s+", " ", sentence).strip()[:280]
                break
    return evidence


def extract_pdf_text(uploaded_file) -> str:
    uploaded_file.seek(0)
    reader = PdfReader(uploaded_file)
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def render_comparison(resume_skills: set[str], role_skills: set[str]) -> None:
    found = sorted(resume_skills & role_skills)
    missing = sorted(role_skills - resume_skills)
    left, right = st.columns(2)
    with left:
        st.markdown("**Evidence found in both**")
        st.write(", ".join(found) if found else "No overlap detected yet.")
    with right:
        st.markdown("**Role skills not found in resume text**")
        st.write(", ".join(missing) if missing else "No listed role skills are missing from the text.")
    st.caption("A missing phrase is not proof that you lack the skill. Review the source text and every match.")


st.set_page_config(page_title="CareerOS | Role comparison", page_icon="🧭", layout="wide")
st.title("CareerOS")
st.caption("An early, evidence-based resume-to-role comparison prototype.")
st.info("Files are processed in this session only. This prototype does not save your resume or profile data.")

resume_file = st.file_uploader("1. Upload your resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = ""
if resume_file is not None:
    try:
        if resume_file.name.lower().endswith(".pdf"):
            resume_text = extract_pdf_text(resume_file)
        else:
            resume_text = resume_file.getvalue().decode("utf-8", errors="replace")
    except Exception as exc:
        st.error(f"Could not read this file: {exc}")

role_description = st.text_area(
    "2. Paste the target role description",
    height=190,
    placeholder="Paste the job description here.",
)

if resume_file is not None and not resume_text:
    st.warning("No readable text was found. Try a text-based PDF or TXT file.")

if resume_text:
    st.subheader("3. Review resume skills")
    resume_evidence = find_skill_evidence(resume_text)
    selected_resume: set[str] = set()
    if resume_evidence:
        columns = st.columns(2)
        for index, (skill, evidence) in enumerate(resume_evidence.items()):
            with columns[index % 2]:
                if st.checkbox(skill, value=True, key=f"resume_{skill}"):
                    selected_resume.add(skill)
                st.caption(f"Evidence: {evidence}")
    else:
        st.warning("No phrases from the current skill list were detected.")

    if role_description.strip():
        st.subheader("4. Review role skills")
        role_evidence = find_skill_evidence(role_description)
        selected_role: set[str] = set()
        if role_evidence:
            columns = st.columns(2)
            for index, (skill, evidence) in enumerate(role_evidence.items()):
                with columns[index % 2]:
                    if st.checkbox(skill, value=True, key=f"role_{skill}"):
                        selected_role.add(skill)
                    st.caption(f"Evidence: {evidence}")
            st.subheader("Comparison")
            render_comparison(selected_resume, selected_role)
        else:
            st.warning("No phrases from the current skill list were detected in the role description.")

    with st.expander("Show extracted resume text"):
        st.text(resume_text[:12000])

st.divider()
st.caption("Prototype only • Phrase matching can miss relevant experience or misread context. It does not predict hiring outcomes.")
