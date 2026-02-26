# pathfinding.py - Algorithme A* sur la grille de tuiles
import heapq
import math
import pygame
from settings import TILE_SIZE, MAX_ASTAR_NODES


class Pathfinder:
    def __init__(self, tilemap):
        self.tilemap = tilemap

    def find_path(self, start_world: pygame.Vector2,
                  end_world: pygame.Vector2) -> list[pygame.Vector2]:
        """Renvoie une liste de positions monde (centres de tuiles) jusqu'a end."""
        tm = self.tilemap
        sc = int(start_world.x // TILE_SIZE), int(start_world.y // TILE_SIZE)
        ec = int(end_world.x   // TILE_SIZE), int(end_world.y   // TILE_SIZE)

        # Si debut == fin
        if sc == ec:
            return [end_world.copy()]

        # Si la destination est solide, chercher la tuile praticable la plus proche
        if tm.is_solid(*ec):
            ec = self._nearest_walkable(ec)
            if ec is None:
                return []

        came_from: dict[tuple, tuple | None] = {sc: None}
        g_score: dict[tuple, float] = {sc: 0.0}
        open_set: list[tuple[float, tuple]] = []
        heapq.heappush(open_set, (self._h(sc, ec), sc))
        expansions = 0

        while open_set:
            _, current = heapq.heappop(open_set)
            if current == ec:
                return self._reconstruct(came_from, ec, end_world)
            expansions += 1
            if expansions > MAX_ASTAR_NODES:
                break

            for nc in self._neighbors(current):
                # Cout diagonal = sqrt(2), cardinal = 1
                dc = abs(nc[0] - current[0]) + abs(nc[1] - current[1])
                step_cost = 1.0 if dc == 1 else 1.414
                tg = g_score[current] + step_cost
                if tg < g_score.get(nc, float("inf")):
                    came_from[nc] = current
                    g_score[nc] = tg
                    f = tg + self._h(nc, ec)
                    heapq.heappush(open_set, (f, nc))

        # Pas de chemin trouve : renvoyer la derniere tuile visitee la plus proche
        best = min(came_from.keys(), key=lambda n: self._h(n, ec))
        return self._reconstruct(came_from, best, end_world)

    def _h(self, a: tuple, b: tuple) -> float:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def _neighbors(self, node: tuple) -> list[tuple]:
        col, row = node
        tm = self.tilemap
        result = []
        for dc in (-1, 0, 1):
            for dr in (-1, 0, 1):
                if dc == 0 and dr == 0:
                    continue
                nc, nr = col + dc, row + dr
                if not tm.in_bounds(nc, nr) or tm.is_solid(nc, nr):
                    continue
                # Eviter de couper les coins
                if dc != 0 and dr != 0:
                    if tm.is_solid(col + dc, row) or tm.is_solid(col, row + dr):
                        continue
                result.append((nc, nr))
        return result

    def _reconstruct(self, came_from: dict, end: tuple,
                     end_world: pygame.Vector2) -> list[pygame.Vector2]:
        path = []
        cur = end
        while cur is not None:
            path.append(self.tilemap.tile_center(cur[0], cur[1]))
            cur = came_from.get(cur)
        path.reverse()
        if path:
            path[-1] = end_world.copy()
        return self._smooth(path)

    def _smooth(self, path: list[pygame.Vector2]) -> list[pygame.Vector2]:
        """String-pulling: supprime les waypoints inutiles si LOS disponible."""
        from game.systems.collision import has_line_of_sight
        if len(path) <= 2:
            return path
        smoothed = [path[0]]
        i = 0
        while i < len(path) - 1:
            j = len(path) - 1
            while j > i + 1:
                if has_line_of_sight(path[i], path[j], self.tilemap):
                    break
                j -= 1
            smoothed.append(path[j])
            i = j
        return smoothed

    def _nearest_walkable(self, tile: tuple) -> tuple | None:
        for radius in range(1, 5):
            col, row = tile
            for dc in range(-radius, radius + 1):
                for dr in range(-radius, radius + 1):
                    nc, nr = col + dc, row + dr
                    if self.tilemap.in_bounds(nc, nr) and not self.tilemap.is_solid(nc, nr):
                        return nc, nr
        return None
