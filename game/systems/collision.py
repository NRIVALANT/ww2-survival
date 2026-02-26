# collision.py - Systeme de detection et resolution des collisions
import pygame
from settings import TILE_SIZE, MAP_W, MAP_H


class SpatialHash:
    """Hachage spatial pour acceleration des collisions O(n)."""
    CELL = 96

    def __init__(self):
        self.table: dict[tuple, list] = {}

    def clear(self):
        self.table.clear()

    def insert(self, entity):
        for cell in self._cells(entity.rect):
            self.table.setdefault(cell, []).append(entity)

    def query(self, rect: pygame.Rect) -> list:
        result = []
        seen = set()
        for cell in self._cells(rect):
            for ent in self.table.get(cell, []):
                if id(ent) not in seen:
                    seen.add(id(ent))
                    result.append(ent)
        return result

    def _cells(self, rect: pygame.Rect):
        x0 = rect.left  // self.CELL
        y0 = rect.top   // self.CELL
        x1 = rect.right  // self.CELL
        y1 = rect.bottom // self.CELL
        return [(x, y) for x in range(x0, x1 + 1) for y in range(y0, y1 + 1)]


def _get_nearby_tiles(rect: pygame.Rect, tilemap) -> list[tuple[int, int]]:
    """Renvoie les (col, row) de tuiles proches du rect."""
    margin = 2
    col_min = max(0, rect.left   // TILE_SIZE - margin)
    col_max = min(tilemap.cols - 1, rect.right  // TILE_SIZE + margin)
    row_min = max(0, rect.top    // TILE_SIZE - margin)
    row_max = min(tilemap.rows - 1, rect.bottom // TILE_SIZE + margin)
    tiles = []
    for r in range(row_min, row_max + 1):
        for c in range(col_min, col_max + 1):
            if tilemap.is_solid(c, r):
                tiles.append((c, r))
    return tiles


def move_and_collide(entity, dx: float, dy: float, tilemap) -> None:
    """Deplace une entite et resout les collisions avec les tuiles (slide)."""
    rect = entity.rect
    T = TILE_SIZE

    # Axe X
    rect.x += int(dx)
    for col, row in _get_nearby_tiles(rect, tilemap):
        tile_rect = tilemap.get_rect(col, row)
        if rect.colliderect(tile_rect):
            if dx > 0:
                rect.right = tile_rect.left
            elif dx < 0:
                rect.left = tile_rect.right

    # Axe Y
    rect.y += int(dy)
    for col, row in _get_nearby_tiles(rect, tilemap):
        tile_rect = tilemap.get_rect(col, row)
        if rect.colliderect(tile_rect):
            if dy > 0:
                rect.bottom = tile_rect.top
            elif dy < 0:
                rect.top = tile_rect.bottom

    # Clamp aux bords de la carte
    rect.clamp_ip(pygame.Rect(0, 0, MAP_W, MAP_H))


def bullet_hits_tile(bullet, tilemap) -> bool:
    """Renvoie True si la balle touche une tuile solide."""
    col = int(bullet.rect.centerx // TILE_SIZE)
    row = int(bullet.rect.centery // TILE_SIZE)
    return tilemap.is_solid(col, row)


def has_line_of_sight(start: pygame.Vector2, end: pygame.Vector2, tilemap) -> bool:
    """Raycasting DDA: renvoie True si aucune tuile solide entre start et end."""
    dx = end.x - start.x
    dy = end.y - start.y
    dist = max(abs(dx), abs(dy))
    if dist == 0:
        return True
    steps = int(dist / (TILE_SIZE * 0.4)) + 1
    for i in range(steps + 1):
        t = i / steps
        wx = start.x + dx * t
        wy = start.y + dy * t
        col = int(wx // TILE_SIZE)
        row = int(wy // TILE_SIZE)
        if tilemap.is_solid(col, row):
            return False
    return True
