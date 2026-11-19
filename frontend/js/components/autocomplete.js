/**
 * Composant Autocomplete pour la recherche stricte de pays.
 * - Affiche un menu déroulant filtré dès la saisie (ex: "Co" -> Congo, Colombie, Comores...)
 * - Supporte la navigation clavier (Flèches Haut/Bas, Entrée, Échap)
 * - Bloque la validation si le pays saisi ne correspond pas à un pays valide.
 */

import { filterCountries, validateCountryInput } from "../config/countries.js";
import { escapeHtml, highlightMatch } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

export function mountCountryAutocomplete({
  inputEl,
  barEl,
  dropdownEl,
  clearBtnEl,
  submitBtnEl,
  validationEl,
  initialCountry = null,
  onValidChange,
  onSubmit,
}) {
  let matches = [];
  let activeIndex = -1;
  let validCountry = initialCountry;

  function renderValidationState(rawValue) {
    const trimmed = rawValue.trim();

    clearBtnEl.classList.toggle("is-visible", trimmed.length > 0);
    barEl.classList.remove("is-valid", "is-invalid");
    validationEl.className = "search-validation";

    if (!trimmed) {
      validCountry = null;
      submitBtnEl.disabled = true;
      validationEl.innerHTML = `<span>Saisissez le nom d'un pays et sélectionnez-le dans la liste pour continuer.</span>`;
      onValidChange?.(null);
      return;
    }

    const matched = validateCountryInput(trimmed);
    if (matched) {
      validCountry = matched;
      barEl.classList.add("is-valid");
      validationEl.classList.add("search-validation--valid");
      validationEl.innerHTML = `${getIcon("checkCircle")} <span>Pays valide : <strong>${escapeHtml(matched.fr)}</strong> (${escapeHtml(matched.code)})</span>`;
      submitBtnEl.disabled = false;
      onValidChange?.(matched);
    } else {
      validCountry = null;
      barEl.classList.add("is-invalid");
      validationEl.classList.add("search-validation--invalid");
      validationEl.innerHTML = `${getIcon("alertCircle")} <span>Nom de pays non reconnu. Veuillez choisir un pays dans le menu déroulant.</span>`;
      submitBtnEl.disabled = true;
      onValidChange?.(null);
    }
  }

  function renderDropdown(query) {
    matches = filterCountries(query, 10);
    activeIndex = matches.length > 0 ? 0 : -1;

    if (matches.length === 0) {
      dropdownEl.innerHTML = `
        <div class="autocomplete-empty">
          Aucun pays trouvé pour « <strong>${escapeHtml(query)}</strong> ».
        </div>
      `;
      dropdownEl.classList.add("is-open");
      return;
    }

    dropdownEl.innerHTML = matches
      .map((country, idx) => {
        const isActive = idx === activeIndex ? "is-active" : "";
        const showEn = country.en.toLowerCase() !== country.fr.toLowerCase();
        return `
          <button
            type="button"
            class="autocomplete-item ${isActive}"
            role="option"
            aria-selected="${idx === activeIndex}"
            data-code="${escapeHtml(country.code)}"
            data-index="${idx}"
          >
            <span class="autocomplete-item__main">
              <span class="autocomplete-item__code">${escapeHtml(country.code)}</span>
              <span class="autocomplete-item__name">
                ${highlightMatch(country.fr, query)}
                ${showEn ? `<span class="autocomplete-item__en">(${escapeHtml(country.en)})</span>` : ""}
              </span>
            </span>
          </button>
        `;
      })
      .join("");

    dropdownEl.classList.add("is-open");
  }

  function closeDropdown() {
    dropdownEl.classList.remove("is-open");
    activeIndex = -1;
  }

  function selectCountry(country) {
    if (!country) return;
    inputEl.value = country.fr;
    renderValidationState(country.fr);
    closeDropdown();
  }

  function updateActiveItem() {
    const items = dropdownEl.querySelectorAll(".autocomplete-item");
    items.forEach((item, idx) => {
      const selected = idx === activeIndex;
      item.classList.toggle("is-active", selected);
      item.setAttribute("aria-selected", String(selected));
      if (selected) {
        item.scrollIntoView({ block: "nearest" });
      }
    });
  }

  // Événements de saisie
  inputEl.addEventListener("input", () => {
    const val = inputEl.value;
    renderValidationState(val);
    renderDropdown(val);
  });

  inputEl.addEventListener("focus", () => {
    renderDropdown(inputEl.value);
  });

  inputEl.addEventListener("keydown", (e) => {
    const isOpen = dropdownEl.classList.contains("is-open");

    if (e.key === "ArrowDown") {
      e.preventDefault();
      if (!isOpen) {
        renderDropdown(inputEl.value);
      } else if (matches.length > 0) {
        activeIndex = (activeIndex + 1) % matches.length;
        updateActiveItem();
      }
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (isOpen && matches.length > 0) {
        activeIndex = (activeIndex - 1 + matches.length) % matches.length;
        updateActiveItem();
      }
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (validCountry && !isOpen) {
        onSubmit?.(validCountry);
      } else if (isOpen && activeIndex >= 0 && matches[activeIndex]) {
        selectCountry(matches[activeIndex]);
      } else if (validCountry) {
        onSubmit?.(validCountry);
      }
    } else if (e.key === "Escape") {
      closeDropdown();
    }
  });

  // Clic sur une suggestion du menu déroulant
  dropdownEl.addEventListener("mousedown", (e) => {
    const item = e.target.closest(".autocomplete-item");
    if (!item) return;
    e.preventDefault(); // Empêche la perte de focus avant sélection
    const idx = Number(item.dataset.index);
    if (matches[idx]) {
      selectCountry(matches[idx]);
    }
  });

  // Effacer la saisie
  clearBtnEl.addEventListener("click", () => {
    inputEl.value = "";
    renderValidationState("");
    renderDropdown("");
    inputEl.focus();
  });

  // Soumission
  submitBtnEl.addEventListener("click", () => {
    if (validCountry) {
      onSubmit?.(validCountry);
    }
  });

  // Fermeture au clic extérieur
  const handleOutsideClick = (e) => {
    if (!barEl.contains(e.target) && !dropdownEl.contains(e.target)) {
      closeDropdown();
    }
  };
  document.addEventListener("click", handleOutsideClick);

  // Initialisation si un pays est déjà pré-rempli
  if (initialCountry) {
    inputEl.value = initialCountry.fr;
    renderValidationState(initialCountry.fr);
  } else {
    renderValidationState("");
  }

  return {
    setCountry(country) {
      selectCountry(country);
    },
    destroy() {
      document.removeEventListener("click", handleOutsideClick);
    },
  };
}
