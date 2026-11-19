"""
Serveur HTTP local UNIDIV — Relie le front-end modulaire (frontend/) au pipeline Python (main.py).

Lancement :
    python server.py
Puis ouvrir http://127.0.0.1:8000 dans un navigateur.
"""

from __future__ import annotations

import json
import mimetypes
import os
import traceback
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from main import main as run_unidiv_pipeline
from src.chatbot import ask_clinical_chatbot

BASE_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = BASE_DIR / "frontend"
HOST = os.environ.get("UNIDIV_HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT") or os.environ.get("UNIDIV_PORT", "8000"))


# Assure les bons types MIME pour les modules ES6 sous Windows
mimetypes.add_type("application/javascript; charset=utf-8", ".js")
mimetypes.add_type("text/css; charset=utf-8", ".css")


def _json_default(obj: Any) -> str:
    """Sérialise les types non-JSON natifs (ex: ObjectId de MongoDB)."""
    return str(obj)


class UnidivRequestHandler(SimpleHTTPRequestHandler):
    """Gestionnaire HTTP servant le front-end statique et les routes API /api/*."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def log_message(self, format: str, *args: Any) -> None:
        """Désactive l'affichage des logs de requêtes HTTP dans la console."""
        pass

    def _send_json(self, status_code: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload, ensure_ascii=False, default=_json_default).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/api/health":
            self._send_json(200, {"ok": True, "service": "unidiv-api"})
            return

        if self.path in ("", "/"):
            self.path = "/index.html"
        super().do_GET()

    def do_POST(self) -> None:
        if self.path not in ("/api/analyze", "/api/chat"):
            self._send_json(404, {"error": "Route API introuvable."})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(length)
            data = json.loads(raw_body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            self._send_json(400, {"error": "Corps JSON invalide."})
            return

        if self.path == "/api/chat":
            self._handle_chat_post(data)
            return

        country = str(data.get("country", "")).strip()
        context = str(data.get("context", "")).strip()
        force_refresh = bool(data.get("force_refresh", False))

        if not country or not context:
            self._send_json(400, {"error": "Les champs 'country' et 'context' sont obligatoires."})
            return

        try:
            result = run_unidiv_pipeline(country, context, force_refresh=force_refresh)
            result["mode"] = "live"
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": f"Erreur lors de l'exécution du pipeline UNIDIV : {exc}",
                },
            )

    def _handle_chat_post(self, data: dict[str, Any]) -> None:
        country = str(data.get("country", "")).strip()
        context = str(data.get("context", "")).strip()
        question = str(data.get("question", "")).strip()
        history = data.get("history") if isinstance(data.get("history"), list) else []
        auto_expand = bool(data.get("auto_expand_search", False))

        if not country or not question:
            self._send_json(400, {"error": "Les champs 'country' et 'question' sont obligatoires."})
            return

        try:
            result = ask_clinical_chatbot(
                country=country,
                context=context or None,
                question=question,
                history=history,
                auto_expand_search=auto_expand,
            )
            result["mode"] = "live"
            self._send_json(200, result)
        except Exception as exc:
            self._send_json(
                500,
                {
                    "error": f"Erreur lors de la réponse du chatbot UNIDIV : {exc}",
                },
            )


def run_server() -> None:
    if not FRONTEND_DIR.exists():
        raise FileNotFoundError(f"Dossier frontend introuvable : {FRONTEND_DIR}")

    server = ThreadingHTTPServer((HOST, PORT), UnidivRequestHandler)
    print(f"Serveur UNIDIV démarré sur http://{HOST}:{PORT}")
    print("Appuyez sur Ctrl+C pour arrêter.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nArrêt du serveur UNIDIV.")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
