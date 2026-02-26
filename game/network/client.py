# client.py - Client WebSocket leger
import asyncio
import threading
import queue
try:
    import websockets
    from websockets.asyncio.client import connect as ws_connect
except ImportError:
    websockets = None

from game.network.messages import MSG_JOIN, MSG_WELCOME, encode, decode
from settings import NET_PORT


class GameClient:
    """
    Client WebSocket tourne dans un thread asyncio daemon.
    Communique avec le thread pygame via deux queues thread-safe.

    send_queue    : le thread pygame pousse les inputs a envoyer
    receive_queue : le thread pygame lit les game_states recus
    """

    def __init__(self, server_ip: str, player_name: str):
        self.server_ip   = server_ip
        self.player_name = player_name
        self.player_id   = None

        self.send_queue:    queue.Queue = queue.Queue()
        self.receive_queue: queue.Queue = queue.Queue()

        self._running   = False
        self._connected = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    async def _send_loop(self, ws):
        while self._running:
            try:
                msg = self.send_queue.get_nowait()
                await ws.send(encode(msg))
            except queue.Empty:
                await asyncio.sleep(0.001)

    async def _recv_loop(self, ws):
        async for raw in ws:
            msg = decode(raw)
            self.receive_queue.put(msg)

    async def _connect_and_run(self):
        uri = f"ws://{self.server_ip}:{NET_PORT}"
        try:
            async with ws_connect(uri) as ws:
                # Envoyer MSG_JOIN
                await ws.send(encode({
                    "type": MSG_JOIN,
                    "player_name": self.player_name,
                }))

                # Attendre MSG_WELCOME
                raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome = decode(raw)
                if welcome.get("type") == MSG_WELCOME:
                    self.player_id = welcome["player_id"]
                self.receive_queue.put(welcome)
                self._connected.set()

                # Lancer send + recv en parallele
                self._running = True
                await asyncio.gather(
                    self._send_loop(ws),
                    self._recv_loop(ws),
                )
        except Exception as e:
            self.receive_queue.put({"type": "error", "reason": str(e)})
            self._connected.set()   # debloquer wait_connected meme en cas d'erreur

    def start_in_thread(self):
        def _thread_func():
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            self._loop.run_until_complete(self._connect_and_run())

        self._thread = threading.Thread(target=_thread_func, daemon=True)
        self._thread.start()

    def wait_connected(self, timeout: float = 10.0) -> bool:
        """Bloque jusqu'a connexion etablie ou timeout. Renvoie True si OK."""
        return self._connected.wait(timeout=timeout)

    def stop(self):
        self._running = False
        if self._loop and not self._loop.is_closed():
            self._loop.call_soon_threadsafe(self._loop.stop)

    # ------------------------------------------------------------------
    def send_input(self, input_dict: dict):
        self.send_queue.put(input_dict)

    def get_messages(self) -> list[dict]:
        msgs = []
        while not self.receive_queue.empty():
            try:
                msgs.append(self.receive_queue.get_nowait())
            except queue.Empty:
                break
        return msgs
