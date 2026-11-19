# Sources Scientifiques Pertinentes & Guide d'Implémentation Multi-Sources

Ce document recense les **sources de données scientifiquement crédibles et complémentaires à PubMed** pour enrichir l'analyse clinique et anthropologique du projet **UNIDIV**, ainsi que la manière de les intégrer proprement dans `src/get_doc_from_site/`.

---

## 1. Pourquoi diversifier au-delà de PubMed ?

PubMed est incontournable pour la **médecine clinique, la psychiatrie et la santé publique**, mais il présente deux angles morts majeurs pour la consultation transculturelle :
1. **Sous-représentation des sciences humaines et sociales (SHS)** : l'anthropologie médicale, la sociologie de la santé, les rites funéraires ou la relation soignant-patient sont souvent publiés dans des revues SHS non indexées sur MEDLINE.
2. **Biais anglophone** : de nombreuses recommandations cliniques adaptées au contexte hospitalier français (ex. parcours des exilés, interprétariat, droit à la santé) sont en français.

---

## 2. Catalogue des sources pertinentes et crédibles

### Niveau 1 — Sources avec API ouverte et structurée (implémentation directe)

#### A. **Europe PMC** *(Biomédical & Santé Publique — Open Access)* — ✅ **Implémenté (`collecte_europepmc.py`)**
- **Crédibilité** : gérée par l'EMBL-EBI (European Bioinformatics Institute). Agrège PubMed, PMC, Agricola, et des préprints évalués, avec accès fréquent au texte intégral en XML/JSON.
- **Pertinence UNIDIV** : meilleure couverture européenne et francophone que PubMed seul, métadonnées complètes (`resultType=core` : `meshHeadingList`, `pubTypeList`, `keywordList`, `isOpenAccess`).
- **API** : REST JSON gratuite (`GET https://www.ebi.ac.uk/europepmc/webservices/rest/search`).

#### B. **OpenAlex** *(Pluridisciplinaire : Médecine + Anthropologie + Sociologie)* — ✅ **Implémenté (`collecte_openalex.py`)**
- **Crédibilité** : index bibliographique ouvert de référence (successeur de Microsoft Academic Graph), utilisé par le CNRS et de nombreuses universités.
- **Pertinence UNIDIV** : couvre à la fois les sciences biomédicales **et** les sciences humaines (anthropologie, géopolitique, alphabétisation, travail), avec descripteurs `mesh`, `concepts` et `topics`.
- **API** : REST JSON gratuite (`https://api.openalex.org/works`), filtrage local des résumés reconstruits depuis `abstract_inverted_index` pour préserver le quota gratuit.

#### C. **Semantic Scholar** *(Graphe scientifique)* — ✅ **Implémenté (`get_doc_from_semantic-scholar.py`)**
- **Crédibilité** : développé par l'Allen Institute for AI ; relie les publications par graphe de citations.
- **Pertinence UNIDIV** : utile pour trouver des articles transversaux (`health literacy`, `medical anthropology`, `cultural competence`) avec qualification `publicationTypes` (`MetaAnalysis`, `ClinicalTrial`, `CaseReport`, `Review`).
- **API** : `https://api.semanticscholar.org/graph/v1/paper/search/bulk` avec contrôleur de débit local thread-safe (`2,2 s` entre requêtes + backoff exponentiel).

#### D. **HAL (Hyper Articles en Ligne / CNRS)** *(Recherche francophone SHS & Santé)* — ✅ **Implémenté (`collecte_hal.py`)**
- **Crédibilité** : archive ouverte nationale du CNRS et des universités françaises (HAL).
- **Pertinence UNIDIV** : mine d'or d'articles d'anthropologie médicale, de sociologie de la migration et de thèses françaises.
- **API** : API REST Solr pour HAL (`https://api.archives-ouvertes.fr/search/?wt=json`), zéro clé requise.

---

### Niveau 2 — Référentiels institutionnels & cliniques spécialisés (très forte autorité)

