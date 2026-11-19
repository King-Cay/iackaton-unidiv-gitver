/**
 * Composant Chatbot Clinique RAG — UNIDIV.
 * Utilise le prompt de l'utilisateur pour sélectionner par similarité cosinus (Nemotron-3-Embed-1B)
 * et Grade HAS les articles les plus pertinents du corpus, puis génère une réponse sourcée.
 *
 * Conçu de façon modulaire pour supporter sans réécriture :
 * - Proposition 1 : Chatbot contextuel sur la page de résultats (Pays × Thème)
 * - Proposition 2 : Option `autoExpandSearch` (élargissement automatique si < 2 sources locales)
 * - Proposition 3 : Montage sur la page des thèmes avec `theme = null` (question libre sur le pays)
 */

import { sendClinicalChatMessage } from "../services/api.js";
import { getCacheKey, store } from "../state/store.js";
import { escapeHtml } from "../utils/dom.js";
import { getIcon } from "../utils/icons.js";

function buildQuickSuggestions(country, theme) {
  const label = theme?.label ? theme.label.toLowerCase() : "la prise en charge médicale";
  return [
    `Quelles précautions de communication adopter autour de ${label} ?`,
    `Comment impliquer la famille ou les proches dans les décisions de soin ?`,
    `Quels freins d'accès aux soins ou représentations culturelles anticiper ?`,
  ];
}

function formatGradeMini(article) {
  const rec = article?.recommendation_score;
  if (!rec || !rec.grade) return "NC";
  const g = String(rec.grade).toUpperCase();
  const niv = rec.niveau_preuve ? `·Niv.${rec.niveau_preuve}` : "";
  return g === "NC" ? "Qualitatif (NC)" : `Grade ${g}${niv}`;
}

