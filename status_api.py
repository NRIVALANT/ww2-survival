"""status_api.py — Serveur HTTP léger exposant l'état de la partie.

Utilisé par server_headless.py comme thread interne.
Répond à GET /status avec du JSON lisible par le site vitrine.

Exemple de réponse :
    {
        "state":   "playing",
        "wave":    3,
        "players": 2,
        "max_players": 4,
        "enemies_remaining": 12,
        "online": true
    }
"""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

# Dict partagé mis à jour par DedicatedServer chaque tick
# Accédé en lecture seule par le handler HTTP (GIL suffit pour la cohérence)
_STATUS: dict = {
    "state":             "waiting",
    "wave":              0,
    "players":           0,
    "max_players":       4,
    "enemies_remaining": 0,
    "online":            True,
}


def update(state: str, wave: int, players: int, enemies_remaining: int) -> None:
    """Mettre à jour l'état partagé depuis la boucle de jeu."""
    _STATUS["state"]             = state
    _STATUS["wave"]              = wave
    _STATUS["players"]           = players
    _STATUS["enemies_remaining"] = enemies_remaining


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass   # silencer les logs HTTP dans le terminal du jeu

    def _send_json(self, data: dict, code: int = 200) -> None:
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        # CORS : autorise le site vitrine à fetch depuis n'importe quelle origine
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/status", "/status/", "/"):
            self._send_json(_STATUS)
        else:
            self._send_json({"error": "not found"}, 404)

    def do_OPTIONS(self):
        # Pré-vol CORS pour les navigateurs modernes
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.end_headers()


def start(port: int = 8080) -> threading.Thread:
    """Démarrer le serveur HTTP dans un thread daemon.

    À appeler une fois depuis DedicatedServer.__init__().
    Le thread s'arrête automatiquement quand le processus principal se termine.

    Returns:
        Le Thread démarré (utile pour les tests).
    """
    server = HTTPServer(("0.0.0.0", port), _Handler)

    t = threading.Thread(target=server.serve_forever, name="status-api", daemon=True)
    t.start()
    print(f"[status] API HTTP démarrée sur le port {port}  →  GET /status")
    return t
