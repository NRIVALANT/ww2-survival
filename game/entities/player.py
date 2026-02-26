# player.py - Entite joueur (mono + multi)
import pygame
import math
import random
import copy
from settings import (
    PLAYER_SPEED, PLAYER_HP, PLAYER_RADIUS, PLAYER_IFRAMES,
    WEAPONS, WEAPON_ORDER,
    COL_PLAYER, COL_HELMET_P, COL_BLACK, COL_WHITE, COL_GREY,
    TILE_SIZE, PLAYER_COLORS, DOWN_TIMEOUT, REVIVE_TIME,
)
from game.systems.collision import move_and_collide


def _make_player_surf(color: tuple, size: int = 32) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    # Corps
    pygame.draw.circle(surf, color, (cx, cy), size // 3)
    # Casque (plus fonce)
    hc = (max(0, color[0] - 40), max(0, color[1] - 40), max(0, color[2] - 40))
    pygame.draw.ellipse(surf, hc, (cx - 9, cy - 13, 18, 12))
    # Arme (pointe vers la droite = angle 0)
    pygame.draw.rect(surf, (50, 50, 50),
                     (cx + 2, cy - 2, size // 2 - 4, 4))
    return surf


class Player(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float,
                 player_id: int = 0, player_name: str = "Joueur",
                 color: tuple = None, groups=()):
        super().__init__(*groups)
        self.player_id   = player_id
        self.player_name = player_name
        self.color       = color or PLAYER_COLORS[player_id % len(PLAYER_COLORS)]

        self.pos    = pygame.Vector2(x, y)
        self.hp     = PLAYER_HP
        self.max_hp = PLAYER_HP
        self.alive  = True   # retro-compat (True si alive ou down, False si dead)
        self.score  = 0
        self.score_popups: list[dict] = []

        # Etat multi (alive / down / dead)
        self.state          = "alive"
        self.down_timer     = 0.0    # countdown avant mort definitive
        self.revive_progress= 0.0    # 0..1

        # Armes : copies des definitions
        self.weapons: dict[str, dict] = {}
        self.ammo:    dict[str, int]  = {}
        for name, data in WEAPONS.items():
            self.weapons[name] = copy.deepcopy(data)
            self.ammo[name]    = data.get("max_ammo", 0)

        self.active_weapon_idx = 0
        self.fire_timer        = 0.0
        self.reload_timer      = 0.0
        self.is_reloading      = False
        self.iframe_timer      = 0.0

        self._base_surf = _make_player_surf(self.color, 32)
        self.facing_angle = 0.0

        self.image = self._base_surf
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    # ------------------------------------------------------------------
    @property
    def active_weapon(self) -> str:
        return WEAPON_ORDER[self.active_weapon_idx]

    def get_weapon_data(self) -> dict:
        return self.weapons[self.active_weapon]

    # ------------------------------------------------------------------
    def handle_input(self, keys, mouse_buttons, mouse_pos: tuple,
                     camera, tilemap, dt: float,
                     bullet_group, grenade_group, explosion_group,
                     enemy_group) -> None:
        if self.state != "alive":
            return

        # Mouvement
        dx = dy = 0
        if keys[pygame.K_w] or keys[pygame.K_UP]:    dy -= 1
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:  dy += 1
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:  dx -= 1
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx += 1

        if dx != 0 and dy != 0:
            dx *= 0.7071
            dy *= 0.7071

        move_and_collide(self, dx * PLAYER_SPEED * dt, dy * PLAYER_SPEED * dt, tilemap)
        self.pos = pygame.Vector2(self.rect.center)

        # Visee
        world_mouse = camera.screen_to_world(mouse_pos[0], mouse_pos[1])
        aim_dx = world_mouse.x - self.pos.x
        aim_dy = world_mouse.y - self.pos.y
        self.facing_angle = math.degrees(math.atan2(aim_dy, aim_dx))

        # Timers
        self.fire_timer   = max(0.0, self.fire_timer   - dt)
        self.iframe_timer = max(0.0, self.iframe_timer - dt)

        # Rechargement
        if self.is_reloading:
            self.reload_timer -= dt
            if self.reload_timer <= 0:
                self.is_reloading = False
                self.ammo[self.active_weapon] = self.get_weapon_data()["max_ammo"]

        # Tir
        wdata = self.get_weapon_data()
        if mouse_buttons[0] and not wdata.get("auto", False):
            shooting = (not getattr(self, "_was_shooting", False))
        else:
            shooting = bool(mouse_buttons[0])
        self._was_shooting = mouse_buttons[0]

        if mouse_buttons[0] and not self.is_reloading:
            aw = self.active_weapon
            if aw == "grenade":
                if self.fire_timer <= 0 and self.ammo[aw] > 0:
                    self._throw_grenade(world_mouse, grenade_group, explosion_group,
                                        enemy_group)
            else:
                if self.fire_timer <= 0 and self.ammo[aw] > 0:
                    self._shoot(world_mouse, bullet_group, enemy_group)

        # Rechargement manuel
        if keys[pygame.K_r] and not self.is_reloading:
            wdata = self.get_weapon_data()
            if "reload_time" in wdata and self.ammo.get(self.active_weapon, 0) < wdata["max_ammo"]:
                self.is_reloading = True
                self.reload_timer = wdata["reload_time"]

    def handle_event(self, event):
        """Appele pour pygame.MOUSEWHEEL et touches Q/E."""
        if event.type == pygame.MOUSEWHEEL:
            self._cycle_weapon(-event.y)
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_q:
                self._cycle_weapon(-1)
            elif event.key in (pygame.K_1, pygame.K_KP1):
                self.active_weapon_idx = 0
            elif event.key in (pygame.K_2, pygame.K_KP2):
                self.active_weapon_idx = 1
            elif event.key in (pygame.K_3, pygame.K_KP3):
                self.active_weapon_idx = 2
            elif event.key in (pygame.K_4, pygame.K_KP4):
                self.active_weapon_idx = 3
            # K_e est reserve au revive en multi (gere ailleurs)

    def _cycle_weapon(self, direction: int):
        self.active_weapon_idx = (self.active_weapon_idx + direction) % len(WEAPON_ORDER)
        self.is_reloading = False

    # ------------------------------------------------------------------
    def _shoot(self, target_world: pygame.Vector2, bullet_group, enemy_group):
        from game.entities.bullet import Bullet
        wdata  = self.get_weapon_data()
        spread = wdata.get("spread", 0)
        base_angle = math.atan2(target_world.y - self.pos.y,
                                target_world.x - self.pos.x)
        angle = base_angle + math.radians(random.uniform(-spread, spread))
        speed = wdata["bullet_speed"]
        Bullet(
            self.pos.x, self.pos.y,
            math.cos(angle) * speed, math.sin(angle) * speed,
            damage=wdata["damage"],
            owner="player",
            owner_id=self.player_id,
            bullet_range=wdata.get("bullet_range", 600),
            groups=(bullet_group,),
        )
        self.ammo[self.active_weapon] -= 1
        self.fire_timer = wdata["fire_rate"]
        if self.ammo[self.active_weapon] <= 0 and not self.is_reloading:
            self.is_reloading = True
            self.reload_timer = wdata.get("reload_time", 1.5)

    def _throw_grenade(self, target_world: pygame.Vector2,
                       grenade_group, explosion_group, enemy_group):
        from game.entities.grenade import Grenade
        wdata = self.weapons["grenade"]
        dx = target_world.x - self.pos.x
        dy = target_world.y - self.pos.y
        dist = math.hypot(dx, dy)
        if dist > 0:
            dx /= dist
            dy /= dist
        speed = wdata["throw_speed"]
        Grenade(
            self.pos.x, self.pos.y,
            dx * speed, dy * speed,
            fuse_time   = wdata["fuse_time"],
            blast_radius= wdata["blast_radius"],
            damage      = wdata["damage"],
            groups=(grenade_group,),
            explosion_groups=(explosion_group,),
        )
        self.ammo["grenade"] -= 1
        self.fire_timer = wdata["fire_rate"]

    def _throw_grenade_from_angle(self, aim_angle_deg: float,
                                  grenade_group, explosion_group, enemy_group):
        """Lancer une grenade depuis un angle (pour les inputs reseau)."""
        from game.entities.grenade import Grenade
        wdata = self.weapons["grenade"]
        if self.fire_timer > 0 or self.ammo.get("grenade", 0) <= 0:
            return
        angle_rad = math.radians(aim_angle_deg)
        speed = wdata["throw_speed"]
        Grenade(
            self.pos.x, self.pos.y,
            math.cos(angle_rad) * speed, math.sin(angle_rad) * speed,
            fuse_time   = wdata["fuse_time"],
            blast_radius= wdata["blast_radius"],
            damage      = wdata["damage"],
            groups=(grenade_group,),
            explosion_groups=(explosion_group,),
        )
        self.ammo["grenade"] -= 1
        self.fire_timer = wdata["fire_rate"]

    # ------------------------------------------------------------------
    def take_damage(self, amount: int):
        if self.iframe_timer > 0 or self.state != "alive":
            return
        self.hp -= amount
        self.iframe_timer = PLAYER_IFRAMES
        if self.hp <= 0:
            self.hp    = 0
            self.state = "down"
            self.down_timer = DOWN_TIMEOUT
            self.alive = False   # retro-compat

    def update_down(self, dt: float):
        """Appelée chaque frame si state == 'down' (cote serveur)."""
        if self.state == "down":
            self.down_timer -= dt
            if self.down_timer <= 0:
                self.state = "dead"

    def revive(self):
        """Releve le joueur (appele par le serveur apres 3s de revive)."""
        self.state          = "alive"
        self.alive          = True
        self.hp             = max(1, int(self.max_hp * 0.3))
        self.down_timer     = 0.0
        self.revive_progress= 0.0
        self.iframe_timer   = PLAYER_IFRAMES * 3   # invincible 1.2s apres revive

    def respawn(self, x: float, y: float):
        """Respawn en debut de manche suivante."""
        self.state          = "alive"
        self.alive          = True
        self.hp             = self.max_hp
        self.down_timer     = 0.0
        self.revive_progress= 0.0
        self.iframe_timer   = 0.0
        self.pos            = pygame.Vector2(x, y)
        self.rect.center    = (int(x), int(y))
        # Recharger les munitions
        for name, data in WEAPONS.items():
            self.ammo[name] = data.get("max_ammo", 0)

    def pick_up(self, pickup):
        wn = pickup.weapon_name
        if wn in self.ammo:
            self.ammo[wn] = min(
                self.weapons[wn].get("max_ammo", 99),
                self.ammo[wn] + pickup.ammo
            )
        pickup.kill()

    def add_score(self, amount: int):
        self.score += amount

    def add_score_popup(self, text: str, world_pos):
        self.score_popups.append({
            "text":  text,
            "x":     float(world_pos.x),
            "y":     float(world_pos.y),
            "timer": 1.0,
        })
        if len(self.score_popups) > 20:
            self.score_popups.pop(0)

    def update_popups(self, dt: float):
        for p in self.score_popups:
            p["timer"] -= dt
        self.score_popups = [p for p in self.score_popups if p["timer"] > 0]

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)

        if self.state == "down":
            # Joueur a terre : cercle rouge clignottant
            col = (220, 60, 30) if (pygame.time.get_ticks() // 400) % 2 == 0 else (120, 30, 10)
            pygame.draw.circle(surface, col, (int(sx), int(sy)), 14)
            pygame.draw.circle(surface, (255, 255, 255), (int(sx), int(sy)), 14, 2)
            # Countdown
            font = pygame.font.SysFont("Arial", 13, bold=True)
            txt  = font.render(f"{int(self.down_timer)}s", True, (255, 200, 50))
            surface.blit(txt, (int(sx) - txt.get_width() // 2, int(sy) - 30))
            # Barre revive si en cours
            if self.revive_progress > 0:
                bar_w = 40
                bx = int(sx) - bar_w // 2
                by = int(sy) + 18
                pygame.draw.rect(surface, (60, 60, 60), (bx, by, bar_w, 5))
                pygame.draw.rect(surface, (50, 220, 50),
                                 (bx, by, int(bar_w * self.revive_progress), 5))
            return

        if self.state == "dead":
            return   # N'affiche pas les joueurs definitivement morts

        # Rotation selon l'angle de visee
        rotated = pygame.transform.rotate(self._base_surf, -self.facing_angle)
        r = rotated.get_rect(center=(int(sx), int(sy)))
        surface.blit(rotated, r)

        # Nom du joueur (en multi)
        if self.player_id > 0:
            font = pygame.font.SysFont("Arial", 12)
            name_surf = font.render(self.player_name, True, (220, 220, 220))
            surface.blit(name_surf, (int(sx) - name_surf.get_width() // 2, int(sy) - 28))

        # Barre de vie
        if self.hp < self.max_hp:
            bar_w = 32
            bar_h = 4
            bx = int(sx) - bar_w // 2
            by = int(sy) - 22
            pygame.draw.rect(surface, (180, 30, 30), (bx, by, bar_w, bar_h))
            ratio = self.hp / self.max_hp
            pygame.draw.rect(surface, (50, 200, 50),
                             (bx, by, int(bar_w * ratio), bar_h))

        # Indicateur rechargement
        if self.is_reloading:
            wdata = self.get_weapon_data()
            rt    = wdata.get("reload_time", 1.5)
            prog  = 1.0 - (self.reload_timer / max(0.001, rt))
            bar_w = 32
            bx    = int(sx) - bar_w // 2
            by    = int(sy) - 28
            pygame.draw.rect(surface, (50, 50, 200),
                             (bx, by, int(bar_w * prog), 3))
