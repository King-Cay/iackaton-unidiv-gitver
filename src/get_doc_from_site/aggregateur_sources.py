"""
Agrégateur Multi-Sources & Déduplication Intelligente pour le projet UNIDIV.
Interroge en parallèle les sources de Niveau 1 à API ouverte :
- PubMed (NCBI E-utilities)
- Europe PMC (EMBL-EBI)
- OpenAlex
- Semantic Scholar (Graph API v1)
- HAL (Archive ouverte CNRS)

Puis fusionne les doublons (par DOI, PMID ou Titre normalisé) en conservant
les métadonnées les plus complètes et le meilleur score de recommandation HAS.
"""

from __future__ import annotations

import importlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from src.get_doc_from_site.collecte_europepmc import collecte_europepmc
from src.get_doc_from_site.collecte_hal import collecte_hal
from src.get_doc_from_site.collecte_openalex import collecte_openalex
from src.get_doc_from_site.collecte_pubmed_unidiv import recuperer_donnees as recuperer_pubmed
from src.get_doc_from_site.schema_unifie import (
    evaluer_grade_has,
    normaliser_doi,
    normaliser_pmid,
    normaliser_titre_cle,
)

# Import du module contenant un tiret dans son nom de fichier
_s2_mod = importlib.import_module("src.get_doc_from_site.get_doc_from_semantic-scholar")
collecte_semantic_scholar = _s2_mod.collecte_semantic_scholar


def _collecter_pubmed_liste(country: str, context: str, sujet: str, max_articles: int) -> list[dict[str, Any]]:
    res = recuperer_pubmed(
        pays=country,
        theme=context,
        sujet=sujet,
        max_articles=max_articles,
        sortie=None,
        corpus_existant=None,
        email=None,
    )
    return res.get("articles", [])


def _fusionner_listes_uniques(liste_a: list[str] | None, liste_b: list[str] | None) -> list[str]:
    vus: set[str] = set()
    resultat: list[str] = []
    for item in (liste_a or []) + (liste_b or []):
        if not item:
            continue
        cle = item.strip().lower()
        if cle and cle not in vus:
            vus.add(cle)
            resultat.append(item.strip())
    return resultat


def _fusionner_deux_notices(existante: dict[str, Any], nouvelle: dict[str, Any]) -> dict[str, Any]:
    """
    Fusionne deux notices représentant le même article scientifique :
    - Combine le nom des sources (ex: 'PubMed · OpenAlex')
    - Conserve le résumé le plus complet
    - Fusionne les types de publication et termes MeSH
    - Conserve ou recalcule le meilleur Grade HAS (Couche 3)
    """
    sources_existantes = [s.strip() for s in str(existante.get("source") or "").split("·") if s.strip()]
    for s in [s.strip() for s in str(nouvelle.get("source") or "").split("·") if s.strip()]:
        if s not in sources_existantes:
            sources_existantes.append(s)
    source_fusionnee = " · ".join(sources_existantes) or "Source scientifique"

    abstract_ex = str(existante.get("abstract") or "")
    abstract_nv = str(nouvelle.get("abstract") or "")
    meilleur_abstract = abstract_nv if len(abstract_nv) > len(abstract_ex) else abstract_ex

    title_ex = str(existante.get("title") or "")
    title_nv = str(nouvelle.get("title") or "")
    meilleur_title = title_ex if len(title_ex) >= len(title_nv) else title_nv

    pub_types = _fusionner_listes_uniques(
        existante.get("publication_types"),
        nouvelle.get("publication_types"),
    )
    mesh_terms = _fusionner_listes_uniques(
        existante.get("mesh_terms"),
        nouvelle.get("mesh_terms"),
    )

    # Recalcul du score HAS sur les métadonnées fusionnées + comparaison avec les scores individuels
    score_recalcule = evaluer_grade_has(
        pub_types=pub_types,
        mesh_terms=mesh_terms,
        title=meilleur_title,
        abstract=meilleur_abstract,
    )
    score_ex = existante.get("recommendation_score") or {}
    score_nv = nouvelle.get("recommendation_score") or {}

    candidats_scores = [score_recalcule, score_ex, score_nv]
    meilleur_score = max(
        candidats_scores,
        key=lambda sc: (
            1 if sc.get("grade") in ("A", "B", "C") else 0,
            int(sc.get("score_numerique") or 0),
        ),
    )

    authors_ex = existante.get("authors") or []
    authors_nv = nouvelle.get("authors") or []
    meilleurs_auteurs = authors_nv if len(authors_nv) > len(authors_ex) else authors_ex

    fusion = dict(existante)
    fusion.update({
        "source": source_fusionnee,
        "pmid": normaliser_pmid(existante.get("pmid")) or normaliser_pmid(nouvelle.get("pmid")),
        "pmcid": existante.get("pmcid") or nouvelle.get("pmcid"),
        "doi": normaliser_doi(existante.get("doi")) or normaliser_doi(nouvelle.get("doi")),
        "title": meilleur_title,
        "abstract": meilleur_abstract,
        "authors": meilleurs_auteurs,
        "journal": existante.get("journal") or nouvelle.get("journal"),
        "publication_year": existante.get("publication_year") or nouvelle.get("publication_year"),
        "language": existante.get("language") or nouvelle.get("language"),
        "url": existante.get("url") or nouvelle.get("url"),
        "publication_types": pub_types,
        "mesh_terms": mesh_terms,
        "recommendation_score": meilleur_score,
    })
    return fusion


