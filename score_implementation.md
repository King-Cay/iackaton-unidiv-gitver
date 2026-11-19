# Implémentation du Score de Recommandation Scientifique (Grades HAS) sur PubMed

Ce document explique comment attribuer automatiquement à chaque article collecté via **PubMed** un **grade de recommandation scientifique (A, B, C)** et un **niveau de preuve (1 à 4)** inspirés de la grille de la **Haute Autorité de Santé (HAS)**, dans le pipeline **UNIDIV**.

---

## 1. Grille de référence retenue (Niveaux de preuve HAS)

| Grade | Qualification | Niveau | Types d'études correspondants |
| :---: | :--- | :---: | :--- |
| **A** | **Preuve scientifique établie** | **Niveau 1** | • Essais comparatifs randomisés (ECR / RCT) de forte puissance<br>• Méta-analyses d'essais comparatifs randomisés<br>• Analyses de décision fondées sur des études bien menées |
| **B** | **Présomption scientifique** | **Niveau 2** | • Essais comparatifs randomisés de faible puissance<br>• Études comparatives non randomisées bien menées<br>• Études de cohortes |
| **C** | **Faible niveau de preuve scientifique** | **Niveau 3** | • Études cas-témoins |
| **C** | **Faible niveau de preuve scientifique** | **Niveau 4** | • Études comparatives comportant des biais importants<br>• Études rétrospectives<br>• Séries de cas<br>• Études épidémiologiques descriptives (transversale, longitudinale) |

> **Nuance clinique importante pour UNIDIV (Sciences humaines & anthropologie médicale)** :  
> De nombreuses publications essentielles à la compréhension transculturelle (ex. *entretiens qualitatifs, études phénoménologiques, ethnographies*) ne sont pas des essais cliniques quantitatifs et ne relèvent donc pas des niveaux 1 à 4. Il est recommandé d'ajouter un statut explicite **`NC` (Non classé HAS — Étude qualitative / Revue narrative)** plutôt que de les déclasser silencieusement, afin que le praticien sache distinguer *méthodologie qualitative* et *faible preuve quantitative*.

---

## 2. Où extraire l'information dans les notices XML PubMed ?

