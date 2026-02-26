# menus.py - Menu principal, pause, game over, menu réseau
import pygame
from settings import (
    SCREEN_W, SCREEN_H, STATE_PLAYING, STATE_MENU, STATE_GAMEOVER,
    COL_BLACK, COL_WHITE, COL_YELLOW, COL_RED, COL_GREY, COL_DARK_GREEN,
    KEYBINDS, KEYBINDS_DEFAULT, STATE_SETTINGS,
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

        # ESPACE → jouer immédiatement (compatibilité ancienne)
        keys = pygame.key.get_pressed()
        if keys[pygame.K_SPACE]:
            result = STATE_PLAYING
        return result

    # ------------------------------------------------------------------
    # Menu paramètres (rebind)
    # ------------------------------------------------------------------
    def handle_settings_event(self, event: pygame.event.Event) -> str | None:
        """
        Gère les événements du menu paramètres.
        Retourne "back" quand l'utilisateur veut revenir au menu principal.
        """
        ROW_H   = 38
        START_Y = 115
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
        ROW_H   = 38
        START_Y = 82
        mx, my  = pygame.mouse.get_pos()

        # En-têtes colonnes
        hdr_a = self._font_small.render("ACTION", True, (80, 78, 65))
        hdr_k = self._font_small.render("TOUCHE", True, (80, 78, 65))
        surface.blit(hdr_a, (TABLE_X + 8, START_Y))
        surface.blit(hdr_k, (KEY_X + 8,   START_Y))
        START_Y += 18

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
            surface.blit(l_surf,
                         (TABLE_X + 8,
                          row_y + (ROW_H - 2 - l_surf.get_height()) // 2))

            # Touche
            if is_sel and self._settings_waiting:
                key_str = "..." if self._blink_state else "   "
                key_col = (100, 180, 255)
            else:
                key_str = pygame.key.name(KEYBINDS.get(action, 0)).upper()
                key_col = COL_YELLOW if is_sel else (160, 150, 110)
            k_surf = self._font_normal.render(key_str, True, key_col)
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
    def draw_pause(self, surface: pygame.Surface) -> str | None:
        """Superpose une couche de pause. Renvoie STATE_PLAYING ou STATE_SETTINGS."""
        overlay = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 140))
        surface.blit(overlay, (0, 0))

        _center_text(surface, self._font_title, "PAUSE", COL_YELLOW, SCREEN_H // 2 - 100)
        _center_text(surface, self._font_sub,
                     f"[ {pygame.key.name(KEYBINDS['pause']).upper()} ]  Reprendre",
                     COL_WHITE, SCREEN_H // 2 - 10)

        # Bouton PARAMÈTRES dans la pause
        btn_w, btn_h = 260, 48
        bx = SCREEN_W // 2 - btn_w // 2
        by = SCREEN_H // 2 + 48
        mx, my = pygame.mouse.get_pos()
        is_h = pygame.Rect(bx, by, btn_w, btn_h).collidepoint(mx, my)
        bg = pygame.Surface((btn_w, btn_h), pygame.SRCALPHA)
        bg.fill((60, 88, 135, 210 if is_h else 150))
        surface.blit(bg, (bx, by))
        pygame.draw.rect(surface, (90, 140, 185),
                         (bx, by, btn_w, btn_h), 2, border_radius=6)
        ps = self._font_normal.render("PARAMÈTRES", True, COL_WHITE)
        surface.blit(ps, (bx + btn_w // 2 - ps.get_width() // 2,
                          by + btn_h // 2 - ps.get_height() // 2))
        if is_h and pygame.mouse.get_pressed()[0]:
            return STATE_SETTINGS

        _center_text(surface, self._font_small, "Quitter : Alt+F4",
                     COL_GREY, SCREEN_H // 2 + 112)
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
