# main_client.py - Client leger : rendu depuis snapshots serveur
import pygame
import sys
import math

from settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    WEAPON_ORDER, WEAPONS, PLAYER_COLORS,
    MAP_W, MAP_H, DOWN_TIMEOUT,
    COL_BULLET_P, COL_BULLET_E, COL_YELLOW, COL_WHITE, COL_GREY, COL_RED,
    UPGRADE_MACHINE_TILE,
)
from game.entities.upgrade_machine import UpgradeMachine
from game.world.tilemap   import TileMap
from game.world.camera    import Camera
from game.world.map_data  import MAP_DATA
from game.ui.hud   import HUD
from game.ui.menus import Menus
from game.network.client   import GameClient
from game.network.messages import MSG_INPUT, MSG_GAME_STATE, make_input


class ClientGame:
    """
    Client pur : pas de simulation locale.
    Recoit MSG_GAME_STATE du serveur et affiche.
    Envoie MSG_INPUT a 60Hz.
    """

    def __init__(self, server_ip: str, player_name: str = "Joueur"):
        pygame.init()
        pygame.display.set_caption(f"{TITLE}  [CLIENT: {player_name}]")
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        pygame.mouse.set_visible(False)

        self.player_name = player_name
        self.player_id   = None
        self._tick       = 0
        self._local_weapon_idx = 0

        # Connexion
        self.net = GameClient(server_ip, player_name)
        self.net.start_in_thread()
        print(f"Connexion a {server_ip}...")
        if not self.net.wait_connected(timeout=10.0):
            print("Impossible de se connecter. Verifiez l'IP et le serveur.")
            pygame.quit()
            sys.exit(1)
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

        self.state = "playing"

        self.hud   = HUD()
        self.menus = Menus()
        self._font_small = pygame.font.SysFont("Arial", 12)
        self._font_med   = pygame.font.SysFont("Arial", 18, bold=True)

    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)
            self._tick += 1

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.net.stop()
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            self._process_server_messages()
            self._update_camera()
            self._send_input()
            self.upgrade_machine.update(dt)
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _handle_event(self, event):
        if event.type == pygame.MOUSEWHEEL:
            self._local_weapon_idx = (self._local_weapon_idx - event.y) % len(WEAPON_ORDER)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1: self._local_weapon_idx = 0
            if event.key == pygame.K_2: self._local_weapon_idx = 1
            if event.key == pygame.K_3: self._local_weapon_idx = 2
            if event.key == pygame.K_4: self._local_weapon_idx = 3
            if event.key == pygame.K_q:
                self._local_weapon_idx = (self._local_weapon_idx - 1) % len(WEAPON_ORDER)
            if event.key == pygame.K_f and self._near_upgrade_machine():
                self.net.send_input({"type": "upgrade_req",
                                     "player_id": self.player_id})

    def _process_server_messages(self):
        for msg in self.net.get_messages():
            t = msg.get("type")
            if t == MSG_GAME_STATE:
                self._apply_state(msg)
            elif t == "game_over":
                self.state = "gameover"
            elif t == "upgrade_result":
                if msg.get("player_id") == self.player_id:
                    self.upgrade_machine._set_message(msg.get("message", ""))
            elif t == "error":
                print(f"Erreur serveur : {msg.get('reason')}")

    def _apply_state(self, state: dict):
        self.remote_players  = {p["player_id"]: p for p in state.get("players", [])}
        self.remote_enemies  = state.get("enemies", [])
        self.remote_bullets  = state.get("bullets", [])
        self.remote_grenades = state.get("grenades", [])
        self.remote_pickups  = state.get("pickups", [])
        self.wave_info       = {k: state[k] for k in
            ("wave_number", "wave_state", "wave_countdown", "enemies_remaining")
            if k in state}
        # Sync upgrade levels depuis serveur
        srv_levels = state.get("upgrade_levels", {})
        if srv_levels:
            self.upgrade_machine.upgrade_levels.update(srv_levels)
        if self.player_id in self.remote_players:
            self.local_state = self.remote_players[self.player_id]
            # Sync weapon index depuis serveur
            self._local_weapon_idx = self.local_state.get("weapon_idx", 0)

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

        dx = (1 if keys[pygame.K_d] or keys[pygame.K_RIGHT] else 0) - \
             (1 if keys[pygame.K_a] or keys[pygame.K_LEFT]  else 0)
        dy = (1 if keys[pygame.K_s] or keys[pygame.K_DOWN]  else 0) - \
             (1 if keys[pygame.K_w] or keys[pygame.K_UP]    else 0)

        # Recharge
        if keys[pygame.K_r]:
            self.net.send_input({"type": "reload_req", "player_id": self.player_id})

        inp = make_input(
            player_id    = self.player_id,
            tick         = self._tick,
            dx           = float(dx),
            dy           = float(dy),
            aim_angle    = aim_angle,
            shooting     = bool(mbtns[0]),
            weapon_idx   = self._local_weapon_idx,
            grenade_throw= bool(mbtns[2]),
            revive_held  = bool(keys[pygame.K_e]),
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
        if self.state == "gameover":
            self.screen.fill((10, 5, 5))
            font = pygame.font.SysFont("Arial", 52, bold=True)
            txt = font.render("MORT AU COMBAT", True, (220, 50, 50))
            self.screen.blit(txt, (SCREEN_W//2 - txt.get_width()//2, SCREEN_H//2 - 60))
            return

        self.screen.fill((80, 72, 55))
        self.tilemap.draw(self.screen, self.camera.offset)

        # Pickups
        for pk in self.remote_pickups:
            sx, sy = self.camera.apply_pos(pk["x"], pk["y"])
            pygame.draw.circle(self.screen, COL_YELLOW, (int(sx), int(sy)), 8)
            label = self._font_small.render(pk["weapon_name"].upper(), True, COL_YELLOW)
            self.screen.blit(label, (int(sx) - label.get_width()//2, int(sy) - 18))

        # Machine d'amélioration
        self.upgrade_machine.draw(self.screen, self.camera)

        # Joueurs
        for pid, p in self.remote_players.items():
            self._draw_remote_player(p, is_local=(pid == self.player_id))

        # Ennemis
        for e in self.remote_enemies:
            self._draw_remote_enemy(e)

        # Grenades
        for g in self.remote_grenades:
            sx, sy = self.camera.apply_pos(g["x"], g["y"])
            pygame.draw.circle(self.screen, (60, 60, 60), (int(sx), int(sy)), 6)
            # Compte a rebours
            fuse = g.get("fuse_remaining", 0)
            if fuse > 0:
                t = self._font_small.render(f"{fuse:.1f}", True, (255, 160, 30))
                self.screen.blit(t, (int(sx) - t.get_width()//2, int(sy) - 16))

        # Balles
        for b in self.remote_bullets:
            sx, sy = self.camera.apply_pos(b["x"], b["y"])
            col = COL_BULLET_P if b.get("owner") == "player" else COL_BULLET_E
            pygame.draw.circle(self.screen, col, (int(sx), int(sy)), 3)

        # HUD depuis etat serveur
        if self.local_state:
            self._draw_client_hud()

        # Prompt machine d'amélioration
        if self._near_upgrade_machine() and self.local_state:
            self.upgrade_machine.draw_hud_prompt(
                self.screen, SCREEN_W, SCREEN_H, self._make_fake_player())
        self.upgrade_machine.draw_result_message(self.screen, SCREEN_W, SCREEN_H)

        # Indicateur connexion
        net_txt = self._font_small.render("CLIENT connecte", True, (180, 220, 180))
        self.screen.blit(net_txt, (10, 10))

        # Crosshair
        mx, my = pygame.mouse.get_pos()
        pygame.draw.line(self.screen, COL_WHITE, (mx-10, my), (mx-4, my), 2)
        pygame.draw.line(self.screen, COL_WHITE, (mx+4,  my), (mx+10, my), 2)
        pygame.draw.line(self.screen, COL_WHITE, (mx, my-10), (mx, my-4), 2)
        pygame.draw.line(self.screen, COL_WHITE, (mx, my+4),  (mx, my+10), 2)

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

        # Corps
        pygame.draw.circle(self.screen, color, (int(sx), int(sy)), 14)
        # Casque
        hc = (max(0, color[0]-40), max(0, color[1]-40), max(0, color[2]-40))
        pygame.draw.ellipse(self.screen, hc,
                            (int(sx)-9, int(sy)-19, 18, 12))
        # Arme (ligne dans la direction de visee)
        angle_rad = math.radians(p.get("facing_angle", 0))
        ex = sx + math.cos(angle_rad) * 18
        ey = sy + math.sin(angle_rad) * 18
        pygame.draw.line(self.screen, (50, 50, 50),
                         (int(sx), int(sy)), (int(ex), int(ey)), 3)

        # Nom
        name_surf = self._font_small.render(p.get("player_name", f"P{pid}"), True,
                                            (220, 220, 220))
        self.screen.blit(name_surf, (int(sx) - name_surf.get_width()//2, int(sy) - 30))

        # Barre HP
        hp    = p.get("hp", 100)
        maxhp = p.get("max_hp", 100)
        if hp < maxhp:
            bw = 32
            bx = int(sx) - bw//2
            by = int(sy) - 22
            pygame.draw.rect(self.screen, (180, 30, 30), (bx, by, bw, 4))
            ratio = hp / maxhp
            pygame.draw.rect(self.screen, (50, 200, 50),
                             (bx, by, int(bw * ratio), 4))

    def _draw_remote_enemy(self, e: dict):
        sx, sy = self.camera.apply_pos(e["x"], e["y"])
        etype  = e.get("enemy_type", "soldier")
        colors = {"soldier": (180, 50, 50), "officer": (200, 80, 30), "heavy": (140, 30, 100)}
        color  = colors.get(etype, (180, 50, 50))

        pygame.draw.circle(self.screen, color, (int(sx), int(sy)), 12)
        hc = (max(0,color[0]-40), max(0,color[1]-30), max(0,color[2]-30))
        pygame.draw.ellipse(self.screen, hc, (int(sx)-7, int(sy)-15, 14, 9))
        # Arme
        angle_rad = math.radians(e.get("facing_angle", 0))
        ex = sx + math.cos(angle_rad) * 15
        ey = sy + math.sin(angle_rad) * 15
        pygame.draw.line(self.screen, (40, 40, 40),
                         (int(sx), int(sy)), (int(ex), int(ey)), 2)

        # Barre HP
        hp    = e.get("hp", 60)
        maxhp = e.get("max_hp", 60)
        bw = 24
        bx = int(sx) - bw//2
        by = int(sy) - 18
        pygame.draw.rect(self.screen, (180, 30, 30), (bx, by, bw, 3))
        ratio = hp / max(1, maxhp)
        g = int(200 * ratio)
        pygame.draw.rect(self.screen, (200-g, g, 20), (bx, by, int(bw*ratio), 3))

    def _draw_client_hud(self):
        """HUD reconstruit depuis le dict d'etat serveur."""
        p = self.local_state

        # Barre de vie
        hp    = p.get("hp", 100)
        maxhp = p.get("max_hp", 100)
        bar_w, bar_h = 200, 20
        bx, by = 20, SCREEN_H - 50
        pygame.draw.rect(self.screen, (30, 30, 30), (bx, by, bar_w, bar_h), border_radius=3)
        ratio = hp / max(1, maxhp)
        col = (50, 200, 50) if ratio > 0.4 else (220, 50, 50)
        pygame.draw.rect(self.screen, col, (bx, by, int(bar_w*ratio), bar_h), border_radius=3)
        pygame.draw.rect(self.screen, COL_WHITE, (bx, by, bar_w, bar_h), 1, border_radius=3)
        hp_txt = self._font_small.render(f"HP  {hp}/{maxhp}", True, COL_WHITE)
        self.screen.blit(hp_txt, (bx, by - 16))

        # Score
        score_txt = self._font_med.render(f"SCORE  {p.get('score', 0):,}", True, COL_WHITE)
        self.screen.blit(score_txt, (SCREEN_W//2 - score_txt.get_width()//2, 10))

        # Vague
        wn   = self.wave_info.get("wave_number", 0)
        wrem = self.wave_info.get("enemies_remaining", 0)
        wave_txt = self._font_med.render(f"VAGUE  {wn}  |  Ennemis: {wrem}", True, COL_YELLOW)
        self.screen.blit(wave_txt, (SCREEN_W - wave_txt.get_width() - 20, 20))

        # Inventaire simplifie
        ammo  = p.get("ammo", {})
        aw_idx = p.get("weapon_idx", 0)
        slot_w = 60
        total_w = len(WEAPON_ORDER) * (slot_w + 6) - 6
        sx0 = SCREEN_W//2 - total_w//2
        sy0 = SCREEN_H - slot_w - 12
        for i, wn2 in enumerate(WEAPON_ORDER):
            sx = sx0 + i * (slot_w + 6)
            is_active = (i == aw_idx)
            bg = (60, 55, 40) if is_active else (30, 28, 22)
            border = COL_YELLOW if is_active else (60, 60, 60)
            pygame.draw.rect(self.screen, bg, (sx, sy0, slot_w, slot_w), border_radius=4)
            pygame.draw.rect(self.screen, border, (sx, sy0, slot_w, slot_w),
                             2 if is_active else 1, border_radius=4)
            n_surf = self._font_small.render(wn2.upper(), True,
                                             COL_YELLOW if is_active else COL_GREY)
            self.screen.blit(n_surf, (sx + slot_w//2 - n_surf.get_width()//2, sy0 + 6))
            cur = ammo.get(wn2, 0)
            mx2 = WEAPONS.get(wn2, {}).get("max_ammo", 0)
            col2 = COL_WHITE if cur > mx2 * 0.3 else COL_RED
            a_surf = self._font_small.render(f"{cur}/{mx2}", True, col2)
            self.screen.blit(a_surf, (sx + slot_w//2 - a_surf.get_width()//2,
                                      sy0 + slot_w - 18))

        # Alliés HUD
        others = [pdata for pid, pdata in self.remote_players.items()
                  if pid != self.player_id]
        y_off = 80
        for pdata in others:
            pid2   = pdata["player_id"]
            name2  = pdata.get("player_name", f"P{pid2}")
            hp2    = pdata.get("hp", 100)
            maxhp2 = pdata.get("max_hp", 100)
            state2 = pdata.get("state", "alive")
            bw = 120
            bx2, by2 = 20, y_off
            pygame.draw.rect(self.screen, (30, 30, 30), (bx2, by2, bw, 12))
            if state2 == "alive":
                r2 = hp2 / max(1, maxhp2)
                gc = (50, 200, 50) if r2 > 0.4 else (220, 50, 50)
                pygame.draw.rect(self.screen, gc, (bx2, by2, int(bw*r2), 12))
            elif state2 == "down":
                dt2 = pdata.get("down_timer", 0)
                r2  = dt2 / DOWN_TIMEOUT
                pygame.draw.rect(self.screen, (220, 140, 30),
                                 (bx2, by2, int(bw*r2), 12))
            pygame.draw.rect(self.screen, (100, 100, 100), (bx2, by2, bw, 12), 1)
            n2 = self._font_small.render(f"{name2} {'[A TERRE]' if state2=='down' else ''}",
                                         True, (200, 200, 200))
            self.screen.blit(n2, (bx2 + bw + 6, by2))
            y_off += 22

        # Rechargement
        if p.get("is_reloading"):
            rp = p.get("reload_progress", 0)
            rld = self._font_med.render("RECHARGEMENT...", True, (80, 160, 255))
            self.screen.blit(rld, (SCREEN_W//2 - rld.get_width()//2, SCREEN_H//2 + 60))
            bar_w2 = 200
            bx3 = SCREEN_W//2 - bar_w2//2
            by3 = SCREEN_H//2 + 90
            pygame.draw.rect(self.screen, (30, 30, 30), (bx3, by3, bar_w2, 6))
            pygame.draw.rect(self.screen, (80, 160, 255),
                             (bx3, by3, int(bar_w2 * rp), 6))

        # Prompt revive
        pstate = p.get("state", "alive")
        if pstate == "down":
            dt3 = p.get("down_timer", 0)
            down_txt = self._font_med.render(
                f"A TERRE - {int(dt3)}s avant elimination", True, (220, 80, 30))
            self.screen.blit(down_txt, (SCREEN_W//2 - down_txt.get_width()//2,
                                        SCREEN_H//2 - 30))


# ------------------------------------------------------------------
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage : python main_client.py <IP_SERVEUR> [NomJoueur]")
        sys.exit(1)
    server_ip = sys.argv[1]
    name      = sys.argv[2] if len(sys.argv) > 2 else "Joueur"
    game = ClientGame(server_ip, player_name=name)
    game.run()
