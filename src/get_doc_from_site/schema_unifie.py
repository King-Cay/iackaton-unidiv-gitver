"""
Schéma JSON unifié et moteur d'évaluation HAS bilingue (FR / EN)
partagé par tous les collecteurs scientifiques du projet UNIDIV.
"""

from __future__ import annotations

import re
from typing import Any


def normaliser_doi(doi: str | None) -> str | None:
    """Nettoie un DOI pour la déduplication (minuscules, sans préfixe URL)."""
    if not doi:
        return None
    clean = str(doi).strip().lower()
    for prefix in ("https://doi.org/", "http://doi.org/", "https://dx.doi.org/", "doi:"):
        if clean.startswith(prefix):
            clean = clean[len(prefix):].strip()
    return clean or None


def normaliser_pmid(pmid: str | int | None) -> str | None:
    """Nettoie un identifiant PubMed (PMID) sous forme de chiffres uniquement."""
    if pmid is None:
        return None
    clean = str(pmid).strip()
    for prefix in ("https://pubmed.ncbi.nlm.nih.gov/", "http://pubmed.ncbi.nlm.nih.gov/", "pmid:", "pmid_"):
        if clean.lower().startswith(prefix):
            clean = clean[len(prefix):]
    clean = clean.strip("/ ")
    return clean if clean.isdigit() else None


def normaliser_titre_cle(title: str | None) -> str:
    """Produit une clé normalisée d'un titre (sans ponctuation ni casse) pour détecter les doublons."""
    if not title:
        return ""
    return re.sub(r"[^a-z0-9]+", " ", title.lower()).strip()


def evaluer_grade_has(
    pub_types: list[str] | None = None,
    mesh_terms: list[str] | None = None,
    title: str = "",
    abstract: str = "",
) -> dict[str, Any]:
    """
    Attribue un grade de recommandation HAS (A, B, C ou NC) et un niveau de preuve (1 à 4)
    à partir des métadonnées structurées (Couche 1) et d'une détection bilingue FR/EN
    dans le titre et le résumé (Couche 2).
    """
    pub_types = [p for p in (pub_types or []) if p]
    mesh_terms = [m for m in (mesh_terms or []) if m]

    pt_lower = {p.lower().strip() for p in pub_types}
    mesh_lower = {m.lower().strip() for m in mesh_terms}
    text = f"{title} {abstract}".lower()

    # Synonymes normalisés de types de publication entre APIs (PubMed, EuropePMC, SemanticScholar, OpenAlex)
    is_meta_or_rct_type = bool(
        pt_lower
        & {
            "meta-analysis",
            "metaanalysis",
            "randomized controlled trial",
            "network meta-analysis",
        }
        or mesh_lower
        & {
            "meta-analysis",
            "meta-analysis as topic",
            "randomized controlled trial",
            "randomized controlled trials as topic",
        }
    )

    is_meta_or_rct_text = bool(
        re.search(
            r"\b("
            r"randomi[sz]ed controlled trial|meta[- ]analysis|network meta[- ]analysis|"
            r"essai comparatif randomis[ée]|essai contr[ôo]l[ée] randomis[ée]|"
            r"essai clinique randomis[ée]|m[ée]ta[- ]analyse"
            r")\b",
            text,
        )
    )

    # 1. Grade A — Niveau 1 (Preuve scientifique établie)
    if is_meta_or_rct_type or is_meta_or_rct_text:
        est_multicentrique = (
            "multicenter study" in pt_lower
            or "multicenter" in text
            or "multicentrique" in text
            or "meta-analysis" in pt_lower
            or "metaanalysis" in pt_lower
            or "méta-analyse" in text
            or "meta-analysis" in text
        )
        return {
            "grade": "A",
            "niveau_preuve": 1,
            "score_numerique": 100,
            "label": "Preuve scientifique établie (Niveau 1)",
            "methode_detectee": ", ".join(pub_types[:3]) or "Essai comparatif randomisé / Méta-analyse",
            "note_prudence": None if est_multicentrique else "Puissance statistique à confirmer dans le texte intégral.",
        }

    # 2. Grade B — Niveau 2 (Présomption scientifique : cohortes, essais comparatifs non randomisés)
    if (
        pt_lower
        & {
            "controlled clinical trial",
            "clinical trial",
            "clinicaltrial",
            "comparative study",
            "pragmatic clinical trial",
        }
        or mesh_lower
        & {
            "cohort studies",
            "cohort study",
            "prospective studies",
            "follow-up studies",
        }
        or re.search(
            r"\b("
            r"cohort study|prospective cohort|prospective study|non[- ]randomi[sz]ed|"
            r"quasi[- ]experimental|controlled clinical trial|"
            r"[ée]tude de cohorte|cohorte prospective|[ée]tude prospective|"
            r"essai comparatif non randomis[ée]|[ée]tude comparative non randomis[ée]|"
            r"[ée]tude quasi[- ]exp[ée]rimentale"
            r")\b",
            text,
        )
    ):
        return {
            "grade": "B",
            "niveau_preuve": 2,
            "score_numerique": 75,
            "label": "Présomption scientifique (Niveau 2)",
            "methode_detectee": ", ".join(pub_types[:2] or mesh_terms[:2]) or "Étude de cohorte / comparative",
            "note_prudence": None,
        }

    # 3. Grade C — Niveau 3 (Études cas-témoins)
    if (
        mesh_lower & {"case-control studies", "case-control study"}
        or re.search(
            r"\b(case[- ]control|[ée]tude cas[- ]t[ée]moins?|cas[- ]t[ée]moins?)\b",
            text,
        )
    ):
        return {
            "grade": "C",
            "niveau_preuve": 3,
            "score_numerique": 50,
            "label": "Faible niveau de preuve scientifique (Niveau 3)",
            "methode_detectee": "Étude cas-témoins",
            "note_prudence": None,
        }

    # 4. Grade C — Niveau 4 (Études rétrospectives, séries de cas, descriptives transversales/longitudinales)
    if (
        pt_lower & {"case reports", "casereport", "observational study"}
        or mesh_lower
        & {
            "retrospective studies",
            "cross-sectional studies",
            "cross-sectional study",
            "longitudinal studies",
        }
        or re.search(
            r"\b("
            r"retrospective|case series|case report|cross[- ]sectional|descriptive study|longitudinal study|"
            r"[ée]tude r[ée]trospective|s[ée]rie de cas|cas clinique|[ée]tude transversale|"
            r"enqu[êe]te transversale|[ée]tude [ée]pid[ée]miologique descriptive|[ée]tude longitudinale"
            r")\b",
            text,
        )
    ):
        return {
            "grade": "C",
            "niveau_preuve": 4,
            "score_numerique": 35,
            "label": "Faible niveau de preuve scientifique (Niveau 4)",
            "methode_detectee": ", ".join(pub_types[:2]) or "Étude descriptive / rétrospective / série de cas",
            "note_prudence": None,
        }

    # 5. Études qualitatives / anthropologiques (pertinentes en médecine transculturelle, hors grille ECR)
    if (
        mesh_lower
        & {
            "qualitative research",
            "anthropology, cultural",
            "medical anthropology",
            "focus groups",
        }
        or re.search(
            r"\b("
            r"qualitative|phenomenological|ethnograph\w*|thematic analysis|semi[- ]structured interviews|focus group|"
            r"[ée]tude qualitative|recherche qualitative|approche ph[ée]nom[ée]nologique|"
            r"ethnographie|[ée]tude ethnographique|entretiens? semi[- ]directifs?|analyse th[ée]matique|"
            r"anthropologie m[ée]dicale"
            r")\b",
            text,
        )
    ):
        return {
            "grade": "NC",
            "niveau_preuve": None,
            "score_numerique": 45,
            "label": "Étude qualitative (hors échelle quantitative HAS)",
            "methode_detectee": "Recherche qualitative / anthropologique",
            "note_prudence": "Pertinente pour les déterminants culturels ; non évaluable selon la grille ECR.",
        }

    return {
        "grade": "NC",
        "niveau_preuve": None,
        "score_numerique": 20,
        "label": "Niveau de preuve non déterminé automatiquement",
        "methode_detectee": ", ".join(pub_types[:2]) if pub_types else "Non spécifié",
        "note_prudence": "Vérification méthodologique manuelle recommandée.",
    }


