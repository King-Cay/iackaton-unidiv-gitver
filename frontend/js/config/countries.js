/**
 * Référentiel des pays reconnus pour l'autocomplétion et la validation stricte.
 * Utilise l'API standard du navigateur `Intl.DisplayNames` pour obtenir les noms
 * officiels en français (affichage) et en anglais (requêtes PubMed).
 */

const ISO_COUNTRY_CODES = [
  "AF", "ZA", "AL", "DZ", "DE", "AD", "AO", "AG", "SA", "AR", "AM", "AU", "AT", "AZ",
  "BS", "BH", "BD", "BB", "BE", "BZ", "BJ", "BT", "BY", "BO", "BA", "BW", "BR", "BN", "BG", "BF", "BI",
  "KH", "CM", "CA", "CV", "CL", "CN", "CY", "CO", "KM", "CG", "CD", "KP", "KR", "CR", "CI", "HR", "CU",
  "DK", "DJ", "DM", "EG", "AE", "EC", "ER", "ES", "EE", "SZ", "US", "ET",
  "FJ", "FI", "FR", "GA", "GM", "GE", "GH", "GR", "GD", "GT", "GN", "GQ", "GW", "GY",
  "HT", "HN", "HU", "IN", "ID", "IQ", "IR", "IE", "IS", "IL", "IT",
  "JM", "JP", "JO", "KZ", "KE", "KG", "KI", "KW", "LA", "LS", "LV", "LB", "LR", "LY", "LI", "LT", "LU",
  "MK", "MG", "MY", "MW", "MV", "ML", "MT", "MA", "MU", "MR", "MX", "FM", "MD", "MC", "MN", "ME", "MZ", "MM",
  "NA", "NR", "NP", "NI", "NE", "NG", "NO", "NZ", "OM", "UG", "UZ",
  "PK", "PW", "PS", "PA", "PG", "PY", "NL", "PE", "PH", "PL", "PT", "QA",
  "CF", "DO", "CZ", "RO", "GB", "RU", "RW",
  "KN", "SM", "VC", "LC", "SB", "SV", "WS", "ST", "SN", "RS", "SC", "SL", "SG", "SK", "SI", "SO", "SD", "SS", "LK", "SE", "CH", "SR", "SY",
  "TJ", "TW", "TZ", "TD", "TH", "TL", "TG", "TO", "TT", "TN", "TM", "TR", "TV",
  "UA", "UY", "VU", "VA", "VE", "VN", "YE", "ZM", "ZW",
];

const FRENCH_OVERRIDES = {
  CG: "Congo",
  CD: "Congo (RDC)",
  CI: "Côte d'Ivoire",
  US: "États-Unis",
  GB: "Royaume-Uni",
  AE: "Émirats arabes unis",
  CZ: "République tchèque",
  VN: "Viêt Nam",
};

const ENGLISH_OVERRIDES = {
  CG: "Congo",
  CD: "Democratic Republic of the Congo",
  CI: "Ivory Coast",
  US: "United States",
  GB: "United Kingdom",
  KR: "South Korea",
  KP: "North Korea",
  VN: "Vietnam",
};

const displayFr = typeof Intl !== "undefined" && Intl.DisplayNames
  ? new Intl.DisplayNames(["fr"], { type: "region" })
  : null;

const displayEn = typeof Intl !== "undefined" && Intl.DisplayNames
  ? new Intl.DisplayNames(["en"], { type: "region" })
  : null;

/**
 * Liste construite dynamiquement et triée alphabétiquement en français.
 */
export const COUNTRIES = ISO_COUNTRY_CODES
  .map((code) => ({
    code,
    fr: FRENCH_OVERRIDES[code] || displayFr?.of(code) || code,
    en: ENGLISH_OVERRIDES[code] || displayEn?.of(code) || code,
  }))
  .sort((a, b) => a.fr.localeCompare(b.fr, "fr"));

/** Suggestions rapides affichées sur la page d'accueil */
export const QUICK_COUNTRY_CODES = ["CG", "MA", "SN", "SY", "UA", "VN"];

/**
 * Normalise une chaîne (minuscules + suppression des accents) pour des comparaisons tolérantes.
 */
export function normalizeText(value) {
  return String(value || "")
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
}

/**
 * Filtre les pays pour l'autocomplétion :
 * 1. Priorité aux pays dont le nom FR ou EN COMMENCE par la saisie (ex: "Co" -> Colombie, Comores, Congo...)
 * 2. Puis aux pays qui contiennent la saisie ailleurs dans le nom.
 */
export function filterCountries(query, limit = 12) {
  const normQuery = normalizeText(query);
  if (!normQuery) {
    return COUNTRIES.slice(0, limit);
  }

  const startsWith = [];
  const contains = [];

  for (const country of COUNTRIES) {
    const frNorm = normalizeText(country.fr);
    const enNorm = normalizeText(country.en);

    if (frNorm.startsWith(normQuery) || enNorm.startsWith(normQuery)) {
      startsWith.push(country);
    } else if (frNorm.includes(normQuery) || enNorm.includes(normQuery)) {
      contains.push(country);
    }
  }

  return [...startsWith, ...contains].slice(0, limit);
}

/**
 * Valide strictement qu'une saisie correspond exactement à un pays reconnu (FR ou EN).
 * Retourne l'objet pays correspondant ou null si invalide.
 */
export function validateCountryInput(value) {
  const norm = normalizeText(value);
  if (!norm) return null;

  return (
    COUNTRIES.find(
      (c) => normalizeText(c.fr) === norm || normalizeText(c.en) === norm
    ) || null
  );
}

/**
 * Recherche un pays par son code ISO alpha-2.
 */
export function findCountryByCode(code) {
  if (!code) return null;
  const upper = String(code).trim().toUpperCase();
  return COUNTRIES.find((c) => c.code === upper) || null;
}