def dedupliquer_et_fusionner_articles(
    articles: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    """
    Déduplique une liste d'articles multi-sources selon 3 clés hiérarchiques :
    1. DOI normalisé
    2. PMID normalisé
    3. Titre normalisé (sans casse ni ponctuation)

    Retourne (liste_articles_uniques, nombre_de_doublons_fusionnes).
    """
    uniques: list[dict[str, Any]] = []
    by_doi: dict[str, int] = {}
    by_pmid: dict[str, int] = {}
    by_title: dict[str, int] = {}
    doublons_fusionnes = 0

    for art in articles:
        if not isinstance(art, dict):
            continue
        title = (art.get("title") or "").strip()
        abstract = (art.get("abstract") or "").strip()
        if not title or not abstract:
            continue

        doi = normaliser_doi(art.get("doi"))
        pmid = normaliser_pmid(art.get("pmid"))
        title_key = normaliser_titre_cle(title)

        match_idx: int | None = None
        if doi and doi in by_doi:
            match_idx = by_doi[doi]
        elif pmid and pmid in by_pmid:
            match_idx = by_pmid[pmid]
        elif title_key and title_key in by_title:
            match_idx = by_title[title_key]

        if match_idx is not None:
            uniques[match_idx] = _fusionner_deux_notices(uniques[match_idx], art)
            doublons_fusionnes += 1
            idx = match_idx
        else:
            idx = len(uniques)
            uniques.append(dict(art))

        # Enregistrement de toutes les clés connues pour cet article canonique
        merged = uniques[idx]
        m_doi = normaliser_doi(merged.get("doi"))
        m_pmid = normaliser_pmid(merged.get("pmid"))
        m_title = normaliser_titre_cle(merged.get("title"))

        if m_doi:
            by_doi[m_doi] = idx
        if m_pmid:
            by_pmid[m_pmid] = idx
        if m_title:
            by_title[m_title] = idx

    return uniques, doublons_fusionnes


def collecter_toutes_sources(
    country: str,
    context: str,
    sujet: str = "",
    max_per_source: int = 20,
    save_to_disk: bool = True,
) -> dict[str, Any]:
    """
    Interroge en parallèle toutes les sources scientifiques de Niveau 1,
    fusionne et déduplique les résultats, et sauvegarde le corpus dans data/raw/.
    """
    collecteurs: list[tuple[str, Callable[[], list[dict[str, Any]]]]] = [
        ("PubMed", lambda: _collecter_pubmed_liste(country, context, sujet, max_per_source)),
        ("Europe PMC", lambda: collecte_europepmc(country, context, sujet, max_per_source)),
        ("OpenAlex", lambda: collecte_openalex(country, context, sujet, max_per_source)),
        ("Semantic Scholar", lambda: collecte_semantic_scholar(country, context, sujet, max_per_source)),
        ("HAL (CNRS)", lambda: collecte_hal(country, context, sujet, max_per_source)),
    ]

    bruts_par_source: dict[str, list[dict[str, Any]]] = {}
    erreurs_sources: dict[str, str] = {}

    with ThreadPoolExecutor(max_workers=len(collecteurs)) as executor:
        future_to_name = {
            executor.submit(fn): nom for nom, fn in collecteurs
        }
        for future in as_completed(future_to_name):
            nom = future_to_name[future]
            try:
                items = future.result() or []
                bruts_par_source[nom] = items
            except Exception as exc:
                bruts_par_source[nom] = []
                erreurs_sources[nom] = str(exc)

    # Assemblage dans un ordre déterministe (PubMed -> Europe PMC -> OpenAlex -> Semantic Scholar -> HAL)
    tous_articles_bruts: list[dict[str, Any]] = []
    stats_sources: dict[str, int] = {}
    for nom, _ in collecteurs:
        liste = bruts_par_source.get(nom, [])
        stats_sources[nom] = len(liste)
        tous_articles_bruts.extend(liste)

    articles_uniques, nb_doublons = dedupliquer_et_fusionner_articles(tous_articles_bruts)

    nom_fichier = lambda x: re.sub(r"[^a-z0-9_-]+", "_", x.strip().lower()).strip("_")
    suffixe_sujet = f"_{nom_fichier(sujet)}" if sujet and sujet.strip() else ""
    destination = Path("data/raw") / f"aggregated_{nom_fichier(country)}_{nom_fichier(context)}{suffixe_sujet}.json"

    payload = {
        "project": "UNIDIV",
        "type": "aggregated_multisource_records_v1",
        "country_query": country,
        "topic_query": context,
        "subtopic_query": sujet,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "sources_queried": [nom for nom, _ in collecteurs],
        "sources_counts_raw": stats_sources,
        "sources_errors": erreurs_sources,
        "total_raw_articles": len(tous_articles_bruts),
        "article_count": len(articles_uniques),
        "duplicates_merged": nb_doublons,
        "articles": articles_uniques,
    }

    if save_to_disk:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "Notices brutes collectées": len(tous_articles_bruts),
        "Notices uniques après déduplication": len(articles_uniques),
        "Doublons fusionnés": nb_doublons,
        "Détail par source": stats_sources,
        "articles": articles_uniques,
        "output_path": destination.resolve(),
    }