def construire_notice_unifiee(
    *,
    document_id: str,
    source: str,
    title: str,
    abstract: str,
    pmid: str | int | None = None,
    pmcid: str | None = None,
    doi: str | None = None,
    authors: list[str] | None = None,
    journal: str | None = None,
    publication_year: int | None = None,
    language: str | None = None,
    url: str | None = None,
    publication_types: list[str] | None = None,
    mesh_terms: list[str] | None = None,
    license_info: str = "unknown_unverified",
) -> dict[str, Any]:
    """
    Construit un dictionnaire d'article conforme au Schéma JSON Unifié UNIDIV
    et calcule automatiquement son `recommendation_score` (Grade HAS).
    """
    clean_pmid = normaliser_pmid(pmid)
    clean_doi = normaliser_doi(doi)
    clean_title = (title or "").strip()
    clean_abstract = (abstract or "").strip()
    pub_types = [p for p in (publication_types or []) if p]
    meshes = [m for m in (mesh_terms or []) if m]

    resolved_url = (url or "").strip()
    if not resolved_url:
        if clean_pmid:
            resolved_url = f"https://pubmed.ncbi.nlm.nih.gov/{clean_pmid}/"
        elif clean_doi:
            resolved_url = f"https://doi.org/{clean_doi}"

    year_int: int | None = None
    if publication_year is not None:
        try:
            year_int = int(publication_year)
        except (ValueError, TypeError):
            year_int = None

    evaluation_has = evaluer_grade_has(
        pub_types=pub_types,
        mesh_terms=meshes,
        title=clean_title,
        abstract=clean_abstract,
    )

    return {
        "document_id": document_id,
        "source": source,
        "pmid": clean_pmid,
        "pmcid": pmcid,
        "doi": clean_doi,
        "title": clean_title,
        "abstract": clean_abstract,
        "authors": [a for a in (authors or []) if a],
        "journal": (journal or source).strip(),
        "publication_year": year_int,
        "language": language,
        "url": resolved_url or None,
        "publication_types": pub_types,
        "mesh_terms": meshes,
        "recommendation_score": evaluation_has,
        "license": license_info,
        "scientific_review_status": "not_reviewed",
        "data_status": "raw_unfiltered",
    }
