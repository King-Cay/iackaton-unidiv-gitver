"""
Collecteur Semantic Scholar (Graph API v1) pour le projet UNIDIV.
Utilise l'endpoint `/paper/search/bulk` avec contrôle de débit (rate-limiting local)
et backoff exponentiel pour respecter la limite de l'API publique sans aucun repli tiers.
Produit des notices 100 % natives Semantic Scholar au Schéma JSON Unifié avec Grade HAS.
"""

from __future__ import annotations

import os
import threading
import time
import requests
from typing import Any

from src.get_doc_from_site.schema_unifie import construire_notice_unifiee

S2_BULK_URL = "https://api.semanticscholar.org/graph/v1/paper/search/bulk"

# Contrôle de débit local (thread-safe) pour éviter le HTTP 429 lors d'appels rapprochés
_S2_LOCK = threading.Lock()
_LAST_S2_CALL_TS = 0.0
_MIN_S2_INTERVAL_SEC = 2.2

# Mapping des types Semantic Scholar vers les intitulés standards HAS / PubMed
S2_PUBTYPE_MAP = {
    "metaanalysis": "Meta-Analysis",
    "clinicaltrial": "Clinical Trial",
    "casereport": "Case Reports",
    "review": "Systematic Review",
    "journalarticle": "Journal Article",
    "study": "Observational Study",
}


def _respecter_quota_s2() -> None:
    """Garantit un espacement minimal entre deux requêtes vers Semantic Scholar."""
    global _LAST_S2_CALL_TS
    with _S2_LOCK:
        maintenant = time.monotonic()
        attente = _MIN_S2_INTERVAL_SEC - (maintenant - _LAST_S2_CALL_TS)
        if attente > 0:
            time.sleep(attente)
        _LAST_S2_CALL_TS = time.monotonic()


def collecte_semantic_scholar(
    country: str,
    context: str,
    sujet: str = "",
    max_articles: int = 20,
    essais: int = 4,
) -> list[dict[str, Any]]:
    """
    Récupère les publications scientifiques depuis Semantic Scholar pour (country, context, sujet).
    Aucun repli tiers : 100 % des notices proviennent de Semantic Scholar.
    """
    parts = [part.strip() for part in (country, context, sujet) if part and part.strip()]
    query = " ".join(parts)
    fields = "paperId,externalIds,url,title,abstract,venue,year,authors,publicationTypes,fieldsOfStudy"

    headers = {"User-Agent": "UNIDIV-collector/1.0 (academic research)"}
    s2_api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if s2_api_key:
        headers["x-api-key"] = s2_api_key

    resp = None
    for essai in range(essais):
        _respecter_quota_s2()
        resp = requests.get(
            S2_BULK_URL,
            params={"query": query, "fields": fields},
            headers=headers,
            timeout=20,
        )
        if resp.status_code == 200:
            break
        if resp.status_code in (429, 500, 502, 503, 504):
            time.sleep(3.0 * (essai + 1))
        else:
            break

    assert resp is not None
    resp.raise_for_status()
    data = resp.json().get("data") or []

    articles: list[dict[str, Any]] = []
    for item in data:
        title = (item.get("title") or "").strip()
        abstract = (item.get("abstract") or "").strip()
        if not title or not abstract:
            continue

        paper_id = item.get("paperId") or title[:24]
        ext_ids = item.get("externalIds") or {}
        pmid = ext_ids.get("PubMed")
        pmcid = ext_ids.get("PubMedCentral")
        doi = ext_ids.get("DOI")

        authors = [
            a.get("name")
            for a in (item.get("authors") or [])
            if isinstance(a, dict) and a.get("name")
        ]

        raw_pts = item.get("publicationTypes") or []
        pub_types = [
            S2_PUBTYPE_MAP.get(str(pt).lower().strip(), str(pt))
            for pt in raw_pts
            if pt
        ]

        fields_of_study = [
            str(f) for f in (item.get("fieldsOfStudy") or []) if f
        ]

        notice = construire_notice_unifiee(
            document_id=f"S2_{paper_id}",
            source="Semantic Scholar",
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=item.get("venue") or "Semantic Scholar",
            publication_year=item.get("year"),
            language="eng",
            url=item.get("url"),
            publication_types=pub_types,
            mesh_terms=fields_of_study,
        )
        articles.append(notice)
        if len(articles) >= max_articles:
            break

    return articles
