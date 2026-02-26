# menus.py - Menu principal, pause, game over
import pygame
from settings import (
    SCREEN_W, SCREEN_H, STATE_PLAYING, STATE_MENU, STATE_GAMEOVER,
    COL_BLACK, COL_WHITE, COL_YELLOW, COL_RED, COL_GREY, COL_DARK_GREEN,
)


def _center_text(surface, font, text, color, y, shadow=True):
    if shadow:
        shadow_surf = font.render(text, True, (0, 0, 0))
        surface.blit(shadow_surf, (SCREEN_W // 2 - shadow_surf.get_width() // 2 + 2,
                                   y + 2))
    txt_surf = font.render(text, True, color)
    surface.blit(txt_surf, (SCREEN_W // 2 - txt_surf.get_width() // 2, y))
    return txt_surf.get_height()


class Menus:
    def __init__(self):
        self._font_title  = pygame.font.SysFont("Arial", 64, bold=True)
        self._font_sub    = pygame.font.SysFont("Arial", 28, bold=True)
        self._font_normal = pygame.font.SysFont("Arial", 22)
        self._font_small  = pygame.font.SysFont("Arial", 16)
        self._blink_timer = 0.0
        self._blink_state = True

    def update(self, dt: float):
        self._blink_timer += dt
        if self._blink_timer >= 0.6:
            self._blink_timer = 0.0
            self._blink_state = not self._blink_state

    # ------------------------------------------------------------------
    def draw_main_menu(self, surface: pygame.Surface) -> str | None:
        """Dessine le menu principal. Renvoie STATE_PLAYING si ESPACE presse."""
        # Fond
        surface.fill((20, 18, 14))
        # Bandeaux decoratifs
        pygame.draw.rect(surface, (40, 35, 25), (0, 0, SCREEN_W, 8))
        pygame.draw.rect(surface, (40, 35, 25), (0, SCREEN_H - 8, SCREEN_W, 8))

        # Titre
        _center_text(surface, self._font_title, "WW2 SURVIVAL", COL_YELLOW, 120)
        _center_text(surface, self._font_sub,   "1944 - FRONT DE L'OUEST", COL_GREY, 200)

        # Separateur
        pygame.draw.line(surface, COL_YELLOW,
                         (SCREEN_W // 4, 245), (SCREEN_W * 3 // 4, 245), 2)

        # Instructions
        controls = [
            ("DEPLACEMENTS",  "W A S D"),
            ("VISER",         "SOURIS"),
            ("TIRER",         "CLIC GAUCHE"),
            ("GRENADE",       "G / CLIC DROIT"),
            ("CHANGER ARME",  "Q / E  ou  MOLETTE"),
            ("RECHARGER",     "R"),
            ("PAUSE",         "ECHAP"),
        ]
        y = 270
        for label, key in controls:
            l_surf = self._font_normal.render(label + " :", True, COL_GREY)
            k_surf = self._font_normal.render(key, True, COL_WHITE)
            lx = SCREEN_W // 2 - 200
            surface.blit(l_surf, (lx, y))
            surface.blit(k_surf, (lx + 240, y))
            y += 28

        # Armes
        pygame.draw.line(surface, COL_GREY,
                         (SCREEN_W // 4, y + 5), (SCREEN_W * 3 // 4, y + 5), 1)
        y += 15
        _center_text(surface, self._font_small,
                     "ARMES : Pistolet | Fusil | Mitraillette | Grenade",
                     COL_GREY, y)

        # Bouton JOUER
        if self._blink_state:
            _center_text(surface, self._font_sub, "[ ESPACE ] JOUER", COL_YELLOW,
                         SCREEN_H - 110)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
            return STATE_PLAYING
        return None

    # ------------------------------------------------------------------
    def draw_pause(self, surface: pygame.Surface) -> str | None:
        """Superpose une couche de pause. Renvoie STATE_PLAYING si reprise."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        _center_text(surface, self._font_title, "PAUSE", COL_YELLOW, SCREEN_H // 2 - 80)
        _center_text(surface, self._font_sub, "ECHAP  pour reprendre",
                     COL_WHITE, SCREEN_H // 2 + 10)
        _center_text(surface, self._font_normal, "QUITTER : Alt+F4",
                     COL_GREY, SCREEN_H // 2 + 50)
        return None

    # ------------------------------------------------------------------
    def draw_game_over(self, surface: pygame.Surface,
                       final_score: int, wave_reached: int) -> str | None:
        """Ecran game over. Renvoie STATE_MENU si ESPACE presse."""
        surface.fill((10, 5, 5))

        _center_text(surface, self._font_title, "MORT AU COMBAT", COL_RED, 140)
        _center_text(surface, self._font_sub,
                     f"Vague atteinte : {wave_reached}", COL_GREY, 240)
        _center_text(surface, self._font_sub,
                     f"Score final : {final_score:,}", COL_YELLOW, 285)

        pygame.draw.line(surface, COL_RED,
                         (SCREEN_W // 4, 330), (SCREEN_W * 3 // 4, 330), 2)

        if self._blink_state:
            _center_text(surface, self._font_sub,
                         "[ ESPACE ] RETOUR AU MENU", COL_WHITE, SCREEN_H - 120)

        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE] or keys[pygame.K_RETURN]:
            return STATE_MENU
        return None
