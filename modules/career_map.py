"""Explainable career-path retrieval over the bundled O*NET occupation graph.

O*NET data is licensed under CC BY 4.0. CareerOS ranks descriptions, work
tasks, and transferable skills locally; its ranking is a discovery aid, not a
validated fit, hiring, or outcome prediction.
"""

from __future__ import annotations

import csv
import gzip
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "onet_31_0"
SOURCE_NAME = "O*NET Database 31.0"
SOURCE_URL = "https://www.onetonline.org/"
_STOP_WORDS = frozenset(
    "a about after all also an and any are as at be because been before being between both but by can career could did do does for from had has have he her here hers him his how i if in into is it its job me more most my of on or our out she should so some such than that the their them then there these they this those through to up us very was we were what when where which while who why will with would you your work worked working experience role skills skill task tasks want hoping curious exploring explore interested unsure know yet sure still trying not".split()
)
_TOKEN_RE = re.compile(r"[a-z][a-z0-9+#-]{1,}")
_CONCEPTS = {
    "science": ("scientist", "scientific"),
    "scienc": ("scientist", "scientific"),
    "scientist": ("science", "scientific"),
    "analyze": ("analysis", "analytical"),
    "analysis": ("analyze", "analytical"),
    "analysi": ("analyze", "analytical"),
    "analyz": ("analysis", "analytical"),
    "help": ("support", "assistance"),
    "support": ("help", "assistance"),
    "organize": ("coordinate", "planning"),
    "coordinate": ("organize", "planning"),
    "care": ("caregiving", "support"),
    "caregiving": ("care", "support"),
}


def _surface_tokens(text: str) -> list[str]:
    return [token for token in _TOKEN_RE.findall(text.casefold()) if token not in _STOP_WORDS]


def _tokens(text: str) -> list[str]:
    output: list[str] = []
    for original in _surface_tokens(text):
        if original in _STOP_WORDS:
            continue
        token = original
        if token.endswith("ies") and len(token) > 5:
            token = token[:-3] + "y"
        elif token.endswith("ing") and len(token) > 6:
            token = token[:-3]
            if len(token) > 3 and token[-1] == token[-2]:
                token = token[:-1]
        elif token.endswith("ed") and len(token) > 5:
            token = token[:-2]
        elif token.endswith("s") and len(token) > 4 and not token.endswith("ss"):
            token = token[:-1]
        if token.endswith("e") and len(token) > 5:
            token = token[:-1]
        output.append(token)
        output.extend(_CONCEPTS.get(original, ()))
        output.extend(_CONCEPTS.get(token, ()))
    return output


def _read_rows(filename: str) -> list[dict[str, str]]:
    path = DATA_DIR / f"{filename}.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


@lru_cache(maxsize=1)
def _catalog() -> dict[str, Any]:
    occupations = {
        row["O*NET-SOC Code"]: {
            "code": row["O*NET-SOC Code"],
            "title": row["Title"],
            "description": row["Description"],
            "tasks": [],
            "skills": [],
            "related": [],
            "job_zone": None,
        }
        for row in _read_rows("occupation_data")
    }
    for row in _read_rows("task_statements"):
        role = occupations.get(row["O*NET-SOC Code"])
        if role and row.get("Task"):
            role["tasks"].append({"text": row["Task"], "type": row.get("Task Type", "")})
    for row in _read_rows("transferable_skills"):
        role = occupations.get(row["O*NET-SOC Code"])
        if role and row.get("Scale ID") == "IM" and row.get("Element Name"):
            try:
                importance = float(row.get("Data Value", "0") or 0)
            except ValueError:
                importance = 0.0
            role["skills"].append({"name": row["Element Name"], "importance": importance})
    for row in _read_rows("related_occupations"):
        role = occupations.get(row["O*NET-SOC Code"])
        if role and row.get("Related O*NET-SOC Code") in occupations:
            role["related"].append({
                "code": row["Related O*NET-SOC Code"],
                "title": row.get("Related Title", ""),
                "tier": row.get("Relatedness Tier", ""),
            })
    for row in _read_rows("job_zones"):
        role = occupations.get(row["O*NET-SOC Code"])
        if role and row.get("Job Zone"):
            role["job_zone"] = row["Job Zone"]

    for role in occupations.values():
        role["tasks"].sort(key=lambda task: (task["type"] != "Core", task["text"]))
        role["skills"].sort(key=lambda skill: (-skill["importance"], skill["name"]))
    return {"occupations": occupations}


