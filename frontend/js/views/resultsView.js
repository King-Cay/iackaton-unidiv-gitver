/**
 * Vue 3 : Affichage des 3 déterminants cliniques + panneau latéral des sources PubMed.
 */

import { mountChatPanel } from "../components/chatPanel.js";
import { renderSourcesSidebar } from "../components/sourcesSidebar.js";
import { fetchClinicalSynthesis } from "../services/api.js";
import { store } from "../state/store.js";
import { escapeHtml, showToast } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

const DETERMINANT_SECTIONS = [
  {
    key: "determinant_individuels",
    modifier: "individuels",
    title: "Déterminants individuels",
    subtitle: "Représentations personnelles, vécu et croyances du patient",
    icon: "user",
  },
  {
    key: "determinant_familiaux",
    modifier: "familiaux",
    title: "Déterminants familiaux",
    subtitle: "Place de l'entourage et dynamique de décision familiale",
    icon: "users",
  },
  {
    key: "determinant_structurels",
    modifier: "structurels",
    title: "Déterminants structurels",
    subtitle: "Système de santé d'origine, contexte sociétal et accès aux soins",
    icon: "building",
  },
];

/**
 * Nettoie côté client les éventuelles phrases d'introduction ("Le paragraphe suivant est élaboré...")
 * pouvant figurer dans d'anciennes entrées mises en cache dans MongoDB.
 */
