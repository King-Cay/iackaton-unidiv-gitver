/**
 * ============================================================================
 * CONFIGURATION DES BOUTONS DE THÈMES — UNIDIV
 * ============================================================================
 * Modifiez ce tableau pour ajouter, retirer, renommer ou réordonner les thèmes.
 * Chaque objet correspond directement à un bouton affiché sur la page des thèmes.
 *
 * Champs :
 * - id           : identifiant unique (utilisé dans l'URL)
 * - label        : intitulé visible sur le bouton
 * - queryContext : terme de recherche transmis au pipeline Python (PubMed + IA)
 * - category     : onglet de regroupement ("Cycle de vie" | "Santé & Soins" | "Société & Culture")
 * - icon         : clé d'icône définie dans `js/utils/icons.js`
 * - accent       : "blue" | "teal" | "amber" | "rose" | "indigo"
 * - description  : sous-titre explicatif pour le praticien
 * ============================================================================
 */

export const THEME_CATEGORIES = [
  "Tous",
  "Cycle de vie",
  "Santé & Soins",
  "Société & Culture",
];

export const THEMES = [
  {
    id: "grossesse",
    label: "Grossesse",
    queryContext: "pregnancy",
    category: "Cycle de vie",
    icon: "heartPulse",
    accent: "rose",
    description: "Suivi prénatal, représentations de la maternité et accouchement.",
  },
  {
    id: "parentalite",
    label: "Parentalité",
    queryContext: "parenting",
    category: "Cycle de vie",
    icon: "users",
    accent: "teal",
    description: "Rôles parentaux, éducation, soins du nourrisson et autorité familiale.",
  },
  {
    id: "sexualite",
    label: "Sexualité",
    queryContext: "sexuality",
    category: "Cycle de vie",
    icon: "shieldHeart",
    accent: "rose",
    description: "Santé sexuelle, pudeur, contraception et tabous culturels.",
  },
  {
    id: "vieillissement",
    label: "Vieillissement",
    queryContext: "aging",
    category: "Cycle de vie",
    icon: "clock",
    accent: "amber",
    description: "Place des aînés, perte d'autonomie et solidarité intergénérationnelle.",
  },
  {
    id: "mort-deuil",
    label: "Mort & Deuil",
    queryContext: "grieving",
    category: "Cycle de vie",
    icon: "feather",
    accent: "indigo",
    description: "Rites funéraires, expression de la perte et accompagnement en fin de vie.",
  },
  {
    id: "alimentation",
    label: "Alimentation",
    queryContext: "nutrition",
    category: "Société & Culture",
    icon: "utensils",
    accent: "teal",
    description: "Interdits alimentaires, jeûne, nutrition thérapeutique et hospitalière.",
  },
  {
    id: "loisirs",
    label: "Loisirs",
    queryContext: "leisure",
    category: "Société & Culture",
    icon: "sun",
    accent: "amber",
    description: "Vie sociale, pratiques communautaires, repos et rapport au temps libre.",
  },
  {
    id: "religion-spiritualite",
    label: "Religion & Spiritualité",
    queryContext: "religion spirituality",
    category: "Société & Culture",
    icon: "sparkles",
    accent: "indigo",
    description: "Croyances, prières, médiation spirituelle et sens donné à la maladie.",
  },
  {
    id: "hygiene",
    label: "Hygiène",
    queryContext: "hygiene",
    category: "Santé & Soins",
    icon: "droplet",
    accent: "blue",
    description: "Pratiques d'hygiène corporelle, ablutions et prévention infectieuse.",
  },
  {
    id: "travail",
    label: "Travail",
    queryContext: "occupational health",
    category: "Société & Culture",
    icon: "briefcase",
    accent: "amber",
    description: "Conditions professionnelles, pénibilité, arrêt maladie et précarité.",
  },
  {
    id: "sante",
    label: "Santé",
    queryContext: "health beliefs",
    category: "Santé & Soins",
    icon: "activity",
    accent: "teal",
    description: "Représentation globale de la santé, du bien-être et de la maladie.",
  },
  {
    id: "soins-medicaux",
    label: "Soins médicaux",
    queryContext: "medical care",
    category: "Santé & Soins",
    icon: "stethoscope",
    accent: "blue",
    description: "Observance, médecine traditionnelle et acceptation des traitements.",
  },
  {
    id: "hygiene-dentaire",
    label: "Hygiène dentaire",
    queryContext: "dental hygiene",
    category: "Santé & Soins",
    icon: "smile",
    accent: "blue",
    description: "Soins bucco-dentaires, recours aux soins préventifs et pratiques locales.",
  },
  {
    id: "systeme-de-soins",
    label: "Système de soins",
    queryContext: "healthcare system",
    category: "Santé & Soins",
    icon: "building",
    accent: "indigo",
    description: "Organisation sanitaire d'origine, couverture santé et parcours d'accès.",
  },
  {
    id: "relation-soignant-patient",
    label: "Relation soignant-patient",
    queryContext: "doctor patient relationship",
    category: "Santé & Soins",
    icon: "messageCircle",
    accent: "teal",
    description: "Communication, annonce diagnostique, confiance et barrière linguistique.",
  },
  {
    id: "contexte-politique",
    label: "Contexte politique",
    queryContext: "political context",
    category: "Société & Culture",
    icon: "globe",
    accent: "amber",
    description: "Conflits, parcours migratoire, exil et traumatismes géopolitiques.",
  },
  {
    id: "alphabetisation",
    label: "Alphabétisation",
    queryContext: "health literacy",
    category: "Société & Culture",
    icon: "bookOpen",
    accent: "blue",
    description: "Littératie en santé, compréhension des ordonnances et supports adaptés.",
  },
  {
    id: "genetique",
    label: "Génétique",
    queryContext: "genetics",
    category: "Santé & Soins",
    icon: "dna",
    accent: "indigo",
    description: "Pathologies héréditaires, consanguinité et perception du conseil génétique.",
  },
];

export function findThemeById(themeId) {
  return THEMES.find((t) => t.id === themeId) || null;
}

export const ACCENT_STYLES = {
  blue: {
    color: "#2563eb",
    soft: "rgba(37, 99, 235, 0.12)",
    gradient: "linear-gradient(90deg, #2563eb, #38bdf8)",
  },
  teal: {
    color: "#0d9488",
    soft: "rgba(13, 148, 136, 0.12)",
    gradient: "linear-gradient(90deg, #0d9488, #2dd4bf)",
  },
  amber: {
    color: "#d97706",
    soft: "rgba(217, 119, 6, 0.12)",
    gradient: "linear-gradient(90deg, #d97706, #fbbf24)",
  },
  rose: {
    color: "#e11d48",
    soft: "rgba(225, 29, 72, 0.12)",
    gradient: "linear-gradient(90deg, #e11d48, #fb7185)",
  },
  indigo: {
    color: "#4f46e5",
    soft: "rgba(79, 70, 229, 0.12)",
    gradient: "linear-gradient(90deg, #4f46e5, #818cf8)",
  },
};
