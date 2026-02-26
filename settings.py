# settings.py - Toutes les constantes du jeu WW2 Survival

# --- Fenetre ---
SCREEN_W = 1280
SCREEN_H = 720
FPS = 60
TITLE = "WW2 Survival - 1944"

# --- Tuiles ---
TILE_SIZE = 48
MAP_COLS = 40
MAP_ROWS = 30
MAP_W = MAP_COLS * TILE_SIZE   # 1920
MAP_H = MAP_ROWS * TILE_SIZE   # 1440

# Types de tuiles
TILE_GROUND  = 0
TILE_WALL    = 1
TILE_SANDBAG = 2
TILE_BUNKER  = 3
TILE_DIRT    = 4   # sol variante

SOLID_TILES = {TILE_WALL, TILE_SANDBAG, TILE_BUNKER}

# --- Joueur ---
PLAYER_SPEED   = 220   # px/s
PLAYER_HP      = 100
PLAYER_RADIUS  = 14
PLAYER_IFRAMES = 0.4   # secondes d'invincibilite apres coup

# --- Armes ---
WEAPONS = {
    "pistol": {
        "damage": 25, "fire_rate": 0.5, "bullet_speed": 520,
        "max_ammo": 12, "reload_time": 1.2, "spread": 2,
        "auto": False, "bullet_range": 500,
    },
    "rifle": {
        "damage": 60, "fire_rate": 1.3, "bullet_speed": 950,
        "max_ammo": 5,  "reload_time": 2.5, "spread": 1,
        "auto": False, "bullet_range": 900,
    },
    "smg": {
        "damage": 18, "fire_rate": 0.12, "bullet_speed": 560,
        "max_ammo": 30, "reload_time": 2.0, "spread": 6,
        "auto": True,  "bullet_range": 400,
    },
    "grenade": {
        "damage": 90, "fire_rate": 1.8, "blast_radius": 110,
        "max_ammo": 3, "fuse_time": 2.5, "throw_speed": 380,
    },
}

# Ordre d'affichage dans l'inventaire
WEAPON_ORDER = ["pistol", "rifle", "smg", "grenade"]

# --- Ennemis ---
ENEMY_TYPES = {
    "soldier": {
        "hp": 60,  "speed": 130, "damage": 15, "fire_rate": 1.0,
        "detect_range": 360, "shoot_range": 280, "score": 100,
        "color": (180, 50, 50),
    },
    "officer": {
        "hp": 80,  "speed": 155, "damage": 20, "fire_rate": 0.75,
        "detect_range": 420, "shoot_range": 320, "score": 200,
        "color": (200, 80, 30),
    },
    "heavy": {
        "hp": 160, "speed": 75,  "damage": 30, "fire_rate": 1.6,
        "detect_range": 300, "shoot_range": 220, "score": 300,
        "color": (140, 30, 100),
    },
}

ENEMY_BULLET_SPEED  = 480
ENEMY_BULLET_RANGE  = 400
ENEMY_SPREAD        = 5    # degres

# --- IA ---
CHASE_RANGE         = 550
COVER_RANGE         = 240
PATROL_SPEED_MOD    = 0.5
LOS_STEP            = 0.4  # fraction de TILE_SIZE pour le raycasting
SUPPRESSION_DIST    = 80   # px - balle proche = suppression
PATH_RECALC_TIME    = 0.6  # secondes entre recalculs A*
MAX_ASTAR_NODES     = 250

# --- Vagues ---
WAVE_COOLDOWN    = 8.0
BASE_ENEMIES     = 5
WAVE_SCALE       = 1.4
SPAWN_INTERVAL   = 0.7   # secondes entre chaque apparition d'ennemi

# --- Physique grenade ---
GRENADE_FRICTION    = 0.82   # par seconde
GRENADE_BOUNCE_DAMP = 0.45

