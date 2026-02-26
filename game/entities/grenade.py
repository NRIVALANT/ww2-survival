# grenade.py - Grenades et explosions
import pygame
import math
from settings import (
    TILE_SIZE, GRENADE_FRICTION, GRENADE_BOUNCE_DAMP,
    COL_GRENADE, COL_EXPLOSION, COL_YELLOW, COL_BLACK,
)


class Explosion(pygame.sprite.Sprite):
    ANIM_DURATION = 0.5
    FRAMES = 6

    def __init__(self, x: float, y: float, blast_radius: float, damage: int,
                 groups=()):
        super().__init__(*groups)
        self.pos          = pygame.Vector2(x, y)
        self.blast_radius = blast_radius
        self.damage       = damage
        self.timer        = 0.0
        self._damaged     = False

        r = int(blast_radius)
        self._surfs = self._build_surfs(r)
        self.image  = self._surfs[0]
        self.rect   = self.image.get_rect(center=(int(x), int(y)))

    def _build_surfs(self, r: int) -> list[pygame.Surface]:
        surfs = []
        for i in range(self.FRAMES):
            t = i / max(1, self.FRAMES - 1)
            cur_r = int(r * (0.3 + 0.7 * t))
            surf = pygame.Surface((r * 2 + 4, r * 2 + 4), pygame.SRCALPHA)
            cx, cy = r + 2, r + 2
            # Halo externe
            alpha = int(200 * (1 - t))
            inner_r = max(1, cur_r - 15)
            pygame.draw.circle(surf, (*COL_EXPLOSION, alpha), (cx, cy), cur_r)
            pygame.draw.circle(surf, (255, 240, 150, alpha), (cx, cy), inner_r)
            surfs.append(surf)
        return surfs

    def update(self, dt: float, enemy_group=None, player=None):
        if not self._damaged:
            self._damaged = True
            # Inflige les degats en zone
            if enemy_group:
                for enemy in enemy_group:
                    d = (pygame.Vector2(enemy.rect.center) - self.pos).length()
                    if d <= self.blast_radius:
                        dmg = int(self.damage * max(0.2, 1.0 - d / self.blast_radius))
                        enemy.take_damage(dmg)
            # player peut etre un seul joueur OU une liste de joueurs
            if player:
                targets = player if isinstance(player, list) else [player]
                for p in targets:
                    d = (pygame.Vector2(p.rect.center) - self.pos).length()
                    if d <= self.blast_radius:
                        dmg = int(self.damage * max(0.2, 1.0 - d / self.blast_radius))
                        p.take_damage(dmg)

        self.timer += dt
        frame = min(self.FRAMES - 1,
                    int(self.timer / self.ANIM_DURATION * self.FRAMES))
        self.image = self._surfs[frame]

        if self.timer >= self.ANIM_DURATION:
            self.kill()

    def draw(self, surface: pygame.Surface, camera):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)
        r = self.image.get_rect(center=(int(sx), int(sy)))
        surface.blit(self.image, r)


class Grenade(pygame.sprite.Sprite):
    RADIUS = 7

    def __init__(self, x: float, y: float,
                 vel_x: float, vel_y: float,
                 fuse_time: float, blast_radius: float, damage: int,
                 groups=(), explosion_groups=()):
        super().__init__(*groups)
        self.pos            = pygame.Vector2(x, y)
        self.velocity       = pygame.Vector2(vel_x, vel_y)
        self.fuse_timer     = fuse_time
        self.blast_radius   = blast_radius
        self.damage         = damage
        self._expl_groups   = explosion_groups

        size = self.RADIUS * 2
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, COL_GRENADE, (self.RADIUS, self.RADIUS), self.RADIUS)
        pygame.draw.circle(surf, (100, 100, 100),
                           (self.RADIUS, self.RADIUS), self.RADIUS, 2)
        self.image = surf
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    def _collides_tile(self, tilemap) -> bool:
        col = int(self.pos.x // TILE_SIZE)
        row = int(self.pos.y // TILE_SIZE)
        return tilemap.is_solid(col, row)

    def update(self, dt: float, tilemap, enemy_group=None, player=None):
        # Friction
        factor = GRENADE_FRICTION ** dt
        self.velocity *= factor

        # Mouvement X
        self.pos.x += self.velocity.x * dt
        self.rect.centerx = int(self.pos.x)
        if self._collides_tile(tilemap):
            self.pos.x -= self.velocity.x * dt
            self.velocity.x *= -GRENADE_BOUNCE_DAMP

        # Mouvement Y
        self.pos.y += self.velocity.y * dt
        self.rect.centery = int(self.pos.y)
        if self._collides_tile(tilemap):
            self.pos.y -= self.velocity.y * dt
            self.velocity.y *= -GRENADE_BOUNCE_DAMP

        # Compte a rebours
        self.fuse_timer -= dt
        if self.fuse_timer <= 0:
            # player peut etre un seul joueur OU une liste de joueurs
            self._detonate(enemy_group, player)

    def _detonate(self, enemy_group, player):
        # Normalise player en liste pour que Explosion.update() puisse iterer
        players_list = player if isinstance(player, list) else ([player] if player else [])
        expl = Explosion(
            self.pos.x, self.pos.y,
            self.blast_radius, self.damage,
            groups=self._expl_groups,
        )
        # Appliquer les degats immediatement au moment de la detonation
        if enemy_group:
            for enemy in enemy_group:
                d = (pygame.Vector2(enemy.rect.center) - self.pos).length()
                if d <= self.blast_radius:
                    dmg = int(self.damage * max(0.2, 1.0 - d / self.blast_radius))
                    enemy.take_damage(dmg)
        for p in players_list:
            d = (pygame.Vector2(p.rect.center) - self.pos).length()
            if d <= self.blast_radius:
                dmg = int(self.damage * max(0.2, 1.0 - d / self.blast_radius))
                p.take_damage(dmg)
        expl._damaged = True  # Marquer comme deja traite pour eviter double application
        self.kill()

    def draw(self, surface: pygame.Surface, camera):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)
        r = self.image.get_rect(center=(int(sx), int(sy)))
        surface.blit(self.image, r)
