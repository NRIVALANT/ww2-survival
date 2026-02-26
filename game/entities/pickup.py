# pickup.py - Ramassage d'armes au sol
import pygame
import math
from settings import (
    TILE_SIZE, WEAPONS, WEAPON_ORDER,
    COL_PICKUP, COL_BLACK, COL_WHITE, COL_YELLOW,
)


# Couleurs et formes par arme
WEAPON_COLORS = {
    "pistol":  (180, 180, 200),
    "rifle":   (120, 100,  60),
    "smg":     (160, 140,  80),
    "grenade": (80,  110,  60),
}


def _make_weapon_icon(weapon_name: str, size: int = 28) -> pygame.Surface:
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    color = WEAPON_COLORS.get(weapon_name, COL_PICKUP)
    cx, cy = size // 2, size // 2

    if weapon_name == "pistol":
        pygame.draw.rect(surf, color, (4, cy - 3, size - 8, 6), border_radius=2)
        pygame.draw.rect(surf, color, (4, cy + 1, 6, 8), border_radius=1)
        pygame.draw.rect(surf, (140, 140, 160), (size - 12, cy - 2, 10, 4))

    elif weapon_name == "rifle":
        pygame.draw.rect(surf, color, (2, cy - 3, size - 4, 5), border_radius=1)
        pygame.draw.rect(surf, color, (2, cy - 1, 8, 7), border_radius=1)
        pygame.draw.rect(surf, (90, 70, 40), (10, cy - 3, size - 14, 5))

    elif weapon_name == "smg":
        pygame.draw.rect(surf, color, (2, cy - 4, size - 4, 7), border_radius=2)
        pygame.draw.rect(surf, (110, 90, 50), (4, cy - 4, 8, 6))
        pygame.draw.rect(surf, (140, 120, 70), (cx - 2, cy + 2, 5, 8), border_radius=1)

    elif weapon_name == "grenade":
        pygame.draw.circle(surf, color, (cx, cy + 2), 9)
        pygame.draw.rect(surf, (60, 80, 50), (cx - 2, cy - 10, 4, 8))
        pygame.draw.circle(surf, (50, 90, 50), (cx, cy + 2), 9, 2)

    return surf


class WeaponPickup(pygame.sprite.Sprite):
    BOB_AMP    = 3.0   # amplitude du flottement
    BOB_SPEED  = 2.5   # cycles/s

    def __init__(self, x: float, y: float, weapon_name: str,
                 ammo: int = -1, groups=()):
        super().__init__(*groups)
        self.pos         = pygame.Vector2(x, y)
        self.weapon_name = weapon_name
        self.ammo        = ammo if ammo >= 0 else WEAPONS[weapon_name].get("max_ammo", 1)
        self._bob_time   = 0.0

        icon = _make_weapon_icon(weapon_name, 28)
        # Fond colore
        size = 36
        base = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(base, (*COL_YELLOW, 180), (size // 2, size // 2), size // 2)
        pygame.draw.circle(base, (*COL_BLACK, 120), (size // 2, size // 2), size // 2, 2)
        base.blit(icon, (4, 4))
        self._base_surf = base

        self.image = base
        self.rect  = self.image.get_rect(center=(int(x), int(y)))

    def update(self, dt: float):
        self._bob_time += dt
        # Bob sinusoidal
        bob_y = math.sin(self._bob_time * self.BOB_SPEED * math.pi * 2) * self.BOB_AMP
        self.rect.centery = int(self.pos.y + bob_y)

    def draw(self, surface: pygame.Surface, camera, font: pygame.font.Font):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)
        bob_y = math.sin(self._bob_time * self.BOB_SPEED * math.pi * 2) * self.BOB_AMP
        r = self._base_surf.get_rect(center=(int(sx), int(sy + bob_y)))
        surface.blit(self._base_surf, r)

        # Label au dessus
        label = font.render(self.weapon_name.upper(), True, COL_YELLOW)
        surface.blit(label, (r.centerx - label.get_width() // 2, r.top - 14))
