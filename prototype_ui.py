"""CareerOS MVP: a transparent resume-to-role comparison prototype."""

git add .
git commit -m "Refactor analysis endpoints and update ATS match UI styling to emerald/neutral tones"
git push origin main

st.markdown("""
    <style>
    .match-badge {
        color: #10b981;
        font-weight: 600;
        background-color: rgba(16, 185, 129, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
    }
    .missing-badge {
        color: #f59e0b;
        font-weight: 600;
        background-color: rgba(245, 158, 11, 0.1);
        padding: 4px 8px;
        border-radius: 4px;
    }
    </style>
""", unsafe_allow_html=True)

from __future__ import annotations

import re
from collections.abc import Iterable
from difflib import SequenceMatcher

import streamlit as st
from pypdf import PdfReader

# Optional OCR helper
try:
    from pdf2image import convert_from_bytes
except Exception:
    convert_from_bytes = None

try:
    import pytesseract
except Exception:
    pytesseract = None


SKILL_ALIASES: dict[str, tuple[str, ...]] = {
    "Python": ("python",),
    "SQL": ("sql", "structured query language"),
    "Excel": ("excel", "microsoft excel"),
    "Power BI": ("power bi", "powerbi"),
    "Tableau": ("tableau",),
    "Data analysis": (
        "data analysis",
        "analyzed data",
        "analysed data",
        "data analytics",
        "analytical",
    ),
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
    "Stakeholder management": (
        "stakeholder management",
        "stakeholder communication",
        "cross-functional",
    ),
}


def normalize_text(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\s]", " ", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def sentence_contains_alias(sentence: str, alias: str) -> bool:
    sentence_norm = normalize_text(sentence)
    alias_norm = normalize_text(alias)

    if not alias_norm:
        return False

    if alias_norm in sentence_norm:
        return True

    # For multiword aliases, match on important tokens
    if " " in alias_norm:
        tokens = [t for t in alias_norm.split() if len(t) > 2]
        if tokens and any(t in sentence_norm for t in tokens):
            return True

    return False


def fuzzy_alias_match(sentence: str, alias: str, threshold: float = 0.72) -> bool:
    sentence_norm = normalize_text(sentence)
    alias_norm = normalize_text(alias)

    if not alias_norm:
        return False

    if alias_norm in sentence_norm:
        return True

    # Global similarity
    similarity = SequenceMatcher(None, alias_norm, sentence_norm).ratio()
    if similarity >= threshold:
        return True

    # Token-level similarity for multi-word aliases
    if " " in alias_norm:
        alias_tokens = [t for t in alias_norm.split() if len(t) > 2]
        sentence_tokens = sentence_norm.split()
        for token in alias_tokens:
            best = 0.0
            for other in sentence_tokens:
                r = SequenceMatcher(None, token, other).ratio()
                if r > best:
                    best = r
            if best >= threshold:
                return True

    return False


def find_skill_evidence(text: str, skills: Iterable[str] | None = None) -> dict[str, str]:
    """Return one concise snippet per skill found by exact or fuzzy alias matching."""
    if not text or not text.strip():
        return {}

    skill_names = list(skills) if skills is not None else list(SKILL_ALIASES.keys())
    # Split into sentences (keeps newline-separated blocks too)
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text)
    evidence: dict[str, str] = {}

    for skill in skill_names:
        aliases = SKILL_ALIASES.get(skill, (skill.lower(),))
        matched_sentence = None
        matched_alias = None

        for sentence in sentences:
            if not sentence.strip():
                continue
            for alias in aliases:
                if sentence_contains_alias(sentence, alias) or fuzzy_alias_match(sentence, alias):
                    matched_sentence = sentence
                    matched_alias = alias
                    break
            if matched_sentence:
                break

        if not matched_sentence:
            continue

        snippet = re.sub(r"\s+", " ", matched_sentence).strip()
        # Highlight the matched alias in the snippet while preserving original case
        if matched_alias:
            try:
                m = re.search(re.escape(matched_alias), snippet, flags=re.IGNORECASE)
                if m:
                    snippet = snippet[: m.start()] + "**" + snippet[m.start() : m.end()] + "**" + snippet[m.end() :]
            except re.error:
                # fallback: no highlighting
                pass

        evidence[skill] = snippet[:280]

    return evidence


