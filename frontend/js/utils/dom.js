/**
 * Utilitaires DOM & Sécurité (échappement HTML, surlignage, toasts).
 */

export function escapeHtml(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

/**
 * Surligne le préfixe ou la correspondance dans un texte sans risque XSS.
 */
export function highlightMatch(text, query) {
  const safeText = escapeHtml(text);
  const cleanQuery = String(query || "").trim();
  if (!cleanQuery) return safeText;

  const escapedQuery = cleanQuery.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  const regex = new RegExp(`(${escapedQuery})`, "i");
  return safeText.replace(regex, "<mark>$1</mark>");
}

/**
 * Affiche une notification toast temporaire en bas à droite.
 */
export function showToast(message, durationMs = 2800) {
  const container = document.getElementById("toastContainer");
  if (!container) return;

  const toast = document.createElement("div");
  toast.className = "toast";
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    toast.style.transform = "translateY(8px)";
    toast.style.transition = "all 200ms ease";
    setTimeout(() => toast.remove(), 220);
  }, durationMs);
}
