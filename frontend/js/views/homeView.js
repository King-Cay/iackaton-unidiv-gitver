/**
 * Vue 1 : Page d'accueil — Recherche et validation stricte du pays d'origine du patient.
 */

import { QUICK_COUNTRY_CODES, findCountryByCode } from "../config/countries.js";
import { mountCountryAutocomplete } from "../components/autocomplete.js";
import { store } from "../state/store.js";
import { escapeHtml } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

export function renderHomeView(containerEl, { onNavigateThemes }) {
  const quickCountries = QUICK_COUNTRY_CODES
    .map((code) => findCountryByCode(code))
    .filter(Boolean);

  containerEl.innerHTML = `
    <section class="home-hero animate-in">
      <div class="container">
        <div class="home-hero__content">
          <div class="hero-logo-wrap">
            <img src="assets/logo.jpg" alt="Logo UNIDIV" class="hero-logo-img" />
          </div>

          <div class="hero-badge">
            <img src="assets/logo.jpg" alt="" class="hero-badge__logo" aria-hidden="true" />
            <span>UNIDIV · Aide à la décision transculturelle</span>
          </div>

          <h1 class="hero-title">
            Comprendre le contexte culturel pour <span class="hero-title__gradient">mieux soigner</span>
          </h1>

          <p class="hero-subtitle">
            Sélectionnez le pays d'origine du patient pour accéder à une synthèse clinique structurée,
            sourcée sur la littérature médicale et anthropologique scientifique.
          </p>

          <!-- Barre de recherche Pays + Menu déroulant -->
          <div class="search-box" id="countrySearchBox">
            <div class="search-box__bar" id="searchBar">
              <span class="search-box__icon" aria-hidden="true">${getIcon("search")}</span>
              <div class="search-box__input-wrap">
                <input
                  type="text"
                  id="countryInput"
                  class="search-box__input"
                  placeholder="Ex : Congo, Maroc, Sénégal, Syrie..."
                  autocomplete="off"
                  aria-label="Nom du pays d'origine du patient"
                  aria-autocomplete="list"
                  aria-controls="countryDropdown"
                />
                <button
                  type="button"
                  id="countryClearBtn"
                  class="search-box__clear"
                  aria-label="Effacer la saisie"
                >
                  ${getIcon("x")}
                </button>
              </div>
              <button
                type="button"
                id="countrySubmitBtn"
                class="btn btn--primary search-box__submit"
                disabled
              >
                <span>Rechercher</span>
                ${getIcon("arrowRight")}
              </button>
            </div>

            <div
              class="autocomplete-dropdown"
              id="countryDropdown"
              role="listbox"
              aria-label="Suggestions de pays"
            ></div>

            <div class="search-validation" id="countryValidation" aria-live="polite"></div>
          </div>

          <!-- Accès rapide -->
          <div class="quick-countries">
            <span class="quick-countries__label">Accès rapide :</span>
            ${quickCountries
              .map(
                (c) => `
              <button type="button" class="quick-chip" data-code="${escapeHtml(c.code)}">
                <span>${escapeHtml(c.fr)}</span>
              </button>
            `
              )
              .join("")}
          </div>

          <!-- Rappel des 3 axes cliniques -->
          <div class="home-pillars">
            <div class="pillar-mini">
              <h2 class="pillar-mini__title">
                <span class="pillar-mini__dot" style="background: var(--det-ind-color);"></span>
                Déterminants individuels
              </h2>
              <p class="pillar-mini__text">
                Représentations personnelles du corps, de la maladie, de la pudeur et du vécu du patient.
              </p>
            </div>

            <div class="pillar-mini">
              <h2 class="pillar-mini__title">
                <span class="pillar-mini__dot" style="background: var(--det-fam-color);"></span>
                Déterminants familiaux
              </h2>
              <p class="pillar-mini__text">
                Rôle des proches, hiérarchie décisionnelle et accompagnement par l'entourage.
              </p>
            </div>

            <div class="pillar-mini">
              <h2 class="pillar-mini__title">
                <span class="pillar-mini__dot" style="background: var(--det-str-color);"></span>
                Déterminants structurels
              </h2>
              <p class="pillar-mini__text">
                Rapport au système de santé d'origine, contexte sociopolitique et barrières d'accès.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  `;

  const autocomplete = mountCountryAutocomplete({
    inputEl: containerEl.querySelector("#countryInput"),
    barEl: containerEl.querySelector("#searchBar"),
    dropdownEl: containerEl.querySelector("#countryDropdown"),
    clearBtnEl: containerEl.querySelector("#countryClearBtn"),
    submitBtnEl: containerEl.querySelector("#countrySubmitBtn"),
    validationEl: containerEl.querySelector("#countryValidation"),
    initialCountry: store.selectedCountry,
    onValidChange: (country) => {
      store.selectedCountry = country;
    },
    onSubmit: (country) => {
      store.selectedCountry = country;
      onNavigateThemes(country);
    },
  });

  // Raccourcis de pays rapides
  containerEl.querySelectorAll(".quick-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const country = findCountryByCode(chip.dataset.code);
      if (country) {
        autocomplete.setCountry(country);
      }
    });
  });

  return () => {
    autocomplete.destroy();
  };
}
