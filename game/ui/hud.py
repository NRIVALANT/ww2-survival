# hud.py - Interface utilisateur en jeu
import pygame
from settings import (
    SCREEN_W, SCREEN_H, WEAPON_ORDER, WEAPONS,
    COL_HUD_BG, COL_HP_BAR, COL_HP_LOW, COL_WHITE, COL_BLACK,
    COL_YELLOW, COL_GREY, COL_DARK_GREY, COL_RED, COL_DARK_GREEN,
    COL_POINTS_POPUP, REVIVE_TIME, DOWN_TIMEOUT, PLAYER_COLORS,
)


class HUD:
    def __init__(self):
        self._font_big   = pygame.font.SysFont("Arial", 24, bold=True)
        self._font_med   = pygame.font.SysFont("Arial", 18, bold=True)
        self._font_small = pygame.font.SysFont("Arial", 14)

    def draw(self, surface: pygame.Surface, player, wave_manager):
        self._draw_player_panel(surface, player)
        self._draw_wave_info(surface, wave_manager)
        self._draw_inventory(surface, player)
        self._draw_crosshair(surface)
        if player.is_reloading:
            self._draw_reload_text(surface)

    def draw_score_popups(self, surface: pygame.Surface, player, camera):
        """Dessine les popups de points flottants (+10, +100, etc.)."""
        for popup in player.score_popups:
            # Convertir position monde → écran
            sx, sy = camera.apply_pos(popup["x"], popup["y"])
            # Remonter au fil du temps
            elapsed = 1.0 - popup["timer"]   # 0..1
            sy -= elapsed * 50               # monte de 50px
            # Fondu sortant
            alpha = int(min(255, popup["timer"] / 0.4 * 255))
            # Couleur selon contenu (négatif = rouge, positif = jaune)
            col = (220, 80, 60) if popup["text"].startswith("-") else COL_POINTS_POPUP
            surf = self._font_med.render(popup["text"], True, col)
            surf.set_alpha(alpha)
            surface.blit(surf, (int(sx) - surf.get_width() // 2, int(sy)))

    # ------------------------------------------------------------------
    def _draw_player_panel(self, surface: pygame.Surface, player):
        """Panneau haut-gauche : nom, score, barre HP."""
        panel_x = 12
        panel_y = 30
        panel_w = 220
        panel_h = 68

        # Fond semi-transparent
        bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        bg.fill((*COL_HUD_BG, 160))
        surface.blit(bg, (panel_x, panel_y))
        pid   = getattr(player, "player_id", 1)
        color = PLAYER_COLORS[(pid - 1) % len(PLAYER_COLORS)]
        pygame.draw.rect(surface, color,
                         (panel_x, panel_y, panel_w, panel_h), 2, border_radius=3)

        # Nom + score
        pname      = getattr(player, "player_name", "Host")
        score      = getattr(player, "score", 0)
        name_surf  = self._font_small.render(pname, True, color)
        score_surf = self._font_small.render(f"{score:,} pts", True, COL_YELLOW)
        surface.blit(name_surf,  (panel_x + 6, panel_y + 5))
        surface.blit(score_surf, (panel_x + panel_w - score_surf.get_width() - 6,
                                  panel_y + 5))

        # Barre HP
        bar_w, bar_h = panel_w - 12, 16
        bx, by = panel_x + 6, panel_y + 26
        pygame.draw.rect(surface, COL_DARK_GREY, (bx, by, bar_w, bar_h), border_radius=3)
        ratio = player.hp / max(1, player.max_hp)
        col = COL_HP_BAR if ratio > 0.4 else COL_HP_LOW
        pygame.draw.rect(surface, col,
                         (bx, by, int(bar_w * ratio), bar_h), border_radius=3)
        pygame.draw.rect(surface, COL_WHITE, (bx, by, bar_w, bar_h), 1, border_radius=3)
        hp_txt = self._font_small.render(f"HP  {player.hp}/{player.max_hp}", True, COL_WHITE)
        surface.blit(hp_txt, (bx + bar_w // 2 - hp_txt.get_width() // 2, by + 1))

        # Score centré en haut
        score_big = self._font_big.render(f"SCORE  {score:,}", True, COL_WHITE)
        surface.blit(score_big, (SCREEN_W // 2 - score_big.get_width() // 2, 10))

    def _draw_health(self, surface: pygame.Surface, player):
        """Compatibilite - appeler _draw_player_panel a la place."""
        self._draw_player_panel(surface, player)

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
        """Compatibilite - le score est desormais dans _draw_player_panel."""
        pass

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

    # ------------------------------------------------------------------
    def draw_other_players_hud(self, surface: pygame.Surface, others: list):
        """Dessine les mini-HUDs des joueurs alliés (HP, état, nom)."""
        if not others:
            return

        panel_w = 180
        panel_h = 52
        gap     = 8
        start_x = SCREEN_W - panel_w - 12
        start_y = 60   # sous l'indicateur de connexion

        for i, player in enumerate(others):
            y = start_y + i * (panel_h + gap)

            # Fond semi-transparent
            bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            state = getattr(player, "state", "alive")
            if state == "down":
                bg.fill((120, 30, 30, 180))
            elif state == "dead":
                bg.fill((50, 50, 50, 180))
            else:
                bg.fill((*COL_HUD_BG, 160))
            surface.blit(bg, (start_x, y))

            # Bordure couleur du joueur
            color = getattr(player, "color", COL_WHITE)
            pygame.draw.rect(surface, color,
                             (start_x, y, panel_w, panel_h), 2, border_radius=3)

            # Nom du joueur
            name = getattr(player, "player_name", "Allié")
            name_surf = self._font_small.render(name[:14], True, color)
            surface.blit(name_surf, (start_x + 6, y + 4))

            if state == "alive":
                # Barre HP
                hp     = getattr(player, "hp", 0)
                max_hp = getattr(player, "max_hp", 100)
                bar_w  = panel_w - 12
                bar_x  = start_x + 6
                bar_y  = y + 24
                pygame.draw.rect(surface, COL_DARK_GREY,
                                 (bar_x, bar_y, bar_w, 12), border_radius=3)
                ratio  = max(0.0, hp / max(1, max_hp))
                hp_col = COL_HP_BAR if ratio > 0.4 else COL_HP_LOW
                pygame.draw.rect(surface, hp_col,
                                 (bar_x, bar_y, int(bar_w * ratio), 12),
                                 border_radius=3)
                pygame.draw.rect(surface, COL_WHITE,
                                 (bar_x, bar_y, bar_w, 12), 1, border_radius=3)
                hp_txt = self._font_small.render(f"{hp}/{max_hp}", True, COL_WHITE)
                surface.blit(hp_txt, (bar_x + bar_w // 2 - hp_txt.get_width() // 2,
                                      bar_y))

            elif state == "down":
                # Compte à rebours de revive + barre de progression
                down_timer  = getattr(player, "down_timer", 0.0)
                rev_progress = getattr(player, "revive_progress", 0.0)

                status_txt = self._font_small.render(
                    f"A TERRE  {int(down_timer)+1}s", True, COL_RED)
                surface.blit(status_txt, (start_x + 6, y + 22))

                # Barre de progression de relève
                if rev_progress > 0:
                    bar_w = panel_w - 12
                    bar_x = start_x + 6
                    bar_y = y + 38
                    pygame.draw.rect(surface, COL_DARK_GREY,
                                     (bar_x, bar_y, bar_w, 8), border_radius=2)
                    pygame.draw.rect(surface, (80, 200, 120),
                                     (bar_x, bar_y, int(bar_w * min(1.0, rev_progress)), 8),
                                     border_radius=2)

            elif state == "dead":
                dead_txt = self._font_small.render("MORT (prochaine vague)", True, COL_GREY)
                surface.blit(dead_txt, (start_x + 6, y + 22))

    def draw_other_players_hud_from_dicts(self, surface: pygame.Surface,
                                          others: list[dict], my_player_id: int):
        """Version pour le ClientGame : alliés = liste de dicts sérialisés."""
        if not others:
            return

        # Importer ici pour éviter la dépendance circulaire
        from settings import PLAYER_COLORS

        panel_w = 180
        panel_h = 52
        gap     = 8
        start_x = SCREEN_W - panel_w - 12
        start_y = 60

        others_filtered = [p for p in others if p.get("player_id") != my_player_id]

        for i, pdata in enumerate(others_filtered):
            y = start_y + i * (panel_h + gap)

            state = pdata.get("state", "alive")

            # Fond
            bg = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
            if state == "down":
                bg.fill((120, 30, 30, 180))
            elif state == "dead":
                bg.fill((50, 50, 50, 180))
            else:
                bg.fill((*COL_HUD_BG, 160))
            surface.blit(bg, (start_x, y))

            # Couleur du joueur
            pid   = pdata.get("player_id", 0)
            color = PLAYER_COLORS[(pid - 1) % len(PLAYER_COLORS)]
            pygame.draw.rect(surface, color,
                             (start_x, y, panel_w, panel_h), 2, border_radius=3)

            # Nom
            name = str(pdata.get("player_name", f"Joueur {pid}"))[:14]
            name_surf = self._font_small.render(name, True, color)
            surface.blit(name_surf, (start_x + 6, y + 4))

            if state == "alive":
                hp     = int(pdata.get("hp", 0))
                max_hp = int(pdata.get("max_hp", 100))
                bar_w  = panel_w - 12
                bar_x  = start_x + 6
                bar_y  = y + 24
                pygame.draw.rect(surface, COL_DARK_GREY,
                                 (bar_x, bar_y, bar_w, 12), border_radius=3)
                ratio  = max(0.0, hp / max(1, max_hp))
                hp_col = COL_HP_BAR if ratio > 0.4 else COL_HP_LOW
                pygame.draw.rect(surface, hp_col,
                                 (bar_x, bar_y, int(bar_w * ratio), 12),
                                 border_radius=3)
                pygame.draw.rect(surface, COL_WHITE,
                                 (bar_x, bar_y, bar_w, 12), 1, border_radius=3)
                hp_txt = self._font_small.render(f"{hp}/{max_hp}", True, COL_WHITE)
                surface.blit(hp_txt, (bar_x + bar_w // 2 - hp_txt.get_width() // 2,
                                      bar_y))

            elif state == "down":
                down_timer   = float(pdata.get("down_timer", 0.0))
                rev_progress = float(pdata.get("revive_progress", 0.0))
                status_txt = self._font_small.render(
                    f"A TERRE  {int(down_timer)+1}s", True, COL_RED)
                surface.blit(status_txt, (start_x + 6, y + 22))
                if rev_progress > 0:
                    bar_w = panel_w - 12
                    bar_x = start_x + 6
                    bar_y = y + 38
                    pygame.draw.rect(surface, COL_DARK_GREY,
                                     (bar_x, bar_y, bar_w, 8), border_radius=2)
                    pygame.draw.rect(surface, (80, 200, 120),
                                     (bar_x, bar_y, int(bar_w * min(1.0, rev_progress)), 8),
                                     border_radius=2)

            elif state == "dead":
                dead_txt = self._font_small.render("MORT (prochaine vague)", True, COL_GREY)
                surface.blit(dead_txt, (start_x + 6, y + 22))
