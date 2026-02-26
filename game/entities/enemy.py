# enemy.py - Entites ennemis avec IA
import pygame
import math
import random
from settings import (
    ENEMY_TYPES, ENEMY_BULLET_SPEED, ENEMY_BULLET_RANGE, ENEMY_SPREAD,
    TILE_SIZE, COL_BLACK,
)
from game.systems.ai import AIController, AI_SHOOT, AI_DEAD, AI_PATROL
from game.systems.collision import move_and_collide


def _make_enemy_surf(color: tuple, size: int = 30) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    # Corps
    pygame.draw.circle(surf, color, (cx, cy), size // 3)
    # Casque (plus fonce)
    hc = (max(0, color[0] - 40), max(0, color[1] - 30), max(0, color[2] - 30))
    pygame.draw.ellipse(surf, hc, (cx - 8, cy - 12, 16, 10))
    # Arme pointant droite
    pygame.draw.rect(surf, (40, 40, 40), (cx + 2, cy - 2, size // 2 - 4, 4))
    return surf


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, enemy_type: str,
                 pathfinder, player, tilemap, groups=()):
        super().__init__(*groups)
        self.enemy_type = enemy_type
        data            = ENEMY_TYPES[enemy_type]

        self.pos             = pygame.Vector2(x, y)
        self.hp              = data["hp"]
        self.max_hp          = data["hp"]
        self.speed           = data["speed"]
        self.damage          = data["damage"]
        self.fire_rate       = data["fire_rate"]
        self.detect_range    = data["detect_range"]
        self.shoot_range     = data["shoot_range"]
        self.score_value     = data["score"]
        self.color           = data["color"]

        self.velocity        = pygame.Vector2(0, 0)
        self.facing_angle    = random.uniform(0, 360)
        self.fire_timer      = random.uniform(0, self.fire_rate)
        self.suppression_timer = 0.0
        self.alive           = True

        # IA
        self.ai = AIController(self, player, tilemap, pathfinder)

        # Sprite
        self._base_surf = _make_enemy_surf(self.color, 30)
        self.image      = self._base_surf
        self.rect       = self.image.get_rect(center=(int(x), int(y)))

    # ------------------------------------------------------------------
    def update(self, dt: float, tilemap, player, bullet_group, explosion_group):
        if not self.alive:
            return

        self.suppression_timer = max(0.0, self.suppression_timer - dt)
        self.fire_timer        = max(0.0, self.fire_timer - dt)

        # IA
        self.ai.update(dt)

        # Deplacement
        if self.velocity.length() > 0:
            move_and_collide(self,
                             self.velocity.x * dt,
                             self.velocity.y * dt,
                             tilemap)
            self.pos = pygame.Vector2(self.rect.center)
        else:
            self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Rotation smooth vers la cible
        target_angle = self.facing_angle
        if self.ai.state == AI_SHOOT or self.ai.state == AI_PATROL:
            p_pos = pygame.Vector2(player.rect.center)
            dx = p_pos.x - self.pos.x
            dy = p_pos.y - self.pos.y
            if self.ai.state == AI_SHOOT:
                target_angle = math.degrees(math.atan2(dy, dx))
            elif self.velocity.length() > 0:
                target_angle = math.degrees(math.atan2(self.velocity.y,
                                                        self.velocity.x))
        elif self.velocity.length() > 0:
            target_angle = math.degrees(math.atan2(self.velocity.y,
                                                    self.velocity.x))

        diff = (target_angle - self.facing_angle + 180) % 360 - 180
        self.facing_angle += diff * min(1.0, 7.0 * dt)

        # Tir
        if self.ai.state == AI_SHOOT and self.fire_timer <= 0:
            self._shoot(player, bullet_group)
            self.fire_timer = self.fire_rate

    # ------------------------------------------------------------------
    def _shoot(self, player, bullet_group):
        from game.entities.bullet import Bullet
        p_pos = pygame.Vector2(player.rect.center)
        dx = p_pos.x - self.pos.x
        dy = p_pos.y - self.pos.y
        base_angle = math.atan2(dy, dx)
        spread_rad = math.radians(ENEMY_SPREAD)
        angle = base_angle + random.uniform(-spread_rad, spread_rad)

        Bullet(
            self.pos.x, self.pos.y,
            math.cos(angle) * ENEMY_BULLET_SPEED,
            math.sin(angle) * ENEMY_BULLET_SPEED,
            damage       = self.damage,
            owner        = "enemy",
            bullet_range = ENEMY_BULLET_RANGE,
            groups       = (bullet_group,),
        )

    # ------------------------------------------------------------------
    def take_damage(self, amount: int):
        self.hp -= amount
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False
            self.kill()

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera):
        rotated = pygame.transform.rotate(self._base_surf, -self.facing_angle)
        sx, sy  = camera.apply_pos(self.pos.x, self.pos.y)
        r       = rotated.get_rect(center=(int(sx), int(sy)))
        surface.blit(rotated, r)

        # Barre de vie
        bar_w = 28
        bar_h = 4
        bx = int(sx) - bar_w // 2
        by = int(sy) - 20
        pygame.draw.rect(surface, (180, 30, 30), (bx, by, bar_w, bar_h))
        ratio = self.hp / self.max_hp
        g = int(200 * ratio)
        pygame.draw.rect(surface, (200 - g, g, 20),
                         (bx, by, int(bar_w * ratio), bar_h))

        # Indicateur d'etat (debug/info)
        state = self.ai.state
        if state != AI_PATROL:
            col = {
                "alert": (240, 200, 0),
                "chase": (255, 100, 0),
                "shoot": (255, 30, 30),
                "cover": (50, 150, 255),
            }.get(state, (200, 200, 200))
            pygame.draw.circle(surface, col, (int(sx), int(sy) - 24), 3)


# ---- Sous-classes ---------------------------------------------------
class SoldierEnemy(Enemy):
    def __init__(self, x, y, pathfinder, player, tilemap, groups=()):
        super().__init__(x, y, "soldier", pathfinder, player, tilemap, groups)


class OfficerEnemy(Enemy):
    def __init__(self, x, y, pathfinder, player, tilemap, groups=()):
        super().__init__(x, y, "officer", pathfinder, player, tilemap, groups)


class HeavyEnemy(Enemy):
    def __init__(self, x, y, pathfinder, player, tilemap, groups=()):
        super().__init__(x, y, "heavy", pathfinder, player, tilemap, groups)
