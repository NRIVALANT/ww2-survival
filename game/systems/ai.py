# ai.py - Machine d'etats IA pour les ennemis
import pygame
import math
import random
from settings import (
    TILE_SIZE, CHASE_RANGE, COVER_RANGE, PATROL_SPEED_MOD,
    PATH_RECALC_TIME,
)
from game.systems.collision import has_line_of_sight


# ---- Etats ----
AI_PATROL  = "patrol"
AI_ALERT   = "alert"
AI_CHASE   = "chase"
AI_SHOOT   = "shoot"
AI_COVER   = "cover"
AI_DEAD    = "dead"


def _dist(a: pygame.Vector2, b: pygame.Vector2) -> float:
    return (b - a).length()


class AIController:
    def __init__(self, enemy, player, tilemap, pathfinder):
        self.enemy       = enemy
        self.player      = player
        self.tilemap     = tilemap
        self.pathfinder  = pathfinder

        self.state       = AI_PATROL
        self.alert_timer = 0.0
        self.los_lost_timer = 0.0
        self.cover_pos: pygame.Vector2 | None = None

        # Points de patrouille
        self.patrol_points: list[pygame.Vector2] = \
            self._generate_patrol_points(enemy.pos, 3, 200)
        self.patrol_idx = 0

        # Chemin courant
        self.current_path: list[pygame.Vector2] = []
        self.path_timer   = 0.0

    # ------------------------------------------------------------------
    def update(self, dt: float):
        e = self.enemy
        p_pos = pygame.Vector2(self.player.rect.center)
        e_pos = e.pos

        dist_to_player = _dist(e_pos, p_pos)
        has_los = has_line_of_sight(e_pos, p_pos, self.tilemap)
        shoot_range = e.shoot_range

        # ---- Transitions ----
        if self.state == AI_PATROL:
            if dist_to_player <= e.detect_range and has_los:
                self.state = AI_ALERT
                self.alert_timer = 0.4

        elif self.state == AI_ALERT:
            self.alert_timer -= dt
            if self.alert_timer <= 0:
                self.state = AI_CHASE
                self.current_path = []
                self.path_timer = 0

        elif self.state == AI_CHASE:
            if dist_to_player <= shoot_range and has_los:
                self.state = AI_SHOOT
            elif dist_to_player > CHASE_RANGE:
                # Joueur trop loin : retour patrouille
                if not has_los:
                    self.los_lost_timer += dt
                    if self.los_lost_timer > 3.0:
                        self.state = AI_PATROL
                        self.current_path = []
                else:
                    self.los_lost_timer = 0
            else:
                self.los_lost_timer = 0

        elif self.state == AI_SHOOT:
            if not has_los or dist_to_player > shoot_range * 1.3:
                self.state = AI_CHASE
                self.current_path = []
            elif e.suppression_timer > 0.5 or e.hp < e.max_hp * 0.35:
                best = self._find_cover(e_pos, p_pos)
                if best:
                    self.cover_pos = best
                    self.state = AI_COVER
                    self.current_path = []

        elif self.state == AI_COVER:
            if self.cover_pos:
                d = _dist(e_pos, self.cover_pos)
                if d < TILE_SIZE * 1.5:
                    # Arrive a couverture : retirer si LOS est perdu
                    if not has_line_of_sight(e_pos, p_pos, self.tilemap):
                        self.state = AI_SHOOT
                        self.cover_pos = None
            else:
                self.state = AI_CHASE

        # ---- Actions par etat ----
        if self.state == AI_PATROL:
            self._do_patrol(dt)
        elif self.state in (AI_ALERT,):
            pass  # Stand still, alert animation
        elif self.state == AI_CHASE:
            self._do_chase(dt, p_pos)
        elif self.state == AI_SHOOT:
            pass  # L'entite enemy gere le tir
        elif self.state == AI_COVER:
            if self.cover_pos:
                self._do_move_to(dt, self.cover_pos)

    # ------------------------------------------------------------------
    def _do_patrol(self, dt: float):
        if not self.patrol_points:
            return
        target = self.patrol_points[self.patrol_idx]
        e = self.enemy
        d = _dist(e.pos, target)
        if d < TILE_SIZE:
            self.patrol_idx = (self.patrol_idx + 1) % len(self.patrol_points)
            self.current_path = []
            return
        self._do_move_to(dt, target, speed_mod=PATROL_SPEED_MOD)

    def _do_chase(self, dt: float, target_pos: pygame.Vector2):
        self._do_move_to(dt, target_pos)

    def _do_move_to(self, dt: float, target_pos: pygame.Vector2,
                    speed_mod: float = 1.0):
        e = self.enemy
        # Recalcul du chemin periodique
        self.path_timer -= dt
        if self.path_timer <= 0 or not self.current_path:
            self.current_path = self.pathfinder.find_path(e.pos, target_pos)
            self.path_timer = PATH_RECALC_TIME

        if not self.current_path:
            return

        # Avancer vers prochain waypoint
        wp = self.current_path[0]
        d = _dist(e.pos, wp)
        if d < TILE_SIZE * 0.6:
            self.current_path.pop(0)
            if not self.current_path:
                return
            wp = self.current_path[0]

        direction = (wp - e.pos)
        if direction.length() > 0:
            direction = direction.normalize()
        e.velocity = direction * e.speed * speed_mod

    # ------------------------------------------------------------------
    def _generate_patrol_points(self, origin: pygame.Vector2,
                                 count: int, radius: float) -> list[pygame.Vector2]:
        points = []
        attempts = 0
        while len(points) < count and attempts < 60:
            angle = random.uniform(0, math.pi * 2)
            dist  = random.uniform(radius * 0.3, radius)
            wx = origin.x + math.cos(angle) * dist
            wy = origin.y + math.sin(angle) * dist
            col = int(wx // TILE_SIZE)
            row = int(wy // TILE_SIZE)
            if self.tilemap.in_bounds(col, row) and not self.tilemap.is_solid(col, row):
                points.append(pygame.Vector2(wx, wy))
            attempts += 1
        return points if points else [origin.copy()]

    def _find_cover(self, enemy_pos: pygame.Vector2,
                    player_pos: pygame.Vector2) -> pygame.Vector2 | None:
        best_pos   = None
        best_score = -1.0
        for col, row in self.tilemap.get_solid_tiles_in_radius(enemy_pos, COVER_RANGE):
            for dc, dr in ((-1,0),(1,0),(0,-1),(0,1)):
                nc, nr = col + dc, row + dr
                if not self.tilemap.in_bounds(nc, nr):
                    continue
                if self.tilemap.is_solid(nc, nr):
                    continue
                cover_pos = self.tilemap.tile_center(nc, nr)
                if has_line_of_sight(cover_pos, player_pos, self.tilemap):
                    continue
                d_enemy  = _dist(cover_pos, enemy_pos) + 0.1
                d_player = _dist(cover_pos, player_pos)
                score = d_player / d_enemy
                if score > best_score:
                    best_score = score
                    best_pos   = cover_pos
        return best_pos