#### E. **OMS / WHO — TMGL (Traditional Medicine Global Library) & IRIS**
- **Crédibilité** : Organisation Mondiale de la Santé (référentiel international).
- **Pertinence UNIDIV** : pratiques médicales traditionnelles, médecines complémentaires, systèmes de santé par pays (`WHO IRIS` : `https://iris.who.int/`).
- **Implémentation** : API OAI-PMH / DSpace REST d'IRIS ou constitution d'un corpus local indexé par pays/thème.

#### F. **COMEDE (Comité pour la santé des exilés) & Centre Primo Lévi**
- **Crédibilité** : références cliniques françaises pour la prise en charge médico-psycho-sociale des personnes exilées et victimes de violences politiques.
- **Pertinence UNIDIV** : indispensable pour les thèmes *Contexte politique*, *Mort & Deuil*, *Relation soignant-patient*, *Système de soins*.
- **Implémentation** : indexation d'un corpus de guides/fiches PDF officielles (avec respect des droits et citation de l'URL source) dans une collection MongoDB dédiée ou via recherche locale par embeddings.

#### G. **Orphanet & Institut Pasteur**
- **Crédibilité** : autorités de référence sur les maladies rares/génétiques (INSERM) et les maladies infectieuses.
- **Pertinence UNIDIV** : ciblent précisément les thèmes *Génétique* (prévalences géographiques, drépanocytose, thalassémies) et *Hygiène* / *Soins médicaux*.
- **Implémentation** : API / fichiers XML ouverts d'Orphadata (`https://www.orphadata.com/`) pour croiser pays/région et pathologies génétiques.

