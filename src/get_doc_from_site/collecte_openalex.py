"""
Collecteur OpenAlex pour le projet UNIDIV.
Couvre à la fois la médecine clinique et les sciences humaines et sociales (anthropologie, sociologie).
Produit des notices au Schéma JSON Unifié avec calcul automatique du Grade HAS.
"""

from __future__ import annotations

import os
import time
import requests
from typing import Any

from src.get_doc_from_site.schema_unifie import construire_notice_unifiee

OPENALEX_WORKS_URL = "https://api.openalex.org/works"


def _reconstruire_abstract(inverted_index: dict[str, list[int]] | None) -> str:
    """Reconstruit le texte du résumé depuis l'index inversé {mot: [positions]} d'OpenAlex."""
    if not inverted_index or not isinstance(inverted_index, dict):
        return ""
    all_positions = [pos for positions in inverted_index.values() for pos in positions if isinstance(pos, int)]
    if not all_positions:
        return ""
    taille = max(all_positions) + 1
    mots = [""] * taille
    for mot, positions in inverted_index.items():
        for pos in positions:
            if isinstance(pos, int) and 0 <= pos < taille:
                mots[pos] = mot
    return " ".join(m for m in mots if m).strip()


def collecte_openalex(
    country: str,
    context: str,
    sujet: str = "",
    max_articles: int = 25,
    essais: int = 3,
) -> list[dict[str, Any]]:
    """
    Récupère les publications scientifiques depuis OpenAlex pour (country, context, sujet).
    """
    search_terms = " ".join(part.strip() for part in (country, context, sujet) if part and part.strip())

    # On filtre les résumés vides côté Python plutôt qu'avec filter=has_abstract:true
    # afin de réduire le coût quota de la requête sur l'API OpenAlex.
    params: dict[str, str | int] = {
        "search": search_terms,
        "per-page": min(max(10, max_articles * 2), 50),
    }
    openalex_key = os.environ.get("OPENALEX_API_KEY")
    if openalex_key:
        params["api_key"] = openalex_key

    headers = {"User-Agent": "UNIDIV-collector/1.0 (mailto:unidiv@univ-lorraine.fr)"}

    resp = None
    for essai in range(essais):
        resp = requests.get(
            OPENALEX_WORKS_URL,
            params=params,
            headers=headers,
            timeout=25,
        )
        if resp.status_code not in (429, 500, 502, 503, 504):
            break
        time.sleep(1.2 * (essai + 1))

    assert resp is not None
    resp.raise_for_status()
    works = resp.json().get("results", [])

    articles: list[dict[str, Any]] = []
    for work in works:
        title = (work.get("title") or work.get("display_name") or "").strip()
        abstract = _reconstruire_abstract(work.get("abstract_inverted_index"))
        if not title or not abstract:
            continue

        work_id = str(work.get("id") or "").split("/")[-1] or title[:24]
        ids_dict = work.get("ids") or {}
        pmid = ids_dict.get("pmid")
        pmcid = ids_dict.get("pmcid")
        doi = work.get("doi") or ids_dict.get("doi")

        authors = [
            a["author"]["display_name"]
            for a in (work.get("authorships") or [])[:12]
            if isinstance(a, dict) and (a.get("author") or {}).get("display_name")
        ]

        primary_loc = work.get("primary_location") or {}
        source_obj = primary_loc.get("source") or {}
        journal = source_obj.get("display_name") or "OpenAlex"

        pub_types: list[str] = []
        if work.get("type"):
            pub_types.append(str(work["type"]))

        mesh_terms: list[str] = []
        for m in work.get("mesh") or []:
            if isinstance(m, dict) and m.get("descriptor_name"):
                mesh_terms.append(str(m["descriptor_name"]))

        for c in (work.get("concepts") or [])[:8]:
            if isinstance(c, dict) and c.get("display_name"):
                mesh_terms.append(str(c["display_name"]))

        for t in (work.get("topics") or [])[:5]:
            if isinstance(t, dict) and t.get("display_name"):
                mesh_terms.append(str(t["display_name"]))

        url = primary_loc.get("landing_page_url") or work.get("doi") or work.get("id")

        notice = construire_notice_unifiee(
            document_id=f"OPENALEX_{work_id}",
            source="OpenAlex",
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal,
            publication_year=work.get("publication_year"),
            language=work.get("language"),
            url=url,
            publication_types=pub_types,
            mesh_terms=mesh_terms,
        )
        articles.append(notice)
        if len(articles) >= max_articles:
            break

    return articles
