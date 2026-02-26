# bullet.py - Projectiles du joueur et des ennemis
import pygame
import math
from settings import TILE_SIZE, COL_BULLET_P, COL_BULLET_E, SUPPRESSION_DIST, POINTS_HIT


def _make_bullet_surf(color: tuple, length: int = 8, width: int = 3) -> pygame.Surface:
    surf = pygame.Surface((length, width), pygame.SRCALPHA)
    pygame.draw.rect(surf, color, (0, 0, length, width), border_radius=1)
    return surf


class Bullet(pygame.sprite.Sprite):
    def __init__(self, x: float, y: float,
                 vel_x: float, vel_y: float,
                 damage: int, owner: str,
                 bullet_range: float,
                 groups=()):
        super().__init__(*groups)
        self.owner    = owner   # "player" ou "enemy"
        self.damage   = damage
        self.velocity = pygame.Vector2(vel_x, vel_y)
        self.pos      = pygame.Vector2(x, y)
        self.max_range = bullet_range
        self.traveled  = 0.0

        color = COL_BULLET_P if owner == "player" else COL_BULLET_E
        angle = math.degrees(math.atan2(-vel_y, vel_x))
        base_surf = _make_bullet_surf(color)
        self._surf = pygame.transform.rotate(base_surf, angle)
        self.image = self._surf
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    def update(self, dt: float, tilemap, enemy_group=None, player=None):
        move = self.velocity * dt
        self.pos += move
        self.traveled += move.length()
        self.rect.center = (int(self.pos.x), int(self.pos.y))

        # Collision avec tuile
        from game.systems.collision import bullet_hits_tile
        if bullet_hits_tile(self, tilemap):
            self.kill()
            return

        # Hors portee
        if self.traveled >= self.max_range:
            self.kill()
            return

        # Collision avec cibles
        if self.owner == "player" and enemy_group:
            for enemy in enemy_group:
                if self.rect.colliderect(enemy.rect):
                    enemy.take_damage(self.damage)
                    # +10 pts pour chaque balle qui touche
                    if player:
                        player.add_score(POINTS_HIT)
                        player.add_score_popup(f"+{POINTS_HIT}", self.pos)
                    # Marquer suppression pour les ennemis proches
                    for e in enemy_group:
                        if e != enemy:
                            d = (pygame.Vector2(e.rect.center) - self.pos).length()
                            if d < SUPPRESSION_DIST * 3:
                                e.suppression_timer = max(e.suppression_timer, 1.2)
                    self.kill()
                    return

        elif self.owner == "enemy" and player:
            if self.rect.colliderect(player.rect):
                player.take_damage(self.damage)
                # Suppression du joueur (pas d'effet mecanique, visuel seulement)
                self.kill()
                return

    def draw(self, surface: pygame.Surface, camera):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)
        r = self.image.get_rect(center=(int(sx), int(sy)))
        surface.blit(self.image, r)
