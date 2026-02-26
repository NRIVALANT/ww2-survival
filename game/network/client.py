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
    Communique avec le thread pygame via :
      - _async_send_queue : asyncio.Queue (zéro latence côté envoi)
      - receive_queue     : queue.Queue thread-safe (lecture pygame)

    Le thread pygame appelle send_input() et get_messages() librement.
    L'envoi est event-driven : dès qu'un message est mis dans _async_send_queue
    il part immédiatement sans polling ni sleep.
    """

    def __init__(self, server_ip: str, player_name: str):
        self.server_ip   = server_ip
        self.player_name = player_name
        self.player_id   = None

        # Queue de réception (thread pygame lit ici)
        self.receive_queue: queue.Queue = queue.Queue()

        # asyncio.Queue créée dans le thread asyncio (évite les race conditions)
        self._async_send_queue: asyncio.Queue | None = None

        self._running   = False
        self._connected = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._thread: threading.Thread | None = None

    # ------------------------------------------------------------------
    async def _send_loop(self, ws):
        """Envoi event-driven : attend un item dans la queue asyncio, l'envoie immédiatement."""
        while self._running:
            try:
                msg = await asyncio.wait_for(self._async_send_queue.get(), timeout=0.5)
                await ws.send(encode(msg))
            except asyncio.TimeoutError:
                continue   # juste pour vérifier _running régulièrement
            except Exception:
                break

    async def _recv_loop(self, ws):
        async for raw in ws:
            msg = decode(raw)
            self.receive_queue.put(msg)
        # La boucle s'est terminée = serveur a fermé la connexion
        if self._running:
            self.receive_queue.put({"type": "error", "reason": "disconnected_by_server"})
            self._running = False

    async def _connect_and_run(self):
        # Créer la asyncio.Queue dans le bon loop
        self._async_send_queue = asyncio.Queue()

        uri = f"ws://{self.server_ip}:{NET_PORT}"
        try:
            async with ws_connect(uri) as ws:
                # Envoyer MSG_JOIN
                await ws.send(encode({
                    "type": MSG_JOIN,
                    "player_name": self.player_name,
                }))

                # Attendre MSG_WELCOME (ou MSG_ERROR si serveur plein)
                raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
                welcome = decode(raw)
                if welcome.get("type") == MSG_WELCOME:
                    self.player_id = welcome["player_id"]
                    self.receive_queue.put(welcome)
                    self._connected.set()
                    # Lancer send + recv en parallèle seulement si accepté
                    self._running = True
                    await asyncio.gather(
                        self._send_loop(ws),
                        self._recv_loop(ws),
                    )
                else:
                    # Refus du serveur (server_full, etc.) → convertir en erreur lisible
                    reason = welcome.get("reason", "refused_by_server")
                    self.receive_queue.put({"type": "error", "reason": reason})
                    self._connected.set()
        except Exception as e:
            self.receive_queue.put({"type": "error", "reason": str(e)})
            self._connected.set()   # débloquer wait_connected même en cas d'erreur

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
        """Appelé depuis le thread pygame — pousse l'input dans la asyncio.Queue sans délai."""
        if self._loop and self._async_send_queue is not None:
            # call_soon_threadsafe est thread-safe et réveille immédiatement le loop asyncio
            self._loop.call_soon_threadsafe(self._async_send_queue.put_nowait, input_dict)

    def get_messages(self) -> list[dict]:
        msgs = []
        while not self.receive_queue.empty():
            try:
                msgs.append(self.receive_queue.get_nowait())
            except queue.Empty:
                break
        return msgs
