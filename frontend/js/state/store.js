/**
 * Store centralisé de l'état de l'application UNIDIV.
 */

export const store = {
  selectedCountry: null,     // { code, fr, en }
  selectedTheme: null,       // Objet thème issu de config/themes.js
  activeCategory: "Tous",    // Filtre de catégorie sur la vue Thèmes
  themeSearchQuery: "",      // Filtre texte sur la vue Thèmes
  activeSourceFilter: "all", // "all" | "determinant_individuels" | "determinant_familiaux" | "determinant_structurels"
  backendOnline: false,      // Indique si server.py répond
  analysisCache: new Map(),  // Cache mémoire navigateur clé `${country.en}::${theme.queryContext}`
  chatHistories: new Map(),  // Historique du chatbot clé `${country.en}::${context}`
};

export function getCacheKey(countryEn, context) {
  return `${countryEn.toLowerCase()}::${context.toLowerCase()}`;
}