function cleanDeterminantText(rawText) {
  if (!rawText) return "";
  let clean = String(rawText).trim();
  const introRegexes = [
    /^(?:voici\s+)?le\s+paragraphe\s+(?:suivant|demand[ée])[^:\n]{0,180}:\s*/i,
    /^voici\s+(?:une\s+synth[èe]se|un\s+paragraphe|la\s+r[ée]ponse)[^:\n]{0,180}:\s*/i,
    /^(?:conform[ée]ment|selon)\s+(?:aux|les)\s+(?:consignes|directives)[^:\n]{0,180}:\s*/i,
    /^en\s+s'appuyant\s+sur\s+(?:le\s+contenu\s+des|les)\s+sources[^:\n]{0,180}:\s*/i,
    /^(?:#+\s*|\*\*\s*)?d[ée]terminants?\s+(?:individuels?|familiaux|structurels?)\s*(?:\*\*)?\s*[:\-–—]?\s*/i,
  ];
  for (const rx of introRegexes) {
    clean = clean.replace(rx, "").trim();
  }
  for (const rx of introRegexes) {
    clean = clean.replace(rx, "").trim();
  }
  return clean;
}

export async function renderResultsView(
  containerEl,
  country,
  theme,
  { onBackThemes, onUpdateStatus, forceRefresh = false }
) {
  let cancelled = false;

  // 1. Affichage du stepper de chargement animé pendant l'exécution du pipeline RAG
  containerEl.innerHTML = `
    <section class="page-section animate-in">
      <div class="container">
        <div class="loading-panel">
          <div class="loading-spinner" aria-hidden="true"></div>
          <h1 style="font-size: 1.35rem; font-weight: 800; margin-bottom: 0.45rem;">
            ${forceRefresh ? "Régénération complète de la synthèse…" : "Synthèse clinique en cours de préparation…"}
          </h1>
          <p style="color: var(--text-secondary); font-size: 0.92rem;">
            Analyse pour <strong>${escapeHtml(country.fr)}</strong> · Thème <strong>${escapeHtml(theme.label)}</strong>
          </p>

          <div class="loading-steps" id="loadingSteps">
            <div class="loading-step is-active" data-step="0">
              <span class="loading-step__dot"></span>
              <span>${
                forceRefresh
                  ? `Contournement du cache MongoDB pour (${escapeHtml(country.en)}, ${escapeHtml(theme.queryContext)})`
                  : `Vérification du cache MongoDB pour (${escapeHtml(country.en)}, ${escapeHtml(theme.queryContext)})`
              }</span>
            </div>
            <div class="loading-step" data-step="1">
              <span class="loading-step__dot"></span>
              <span>Collecte des publications dans les bases de données scientifiques</span>
            </div>
            <div class="loading-step" data-step="2">
              <span class="loading-step__dot"></span>
              <span>Classement sémantique par embeddings (NVIDIA Nemotron Embed)</span>
            </div>
            <div class="loading-step" data-step="3">
              <span class="loading-step__dot"></span>
              <span>Rédaction structurée des 3 déterminants (NVIDIA Nemotron LLM)</span>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;

  // Animation progressive des étapes pendant la requête
  let stepIdx = 0;
  const stepTimer = setInterval(() => {
    const steps = containerEl.querySelectorAll(".loading-step");
    if (!steps.length || stepIdx >= steps.length - 1) return;
    steps[stepIdx].classList.remove("is-active");
    steps[stepIdx].classList.add("is-done");
    stepIdx += 1;
    steps[stepIdx].classList.add("is-active");
  }, 1300);

  try {
    const result = await fetchClinicalSynthesis(country, theme, { forceRefresh });
    clearInterval(stepTimer);
    if (cancelled) return;

    onUpdateStatus?.(result.mode === "demo" ? "demo" : "online");
    renderLoadedResults(containerEl, country, theme, result, { onBackThemes, onUpdateStatus });
    if (forceRefresh) {
      showToast("Pipeline RAG relancé : les résultats ont été mis à jour.");
    }
  } catch (err) {
    clearInterval(stepTimer);
    if (cancelled) return;

    containerEl.innerHTML = `
      <section class="page-section animate-in">
        <div class="container">
          <div class="loading-panel">
            <div style="color: var(--status-error); width: 44px; height: 44px; margin: 0 auto 1rem;">
              ${getIcon("alertCircle")}
            </div>
            <h1 style="font-size: 1.3rem; font-weight: 800; margin-bottom: 0.5rem;">
              Impossible de générer la synthèse
            </h1>
            <p style="color: var(--text-secondary); font-size: 0.92rem; margin-bottom: 1.5rem;">
              ${escapeHtml(err.message || "Erreur inattendue lors de l'appel au pipeline.")}
            </p>
            <div style="display: flex; justify-content: center; gap: 0.75rem;">
              <button type="button" class="btn btn--secondary" id="errorBackBtn">
                ${getIcon("arrowLeft")}
                <span>Retour aux thèmes</span>
              </button>
              <button type="button" class="btn btn--primary" id="errorRetryBtn">
                <span>Réessayer</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    `;

    containerEl.querySelector("#errorBackBtn")?.addEventListener("click", onBackThemes);
    containerEl.querySelector("#errorRetryBtn")?.addEventListener("click", () => {
      renderResultsView(containerEl, country, theme, { onBackThemes, onUpdateStatus });
    });
  }

  return () => {
    cancelled = true;
    clearInterval(stepTimer);
  };
}

function countUniqueReferences(references) {
  const seen = new Set();
  for (const key of ["determinant_individuels", "determinant_familiaux", "determinant_structurels"]) {
    const list = Array.isArray(references?.[key]) ? references[key] : [];
    for (const art of list) {
      const id = art.document_id || art.pmid || art.doi || art.url || art.title;
      if (id) seen.add(id);
    }
  }
  return seen.size;
}

function renderLoadedResults(containerEl, country, theme, result, { onBackThemes, onUpdateStatus }) {
  store.activeSourceFilter = "all";

  const countsByAxis = {
    determinant_individuels: (result?.references?.determinant_individuels || []).length,
    determinant_familiaux: (result?.references?.determinant_familiaux || []).length,
    determinant_structurels: (result?.references?.determinant_structurels || []).length,
  };
  const totalUniqueSources = countUniqueReferences(result?.references);
  const hasLowCoverageAxis = Object.values(countsByAxis).some((c) => c < 3);

  let disclaimerHtml = "";
  if (totalUniqueSources === 0) {
    disclaimerHtml = `
      <div class="coverage-disclaimer coverage-disclaimer--empty" role="alert">
        ${getIcon("alertCircle")}
        <div>
          <strong>Données scientifiques insuffisantes (0 source pertinente) :</strong>
          aucune publication issue des bases interrogées n'a franchi le seuil de pertinence sémantique minimale pour
          <strong>${escapeHtml(country.fr)}</strong> × <strong>${escapeHtml(theme.label)}</strong>.
          Afin de garantir l'absence d'hallucination, le modèle s'est abstenu de générer des hypothèses non sourcées.
        </div>
      </div>
    `;
  } else if (hasLowCoverageAxis || totalUniqueSources < 5) {
    disclaimerHtml = `
      <div class="coverage-disclaimer" role="status">
        ${getIcon("alertCircle")}
        <div>
          <strong>Avertissement — Couverture documentaire restreinte (${totalUniqueSources} source${totalUniqueSources > 1 ? "s" : ""} unique${totalUniqueSources > 1 ? "s" : ""} retenue${totalUniqueSources > 1 ? "s" : ""}) :</strong>
          après élimination automatique des articles sous le seuil de pertinence sémantique, au moins un déterminant
          repose sur moins de 3 publications scientifiques. Les éléments ci-dessous doivent être interprétés avec une prudence clinique accrue.
        </div>
      </div>
    `;
  }

  containerEl.innerHTML = `
    <section class="page-section animate-in">
      <div class="container">
        <!-- En-tête des résultats -->
        <div class="results-header">
          <div class="results-header__left">
            <div class="results-header__badges">
              <span class="context-pill">${escapeHtml(country.code)} · ${escapeHtml(country.fr)}</span>
              <span class="context-pill context-pill--theme">${escapeHtml(theme.label)}</span>
              ${
                result.mode === "demo"
                  ? `<span class="context-pill" style="background: var(--status-warning-soft); color: var(--status-warning);">Aperçu Démo (backend hors ligne)</span>`
                  : ""
              }
            </div>
            <h1 class="results-header__title">Synthèse clinique & anthropologique</h1>
          </div>

          <div class="results-actions">
            <button type="button" class="btn btn--secondary btn-back" id="backToThemesBtn">
              ${getIcon("arrowLeft")}
              <span>Autres thèmes</span>
            </button>
            <button
              type="button"
              class="btn btn--secondary"
              id="rerunPipelineBtn"
              title="Relancer le pipeline RAG et écraser les résultats existants"
            >
              ${getIcon("refreshCw")}
              <span>Relancer le pipeline</span>
            </button>
            <button type="button" class="btn btn--secondary" id="copySummaryBtn">
              ${getIcon("copy")}
              <span>Copier</span>
            </button>
            <button type="button" class="btn btn--primary" id="printSummaryBtn">
              ${getIcon("printer")}
              <span>Exporter / PDF</span>
            </button>
          </div>
        </div>

        <!-- Grille principale : Déterminants (gauche) + Sources (droite) -->
        <div class="results-layout">
          <div class="determinants-stack">
            <div class="ethics-callout">
              ${getIcon("shieldCheck")}
              <div>
                <strong>Repères d'éthique clinique :</strong> cette fiche est générée à partir de sources
                scientifiques et anthropologiques pour éclairer la consultation. Elle propose des pistes de
                compréhension culturelles sans jamais réduire l'individu à son origine.
              </div>
            </div>

            ${disclaimerHtml}

            ${DETERMINANT_SECTIONS.map((sec) => {
              const content = cleanDeterminantText(result?.text?.[sec.key]) || "Aucun contenu généré pour cet axe.";
              const axisCount = countsByAxis[sec.key] ?? 0;
              return `
                <article class="determinant-card determinant-card--${sec.modifier}">
                  <header class="determinant-card__header">
                    <div class="determinant-card__title-group">
                      <span class="determinant-card__badge-icon" aria-hidden="true">${getIcon(sec.icon)}</span>
                      <div>
                        <h2 class="determinant-card__title">${escapeHtml(sec.title)}</h2>
                        <p class="determinant-card__subtitle">${escapeHtml(sec.subtitle)}</p>
                      </div>
                    </div>
                    <button
                      type="button"
                      class="determinant-card__filter-btn"
                      data-filter-axis="${sec.key}"
                      title="Afficher uniquement les sources utilisées pour cet axe"
                    >
                      Voir ses sources (${axisCount}) →
                    </button>
                  </header>
                  ${
                    axisCount > 0 && axisCount < 3
                      ? `<div class="determinant-card__low-sources">
                          ${getIcon("alertCircle")}
                          <span>Corpus restreint : synthèse appuyée sur ${axisCount} seule${axisCount > 1 ? "s" : ""} publication${axisCount > 1 ? "s" : ""} ayant franchi le seuil de pertinence.</span>
                        </div>`
                      : ""
                  }
                  <div class="determinant-card__body">${escapeHtml(content)}</div>
                </article>
              `;
            }).join("")}

            <!-- Chatbot Clinique RAG (Proposition 1, extensible aux Propositions 2 & 3) -->
            <div id="clinicalChatContainer"></div>
          </div>

          <!-- Panneau latéral des sources -->
          <aside class="sources-sidebar" id="sourcesSidebar" aria-label="Sources scientifiques utilisées"></aside>
        </div>
      </div>
    </section>
  `;

  const sidebarEl = containerEl.querySelector("#sourcesSidebar");
  const chatContainerEl = containerEl.querySelector("#clinicalChatContainer");
  const enrichedReferences = { ...(result.references || {}) };

  function refreshSidebar(filterKey) {
    store.activeSourceFilter = filterKey;
    renderSourcesSidebar(sidebarEl, enrichedReferences, filterKey, refreshSidebar);
  }

  refreshSidebar("all");

  // Montage du Chatbot Clinique RAG avec synchronisation des sources dans le panneau latéral
  if (chatContainerEl) {
    mountChatPanel(chatContainerEl, {
      country,
      theme,
      autoExpandSearch: false,
      onInspectChatSources: (chatRefs) => {
        enrichedReferences.chat_response = chatRefs;
        refreshSidebar("chat_response");
      },
    });
  }

  // Bouton "Voir ses sources" sur chaque déterminant -> synchronise la sidebar
  containerEl.querySelectorAll("[data-filter-axis]").forEach((btn) => {
    btn.addEventListener("click", () => {
      refreshSidebar(btn.dataset.filterAxis);
      sidebarEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
    });
  });

  // Retour vers les thèmes
  containerEl.querySelector("#backToThemesBtn").addEventListener("click", onBackThemes);

  // Relancer le pipeline RAG en écrasant les anciens résultats (cache navigateur + MongoDB)
  containerEl.querySelector("#rerunPipelineBtn").addEventListener("click", () => {
    renderResultsView(containerEl, country, theme, {
      onBackThemes,
      onUpdateStatus,
      forceRefresh: true,
    });
  });

  // Impression / Export PDF
  containerEl.querySelector("#printSummaryBtn").addEventListener("click", () => {
    window.print();
  });

  // Copier la synthèse complète dans le presse-papiers
  containerEl.querySelector("#copySummaryBtn").addEventListener("click", async () => {
    const plainText = [
      `UNIDIV — Synthèse transculturelle : ${country.fr} (${theme.label})`,
      "",
      ...DETERMINANT_SECTIONS.map(
        (sec) => `## ${sec.title}\n${cleanDeterminantText(result?.text?.[sec.key])}`
      ),
    ].join("\n\n");

    try {
      await navigator.clipboard.writeText(plainText);
      showToast("Synthèse clinique copiée dans le presse-papiers.");
    } catch {
      showToast("Impossible de copier automatiquement.");
    }
  });
}
