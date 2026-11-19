/**
 * Point d'entrée principal de l'application SPA UNIDIV.
 * Gère le routage par hash (`#/`, `#/themes/:code`, `#/resultats/:code/:themeId`),
 * le fil d'Ariane, le mode clair/sombre et l'état de connexion au backend.
 */

import { findCountryByCode } from "./config/countries.js";
import { findThemeById } from "./config/themes.js";
import { checkBackendHealth } from "./services/api.js";
import { store } from "./state/store.js";
import { escapeHtml } from "./utils/dom.js";
import { getIcon } from "./utils/icons.js";
import { renderHomeView } from "./views/homeView.js";
import { renderThemesView } from "./views/themesView.js";
import { renderResultsView } from "./views/resultsView.js";

const appEl = document.getElementById("app");
const breadcrumbEl = document.getElementById("breadcrumb");
const statusPillEl = document.getElementById("backendStatusPill");
const themeToggleBtn = document.getElementById("themeToggleBtn");

let currentCleanup = null;

function setBackendStatus(mode) {
  if (!statusPillEl) return;
  const labelEl = statusPillEl.querySelector(".status-pill__label");
  statusPillEl.classList.remove("status-pill--online", "status-pill--demo");

  if (mode === "online") {
    statusPillEl.classList.add("status-pill--online");
    labelEl.textContent = "API Python connectée";
  } else {
    statusPillEl.classList.add("status-pill--demo");
    labelEl.textContent = "Mode Aperçu Démo";
  }
}

function updateBreadcrumb(items) {
  if (!breadcrumbEl) return;
  breadcrumbEl.innerHTML = items
    .map((item, idx) => {
      const sep = idx > 0 ? `<span class="breadcrumb__sep">/</span>` : "";
      if (item.href) {
        return `<span class="breadcrumb__item">${sep}<a href="${item.href}" class="breadcrumb__link">${escapeHtml(item.label)}</a></span>`;
      }
      return `<span class="breadcrumb__item">${sep}<span class="breadcrumb__current">${escapeHtml(item.label)}</span></span>`;
    })
    .join("");
}

function initDarkMode() {
  const saved = localStorage.getItem("unidiv_theme") || "light";
  applyColorTheme(saved);

  themeToggleBtn?.addEventListener("click", () => {
    const current = document.documentElement.getAttribute("data-theme");
    const next = current === "dark" ? "light" : "dark";
    applyColorTheme(next);
    localStorage.setItem("unidiv_theme", next);
  });
}

function applyColorTheme(themeName) {
  document.documentElement.setAttribute("data-theme", themeName);
  if (themeToggleBtn) {
    themeToggleBtn.innerHTML = themeName === "dark" ? getIcon("sun") : getIcon("moon");
  }
}

async function route() {
  if (typeof currentCleanup === "function") {
    currentCleanup();
    currentCleanup = null;
  }

  const hash = window.location.hash || "#/";
  const parts = hash.replace(/^#\/?/, "").split("/").filter(Boolean);

  // Route 1 : Accueil
  if (parts.length === 0) {
    updateBreadcrumb([{ label: "Accueil" }]);
    currentCleanup = renderHomeView(appEl, {
      onNavigateThemes: (country) => {
        window.location.hash = `#/themes/${country.code}`;
      },
    });
    return;
  }

  // Route 2 : Sélection des thèmes pour un pays valide
  if (parts[0] === "themes" && parts[1]) {
    const country = findCountryByCode(parts[1]);
    if (!country) {
      window.location.hash = "#/";
      return;
    }
    store.selectedCountry = country;
    updateBreadcrumb([
      { label: "Accueil", href: "#/" },
      { label: country.fr },
    ]);
    currentCleanup = renderThemesView(appEl, country, {
      onSelectTheme: (theme) => {
        store.selectedTheme = theme;
        window.location.hash = `#/resultats/${country.code}/${theme.id}`;
      },
      onBackHome: () => {
        window.location.hash = "#/";
      },
    });
    return;
  }

  // Route 3 : Déterminants & Sources
  if (parts[0] === "resultats" && parts[1] && parts[2]) {
    const country = findCountryByCode(parts[1]);
    const theme = findThemeById(parts[2]);
    if (!country || !theme) {
      window.location.hash = "#/";
      return;
    }
    store.selectedCountry = country;
    store.selectedTheme = theme;

    updateBreadcrumb([
      { label: "Accueil", href: "#/" },
      { label: country.fr, href: `#/themes/${country.code}` },
      { label: theme.label },
    ]);

    currentCleanup = await renderResultsView(appEl, country, theme, {
      onBackThemes: () => {
        window.location.hash = `#/themes/${country.code}`;
      },
      onUpdateStatus: setBackendStatus,
    });
    return;
  }

  // Fallback
  window.location.hash = "#/";
}

async function bootstrap() {
  initDarkMode();
  const isOnline = await checkBackendHealth();
  setBackendStatus(isOnline ? "online" : "demo");

  window.addEventListener("hashchange", route);
  await route();
}

bootstrap();
