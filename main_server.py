# main_server.py - Hote : simulation autorite + rendu local joueur 1
import pygame
import sys
import math
import socket

from settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    STATE_PLAYING, STATE_GAMEOVER, STATE_MENU, STATE_SETTINGS, STATE_NETWORK_MENU,
    PLAYER_SPEED, WEAPONS, WEAPON_ORDER, PLAYER_COLORS,
    NET_PORT, NET_BROADCAST_RATE,
    REVIVE_RANGE, REVIVE_TIME, DOWN_TIMEOUT,
    UPGRADE_MACHINE_TILE, KEYBINDS,
)
from game.entities.upgrade_machine import UpgradeMachine
from game.world.tilemap    import TileMap
from game.world.camera     import Camera
from game.world.map_data   import MAP_DATA, PLAYER_START
from game.entities.player  import Player
from game.entities.bullet  import Bullet
from game.systems.pathfinding  import Pathfinder
from game.systems.wave_manager import WaveManager
from game.systems.collision    import move_and_collide
from game.ui.hud   import HUD
from game.ui.menus import Menus
from game.network.server   import GameServer
from game.network.messages import (
    MSG_INPUT, MSG_GAME_STATE,
    encode, make_game_state,
    serialize_player, serialize_enemy, serialize_bullet,
    serialize_grenade, serialize_pickup,
)


