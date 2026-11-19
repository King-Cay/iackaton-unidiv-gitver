# IAckaton CHRU — UNIDIV

**Outil d'aide à la consultation médicale transculturelle fondé sur la littérature scientifique (RAG Multi-Sources & Grades HAS)**  
*Développé dans le cadre du hackathon IAckaton CHRU × TELECOM Nancy (Université de Lorraine).*

---

## Présentation

Lorsqu'un professionnel de santé français reçoit un patient originaire d'un pays donné pour une problématique ou un contexte clinique spécifique (ex. *grossesse*, *mort & deuil*, *alimentation*, *relation soignant-patient*, *génétique*…), **UNIDIV** génère automatiquement une **fiche de synthèse clinique et anthropologique sourcée**, structurée autour de **3 axes** :

1. **Déterminants individuels** : représentations personnelles de la maladie et du corps, vécu psychologique, pudeur et spiritualité du patient.
2. **Déterminants familiaux** : rôle de l'entourage, solidarité intergénérationnelle et dynamique de prise de décision médicale au sein de la famille.
3. **Déterminants structurels** : organisation du système de santé dans le pays d'origine, contexte sociopolitique et barrières d'accès aux soins.

Contrairement à un appel direct à un LLM générique, UNIDIV s'appuie exclusivement sur des **publications scientifiques réelles** collectées en temps réel, évaluées selon la **grille des niveaux de preuve de la Haute Autorité de Santé (HAS)**, filtrées par seuil de pertinence sémantique et affichées en regard de la synthèse.

---

## Fonctionnalités Clés

### 1. Pipeline RAG Scientifique Multi-Sources & Anti-Hallucination
- **Collecte parallèle sur 5 bases scientifiques ouvertes** (`ThreadPoolExecutor`, tolérant aux pannes) :
  - **PubMed** (NCBI E-utilities — biomédical & MeSH)
  - **Europe PMC** (EMBL-EBI — littérature biomédicale européenne)
  - **OpenAlex** (pluridisciplinaire : médecine, anthropologie, sociologie)
  - **Semantic Scholar** (graphe de citations scientifiques)
  - **HAL (CNRS)** (archives ouvertes francophones & sciences humaines et sociales)
- **Schéma JSON Unifié & Déduplication intelligente** : normalisation des notices et fusion des doublons (par **DOI**, **PMID**, puis **Titre normalisé**) en conservant le résumé le plus complet et le meilleur niveau de preuve.
- **Qualification automatique du Niveau de Preuve (Grades HAS : A, B, C, NC)** :
  - **Grade A (Niveau 1)** : essais comparatifs randomisés (ECR/RCT), méta-analyses.
  - **Grade B (Niveau 2)** : études de cohortes prospectives, essais comparatifs non randomisés.
  - **Grade C (Niveau 3 & Niveau 4)** : études cas-témoins (Niv. 3), études rétrospectives, séries de cas, études transversales descriptives (Niv. 4).
  - **Statut `NC` (Études qualitatives / anthropologiques)** : distinction explicite des recherches ethnographiques et phénoménologiques (hors grille quantitative ECR mais essentielles en médecine transculturelle).
- **Tri sémantique hybride & Seuil de pertinence (`nvidia/nemotron-3-embed-1b`)** :
  - Vectorisation unique du pool (`Titre + 600 premiers caractères du résumé`) mise en cache mémoire.
  - 3 requêtes sémantiques bilingues (EN/FR) spécialisées par déterminant.
  - Pondération **80 % similarité cosinus + 20 % score HAS**, avec **malus anti-redondance (`-0.15`)** pour diversifier les sources entre les 3 déterminants.
  - **Seuil minimal de pertinence (`MIN_COSINE_SIMILARITY = 0.28`)** : élimine automatiquement les articles hors-sujet même s'ils figurent dans le Top 5.
  - **Abstention méthodologique (0 % hallucination)** : si 0 article ne franchit le seuil pour un déterminant, l'appel au LLM est court-circuité au profit d'un message d'abstention explicite.
- **Génération parallèle & Nettoyage (`nvidia/nemotron-3.5-lightning-30b-a3b`)** :
  - Les 3 paragraphes sont générés en parallèle avec injection du Grade HAS dans le prompt et post-traitement automatique.
- **Cache MongoDB résilient** : persistance locale avec timeout court (`2s`) et fonctionnement dégradé transparent si le service MongoDB n'est pas démarré.

