# tilemap.py - Gestion de la grille de tuiles
import pygame
from settings import (
    TILE_SIZE, MAP_COLS, MAP_ROWS, MAP_W, MAP_H,
    SOLID_TILES,
    COL_GROUND_A, COL_GROUND_B, COL_WALL, COL_SANDBAG, COL_BUNKER,
    TILE_GROUND, TILE_WALL, TILE_SANDBAG, TILE_BUNKER, TILE_DIRT,
)


def _make_tile_surface(tile_id: int) -> pygame.Surface:
    """Genere un sprite de tuile en code (pas d'images requises)."""
    surf = pygame.Surface((TILE_SIZE, TILE_SIZE))
    T = TILE_SIZE

    if tile_id == TILE_GROUND:
        surf.fill(COL_GROUND_A)
        # Petits details texture
        pygame.draw.line(surf, COL_GROUND_B, (0, T//3), (T, T//3), 1)
        pygame.draw.line(surf, COL_GROUND_B, (T//3, 0), (T//3, T), 1)

    elif tile_id == TILE_WALL:
        surf.fill(COL_WALL)
        # Motif brique
        for row in range(0, T, T//4):
            pygame.draw.line(surf, (55, 50, 38), (0, row), (T, row), 1)
        for row in range(0, T, T//4):
            offset = (T // 3) if (row // (T // 4)) % 2 == 0 else 0
            for col in range(offset, T, T//2):
                pygame.draw.line(surf, (55, 50, 38), (col, row), (col, row + T//4), 1)

    elif tile_id == TILE_SANDBAG:
        surf.fill(COL_GROUND_A)
        # Sacs de sable empiles
        for i in range(3):
            x = 4 + i * (T // 3 - 2)
            pygame.draw.ellipse(surf, COL_SANDBAG, (x, T//4, T//3, T//2))
            pygame.draw.ellipse(surf, (160, 130, 70), (x, T//4, T//3, T//2), 2)

    elif tile_id == TILE_BUNKER:
        surf.fill(COL_BUNKER)
        # Beton avec fissures
        pygame.draw.rect(surf, (70, 65, 50), (2, 2, T-4, T-4), 3)
        pygame.draw.line(surf, (60, 55, 42), (5, 5), (T//2, T//3), 1)
        pygame.draw.line(surf, (60, 55, 42), (T//2, T//3), (T-5, T//2), 1)

    elif tile_id == TILE_DIRT:
        surf.fill(COL_GROUND_A)
        # Cratere
        pygame.draw.circle(surf, (75, 65, 48), (T//2, T//2), T//3)
        pygame.draw.circle(surf, (65, 55, 40), (T//2, T//2), T//4)

    return surf


class TileMap:
    def __init__(self, data: list[list[int]]):
        self.data = data
        self.rows = len(data)
        self.cols = len(data[0]) if self.rows > 0 else 0

        # Pre-generer les surfaces
        self._tile_surfs = {}
        tile_ids = set()
        for row in data:
            for tid in row:
                tile_ids.add(tid)
        for tid in tile_ids:
            self._tile_surfs[tid] = _make_tile_surface(tid)

    def get_tile(self, col: int, row: int) -> int:
        if 0 <= col < self.cols and 0 <= row < self.rows:
            return self.data[row][col]
        return TILE_WALL   # hors limites = mur

    def is_solid(self, col: int, row: int) -> bool:
        return self.get_tile(col, row) in SOLID_TILES

    def in_bounds(self, col: int, row: int) -> bool:
        return 0 <= col < self.cols and 0 <= row < self.rows

    def get_rect(self, col: int, row: int) -> pygame.Rect:
        return pygame.Rect(col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE)

    def world_to_tile(self, wx: float, wy: float) -> tuple[int, int]:
        return int(wx // TILE_SIZE), int(wy // TILE_SIZE)

    def tile_center(self, col: int, row: int) -> pygame.Vector2:
        return pygame.Vector2(col * TILE_SIZE + TILE_SIZE // 2,
                              row * TILE_SIZE + TILE_SIZE // 2)

    def get_solid_tiles_in_radius(self, world_pos: pygame.Vector2, radius: float):
        """Iterateur: donne les (col, row) solides dans un rayon donne."""
        cx, cy = self.world_to_tile(world_pos.x, world_pos.y)
        tile_radius = int(radius / TILE_SIZE) + 1
        for r in range(cy - tile_radius, cy + tile_radius + 1):
            for c in range(cx - tile_radius, cx + tile_radius + 1):
                if self.is_solid(c, r):
                    center = self.tile_center(c, r)
                    if (center - world_pos).length() <= radius + TILE_SIZE:
                        yield c, r

    def get_neighbors(self, col: int, row: int):
        """4 voisins cardinaux + 4 diagonaux."""
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = col + dc, row + dr
                if self.in_bounds(nc, nr):
                    yield nc, nr

    def draw(self, surface: pygame.Surface, camera_offset: pygame.Vector2):
        """Ne dessine que les tuiles visibles dans le viewport."""
        ox, oy = int(camera_offset.x), int(camera_offset.y)
        screen_w = surface.get_width()
        screen_h = surface.get_height()

        col_start = max(0, ox // TILE_SIZE)
        col_end   = min(self.cols, (ox + screen_w) // TILE_SIZE + 2)
        row_start = max(0, oy // TILE_SIZE)
        row_end   = min(self.rows, (oy + screen_h) // TILE_SIZE + 2)

        for row in range(row_start, row_end):
            for col in range(col_start, col_end):
                tid = self.data[row][col]
                surf = self._tile_surfs.get(tid, self._tile_surfs[TILE_GROUND])
                sx = col * TILE_SIZE - ox
                sy = row * TILE_SIZE - oy
                surface.blit(surf, (sx, sy))