export function mountChatPanel(
  containerEl,
  { country, theme = null, autoExpandSearch = false, onInspectChatSources }
) {
  const historyKey = getCacheKey(country.en, theme?.queryContext || "__free__");
  if (!store.chatHistories.has(historyKey)) {
    store.chatHistories.set(historyKey, []);
  }

  let isSending = false;
  const suggestions = buildQuickSuggestions(country, theme);
  const contextBadge = theme?.label
    ? `${country.fr} · ${theme.label}`
    : `${country.fr} · Question libre`;

  containerEl.innerHTML = `
    <section class="chat-panel" aria-label="Assistant clinique conversationnel">
      <header class="chat-panel__header">
        <div class="chat-panel__title-group">
          <span class="chat-panel__icon" aria-hidden="true">${getIcon("messageCircle")}</span>
          <div>
            <div class="chat-panel__title-row">
              <h2 class="chat-panel__title">Poser une question clinique précise</h2>
              <span class="chat-panel__badge">${escapeHtml(contextBadge)}</span>
            </div>
            <p class="chat-panel__subtitle">
              Votre question est vectorisée (Nemotron Embed) pour extraire et analyser les publications
              les plus proches dans le corpus scientifique collecté.
            </p>
          </div>
        </div>
        <button
          type="button"
          class="btn btn--ghost chat-panel__clear"
          id="clearChatBtn"
          title="Réinitialiser la conversation"
        >
          Effacer
        </button>
      </header>

      <!-- Suggestions de questions rapides -->
      <div class="chat-suggestions" id="chatSuggestions">
        <span class="chat-suggestions__label">Questions suggérées :</span>
        ${suggestions
          .map(
            (q) => `
          <button type="button" class="chat-suggestion-chip" data-question="${escapeHtml(q)}">
            ${escapeHtml(q)}
          </button>
        `
          )
          .join("")}
      </div>

      <!-- Fil des messages -->
      <div class="chat-messages" id="chatMessages" role="log" aria-live="polite"></div>

      <!-- Barre de saisie -->
      <form class="chat-form" id="chatForm" autocomplete="off">
        <input
          type="text"
          id="chatInput"
          class="chat-form__input"
          placeholder="Posez votre question clinique (ex : annonce diagnostique, pudeur, observance...)"
          aria-label="Votre question clinique"
          required
        />
        <button type="submit" id="chatSubmitBtn" class="btn btn--primary chat-form__submit">
          <span>Demander</span>
          ${getIcon("arrowRight")}
        </button>
      </form>
    </section>
  `;

  const messagesEl = containerEl.querySelector("#chatMessages");
  const formEl = containerEl.querySelector("#chatForm");
  const inputEl = containerEl.querySelector("#chatInput");
  const submitBtnEl = containerEl.querySelector("#chatSubmitBtn");
  const clearBtnEl = containerEl.querySelector("#clearChatBtn");

  function renderMessages() {
    const history = store.chatHistories.get(historyKey) || [];
    clearBtnEl.style.display = history.length > 0 ? "inline-flex" : "none";

    if (history.length === 0) {
      messagesEl.innerHTML = `
        <div class="chat-empty">
          Cliquez sur une question suggérée ci-dessus ou saisissez votre propre question clinique
          pour interroger les sources scientifiques.
        </div>
      `;
      return;
    }

    messagesEl.innerHTML = history
      .map((msg, idx) => {
        if (msg.role === "user") {
          return `
            <div class="chat-message chat-message--user">
              <div class="chat-bubble chat-bubble--user">
                ${escapeHtml(msg.content)}
              </div>
            </div>
          `;
        }

        const refs = Array.isArray(msg.references) ? msg.references : [];
        const abstained = Boolean(msg.abstained);

        return `
          <div class="chat-message chat-message--assistant">
            <div class="chat-bubble chat-bubble--assistant ${abstained ? "chat-bubble--abstained" : ""}">
              <div class="chat-bubble__text">${escapeHtml(msg.content)}</div>

              <div class="chat-bubble__footer">
                ${
                  abstained || refs.length === 0
                    ? `<span class="chat-source-tag chat-source-tag--abstained">
                        ${getIcon("alertCircle")}
                        <span>Abstention méthodologique (0 source au-dessus du seuil cosinus)</span>
                      </span>`
                    : `
                      <div class="chat-bubble__sources-list">
                        ${refs
                          .slice(0, 3)
                          .map(
                            (art) => `
                          <span class="chat-source-tag" title="${escapeHtml(art.title || "")}">
                            <strong>${escapeHtml(art.source || "Source")}</strong> · ${escapeHtml(formatGradeMini(art))}
                          </span>
                        `
                          )
                          .join("")}
                        ${refs.length > 3 ? `<span class="chat-source-tag">+${refs.length - 3}</span>` : ""}
                      </div>
                      <button
                        type="button"
                        class="chat-inspect-sources-btn"
                        data-msg-idx="${idx}"
                      >
                        Afficher ces ${refs.length} source${refs.length > 1 ? "s" : ""} à droite →
                      </button>
                    `
                }
              </div>
            </div>
          </div>
        `;
      })
      .join("");

    messagesEl.querySelectorAll(".chat-inspect-sources-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const msgIdx = Number(btn.dataset.msgIdx);
        const targetMsg = history[msgIdx];
        if (targetMsg && Array.isArray(targetMsg.references)) {
          onInspectChatSources?.(targetMsg.references);
        }
      });
    });

    messagesEl.scrollTop = messagesEl.scrollHeight;
  }

  async function handleSendQuestion(rawQuestion) {
    const question = String(rawQuestion || "").trim();
    if (!question || isSending) return;

    const history = store.chatHistories.get(historyKey) || [];
    const priorHistoryForApi = history.map((m) => ({
      role: m.role,
      content: m.content,
    }));

    history.push({ role: "user", content: question });
    renderMessages();

    isSending = true;
    inputEl.value = "";
    inputEl.disabled = true;
    submitBtnEl.disabled = true;

    // Bulle d'attente animée
    const loadingNode = document.createElement("div");
    loadingNode.className = "chat-message chat-message--assistant";
    loadingNode.innerHTML = `
      <div class="chat-bubble chat-bubble--assistant chat-bubble--loading">
        <span>Vectorisation de votre question & analyse des sources HAS en cours…</span>
      </div>
    `;
    messagesEl.appendChild(loadingNode);
    messagesEl.scrollTop = messagesEl.scrollHeight;

    try {
      const res = await sendClinicalChatMessage({
        country,
        theme,
        question,
        history: priorHistoryForApi,
        autoExpandSearch,
      });

      history.push({
        role: "assistant",
        content: res.answer,
        references: res.references || [],
        abstained: Boolean(res.abstained),
      });

      // Si des sources ont été trouvées, on peut également les mettre en évidence à droite
      if (Array.isArray(res.references) && res.references.length > 0) {
        onInspectChatSources?.(res.references);
      }
    } catch (err) {
      history.push({
        role: "assistant",
        content: `Erreur lors de l'interrogation du chatbot : ${err.message || "Erreur inconnue"}`,
        references: [],
        abstained: true,
      });
    } finally {
      isSending = false;
      inputEl.disabled = false;
      submitBtnEl.disabled = false;
      renderMessages();
      inputEl.focus();
    }
  }

  formEl.addEventListener("submit", (e) => {
    e.preventDefault();
    handleSendQuestion(inputEl.value);
  });

  containerEl.querySelectorAll(".chat-suggestion-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      handleSendQuestion(chip.dataset.question);
    });
  });

  clearBtnEl.addEventListener("click", () => {
    store.chatHistories.set(historyKey, []);
    renderMessages();
  });

  renderMessages();
}
