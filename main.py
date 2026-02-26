# main.py - Point d'entree du jeu WW2 Survival
import pygame
import sys

from settings import (
    SCREEN_W, SCREEN_H, FPS, TITLE,
    STATE_MENU, STATE_PLAYING, STATE_PAUSED, STATE_GAMEOVER,
    TILE_SIZE, UPGRADE_MACHINE_TILE,
)
from game.world.tilemap   import TileMap
from game.world.camera    import Camera
from game.world.map_data  import MAP_DATA, PLAYER_START
from game.entities.player import Player
from game.systems.pathfinding import Pathfinder
from game.systems.wave_manager import WaveManager
from game.ui.hud   import HUD
from game.ui.menus import Menus
from game.entities.upgrade_machine import UpgradeMachine


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        self.clock  = pygame.time.Clock()
        pygame.mouse.set_visible(False)   # curseur personnalise

        self.state      = STATE_MENU
        self.hud        = HUD()
        self.menus      = Menus()
        self._last_gameover_wave  = 0
        self._last_gameover_score = 0

        self._init_game()

    # ------------------------------------------------------------------
    def _init_game(self):
        """Initialise / recharge une nouvelle partie."""
        self.tilemap    = TileMap(MAP_DATA)
        self.camera     = Camera()
        self.pathfinder = Pathfinder(self.tilemap)

        # Groupes de sprites
        self.all_sprites    = pygame.sprite.Group()
        self.enemy_group    = pygame.sprite.Group()
        self.bullet_group   = pygame.sprite.Group()
        self.grenade_group  = pygame.sprite.Group()
        self.explosion_group= pygame.sprite.Group()
        self.pickup_group   = pygame.sprite.Group()

        px, py = PLAYER_START
        self.player = Player(px, py)

        # Machine d'amélioration (style CoD Zombies)
        col, row = UPGRADE_MACHINE_TILE
        self.upgrade_machine = UpgradeMachine(col, row)

        self.wave_manager = WaveManager(
            tilemap        = self.tilemap,
            pathfinder     = self.pathfinder,
            player         = self.player,
            enemy_group    = self.enemy_group,
            pickup_group   = self.pickup_group,
            all_groups     = (self.all_sprites,),
        )

    # ------------------------------------------------------------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            dt = min(dt, 0.05)   # cap a 50ms (protection freeze)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self._handle_event(event)

            self._update(dt)
            self._draw()
            pygame.display.flip()

    # ------------------------------------------------------------------
    def _handle_event(self, event):
        if self.state == STATE_PLAYING:
            self.player.handle_event(event)
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = STATE_PAUSED
            # Interaction avec la machine d'amelioration
            if event.type == pygame.KEYDOWN and event.key == pygame.K_f:
                if self.upgrade_machine.player_in_range(self.player):
                    self.upgrade_machine.try_upgrade(self.player)

        elif self.state == STATE_PAUSED:
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.state = STATE_PLAYING

    # ------------------------------------------------------------------
    def _update(self, dt: float):
        self.menus.update(dt)

        if self.state == STATE_MENU:
            pass

        elif self.state == STATE_PLAYING:
            keys   = pygame.key.get_pressed()
            mbtns  = pygame.mouse.get_pressed()
            mpos   = pygame.mouse.get_pos()

            self.player.handle_input(
                keys, mbtns, mpos,
                self.camera, self.tilemap, dt,
                self.bullet_group,
                self.grenade_group,
                self.explosion_group,
                self.enemy_group,
            )

            if not self.player.alive:
                self._last_gameover_wave  = self.wave_manager.wave_number
                self._last_gameover_score = self.player.score
                self.state = STATE_GAMEOVER
                return

            # Ennemis
            dead_enemies = []
            for enemy in list(self.enemy_group):
                enemy.update(dt, self.tilemap, self.player,
                             self.bullet_group, self.explosion_group)
                if not enemy.alive:
                    kill_pts = enemy.score_value
                    self.player.add_score(kill_pts)
                    self.player.add_score_popup(f"+{kill_pts}", enemy.pos)
                    dead_enemies.append(enemy)

            # Balles
            for bullet in list(self.bullet_group):
                bullet.update(dt, self.tilemap, self.enemy_group, self.player)

            # Grenades
            for grenade in list(self.grenade_group):
                grenade.update(dt, self.tilemap, self.enemy_group, self.player)

            # Explosions
            for expl in list(self.explosion_group):
                expl.update(dt, self.enemy_group, self.player)

            # Ramassages
            for pickup in list(self.pickup_group):
                pickup.update(dt)
                if self.player.rect.colliderect(pickup.rect):
                    self.player.pick_up(pickup)

            # Vagues
            self.wave_manager.update(dt)

            # Nettoyage ennemis morts
            for e in dead_enemies:
                if e in self.enemy_group:
                    self.enemy_group.remove(e)
                if e in self.all_sprites:
                    self.all_sprites.remove(e)

            # Machine d'amelioration
            self.upgrade_machine.update(dt)

            # Popups de score
            self.player.update_popups(dt)

            # Camera
            self.camera.update(self.player.rect)

        elif self.state == STATE_GAMEOVER:
            pass

    # ------------------------------------------------------------------
    def _draw(self):
        if self.state == STATE_MENU:
            result = self.menus.draw_main_menu(self.screen)
            if result == STATE_PLAYING:
                self._init_game()
                self.state = STATE_PLAYING
            return

        if self.state == STATE_GAMEOVER:
            result = self.menus.draw_game_over(
                self.screen,
                self._last_gameover_score,
                self._last_gameover_wave,
            )
            if result == STATE_MENU:
                self.state = STATE_MENU
            return

        # Fond
        self.screen.fill((80, 72, 55))

        # Carte
        self.tilemap.draw(self.screen, self.camera.offset)

        # Ramassages
        font_small = pygame.font.SysFont("Arial", 12)
        for pickup in self.pickup_group:
            pickup.draw(self.screen, self.camera, font_small)

        # Machine d'amelioration
        self.upgrade_machine.draw(self.screen, self.camera, self.player)

        # Joueur
        self.player.draw(self.screen, self.camera)

        # Ennemis
        for enemy in self.enemy_group:
            enemy.draw(self.screen, self.camera)

        # Grenades
        for grenade in self.grenade_group:
            grenade.draw(self.screen, self.camera)

        # Explosions
        for expl in self.explosion_group:
            expl.draw(self.screen, self.camera)

        # Balles (par dessus tout)
        for bullet in self.bullet_group:
            bullet.draw(self.screen, self.camera)

        # HUD
        self.hud.draw(self.screen, self.player, self.wave_manager)

        # Popups de points flottants
        self.hud.draw_score_popups(self.screen, self.player, self.camera)

        # Prompt machine d'amelioration
        if self.upgrade_machine.player_in_range(self.player):
            self.upgrade_machine.draw_hud_prompt(
                self.screen, SCREEN_W, SCREEN_H, self.player)
        self.upgrade_machine.draw_result_message(self.screen, SCREEN_W, SCREEN_H)

        # Pause par dessus
        if self.state == STATE_PAUSED:
            self.menus.draw_pause(self.screen)


# ------------------------------------------------------------------
if __name__ == "__main__":
    game = Game()
    game.run()
