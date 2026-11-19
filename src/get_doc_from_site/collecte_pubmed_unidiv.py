"""Collecte de notices scientifiques PubMed pour le projet UNIDIV.

Fonction principale : recuperer_donnees(pays, theme, max_articles=50)

À noter : le JSON généré contient des notices BRUTES. Il ne remplace pas
le filtrage scientifique, le contrôle des licences, ni la préparation des
passages MiniLM du pipeline UNIDIV.

Exemple :
  python collecte_pubmed_unidiv.py --pays Morocco --theme Pregnancy --max 30
  python collecte_pubmed_unidiv.py --pays Senegal --theme Nutrition --max 50 \
      --corpus-existant ./minilm/data --sortie ./articles_nouveaux.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from src.get_doc_from_site.schema_unifie import construire_notice_unifiee, evaluer_grade_has as _evaluer_grade_has

NCBI_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
TOOL_NAME = "UNIDIV-collector"
# Le service NCBI recommande au maximum 3 requêtes/s sans clé d'API.
REQUEST_PAUSE_SECONDS = 0.4


def _normaliser_texte(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return re.sub(r"\s+", " ", html.unescape("".join(element.itertext()))).strip()


def _texte(element: ET.Element, chemin: str) -> str:
    return _normaliser_texte(element.find(chemin))


def _requete_ncbi(endpoint: str, params: dict[str, str | int], essais: int = 3) -> bytes:
    """Requête HTTP GET, avec contrôle basique des erreurs et tentatives."""
    data = dict(params)
    data["tool"] = TOOL_NAME
    url = f"{NCBI_BASE}/{endpoint}?{urllib.parse.urlencode(data)}"
    request = urllib.request.Request(url, headers={"User-Agent": "UNIDIV-collector/1.0 (academic research)"})

    for essai in range(essais):
        try:
            time.sleep(REQUEST_PAUSE_SECONDS)
            with urllib.request.urlopen(request, timeout=35) as response:
                return response.read()
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as exc:
            # Ne pas retenter les erreurs définitives comme 400 et 404.
            if isinstance(exc, urllib.error.HTTPError) and exc.code not in (429, 500, 502, 503, 504):
                raise RuntimeError(f"Erreur PubMed HTTP {exc.code}: {exc.reason}") from exc
            if essai == essais - 1:
                raise RuntimeError("PubMed est inaccessible après plusieurs tentatives") from exc
            time.sleep(2 ** essai)
    raise RuntimeError("Requête PubMed non aboutie")


def _requete_recherche(pays: str, theme: str, sujet: str = "") -> str:
    """Interroger les champs titre/résumé et les termes MeSH de PubMed.

    Une correspondance dans une notice ne prouve PAS qu'une étude concerne
    directement la population du pays; filtrage manuel/pipeline requis.
    """
    for nom, valeur in (("pays", pays), ("thème", theme)):
        if not valeur.strip() or any(car in valeur for car in '[]"\n\r'):
            raise ValueError(f"{nom} non valide")
    pays = pays.strip()
    theme = theme.strip()
    sujet = (sujet or "").strip()
    requete = (
        f'("{pays}"[Title/Abstract] OR "{pays}"[MeSH Terms]) '
        f'AND ("{theme}"[Title/Abstract] OR "{theme}"[MeSH Terms])'
    )
    if sujet:
        requete += f' AND ("{sujet}"[Title/Abstract] OR "{sujet}"[MeSH Terms])'
    return requete


def _parser_article(article: ET.Element) -> dict | None:
    """Convertir un <PubmedArticle> XML en notice JSON avec provenance."""
    pmid = _texte(article, "./MedlineCitation/PMID")
    if not pmid:
        return None
    article_node = article.find("./MedlineCitation/Article")
    if article_node is None:
        return None

    title = _texte(article_node, "ArticleTitle")
    parties_resume = []
    for passage in article_node.findall("./Abstract/AbstractText"):
        valeur = _normaliser_texte(passage)
        if not valeur:
            continue
        etiquette = passage.attrib.get("Label") or passage.attrib.get("NlmCategory", "")
        if etiquette and etiquette.upper() != "UNASSIGNED":
            valeur = f"{etiquette}: {valeur}"
        parties_resume.append(valeur)
    resume = "\n".join(parties_resume)

    auteurs = []
    for auteur in article_node.findall("./AuthorList/Author"):
        nom = " ".join(filter(None, [
            _texte(auteur, "ForeName") or _texte(auteur, "Initials"),
            _texte(auteur, "LastName"),
        ]))
        nom = nom or _texte(auteur, "CollectiveName")
        if nom:
            auteurs.append(nom)

    ids: dict[str, str] = {}
    for identifiant in article.findall("./PubmedData/ArticleIdList/ArticleId"):
        type_id = identifiant.attrib.get("IdType", "").lower()
        valeur = _normaliser_texte(identifiant)
        if type_id in ("doi", "pmc") and valeur:
            ids[type_id] = valeur
    for identifiant in article_node.findall("ELocationID"):
        if identifiant.attrib.get("EIdType", "").lower() == "doi" and _normaliser_texte(identifiant):
            ids.setdefault("doi", _normaliser_texte(identifiant))

    annee = (_texte(article_node, "Journal/JournalIssue/PubDate/Year")
             or _texte(article_node, "ArticleDate/Year"))
    if not annee:
        date_imprecise = _texte(article_node, "Journal/JournalIssue/PubDate/MedlineDate")
        m = re.search(r"\b(?:18|19|20)\d{2}\b", date_imprecise)
        annee = m.group(0) if m else ""

    pub_types = [
        _normaliser_texte(node)
        for node in article_node.findall("./PublicationTypeList/PublicationType")
        if _normaliser_texte(node)
    ]
    mesh_terms = [
        _normaliser_texte(node)
        for node in article.findall("./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName")
        if _normaliser_texte(node)
    ]

    return construire_notice_unifiee(
        document_id=f"PMID_{pmid}",
        source="PubMed",
        pmid=pmid,
        pmcid=ids.get("pmc"),
        doi=ids.get("doi"),
        title=title,
        abstract=resume,
        authors=auteurs,
        journal=_texte(article_node, "Journal/Title"),
        publication_year=int(annee) if annee.isdigit() else None,
        language=_texte(article_node, "Language") or None,
        url=f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
        publication_types=pub_types,
        mesh_terms=mesh_terms,
    )


def _pmids_deja_presents(dossier: str | Path | None) -> set[str]:
    """Lire les PMIDs des corpus MiniLM existants pour éviter les doublons."""
    if dossier is None:
        return set()
    dossier = Path(dossier)
    if not dossier.exists():
        raise FileNotFoundError(f"Corpus existant introuvable : {dossier}")
    pmids = set()
    fichiers = sorted(dossier.rglob("minilm_*.json")) if dossier.is_dir() else [dossier]
    for fichier in fichiers:
        donnees = json.loads(fichier.read_text(encoding="utf-8"))
        for publication in donnees.get("publications", []):
            pmid = publication.get("identifiers", {}).get("pmid")
            if pmid:
                pmids.add(str(pmid))
        for passage in donnees.get("documents", []):
            pmid = passage.get("metadata", {}).get("pmid")
            if pmid:
                pmids.add(str(pmid))
    return pmids


def recuperer_donnees(
    pays: str,
    theme: str,
    sujet : str,
    max_articles: int = 50,
    sortie: str | Path | None = None,
    corpus_existant: str | Path | None = None,
    email: str | None = None
) -> dict:
    """Récupérer des notices PubMed par pays/thème et les sauvegarder.

    Retourne un dict : query, total_pubmed_results, articles, article_count,
    skipped_existing, etc. Pas de sélection scientifique automatique ici.
    Par défaut, la collecte est limitée à 50 articles (maximum 1000).
    """
    if not 1 <= max_articles <= 1000:
        raise ValueError("max_articles doit être compris entre 1 et 1000")
    requete = _requete_recherche(pays, theme,sujet)
    deja_presents = _pmids_deja_presents(corpus_existant)
    common = {"db": "pubmed", "retmode": "xml"}
    if email:
        common["email"] = email

    # Recherche par page : on peut demander davantage que max_articles
    # pour obtenir max_articles *nouveaux* après élimination des doublons.
    articles = []
    vus = set()
    ignores_existants = 0
    total = 0
    depart = 0
    while len(articles) < max_articles and depart < 10000:
        lot = min(100, 10000 - depart)
        search_xml = _requete_ncbi("esearch.fcgi", {
            **common, "term": requete, "retstart": depart,
            "retmax": lot, "sort": "relevance",
        })
        search_root = ET.fromstring(search_xml)
        total = int(search_root.findtext("Count", default="0"))
        ids = [node.text for node in search_root.findall("./IdList/Id") if node.text]
        if not ids:
            break
        depart += len(ids)
        nouveaux_ids = []
        for pmid in ids:
            if pmid in deja_presents:
                ignores_existants += 1
            elif pmid not in vus:
                nouveaux_ids.append(pmid)
                vus.add(pmid)
        if nouveaux_ids:
            # EFetch fonctionne ici par petits lots de 100 identifiants.
            fetch_xml = _requete_ncbi("efetch.fcgi", {
                **common, "id": ",".join(nouveaux_ids), "rettype": "xml",
            })
            fetch_root = ET.fromstring(fetch_xml)
            for item in fetch_root.findall("./PubmedArticle"):
                notice = _parser_article(item)
                if notice:
                    articles.append(notice)
                    if len(articles) >= max_articles:
                        break
        if depart >= total:
            break

    resultat = {
        "project": "UNIDIV",
        "type": "raw_pubmed_records_v1",
        "country_query": pays,
        "topic_query": theme,
        "pubmed_query": requete,
        "collected_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_pubmed_results": total,
        "article_count": len(articles),
        "skipped_existing": ignores_existants,
        "disclaimer": "Notices brutes : pas de revue scientifique ni de validation des licences.",
        "articles": articles,
    }
    if sortie is not None:
        path = Path(sortie)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
    return resultat


def collecte_pubmed_unidiv(country,context,sujet,email,max=50):
    nom = lambda x: re.sub(r"[^a-z0-9_-]+", "_", x.strip().lower()).strip("_")
    destination = Path("data/raw") / f"pubmed_{nom(country)}_{nom(context)}.json"

    resultat = recuperer_donnees(
        pays=country, theme=context, sujet = sujet,max_articles=max,
        sortie=destination, corpus_existant=None, email=email,
    )
    return {
        "Résultats PubMed trouvés" : resultat['total_pubmed_results'],
        "Notices récupérées" : resultat['article_count'],
        "Notices déjà présentes ignorées" : resultat['skipped_existing'],
        "output_path" : destination.resolve()
    }



