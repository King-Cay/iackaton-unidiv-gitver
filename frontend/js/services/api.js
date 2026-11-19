/**
 * Service de communication avec le backend Python (server.py -> main.py).
 * Fournit également un fallback de démonstration réaliste si le serveur backend
 * n'est pas démarré (ex. ouverture statique du dossier frontend/).
 */

import { getCacheKey, store } from "../state/store.js";

export async function checkBackendHealth() {
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 1800);
    const res = await fetch("/api/health", { signal: controller.signal });
    clearTimeout(timer);
    if (!res.ok) return false;
    const data = await res.json();
    store.backendOnline = Boolean(data?.ok);
    return store.backendOnline;
  } catch {
    store.backendOnline = false;
    return false;
  }
}

/**
 * Appelle le pipeline RAG complet (`POST /api/analyze`) pour un pays et un thème.
 * Si `forceRefresh` vaut true, ignore le cache local et demande au backend
 * de relancer le pipeline RAG en écrasant les anciens résultats.
 */
export async function fetchClinicalSynthesis(country, theme, { forceRefresh = false } = {}) {
  const key = getCacheKey(country.en, theme.queryContext);
  if (!forceRefresh && store.analysisCache.has(key)) {
    return store.analysisCache.get(key);
  }
  if (forceRefresh) {
    store.analysisCache.delete(key);
  }

  try {
    const response = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country: country.en,
        country_fr: country.fr,
        context: theme.queryContext,
        theme_label: theme.label,
        force_refresh: forceRefresh,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Erreur serveur HTTP ${response.status}`);
    }

    const payload = await response.json();
    const normalized = { ...payload, mode: payload.mode || "live" };
    store.analysisCache.set(key, normalized);
    return normalized;
  } catch (err) {
    // Si le backend n'est pas joignable (ex: ouverture directe du fichier HTML), on propose un aperçu démo
    if (!store.backendOnline) {
      const demo = buildDemoFallback(country, theme);
      store.analysisCache.set(key, demo);
      return demo;
    }
    throw err;
  }
}

/**
 * Envoie une question clinique libre au Chatbot RAG (`POST /api/chat`).
 * Le prompt de l'utilisateur sert directement à la comparaison d'embeddings sur le corpus.
 * Compatible avec Proposition 1 (sur un thème donné), Proposition 2 (`autoExpandSearch`)
 * et Proposition 3 (`theme = null`, question libre sur le pays).
 */
export async function sendClinicalChatMessage({
  country,
  theme = null,
  question,
  history = [],
  autoExpandSearch = false,
}) {
  const contextQuery = theme?.queryContext || "";

  try {
    const response = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        country: country.en,
        country_fr: country.fr,
        context: contextQuery,
        question,
        history,
        auto_expand_search: autoExpandSearch,
      }),
    });

    if (!response.ok) {
      const errData = await response.json().catch(() => ({}));
      throw new Error(errData.error || `Erreur serveur HTTP ${response.status}`);
    }

    return await response.json();
  } catch (err) {
    if (!store.backendOnline) {
      return {
        mode: "demo",
        country: country.en,
        context: contextQuery || question,
        question,
        abstained: false,
        corpus_size: 2,
        answer:
          `[Aperçu Démo — démarrez server.py pour interroger le corpus scientifique réel]\n\n` +
          `Pour votre question « ${question} » concernant un patient originaire de ${country.fr}, ` +
          `les publications soulignent l'importance d'une écoute active, de la vérification de la compréhension mutuelle ` +
          `(recours à l'interprétariat professionnel si nécessaire) et de l'exploration respectueuse des attentes du patient et de ses proches.`,
        references: [
          {
            document_id: "PMID_CHAT_DEMO_01",
            source: "PubMed",
            pmid: "41793283",
            title: `Patient-centered communication regarding ${contextQuery || "clinical care"} in ${country.en}.`,
            abstract: "Qualitative findings on clinician-patient dialogue and culturally sensitive care.",
            authors: ["Équipe UNIDIV"],
            journal: "Global Public Health (Aperçu Démo)",
            publication_year: 2026,
            url: "https://pubmed.ncbi.nlm.nih.gov/41793283/",
            recommendation_score: {
              grade: "B",
              niveau_preuve: 2,
              score_numerique: 75,
              label: "Présomption scientifique (Niveau 2)",
              methode_detectee: "Étude de cohorte / comparative",
            },
          },
        ],
      };
    }
    throw err;
  }
}

/**
 * Données de démonstration structurées au format exact retourné par `main.py`
 * lorsque le frontend est prévisualisé sans serveur Python actif.
 */
function buildDemoFallback(country, theme) {
  const cFr = country.fr;
  const tLabel = theme.label.toLowerCase();

  const sampleRefs = [
    {
      document_id: "PMID_DEMO_01",
      source: "PubMed",
      pmid: "41793283",
      doi: "10.1080/17441692.2026.2640771",
      title: `Cultural perspectives and patient-centered care regarding ${theme.queryContext} in ${country.en}: a qualitative synthesis.`,
      abstract: `Objective: To explore individual, family, and structural determinants shaping healthcare interactions around ${theme.queryContext} among patients originating from ${country.en}. Findings emphasize respectful communication, cultural humility, and involvement of trusted family mediators when appropriate.`,
      authors: ["Équipe UNIDIV", "Université de Lorraine"],
      journal: "Global Public Health (Aperçu Démo)",
      publication_year: 2026,
      url: "https://pubmed.ncbi.nlm.nih.gov/41793283/",
      recommendation_score: {
        grade: "NC",
        niveau_preuve: null,
        score_numerique: 45,
        label: "Étude qualitative (hors échelle quantitative HAS)",
        methode_detectee: "Recherche qualitative / anthropologique",
      },
    },
    {
      document_id: "S2_DEMO_02",
      source: "Semantic Scholar",
      doi: "10.1016/j.socscimed.2024.116842",
      title: `Transcultural clinical encounters and health literacy in ${theme.queryContext}: lessons for European clinicians.`,
      abstract: `This review highlights how health beliefs, trust in healthcare institutions, and socio-economic barriers influence clinical adherence and shared decision-making in multicultural consultations.`,
      authors: ["M. Laurent", "A. Diallo", "S. Benali"],
      journal: "Social Science & Medicine (Aperçu Démo)",
      publication_year: 2025,
      url: "https://doi.org/10.1016/j.socscimed.2024.116842",
      recommendation_score: {
        grade: "B",
        niveau_preuve: 2,
        score_numerique: 75,
        label: "Présomption scientifique (Niveau 2)",
        methode_detectee: "Étude de cohorte / comparative",
      },
    },
  ];

  return {
    mode: "demo",
    country: country.en,
    context: theme.queryContext,
    text: {
      determinant_individuels:
        `[Mode Aperçu Démo — démarrez server.py pour interroger les bases scientifiques & NVIDIA NIM en direct]\n\n` +
        `Chez un patient originaire de ${cFr} consultant dans un contexte de ${tLabel}, la perception individuelle de la situation de soin peut s'articuler autour de représentations culturelles, spirituelles ou corporelles spécifiques. Il est recommandé d'explorer avec tact ce que le patient comprend de son symptôme, ses attentes vis-à-vis de la prise en charge et les éventuelles dimensions de pudeur ou de pudeur émotionnelle sans jamais présumer de son adhésion personnelle à une norme collective.`,
      determinant_familiaux:
        `Dans de nombreux parcours de soins impliquant des patients issus de ${cFr}, l'entourage familial joue un rôle d'appui affectif, moral et parfois décisionnel majeur autour de la thématique « ${theme.label} ». Le praticien gagnera à clarifier directement avec le patient qui doit être associé à l'information médicale, tout en veillant au respect strict du secret médical et du consentement libre et éclairé de la personne soignée.`,
      determinant_structurels:
        `Sur le plan structurel, le rapport du patient au système de santé français peut être influencé par l'organisation sanitaire connue en ${cFr} (accès aux soins primaires, coût des traitements, place des médecines complémentaires), ainsi que par d'éventuelles barrières administratives, linguistiques ou liées au parcours migratoire. L'usage d'un interprétariat professionnel et de supports visuels adaptés favorise l'alliance thérapeutique.`,
    },
    references: {
      determinant_individuels: [sampleRefs[0]],
      determinant_familiaux: [sampleRefs[0], sampleRefs[1]],
      determinant_structurels: [sampleRefs[1]],
    },
  };
}
