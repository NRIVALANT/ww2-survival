"""server_headless.py — Serveur dédié WW2 Survival (sans affichage).

Lancement :
    python server_headless.py [--autostart 15]

Fonctionne sur un VPS Linux sans carte graphique ni écran (SDL dummy driver).
Les clients se connectent en WebSocket normalement — aucun changement côté client.
"""
import os
import sys
import signal
import argparse

# Doit être défini AVANT pygame.init()
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import status_api
from main_server import ServerGame
from settings import STATE_LOBBY, STATE_PLAYING, NET_PORT
from game.network.messages import encode, MSG_START_GAME

_DEFAULT_AUTOSTART = 15.0   # secondes après que le 1er client a rejoint


class DedicatedServer(ServerGame):
    """ServerGame sans joueur local ni rendu graphique.

    Différences avec ServerGame :
    - Aucun joueur hôte (slot player_id=1 retiré).
    - Pas de rendu écran (_draw = no-op).
    - Pas d'événements clavier/souris (_handle_local_event = no-op).
    - Démarrage automatique N secondes après la connexion du 1er joueur.
    - Arrêt propre sur SIGTERM / Ctrl-C.
    """

    def __init__(self, autostart_delay: float = _DEFAULT_AUTOSTART):
        super().__init__(host_name="__dedicated__")

        # Retirer le slot hôte local créé par ServerGame.__init__
        self.players.pop(self.host_player_id, None)
        self.host_player_id = 0          # sentinelle : pas d'hôte local

        self._autostart_delay = autostart_delay
        self._autostart_timer: float | None = None

        # Démarrer l'API statut HTTP (port 8080) dans un thread daemon
        status_api.start(port=8080)

    # ------------------------------------------------------------------ rendu

    def _draw(self) -> None:
        """Pas de rendu — gère uniquement le compte à rebours de démarrage."""
        if self.state == STATE_LOBBY and self.players:
            if self._autostart_timer is None:
                self._autostart_timer = self._autostart_delay
                print(f"[dédié] 1er joueur connecté — démarrage dans {int(self._autostart_delay)}s …")
                self._broadcast_lobby()

    def _handle_local_event(self, event) -> None:
        """Pas d'événements locaux sur un serveur dédié."""

    # ------------------------------------------------------------------ boucle

    def run(self, owns_pygame: bool = False) -> None:  # type: ignore[override]
        self._quit_requested = False

        def _shutdown(sig, frame):
            self._quit_requested = True

        signal.signal(signal.SIGTERM, _shutdown)
        signal.signal(signal.SIGINT,  _shutdown)

        print(f"[dédié] En attente de joueurs sur le port {NET_PORT} …")

        while not self._quit_requested:
            dt = self.clock.tick(60) / 1000.0
            dt = min(dt, 0.05)
            self._tick += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._quit_requested = True

            self._process_network_messages()
            self._update(dt)
            self._maybe_broadcast(dt)
            self._draw()

            # Mettre à jour l'état exposé par l'API HTTP
            status_api.update(
                state=self.state,
                wave=getattr(self.wave_manager, "wave_number", 0),
                players=len(self.players),
                enemies_remaining=getattr(self.wave_manager, "enemies_remaining", 0),
            )

            # Compte à rebours → démarrage automatique
            if self._autostart_timer is not None and self.state == STATE_LOBBY:
                self._autostart_timer -= dt
                remaining = int(self._autostart_timer) + 1
                if int(self._autostart_timer + dt) != int(self._autostart_timer):
                    print(f"[dédié] Démarrage dans {remaining}s …")
                if self._autostart_timer <= 0:
                    self._autostart_timer = None
                    self.state = STATE_PLAYING
                    self.server.broadcast(encode({"type": MSG_START_GAME}))
                    self.wave_manager.players = list(self.players.values())
                    print("[dédié] Partie lancée.")

        print("[dédié] Arrêt du serveur …")
        self.server.stop()
        pygame.quit()


# --------------------------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="WW2 Survival — Serveur dédié")
    parser.add_argument(
        "--autostart", type=float, default=_DEFAULT_AUTOSTART,
        metavar="SECONDES",
        help="Délai avant démarrage auto après le 1er joueur (défaut: %(default)s)",
    )
    args = parser.parse_args()

    print("=== WW2 Survival — Serveur dédié ===")
    pygame.init()
    pygame.display.set_mode((1, 1))   # surface factice (SDL dummy driver)
    DedicatedServer(autostart_delay=args.autostart).run(owns_pygame=True)