class ServerGame:
    """Boucle de jeu autorité. Simule tout, broadcaste l'état."""

    def __init__(self, host_name: str = "Host", screen: pygame.Surface | None = None):
        if not pygame.get_init():
            pygame.init()
        pygame.display.set_caption(f"{TITLE}  [HOST: {self._get_local_ip()}:{NET_PORT}]")
        self.screen = screen if screen is not None else pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        pygame.mouse.set_visible(False)

        # Serveur reseau
        self.server = GameServer()
        self.server.start_in_thread()
        local_ip = self._get_local_ip()
        print(f"\n=== SERVEUR DEMARRE ===")
        print(f"IP locale : {local_ip}")
        print(f"Port      : {NET_PORT}")
        print(f"Commande client : python main_client.py {local_ip} <Nom>")
        print(f"========================\n")

        # Joueurs : host = player_id 1
        self.host_player_id = 1
        self.players: dict[int, Player] = {}
        self._add_player(1, host_name)

        # Inputs en attente des clients (player_id -> dernier input)
        self.pending_inputs: dict[int, dict] = {}

        # Broadcast timer
        self._broadcast_timer   = 0.0
        self._broadcast_interval = 1.0 / NET_BROADCAST_RATE

        self._tick = 0
        self.state = STATE_PLAYING

        # Splash "IP à donner aux clients" affiché en superposition pendant quelques secondes
        self._local_ip = local_ip
        self._ip_splash_timer = 8.0   # secondes d'affichage

        self._init_world()
        self.hud   = HUD()
        self.menus = Menus()

    # ------------------------------------------------------------------
    def _get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except Exception:
            return "127.0.0.1"

    def _add_player(self, player_id: int, name: str):
        px, py = PLAYER_START
        color = PLAYER_COLORS[(player_id - 1) % len(PLAYER_COLORS)]
        p = Player(float(px), float(py),
                   player_id=player_id, player_name=name, color=color)
        self.players[player_id] = p

    def _init_world(self):
        self.tilemap    = TileMap(MAP_DATA)
        self.camera     = Camera()
        self.pathfinder = Pathfinder(self.tilemap)

        self.all_sprites     = pygame.sprite.Group()
        self.enemy_group     = pygame.sprite.Group()
        self.bullet_group    = pygame.sprite.Group()
        self.grenade_group   = pygame.sprite.Group()
        self.explosion_group = pygame.sprite.Group()
        self.pickup_group    = pygame.sprite.Group()

        # Machine d'amélioration
        col, row = UPGRADE_MACHINE_TILE
        self.upgrade_machine = UpgradeMachine(col, row)

        players_list = list(self.players.values())
        self.wave_manager = WaveManager(
            tilemap    = self.tilemap,
            pathfinder = self.pathfinder,
            players    = players_list,
            enemy_group  = self.enemy_group,
            pickup_group = self.pickup_group,
            all_groups   = (self.all_sprites,),
        )

    # ------------------------------------------------------------------
    def run(self):
        """Boucle principale. Retourne normalement pour permettre le retour au menu."""
        # Déterminer si on possède pygame (lancement direct) ou si on partage (depuis main.py)
        owns_pygame = len(sys.argv) > 1   # True si lancé directement avec argument
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._tick += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.server.stop()
                    if owns_pygame:
                        pygame.quit()
                        sys.exit()
                    else:
                        return   # Retour propre vers main.py
                self._handle_local_event(event)

            self._process_network_messages()
            self._update(dt)
            self._maybe_broadcast(dt)
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _handle_local_event(self, event):
        host = self.players.get(self.host_player_id)
        if not host:
            return
        if event.type == pygame.KEYDOWN and event.key == KEYBINDS["upgrade"]:
            if self.upgrade_machine.player_in_range(host):
                msg = self.upgrade_machine.try_upgrade(host)
                self.server.broadcast(encode({"type": "upgrade_result",
                                              "player_id": self.host_player_id,
                                              "message": msg}))
        host.handle_event(event)

    def _process_network_messages(self):
        for msg in self.server.get_pending_inputs():
            mtype = msg.get("type")

            if mtype == "player_joined":
                pid  = msg["player_id"]
                name = msg["player_name"]
                self._add_player(pid, name)
                players_list = list(self.players.values())
                self.wave_manager.players = players_list
                for enemy in self.enemy_group:
                    enemy.players = players_list
                    enemy.ai.players = players_list
                print(f"[+] {name} (ID {pid}) a rejoint la partie")

            elif mtype == "player_left":
                pid = msg["player_id"]
                if pid in self.players:
                    name = self.players[pid].player_name
                    del self.players[pid]
                    players_list = list(self.players.values())
                    self.wave_manager.players = players_list
                    print(f"[-] {name} (ID {pid}) a quitte la partie")

            elif "input" in msg:
                pid = msg["player_id"]
                inp = msg["input"]
                if inp.get("type") == MSG_INPUT:
                    self.pending_inputs[pid] = inp
                elif inp.get("type") == "reload_req":
                    player = self.players.get(pid)
                    if player and player.state == "alive" and not player.is_reloading:
                        wdata = player.get_weapon_data()
                        aw = player.active_weapon
                        if player.ammo.get(aw, 0) < wdata.get("max_ammo", 1):
                            player.is_reloading = True
                            player.reload_timer = wdata.get("reload_time", 1.5)
                elif inp.get("type") == "upgrade_req":
                    player = self.players.get(pid)
                    if player and self.upgrade_machine.player_in_range(player):
                        result_msg = self.upgrade_machine.try_upgrade(player)
                        self.server.broadcast(encode({"type": "upgrade_result",
                                                      "player_id": pid,
                                                      "message": result_msg}))

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        if self.state != STATE_PLAYING:
            return

        keys  = pygame.key.get_pressed()
        mbtns = pygame.mouse.get_pressed()
        mpos  = pygame.mouse.get_pos()

        # ---- Host (input local) ----
        host = self.players.get(self.host_player_id)
        if host and host.state == "alive":
            host.handle_input(
                keys, mbtns, mpos,
                self.camera, self.tilemap, dt,
                self.bullet_group, self.grenade_group,
                self.explosion_group, list(self.enemy_group),
            )
            # Revive via touche configurable
            if keys[KEYBINDS["revive"]]:
                self._try_revive(self.host_player_id, dt)
            else:
                if host:
                    # Reset progress si la touche est relachee
                    for pid, target in self.players.items():
                        if pid != self.host_player_id and target.state == "down":
                            if (host.pos - target.pos).length() <= REVIVE_RANGE:
                                target.revive_progress = max(0, target.revive_progress - dt * 2)

        # ---- Joueurs distants (inputs reseau) ----
        for pid, inp in list(self.pending_inputs.items()):
            player = self.players.get(pid)
            if not player or player.state != "alive":
                continue
            self._apply_remote_input(player, inp, dt)
            # Revive distant
            if inp.get("revive_held"):
                self._try_revive(pid, dt)

        # ---- Mise a jour "down" ----
        players_list = list(self.players.values())
        all_gone = all(p.state in ("dead", "down") for p in players_list) if players_list else False

        for player in players_list:
            player.update_popups(dt)
            if player.state == "down":
                player.update_down(dt)
                if player.state == "dead":
                    self.server.broadcast(encode({
                        "type": "player_dead",
                        "player_id": player.player_id,
                    }))

        # Game over si tous dead (pas "down")
        if players_list and all(p.state == "dead" for p in players_list):
            self.state = STATE_GAMEOVER
            scores = [
                {"player_id": p.player_id, "name": p.player_name, "score": p.score}
                for p in players_list
            ]
            self.server.broadcast(encode({
                "type": "game_over",
                "wave_reached": self.wave_manager.wave_number,
                "scores": scores,
            }))
            return

        # ---- Ennemis ----
        dead_enemies = []
        for enemy in list(self.enemy_group):
            enemy.update(dt, self.tilemap, players_list,
                         self.bullet_group, self.explosion_group)
            if not enemy.alive:
                # Attribuer le score au joueur le plus proche
                alive_players = [p for p in players_list if p.state == "alive"]
                if alive_players:
                    nearest = min(alive_players,
                                  key=lambda p: (p.pos - enemy.pos).length())
                    nearest.add_score(enemy.score_value)
                    nearest.add_score_popup(f"+{enemy.score_value}", enemy.pos)
                dead_enemies.append(enemy)

        # ---- Balles ----
        for bullet in list(self.bullet_group):
            bullet.update(dt, self.tilemap, self.enemy_group, players_list)

        # ---- Grenades ----
        for grenade in list(self.grenade_group):
            grenade.update(dt, self.tilemap, self.enemy_group, players_list)

        # ---- Explosions ----
        for expl in list(self.explosion_group):
            expl.update(dt, self.enemy_group, players_list)

        # ---- Ramassages ----
        for pickup in list(self.pickup_group):
            pickup.update(dt)
            for player in players_list:
                if player.state == "alive" and player.rect.colliderect(pickup.rect):
                    player.pick_up(pickup)
                    break

        # ---- Nettoyage ennemis ----
        for e in dead_enemies:
            self.enemy_group.discard(e) if hasattr(self.enemy_group, 'discard') else None
            if e in self.enemy_group:
                self.enemy_group.remove(e)
            if e in self.all_sprites:
                self.all_sprites.remove(e)

        # ---- Vagues ----
        self.wave_manager.players = players_list
        self.wave_manager.update(dt)

        # ---- Machine d'amélioration ----
        self.upgrade_machine.update(dt)

        # ---- Splash IP ----
        if self._ip_splash_timer > 0:
            self._ip_splash_timer -= dt

        # ---- Camera host ----
        if host:
            self.camera.update(host.rect)

    # ------------------------------------------------------------------
    def _apply_remote_input(self, player: Player, inp: dict, dt: float):
        """Applique un dict d'input reseau sur un joueur distant."""
        dx = float(inp.get("dx", 0))
        dy = float(inp.get("dy", 0))
        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        move_and_collide(player, dx * PLAYER_SPEED * dt, dy * PLAYER_SPEED * dt,
                         self.tilemap)
        player.pos = pygame.Vector2(player.rect.center)
        player.facing_angle     = float(inp.get("aim_angle", 0))
        player.active_weapon_idx = int(inp.get("weapon_idx", 0))

        player.fire_timer   = max(0.0, player.fire_timer   - dt)
        player.iframe_timer = max(0.0, player.iframe_timer - dt)

        # Rechargement
        if player.is_reloading:
            player.reload_timer -= dt
            if player.reload_timer <= 0:
                player.is_reloading = False
                player.ammo[player.active_weapon] = \
                    player.get_weapon_data().get("max_ammo", 1)

        aw = player.active_weapon

        # Grenade
        if inp.get("grenade_throw") and aw != "grenade":
            pass  # Ignore si pas grenade selectionnee
        if inp.get("shooting") and not player.is_reloading:
            if aw == "grenade":
                if player.fire_timer <= 0 and player.ammo.get("grenade", 0) > 0:
                    player._throw_grenade_from_angle(
                        player.facing_angle,
                        self.grenade_group, self.explosion_group,
                        list(self.enemy_group),
                    )
            else:
                if player.fire_timer <= 0 and player.ammo.get(aw, 0) > 0:
                    wdata  = player.get_weapon_data()
                    spread = wdata.get("spread", 0)
                    angle  = math.radians(player.facing_angle) + \
                             math.radians(__import__("random").uniform(-spread, spread))
                    speed  = wdata["bullet_speed"]
                    Bullet(
                        player.pos.x, player.pos.y,
                        math.cos(angle) * speed, math.sin(angle) * speed,
                        damage=wdata["damage"],
                        owner="player",
                        owner_id=player.player_id,
                        bullet_range=wdata.get("bullet_range", 600),
                        groups=(self.bullet_group,),
                    )
                    player.ammo[aw] -= 1
                    player.fire_timer = wdata["fire_rate"]
                    if player.ammo[aw] <= 0 and not player.is_reloading:
                        player.is_reloading = True
                        player.reload_timer = wdata.get("reload_time", 1.5)

    def _try_revive(self, reviver_id: int, dt: float):
        reviver = self.players.get(reviver_id)
        if not reviver or reviver.state != "alive":
            return
        for pid, target in self.players.items():
            if pid == reviver_id or target.state != "down":
                continue
            if (reviver.pos - target.pos).length() <= REVIVE_RANGE:
                target.revive_progress += dt / REVIVE_TIME
                if target.revive_progress >= 1.0:
                    target.revive()
                    self.server.broadcast(encode({
                        "type": "player_revived",
                        "player_id": pid,
                        "by_player_id": reviver_id,
                    }))
                return

    # ------------------------------------------------------------------
    def _maybe_broadcast(self, dt: float):
        self._broadcast_timer += dt
        if self._broadcast_timer < self._broadcast_interval:
            return
        self._broadcast_timer = 0.0

        players_data  = [serialize_player(p) for p in self.players.values()]
        enemies_data  = [serialize_enemy(e) for e in self.enemy_group]
        bullets_data  = [serialize_bullet(b) for b in self.bullet_group]
        grenades_data = [serialize_grenade(g) for g in self.grenade_group]
        pickups_data  = [serialize_pickup(pk) for pk in self.pickup_group]
        wave_info = {
            "wave_number":       self.wave_manager.wave_number,
            "wave_state":        self.wave_manager.state,
            "wave_countdown":    round(self.wave_manager.clear_countdown, 1),
            "enemies_remaining": self.wave_manager.enemies_remaining,
        }
        snapshot = make_game_state(
            self._tick,
            players_data, enemies_data,
            bullets_data, grenades_data,
            pickups_data, wave_info,
            upgrade_levels=dict(self.upgrade_machine.upgrade_levels),
        )
        self.server.broadcast(encode(snapshot))

    # ------------------------------------------------------------------
    def _draw(self):
        host = self.players.get(self.host_player_id)

        if self.state == STATE_GAMEOVER:
            self.screen.fill((10, 5, 5))
            font = pygame.font.SysFont("Arial", 52, bold=True)
            txt = font.render("PARTIE TERMINEE", True, (220, 50, 50))
            self.screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, SCREEN_H//2 - 60))
            font2 = pygame.font.SysFont("Arial", 24)
            txt2 = font2.render("Fermez la fenetre pour quitter", True, (180, 180, 180))
            self.screen.blit(txt2, (SCREEN_W//2 - txt2.get_width()//2, SCREEN_H//2 + 20))
            return

        self.screen.fill((80, 72, 55))
        self.tilemap.draw(self.screen, self.camera.offset)

        # Ramassages
        font_small = pygame.font.SysFont("Arial", 12)
        for pickup in self.pickup_group:
            pickup.draw(self.screen, self.camera, font_small)

        # Machine d'amélioration
        self.upgrade_machine.draw(self.screen, self.camera, host)

        # Tous les joueurs
        for player in self.players.values():
            player.draw(self.screen, self.camera)

        # Ennemis
        for enemy in self.enemy_group:
            enemy.draw(self.screen, self.camera)

        # Grenades
        for grenade in self.grenade_group:
            grenade.draw(self.screen, self.camera)

        # Explosions
        for expl in self.explosion_group:
            expl.draw(self.screen, self.camera)

        # Balles
        for bullet in self.bullet_group:
            bullet.draw(self.screen, self.camera)

        # HUD du host
        if host:
            self.hud.draw(self.screen, host, self.wave_manager)
            others = [p for pid, p in self.players.items()
                      if pid != self.host_player_id]
            self.hud.draw_other_players_hud(self.screen, others)
            self.hud.draw_score_popups(self.screen, host, self.camera)

        # Prompt machine d'amélioration (host)
        if host and self.upgrade_machine.player_in_range(host):
            self.upgrade_machine.draw_hud_prompt(self.screen, SCREEN_W, SCREEN_H, host)
        self.upgrade_machine.draw_result_message(self.screen, SCREEN_W, SCREEN_H)

        # Indicateur de connexion (barre en bas)
        font_net = pygame.font.SysFont("Arial", 13)
        nb_clients = len(self.server.clients)
        net_txt = font_net.render(
            f"HOST  {self._local_ip}:{NET_PORT}  |  {nb_clients} client(s)",
            True, (180, 220, 180))
        self.screen.blit(net_txt, (10, SCREEN_H - 20))

        # Splash IP en grand (8 premières secondes)
        if self._ip_splash_timer > 0:
            alpha = min(255, int(self._ip_splash_timer / 8.0 * 255 * 3))
            alpha = min(255, alpha)
            font_ip_big  = pygame.font.SysFont("Arial", 28, bold=True)
            font_ip_sub  = pygame.font.SysFont("Arial", 18)
            splash_w, splash_h = 500, 90
            splash_x = SCREEN_W // 2 - splash_w // 2
            splash_y = SCREEN_H - 130
            bg = pygame.Surface((splash_w, splash_h), pygame.SRCALPHA)
            bg.fill((0, 0, 0, min(200, alpha)))
            self.screen.blit(bg, (splash_x, splash_y))
            pygame.draw.rect(self.screen, (80, 200, 80),
                             (splash_x, splash_y, splash_w, splash_h), 2, border_radius=6)
            t1 = font_ip_big.render(
                f"Donnez cette IP aux clients : {self._local_ip}", True, (120, 255, 120))
            t2 = font_ip_sub.render(
                f"port {NET_PORT}  —  python main_client.py {self._local_ip}  [Nom]",
                True, (180, 220, 180))
            t1.set_alpha(alpha); t2.set_alpha(alpha)
            self.screen.blit(t1, (splash_x + splash_w // 2 - t1.get_width() // 2,
                                  splash_y + 12))
            self.screen.blit(t2, (splash_x + splash_w // 2 - t2.get_width() // 2,
                                  splash_y + 52))


# ------------------------------------------------------------------
def _pre_menu() -> tuple[str, pygame.Surface]:
    """
    Affiche le menu principal puis le menu réseau (HÉBERGER pré-sélectionné).
    Retourne (nom_du_host, surface) quand le joueur confirme HÉBERGER.
    """
    from game.ui.menus import Menus, NET_MENU_HOST

    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption(TITLE)
    pygame.mouse.set_visible(True)   # curseur visible dans les menus
    clock  = pygame.time.Clock()
    menus  = Menus()
    # Pré-sélectionner l'option HÉBERGER dans le menu réseau
    menus._net_selected = 0

    state = STATE_MENU
    settings_return = STATE_MENU

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
                    state = STATE_MENU
                else:
                    result = menus.handle_net_event(event)
                    if result == NET_MENU_HOST:
                        # Cacher le curseur avant de démarrer le jeu
                        pygame.mouse.set_visible(False)
                        return menus.net_name or "Host", screen

            elif state == STATE_SETTINGS:
                res = menus.handle_settings_event(event)
                if res == "back":
                    state = settings_return

        # ---- gestion curseur selon état ----
        in_menu = state in (STATE_MENU, STATE_NETWORK_MENU, STATE_SETTINGS)
        pygame.mouse.set_visible(in_menu)

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

        elif state == STATE_SETTINGS:
            menus.draw_settings_menu(screen)

        pygame.display.flip()


# ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Lancement direct avec nom en argument (ex: python main_server.py Host)
        pygame.init()
        screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.mouse.set_visible(False)
        name = sys.argv[1]
    else:
        name, screen = _pre_menu()
    ServerGame(host_name=name, screen=screen).run()
