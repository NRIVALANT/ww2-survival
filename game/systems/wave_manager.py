# wave_manager.py - Gestionnaire de vagues d'ennemis (supporte multi-joueurs)
import pygame
import random
from settings import (
    WAVE_COOLDOWN, BASE_ENEMIES, WAVE_SCALE, SPAWN_INTERVAL,
    TILE_SIZE, PLAYER_HP,
)
from game.world.map_data import SPAWN_ZONES


_WAVE_PICKUPS = ["pistol", "rifle", "smg", "grenade"]


class WaveManager:
    STATE_WAITING   = "waiting"
    STATE_SPAWNING  = "spawning"
    STATE_ACTIVE    = "active"
    STATE_CLEAR     = "clear"

    def __init__(self, tilemap, pathfinder, players,
                 enemy_group, pickup_group, all_groups):
        self.tilemap      = tilemap
        self.pathfinder   = pathfinder
        # Accepte un joueur unique (retro-compat) ou une liste
        self.players      = players if isinstance(players, list) else [players]
        self.enemy_group  = enemy_group
        self.pickup_group = pickup_group
        self.all_groups   = all_groups

        self.wave_number     = 0
        self.state           = self.STATE_WAITING
        self.cooldown_timer  = 3.0
        self.spawn_timer     = 0.0
        self.enemies_queue: list[str] = []

        self.total_this_wave  = 0
        self.killed_this_wave = 0

    # ------------------------------------------------------------------
    def update(self, dt: float):
        if self.state == self.STATE_WAITING:
            self.cooldown_timer -= dt
            if self.cooldown_timer <= 0:
                self._start_wave()

        elif self.state == self.STATE_SPAWNING:
            self.spawn_timer -= dt
            if self.spawn_timer <= 0 and self.enemies_queue:
                self._spawn_enemy(self.enemies_queue.pop(0))
                self.spawn_timer = SPAWN_INTERVAL
            if not self.enemies_queue:
                self.state = self.STATE_ACTIVE

        elif self.state == self.STATE_ACTIVE:
            if len(self.enemy_group) == 0:
                self.state = self.STATE_CLEAR
                self.cooldown_timer = WAVE_COOLDOWN
                self._drop_pickups()
                self._respawn_dead_players()

        elif self.state == self.STATE_CLEAR:
            self.cooldown_timer -= dt
            if self.cooldown_timer <= 0:
                self._start_wave()

    # ------------------------------------------------------------------
    def _start_wave(self):
        self.wave_number += 1
        count = int(BASE_ENEMIES * (WAVE_SCALE ** (self.wave_number - 1)))
        self.total_this_wave  = count
        self.killed_this_wave = 0
        self.enemies_queue = self._build_composition(count)
        self.state = self.STATE_SPAWNING
        self.spawn_timer = 0.0

    def _build_composition(self, count: int) -> list[str]:
        types = []
        for _ in range(count):
            r = random.random()
            if self.wave_number >= 6 and r < 0.20:
                types.append("heavy")
            elif self.wave_number >= 3 and r < 0.35:
                types.append("officer")
            else:
                types.append("soldier")
        return types

    def _spawn_enemy(self, enemy_type: str):
        from game.entities.enemy import SoldierEnemy, OfficerEnemy, HeavyEnemy

        # Choisir un spawn loin de TOUS les joueurs vivants
        alive_positions = [
            pygame.Vector2(p.rect.center)
            for p in self.players
            if getattr(p, "state", "alive") == "alive"
        ]

        valid = []
        for col, row in SPAWN_ZONES:
            spawn_world = pygame.Vector2(col * TILE_SIZE + TILE_SIZE // 2,
                                        row * TILE_SIZE + TILE_SIZE // 2)
            if self.tilemap.is_solid(col, row):
                continue
            # Doit etre loin de tous les joueurs vivants
            far_enough = all(
                (spawn_world - p_pos).length() > 350
                for p_pos in alive_positions
            ) if alive_positions else True
            if far_enough:
                valid.append(spawn_world)

        if not valid:
            valid = [pygame.Vector2(col * TILE_SIZE + TILE_SIZE // 2,
                                    row * TILE_SIZE + TILE_SIZE // 2)
                     for col, row in SPAWN_ZONES
                     if not self.tilemap.is_solid(col, row)]
        if not valid:
            return

        pos = random.choice(valid)
        cls_map = {
            "soldier": SoldierEnemy,
            "officer": OfficerEnemy,
            "heavy":   HeavyEnemy,
        }
        cls = cls_map.get(enemy_type, SoldierEnemy)
        cls(pos.x, pos.y,
            self.pathfinder, self.players, self.tilemap,
            groups=self.all_groups + (self.enemy_group,))

    def _drop_pickups(self):
        from game.entities.pickup import WeaponPickup
        count = min(3, 1 + self.wave_number // 2)
        placed = set()
        for _ in range(count):
            wn = random.choice(_WAVE_PICKUPS)
            for _attempt in range(40):
                col = random.randint(2, self.tilemap.cols - 3)
                row = random.randint(2, self.tilemap.rows - 3)
                if not self.tilemap.is_solid(col, row) and (col, row) not in placed:
                    placed.add((col, row))
                    wx = col * TILE_SIZE + TILE_SIZE // 2
                    wy = row * TILE_SIZE + TILE_SIZE // 2
                    WeaponPickup(wx, wy, wn, groups=(self.pickup_group,))
                    break

    def _respawn_dead_players(self):
        """Respawn les joueurs morts au debut de la prochaine manche."""
        from game.world.map_data import PLAYER_START
        for p in self.players:
            if getattr(p, "state", "alive") == "dead":
                px, py = PLAYER_START
                p.respawn(float(px), float(py))

    # ------------------------------------------------------------------
    @property
    def is_wave_clear(self) -> bool:
        return self.state == self.STATE_CLEAR

    @property
    def clear_countdown(self) -> float:
        return max(0.0, self.cooldown_timer)

    @property
    def enemies_remaining(self) -> int:
        return len(self.enemy_group)