Dans [collecte_pubmed_unidiv.py](file:///c:/Users/Lenovo/OneDrive/Bureau/projets/iackaton-chru-unidiv/src/get_doc_from_site/collecte_pubmed_unidiv.py), la fonction `_parser_article(article: ET.Element)` lit déjà le nœud `./MedlineCitation/Article`.

PubMed fournit nativement **deux champs structurés** dans le XML renvoyé par `efetch.fcgi` :

1. **`PublicationTypeList` (le signal le plus fiable)**  
   Chemin XML : `./MedlineCitation/Article/PublicationTypeList/PublicationType`  
   Exemples de valeurs officielles NLM :
   - `"Meta-Analysis"`, `"Randomized Controlled Trial"`, `"Systematic Review"`
   - `"Controlled Clinical Trial"`, `"Clinical Trial"`, `"Comparative Study"`
   - `"Observational Study"`, `"Multicenter Study"`, `"Case Reports"`
2. **`MeshHeadingList` (descripteurs de méthodologie)**  
   Chemin XML : `./MedlineCitation/MeshHeadingList/MeshHeading/DescriptorName`  
   Exemples de descripteurs MeSH :
   - `"Cohort Studies"`, `"Prospective Studies"`, `"Longitudinal Studies"`
   - `"Case-Control Studies"`, `"Retrospective Studies"`, `"Cross-Sectional Studies"`
   - `"Qualitative Research"`
3. **Titre & Abstract (repli par expressions régulières)**  
   Utile lorsque les métadonnées MeSH ne sont pas encore indexées (articles très récents / pré-MEDLINE).

---

## 3. Correspondance PubMed → Grade HAS

### Règles de classification suggérées (par ordre de priorité décroissant)

1. **Grade A · Niveau 1**
   - `PublicationType` contient : `Meta-Analysis`, `Randomized Controlled Trial`, `Network Meta-Analysis`
   - *Note sur la puissance* : sans lecture du texte intégral (calcul de puissance *a priori*), PubMed ne distingue pas directement « forte » vs « faible » puissance. On peut utiliser comme heuristique complémentaire la présence d'un large échantillon (`n >= 200` ou `Multicenter Study` dans `PublicationType` / `Abstract`) pour confirmer le **Niveau 1**, sinon signaler « ECR — puissance non vérifiée automatiquement » ou classer en **B (Niveau 2)** par prudence.
2. **Grade B · Niveau 2**
   - `PublicationType` contient : `Controlled Clinical Trial`, `Clinical Trial`, `Comparative Study`, `Pragmatic Clinical Trial`
   - Ou `MeSH` contient : `Cohort Studies`, `Prospective Studies`, `Follow-Up Studies`
   - Ou titre/abstract mentionne explicitement `cohort study`, `non-randomized comparative`, `quasi-experimental`.
3. **Grade C · Niveau 3**
   - `MeSH` contient : `Case-Control Studies`
   - Ou titre/abstract mentionne `case-control`.
4. **Grade C · Niveau 4**
   - `PublicationType` contient : `Case Reports`, `Observational Study` (sans cohorte/cas-témoin identifié)
   - Ou `MeSH` contient : `Retrospective Studies`, `Cross-Sectional Studies`, `Longitudinal Studies`, `Epidemiologic Studies`
   - Ou titre/abstract mentionne `retrospective`, `case series`, `cross-sectional`, `descriptive study`.
5. **Non classé HAS (`NC`) — Littérature qualitative / conceptuelle**
   - `MeSH` contient `Qualitative Research` ou `Anthropology, Cultural`, ou titre/abstract mentionne `qualitative`, `phenomenological`, `ethnographic`, `thematic analysis`.

---

## 4. Implémentation Python prête à intégrer dans `collecte_pubmed_unidiv.py`

### Étape 1 : Ajouter une fonction dédiée `_evaluer_grade_has(...)`

```python
def _evaluer_grade_has(
    pub_types: list[str],
    mesh_terms: list[str],
    title: str,
    abstract: str,
) -> dict:
    """Attribuer un grade HAS indicatif (A/B/C ou NC) depuis les métadonnées PubMed."""
    pt_lower = {p.lower() for p in pub_types}
    mesh_lower = {m.lower() for m in mesh_terms}
    text = f"{title} {abstract}".lower()

    # 1. Grade A — Niveau 1
    if "meta-analysis" in pt_lower or "randomized controlled trial" in pt_lower:
        # Heuristique simple de prudence sur la taille/multicentrique
        est_multicentrique = "multicenter study" in pt_lower or "multicenter" in text
        return {
            "grade": "A",
            "niveau_preuve": 1,
            "score_numerique": 100,
            "label": "Preuve scientifique établie (Niveau 1)",
            "methode_detectee": ", ".join(pub_types) or "ECR / Méta-analyse",
            "note_prudence": None if est_multicentrique else "Puissance statistique à confirmer dans le texte intégral.",
        }

    # 2. Grade B — Niveau 2
    if (
        pt_lower & {"controlled clinical trial", "clinical trial", "comparative study"}
        or mesh_lower & {"cohort studies", "prospective studies", "follow-up studies"}
        or re.search(r"\b(cohort study|non-randomized|quasi-experimental)\b", text)
    ):
        return {
            "grade": "B",
            "niveau_preuve": 2,
            "score_numerique": 75,
            "label": "Présomption scientifique (Niveau 2)",
            "methode_detectee": ", ".join(pub_types or mesh_terms) or "Cohorte / Étude comparative",
            "note_prudence": None,
        }

    # 3. Grade C — Niveau 3 (Cas-témoins)
    if "case-control studies" in mesh_lower or re.search(r"\bcase[- ]control\b", text):
        return {
            "grade": "C",
            "niveau_preuve": 3,
            "score_numerique": 50,
            "label": "Faible niveau de preuve scientifique (Niveau 3)",
            "methode_detectee": "Étude cas-témoins",
            "note_prudence": None,
        }

    # 4. Grade C — Niveau 4 (Rétrospectives, séries de cas, descriptives)
    if (
        pt_lower & {"case reports", "observational study"}
        or mesh_lower & {"retrospective studies", "cross-sectional studies", "longitudinal studies"}
        or re.search(r"\b(retrospective|case series|cross[- ]sectional|descriptive study|prevalence)\b", text)
    ):
        return {
            "grade": "C",
            "niveau_preuve": 4,
            "score_numerique": 35,
            "label": "Faible niveau de preuve scientifique (Niveau 4)",
            "methode_detectee": ", ".join(pub_types) or "Étude descriptive / rétrospective",
            "note_prudence": None,
        }

    # 5. Études qualitatives / anthropologiques (pertinentes en contexte transculturel)
    if (
        "qualitative research" in mesh_lower
        or re.search(r"\b(qualitative|phenomenological|ethnograph|thematic analysis|interviews)\b", text)
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
        "methode_detectee": ", ".join(pub_types) if pub_types else "Non spécifié",
        "note_prudence": "Vérification méthodologique manuelle recommandée.",
    }
```

### Étape 2 : Extraire `PublicationType` et `MeshHeading` dans `_parser_article()`

Dans `_parser_article(article: ET.Element)` :

```python
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

    evaluation_has = _evaluer_grade_has(pub_types, mesh_terms, title, resume)
```

Puis inclure ces champs dans le dictionnaire retourné par `_parser_article` :

```python
        "publication_types": pub_types,
        "mesh_terms": mesh_terms,
        "recommendation_score": evaluation_has,
```

---

## 5. Exploitation dans le pipeline RAG et le Front-end

1. **Classement / Pondération dans `main.py`** :
   - Après le filtrage sémantique (`compare_titles_to_prompt`), vous pouvez combiner la **similarité cosinus** et le **`score_numerique` HAS** (ex. `score_final = 0.75 * sim_cosinus + 0.25 * (score_numerique / 100)`) pour privilégier les méta-analyses ou cohortes à pertinence égale.
2. **Transmission au LLM dans `src/ia_treatment.py`** :
   - Formater chaque source avec son grade (`--- ARTICLE 1 [Grade A - Niveau 1] ---`) afin que le LLM nuance automatiquement son propos selon la solidité de la preuve.
3. **Affichage dans le panneau latéral (`frontend/js/components/sourcesSidebar.js`)** :
   - Lire `article.recommendation_score` pour afficher une pastille colorée :
     - **Grade A** : vert (`#059669`)
     - **Grade B** : bleu (`#2563eb`)
     - **Grade C** : ambre (`#d97706`)
     - **NC (Qualitatif)** : violet/indigo (`#4f46e5`)
   - Afficher au survol ou en sous-titre `label` et `methode_detectee`.

---

## 6. Extension du Système de Score aux Nouvelles Sources (Europe PMC, OpenAlex, Semantic Scholar, HAL)

Contrairement à PubMed, les autres bases de données scientifiques n'utilisent pas toutes le format XML MEDLINE. Pourtant, nous voulons que **chaque article, quelle que soit sa bibliothèque d'origine**, reçoive exactement le même objet `recommendation_score` (Grades HAS **A, B, C ou NC**) pour pouvoir être comparé équitablement.

Pour y parvenir, le calcul du score est centralisé dans une fonction universelle (`evaluer_grade_has` dans `src/get_doc_from_site/schema_unifie.py`) qui s'appuie sur **3 couches complémentaires** :

---

### Couche 1 : Extraction des métadonnées natives propres à chaque API

Chaque API de Niveau 1 fournit ses propres champs de qualification méthodologique. Chaque collecteur traduit ces champs vers nos deux listes standards `pub_types` et `mesh_terms` avant d'appeler l'évaluateur HAS :

| Source | Champs natifs fournis par l'API | Comment on les convertit pour le score HAS |
| :--- | :--- | :--- |
| **Europe PMC** | `pubTypeList.pubType` et `meshHeadingList.meshHeading` (avec `resultType=core`) | Identique à PubMed : contient directement `"Randomized Controlled Trial"`, `"Meta-Analysis"`, `"Cohort Studies"`, `"Case Reports"`, etc. |
| **OpenAlex** | `type`, `mesh` (descripteurs MeSH intégrés !), `concepts` / `topics` | • `work["mesh"]` fournit les descripteurs MeSH (`descriptor_name`) quand l'article est biomédical.<br>• `work["concepts"]` et `work["topics"]` contiennent des étiquettes comme `"Randomized controlled trial"`, `"Meta-analysis"`, `"Cohort study"`, `"Qualitative research"`. |
| **Semantic Scholar** | `publicationTypes`, `fieldsOfStudy` | `publicationTypes` renvoie des étiquettes normalisées que l'on mappe directement :<br>• `"MetaAnalysis"` $\rightarrow$ `"Meta-Analysis"` (Grade A)<br>• `"ClinicalTrial"` $\rightarrow$ `"Clinical Trial"` (Grade A/B selon randomisation)<br>• `"CaseReport"` $\rightarrow$ `"Case Reports"` (Grade C - Niveau 4)<br>• `"Review"` $\rightarrow$ `"Systematic Review"` ou revue narrative. |
| **HAL (CNRS)** | `docType_s`, `keyword_s`, `peerReviewing_s` | • `keyword_s` (mots-clés auteur) est injecté dans `mesh_terms`.<br>• `docType_s` indique le type de publication (`"ART"` = article de revue, `"THESE"` = thèse, `"REPORT"` = rapport). |

---

### Couche 2 : Détection méthodologique bilingue (Anglais + Français) dans le Titre et le Résumé

Dans les bases pluridisciplinaires ou francophones (comme **HAL** ou **OpenAlex**), un article peut être une étude de cohorte ou une étude cas-témoins sans avoir d'étiquette MeSH en anglais.

L'évaluateur universel analyse donc le couple `(title + abstract)` avec des **expressions régulières bilingues (EN + FR)** en respectant strictement la hiérarchie HAS :

1. **Grade A · Niveau 1 (`score_numerique = 100`)**
   - **Anglais** : `randomized controlled trial`, `randomised controlled trial`, `meta-analysis`, `systematic review and meta-analysis`, `network meta-analysis`.
   - **Français** : `essai comparatif randomisé`, `essai contrôlé randomisé`, `essai clinique randomisé`, `méta-analyse`, `revue systématique et méta-analyse`.

2. **Grade B · Niveau 2 (`score_numerique = 75`)**
   - **Anglais** : `cohort study`, `prospective cohort`, `prospective study`, `non-randomized comparative`, `controlled clinical trial`, `quasi-experimental`.
   - **Français** : `étude de cohorte`, `cohorte prospective`, `étude prospective`, `essai comparatif non randomisé`, `étude comparative non randomisée`, `étude quasi-expérimentale`.

3. **Grade C · Niveau 3 (`score_numerique = 50`)**
   - **Anglais** : `case-control study`, `case control study`, `nested case-control`.
   - **Français** : `étude cas-témoins`, `étude cas témoins`, `cas-témoin`.

4. **Grade C · Niveau 4 (`score_numerique = 35`)**
   - **Anglais** : `retrospective study`, `case series`, `case report`, `cross-sectional study`, `descriptive study`, `longitudinal survey`.
   - **Français** : `étude rétrospective`, `série de cas`, `cas clinique`, `étude transversale`, `étude épidémiologique descriptive`, `enquête transversale`.

5. **Qualitatif / Sciences Humaines (`grade = "NC"`, `score_numerique = 45`)**
   - **Anglais** : `qualitative study`, `phenomenological`, `ethnographic`, `ethnography`, `thematic analysis`, `semi-structured interviews`, `focus group`.
   - **Français** : `étude qualitative`, `recherche qualitative`, `approche phénoménologique`, `étude ethnographique`, `ethnographie`, `entretiens semi-directifs`, `analyse thématique`, `anthropologie médicale`.

---

### Couche 3 : Conservation du meilleur score lors de la Déduplication

Lorsqu'un même article est trouvé dans plusieurs bibliothèques simultanément (par exemple **PubMed** + **OpenAlex** + **Semantic Scholar**) :
1. Chaque collecteur calcule d'abord un `recommendation_score` avec les informations dont il dispose.
2. Au moment de la **déduplication** (par DOI, PMID ou titre), l'agrégateur compare les fiches doublons et **conserve le `recommendation_score` le plus précis** (priorité au grade établi A/B/C ayant le `score_numerique` le plus élevé et les `mesh_terms` / `publication_types` les plus complets).
3. Ainsi, un article trouvé sur OpenAlex bénéficie automatiquement de la précision des descripteurs MeSH s'il est également présent dans PubMed ou Europe PMC.

