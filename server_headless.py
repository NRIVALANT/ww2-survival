"""server_headless.py — Serveur dédié WW2 Survival (sans affichage).

Lancement :
    python server_headless.py

Fonctionne sur un VPS Linux sans carte graphique ni écran (SDL dummy driver).
Les clients se connectent en WebSocket normalement — aucun changement côté client.

Comportement :
  - Le 1er joueur connecté est l'hôte virtuel (bouton "Lancer" dans son lobby).
  - Les autres joueurs voient le lobby et attendent.
  - Après une partie, le serveur réinitialise automatiquement le lobby.
"""
import os
import signal

# Doit être défini AVANT pygame.init()
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import status_api
from main_server import ServerGame
from settings import STATE_LOBBY, STATE_PLAYING, STATE_GAMEOVER, NET_PORT
from game.network.messages import encode, make_lobby_state, MSG_START_GAME
from game.world.map_data import PLAYER_START

_GAMEOVER_RESET_DELAY = 10.0   # secondes avant réinitialisation du lobby


class DedicatedServer(ServerGame):
    """ServerGame sans joueur local ni rendu graphique.

    Différences avec ServerGame :
    - Aucun joueur hôte : le 1er client connecté est l'hôte virtuel.
    - Pas de rendu écran (_draw = no-op).
    - Pas d'événements clavier/souris (_handle_local_event = no-op).
    - Démarrage manuel via bouton "Lancer" de l'hôte virtuel.
    - Réinitialisation automatique du lobby après game over.
    - Arrêt propre sur SIGTERM / Ctrl-C.
    """

    def __init__(self):
        super().__init__(host_name="__dedicated__")

        # Retirer le slot hôte local créé par ServerGame.__init__
        self.players.pop(self.host_player_id, None)
        self.host_player_id = 0          # sentinelle : pas d'hôte local

        self._gameover_timer: float | None = None

        # Démarrer l'API statut HTTP (port 8080) dans un thread daemon
        status_api.start(port=8080)

    # ------------------------------------------------------------------ lobby

    def _broadcast_lobby(self) -> None:
        """Marque le 1er joueur connecté comme hôte virtuel."""
        if not self.players:
            return
        first_pid = min(self.players.keys())
        lobby_players = [
            {
                "player_id":   pid,
                "player_name": p.player_name,
                "is_host":     (pid == first_pid),
            }
            for pid, p in self.players.items()
        ]
        self.server.broadcast(encode(make_lobby_state(lobby_players)))
        names = [p["player_name"] for p in lobby_players]
        print(f"[lobby] {len(lobby_players)} joueur(s) : {names}  (hôte : {self.players[first_pid].player_name})")

    def _reset_game(self) -> None:
        """Réinitialiser le monde et rouvrir le lobby pour une nouvelle partie."""
        print("[dédié] Réinitialisation — lobby ouvert.")
        saved = {pid: p.player_name for pid, p in self.players.items()}
        self.players.clear()
        self._init_world()
        self.state = STATE_LOBBY
        self._gameover_timer = None
        for pid, name in saved.items():
            self._add_player(pid, name)
        self.wave_manager.players = list(self.players.values())
        self._broadcast_lobby()

    # ------------------------------------------------------------------ réseau

    def _on_start_game_req(self, pid: int) -> None:
        """L'hôte virtuel (1er connecté) demande à lancer la partie."""
        if not self.players or self.state != STATE_LOBBY:
            return
        first_pid = min(self.players.keys())
        if pid != first_pid:
            return
        self.state = STATE_PLAYING
        self.server.broadcast(encode({"type": MSG_START_GAME}))
        self.wave_manager.players = list(self.players.values())
        print(f"[dédié] Partie lancée par {self.players[pid].player_name}.")

    # ------------------------------------------------------------------ rendu

    def _draw(self) -> None:
        """Pas de rendu graphique."""

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

            pygame.event.get()   # vider la queue (pas de QUIT sur SDL dummy)

            self._process_network_messages()
            self._update(dt)
            self._maybe_broadcast(dt)
            self._draw()

            # Mettre à jour l'API statut HTTP
            status_api.update(
                state=self.state,
                wave=getattr(self.wave_manager, "wave_number", 0),
                players=len(self.players),
                enemies_remaining=getattr(self.wave_manager, "enemies_remaining", 0),
            )

            # Réinitialisation automatique après game over
            if self.state == STATE_GAMEOVER:
                if self._gameover_timer is None:
                    self._gameover_timer = _GAMEOVER_RESET_DELAY
                    print(f"[dédié] Partie terminée — réinitialisation dans {int(_GAMEOVER_RESET_DELAY)}s …")
                else:
                    self._gameover_timer -= dt
                    if self._gameover_timer <= 0:
                        self._reset_game()

        print("[dédié] Arrêt du serveur …")
        self.server.stop()
        pygame.quit()


# --------------------------------------------------------------------------

if __name__ == "__main__":
    print("=== WW2 Survival — Serveur dédié ===")
    pygame.init()
    pygame.display.set_mode((1, 1))   # surface factice (SDL dummy driver)
    DedicatedServer().run(owns_pygame=True)
