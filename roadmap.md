# Feuille de Route (Roadmap) — Évolution du Pipeline RAG UNIDIV

Ce document détaille le plan d'exécution en deux phases (**Tâche A** puis **Tâche B**, avec point d'arrêt et validation utilisateur entre les deux) conformément aux spécifications de [score_implementation.md](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/score_implementation.md) et [source_implementation.md](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/source_implementation.md).

---

## Vue d'ensemble du déroulement (Statut : 100 % Terminé ✅)

1. ✅ **Rédaction de la feuille de route (`roadmap.md`)**
2. ✅ **Exécution de la Tâche A** : Implémentation du score de recommandation scientifique (Grades HAS : A, B, C, NC) et exploitation de bout en bout (Collecte → Classement RAG → Prompt LLM → Front-end).
3. ✅ **PAUSE & Revue utilisateur** : Validation de la Tâche A et de l'architecture d'agrégation.
4. ✅ **Exécution de la Tâche B** : Schéma JSON unifié (`schema_unifie.py`), implémentation des collecteurs de Niveau 1 à API ouverte (`PubMed`, `Europe PMC`, `OpenAlex`, `Semantic Scholar`, `HAL`) et agrégateur multi-sources avec déduplication (`aggregateur_sources.py`).
5. ✅ **Phase 3 — Optimisations RAG, Abstention & Disclaimers** :
   - Collecte multi-sources unique hors de la boucle des déterminants + vectorisation sur `Titre + Résumé` avec cache mémoire.
   - 3 requêtes sémantiques bilingues spécialisées + malus anti-redondance (`-0.15`).
   - Seuil minimal de similarité cosinus (`MIN_COSINE_SIMILARITY = 0.28`), abstention anti-hallucination à 0 source, génération parallèle des 3 déterminants (`ThreadPoolExecutor`), résilience MongoDB (`2s` timeout) et bandeaux de disclaimer clinique côté front-end.
6. ✅ **Phase 4 — Suite de 20 Tests Unitaires / Intégration & Audit Critique ([test.md](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/test.md))** :
   - Vérification en direct des 5 collecteurs 100 % natifs (sans repli tiers déguisé), tests de résilience, d'API HTTP, d'abstention et de bout-en-bout (`20 passed`).

---

## Phase 1 — TÂCHE A : Score de Recommandation HAS & Exploitation RAG / Front-end

### A.1. Calcul du grade HAS lors de la collecte (`src/get_doc_from_site/collecte_pubmed_unidiv.py`)
- Extraction des balises XML natives dans `_parser_article()` :
  - `./PublicationTypeList/PublicationType` (`pub_types`)
  - `./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName` (`mesh_terms`)
- Implémentation de la fonction d'évaluation `_evaluer_grade_has(pub_types, mesh_terms, title, abstract)` :
  - **Grade A (Niveau 1 — score 100)** : Essais comparatifs randomisés (ECR / RCT), méta-analyses d'ECR.
  - **Grade B (Niveau 2 — score 75)** : Essais cliniques contrôlés non randomisés, études comparatives bien menées, études de cohortes / prospectives.
  - **Grade C (Niveau 3 — score 50)** : Études cas-témoins (`case-control`).
  - **Grade C (Niveau 4 — score 35)** : Études rétrospectives, séries de cas, études descriptives / transversales (`cross-sectional`).
  - **Statut `NC` (Étude qualitative — score 45 ou Non déterminé — score 20)** : Recherche qualitative, phénoménologique ou anthropologique (essentielle en médecine transculturelle mais hors grille quantitative ECR).
- Enrichissement du dictionnaire de chaque notice avec `publication_types`, `mesh_terms` et l'objet `recommendation_score` :
  ```json
  "recommendation_score": {
    "grade": "A | B | C | NC",
    "niveau_preuve": 1,
    "score_numerique": 100,
    "label": "Preuve scientifique établie (Niveau 1)",
    "methode_detectee": "Randomized Controlled Trial",
    "note_prudence": "..."
  }
  ```