def _bm25(query: str, documents: Iterable[str]) -> list[tuple[float, set[str]]]:
    tokenized = [_tokens(document) for document in documents]
    query_terms = set(_tokens(query))
    if not query_terms:
        return [(0.0, set()) for _ in tokenized]
    document_frequency: Counter[str] = Counter()
    for terms in tokenized:
        document_frequency.update(set(terms))
    count = max(len(tokenized), 1)
    average_length = sum(map(len, tokenized)) / count or 1.0
    results: list[tuple[float, set[str]]] = []
    for terms in tokenized:
        frequencies = Counter(terms)
        score = 0.0
        for term in query_terms:
            frequency = frequencies[term]
            if not frequency:
                continue
            inverse = math.log(1 + (count - document_frequency[term] + 0.5) / (document_frequency[term] + 0.5))
            denominator = frequency + 1.5 * (0.25 + 0.75 * len(terms) / average_length)
            score += inverse * frequency * 2.5 / denominator
        results.append((score, query_terms.intersection(frequencies)))
    return results


def rank_career_paths(
    experiences: Iterable[str],
    interests: str = "",
    limit: int = 12,
) -> list[dict[str, Any]]:
    """Rank occupations against life and work evidence, interests, and goals."""
    evidence = " ".join(part.strip() for part in experiences if part and part.strip())
    query = " ".join(part for part in (evidence, interests.strip()) if part)
    if not _tokens(query):
        return []

    catalog = _catalog()["occupations"]
    roles = list(catalog.values())
    documents = [
        " ".join([
            role["title"],
            role["description"],
            " ".join(task["text"] for task in role["tasks"][:12]),
            " ".join(skill["name"] for skill in role["skills"][:18]),
        ])
        for role in roles
    ]
    ranked = _bm25(query, documents)
    title_ranked = _bm25(query, [role["title"] for role in roles])
    candidates = [
        (score + title_ranked[index][0] * 2.5, index)
        for index, (score, _) in enumerate(ranked)
        if score > 0 or title_ranked[index][0] > 0
    ]
    candidates.sort(key=lambda item: (-item[0], roles[item[1]]["title"]))

    results: list[dict[str, Any]] = []
    surface_query_terms = set(_surface_tokens(query))
    evidence_terms = set(_tokens(evidence))
    for score, index in candidates[: max(1, min(limit, 30))]:
        role = roles[index]
        matched_terms = surface_query_terms & set(_surface_tokens(documents[index]))
        task_texts = [task["text"] for task in role["tasks"]]
        task_hits = _bm25(evidence or interests, task_texts)
        best_task_indexes = sorted(
            (task_index for task_index, (task_score, _) in enumerate(task_hits) if task_score > 0),
            key=lambda task_index: (-task_hits[task_index][0], role["tasks"][task_index]["type"] != "Core"),
        )[:3]
        matched_skills = [
            skill["name"] for skill in role["skills"] if set(_tokens(skill["name"])) & evidence_terms
        ][:6]
        results.append({
            "code": role["code"],
            "title": role["title"],
            "description": role["description"],
            "source_url": f"https://www.onetonline.org/link/summary/{role['code']}",
            "source": SOURCE_NAME,
            "matched_signals": sorted(matched_terms, key=lambda term: (-len(term), term))[:6],
            "tasks": [role["tasks"][task_index]["text"] for task_index in best_task_indexes],
            "transferable_skills": [skill["name"] for skill in role["skills"][:6]],
            "evidence_skill_overlap": matched_skills,
            "job_zone": role["job_zone"],
            "related_roles": [
                item["title"]
                for item in sorted(role["related"], key=lambda item: ("Short" not in item["tier"], item["tier"], item["title"]))[:4]
            ],
            "_score": score,
        })
    # Only return a role's explanation data; the numeric retrieval score is not
    # presented as a probability, fit percentage, or assessment result.
    for result in results:
        result.pop("_score", None)
    return results


def career_map_source() -> dict[str, str]:
    return {
        "name": SOURCE_NAME,
        "url": "https://www.onetcenter.org/database.html",
        "license": "CC BY 4.0",
        "license_url": "https://creativecommons.org/licenses/by/4.0/",
    }