### 2. Interface Web (SPA Modulaire en 3 Vues)
- **Vue 1 — Accueil & Recherche stricte de pays** : barre de recherche avec menu déroulant d'autocomplétion priorisant les préfixes (ex. `"Co"` $\rightarrow$ *Colombie, Comores, Congo…*), navigation clavier complète et validation stricte du pays.
- **Vue 2 — Grille des 18 thèmes cliniques & anthropologiques** : *Grossesse, Parentalité, Sexualité, Vieillissement, Mort & Deuil, Alimentation, Loisirs, Religion & Spiritualité, Hygiène, Travail, Santé, Soins médicaux, Hygiène dentaire, Système de soins, Relation soignant-patient, Contexte politique, Alphabétisation, Génétique* (entièrement configurables dans `frontend/js/config/themes.js`).
- **Vue 3 — Fiche de synthèse & Panneau latéral des sources** :
  - Affichage des 3 déterminants avec bandeaux de **disclaimer automatique** lorsque la couverture documentaire est restreinte ($< 3$ sources sur un axe).
  - Panneau latéral *sticky* des sources avec **badges de provenance** (`PubMed`, `OpenAlex`, `Europe PMC`, `HAL`…), **badges colorés de Grade HAS**, filtrage par axe et résumés (*abstracts*) dépliables.
  - Bouton **« Relancer le pipeline »** (`force_refresh`) pour régénérer la synthèse et écraser l'entrée en cache MongoDB.
  - Mode Clair / Sombre, copie en 1 clic et **Export PDF / Impression** (`@media print`).

---

## Architecture du Projet

```text
iackaton-chru-unidiv/
├── main.py                                         # Orchestrateur principal du pipeline RAG
├── server.py                                       # Serveur HTTP local (sert frontend/ + API REST /api/*)
├── keys.py                                         # Clé API NVIDIA NIM (ignoré par Git)
├── requirements.txt                                # Dépendances Python épurées
├── README.md                                       # Présentation générale du projet
├── pipeline.md                                     # Description détaillée des 6 étapes du pipeline RAG
├── implementation.md                               # Documentation technique du front-end et de l'API
├── score_implementation.md                         # Spécification des Grades HAS (A, B, C, NC) bilingues
├── source_implementation.md                        # Spécification des sources scientifiques et du schéma unifié
├── roadmap.md                                      # Feuille de route et suivi des phases d'implémentation
├── test.md                                         # Documentation détaillée et audit critique des 20 tests
├── data/
│   └── raw/                                        # Corpus JSON collectés et agrégés (data/raw/aggregated_*.json)
├── src/
│   ├── config.py                                   # Configuration MongoDB, seuil cosinus, requêtes embeddings & prompts LLM
│   ├── mongo.py                                    # Lecture, écriture et suppression résilientes dans MongoDB
│   ├── compare_title_to_prompt.py                  # Embeddings, cache mémoire, score hybride (Cosinus + HAS) et seuil minimal
│   ├── ia_treatment.py                             # Appel parallèle au LLM NVIDIA NIM et nettoyage des réponses
│   └── get_doc_from_site/
│       ├── schema_unifie.py                        # Schéma JSON Unifié et évaluateur HAS bilingue (FR/EN)
│       ├── aggregateur_sources.py                  # Collecte parallèle multi-sources et déduplication/fusion (DOI/PMID/Titre)
│       ├── collecte_pubmed_unidiv.py               # Collecteur PubMed (NCBI E-utilities)
│       ├── collecte_europepmc.py                   # Collecteur Europe PMC (EMBL-EBI)
│       ├── collecte_openalex.py                    # Collecteur OpenAlex (Médecine & SHS)
│       ├── get_doc_from_semantic-scholar.py        # Collecteur Semantic Scholar (Graph API v1)
│       └── collecte_hal.py                         # Collecteur HAL / CNRS (Archives ouvertes francophones)
├── frontend/
│   ├── index.html                                  # Point d'entrée HTML5 de la SPA
│   ├── css/
│   │   ├── tokens.css                              # Design tokens (couleurs médicales, modes clair/sombre)
│   │   ├── base.css                                # Reset, animations, grille ambiante et @media print
│   │   ├── components.css                          # Topbar, autocomplete, cartes, badges HAS, stepper RAG
│   │   └── pages.css                               # Layouts des 3 vues et bandeaux de disclaimer clinique
│   └── js/
│       ├── app.js                                  # Routeur SPA (#/, #/themes/:code, #/resultats/:code/:theme)
│       ├── config/
│       │   ├── countries.js                        # Référentiel des pays (Intl.DisplayNames) + validation stricte
│       │   └── themes.js                           # Configuration déclarative des 18 boutons de thèmes
│       ├── state/
│       │   └── store.js                            # État global et cache client
│       ├── services/
│       │   └── api.js                              # Client HTTP vers /api/analyze + mode Aperçu Démo hors ligne
│       ├── components/
│       │   ├── autocomplete.js                     # Barre de recherche pays avec menu déroulant et navigation clavier
│       │   └── sourcesSidebar.js                   # Panneau latéral multi-sources avec badges HAS et filtres
│       ├── views/
│       │   ├── homeView.js                         # Vue 1 : Recherche et sélection du pays
│       │   ├── themesView.js                       # Vue 2 : Sélection du thème clinique
│       │   └── resultsView.js                      # Vue 3 : Déterminants, disclaimers, sources et actions
│       └── utils/
│           ├── dom.js                              # Protection XSS (escapeHtml), surlignage, notifications toast
│           └── icons.js                            # Icônes SVG inline sans dépendance externe
└── test_unitaires/
    ├── test_compare_title_to_prompt.py             # Tests du classement sémantique, seuil cosinus, malus et bonus HAS
    ├── test_ia_and_abstention.py                   # Tests du nettoyage LLM, du formatage HAS et de l'abstention à 0 source
    ├── test_pipeline_e2e.py                        # Test d'intégration bout-en-bout hors cache MongoDB
    ├── test_resilience_et_api.py                   # Tests de tolérance aux pannes (sources, MongoDB) et routes HTTP server.py
    ├── test_sources_collecteurs.py                 # Tests d'intégration en direct des 5 collecteurs et de l'agrégateur
    └── test_tache_b_multisources.py                # Tests du schéma unifié, du score HAS bilingue et de la déduplication
```

