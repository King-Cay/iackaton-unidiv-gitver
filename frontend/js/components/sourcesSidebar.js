/**
 * Composant Panneau Latéral des Sources Scientifiques (multi-sources).
 * Supporte toute provenance (`article.source` : PubMed, Semantic Scholar, OMS, Cairn, etc.)
 * avec filtrage par axe (Tous / Individuels / Familiaux / Structurels) et abstract dépliable.
 */

import { escapeHtml } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

const AXIS_LABELS = {
  determinant_individuels: "Individuels",
  determinant_familiaux: "Familiaux",
  determinant_structurels: "Structurels",
  chat_response: "Chatbot",
};

/**
 * Construit un identifiant lisible et une URL externe agnostique de la base source.
 */
function resolveSourceMeta(article) {
  const sourceName = article.source || "Source scientifique";
  let identifier = article.document_id || sourceName;
  if (article.pmid) {
    identifier = `PMID ${article.pmid}`;
  } else if (article.doi) {
    identifier = `DOI ${article.doi}`;
  }

  let externalUrl = article.url || "";
  if (!externalUrl && article.pmid) {
    externalUrl = `https://pubmed.ncbi.nlm.nih.gov/${article.pmid}/`;
  } else if (!externalUrl && article.doi) {
    externalUrl = `https://doi.org/${article.doi}`;
  }

  return { sourceName, identifier, externalUrl };
}

/**
 * Formate le badge de niveau de preuve HAS (Grade A, B, C ou NC).
 */
function resolveGradeBadge(article) {
  const rec = article.recommendation_score;
  if (!rec || !rec.grade) {
    return null;
  }
  const grade = String(rec.grade).toUpperCase();
  const niveau = rec.niveau_preuve ? ` · Niv. ${rec.niveau_preuve}` : "";
  const cssMod = ["A", "B", "C"].includes(grade) ? grade.toLowerCase() : "nc";
  const shortBadge =
    grade === "NC"
      ? rec.score_numerique >= 40
        ? "Qualitatif (NC)"
        : "Grade NC"
      : `Grade ${grade}${niveau}`;

  return {
    cssMod,
    shortBadge,
    label: rec.label || "",
    methode: rec.methode_detectee || "",
  };
}

/**
 * Déduplique les articles tout en conservant la liste des axes auxquels ils ont contribué.
 */
function flattenReferences(references, activeFilter) {
  const axesToRead =
    activeFilter === "all"
      ? ["determinant_individuels", "determinant_familiaux", "determinant_structurels"]
      : [activeFilter];

  const byId = new Map();

  for (const axisKey of axesToRead) {
    const list = Array.isArray(references?.[axisKey]) ? references[axisKey] : [];
    for (const article of list) {
      const uniqueKey = article.document_id || article.pmid || article.doi || article.url || article.title;
      if (!uniqueKey) continue;

      if (!byId.has(uniqueKey)) {
        byId.set(uniqueKey, {
          ...article,
          axes: [AXIS_LABELS[axisKey]],
        });
      } else {
        const existing = byId.get(uniqueKey);
        const label = AXIS_LABELS[axisKey];
        if (!existing.axes.includes(label)) {
          existing.axes.push(label);
        }
      }
    }
  }

  return Array.from(byId.values());
}

