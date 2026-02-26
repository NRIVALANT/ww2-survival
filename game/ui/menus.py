# menus.py - Menu principal, pause, game over, menu réseau
import pygame
from settings import (
    SCREEN_W, SCREEN_H, STATE_PLAYING, STATE_MENU, STATE_GAMEOVER,
    COL_BLACK, COL_WHITE, COL_YELLOW, COL_RED, COL_GREY, COL_DARK_GREEN,
)

# Résultats possibles du menu réseau
NET_MENU_HOST  = "host"
NET_MENU_JOIN  = "join"
NET_MENU_LOCAL = "local"


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

        # État du menu réseau
        self._net_selected = 0          # 0=Héberger, 1=Rejoindre, 2=Solo
        self._net_ip_input = ""         # IP saisie par l'utilisateur
        self._net_ip_active = False     # La zone IP est-elle active (focus)?
        self._net_name_input = ""       # Nom du joueur
        self._net_name_active = False   # La zone Nom est-elle active?

    def update(self, dt: float):
        self._blink_timer += dt
        if self._blink_timer >= 0.6:
            self._blink_timer = 0.0
            self._blink_state = not self._blink_state

    # ------------------------------------------------------------------
    # Menu réseau : sélection du mode de jeu + saisie IP / Nom
    # ------------------------------------------------------------------
    def handle_net_event(self, event: pygame.event.Event) -> str | None:
        """
        Gère les événements clavier pour le menu réseau.
        Renvoie NET_MENU_HOST / NET_MENU_JOIN / NET_MENU_LOCAL quand
        l'utilisateur confirme son choix avec ENTRÉE, sinon None.
        """
        if event.type == pygame.KEYDOWN:
            # Navigation entre champs via TAB / Flèches
            if event.key in (pygame.K_UP, pygame.K_LEFT):
                self._net_selected = (self._net_selected - 1) % 3
                self._net_ip_active   = False
                self._net_name_active = False

            elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                self._net_selected = (self._net_selected + 1) % 3
                self._net_ip_active   = False
                self._net_name_active = False

            elif event.key == pygame.K_TAB:
                # Basculer le focus entre les champs texte
                if self._net_ip_active:
                    self._net_ip_active   = False
                    self._net_name_active = True
                elif self._net_name_active:
                    self._net_name_active = False
                    self._net_ip_active   = False
                else:
                    self._net_name_active = True

            elif event.key == pygame.K_BACKSPACE:
                if self._net_ip_active and self._net_ip_input:
                    self._net_ip_input = self._net_ip_input[:-1]
                elif self._net_name_active and self._net_name_input:
                    self._net_name_input = self._net_name_input[:-1]

            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                # Désactiver les champs texte, confirmer le choix
                if self._net_ip_active or self._net_name_active:
                    self._net_ip_active   = False
                    self._net_name_active = False
                else:
                    return [NET_MENU_HOST, NET_MENU_JOIN, NET_MENU_LOCAL][self._net_selected]

            else:
                # Saisie de texte
                char = event.unicode
                if self._net_ip_active:
                    # IP : chiffres et points uniquement, max 15 chars
                    if char in "0123456789." and len(self._net_ip_input) < 15:
                        self._net_ip_input += char
                elif self._net_name_active:
                    # Nom : alphanum + espaces, max 16 chars
                    if char.isprintable() and len(self._net_name_input) < 16:
                        self._net_name_input += char

        elif event.type == pygame.MOUSEBUTTONDOWN:
            mx, my = event.pos
            # Zones de clic définies dans draw_network_menu
            # On les recalcule ici pour la détection
            btn_x  = SCREEN_W // 2 - 160
            btn_w  = 320
            btn_h  = 52
            gap    = 16
            base_y = 260

            options = [NET_MENU_HOST, NET_MENU_JOIN, NET_MENU_LOCAL]
            for i, _ in enumerate(options):
                by = base_y + i * (btn_h + gap)
                if btn_x <= mx <= btn_x + btn_w and by <= my <= by + btn_h:
                    self._net_selected = i
                    self._net_ip_active   = False
                    self._net_name_active = False

            # Zone saisie IP
            ip_rect = pygame.Rect(SCREEN_W // 2 - 140, base_y + 3 * (btn_h + gap) + 30,
                                  280, 34)
            if ip_rect.collidepoint(mx, my):
                self._net_ip_active   = True
                self._net_name_active = False

            # Zone saisie Nom
            name_rect = pygame.Rect(SCREEN_W // 2 - 140, ip_rect.y + 60, 280, 34)
            if name_rect.collidepoint(mx, my):
                self._net_name_active = True
                self._net_ip_active   = False

        return None

    def draw_network_menu(self, surface: pygame.Surface):
        """
        Dessine le menu de sélection réseau.
        Retourne None en continu (la confirmation se fait via handle_net_event).
        """
        surface.fill((18, 16, 12))
        pygame.draw.rect(surface, (40, 35, 25), (0, 0, SCREEN_W, 8))
        pygame.draw.rect(surface, (40, 35, 25), (0, SCREEN_H - 8, SCREEN_W, 8))

        _center_text(surface, self._font_title, "WW2 SURVIVAL", COL_YELLOW, 80)
        _center_text(surface, self._font_sub,   "MODE MULTIJOUEUR LAN", COL_GREY, 165)

        pygame.draw.line(surface, COL_YELLOW,
                         (SCREEN_W // 4, 205), (SCREEN_W * 3 // 4, 205), 2)

        options = [
            ("HÉBERGER",  "Vous créez la partie (vous jouez en même temps)",  (55, 180, 55)),
            ("REJOINDRE", "Rejoignez un serveur existant (saisissez l'IP)",   (55, 120, 200)),
            ("SOLO",      "Mode local, sans réseau",                          (180, 160, 60)),
        ]
        btn_x = SCREEN_W // 2 - 160
        btn_w = 320
        btn_h = 52
        gap   = 16
        base_y = 230

        for i, (label, desc, col) in enumerate(options):
            by     = base_y + i * (btn_h + gap)
            is_sel = (i == self._net_selected)

            # Fond du bouton
            bg_col = (*col, 180) if is_sel else (30, 28, 22, 200)
            bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            bg.fill(bg_col)
            surface.blit(bg, (btn_x, by))
            border_col = col if is_sel else (60, 58, 50)
            pygame.draw.rect(surface, border_col,
                             (btn_x, by, btn_w, btn_h), 2 if is_sel else 1,
                             border_radius=6)

            # Label
            lbl_surf = self._font_sub.render(label, True,
                                             COL_WHITE if is_sel else COL_GREY)
            surface.blit(lbl_surf, (btn_x + btn_w // 2 - lbl_surf.get_width() // 2,
                                    by + 6))

            # Description (petite police, sous le label)
            desc_surf = self._font_small.render(desc, True,
                                                COL_WHITE if is_sel else (90, 88, 80))
            surface.blit(desc_surf, (btn_x + btn_w // 2 - desc_surf.get_width() // 2,
                                     by + 32))

        # ---- Champs de saisie ----
        field_y = base_y + 3 * (btn_h + gap) + 20

        # IP du serveur
        _center_text(surface, self._font_small, "IP du serveur (pour rejoindre) :",
                     COL_GREY, field_y)
        field_y += 22
        ip_rect = pygame.Rect(SCREEN_W // 2 - 140, field_y, 280, 34)
        ip_bg   = (35, 40, 35) if self._net_ip_active else (25, 25, 22)
        pygame.draw.rect(surface, ip_bg, ip_rect, border_radius=4)
        pygame.draw.rect(surface, COL_YELLOW if self._net_ip_active else COL_GREY,
                         ip_rect, 2, border_radius=4)
        ip_txt = self._font_normal.render(
            self._net_ip_input + ("|" if self._net_ip_active and self._blink_state else ""),
            True, COL_WHITE)
        surface.blit(ip_txt, (ip_rect.x + 8, ip_rect.y + 7))
        if not self._net_ip_input:
            hint = self._font_small.render("ex: 192.168.1.X", True, (80, 80, 70))
            surface.blit(hint, (ip_rect.x + 8, ip_rect.y + 10))

        field_y += 42

        # Nom du joueur
        _center_text(surface, self._font_small, "Votre nom :", COL_GREY, field_y)
        field_y += 22
        name_rect = pygame.Rect(SCREEN_W // 2 - 140, field_y, 280, 34)
        name_bg   = (35, 40, 35) if self._net_name_active else (25, 25, 22)
        pygame.draw.rect(surface, name_bg, name_rect, border_radius=4)
        pygame.draw.rect(surface, COL_YELLOW if self._net_name_active else COL_GREY,
                         name_rect, 2, border_radius=4)
        name_txt = self._font_normal.render(
            self._net_name_input + ("|" if self._net_name_active and self._blink_state else ""),
            True, COL_WHITE)
        surface.blit(name_txt, (name_rect.x + 8, name_rect.y + 7))
        if not self._net_name_input:
            hint2 = self._font_small.render("ex: Joueur1", True, (80, 80, 70))
            surface.blit(hint2, (name_rect.x + 8, name_rect.y + 10))

        field_y += 50

        # Aide clavier
        help_lines = [
            "← → ou ↑ ↓  :  changer le mode",
            "ENTRÉE  :  confirmer",
            "TAB  :  basculer vers les champs texte",
            "CLIC  :  cliquer sur un bouton / champ",
        ]
        for line in help_lines:
            hs = self._font_small.render(line, True, (70, 68, 60))
            surface.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, field_y))
            field_y += 20

    @property
    def net_ip(self) -> str:
        return self._net_ip_input.strip()

    @property
    def net_name(self) -> str:
        return self._net_name_input.strip() or "Joueur"

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
