# Documentation d'implémentation — Front-end & API UNIDIV

Ce document décrit l'architecture complète, les choix techniques et le fonctionnement du front-end développé pour le projet **IAckaton CHRU — UNIDIV**, ainsi que le serveur HTTP local permettant de le relier directement au pipeline Python (`main.py`).

---

## 1. Vue d'ensemble des 3 écrans

L'application fonctionne comme une **Single Page Application (SPA)** découpée en 3 vues successives reliées par un routage par hash (`#/`, `#/themes/:code`, `#/resultats/:code/:themeId`) :

1. **Page d'accueil (`#/`) — Recherche & validation stricte du pays**
   - Barre de recherche centrale avec menu déroulant d'autocomplétion dynamique.
   - Priorisation des correspondances par préfixe (ex. saisir `"Co"` affiche en priorité *Colombie*, *Comores*, *Congo*, *Congo (RDC)*, *Corée du Nord*, *Corée du Sud*, *Costa Rica*, *Côte d'Ivoire*), avec surlignage des lettres saisies et insensibilité aux accents et à la casse.
   - Navigation complète au clavier (`Flèche Haut`, `Flèche Bas`, `Entrée`, `Échap`).
   - **Validation stricte** : le bouton *Rechercher* reste désactivé tant que le texte saisi ne correspond pas exactement à un pays reconnu dans le référentiel officiel.
   - Raccourcis de sélection rapide et rappel visuel des 3 axes d'analyse clinique.

2. **Page de sélection des thèmes (`#/themes/:code`)**
   - Affiche une bannière récapitulative du pays sélectionné (code ISO, nom français, nom anglais envoyé à PubMed) avec un bouton pour changer de pays.
   - Affiche les **18 boutons de thèmes** demandés :
     *Grossesse*, *Parentalité*, *Sexualité*, *Vieillissement*, *Mort & Deuil*, *Alimentation*, *Loisirs*, *Religion & Spiritualité*, *Hygiène*, *Travail*, *Santé*, *Soins médicaux*, *Hygiène dentaire*, *Système de soins*, *Relation soignant-patient*, *Contexte politique*, *Alphabétisation*, *Génétique*.
   - Inclut des onglets de filtrage par catégorie (*Tous*, *Cycle de vie*, *Santé & Soins*, *Société & Culture*) et un champ de recherche instantanée.

3. **Page de synthèse clinique & sources (`#/resultats/:code/:themeId`)**
   - **Stepper de chargement animé** pendant l'interrogation du pipeline RAG (cache MongoDB → collecte multi-sources → NVIDIA Nemotron Embed → NVIDIA Nemotron LLM).
   - **Bandeaux de Disclaimer Clinique à 2 niveaux** :
     - *Bandeau global* : alerte le praticien lorsque le nombre total de publications ayant franchi le seuil de pertinence sémantique (`MIN_COSINE_SIMILARITY = 0.28`) est restreint ($< 5$ sources uniques) ou nul (0 source $\rightarrow$ abstention méthodologique sans appel LLM).
     - *Bandeau par déterminant* : signale sur la carte concernée lorsqu'un axe repose sur seulement 1 ou 2 publications pertinentes.
   - **Colonne principale (gauche)** : affichage structuré des **3 déterminants** (*Déterminants individuels*, *Déterminants familiaux*, *Déterminants structurels*) avec encadré d'éthique clinique, nettoyage automatique des phrases d'introduction (`cleanDeterminantText`) et compteur de sources sur chaque bouton (`Voir ses sources (N) →`).
   - **Panneau latéral sticky (droite)** : affichage des **sources scientifiques** de façon agnostique vis-à-vis de la base d'origine (`article.source` : PubMed, Europe PMC, OpenAlex, Semantic Scholar, HAL, etc.), avec **badge coloré de Grade HAS** (`Grade A · Niv. 1`, `Grade B · Niv. 2`, `Grade C · Niv. 3/4`, `Qualitatif (NC)`), méthodologie détectée, identifiant PMID/DOI/`document_id`, lien externe `article.url`, année, revue, auteurs, axe(s) associé(s) et bouton *Résumé* pour déplier l'abstract.
   - Filtrage croisé : les onglets du panneau latéral (*Toutes*, *Individuels*, *Familiaux*, *Structurels*) et les boutons *Voir ses sources →* sur chaque déterminant permettent d'isoler instantanément les articles correspondants.
   - Actions d'export et régénération : copie complète dans le presse-papiers, impression / export PDF via une feuille de style `@media print` dédiée, et bouton **Relancer le pipeline** pour régénérer la synthèse et écraser les anciens résultats en base MongoDB (`force_refresh: true`).

---

## 2. Arborescence des fichiers créés

```text
iackaton-chru-unidiv/
├── server.py                               # Serveur HTTP Python (API /api/* + fichiers statiques)
├── implementation.md                       # Présente documentation technique
└── frontend/
    ├── index.html                          # Point d'entrée HTML5 de la SPA
    ├── css/
    │   ├── tokens.css                      # Variables CSS (couleurs, modes clair/sombre, ombres, rayons)
    │   ├── base.css                        # Reset, grille ambiante, animations et @media print
    │   ├── components.css                  # Topbar, autocomplete, cartes thèmes/déterminants, sidebar sources
    │   └── pages.css                       # Mises en page des 3 vues et responsive design
    └── js/
        ├── app.js                          # Routeur SPA, fil d'Ariane, mode sombre et initialisation
        ├── config/
        │   ├── countries.js                # Référentiel des pays (Intl.DisplayNames) + filtrage + validation
        │   └── themes.js                   # Configuration déclarative des 18 boutons de thèmes
        ├── state/
        │   └── store.js                    # État global partagé et cache mémoire côté navigateur
        ├── services/
        │   └── api.js                      # Client HTTP vers /api/analyze + mode Aperçu Démo si hors ligne
        ├── components/
        │   ├── autocomplete.js             # Composant barre de recherche pays + dropdown + clavier
        │   └── sourcesSidebar.js           # Composant panneau latéral des sources PubMed
        ├── views/
        │   ├── homeView.js                 # Vue 1 : Page d'accueil
        │   ├── themesView.js               # Vue 2 : Grille des thèmes
        │   └── resultsView.js              # Vue 3 : Déterminants + Sources + Export
        └── utils/
            ├── dom.js                      # Échappement XSS (escapeHtml), surlignage, toasts
            └── icons.js                    # Bibliothèque d'icônes SVG inline (aucune dépendance CDN)
```

---

## 3. Comment modifier, ajouter ou supprimer des boutons de thèmes ?

Tout est centralisé dans le fichier **`frontend/js/config/themes.js`**.
Aucun autre fichier HTML, CSS ou JS n'a besoin d'être modifié pour changer les boutons.

Chaque bouton est décrit par un objet dans le tableau `THEMES` :

```js
{
  id: "grossesse",                  // Identifiant unique utilisé dans l'URL
  label: "Grossesse",               // Texte affiché sur le bouton
  queryContext: "pregnancy",        // Terme transmis au backend PubMed & IA (main.py)
  category: "Cycle de vie",         // "Cycle de vie" | "Santé & Soins" | "Société & Culture"
  icon: "heartPulse",               // Nom de l'icône SVG (voir frontend/js/utils/icons.js)
  accent: "rose",                   // Couleur : "blue" | "teal" | "amber" | "rose" | "indigo"
  description: "Suivi prénatal...", // Courte description affichée sur la carte
}
```

- **Ajouter un thème** : ajoutez un nouvel objet dans `THEMES`.
- **Renommer ou traduire un bouton** : modifiez `label` ou `queryContext`.
- **Supprimer un thème** : retirez l'objet correspondant de `THEMES`.
- **Réorganiser l'ordre** : changez simplement la position des objets dans le tableau `THEMES`.

---

## 4. Architecture technique & Documentation des modules

### 4.1 Serveur pont Python (`server.py`)
Écrit uniquement avec la bibliothèque standard Python (`http.server.ThreadingHTTPServer`, `json`, `mimetypes`), sans dépendance supplémentaire à installer :
- Sert le dossier `frontend/` à la racine `http://127.0.0.1:8000/`.
- **`GET /api/health`** : retourne `{"ok": true, "service": "unidiv-api"}` pour indiquer à l'interface que le pipeline Python est actif.
- **`POST /api/analyze`** : attend un JSON `{"country": "<nom anglais>", "context": "<queryContext>", "force_refresh": false}`, appelle `main(country, context, force_refresh=force_refresh)` dans `main.py`, supprime l'ancienne entrée MongoDB si `force_refresh` vaut `true`, convertit l'`ObjectId` MongoDB en chaîne de caractères et renvoie le résultat complet (`text` + `references`).

### 4.2 Référentiel des pays (`frontend/js/config/countries.js`)
- S'appuie sur la liste des codes ISO 3166-1 alpha-2 et l'API native `Intl.DisplayNames` pour obtenir les noms officiels en français (`fr`, affichés à l'utilisateur) et en anglais (`en`, envoyés à PubMed qui indexe majoritairement en anglais).
- `filterCountries(query)` place en priorité les pays commençant par la chaîne saisie, puis ceux la contenant ailleurs.
- `validateCountryInput(value)` vérifie une correspondance exacte (après normalisation des accents et de la casse) avant d'autoriser la navigation vers les thèmes.

### 4.3 Gestion du mode hors ligne (`frontend/js/services/api.js`)
- Au démarrage, `checkBackendHealth()` sonde `/api/health`.
- Si `server.py` est actif, l'indicateur du header passe au vert (*API Python connectée*) et chaque clic sur un thème appelle le vrai pipeline (`main.py`).
- Si le front-end est ouvert en statique sans serveur Python, l'interface bascule automatiquement en **Mode Aperçu Démo** avec des données structurées au même format, permettant de tester toute l'ergonomie de l'application à tout moment.

### 4.4 Sécurité & Accessibilité
- **Protection XSS** : toutes les données dynamiques (titres, résumés PubMed, textes générés, filtres saisis) passent par `escapeHtml()` dans `frontend/js/utils/dom.js` avant insertion dans le DOM.
- **Navigation clavier & ARIA** : attributs `role="listbox"`, `role="option"`, `role="tablist"`, `aria-selected`, `aria-live`, et focus visible contrasté.
- **Mode clair / sombre** : persistance dans `localStorage` (`unidiv_theme`) pilotée par les tokens CSS dans `frontend/css/tokens.css`.

---

## 5. Lancement du site complet

1. Vérifiez que **MongoDB** est démarré localement (`mongodb://127.0.0.1:27017/`) et que votre fichier `keys.py` contient votre clé API NVIDIA.
2. Lancez le serveur depuis la racine du projet :

```bash
# Avec l'environnement virtuel du projet (Windows PowerShell)
.\.env\Scripts\python.exe server.py
```

3. Ouvrez votre navigateur à l'adresse : **`http://127.0.0.1:8000`**
