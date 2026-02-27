# enemy.py - Entites ennemis avec IA (supporte multi-joueurs)
import pygame
import math
import random
import itertools
from settings import (
    ENEMY_TYPES, ENEMY_BULLET_SPEED, ENEMY_BULLET_RANGE, ENEMY_SPREAD,
    TILE_SIZE,
)
from game.systems.ai import AIController, AI_SHOOT, AI_PATROL
from game.systems.collision import move_and_collide


_enemy_counter = itertools.count(1)   # IDs uniques globaux


def _make_enemy_surf(color: tuple, size: int = 32,
                     enemy_type: str = "soldier") -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    cx, cy = size // 2, size // 2
    s = size / 32.0   # facteur d'echelle
    face_col = (190, 155, 115)
    helm_col  = (max(0, color[0]-60), max(0, color[1]-55), max(0, color[2]-45))

    if enemy_type == "soldier":
        # Corps
        pygame.draw.ellipse(surf, color,
                            (int(cx - 8*s), int(cy - 2*s), int(16*s), int(11*s)))
        # Tete
        pygame.draw.circle(surf, face_col, (int(cx), int(cy - 5*s)), int(5*s))
        # Stahlhelm : bord large + dome bombe
        pygame.draw.ellipse(surf, helm_col,
                            (int(cx - 9*s), int(cy - 11*s), int(18*s), int(5*s)))
        pygame.draw.ellipse(surf, helm_col,
                            (int(cx - 6*s), int(cy - 14*s), int(12*s), int(7*s)))
        # Arme (fusil standard)
        pygame.draw.rect(surf, (55, 50, 45),
                         (int(cx + 5*s), int(cy - 1*s), int(11*s), int(3*s)))

    elif enemy_type == "officer":
        # Corps plus fin
        pygame.draw.ellipse(surf, color,
                            (int(cx - 6*s), int(cy - 2*s), int(12*s), int(9*s)))
        # Tete
        pygame.draw.circle(surf, face_col, (int(cx), int(cy - 5*s)), int(4*s))
        # Casquette plate a visiere
        cap_col = (max(0, color[0]-40), max(0, color[1]-40), max(0, color[2]-40))
        pygame.draw.ellipse(surf, cap_col,
                            (int(cx - 5*s), int(cy - 11*s), int(10*s), int(4*s)))
        # Visiere qui depasse vers la droite (direction de visee)
        pygame.draw.polygon(surf, (30, 25, 20), [
            (int(cx + 4*s), int(cy - 10*s)),
            (int(cx + 9*s), int(cy - 8*s)),
            (int(cx + 4*s), int(cy - 8*s)),
        ])
        # Pistolet court
        pygame.draw.rect(surf, (55, 50, 45),
                         (int(cx + 4*s), int(cy - 1*s), int(7*s), int(3*s)))

    elif enemy_type == "heavy":
        # Corps tres epais
        pygame.draw.ellipse(surf, color,
                            (int(cx - 10*s), int(cy - 2*s), int(20*s), int(13*s)))
        # Tete large
        pygame.draw.circle(surf, face_col, (int(cx), int(cy - 5*s)), int(6*s))
        # Casque lourd avec protege-nuque
        pygame.draw.ellipse(surf, helm_col,
                            (int(cx - 11*s), int(cy - 12*s), int(22*s), int(6*s)))
        pygame.draw.ellipse(surf, helm_col,
                            (int(cx - 8*s), int(cy - 16*s), int(16*s), int(9*s)))
        # Arme lourde (longue + epaisse)
        pygame.draw.rect(surf, (45, 42, 38),
                         (int(cx + 7*s), int(cy - 2*s), int(13*s), int(4*s)))
        pygame.draw.rect(surf, (65, 58, 50),
                         (int(cx + 3*s), int(cy - 4*s), int(6*s), int(7*s)),
                         border_radius=1)

    return surf


class Enemy(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float, enemy_type: str,
                 pathfinder, players, tilemap, groups=()):
        super().__init__(*groups)
        self.enemy_id   = next(_enemy_counter)
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

        self.velocity          = pygame.Vector2(0, 0)
        self.facing_angle      = random.uniform(0, 360)
        self.fire_timer        = random.uniform(0, self.fire_rate)
        self.suppression_timer = 0.0
        self.alive             = True

        # players peut etre un joueur unique (retro-compat) ou une liste
        self.players = players if isinstance(players, list) else [players]

        # IA
        self.ai = AIController(self, self.players, tilemap, pathfinder)

        _size_map = {"soldier": 32, "officer": 26, "heavy": 40}
        _size = _size_map.get(enemy_type, 32)
        self._base_surf = _make_enemy_surf(self.color, _size, enemy_type)
        self.image      = self._base_surf
        self.rect       = self.image.get_rect(center=(int(x), int(y)))

    # ------------------------------------------------------------------
    def update(self, dt: float, tilemap, players, bullet_group, explosion_group):
        if not self.alive:
            return

        # Mettre a jour la liste de joueurs de l'IA
        if isinstance(players, list):
            self.players = players
            self.ai.players = players
        else:
            self.players = [players]
            self.ai.players = [players]

        self.suppression_timer = max(0.0, self.suppression_timer - dt)
        self.fire_timer        = max(0.0, self.fire_timer - dt)

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
        current_target = self.ai.current_target

        if self.ai.state == AI_SHOOT and current_target:
            p_pos = pygame.Vector2(current_target.rect.center)
            dx = p_pos.x - self.pos.x
            dy = p_pos.y - self.pos.y
            target_angle = math.degrees(math.atan2(dy, dx))
        elif self.velocity.length() > 0:
            target_angle = math.degrees(math.atan2(self.velocity.y,
                                                    self.velocity.x))

        diff = (target_angle - self.facing_angle + 180) % 360 - 180
        self.facing_angle += diff * min(1.0, 7.0 * dt)

        # Tir
        if self.ai.state == AI_SHOOT and self.fire_timer <= 0 and current_target:
            self._shoot(current_target, bullet_group)
            self.fire_timer = self.fire_rate

    # ------------------------------------------------------------------
    def _shoot(self, target_player, bullet_group):
        from game.entities.bullet import Bullet
        p_pos = pygame.Vector2(target_player.rect.center)
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
            owner_id     = None,
            bullet_range = ENEMY_BULLET_RANGE,
            groups       = (bullet_group,),
        )

    # ------------------------------------------------------------------
    def take_damage(self, amount: int):
        if not self.alive:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.hp    = 0
            self.alive = False

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

        # Indicateur d'etat
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
    def __init__(self, x, y, pathfinder, players, tilemap, groups=()):
        super().__init__(x, y, "soldier", pathfinder, players, tilemap, groups)


class OfficerEnemy(Enemy):
    def __init__(self, x, y, pathfinder, players, tilemap, groups=()):
        super().__init__(x, y, "officer", pathfinder, players, tilemap, groups)


class HeavyEnemy(Enemy):
    def __init__(self, x, y, pathfinder, players, tilemap, groups=()):
        super().__init__(x, y, "heavy", pathfinder, players, tilemap, groups)
