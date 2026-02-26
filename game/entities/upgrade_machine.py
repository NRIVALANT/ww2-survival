# upgrade_machine.py - Machine d'amélioration d'armes (style CoD Zombies)
import pygame
import math

from settings import (
    TILE_SIZE,
    UPGRADE_MACHINE_COST, UPGRADE_MACHINE_MAX_LVL,
    COL_WHITE, COL_BLACK, COL_YELLOW,
)

# Couleur de la machine (définie localement pour éviter les imports circulaires)
_COL_MACH_BASE  = (30,  40,  60)
_COL_MACH_GLOW  = (80, 180, 255)
_COL_MACH_TEXT  = (200, 230, 255)
_COL_MAX_LVL    = (255, 190,  40)
_COL_CANT_AFFORD= (220,  60,  60)


def _draw_lightning(surface: pygame.Surface, cx: int, cy: int, size: int, color):
    """Dessine un éclair stylisé centré sur (cx, cy)."""
    h = size
    w = size // 2
    pts_top = [
        (cx + w // 3,          cy - h // 2),
        (cx - w // 4,          cy + 2),
        (cx + w // 5,          cy + 2),
        (cx - w // 3,          cy + h // 2),
        (cx + w // 4,          cy - 2),
        (cx - w // 5,          cy - 2),
    ]
    if len(pts_top) >= 3:
        pygame.draw.polygon(surface, color, pts_top)


class UpgradeMachine:
    """
    Machine d'amélioration placée dans le bunker central.
    Appuyer sur [F] quand à portée pour améliorer l'arme active (coût : 5 000 pts).
    Effets par niveau : dégâts ×1.5 · vitesse balle ×1.1 · chargeur ×1.5
    Max 3 niveaux par arme.
    """

    INTERACT_RANGE = 90   # px
    WIDTH  = 42
    HEIGHT = 54

    def __init__(self, tile_col: int, tile_row: int):
        wx = tile_col * TILE_SIZE + TILE_SIZE // 2
        wy = tile_row * TILE_SIZE + TILE_SIZE // 2
        self.pos  = pygame.Vector2(wx, wy)
        self.rect = pygame.Rect(0, 0, self.WIDTH, self.HEIGHT)
        self.rect.center = (int(wx), int(wy))

        # Niveaux d'amélioration par nom d'arme
        self.upgrade_levels: dict[str, int] = {}

        # Dernier message de résultat (affiché à l'écran)
        self.last_message      = ""
        self.last_message_timer = 0.0

        self._anim_t = 0.0

        # Cache de fontes (initialisé paresseusement)
        self._font_sm  = None
        self._font_med = None

    # ------------------------------------------------------------------
    def update(self, dt: float):
        self._anim_t += dt
        if self.last_message_timer > 0:
            self.last_message_timer -= dt

    def player_in_range(self, player) -> bool:
        return (pygame.Vector2(player.rect.center) - self.pos).length() <= self.INTERACT_RANGE

    # ------------------------------------------------------------------
    def try_upgrade(self, player) -> str:
        """
        Tente d'améliorer l'arme active du joueur.
        Retourne un message de résultat (string).
        """
        weapon_name = player.active_weapon

        # Les grenades ne peuvent pas être améliorées
        if weapon_name == "grenade":
            msg = "Impossible d'améliorer les grenades !"
            self._set_message(msg)
            return msg

        level = self.upgrade_levels.get(weapon_name, 0)

        if level >= UPGRADE_MACHINE_MAX_LVL:
            msg = f"{weapon_name.upper()} : niveau maximum atteint !"
            self._set_message(msg)
            return msg

        if player.score < UPGRADE_MACHINE_COST:
            manque = UPGRADE_MACHINE_COST - player.score
            msg = f"Pas assez de points ! (manque {manque} pts)"
            self._set_message(msg)
            return msg

        # Déduire les points, appliquer l'amélioration
        player.score -= UPGRADE_MACHINE_COST
        self.upgrade_levels[weapon_name] = level + 1
        self._apply_upgrade(player, weapon_name)

        new_lvl = level + 1
        msg = (f"{weapon_name.upper()} amélioré ! "
               f"Niveau {new_lvl}/{UPGRADE_MACHINE_MAX_LVL}  "
               f"(-{UPGRADE_MACHINE_COST} pts)")
        self._set_message(msg)

        # Popup de points sur le joueur
        player.add_score_popup(f"-{UPGRADE_MACHINE_COST} pts", player.pos)
        return msg

    def _apply_upgrade(self, player, weapon_name: str):
        """Applique les bonus d'amélioration sur une copie profonde déjà créée."""
        wdata = player.weapons[weapon_name]
        wdata["damage"]       = int(wdata["damage"]       * 1.5)
        wdata["bullet_speed"] = int(wdata["bullet_speed"] * 1.1)
        old_max = wdata["max_ammo"]
        wdata["max_ammo"]     = int(old_max * 1.5)
        # Recharger le chargeur au nouveau maximum
        player.ammo[weapon_name] = wdata["max_ammo"]

    def _set_message(self, msg: str):
        self.last_message       = msg
        self.last_message_timer = 3.0

    def get_level(self, weapon_name: str) -> int:
        return self.upgrade_levels.get(weapon_name, 0)

    # ------------------------------------------------------------------
    def draw(self, surface: pygame.Surface, camera, player=None):
        sx, sy = camera.apply_pos(self.pos.x, self.pos.y)
        sx, sy = int(sx), int(sy)

        if self._font_sm  is None:
            self._font_sm  = pygame.font.SysFont("Arial", 11, bold=True)
        if self._font_med is None:
            self._font_med = pygame.font.SysFont("Arial", 14, bold=True)

        # Pulsation lumineuse
        pulse = (math.sin(self._anim_t * 3.0) + 1.0) / 2.0   # 0..1
        glow = (
            int(_COL_MACH_GLOW[0] + pulse * 80),
            int(_COL_MACH_GLOW[1] + pulse * 60),
            min(255, int(_COL_MACH_GLOW[2] + pulse * 40)),
        )

        # --- Corps de la machine ---
        body = pygame.Rect(sx - self.WIDTH // 2, sy - self.HEIGHT // 2,
                           self.WIDTH, self.HEIGHT)
        pygame.draw.rect(surface, _COL_MACH_BASE, body, border_radius=5)

        # Bordure animée
        pygame.draw.rect(surface, glow, body, 2, border_radius=5)

        # Panneau supérieur (écran)
        panel = pygame.Rect(body.x + 4, body.y + 4, self.WIDTH - 8, 18)
        pygame.draw.rect(surface, (10, 20, 40), panel, border_radius=3)
        pygame.draw.rect(surface, glow, panel, 1, border_radius=3)

        # Éclair dessiné
        _draw_lightning(surface, sx, sy + 8, 22, glow)

        # Texte coût en bas
        in_range     = player is not None and self.player_in_range(player)
        can_afford   = player is not None and player.score >= UPGRADE_MACHINE_COST

        if in_range and player is not None:
            wname = player.active_weapon
            lvl   = self.get_level(wname)
            if lvl >= UPGRADE_MACHINE_MAX_LVL:
                cost_col = _COL_MAX_LVL
                cost_str = f"MAX ({wname.upper()})"
            elif not can_afford:
                cost_col = _COL_CANT_AFFORD
                cost_str = f"{UPGRADE_MACHINE_COST} pts"
            else:
                cost_col = COL_YELLOW
                cost_str = f"{UPGRADE_MACHINE_COST} pts"
        else:
            cost_col = _COL_MACH_TEXT
            cost_str = f"{UPGRADE_MACHINE_COST} pts"

        cost_surf = self._font_sm.render(cost_str, True, cost_col)
        surface.blit(cost_surf,
                     (sx - cost_surf.get_width() // 2,
                      sy + self.HEIGHT // 2 + 4))

        # Étiquette "UPGRADE"
        label = self._font_sm.render("UPGRADE", True, _COL_MACH_TEXT)
        surface.blit(label, (sx - label.get_width() // 2, body.y - 14))

    def draw_hud_prompt(self, surface: pygame.Surface,
                        screen_w: int, screen_h: int, player):
        """Affiche le prompt [F] et le message de résultat en bas de l'écran."""
        if self._font_med is None:
            self._font_med = pygame.font.SysFont("Arial", 14, bold=True)
        font_big = pygame.font.SysFont("Arial", 20, bold=True)

        wname = player.active_weapon
        lvl   = self.get_level(wname)

        if lvl >= UPGRADE_MACHINE_MAX_LVL:
            prompt = f"[F]  {wname.upper()} déjà au niveau MAX"
            pcol   = _COL_MAX_LVL
        elif player.score < UPGRADE_MACHINE_COST:
            manque = UPGRADE_MACHINE_COST - player.score
            prompt = f"[F]  Améliorer {wname.upper()}  —  {UPGRADE_MACHINE_COST} pts  (manque {manque})"
            pcol   = _COL_CANT_AFFORD
        else:
            prompt = f"[F]  Améliorer {wname.upper()}  —  {UPGRADE_MACHINE_COST} pts"
            pcol   = COL_YELLOW

        # Fond semi-transparent
        psurf = font_big.render(prompt, True, pcol)
        bx = screen_w // 2 - psurf.get_width() // 2 - 10
        by = screen_h - 160
        bg = pygame.Surface((psurf.get_width() + 20, psurf.get_height() + 10),
                             pygame.SRCALPHA)
        bg.fill((10, 10, 10, 180))
        surface.blit(bg, (bx, by))
        surface.blit(psurf, (bx + 10, by + 5))

        # Niveau actuel
        lvl_str  = f"Niveau actuel : {lvl}/{UPGRADE_MACHINE_MAX_LVL}"
        lvl_surf = self._font_med.render(lvl_str, True, _COL_MACH_TEXT)
        surface.blit(lvl_surf, (screen_w // 2 - lvl_surf.get_width() // 2,
                                by + psurf.get_height() + 12))

    def draw_result_message(self, surface: pygame.Surface,
                            screen_w: int, screen_h: int):
        """Affiche le message de résultat temporaire après une interaction."""
        if self.last_message_timer <= 0 or not self.last_message:
            return
        if self._font_med is None:
            self._font_med = pygame.font.SysFont("Arial", 14, bold=True)
        font = pygame.font.SysFont("Arial", 22, bold=True)

        alpha = min(255, int(self.last_message_timer / 3.0 * 255))
        surf  = font.render(self.last_message, True, COL_YELLOW)
        surf.set_alpha(alpha)
        x = screen_w // 2 - surf.get_width() // 2
        y = screen_h // 2 - 80
        surface.blit(surf, (x, y))
