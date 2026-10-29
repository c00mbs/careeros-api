"""Session-only résumé text extraction and evidence-based skill matching."""

from __future__ import annotations

import re
from collections.abc import Iterable
from difflib import SequenceMatcher

from pypdf import PdfReader


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Data analysis": ("data analysis", "analyzed data", "analysed data", "data analytics", "analytical"),
    "Project management": ("project management", "managed projects", "project manager"),
    "Operations": ("operations", "operational"),
    "Customer service": ("customer service", "customer support", "client support"),
    "Communication": ("communication", "presented findings", "stakeholder communication"),
    "Leadership": ("leadership", "led a team", "team lead", "managed a team"),
    "Forecasting": ("forecasting", "forecasted"),
    "Research": ("research", "market research"),
    "Training": ("training", "trained staff", "employee onboarding"),
    "Analytics": ("analytics", "analysis", "analytical"),
    "Data visualization": ("data visualization", "dashboarding", "visualization"),
    "Problem solving": ("problem solving", "problem-solving", "troubleshooting"),
    "Business analysis": ("business analysis", "business analyst", "requirements gathering"),
    "Stakeholder management": ("stakeholder management", "stakeholder communication", "cross-functional"),
}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _matches(sentence: str, alias: str) -> bool:
    sentence_norm, alias_norm = normalize_text(sentence), normalize_text(alias)
    if not alias_norm:
        return False
    if re.search(rf"(?<!\w){re.escape(alias_norm)}(?!\w)", sentence_norm):
        return True
    if len(alias_norm) >= 5 and SequenceMatcher(None, alias_norm, sentence_norm).ratio() >= 0.82:
        return True
    return False


def find_skill_evidence(text: str, skills: Iterable[str] | None = None) -> dict[str, str]:
    """Find one sentence of supporting text for each recognized skill."""
    if not text.strip():
        return {}
    evidence: dict[str, str] = {}
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    for skill in skills or SKILL_ALIASES:
        aliases = SKILL_ALIASES.get(skill, (skill,))
        for sentence in sentences:
            if sentence.strip() and any(_matches(sentence, alias) for alias in aliases):
                evidence[skill] = re.sub(r"\s+", " ", sentence).strip()[:280]
                break
    return evidence


def rank_jobs_by_resume(jobs: Iterable[dict], resume_skills: Iterable[str]) -> list[dict]:
    """Rank one fetched page of jobs by recognized résumé skills in listing text.

    Matching is local and uses only the title, company, and provider excerpt;
    résumé text is never sent to the job provider. This is an evidence hint,
    not a hiring or suitability score.
    """
    skills = tuple(resume_skills)
    ranked: list[dict] = []
    for job in jobs:
        listing_text = " ".join(
            str(job.get(field) or "")
            for field in ("title", "company", "excerpt", "employment_type")
        )
        matched = tuple(find_skill_evidence(listing_text, skills))
        ranked.append({**job, "resume_matched_skills": matched, "resume_match_count": len(matched)})
    return sorted(ranked, key=lambda job: job["resume_match_count"], reverse=True)


def extract_resume_text(uploaded_file) -> str:
    """Read a PDF's selectable text or decode a TXT upload; never persist it."""
    filename = uploaded_file.name.lower()
    if filename.endswith(".pdf"):
        uploaded_file.seek(0)
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages).strip()
    return uploaded_file.getvalue().decode("utf-8", errors="replace").strip()