def extract_pdf_text(pdf_file) -> str:
    """Extract text from a PDF and fallback to OCR if needed."""
    # First try selectable text via pypdf
    try:
        pdf_file.seek(0)
        reader = PdfReader(pdf_file)
        pages = [page.extract_text() or "" for page in reader.pages]
        text = "\n".join(pages).strip()
        if text:
            return text
    except Exception:
        # fall through to OCR fallback if available
        pass

    # Fallback: render pages to images and OCR
    if convert_from_bytes is not None and pytesseract is not None:
        try:
            pdf_file.seek(0)
            images = convert_from_bytes(pdf_file.getvalue())
            ocr_pages = [pytesseract.image_to_string(img) for img in images]
            text = "\n".join(ocr_pages).strip()
            if text:
                return text
        except Exception:
            pass

    return ""


def render_comparison(resume_skills: set[str], role_skills: set[str]) -> None:
    supported = sorted(resume_skills & role_skills)
    not_found = sorted(role_skills - resume_skills)

    st.subheader("Role comparison")
    st.caption("‘Not found’ means the skill was not detected in the supplied text. It does not mean you lack that skill.")
    left, right = st.columns(2)

    with left:
        st.markdown("**Evidence found in both**")
        st.write(", ".join(supported) if supported else "No overlap detected yet.")

    with right:
        st.markdown("**Role skills not found in the resume text**")
        st.write(", ".join(not_found) if not_found else "No listed role skills are missing from the text.")


# Streamlit UI
st.set_page_config(page_title="CareerOS | Career profile", page_icon="🧭", layout="wide")
st.title("CareerOS")
st.caption("Turn experience into a clearer, evidence-backed view of your skills.")

with st.expander("About this early prototype", expanded=False):
    st.write(
        "This version uses transparent phrase matching with light fuzzy matching and an OCR fallback for scanned PDFs. "
        "It does not rank your worth, predict hiring outcomes, or send your resume to an AI service. Review every detected skill before using the comparison."
    )

st.info("Your resume is processed in this session only. This prototype does not save uploaded files or profile data.")

resume_file = st.file_uploader("1. Upload your resume (PDF or TXT)", type=["pdf", "txt"])
resume_text = ""

if resume_file is not None:
    try:
        if resume_file.name.lower().endswith(".pdf"):
            resume_text = extract_pdf_text(resume_file)
        else:
            resume_text = resume_file.getvalue().decode("utf-8", errors="replace")
    except Exception as exc:
        st.error(f"I couldn't read this file: {exc}")

if resume_file is not None and not resume_text:
    st.warning("No selectable text was found. Scanned PDFs need OCR or a cleaner source file. Ensure Tesseract/pdf2image are installed for OCR fallback.")

role_description = st.text_area(
    "2. Paste the target role description",
    height=190,
    placeholder="Paste a job description here. CareerOS compares skills from its visible skill list.",
)

if resume_text:
    st.subheader("3. Review skills found in your resume")
    resume_evidence = find_skill_evidence(resume_text)
    if not resume_evidence:
        st.warning("No skills from the prototype's current skill list were found. You can still review the extracted text below.")
        selected_resume_skills: set[str] = set()
    else:
        st.caption("Select the skills you want to include. Each one shows the resume text that triggered the match.")
        selected_resume_skills = set()
        cols = st.columns(2)
        for idx, (skill, snippet) in enumerate(resume_evidence.items()):
            with cols[idx % 2]:
                checked = st.checkbox(skill, value=True, key=f"resume_skill_{skill}")
                if checked:
                    selected_resume_skills.add(skill)
                st.caption(f"Evidence: {snippet}")

    role_evidence = find_skill_evidence(role_description) if role_description.strip() else {}
    if role_description.strip():
        st.subheader("Skills detected in the role description")
        if role_evidence:
            selected_role_skills = set()
            role_cols = st.columns(2)
            for idx, (skill, snippet) in enumerate(role_evidence.items()):
                with role_cols[idx % 2]:
                    checked = st.checkbox(skill, value=True, key=f"role_skill_{skill}")
                    if checked:
                        selected_role_skills.add(skill)
                    st.caption(f"Evidence: {snippet}")

            render_comparison(selected_resume_skills, selected_role_skills)
        else:
            st.warning("No skills from the current skill list were detected in this role description.")

    with st.expander("Show extracted resume text"):
        st.text(resume_text[:12000])

st.divider()
st.caption("Early MVP • Phrase matching can miss relevant experience or flag a word used in the wrong context. Always review the evidence.")