export function renderSourcesSidebar(containerEl, references, activeFilter = "all", onFilterChange) {
  const items = flattenReferences(references, activeFilter);
  const hasChatSources = Array.isArray(references?.chat_response) && references.chat_response.length > 0;

  const filterButtons = [
    { key: "all", label: "Toutes" },
    { key: "determinant_individuels", label: "Individuels" },
    { key: "determinant_familiaux", label: "Familiaux" },
    { key: "determinant_structurels", label: "Structurels" },
    ...(hasChatSources ? [{ key: "chat_response", label: "Chatbot" }] : []),
  ];

  containerEl.innerHTML = `
    <div class="sources-panel">
      <div class="sources-panel__header">
        <h2 class="sources-panel__title">
          ${getIcon("bookOpen")}
          <span>Sources scientifiques</span>
        </h2>
        <span class="sources-panel__count">${items.length} source${items.length > 1 ? "s" : ""}</span>
      </div>

      <div class="sources-filter" role="tablist" aria-label="Filtrer les sources par déterminant">
        ${filterButtons
          .map(
            (btn) => `
          <button
            type="button"
            class="filter-chip ${activeFilter === btn.key ? "is-active" : ""}"
            data-filter="${btn.key}"
            role="tab"
            aria-selected="${activeFilter === btn.key}"
          >
            ${escapeHtml(btn.label)}
          </button>
        `
          )
          .join("")}
      </div>

      <div class="sources-list">
        ${
          items.length === 0
            ? `<p class="autocomplete-empty">Aucune source scientifique associée à ce filtre.</p>`
            : items
                .map((article, idx) => {
                  const { sourceName, identifier, externalUrl } = resolveSourceMeta(article);
                  const gradeInfo = resolveGradeBadge(article);
                  const year = article.publication_year || "n.d.";
                  const authors = Array.isArray(article.authors) && article.authors.length > 0
                    ? `${article.authors.slice(0, 3).join(", ")}${article.authors.length > 3 ? " et al." : ""}`
                    : "";

                  return `
                    <article class="source-card">
                      <div class="source-card__meta">
                        <span class="source-badge">${escapeHtml(sourceName)}</span>
                        ${
                          gradeInfo
                            ? `<span class="grade-badge grade-badge--${gradeInfo.cssMod}" title="${escapeHtml(gradeInfo.label)}">
                                ${escapeHtml(gradeInfo.shortBadge)}
                              </span>`
                            : ""
                        }
                        <span class="source-year">${escapeHtml(identifier)} · ${escapeHtml(year)}</span>
                        <span class="source-axis-tag">${escapeHtml(article.axes.join(" · "))}</span>
                      </div>
                      <h3 class="source-card__title">${escapeHtml(article.title || "Document sans titre")}</h3>
                      <p class="source-card__journal">
                        ${escapeHtml(article.journal || sourceName)}${authors ? ` — ${escapeHtml(authors)}` : ""}
                      </p>
                      ${
                        gradeInfo && (gradeInfo.label || gradeInfo.methode)
                          ? `<div class="source-card__has-info">
                              <strong>${escapeHtml(gradeInfo.label)}</strong>
                              ${gradeInfo.methode ? ` · <span>${escapeHtml(gradeInfo.methode)}</span>` : ""}
                            </div>`
                          : ""
                      }
                      <div class="source-card__actions">
                        ${
                          externalUrl
                            ? `<a
                                href="${escapeHtml(externalUrl)}"
                                target="_blank"
                                rel="noopener noreferrer"
                                class="source-card__link"
                              >
                                <span>Consulter la source</span>
                                ${getIcon("externalLink")}
                              </a>`
                            : `<span></span>`
                        }
                        ${
                          article.abstract
                            ? `<button type="button" class="source-card__toggle" data-abstract-idx="${idx}" aria-expanded="false">
                                Résumé
                              </button>`
                            : ""
                        }
                      </div>
                      ${
                        article.abstract
                          ? `<div class="source-card__abstract" id="source-abstract-${idx}">
                              ${escapeHtml(article.abstract)}
                            </div>`
                          : ""
                      }
                    </article>
                  `;
                })
                .join("")
        }
      </div>
    </div>
  `;

  // Événements des filtres
  containerEl.querySelectorAll(".filter-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      const nextFilter = chip.dataset.filter;
      onFilterChange?.(nextFilter);
    });
  });

  // Accordéon des résumés
  containerEl.querySelectorAll(".source-card__toggle").forEach((btn) => {
    btn.addEventListener("click", () => {
      const idx = btn.dataset.abstractIdx;
      const box = containerEl.querySelector(`#source-abstract-${idx}`);
      if (!box) return;
      const isOpen = box.classList.toggle("is-open");
      btn.setAttribute("aria-expanded", String(isOpen));
      btn.textContent = isOpen ? "Masquer" : "Résumé";
    });
  });
}
