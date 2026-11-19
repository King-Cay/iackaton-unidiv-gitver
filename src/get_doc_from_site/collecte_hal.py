"""
Collecteur HAL (Archive ouverte du CNRS et des universités françaises) pour le projet UNIDIV.
Particulièrement pertinent pour l'anthropologie médicale, la sociologie de la santé
et la littérature clinique francophone.
Produit des notices au Schéma JSON Unifié avec calcul automatique du Grade HAS bilingue.
"""

from __future__ import annotations

import requests
from typing import Any

from src.get_doc_from_site.schema_unifie import construire_notice_unifiee

HAL_SEARCH_URL = "https://api.archives-ouvertes.fr/search/"

HAL_DOCTYPE_MAP = {
    "ART": "Journal Article",
    "THESE": "Doctoral Thesis",
    "OUV": "Book",
    "COUV": "Book Chapter",
    "COMM": "Conference Paper",
    "REPORT": "Research Report",
}


def _premier_element(val: Any) -> str:
    if isinstance(val, list):
        return str(val[0]).strip() if val else ""
    if isinstance(val, str):
        return val.strip()
    return ""


def collecte_hal(
    country: str,
    context: str,
    sujet: str = "",
    max_articles: int = 20,
) -> list[dict[str, Any]]:
    """
    Récupère les publications scientifiques depuis l'API HAL (CNRS) pour (country, context, sujet).
    """
    termes = [f'"{country.strip()}"', f'"{context.strip()}"']
    if sujet and sujet.strip():
        termes.append(f'"{sujet.strip()}"')
    query = " AND ".join(termes)

    params = {
        "q": query,
        "fq": "abstract_s:*",
        "fl": (
            "docid,title_s,abstract_s,authFullName_s,journalTitle_s,"
            "publicationDateY_i,uri_s,doiId_s,language_s,docType_s,keyword_s"
        ),
        "rows": min(max(1, max_articles), 50),
        "sort": "score desc",
        "wt": "json",
    }

    resp = requests.get(
        HAL_SEARCH_URL,
        params=params,
        headers={"User-Agent": "UNIDIV-collector/1.0 (academic research)"},
        timeout=20,
    )
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])

    articles: list[dict[str, Any]] = []
    for doc in docs:
        title = _premier_element(doc.get("title_s"))
        abstract = _premier_element(doc.get("abstract_s"))
        if not title or not abstract:
            continue

        docid = doc.get("docid") or title[:24]
        raw_doctype = doc.get("docType_s") or ""
        pub_types = [HAL_DOCTYPE_MAP.get(raw_doctype, raw_doctype)] if raw_doctype else []
        keywords = [str(k) for k in (doc.get("keyword_s") or []) if k]

        notice = construire_notice_unifiee(
            document_id=f"HAL_{docid}",
            source="HAL (CNRS)",
            pmid=None,
            pmcid=None,
            doi=doc.get("doiId_s"),
            title=title,
            abstract=abstract,
            authors=[str(a) for a in (doc.get("authFullName_s") or []) if a],
            journal=doc.get("journalTitle_s") or "Archive ouverte HAL (CNRS)",
            publication_year=doc.get("publicationDateY_i"),
            language=_premier_element(doc.get("language_s")) or "fr",
            url=doc.get("uri_s"),
            publication_types=pub_types,
            mesh_terms=keywords,
        )
        articles.append(notice)
        if len(articles) >= max_articles:
            break

    return articles
