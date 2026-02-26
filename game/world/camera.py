# camera.py - Gestion de la camera (vue centree sur le joueur)
import pygame
from settings import SCREEN_W, SCREEN_H, MAP_W, MAP_H


class Camera:
    def __init__(self):
        self.offset = pygame.Vector2(0, 0)

    def update(self, target_rect: pygame.Rect):
        """Centre la camera sur la cible, clampee aux bords de la carte."""
        x = target_rect.centerx - SCREEN_W // 2
        y = target_rect.centery - SCREEN_H // 2
        # Clamp pour ne pas depasser les bords
        x = max(0, min(x, MAP_W - SCREEN_W))
        y = max(0, min(y, MAP_H - SCREEN_H))
        self.offset.x = x
        self.offset.y = y

    def apply(self, rect: pygame.Rect) -> pygame.Rect:
        """Convertit un rect monde en rect ecran."""
        return pygame.Rect(
            rect.x - int(self.offset.x),
            rect.y - int(self.offset.y),
            rect.width,
            rect.height,
        )

    def apply_pos(self, wx: float, wy: float) -> tuple[float, float]:
        return wx - self.offset.x, wy - self.offset.y

    def screen_to_world(self, sx: float, sy: float) -> pygame.Vector2:
        return pygame.Vector2(sx + self.offset.x, sy + self.offset.y)

    def world_to_screen(self, wx: float, wy: float) -> pygame.Vector2:
        return pygame.Vector2(wx - self.offset.x, wy - self.offset.y)
