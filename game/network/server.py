# server.py - Serveur WebSocket autoritaire
import asyncio
import threading
import queue
import json
try:
    import websockets
    from websockets.asyncio.server import serve as ws_serve
except ImportError:
    websockets = None

import time

from game.network.messages import (
    MSG_JOIN, MSG_WELCOME, MSG_ERROR, encode, decode
)
from settings import NET_PORT, NET_MAX_PLAYERS, NET_TIMEOUT


class GameServer:
    """
    Serveur WebSocket tourne dans un thread asyncio daemon.
    Communique avec le thread pygame via :
      - input_queue        : queue.Queue thread-safe (pygame lit les inputs reçus)
      - _async_bcast_queue : asyncio.Queue (broadcast event-driven, zéro latence)

    Le thread pygame appelle broadcast() et get_pending_inputs() librement.
    """

    def __init__(self):
        self.clients: dict[int, object] = {}   # player_id -> websocket
        self.player_names: dict[int, str] = {}
        self.next_player_id = 2   # host = 1

        # Queue de réception (thread pygame lit ici)
        self.input_queue: queue.Queue = queue.Queue()

        # asyncio.Queue pour le broadcast (créée dans le thread asyncio)
        self._async_bcast_queue: asyncio.Queue | None = None
        # Event signalant que la queue asyncio est prête (évite race condition)
        self._queue_ready = threading.Event()

        self._running = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    async def _handler(self, websocket):
        player_id = None
        try:
            # Attendre MSG_JOIN
            raw = await asyncio.wait_for(websocket.recv(), timeout=8.0)
            msg = decode(raw)

            if msg.get("type") != MSG_JOIN:
                await websocket.send(encode({
                    "type": MSG_ERROR, "reason": "expected_join"
                }))
                return

            if len(self.clients) >= NET_MAX_PLAYERS - 1:
                await websocket.send(encode({
                    "type": MSG_ERROR, "reason": "server_full"
                }))
                return

            player_id = self.next_player_id
            self.next_player_id += 1
            self.clients[player_id]      = websocket
            self.player_names[player_id] = msg.get("player_name",
                                                    f"Joueur{player_id}")

            # Envoyer MSG_WELCOME
            welcome = {
                "type":       MSG_WELCOME,
                "player_id":  player_id,
                "all_players": [
                    {"player_id": pid, "name": name}
                    for pid, name in self.player_names.items()
                ],
            }
            await websocket.send(encode(welcome))

            # Notifier le thread pygame
            self.input_queue.put({
                "type":        "player_joined",
                "player_id":   player_id,
                "player_name": self.player_names[player_id],
            })

            # Boucle de réception des inputs avec timeout d'inactivité
            last_recv = time.monotonic()
            while True:
                try:
                    remaining = NET_TIMEOUT - (time.monotonic() - last_recv)
                    if remaining <= 0:
                        # Client silencieux depuis trop longtemps → déconnexion
                        await websocket.close()
                        break
                    raw_msg = await asyncio.wait_for(websocket.recv(), timeout=remaining)
                    last_recv = time.monotonic()
                    msg = decode(raw_msg)
                    if msg.get("type") == "ping":
                        continue   # renouveler last_recv, ne pas mettre dans la queue
                    self.input_queue.put({
                        "player_id": player_id,
                        "input":     msg,
                    })
                except asyncio.TimeoutError:
                    # Timeout atteint sans message → kick
                    await websocket.close()
                    break
                except Exception:
                    break

        except (Exception,):
            pass
        finally:
            if player_id and player_id in self.clients:
                del self.clients[player_id]
                if player_id in self.player_names:
                    del self.player_names[player_id]
                self.input_queue.put({
                    "type":      "player_left",
                    "player_id": player_id,
                })

    async def _broadcast_loop(self):
        """Broadcast event-driven : attend un message dans la asyncio.Queue, l'envoie immédiatement."""
        while self._running:
            try:
                msg_str = await asyncio.wait_for(self._async_bcast_queue.get(), timeout=0.5)
                if self.clients:
                    tasks = [
                        asyncio.create_task(ws.send(msg_str))
                        for ws in list(self.clients.values())
                    ]
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
            except asyncio.TimeoutError:
                continue   # vérifier _running
            except Exception:
                continue

    async def _run(self):
        # Créer la asyncio.Queue dans le bon loop, puis signaler qu'elle est prête
        self._async_bcast_queue = asyncio.Queue()
        self._queue_ready.set()
        self._running = True
        broadcast_task = asyncio.create_task(self._broadcast_loop())
        async with ws_serve(self._handler, "0.0.0.0", NET_PORT) as server:
            # Tourner indéfiniment
            await asyncio.get_running_loop().create_future()
        broadcast_task.cancel()

    def start_in_thread(self, wait_ready: bool = True):
        """Démarre le serveur dans un thread daemon.
        Si wait_ready=True, attend que la asyncio.Queue soit initialisée (max 3s).
        """
        def _thread_func():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._run())
            except Exception:
                pass

        self._thread = threading.Thread(target=_thread_func, daemon=True)
        self._thread.start()
        if wait_ready:
            self._queue_ready.wait(timeout=3.0)

    def stop(self):
        self._running = False
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------
    def broadcast(self, msg_str: str):
        """Appelé depuis le thread pygame — broadcast event-driven sans polling."""
        if self._loop and self._loop.is_running() and self._async_bcast_queue is not None:
            self._loop.call_soon_threadsafe(self._async_bcast_queue.put_nowait, msg_str)

    def get_pending_inputs(self) -> list[dict]:
        """Appelé depuis le thread pygame pour récupérer les inputs clients."""
        inputs = []
        while not self.input_queue.empty():
            try:
                inputs.append(self.input_queue.get_nowait())
            except queue.Empty:
                break
        return inputs
