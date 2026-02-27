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
    s = size / 28.0   # facteur d'echelle

    if weapon_name == "pistol":
        # Canon fin qui depasse a droite
        barrel_col = (200, 200, 210)
        pygame.draw.rect(surf, barrel_col,
                         (int(cx - 1*s), int(cy - 4*s), int(13*s), int(3*s)),
                         border_radius=1)
        # Slide / corps principal
        pygame.draw.rect(surf, color,
                         (int(4*s), int(cy - 3*s), int(13*s), int(6*s)),
                         border_radius=2)
        # Crosse (grip) vers le bas
        grip_col = (150, 130, 160)
        pygame.draw.rect(surf, grip_col,
                         (int(5*s), int(cy + 2*s), int(6*s), int(7*s)),
                         border_radius=2)
        # Gachette
        pygame.draw.rect(surf, (220, 200, 200),
                         (int(11*s), int(cy + 2*s), int(2*s), int(4*s)),
                         border_radius=1)
        # Ligne de detail sur le slide
        pygame.draw.rect(surf, (210, 210, 225),
                         (int(8*s), int(cy - 2*s), int(7*s), int(1*s)))

    elif weapon_name == "rifle":
        stock_col = (100, 75, 45)
        metal_col = (120, 110, 100)
        # Crosse (bois) a gauche
        pygame.draw.rect(surf, stock_col,
                         (int(1*s), int(cy - 4*s), int(9*s), int(8*s)),
                         border_radius=2)
        # Corps central
        pygame.draw.rect(surf, color,
                         (int(6*s), int(cy - 3*s), int(10*s), int(6*s)),
                         border_radius=1)
        # Canon long a droite
        pygame.draw.rect(surf, metal_col,
                         (int(14*s), int(cy - 2*s), int(12*s), int(4*s)),
                         border_radius=1)
        # Poignee pistolet sous corps
        pygame.draw.rect(surf, stock_col,
                         (int(9*s), int(cy + 2*s), int(5*s), int(6*s)),
                         border_radius=1)
        # Chargeur amovible
        pygame.draw.rect(surf, (90, 85, 80),
                         (int(12*s), int(cy + 1*s), int(4*s), int(4*s)),
                         border_radius=1)

    elif weapon_name == "smg":
        metal_col = (110, 100, 90)
        # Corps compact
        pygame.draw.rect(surf, color,
                         (int(3*s), int(cy - 4*s), int(16*s), int(7*s)),
                         border_radius=2)
        # Canon court
        pygame.draw.rect(surf, metal_col,
                         (int(18*s), int(cy - 2*s), int(7*s), int(3*s)),
                         border_radius=1)
        # Crosse repliable (arriere)
        pygame.draw.rect(surf, (130, 110, 60),
                         (int(1*s), int(cy - 2*s), int(4*s), int(4*s)),
                         border_radius=1)
        # Chargeur vertical (box magazine)
        pygame.draw.rect(surf, (120, 105, 70),
                         (int(8*s), int(cy + 2*s), int(5*s), int(7*s)),
                         border_radius=2)
        # Ligne de detail corps
        pygame.draw.rect(surf, (170, 150, 90),
                         (int(4*s), int(cy - 1*s), int(12*s), int(1*s)))

    elif weapon_name == "grenade":
        detail_col = (50, 90, 45)
        metal_col  = (160, 150, 100)
        # Corps ovale
        pygame.draw.ellipse(surf, color,
                            (int(cx - 7*s), int(cy - 5*s),
                             int(14*s), int(11*s)))
        # Contour
        pygame.draw.ellipse(surf, detail_col,
                            (int(cx - 7*s), int(cy - 5*s),
                             int(14*s), int(11*s)), max(1, int(1.5*s)))
        # Bandes horizontales de segment
        for dy_off in (-2, 0, 2):
            pygame.draw.line(surf, detail_col,
                             (int(cx - 6*s), int(cy + dy_off*s)),
                             (int(cx + 6*s), int(cy + dy_off*s)),
                             max(1, int(s)))
        # Col metallique en haut
        pygame.draw.rect(surf, metal_col,
                         (int(cx - 2*s), int(cy - 8*s), int(5*s), int(4*s)),
                         border_radius=1)
        # Anneau (pin)
        pygame.draw.circle(surf, metal_col,
                           (int(cx - 3*s), int(cy - 8*s)),
                           max(1, int(2*s)), max(1, int(s)))

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
