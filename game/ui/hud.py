# hud.py - Interface utilisateur en jeu
import pygame
from settings import (
    SCREEN_W, SCREEN_H, WEAPON_ORDER, WEAPONS,
    COL_HUD_BG, COL_HP_BAR, COL_HP_LOW, COL_WHITE, COL_BLACK,
    COL_YELLOW, COL_GREY, COL_DARK_GREY, COL_RED, COL_DARK_GREEN,
)


class HUD:
    def __init__(self):
        self._font_big   = pygame.font.SysFont("Arial", 24, bold=True)
        self._font_med   = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_small = pygame.font.SysFont("Arial", 14)

    def draw(self, surface: pygame.Surface, player, wave_manager):
        self._draw_health(surface, player)
        self._draw_wave_info(surface, wave_manager)
        self._draw_score(surface, player)
        self._draw_inventory(surface, player)
        self._draw_crosshair(surface)
        if player.is_reloading:
            self._draw_reload_text(surface)

    # ------------------------------------------------------------------
    def _draw_health(self, surface: pygame.Surface, player):
        # Fond semi-transparent
        bar_w, bar_h = 200, 20
        bx, by = 20, SCREEN_H - 50
        bg_surf = pygame.Surface((bar_w + 60, bar_h + 10), pygame.SRCALPHA)
        bg_surf.fill((*COL_HUD_BG, 160))
        surface.blit(bg_surf, (bx - 5, by - 5))

        # Texte HP
        label = self._font_med.render("HP", True, COL_WHITE)
        surface.blit(label, (bx, by - 18))

        # Barre fond
        pygame.draw.rect(surface, COL_DARK_GREY, (bx, by, bar_w, bar_h), border_radius=3)

        # Barre vie
        ratio = player.hp / player.max_hp
        col = COL_HP_BAR if ratio > 0.4 else COL_HP_LOW
        pygame.draw.rect(surface, col,
                         (bx, by, int(bar_w * ratio), bar_h), border_radius=3)
        pygame.draw.rect(surface, COL_WHITE, (bx, by, bar_w, bar_h), 1, border_radius=3)

        # Valeur numerique
        hp_txt = self._font_small.render(f"{player.hp}/{player.max_hp}", True, COL_WHITE)
        surface.blit(hp_txt, (bx + bar_w + 6, by + 3))

    def _draw_wave_info(self, surface: pygame.Surface, wave_manager):
        # Vague actuelle
        wave_txt = self._font_big.render(
            f"VAGUE  {wave_manager.wave_number}", True, COL_YELLOW)
        surface.blit(wave_txt, (SCREEN_W - wave_txt.get_width() - 20, 20))

        # Ennemis restants
        if wave_manager.state == wave_manager.STATE_ACTIVE or \
           wave_manager.state == wave_manager.STATE_SPAWNING:
            enemy_txt = self._font_med.render(
                f"Ennemis: {wave_manager.enemies_remaining}", True, COL_GREY)
            surface.blit(enemy_txt, (SCREEN_W - enemy_txt.get_width() - 20, 52))

        # Compte a rebours entre vagues
        if wave_manager.state in (wave_manager.STATE_CLEAR, wave_manager.STATE_WAITING):
            cd = int(wave_manager.clear_countdown) + 1
            cd_txt = self._font_med.render(
                f"Prochaine vague: {cd}s", True, (100, 220, 100))
            surface.blit(cd_txt, (SCREEN_W - cd_txt.get_width() - 20, 52))

    def _draw_score(self, surface: pygame.Surface, player):
        score_txt = self._font_big.render(f"SCORE  {player.score:,}", True, COL_WHITE)
        surface.blit(score_txt, (SCREEN_W // 2 - score_txt.get_width() // 2, 10))

    def _draw_inventory(self, surface: pygame.Surface, player):
        slot_w, slot_h = 64, 64
        gap = 8
        total_w = len(WEAPON_ORDER) * (slot_w + gap) - gap
        start_x = SCREEN_W // 2 - total_w // 2
        start_y = SCREEN_H - slot_h - 20

        for i, wname in enumerate(WEAPON_ORDER):
            sx = start_x + i * (slot_w + gap)
            sy = start_y
            is_active = (i == player.active_weapon_idx)

            # Fond du slot
            bg_col = (60, 55, 40) if is_active else (30, 28, 22)
            border_col = COL_YELLOW if is_active else COL_DARK_GREY
            pygame.draw.rect(surface, bg_col, (sx, sy, slot_w, slot_h), border_radius=4)
            pygame.draw.rect(surface, border_col, (sx, sy, slot_w, slot_h),
                             2 if is_active else 1, border_radius=4)

            # Nom de l'arme
            name_txt = self._font_small.render(wname.upper(), True,
                                               COL_YELLOW if is_active else COL_GREY)
            surface.blit(name_txt, (sx + slot_w // 2 - name_txt.get_width() // 2,
                                    sy + 6))

            # Munitions
            ammo = player.ammo.get(wname, 0)
            max_ammo = WEAPONS[wname].get("max_ammo", 0)
            ammo_col = COL_WHITE if ammo > max_ammo * 0.3 else COL_RED
            ammo_txt = self._font_med.render(f"{ammo}/{max_ammo}", True, ammo_col)
            surface.blit(ammo_txt, (sx + slot_w // 2 - ammo_txt.get_width() // 2,
                                    sy + slot_h - 24))

            # Indicateur rechargement
            if is_active and player.is_reloading:
                prog_w = int(slot_w * (1.0 - player.reload_timer /
                                       max(0.01, WEAPONS[wname].get("reload_time", 1.5))))
                pygame.draw.rect(surface, (80, 80, 220),
                                 (sx, sy + slot_h - 4, prog_w, 4))

    def _draw_crosshair(self, surface: pygame.Surface):
        mx, my = pygame.mouse.get_pos()
        size = 10
        gap  = 4
        col  = (255, 255, 255)
        pygame.draw.line(surface, col, (mx - size, my), (mx - gap, my), 2)
        pygame.draw.line(surface, col, (mx + gap, my), (mx + size, my), 2)
        pygame.draw.line(surface, col, (mx, my - size), (mx, my - gap), 2)
        pygame.draw.line(surface, col, (mx, my + gap), (mx, my + size), 2)

    def _draw_reload_text(self, surface: pygame.Surface):
        txt = self._font_big.render("RECHARGEMENT...", True, (80, 160, 255))
        surface.blit(txt, (SCREEN_W // 2 - txt.get_width() // 2,
                           SCREEN_H // 2 + 60))
