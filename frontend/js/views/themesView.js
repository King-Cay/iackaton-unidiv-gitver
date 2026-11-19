/**
 * Vue 2 : Sélection du thème clinique / anthropologique pour le pays validé.
 * Les boutons sont entièrement générés depuis `js/config/themes.js`.
 */

import { ACCENT_STYLES, THEMES, THEME_CATEGORIES } from "../config/themes.js";
import { normalizeText } from "../config/countries.js";
import { store } from "../state/store.js";
import { escapeHtml } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

export function renderThemesView(containerEl, country, { onSelectTheme, onBackHome }) {
  containerEl.innerHTML = `
    <section class="page-section animate-in">
      <div class="container">
        <!-- Bannière pays sélectionné -->
        <div class="country-banner">
          <div class="country-banner__info">
            <div class="country-banner__iso">${escapeHtml(country.code)}</div>
            <div>
              <span class="country-banner__eyebrow">Pays sélectionné</span>
              <h1 class="country-banner__title">${escapeHtml(country.fr)}</h1>
              <p class="country-banner__meta">
                Requête scientifique associée : <code>${escapeHtml(country.en)}</code> · Choisissez une thématique de consultation ci-dessous
              </p>
            </div>
          </div>

          <button type="button" class="btn btn--secondary btn-back" id="changeCountryBtn">
            ${getIcon("arrowLeft")}
            <span>Changer de pays</span>
          </button>
        </div>

        <!-- Barre d'outils : onglets de catégories + filtre texte -->
        <div class="themes-toolbar">
          <div class="category-tabs" role="tablist" aria-label="Filtrer par catégorie de thème">
            ${THEME_CATEGORIES.map(
              (cat) => `
              <button
                type="button"
                class="category-tab ${store.activeCategory === cat ? "is-active" : ""}"
                data-category="${escapeHtml(cat)}"
                role="tab"
                aria-selected="${store.activeCategory === cat}"
              >
                ${escapeHtml(cat)}
              </button>
            `
            ).join("")}
          </div>

          <input
            type="search"
            id="themeFilterInput"
            class="themes-filter-input"
            placeholder="Filtrer un thème (ex : dentaire, deuil...)"
            value="${escapeHtml(store.themeSearchQuery)}"
            aria-label="Filtrer les thèmes"
          />
        </div>

        <!-- Grille dynamique des boutons de thèmes -->
        <div class="themes-grid" id="themesGrid"></div>
      </div>
    </section>
  `;

  const gridEl = containerEl.querySelector("#themesGrid");
  const filterInput = containerEl.querySelector("#themeFilterInput");

  function renderGrid() {
    const query = normalizeText(store.themeSearchQuery);
    const filtered = THEMES.filter((theme) => {
      const matchCat =
        store.activeCategory === "Tous" || theme.category === store.activeCategory;
      const matchText =
        !query ||
        normalizeText(theme.label).includes(query) ||
        normalizeText(theme.description).includes(query);
      return matchCat && matchText;
    });

    if (filtered.length === 0) {
      gridEl.innerHTML = `
        <div class="autocomplete-empty" style="grid-column: 1 / -1; padding: 3rem 1rem;">
          Aucun thème ne correspond à « <strong>${escapeHtml(store.themeSearchQuery)}</strong> ».
        </div>
      `;
      return;
    }

    gridEl.innerHTML = filtered
      .map((theme) => {
        const accent = ACCENT_STYLES[theme.accent] || ACCENT_STYLES.blue;
        return `
          <button
            type="button"
            class="theme-card"
            data-theme-id="${escapeHtml(theme.id)}"
            style="--card-accent: ${accent.gradient}; --card-accent-soft: ${accent.soft}; --card-accent-color: ${accent.color};"
          >
            <div class="theme-card__top">
              <span class="theme-card__icon" aria-hidden="true">${getIcon(theme.icon)}</span>
              <span class="theme-card__category">${escapeHtml(theme.category)}</span>
            </div>
            <span class="theme-card__title">${escapeHtml(theme.label)}</span>
            <span class="theme-card__desc">${escapeHtml(theme.description)}</span>
            <span class="theme-card__arrow">
              <span>Générer la synthèse</span>
              ${getIcon("arrowRight")}
            </span>
          </button>
        `;
      })
      .join("");

    gridEl.querySelectorAll(".theme-card").forEach((card) => {
      card.addEventListener("click", () => {
        const selected = THEMES.find((t) => t.id === card.dataset.themeId);
        if (selected) {
          onSelectTheme(selected);
        }
      });
    });
  }

  // Événements catégories
  containerEl.querySelectorAll(".category-tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      store.activeCategory = tab.dataset.category;
      containerEl.querySelectorAll(".category-tab").forEach((el) => {
        const active = el.dataset.category === store.activeCategory;
        el.classList.toggle("is-active", active);
        el.setAttribute("aria-selected", String(active));
      });
      renderGrid();
    });
  });

  // Filtre texte en direct
  filterInput.addEventListener("input", () => {
    store.themeSearchQuery = filterInput.value;
    renderGrid();
  });

  containerEl.querySelector("#changeCountryBtn").addEventListener("click", onBackHome);

  renderGrid();
}
