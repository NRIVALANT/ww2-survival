# main_client.py - Client leger : rendu depuis snapshots serveur
import pygame
import sys
import math

from settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    WEAPON_ORDER, WEAPONS, PLAYER_COLORS, ENEMY_TYPES,
    COL_BULLET_P, COL_BULLET_E, COL_YELLOW, COL_WHITE, COL_GREY, COL_RED,
    COL_BLACK,
    UPGRADE_MACHINE_TILE, KEYBINDS, NET_PORT,
    STATE_MENU, STATE_SETTINGS, STATE_NETWORK_MENU, STATE_PLAYING,
    STATE_PAUSED, STATE_GAMEOVER, STATE_LOBBY,
)
from game.entities.upgrade_machine import UpgradeMachine
from game.entities.player import _make_player_surf
from game.entities.enemy  import _make_enemy_surf
from game.world.tilemap   import TileMap
from game.world.camera    import Camera
from game.world.map_data  import MAP_DATA
from game.ui.hud   import HUD
from game.ui.menus import Menus
from game.network.client   import GameClient
from game.network.messages import (
    MSG_GAME_STATE, MSG_LOBBY_STATE, MSG_START_GAME, make_input,
)


class ClientGame:
    """
    Client pur : pas de simulation locale.
    Recoit MSG_GAME_STATE du serveur et affiche.
    Envoie MSG_INPUT a 60Hz.
    """

    def __init__(self, server_ip: str, player_name: str = "Joueur",
                 screen: pygame.Surface | None = None):
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(f"{TITLE}  [CLIENT: {player_name}]")
        self._owns_screen = (screen is None)
        self.screen = screen if screen is not None else pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        pygame.mouse.set_visible(False)   # caché pendant le jeu (crosshair custom)

        self.player_name = player_name
        self.player_id   = None
        self._tick       = 0
        self._local_weapon_idx = 0

        # Connexion — attendre le MSG_WELCOME avec timeout
        self.net = GameClient(server_ip, player_name)
        self.net.start_in_thread()
        print(f"Connexion a {server_ip}:{NET_PORT}...")
        connected = self.net.wait_connected(timeout=10.0)
        if not connected or self.net.player_id is None:
            # Récupérer la raison depuis la queue
            reason = "timeout"
            msgs = self.net.get_messages()
            for m in msgs:
                if m.get("type") == "error":
                    r = m.get("reason", "")
                    if r == "server_full":
                        reason = "serveur plein"
                    elif r:
                        reason = r
            err_msg = f"Connexion impossible à {server_ip} ({reason})"
            print(err_msg)
            if self._owns_screen:
                pygame.quit()
                sys.exit(1)
            else:
                raise RuntimeError(err_msg)
        self.player_id = self.net.player_id
        print(f"Connecte en tant que Joueur {self.player_id}")

        # Monde local (rendu uniquement)
        self.tilemap = TileMap(MAP_DATA)
        self.camera  = Camera()

        # Machine d'amélioration (rendu local)
        col, row = UPGRADE_MACHINE_TILE
        self.upgrade_machine = UpgradeMachine(col, row)

        # Donnees recues du serveur
        self.remote_players:  dict[int, dict] = {}
        self.remote_enemies:  list[dict] = []
        self.remote_bullets:  list[dict] = []
        self.remote_grenades: list[dict] = []
        self.remote_pickups:  list[dict] = []
        self.wave_info: dict = {}
        self.local_state: dict = {}   # etat du joueur local

        self.state = STATE_LOBBY
        self._settings_return_state = STATE_PLAYING
        self._quit_requested = False
        self._reload_pressed = False
        self._heartbeat_timer = 0.0

        # Lobby : liste des joueurs en attente
        self._lobby_players: list[dict] = [
            {"player_id": self.player_id, "player_name": player_name, "is_host": False}
        ]

        # Données conservées pour l'écran game over
        self._gameover_scores: list[dict] = []
        self._gameover_wave: int = 0

        self.hud   = HUD()
        self.menus = Menus()
        self._font_small = pygame.font.SysFont("Arial", 12)
        self._font_med   = pygame.font.SysFont("Arial", 18, bold=True)

        # Surfaces pré-calculées pour les pickups (même rendu que le serveur)
        from game.entities.pickup import _make_weapon_icon
        self._pickup_surfs: dict[str, pygame.Surface] = {}
        for _wname in WEAPON_ORDER:
            _icon = _make_weapon_icon(_wname, 28)
            _size = 36
            _base = pygame.Surface((_size, _size), pygame.SRCALPHA)
            pygame.draw.circle(_base, (*COL_YELLOW, 180), (_size // 2, _size // 2), _size // 2)
            pygame.draw.circle(_base, (*COL_BLACK,  120), (_size // 2, _size // 2), _size // 2, 2)
            _base.blit(_icon, (4, 4))
            self._pickup_surfs[_wname] = _base

        # Surface pré-calculée pour les grenades (même rendu que Grenade.draw serveur)
        _gr = 7   # Grenade.RADIUS
        self._grenade_surf = pygame.Surface((_gr * 2, _gr * 2), pygame.SRCALPHA)
        pygame.draw.circle(self._grenade_surf, (60, 60, 60),    (_gr, _gr), _gr)
        pygame.draw.circle(self._grenade_surf, (100, 100, 100), (_gr, _gr), _gr, 2)

        # Données distantes : explosions (absentes avant ce correctif)
        self.remote_explosions: list[dict] = []

        # Score popups locaux (générés quand le score augmente entre deux snapshots)
        self._score_popups: list[dict] = []

        # Cache de surfaces par couleur pour les joueurs (evite de recalculer chaque frame)
        self._player_surf_cache: dict[tuple, pygame.Surface] = {}
        # Cache de surfaces par (type, couleur) pour les ennemis
        self._enemy_surf_cache: dict[tuple, pygame.Surface] = {}

    # ------------------------------------------------------------------
    def run(self, owns_pygame: bool = False):
        """Boucle principale.
        owns_pygame=True  -> lancé directement (__main__), sys.exit() à la fin.
        owns_pygame=False -> appelé depuis main.py ou _pre_menu, on fait return.
        """
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._tick += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.net.stop()
                    if owns_pygame:
                        pygame.quit()
                        sys.exit()
                    else:
                        pygame.mouse.set_visible(True)
                        return
                self._handle_event(event)

            self._process_server_messages()
            # Quitter si demandé (game over retour menu ou menu pause)
            if getattr(self, "_quit_requested", False):
                self.net.stop()
                if owns_pygame:
                    pygame.quit()
                    sys.exit()
                else:
                    pygame.mouse.set_visible(True)
                    return
            self._update_camera()
            # N'envoyer les inputs que pendant le jeu actif
            if self.state not in (STATE_PAUSED, STATE_SETTINGS, STATE_LOBBY):
                self._send_input()
            self.upgrade_machine.update(dt)
            # Décompte des score popups locaux
            for _pp in self._score_popups:
                _pp["timer"] -= dt
            self._score_popups = [_pp for _pp in self._score_popups if _pp["timer"] > 0]
            # Heartbeat : garder la connexion active même en pause
            self._heartbeat_timer += dt
            if self._heartbeat_timer >= 5.0:
                self._heartbeat_timer = 0.0
                self.net.send_input({"type": "ping"})
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _handle_event(self, event):
        # Lobby : pas d'action côté client (l'hôte lance)
        if self.state == STATE_LOBBY:
            return

        # Gestion du menu paramètres (priorité haute)
        if self.state == STATE_SETTINGS:
            result = self.menus.handle_settings_event(event)
            if result == "back":
                self.state = self._settings_return_state
            return

        # Gestion du game over
        if self.state == STATE_GAMEOVER:
            self.menus.handle_gameover_event(event)
            return

        # Gestion de la pause
        if event.type == pygame.KEYDOWN and event.key == KEYBINDS["pause"]:
            if self.state == STATE_PLAYING:
                self.state = STATE_PAUSED
            elif self.state == STATE_PAUSED:
                self.state = STATE_PLAYING
            return

        if self.state == STATE_PAUSED:
            self.menus.handle_pause_event(event)
            return

        if event.type == pygame.MOUSEWHEEL:
            self._local_weapon_idx = (self._local_weapon_idx - event.y) % len(WEAPON_ORDER)
        elif event.type == pygame.KEYDOWN:
            if event.key == KEYBINDS["slot_1"]: self._local_weapon_idx = 0
            if event.key == KEYBINDS["slot_2"]: self._local_weapon_idx = 1
            if event.key == KEYBINDS["slot_3"]: self._local_weapon_idx = 2
            if event.key == KEYBINDS["slot_4"]: self._local_weapon_idx = 3
            if event.key == KEYBINDS["weapon_prev"]:
                self._local_weapon_idx = (self._local_weapon_idx - 1) % len(WEAPON_ORDER)
            if event.key == KEYBINDS["upgrade"] and self._near_upgrade_machine():
                self.net.send_input({"type": "upgrade_req",
                                     "player_id": self.player_id})

    def _process_server_messages(self):
        for msg in self.net.get_messages():
            t = msg.get("type")
            if t == MSG_LOBBY_STATE:
                self._lobby_players = msg.get("players", self._lobby_players)
            elif t == MSG_START_GAME:
                self.state = STATE_PLAYING
                pygame.mouse.set_visible(False)
            elif t == MSG_GAME_STATE:
                self._apply_state(msg)
            elif t == "game_over":
                self.state = STATE_GAMEOVER
                self._gameover_wave = msg.get("wave_reached", 0)
                self._gameover_scores = sorted(
                    [{"player_name": p.get("player_name", "?"), "score": p.get("score", 0)}
                     for p in msg.get("scores", [])],
                    key=lambda x: x["score"], reverse=True
                )
            elif t == "upgrade_result":
                if msg.get("player_id") == self.player_id:
                    self.upgrade_machine._set_message(msg.get("message", ""))
            elif t == "error":
                reason = msg.get("reason", "erreur inconnue")
                print(f"Erreur réseau : {reason}")
                if reason == "disconnected_by_server":
                    # Retourner au menu proprement
                    self._quit_requested = True

    def _apply_state(self, state: dict):
        # Score avant mise à jour → pour détecter les kills
        old_score = self.local_state.get("score", 0)

        self.remote_players    = {p["player_id"]: p for p in state.get("players", [])}
        self.remote_enemies    = state.get("enemies", [])
        self.remote_bullets    = state.get("bullets", [])
        self.remote_grenades   = state.get("grenades", [])
        self.remote_pickups    = state.get("pickups", [])
        self.remote_explosions = state.get("explosions", [])
        self.wave_info         = {k: state[k] for k in
            ("wave_number", "wave_state", "wave_countdown", "enemies_remaining")
            if k in state}
        # Sync upgrade levels depuis serveur
        srv_levels = state.get("upgrade_levels", {})
        if srv_levels:
            self.upgrade_machine.upgrade_levels.update(srv_levels)
        if self.player_id in self.remote_players:
            self.local_state = dict(self.remote_players[self.player_id])
            self.local_state["all_players"] = list(self.remote_players.values())
            # Score popup local quand le score augmente (kill ennemi)
            new_score = self.local_state.get("score", 0)
            if new_score > old_score:
                diff = new_score - old_score
                self._score_popups.append({
                    "text":  f"+{diff}",
                    "x":     float(self.local_state.get("x", SCREEN_W / 2)),
                    "y":     float(self.local_state.get("y", SCREEN_H / 2)),
                    "timer": 1.0,
                })
            # NE PAS écraser _local_weapon_idx depuis le serveur :
            # le retour serveur confirme l'arme mais l'affichage reste instantané
            # (voir _draw_client_hud qui utilise self._local_weapon_idx directement)

    def _update_camera(self):
        px = float(self.local_state.get("x", SCREEN_W / 2))
        py = float(self.local_state.get("y", SCREEN_H / 2))
        fake_rect = pygame.Rect(int(px), int(py), 1, 1)
        self.camera.update(fake_rect)

    def _send_input(self):
        keys  = pygame.key.get_pressed()
        mbtns = pygame.mouse.get_pressed()
        mpos  = pygame.mouse.get_pos()

        # Aim angle en world coords
        ox = self.camera.offset.x
        oy = self.camera.offset.y
        world_mx = mpos[0] + ox
        world_my = mpos[1] + oy
        px = float(self.local_state.get("x", SCREEN_W / 2))
        py = float(self.local_state.get("y", SCREEN_H / 2))
        aim_angle = math.degrees(math.atan2(world_my - py, world_mx - px))

        dx = (1 if keys[KEYBINDS["move_right"]] else 0) - \
             (1 if keys[KEYBINDS["move_left"]]  else 0)
        dy = (1 if keys[KEYBINDS["move_down"]]  else 0) - \
             (1 if keys[KEYBINDS["move_up"]]    else 0)

        # Recharge : n'envoyer qu'une seule fois par pression (edge detection)
        if keys[KEYBINDS["reload"]]:
            if not self._reload_pressed:
                self.net.send_input({"type": "reload_req", "player_id": self.player_id})
                self._reload_pressed = True
        else:
            self._reload_pressed = False

        inp = make_input(
            player_id  = self.player_id,
            tick       = self._tick,
            dx         = float(dx),
            dy         = float(dy),
            aim_angle  = aim_angle,
            shooting   = bool(mbtns[0]),
            weapon_idx = self._local_weapon_idx,
            revive_held= bool(keys[KEYBINDS["revive"]]),
        )
        self.net.send_input(inp)

    # ------------------------------------------------------------------
    def _near_upgrade_machine(self) -> bool:
        """Verifie si le joueur local est a portee de la machine."""
        px = float(self.local_state.get("x", 0))
        py = float(self.local_state.get("y", 0))
        return (pygame.Vector2(px, py) - self.upgrade_machine.pos).length() \
               <= self.upgrade_machine.INTERACT_RANGE

    def _make_fake_player(self):
        """Cree un objet minimal pour draw_hud_prompt."""
        class _FakePlayer:
            pass
        fp = _FakePlayer()
        fp.active_weapon = WEAPON_ORDER[self._local_weapon_idx]
        fp.score         = int(self.local_state.get("score", 0))
        return fp

    # ------------------------------------------------------------------
    def _draw(self):
        # ---- Lobby ----
        if self.state == STATE_LOBBY:
            pygame.mouse.set_visible(True)
            self.menus.draw_lobby(
                self.screen,
                players=self._lobby_players,
                local_player_id=self.player_id,
                is_host=False,
            )
            return

        if self.state == STATE_SETTINGS:
            pygame.mouse.set_visible(True)
            self.menus.draw_settings_menu(self.screen)
            return

        pygame.mouse.set_visible(self.state == STATE_PAUSED)

        if self.state == STATE_GAMEOVER:
            pygame.mouse.set_visible(True)
            result = self.menus.draw_game_over(
                self.screen,
                int(self.local_state.get("score", 0)),
                self._gameover_wave,
                all_scores=self._gameover_scores,
            )
            if result == STATE_MENU:
                self._quit_requested = True
            return

        self.screen.fill((80, 72, 55))
        self.tilemap.draw(self.screen, self.camera.offset)

        # Pickups (rendu identique au serveur : icône + effet bob sinusoïdal)
        _t = pygame.time.get_ticks() / 1000.0
        for pk in self.remote_pickups:
            sx, sy = self.camera.apply_pos(pk["x"], pk["y"])
            wname = pk.get("weapon_name", "pistol")
            surf  = self._pickup_surfs.get(wname)
            if surf:
                phase = (pk["x"] + pk["y"]) * 0.01   # phase unique par position
                bob_y = math.sin((_t + phase) * 2.5 * math.pi * 2) * 3.0
                r = surf.get_rect(center=(int(sx), int(sy + bob_y)))
                self.screen.blit(surf, r)
                label = self._font_small.render(wname.upper(), True, COL_YELLOW)
                self.screen.blit(label, (r.centerx - label.get_width() // 2, r.top - 14))
            else:
                pygame.draw.circle(self.screen, COL_YELLOW, (int(sx), int(sy)), 8)
                label = self._font_small.render(wname.upper(), True, COL_YELLOW)
                self.screen.blit(label, (int(sx) - label.get_width()//2, int(sy) - 18))

        # Machine d'amélioration
        self.upgrade_machine.draw(self.screen, self.camera)

        # Joueurs
        for pid, p in self.remote_players.items():
            self._draw_remote_player(p, is_local=(pid == self.player_id))

        # Ennemis
        for e in self.remote_enemies:
            self._draw_remote_enemy(e)

        # Grenades (surface pré-rendue identique à Grenade.draw serveur)
        for g in self.remote_grenades:
            sx, sy = self.camera.apply_pos(g["x"], g["y"])
            r = self._grenade_surf.get_rect(center=(int(sx), int(sy)))
            self.screen.blit(self._grenade_surf, r)
            fuse = g.get("fuse_remaining", 0)
            if fuse > 0:
                fuse_surf = self._font_small.render(f"{fuse:.1f}", True, (255, 160, 30))
                self.screen.blit(fuse_surf, (int(sx) - fuse_surf.get_width()//2, int(sy) - 16))

        # Explosions (reçues du serveur depuis ce correctif)
        for expl in self.remote_explosions:
            _ex = expl["x"]; _ey = expl["y"]
            _er = int(expl.get("blast_radius", 110))
            _et = expl.get("timer", 0.0)
            _ed = expl.get("duration", 0.5)
            _progress = min(1.0, _et / max(0.001, _ed))
            _cur_r    = max(4, int(_er * (0.3 + 0.7 * _progress)))
            _alpha    = int(200 * (1.0 - _progress))
            _inner_r  = max(1, _cur_r - 15)
            _esx, _esy = self.camera.apply_pos(_ex, _ey)
            _surf_sz   = _er * 2 + 8
            _expl_surf = pygame.Surface((_surf_sz, _surf_sz), pygame.SRCALPHA)
            _cx = _cy = _surf_sz // 2
            pygame.draw.circle(_expl_surf, (255, 160, 30, _alpha), (_cx, _cy), _cur_r)
            pygame.draw.circle(_expl_surf, (255, 240, 150, _alpha), (_cx, _cy), _inner_r)
            self.screen.blit(_expl_surf, (int(_esx) - _cx, int(_esy) - _cy))

        # Balles (couleur et forme selon l'arme)
        for b in self.remote_bullets:
            sx, sy = self.camera.apply_pos(b["x"], b["y"])
            if b.get("owner") == "player":
                weapon = b.get("weapon", "pistol")
                if weapon == "pistol":
                    pygame.draw.circle(self.screen, (255, 230, 60), (int(sx), int(sy)), 2)
                elif weapon == "rifle":
                    vx = b.get("vel_x", 1.0)
                    vy = b.get("vel_y", 0.0)
                    angle = math.degrees(math.atan2(-vy, vx))
                    _bsurf = pygame.Surface((9, 2), pygame.SRCALPHA)
                    pygame.draw.rect(_bsurf, (220, 235, 255), (0, 0, 9, 2), border_radius=1)
                    _brot = pygame.transform.rotate(_bsurf, angle)
                    _br = _brot.get_rect(center=(int(sx), int(sy)))
                    self.screen.blit(_brot, _br)
                elif weapon == "smg":
                    pygame.draw.circle(self.screen, (255, 145, 30), (int(sx), int(sy)), 2)
                else:
                    pygame.draw.circle(self.screen, COL_BULLET_P, (int(sx), int(sy)), 3)
            else:
                pygame.draw.circle(self.screen, COL_BULLET_E, (int(sx), int(sy)), 3)

        # Score popups flottants (même logique que hud.draw_score_popups serveur)
        for _pp in self._score_popups:
            _psx, _psy = self.camera.apply_pos(_pp["x"], _pp["y"])
            _elapsed   = 1.0 - _pp["timer"]
            _psy      -= _elapsed * 50           # monte au fil du temps
            _palpha    = int(min(255, _pp["timer"] / 0.4 * 255))
            _pp_surf   = self._font_med.render(_pp["text"], True, COL_YELLOW)
            _pp_surf.set_alpha(_palpha)
            self.screen.blit(_pp_surf, (int(_psx) - _pp_surf.get_width() // 2, int(_psy)))

        # HUD depuis etat serveur
        if self.local_state:
            self._draw_client_hud()

        # Prompt machine d'amélioration
        if self._near_upgrade_machine() and self.local_state:
            self.upgrade_machine.draw_hud_prompt(
                self.screen, SCREEN_W, SCREEN_H, self._make_fake_player())
        self.upgrade_machine.draw_result_message(self.screen, SCREEN_W, SCREEN_H)

        # Indicateur connexion (en bas)
        net_txt = self._font_small.render("CLIENT connecte", True, (180, 220, 180))
        self.screen.blit(net_txt, (10, SCREEN_H - 20))

        # Menu pause en overlay
        if self.state == STATE_PAUSED:
            pause_result = self.menus.draw_pause(self.screen)
            if pause_result == STATE_SETTINGS:
                self._settings_return_state = STATE_PAUSED
                self.state = STATE_SETTINGS
            elif pause_result == "quit":
                self._quit_requested = True
            return   # Pas de crosshair pendant la pause

        # Crosshair unifié (cache aussi le curseur système)
        HUD.draw_crosshair(self.screen)

    # ------------------------------------------------------------------
    def _get_player_surf(self, color: tuple) -> pygame.Surface:
        """Retourne la surface joueur pour la couleur donnee, avec cache."""
        if color not in self._player_surf_cache:
            self._player_surf_cache[color] = _make_player_surf(color, 40)
        return self._player_surf_cache[color]

    def _get_enemy_surf(self, etype: str, color: tuple) -> pygame.Surface:
        """Retourne la surface ennemi pour le (type, couleur) donne, avec cache."""
        key = (etype, color)
        if key not in self._enemy_surf_cache:
            _size_map = {"soldier": 32, "officer": 26, "heavy": 40}
            size = _size_map.get(etype, 32)
            self._enemy_surf_cache[key] = _make_enemy_surf(color, size, etype)
        return self._enemy_surf_cache[key]

    # ------------------------------------------------------------------
    def _draw_remote_player(self, p: dict, is_local: bool):
        sx, sy = self.camera.apply_pos(p["x"], p["y"])
        pid    = p["player_id"]
        color  = PLAYER_COLORS[(pid - 1) % len(PLAYER_COLORS)]
        state  = p.get("state", "alive")

        if state == "dead":
            return

        if state == "down":
            col = (220, 60, 30) if (pygame.time.get_ticks() // 400) % 2 == 0 else (120, 30, 10)
            pygame.draw.circle(self.screen, col, (int(sx), int(sy)), 14)
            pygame.draw.circle(self.screen, COL_WHITE, (int(sx), int(sy)), 14, 2)
            down_t = p.get("down_timer", 0)
            txt = self._font_med.render(f"{int(down_t)}s", True, (255, 200, 50))
            self.screen.blit(txt, (int(sx) - txt.get_width()//2, int(sy) - 32))
            # Barre revive
            rp = p.get("revive_progress", 0)
            if rp > 0:
                bw = 40
                bx = int(sx) - bw//2
                by = int(sy) + 18
                pygame.draw.rect(self.screen, (60, 60, 60), (bx, by, bw, 5))
                pygame.draw.rect(self.screen, (50, 220, 50), (bx, by, int(bw * rp), 5))
            return

        # Rendu joueur distant : meme surface que player.py, avec rotation identique au serveur
        surf    = self._get_player_surf(color)
        rotated = pygame.transform.rotate(surf, -p.get("facing_angle", 0))
        r       = rotated.get_rect(center=(int(sx), int(sy)))
        self.screen.blit(rotated, r)

        # Nom du joueur
        name_surf = self._font_small.render(p.get("player_name", f"P{pid}"), True,
                                            (220, 220, 220))
        self.screen.blit(name_surf, (int(sx) - name_surf.get_width()//2, int(sy) - 30))

        # Barre HP
        hp    = p.get("hp", 100)
        maxhp = p.get("max_hp", 100)
        if hp < maxhp:
            bw = 36
            bx = int(sx) - bw//2
            by = int(sy) - 24
            pygame.draw.rect(self.screen, (180, 30, 30), (bx, by, bw, 4))
            ratio  = hp / max(1, maxhp)
            hp_col = (50, 200, 50) if ratio > 0.4 else (220, 80, 30)
            pygame.draw.rect(self.screen, hp_col, (bx, by, int(bw * ratio), 4))

    def _draw_remote_enemy(self, e: dict):
        sx, sy = self.camera.apply_pos(e["x"], e["y"])
        etype  = e.get("enemy_type", "soldier")

        # Couleur depuis ENEMY_TYPES (identique au serveur)
        color = ENEMY_TYPES.get(etype, ENEMY_TYPES["soldier"])["color"]

        # Rendu ennemi distant : meme surface que enemy.py, avec rotation identique au serveur
        surf    = self._get_enemy_surf(etype, color)
        rotated = pygame.transform.rotate(surf, -e.get("facing_angle", 0))
        r       = rotated.get_rect(center=(int(sx), int(sy)))
        self.screen.blit(rotated, r)

        # Barre HP
        hp    = e.get("hp", 60)
        maxhp = e.get("max_hp", 60)
        bw = 28
        bx = int(sx) - bw//2
        by = int(sy) - 20
        pygame.draw.rect(self.screen, (180, 30, 30), (bx, by, bw, 4))
        ratio = hp / max(1, maxhp)
        g = int(200 * ratio)
        pygame.draw.rect(self.screen, (200 - g, g, 20), (bx, by, int(bw * ratio), 4))

        # Indicateur d'etat IA (point colore)
        ai_state = e.get("ai_state", "patrol")
        if ai_state != "patrol":
            state_col = {
                "alert": (240, 200, 0),
                "chase": (255, 100, 0),
                "shoot": (255, 30,  30),
                "cover": (50,  150, 255),
            }.get(ai_state, (200, 200, 200))
            pygame.draw.circle(self.screen, state_col, (int(sx), int(sy) - 24), 3)

    def _draw_client_hud(self):
        """HUD reconstruit depuis le dict d'etat serveur."""
        self.hud.draw_from_state(
            self.screen, self.local_state, self.wave_info,
            self._local_weapon_idx, SCREEN_W, SCREEN_H,
        )


# ------------------------------------------------------------------
def _pre_menu() -> tuple[str, str, pygame.Surface]:
    """
    Affiche le menu principal puis le menu réseau (REJOINDRE pré-sélectionné).
    Retourne (server_ip, nom_joueur, surface) quand le joueur confirme REJOINDRE.
    """
    from game.ui.menus import Menus, NET_MENU_JOIN

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(True)   # curseur visible dans les menus
    clock  = pygame.time.Clock()
    menus  = Menus()
    # Pré-sélectionner l'option REJOINDRE dans le menu réseau
    menus._net_selected = 1

    state = STATE_MENU
    settings_return = STATE_MENU
    error_msg: str | None = None

    while True:
        dt = clock.tick(FPS) / 1000.0
        dt = min(dt, 0.05)
        menus.update(dt)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if state == STATE_MENU:
                menus.handle_main_event(event)

            elif state == STATE_NETWORK_MENU:
                if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    error_msg = None
                    state = STATE_MENU
                else:
                    result = menus.handle_net_event(event)
                    if result == NET_MENU_JOIN:
                        ip = menus.net_ip
                        if not ip:
                            error_msg = "Entrez une IP avant de confirmer."
                        else:
                            error_msg = None
                            return ip, menus.net_name or "Joueur", screen

            elif state == STATE_SETTINGS:
                res = menus.handle_settings_event(event)
                if res == "back":
                    state = settings_return

        # ---- dessin ----
        if state == STATE_MENU:
            action = menus.draw_main_menu(screen)
            if action == STATE_PLAYING:
                state = STATE_NETWORK_MENU
            elif action == STATE_SETTINGS:
                settings_return = STATE_MENU
                state = STATE_SETTINGS
            elif action == "quit":
                pygame.quit()
                sys.exit()

        elif state == STATE_NETWORK_MENU:
            menus.draw_network_menu(screen)
            if error_msg:
                font_err = pygame.font.SysFont("Arial", 18, bold=True)
                err_s = font_err.render(error_msg, True, (220, 60, 60))
                screen.blit(err_s, (SCREEN_W // 2 - err_s.get_width() // 2,
                                    SCREEN_H - 52))

        elif state == STATE_SETTINGS:
            menus.draw_settings_menu(screen)

        pygame.display.flip()


# ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) >= 2:
        # Lancement direct avec IP en argument (ex: python main_client.py 192.168.1.X)
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        server_ip = sys.argv[1]
        name      = sys.argv[2] if len(sys.argv) > 2 else "Joueur"
    else:
        server_ip, name, screen = _pre_menu()
    ClientGame(server_ip, player_name=name, screen=screen).run(owns_pygame=True)