### A.2. Exploitation dans le classement sémantique (`src/compare_title_to_prompt.py` & `main.py`)
- Ajout d'un paramètre optionnel `articles_scores: list[float] | None = None` à `compare_titles_to_prompt()` (rétrocompatible à 100 % avec les tests unitaires existants qui passent uniquement `prompt` et `titles`).
- Lorsque les scores de recommandation sont fournis, pondération hybride pour départager les articles à pertinence sémantique proche :
  $$\text{Score final} = 0.80 \times \text{Similarité Cosinus} + 0.20 \times \left(\frac{\text{score\_numerique}}{100}\right)$$

### A.3. Exploitation dans le prompt envoyé au LLM (`src/ia_treatment.py` & `main.py`)
- Possibilité de transmettre à `ia_treatment()` soit une liste de textes bruts (compatibilité ascendante), soit une liste de dictionnaires d'articles (ou résumés annotés) contenant le grade HAS.
- Formatage enrichi de chaque source injectée dans le prompt :
  `--- ARTICLE 1 [Grade HAS : B (Niveau 2) — Présomption scientifique | Méthode : Cohort Studies] ---`
- Ainsi, le LLM peut appuyer prioritairement ses affirmations cliniques sur les preuves les plus robustes tout en valorisant les études qualitatives pour le vécu culturel.

### A.4. Affichage visuel dans le Front-end (`frontend/js/components/sourcesSidebar.js` & `frontend/css/components.css`)
- Ajout d'un badge de fiabilité coloré sur chaque carte de source dans le panneau latéral :
  - **Grade A · Niv. 1** : badge vert émeraude
  - **Grade B · Niv. 2** : badge bleu saphir
  - **Grade C · Niv. 3/4** : badge ambre
  - **Qualitatif / NC** : badge indigo / neutre
- Affichage de la qualification HAS (`label`) et de la méthodologie détectée (`methode_detectee`) sur chaque carte de référence, ainsi que mise à jour des données de démonstration dans `frontend/js/services/api.js`.

> **POINT D'ARRÊT** : Fin de la Tâche A. Attente de votre inspection et de votre feu vert (« GO »).

---

## Phase 2 — TÂCHE B : Sources Niveau 1, Schéma Unifié & Agrégateur Multi-Sources *(Après votre GO)*

### B.1. Schéma JSON unifié & Evaluateur de grade partagé (`src/get_doc_from_site/schema_unifie.py`)
- Factorisation de la fonction de normalisation d'article et d'évaluation du grade HAS pour que **toutes les sources** (PubMed, Europe PMC, OpenAlex, Semantic Scholar, HAL) produisent exactement le même contrat JSON avec `recommendation_score`.

### B.2. Implémentation des collecteurs de Niveau 1 (APIs ouvertes sans clé bloquante)
1. **PubMed** (`src/get_doc_from_site/collecte_pubmed_unidiv.py`) — aligné sur le schéma unifié.
2. **Europe PMC** (`src/get_doc_from_site/collecte_europepmc.py`) — API REST EMBL-EBI (`https://www.ebi.ac.uk/europepmc/webservices/rest/search`).
3. **OpenAlex** (`src/get_doc_from_site/collecte_openalex.py`) — API REST (`https://api.openalex.org/works`) avec reconstruction de l'abstract depuis l'index inversé.
4. **Semantic Scholar** (`src/get_doc_from_site/get_doc_from_semantic-scholar.py`) — API Graph v1 (`https://api.semanticscholar.org/graph/v1/paper/search`) avec gestion gracieuse du rate-limit.
5. **HAL / CNRS** (`src/get_doc_from_site/collecte_hal.py`) — API ouverte (`https://api.archives-ouvertes.fr/search/`) pour la littérature francophone et SHS.

### B.3. Agrégateur Multi-Sources & Déduplication (`src/get_doc_from_site/aggregateur_sources.py` & `main.py`)
- Exécution parallèle (`ThreadPoolExecutor`) des collecteurs avec tolérance aux pannes (si une API externe est lente ou indisponible, les autres sources continuent sans bloquer le pipeline).
- Déduplication intelligente par **DOI normalisé**, **PMID**, puis **titre normalisé** (en fusionnant les métadonnées les plus riches).
- Sauvegarde du corpus agrégé dans `data/raw/aggregated_<country>_<context>.json` et branchement dans `main.py`.