---

## Prérequis et Installation

### 1. Prérequis système
- **Python 3.10+**
- Une clé d'API **NVIDIA NIM** (`https://integrate.api.nvidia.com/v1`)
- **MongoDB** en local sur `mongodb://127.0.0.1:27017/` *(optionnel pour tester : si MongoDB est éteint, le pipeline s'exécute automatiquement sans cache local)*.

### 2. Installation des dépendances

```bash
python -m venv .env
# Sous Windows (PowerShell)
.\.env\Scripts\Activate.ps1
# Sous Linux / macOS
source .env/bin/activate

pip install -r requirements.txt
```

### 3. Configuration de la clé API

Créez un fichier `keys.py` à la racine du projet :

```python
API_KEY = "nvapi-votre_cle_api_ici"
```

---

## Utilisation

### 1. Lancer l'application Web complète (Front-end + API Python)

```bash
.\.env\Scripts\python.exe server.py
```

Puis ouvrez **`http://127.0.0.1:8000`** dans votre navigateur.

### 2. Utiliser le pipeline directement en Python

```python
from main import main

# Appel standard (utilise le cache MongoDB s'il existe)
resultat = main("Congo", "grieving")

# Ou forcer la régénération complète et écraser l'entrée MongoDB
resultat_frais = main("Congo", "grieving", force_refresh=True)

print(resultat["text"]["determinant_individuels"])
print(resultat["text"]["determinant_familiaux"])
print(resultat["text"]["determinant_structurels"])
```

---

## Tests Unitaires

Pour exécuter l'ensemble des tests unitaires (classement sémantique, normalisation DOI/PMID, calcul bilingue des grades HAS et déduplication multi-sources) :

```bash
.\.env\Scripts\python.exe -m pytest test_unitaires/ -v
```

---

## Documentation Technique Détaillée

- **[pipeline.md](iackaton-chru-unidiv/pipeline.md)** : Schéma Mermaid et explication pas à pas des 6 étapes menant de `(country, context)` aux 3 paragraphes.
- **[implementation.md](iackaton-chru-unidiv/implementation.md)** : Architecture du front-end SPA, du serveur `server.py` et guide pour modifier les boutons de thèmes.
- **[score_implementation.md](iackaton-chru-unidiv/score_implementation.md)** : Grille de niveau de preuve HAS (Grades A, B, C, NC) et règles de détection bilingues sur toutes les sources.
- **[source_implementation.md](iackaton-chru-unidiv/source_implementation.md)** : Catalogue des sources scientifiques, contrat du Schéma JSON Unifié et fonctionnement des collecteurs.
- **[test.md](iackaton-chru-unidiv/test.md)** : Explication complète et audit de rigueur des 20 tests unitaires et d'intégration.
- **[roadmap.md](iackaton-chru-unidiv/roadmap.md)** : Historique et statut des phases de développement du projet.
