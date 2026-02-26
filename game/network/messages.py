# messages.py - Protocole de messages WebSocket du jeu WW2 Survival
import json

# ---- Types de messages ----
# Client -> Serveur
MSG_JOIN        = "join"
MSG_INPUT       = "input"
MSG_REVIVE_REQ  = "revive_req"

# Serveur -> Client
MSG_WELCOME        = "welcome"
MSG_GAME_STATE     = "game_state"
MSG_PLAYER_JOINED  = "player_joined"
MSG_PLAYER_LEFT    = "player_left"
MSG_WAVE_START     = "wave_start"
MSG_WAVE_CLEAR     = "wave_clear"
MSG_GAME_OVER      = "game_over"
MSG_PLAYER_DOWN    = "player_down"
MSG_PLAYER_REVIVED = "player_revived"
MSG_PLAYER_DEAD    = "player_dead"
MSG_ERROR          = "error"


# ---- Serialisation ----
def encode(msg_dict: dict) -> str:
    return json.dumps(msg_dict, separators=(",", ":"))


def decode(raw: str) -> dict:
    return json.loads(raw)


# ---- Constructeurs de messages ----
def make_join(player_name: str) -> dict:
    return {"type": MSG_JOIN, "player_name": player_name}


def make_input(player_id: int, tick: int, dx: float, dy: float,
               aim_angle: float, shooting: bool, weapon_idx: int,
               grenade_throw: bool, revive_held: bool) -> dict:
    return {
        "type":         MSG_INPUT,
        "player_id":    player_id,
        "tick":         tick,
        "dx":           dx,
        "dy":           dy,
        "aim_angle":    round(aim_angle, 2),
        "shooting":     shooting,
        "weapon_idx":   weapon_idx,
        "grenade_throw": grenade_throw,
        "revive_held":  revive_held,
    }


def make_game_state(tick: int, players_data: list, enemies_data: list,
                    bullets_data: list, grenades_data: list,
                    pickups_data: list, wave_info: dict) -> dict:
    msg = {
        "type":    MSG_GAME_STATE,
        "tick":    tick,
        "players": players_data,
        "enemies": enemies_data,
        "bullets": bullets_data,
        "grenades": grenades_data,
        "pickups": pickups_data,
    }
    msg.update(wave_info)
    return msg


# ---- Serialisation d'entites ----
def serialize_player(p) -> dict:
    wdata = p.get_weapon_data() if hasattr(p, "get_weapon_data") else {}
    rt = wdata.get("reload_time", 1.5) if wdata else 1.5
    reload_progress = 0.0
    if p.is_reloading and rt > 0:
        reload_progress = round(1.0 - p.reload_timer / rt, 3)

    return {
        "player_id":      p.player_id,
        "player_name":    p.player_name,
        "x":              round(p.pos.x, 1),
        "y":              round(p.pos.y, 1),
        "hp":             p.hp,
        "max_hp":         p.max_hp,
        "facing_angle":   round(p.facing_angle, 1),
        "weapon_idx":     p.active_weapon_idx,
        "ammo":           dict(p.ammo),
        "score":          p.score,
        "is_reloading":   p.is_reloading,
        "reload_progress": reload_progress,
        "state":          p.state,
        "down_timer":     round(p.down_timer, 1),
        "revive_progress": round(p.revive_progress, 2),
    }


def serialize_enemy(e) -> dict:
    return {
        "enemy_id":    e.enemy_id,
        "enemy_type":  e.enemy_type,
        "x":           round(e.pos.x, 1),
        "y":           round(e.pos.y, 1),
        "hp":          e.hp,
        "max_hp":      e.max_hp,
        "facing_angle": round(e.facing_angle, 1),
        "ai_state":    e.ai.state,
    }


def serialize_bullet(b) -> dict:
    return {
        "bullet_id": id(b),
        "x":        round(b.pos.x, 1),
        "y":        round(b.pos.y, 1),
        "vel_x":    round(b.velocity.x, 1),
        "vel_y":    round(b.velocity.y, 1),
        "owner":    b.owner,
    }


def serialize_grenade(g) -> dict:
    return {
        "grenade_id":     id(g),
        "x":              round(g.pos.x, 1),
        "y":              round(g.pos.y, 1),
        "fuse_remaining": round(g.fuse_timer, 2),
    }


def serialize_pickup(pk) -> dict:
    return {
        "pickup_id":   id(pk),
        "weapon_name": pk.weapon_name,
        "x":           round(pk.pos.x, 1),
        "y":           round(pk.pos.y, 1),
    }