# --- Couleurs (fallback sans sprites) ---
COL_GROUND_A  = (95,  85,  65)
COL_GROUND_B  = (88,  79,  58)   # variation de sol
COL_WALL      = (70,  65,  52)
COL_SANDBAG   = (180, 155, 90)
COL_BUNKER    = (90,  85,  70)
COL_PLAYER    = (55,  135, 55)
COL_HELMET_P  = (40,  100, 40)
COL_BULLET_P  = (255, 230, 60)
COL_BULLET_E  = (255, 80,  80)
COL_GRENADE   = (60,  60,  60)
COL_EXPLOSION = (255, 160, 30)
COL_PICKUP    = (220, 200, 80)
COL_HUD_BG    = (15,  15,  15)
COL_HP_BAR    = (60,  200, 60)
COL_HP_LOW    = (220, 50,  50)
COL_WAVE_CLEAR= (60,  220, 120)
COL_WHITE     = (255, 255, 255)
COL_BLACK     = (0,   0,   0)
COL_GREY      = (160, 160, 160)
COL_DARK_GREY = (60,  60,  60)
COL_RED       = (220, 50,  50)
COL_YELLOW    = (240, 210, 50)
COL_DARK_GREEN= (30,  80,  30)

# --- Couches de rendu ---
LAYER_GROUND   = 0
LAYER_PICKUPS  = 1
LAYER_ENTITIES = 2
LAYER_BULLETS  = 3
LAYER_FX       = 4
LAYER_HUD      = 5

# --- Etats du jeu ---
STATE_MENU     = "menu"
STATE_PLAYING  = "playing"
STATE_PAUSED   = "paused"
STATE_GAMEOVER = "gameover"
STATE_WAVE_CLEAR = "wave_clear"

# --- Reseau ---
NET_PORT           = 8765
NET_MAX_PLAYERS    = 4
NET_BROADCAST_RATE = 20      # snapshots/s envoyes aux clients
NET_TIMEOUT        = 10.0    # secondes avant kick client silencieux

# --- Revive (coop) ---
REVIVE_TIME    = 3.0    # secondes pour relever (touche E maintenue)
REVIVE_RANGE   = 70     # px de portee pour relever
DOWN_TIMEOUT   = 30.0   # secondes avant mort definitive si non releve

# --- Couleurs joueurs multi ---
PLAYER_COLORS = [
    (55,  135,  55),   # Joueur 1 - vert
    (55,  100, 180),   # Joueur 2 - bleu
    (200, 170,  40),   # Joueur 3 - jaune
    (180,  60, 180),   # Joueur 4 - violet
]

# --- Score ---
POINTS_HIT     = 10    # points par balle qui touche
COL_POINTS_POPUP = (255, 230, 60)

# --- Systeme de points (style CoD Zombies) ---
POINTS_HIT              = 10    # points gagnés par balle qui touche un ennemi
POINTS_KILL_BASE        = 100   # points bonus pour tuer un ennemi (base)
UPGRADE_MACHINE_COST    = 5000  # coût pour améliorer une arme
UPGRADE_MACHINE_MAX_LVL = 3     # nombre max d'améliorations par arme
UPGRADE_MACHINE_TILE    = (19, 17)  # position tuile de la machine (col, row)

COL_UPGRADE_MACHINE  = (80, 180, 255)   # couleur de la machine
COL_POINTS_POPUP     = (255, 220, 60)   # couleur des popups "+pts"

# --- Raccourcis clavier (modifiables en jeu) ---
import pygame as _pg
KEYBINDS: dict = {
    "move_up":    _pg.K_w,
    "move_down":  _pg.K_s,
    "move_left":  _pg.K_a,
    "move_right": _pg.K_d,
    "reload":     _pg.K_r,
    "weapon_prev": _pg.K_q,
    "revive":     _pg.K_e,
    "upgrade":    _pg.K_f,
    "pause":      _pg.K_ESCAPE,
    "slot_1":     _pg.K_1,
    "slot_2":     _pg.K_2,
    "slot_3":     _pg.K_3,
    "slot_4":     _pg.K_4,
}
KEYBINDS_DEFAULT: dict = dict(KEYBINDS)  # copie pour reset

# --- Etats supplementaires ---
STATE_SETTINGS     = "settings"
STATE_NETWORK_MENU = "network_menu"
