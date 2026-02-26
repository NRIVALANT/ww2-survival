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

from game.network.messages import (
    MSG_JOIN, MSG_WELCOME, MSG_ERROR, encode, decode
)
from settings import NET_PORT, NET_MAX_PLAYERS


class GameServer:
    """
    Serveur WebSocket tourne dans un thread asyncio daemon.
    Communique avec le thread pygame via deux queues thread-safe.

    input_queue   : recoit les messages/inputs des clients
    broadcast_queue: recoit les game_state JSON a envoyer a tous les clients
    """

    def __init__(self):
        self.clients: dict[int, object] = {}   # player_id -> websocket
        self.player_names: dict[int, str] = {}
        self.next_player_id = 2   # host = 1

        self.input_queue:     queue.Queue = queue.Queue()
        self.broadcast_queue: queue.Queue = queue.Queue()

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

            # Boucle de reception des inputs
            async for raw_msg in websocket:
                msg = decode(raw_msg)
                self.input_queue.put({
                    "player_id": player_id,
                    "input":     msg,
                })

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
        """Depile broadcast_queue et envoie a tous les clients."""
        while self._running:
            try:
                msg_str = self.broadcast_queue.get_nowait()
                if self.clients:
                    tasks = [
                        asyncio.create_task(ws.send(msg_str))
                        for ws in list(self.clients.values())
                    ]
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
            except queue.Empty:
                await asyncio.sleep(0.001)

    async def _run(self):
        self._running = True
        broadcast_task = asyncio.create_task(self._broadcast_loop())
        async with ws_serve(self._handler, "0.0.0.0", NET_PORT) as server:
            # Tourner indefiniment
            await asyncio.get_running_loop().create_future()
        broadcast_task.cancel()

    def start_in_thread(self):
        def _thread_func():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            try:
                self._loop.run_until_complete(self._run())
            except Exception:
                pass

        self._thread = threading.Thread(target=_thread_func, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------
    def broadcast(self, msg_str: str):
        """Appele depuis le thread pygame pour broadcaster un etat."""
        self.broadcast_queue.put(msg_str)

    def get_pending_inputs(self) -> list[dict]:
        """Appele depuis le thread pygame pour recuperer les inputs clients."""
        inputs = []
        while not self.input_queue.empty():
            try:
                inputs.append(self.input_queue.get_nowait())
            except queue.Empty:
                break
        return inputs