#### H. **Cairn.info & JSTOR (via accès institutionnel / métadonnées Crossref)**
- **Crédibilité** : revues académiques majeures en psychologie transculturelle, anthropologie et santé publique (ex. *Rhizome*, *L'Autre*, *Sciences Sociales et Santé*).
- **Contrainte technique** : pas d'API ouverte libre sur le texte intégral payant ; utiliser **Crossref** (`https://api.crossref.org/works`) ou les flux OAI-PMH pour récupérer métadonnées + résumés ouverts.

---

## 3. Schéma JSON unifié (Contrat entre collecteurs et pipeline)

Pour que `main.py`, `compare_title_to_prompt.py`, `ia_treatment.py` et le panneau latéral du front-end (`sourcesSidebar.js`) fonctionnent de manière transparente avec **n'importe quelle source**, chaque collecteur doit retourner la même structure d'article :

```json
{
  "document_id": "OPENALEX_W29481234",
  "source": "OpenAlex",
  "pmid": null,
  "doi": "10.1016/j.socscimed.2024.116842",
  "title": "Titre de l'article",
  "abstract": "Résumé complet utilisé par le LLM...",
  "authors": ["Auteur 1", "Auteur 2"],
  "journal": "Nom de la revue ou de l'institution",
  "publication_year": 2025,
  "language": "fr",
  "url": "https://doi.org/10.1016/j.socscimed.2024.116842",
  "publication_types": ["Review"],
  "recommendation_score": {
    "grade": "B",
    "niveau_preuve": 2,
    "score_numerique": 75,
    "label": "Présomption scientifique (Niveau 2)"
  }
}
```

> Le front-end ([sourcesSidebar.js](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/frontend/js/components/sourcesSidebar.js)) lit déjà `source`, `url`, `pmid`, `doi`, `document_id`, `title`, `abstract`, `authors`, `journal` et `publication_year` de façon totalement agnostique.

---

## 4. Exemple d'implémentation modulaire dans `src/get_doc_from_site/`

### 4.1 Collecteur OpenAlex (`src/get_doc_from_site/collecte_openalex.py`)

OpenAlex permet de chercher à la fois en médecine et en anthropologie en une seule requête REST :

```python
import requests

OPENALEX_URL = "https://api.openalex.org/works"

def _reconstruire_abstract(inverted_index: dict | None) -> str:
    """OpenAlex stocke les résumés sous forme d'index inversé {mot: [positions]}."""
    if not inverted_index:
        return ""
    taille = max(pos for positions in inverted_index.values() for pos in positions) + 1
    mots = [""] * taille
    for mot, positions in inverted_index.items():
        for pos in positions:
            mots[pos] = mot
    return " ".join(mots)

def collecte_openalex(country: str, context: str, max_articles: int = 25) -> list[dict]:
    params = {
        "search": f"{country} {context}",
        "filter": "has_abstract:true",
        "per-page": max_articles,
        "sort": "relevance_score:desc",
    }
    resp = requests.get(OPENALEX_URL, params=params, timeout=20)
    resp.raise_for_status()
    results = []

    for work in resp.json().get("results", []):
        abstract = _reconstruire_abstract(work.get("abstract_inverted_index"))
        if not abstract:
            continue
        doi_raw = work.get("doi") or ""
        doi = doi_raw.replace("https://doi.org/", "") or None
        source_info = (work.get("primary_location") or {}).get("source") or {}

        results.append({
            "document_id": f"OPENALEX_{work['id'].split('/')[-1]}",
            "source": "OpenAlex",
            "pmid": (work.get("ids") or {}).get("pmid"),
            "doi": doi,
            "title": work.get("title") or "",
            "abstract": abstract,
            "authors": [
                a["author"]["display_name"]
                for a in work.get("authorships", [])[:10]
                if a.get("author", {}).get("display_name")
            ],
            "journal": source_info.get("display_name") or "OpenAlex",
            "publication_year": work.get("publication_year"),
            "language": work.get("language"),
            "url": work.get("doi") or work.get("id"),
        })
    return results
```

### 4.2 Collecteur HAL (`src/get_doc_from_site/collecte_hal.py`) — Sources francophones & SHS

```python
import requests

HAL_URL = "https://api.archives-ouvertes.fr/search/"

def collecte_hal(country_fr: str, theme_fr: str, max_articles: int = 20) -> list[dict]:
    params = {
        "q": f'"{country_fr}" AND "{theme_fr}"',
        "fq": "abstract_s:*",
        "fl": "docid,title_s,abstract_s,authFullName_s,journalTitle_s,publicationDateY_i,uri_s,doiId_s,language_s",
        "rows": max_articles,
        "wt": "json",
    }
    resp = requests.get(HAL_URL, params=params, timeout=20)
    resp.raise_for_status()
    docs = resp.json().get("response", {}).get("docs", [])

    results = []
    for d in docs:
        abstracts = d.get("abstract_s") or []
        titles = d.get("title_s") or []
        if not abstracts or not titles:
            continue
        results.append({
            "document_id": f"HAL_{d['docid']}",
            "source": "HAL (CNRS)",
            "pmid": None,
            "doi": d.get("doiId_s"),
            "title": titles[0],
            "abstract": abstracts[0],
            "authors": d.get("authFullName_s") or [],
            "journal": d.get("journalTitle_s") or "Archive ouverte HAL",
            "publication_year": d.get("publicationDateY_i"),
            "language": (d.get("language_s") or ["fr"])[0],
            "url": d.get("uri_s"),
        })
    return results
```

### 4.3 Agrégateur multi-sources avec déduplication (à appeler depuis `main.py`)

Dans `main.py`, au lieu d'interroger uniquement `collecte_pubmed_unidiv`, créez une fonction `collecter_toutes_sources(country, context)` qui :
1. Appelle en parallèle (`concurrent.futures.ThreadPoolExecutor`) :
   - `collecte_pubmed_unidiv` (biomédical)
   - `collecte_openalex` (pluridisciplinaire)
   - `collecte_hal` (SHS & médecine francophone)
   - `collecte_semantic_scholar` (graphe de citations)
2. **Déduplique** les articles sur la base du **DOI normalisé** (ou du titre en minuscules si pas de DOI), afin qu'un même article présent à la fois dans PubMed et OpenAlex ne soit pas compté deux fois.
3. Passe la liste fusionnée à `compare_titles_to_prompt(...)`, puis enrichit chaque article avec son score de recommandation (voir [score_implementation.md](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/score_implementation.md)).
