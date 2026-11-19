"""
Collecteur Europe PMC (EMBL-EBI) pour le projet UNIDIV.
Implémenté conformément à la documentation officielle RESTful Europe PMC (`GET /search`,
`resultType=core`, `format=json`).
Produit des notices 100 % natives Europe PMC au Schéma JSON Unifié avec Grade HAS.
"""

from __future__ import annotations

import re
import time
import requests
from typing import Any

from src.get_doc_from_site.schema_unifie import construire_notice_unifiee

EUROPEPMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _nettoyer_html(texte: str | None) -> str:
    if not texte:
        return ""
    sans_balises = re.sub(r"<[^>]+>", " ", texte)
    return re.sub(r"\s+", " ", sans_balises).strip()


def collecte_europepmc(
    country: str,
    context: str,
    sujet: str = "",
    max_articles: int = 25,
    essais: int = 3,
) -> list[dict[str, Any]]:
    """
    Récupère les publications scientifiques depuis l'API REST Europe PMC (`GET /search`)
    pour (country, context, sujet). Aucun repli tiers : 100 % des notices proviennent d'Europe PMC.
    """
    mots = [part.strip() for part in (country, context, sujet) if part and part.strip()]
    if not mots:
        raise ValueError("country et context sont requis pour interroger Europe PMC.")
    query = " ".join(mots)

    params = {
        "query": query,
        "resultType": "core",
        "pageSize": min(max(5, max_articles * 2), 100),
        "format": "json",
    }

    derniere_erreur: Exception | None = None
    payload: dict[str, Any] = {}

    for essai in range(essais):
        try:
            resp = requests.get(EUROPEPMC_SEARCH_URL, params=params, timeout=20)
            if resp.status_code in (429, 500, 502, 503, 504):
                time.sleep(1.5 * (essai + 1))
                continue
            resp.raise_for_status()
            if not resp.content or not resp.content.strip():
                time.sleep(1.5 * (essai + 1))
                continue
            payload = resp.json()
            break
        except (requests.exceptions.RequestException, ValueError) as exc:
            derniere_erreur = exc
            if essai == essais - 1:
                raise
            time.sleep(1.5 * (essai + 1))

    if not payload and derniere_erreur is not None:
        raise derniere_erreur

    raw_items = payload.get("resultList", {}).get("result", [])

    articles: list[dict[str, Any]] = []
    for item in raw_items:
        title = _nettoyer_html(item.get("title"))
        abstract = _nettoyer_html(item.get("abstractText"))
        if not title or not abstract:
            continue

        doc_id_raw = item.get("id") or item.get("pmid") or item.get("doi") or title[:32]
        pmid = item.get("pmid")
        pmcid = item.get("pmcid")
        doi = item.get("doi")

        authors: list[str] = []
        author_list = item.get("authorList", {}).get("author", [])
        if isinstance(author_list, list):
            for a in author_list:
                full_name = a.get("fullName")
                if full_name:
                    authors.append(full_name)
        elif item.get("authorString"):
            authors = [a.strip() for a in str(item["authorString"]).split(",") if a.strip()]

        pub_types: list[str] = []
        pt_raw = item.get("pubTypeList", {}).get("pubType", [])
        if isinstance(pt_raw, list):
            pub_types = [str(p) for p in pt_raw if p]
        elif isinstance(pt_raw, str):
            pub_types = [pt_raw]

        mesh_terms: list[str] = []
        mesh_raw = item.get("meshHeadingList", {}).get("meshHeading", [])
        if isinstance(mesh_raw, list):
            for m in mesh_raw:
                if isinstance(m, dict) and m.get("descriptorName"):
                    mesh_terms.append(str(m["descriptorName"]))

        # Ajout des mots-clés auteur éventuels (keywordList) décrits dans la documentation Europe PMC
        kw_raw = item.get("keywordList", {}).get("keyword", [])
        if isinstance(kw_raw, list):
            for kw in kw_raw:
                if kw and str(kw) not in mesh_terms:
                    mesh_terms.append(str(kw))

        journal_info = item.get("journalInfo", {}).get("journal", {})
        journal_title = journal_info.get("title") or item.get("journalTitle") or "Europe PMC"
        pub_year = item.get("pubYear")

        src_code = item.get("source") or "MED"
        url = ""
        if pmcid:
            url = f"https://europepmc.org/article/PMC/{pmcid}"
        elif pmid:
            url = f"https://europepmc.org/article/MED/{pmid}"
        elif item.get("id"):
            url = f"https://europepmc.org/article/{src_code}/{item['id']}"

        notice = construire_notice_unifiee(
            document_id=f"EPMC_{doc_id_raw}",
            source="Europe PMC",
            pmid=pmid,
            pmcid=pmcid,
            doi=doi,
            title=title,
            abstract=abstract,
            authors=authors,
            journal=journal_title,
            publication_year=int(pub_year) if str(pub_year).isdigit() else None,
            language=item.get("language"),
            url=url,
            publication_types=pub_types,
            mesh_terms=mesh_terms,
            license_info="open_access" if item.get("isOpenAccess") == "Y" else "unknown_unverified",
        )
        articles.append(notice)
        if len(articles) >= max_articles:
            break

    return articles
