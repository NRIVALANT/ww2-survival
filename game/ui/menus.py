# menus.py - Menu principal, pause, game over, menu réseau
import pygame
from settings import (
    SCREEN_W, SCREEN_H, STATE_PLAYING, STATE_MENU, STATE_GAMEOVER,
    COL_BLACK, COL_WHITE, COL_YELLOW, COL_RED, COL_GREY, COL_DARK_GREEN,
    KEYBINDS, KEYBINDS_DEFAULT, STATE_SETTINGS, PLAYER_COLORS, NET_MAX_PLAYERS,
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
    # Libellés affichés dans le menu paramètres
    _KEYBIND_ROWS = [
        ("move_up",    "Avancer"),
        ("move_down",  "Reculer"),
        ("move_left",  "Aller à gauche"),
        ("move_right", "Aller à droite"),
        ("reload",     "Recharger"),
        ("weapon_prev","Arme précédente"),
        ("revive",     "Relever allié"),
        ("upgrade",    "Machine d'amélioration"),
        ("pause",      "Pause"),
        ("slot_1",     "Slot 1 (Pistolet)"),
        ("slot_2",     "Slot 2 (Fusil)"),
        ("slot_3",     "Slot 3 (Mitraillette)"),
        ("slot_4",     "Slot 4 (Grenade)"),
    ]

    def __init__(self):
        self._font_title  = pygame.font.SysFont("Arial", 64, bold=True)
        self._font_sub    = pygame.font.SysFont("Arial", 28, bold=True)
        self._font_normal = pygame.font.SysFont("Arial", 22)
        self._font_small  = pygame.font.SysFont("Arial", 16)
        self._blink_timer = 0.0
        self._blink_state = True

        # Menu principal : navigation clavier + résultat clic en attente
        self._main_selected  = 0       # 0=JOUER 1=PARAMÈTRES 2=QUITTER
        self._main_result    = None    # résultat d'un clic mouse, lu par draw

        # Menu paramètres : rebind
        self._settings_selected = -1   # index ligne sélectionnée
        self._settings_waiting  = False  # en attente d'une touche

        # Menu pause : résultat clic stocké par handle_pause_event, consommé par draw_pause
        self._pause_result = None

        # Menu game over : résultat clic stocké par handle_gameover_event, consommé par draw_game_over
        self._gameover_result = None

        # Lobby : résultat bouton "LANCER" stocké par handle_lobby_event
        self._lobby_start_result = None

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
            base_y = 230   # doit correspondre exactement à draw_network_menu

            options = [NET_MENU_HOST, NET_MENU_JOIN, NET_MENU_LOCAL]
            for i, _ in enumerate(options):
                by = base_y + i * (btn_h + gap)
                if btn_x <= mx <= btn_x + btn_w and by <= my <= by + btn_h:
                    self._net_selected = i
                    self._net_ip_active   = False
                    self._net_name_active = False

            # Zone saisie IP — calcul identique à draw_network_menu
            # field_y = base_y + 3*(btn_h+gap) + 20  puis +22 pour le label
            ip_y = base_y + 3 * (btn_h + gap) + 20 + 22
            ip_rect = pygame.Rect(SCREEN_W // 2 - 140, ip_y, 280, 34)
            if ip_rect.collidepoint(mx, my):
                self._net_ip_active   = True
                self._net_name_active = False

            # Zone saisie Nom — +42 (hauteur champ IP) +22 (label Nom)
            name_y = ip_y + 42 + 22
            name_rect = pygame.Rect(SCREEN_W // 2 - 140, name_y, 280, 34)
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
    # Menu principal
    # ------------------------------------------------------------------
    def handle_main_event(self, event: pygame.event.Event) -> None:
        """Gère les événements clavier/souris du menu principal."""
        BTN_W, BTN_H = 340, 62
        GAP      = 16
        START_Y  = 255
        ACTIONS  = [STATE_PLAYING, STATE_SETTINGS, "quit"]

        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_UP, pygame.K_LEFT):
                self._main_selected = (self._main_selected - 1) % 3
            elif event.key in (pygame.K_DOWN, pygame.K_RIGHT):
                self._main_selected = (self._main_selected + 1) % 3
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self._main_result = ACTIONS[self._main_selected]
            elif event.key == pygame.K_SPACE:
                self._main_result = STATE_PLAYING

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            for i, action in enumerate(ACTIONS):
                bx = SCREEN_W // 2 - BTN_W // 2
                by = START_Y + i * (BTN_H + GAP)
                if bx <= mx <= bx + BTN_W and by <= my <= by + BTN_H:
                    self._main_result = action
                    break

    def draw_main_menu(self, surface: pygame.Surface) -> str | None:
        """Dessine le menu principal avec boutons cliquables."""
        surface.fill((20, 18, 14))
        pygame.draw.rect(surface, (40, 35, 25), (0, 0, SCREEN_W, 8))
        pygame.draw.rect(surface, (40, 35, 25), (0, SCREEN_H - 8, SCREEN_W, 8))

        _center_text(surface, self._font_title, "WW2 SURVIVAL", COL_YELLOW, 95)
        _center_text(surface, self._font_sub,   "1944 — FRONT DE L'OUEST", COL_GREY, 178)
        pygame.draw.line(surface, COL_YELLOW,
                         (SCREEN_W // 4, 222), (SCREEN_W * 3 // 4, 222), 2)

        BUTTONS = [
            ("JOUER",      (50, 155, 55),  (85, 210, 90)),
            ("PARAMÈTRES", (60,  88, 135), (90, 140, 185)),
            ("QUITTER",    (140, 50,  50), (195, 75,  75)),
        ]
        BTN_W, BTN_H = 340, 62
        GAP = 16
        START_Y = 255
        mx, my = pygame.mouse.get_pos()

        result = self._main_result
        self._main_result = None   # consomme

        for i, (label, col, hcol) in enumerate(BUTTONS):
            bx = SCREEN_W // 2 - BTN_W // 2
            by = START_Y + i * (BTN_H + GAP)
            rect = pygame.Rect(bx, by, BTN_W, BTN_H)
            is_hover  = rect.collidepoint(mx, my)
            is_kbsel  = (i == self._main_selected)
            cur_col   = hcol if (is_hover or is_kbsel) else col

            bg = pygame.Surface((BTN_W, BTN_H), pygame.SRCALPHA)
            bg.fill((*cur_col, 215))
            surface.blit(bg, (bx, by))
            pygame.draw.rect(surface, hcol if (is_hover or is_kbsel) else
                             tuple(min(255, c + 20) for c in col),
                             rect, 2, border_radius=8)

            lbl = self._font_sub.render(label, True, COL_WHITE)
            surface.blit(lbl, (bx + BTN_W // 2 - lbl.get_width() // 2,
                               by + BTN_H // 2 - lbl.get_height() // 2))

        # Récapitulatif raccourcis basé sur KEYBINDS courants
        sep_y = START_Y + 3 * (BTN_H + GAP) + 8
        pygame.draw.line(surface, (45, 42, 35),
                         (SCREEN_W // 4, sep_y), (SCREEN_W * 3 // 4, sep_y), 1)
        def kn(k): return pygame.key.name(KEYBINDS[k]).upper()
        lines = [
            (f"Dépl. : {kn('move_up')} {kn('move_left')} {kn('move_down')} {kn('move_right')}   "
             f"  Tirer : CLIC G   Recharger : {kn('reload')}"),
            (f"Pause : {kn('pause')}   Améliorer : {kn('upgrade')}   "
             f"Arme préc. : {kn('weapon_prev')}   Relever : {kn('revive')}"),
        ]
        ry = sep_y + 10
        for line in lines:
            s = self._font_small.render(line, True, (90, 88, 78))
            surface.blit(s, (SCREEN_W // 2 - s.get_width() // 2, ry))
            ry += 20

        _center_text(surface, self._font_small,
                     "⬆⬇ naviguer  |  ENTRÉE confirmer  |  ESPACE jouer directement",
                     (70, 68, 58), SCREEN_H - 32, shadow=False)

        return result

    # ------------------------------------------------------------------
    # Menu paramètres (rebind)
    # ------------------------------------------------------------------
    def handle_settings_event(self, event: pygame.event.Event) -> str | None:
        """
        Gère les événements du menu paramètres.
        Retourne "back" quand l'utilisateur veut revenir au menu principal.
        """
        ROW_H   = 32
        START_Y = 100   # = 82 (base) + 18 (hauteur en-tête) — doit correspondre à draw_settings_menu
        TABLE_X = SCREEN_W // 2 - 270
        TABLE_W = 540

        if event.type == pygame.KEYDOWN:
            if self._settings_waiting and self._settings_selected >= 0:
                if event.key == pygame.K_ESCAPE:
                    # Annuler le rebind en cours
                    self._settings_waiting  = False
                    self._settings_selected = -1
                else:
                    action = self._KEYBIND_ROWS[self._settings_selected][0]
                    KEYBINDS[action] = event.key
                    self._settings_waiting  = False
                    self._settings_selected = -1
            else:
                if event.key == pygame.K_ESCAPE:
                    return "back"

        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            # Clics sur les lignes du tableau
            for i in range(len(self._KEYBIND_ROWS)):
                row_y = START_Y + i * ROW_H
                row_rect = pygame.Rect(TABLE_X, row_y, TABLE_W, ROW_H - 2)
                if row_rect.collidepoint(mx, my):
                    if self._settings_selected == i and not self._settings_waiting:
                        self._settings_waiting = True
                    else:
                        self._settings_selected = i
                        self._settings_waiting  = False
                    return None

            # Bouton RÉINITIALISER
            reset_rect = pygame.Rect(SCREEN_W // 2 - 260, SCREEN_H - 68, 244, 44)
            if reset_rect.collidepoint(mx, my):
                KEYBINDS.update(KEYBINDS_DEFAULT)
                self._settings_selected = -1
                self._settings_waiting  = False
                return None

            # Bouton RETOUR
            back_rect = pygame.Rect(SCREEN_W // 2 + 16, SCREEN_H - 68, 244, 44)
            if back_rect.collidepoint(mx, my):
                return "back"

        return None

    def draw_settings_menu(self, surface: pygame.Surface) -> None:
        """Dessine le menu de modification des raccourcis clavier."""
        surface.fill((18, 16, 12))
        pygame.draw.rect(surface, (40, 35, 25), (0, 0, SCREEN_W, 8))
        pygame.draw.rect(surface, (40, 35, 25), (0, SCREEN_H - 8, SCREEN_W, 8))

        _center_text(surface, self._font_sub,
                     "PARAMÈTRES — RACCOURCIS CLAVIER", COL_YELLOW, 28)
        pygame.draw.line(surface, COL_YELLOW,
                         (SCREEN_W // 4, 72), (SCREEN_W * 3 // 4, 72), 2)

        TABLE_X = SCREEN_W // 2 - 270
        KEY_X   = SCREEN_W // 2 + 80
        TABLE_W = 540
        ROW_H   = 32
        START_Y = 82
        mx, my  = pygame.mouse.get_pos()

        # En-têtes colonnes
        hdr_a = self._font_small.render("ACTION", True, (80, 78, 65))
        hdr_k = self._font_small.render("TOUCHE", True, (80, 78, 65))
        surface.blit(hdr_a, (TABLE_X + 8, START_Y))
        surface.blit(hdr_k, (KEY_X + 8,   START_Y))
        START_Y += 18   # START_Y est maintenant 100, cohérent avec handle_settings_event

        for i, (action, label) in enumerate(self._KEYBIND_ROWS):
            row_y    = START_Y + i * ROW_H
            row_rect = pygame.Rect(TABLE_X, row_y, TABLE_W, ROW_H - 2)
            is_sel   = (i == self._settings_selected)
            is_hover = row_rect.collidepoint(mx, my) and not self._settings_waiting

            # Fond de ligne
            if is_sel and self._settings_waiting:
                bg_col = (30, 50, 88, 230)
            elif is_sel:
                bg_col = (60, 54, 35, 215)
            elif i % 2 == 0:
                bg_col = (22, 20, 16, 190)
            else:
                bg_col = (28, 26, 20, 190)
            if is_hover and not is_sel:
                bg_col = (42, 40, 30, 190)

            bg = pygame.Surface((TABLE_W, ROW_H - 2), pygame.SRCALPHA)
            bg.fill(bg_col)
            surface.blit(bg, (TABLE_X, row_y))
            border = COL_YELLOW if is_sel else (COL_GREY if is_hover else None)
            if border:
                pygame.draw.rect(surface, border, row_rect, 1, border_radius=3)

            # Libellé action
            l_col  = COL_WHITE if is_sel else COL_GREY
            l_surf = self._font_small.render(label, True, l_col)
            cy = row_y + (ROW_H - 2 - l_surf.get_height()) // 2
            surface.blit(l_surf, (TABLE_X + 8, cy))

            # Touche
            if is_sel and self._settings_waiting:
                key_str = "..." if self._blink_state else "   "
                key_col = (100, 180, 255)
            else:
                key_str = pygame.key.name(KEYBINDS.get(action, 0)).upper()
                key_col = COL_YELLOW if is_sel else (160, 150, 110)
            k_surf = self._font_small.render(key_str, True, key_col)
            surface.blit(k_surf,
                         (KEY_X + 8,
                          row_y + (ROW_H - 2 - k_surf.get_height()) // 2))

        # Aide contextuelle
        hint_y = START_Y + len(self._KEYBIND_ROWS) * ROW_H + 8
        if self._settings_waiting:
            hint = "Appuyez sur une touche pour l'assigner   ( ÉCHAP = annuler )"
            hint_col = (100, 180, 255)
        elif self._settings_selected >= 0:
            hint = "Cliquez à nouveau sur la ligne pour rebind   ( ÉCHAP = retour )"
            hint_col = COL_GREY
        else:
            hint = "Cliquez sur une ligne, puis recliquez pour changer la touche   ( ÉCHAP = retour )"
            hint_col = (80, 78, 65)
        hs = self._font_small.render(hint, True, hint_col)
        surface.blit(hs, (SCREEN_W // 2 - hs.get_width() // 2, hint_y))

        # Boutons bas
        for rect, lbl, col in [
            (pygame.Rect(SCREEN_W // 2 - 260, SCREEN_H - 68, 244, 44),
             "RÉINITIALISER", (150, 55, 55)),
            (pygame.Rect(SCREEN_W // 2 + 16,  SCREEN_H - 68, 244, 44),
             "RETOUR",        (55, 130, 55)),
        ]:
            is_h = rect.collidepoint(mx, my)
            bg_s = pygame.Surface(rect.size, pygame.SRCALPHA)
            bg_s.fill((*col, 210 if is_h else 150))
            surface.blit(bg_s, rect.topleft)
            pygame.draw.rect(surface, col, rect, 2, border_radius=6)
            ls = self._font_normal.render(lbl, True, COL_WHITE)
            surface.blit(ls, (rect.centerx - ls.get_width() // 2,
                              rect.centery - ls.get_height() // 2))

    # ------------------------------------------------------------------
    def handle_pause_event(self, event: pygame.event.Event) -> None:
        """
        Gère les événements MOUSEBUTTONDOWN pour les boutons du menu pause.
        Stocke le résultat dans _pause_result, consommé par draw_pause().
        """
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            btn_w, btn_h = 260, 48
            bx = SCREEN_W // 2 - btn_w // 2

            by_settings = SCREEN_H // 2 + 30
            if pygame.Rect(bx, by_settings, btn_w, btn_h).collidepoint(mx, my):
                self._pause_result = STATE_SETTINGS
                return

            by_quit = SCREEN_H // 2 + 92
            if pygame.Rect(bx, by_quit, btn_w, btn_h).collidepoint(mx, my):
                self._pause_result = "quit"

    # ------------------------------------------------------------------
    def draw_pause(self, surface: pygame.Surface) -> str | None:
        """
        Superpose une couche de pause.
        Renvoie STATE_SETTINGS, "quit", ou None.
        Les clics sont enregistrés par handle_pause_event() et consommés ici.
        """
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        _center_text(surface, self._font_title, "PAUSE", COL_YELLOW, SCREEN_H // 2 - 110)
        _center_text(surface, self._font_sub,
                     f"[ {pygame.key.name(KEYBINDS['pause']).upper()} ]  Reprendre",
                     COL_WHITE, SCREEN_H // 2 - 20)

        mx, my = pygame.mouse.get_pos()

        # Bouton PARAMÈTRES dans la pause
        btn_w, btn_h = 260, 48
        bx = SCREEN_W // 2 - btn_w // 2

        by_settings = SCREEN_H // 2 + 30
        is_h_settings = pygame.Rect(bx, by_settings, btn_w, btn_h).collidepoint(mx, my)
        bg_settings = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg_settings.fill((60, 88, 135, 210 if is_h_settings else 150))
        surface.blit(bg_settings, (bx, by_settings))
        pygame.draw.rect(surface, (90, 140, 185),
                         (bx, by_settings, btn_w, btn_h), 2, border_radius=6)
        ps = self._font_normal.render("PARAMÈTRES", True, COL_WHITE)
        surface.blit(ps, (bx + btn_w // 2 - ps.get_width() // 2,
                          by_settings + btn_h // 2 - ps.get_height() // 2))

        # Bouton QUITTER dans la pause
        by_quit = SCREEN_H // 2 + 92
        is_h_quit = pygame.Rect(bx, by_quit, btn_w, btn_h).collidepoint(mx, my)
        bg_quit = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg_quit.fill((135, 40, 40, 210 if is_h_quit else 150))
        surface.blit(bg_quit, (bx, by_quit))
        pygame.draw.rect(surface, (185, 70, 70),
                         (bx, by_quit, btn_w, btn_h), 2, border_radius=6)
        qs = self._font_normal.render("QUITTER", True, COL_WHITE)
        surface.blit(qs, (bx + btn_w // 2 - qs.get_width() // 2,
                          by_quit + btn_h // 2 - qs.get_height() // 2))

        # Consommer le résultat stocké par handle_pause_event()
        result = self._pause_result
        self._pause_result = None
        return result

    # ------------------------------------------------------------------
    def handle_gameover_event(self, event: pygame.event.Event) -> None:
        """
        Gère les événements pour le bouton "RETOUR AU MENU" du game over.
        Stocke le résultat dans _gameover_result, consommé par draw_game_over().
        """
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_SPACE, pygame.K_RETURN, pygame.K_KP_ENTER):
                self._gameover_result = STATE_MENU
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            btn_w, btn_h = 300, 52
            btn_x = SCREEN_W // 2 - btn_w // 2
            btn_y = SCREEN_H - 140
            btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
            if btn_rect.collidepoint(event.pos):
                self._gameover_result = STATE_MENU

    # ------------------------------------------------------------------
    def draw_game_over(self, surface: pygame.Surface,
                       final_score: int, wave_reached: int,
                       all_scores=None) -> str | None:
        """
        Ecran game over.
        - Si all_scores est une liste de dicts {"player_name": ..., "score": ...},
          affiche le classement de tous les joueurs (trié par score décroissant).
        - Sinon affiche seulement final_score comme avant.
        Renvoie STATE_MENU si ESPACE / ENTRÉE pressé ou bouton "RETOUR AU MENU" cliqué.
        """
        surface.fill((10, 5, 5))

        _center_text(surface, self._font_title, "MORT AU COMBAT", COL_RED, 60)
        _center_text(surface, self._font_sub,
                     f"Vague atteinte : {wave_reached}", COL_GREY, 158)

        pygame.draw.line(surface, COL_RED,
                         (SCREEN_W // 4, 200), (SCREEN_W * 3 // 4, 200), 2)

        if all_scores:
            # Affichage classement multi-joueurs
            scores_sorted = sorted(all_scores, key=lambda x: x.get("score", 0), reverse=True)
            _center_text(surface, self._font_sub, "CLASSEMENT", COL_YELLOW, 215)
            y_row = 258
            for i, entry in enumerate(scores_sorted):
                name  = entry.get("player_name", "?")
                score = entry.get("score", 0)
                # Couleur jaune pour le premier (meilleur score)
                row_col = COL_YELLOW if i == 0 else COL_WHITE
                rank_str = f"{i + 1}.  {name}  —  {score:,} pts"
                _center_text(surface, self._font_sub, rank_str, row_col, y_row)
                y_row += 40
        else:
            # Mode solo : affichage score unique
            _center_text(surface, self._font_sub,
                         f"Score final : {final_score:,}", COL_YELLOW, 230)
            y_row = 270

        # Séparateur bas
        sep_y = max(y_row + 10, 350)
        pygame.draw.line(surface, COL_RED,
                         (SCREEN_W // 4, sep_y), (SCREEN_W * 3 // 4, sep_y), 2)

        # Bouton "RETOUR AU MENU" cliquable
        btn_w, btn_h = 300, 52
        btn_x = SCREEN_W // 2 - btn_w // 2
        btn_y = SCREEN_H - 140
        mx, my = pygame.mouse.get_pos()
        btn_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
        is_hover = btn_rect.collidepoint(mx, my)
        btn_col  = (180, 50, 50) if is_hover else (120, 30, 30)
        bg_btn = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg_btn.fill((*btn_col, 220))
        surface.blit(bg_btn, (btn_x, btn_y))
        pygame.draw.rect(surface, (220, 70, 70), btn_rect, 2, border_radius=7)
        btn_lbl = self._font_sub.render("RETOUR AU MENU", True, COL_WHITE)
        surface.blit(btn_lbl, (btn_x + btn_w // 2 - btn_lbl.get_width() // 2,
                               btn_y + btn_h // 2 - btn_lbl.get_height() // 2))

        # Texte clignotant ESPACE
        if self._blink_state:
            _center_text(surface, self._font_normal,
                         "[ ESPACE / ENTRÉE ] pour revenir au menu",
                         COL_GREY, SCREEN_H - 72, shadow=False)

        # Consommer le résultat stocké par handle_gameover_event()
        if self._gameover_result is not None:
            result = self._gameover_result
            self._gameover_result = None
            return result
        return None

    # ------------------------------------------------------------------
    def handle_lobby_event(self, event: pygame.event.Event,
                           is_host: bool = False) -> None:
        """
        Gère les événements du lobby.
        is_host=True : affiche le bouton LANCER (seul l'hôte peut lancer).
        Stocke "start" dans _lobby_start_result si l'hôte clique LANCER.
        """
        if not is_host:
            return
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            btn_w, btn_h = 280, 54
            btn_x = SCREEN_W // 2 - btn_w // 2
            btn_y = SCREEN_H - 120
            if pygame.Rect(btn_x, btn_y, btn_w, btn_h).collidepoint(event.pos):
                self._lobby_start_result = "start"
        if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
            self._lobby_start_result = "start"

    # ------------------------------------------------------------------
    def draw_lobby(self, surface: pygame.Surface,
                   players: list,
                   local_player_id: int,
                   is_host: bool,
                   server_ip: str = "") -> str | None:
        """
        Écran de lobby affiché en attente avant le début de la partie.
        players = [{"player_id": int, "player_name": str, "is_host": bool}, ...]
        Retourne "start" si l'hôte clique LANCER, sinon None.
        """
        surface.fill((12, 10, 18))

        # Titre
        _center_text(surface, self._font_title, "SALLE D'ATTENTE", COL_YELLOW, 40)
        _center_text(surface, self._font_small,
                     f"En attente de joueurs...  ({len(players)}/{NET_MAX_PLAYERS})",
                     COL_GREY, 120)

        # Séparateur haut
        pygame.draw.line(surface, COL_YELLOW,
                         (SCREEN_W // 4, 155), (SCREEN_W * 3 // 4, 155), 2)

        # Liste des joueurs
        card_w, card_h = 480, 58
        card_x = SCREEN_W // 2 - card_w // 2
        card_y = 170

        for entry in players:
            pid      = entry.get("player_id", 0)
            pname    = entry.get("player_name", f"Joueur {pid}")
            phost    = entry.get("is_host", False)
            is_local = (pid == local_player_id)
            color    = PLAYER_COLORS[(pid - 1) % len(PLAYER_COLORS)]

            # Fond de la carte
            bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg.fill((color[0]//6, color[1]//6, color[2]//6, 200))
            surface.blit(bg, (card_x, card_y))
            border_col = color if is_local else (80, 80, 80)
            pygame.draw.rect(surface, border_col,
                             (card_x, card_y, card_w, card_h), 2, border_radius=6)

            # Pastille couleur joueur
            pygame.draw.circle(surface, color,
                               (card_x + 28, card_y + card_h // 2), 12)
            pygame.draw.circle(surface, COL_WHITE,
                               (card_x + 28, card_y + card_h // 2), 12, 2)

            # Nom
            name_col = COL_WHITE if is_local else COL_GREY
            n_surf = self._font_sub.render(pname, True, name_col)
            surface.blit(n_surf, (card_x + 52, card_y + card_h // 2 - n_surf.get_height() // 2))

            # Badge HOST / VOUS
            badge_parts = []
            if phost:
                badge_parts.append(("HÔTE", COL_YELLOW))
            if is_local:
                badge_parts.append(("VOUS", (100, 200, 100)))
            bx = card_x + card_w - 10
            for label, bcol in reversed(badge_parts):
                bs = self._font_small.render(label, True, bcol)
                bx -= bs.get_width() + 6
                surface.blit(bs, (bx, card_y + card_h // 2 - bs.get_height() // 2))

            card_y += card_h + 8

        # Emplacements vides
        for i in range(len(players), NET_MAX_PLAYERS):
            bg = pygame.Surface((card_w, card_h), pygame.SRCALPHA)
            bg.fill((30, 30, 30, 120))
            surface.blit(bg, (card_x, card_y))
            pygame.draw.rect(surface, (50, 50, 50),
                             (card_x, card_y, card_w, card_h), 1,
                             border_radius=6, )
            empty_s = self._font_small.render("— En attente d'un joueur... —",
                                              True, (70, 70, 70))
            surface.blit(empty_s, (card_x + card_w // 2 - empty_s.get_width() // 2,
                                   card_y + card_h // 2 - empty_s.get_height() // 2))
            card_y += card_h + 8

        # IP affichée pour que les autres puissent rejoindre
        if server_ip:
            ip_surf = self._font_normal.render(
                f"IP : {server_ip}  — donnez cette adresse aux autres joueurs",
                True, (100, 180, 100))
            surface.blit(ip_surf, (SCREEN_W // 2 - ip_surf.get_width() // 2,
                                   SCREEN_H - 170))

        # Bouton LANCER (hôte seulement) ou message d'attente (clients)
        if is_host:
            btn_w, btn_h = 280, 54
            btn_x = SCREEN_W // 2 - btn_w // 2
            btn_y = SCREEN_H - 120
            mx, my = pygame.mouse.get_pos()
            is_hov = pygame.Rect(btn_x, btn_y, btn_w, btn_h).collidepoint(mx, my)
            bg_col = (50, 150, 50) if is_hov else (30, 100, 30)
            bg_btn = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
            bg_btn.fill((*bg_col, 230))
            surface.blit(bg_btn, (btn_x, btn_y))
            pygame.draw.rect(surface, (80, 200, 80),
                             (btn_x, btn_y, btn_w, btn_h), 2, border_radius=8)
            lbl = self._font_sub.render("▶  LANCER LA PARTIE", True, COL_WHITE)
            surface.blit(lbl, (btn_x + btn_w // 2 - lbl.get_width() // 2,
                                btn_y + btn_h // 2 - lbl.get_height() // 2))
            hint = self._font_small.render("ou appuyez sur ENTRÉE", True, COL_GREY)
            surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2,
                                btn_y + btn_h + 6))
        else:
            if self._blink_state:
                _center_text(surface, self._font_normal,
                             "En attente que l'hôte lance la partie...",
                             COL_GREY, SCREEN_H - 100, shadow=False)

        # Consommer le résultat
        result = self._lobby_start_result
        self._lobby_start_result = None
        return result
