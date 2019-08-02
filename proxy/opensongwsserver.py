import websockets
from typing import Optional, List
from .proxyconfig import ProxyConfig
from .opensongwsclient import OpenSongWsClient
from .opensongwsconnection import OpenSongWsConnection


class OpenSongWsServer:
    def __init__(self, config: ProxyConfig, client: OpenSongWsClient):
        self.config = config
        self._client = client
        self._server: Optional[websockets.serve] = None
        self._connections: List[OpenSongWsConnection] = []

    async def _client_connection(self, websocket: websockets.WebSocketServerProtocol, _path: str):
        self.config.logger.debug("New connection")

        connection = OpenSongWsConnection(websocket, self.config)
        self._connections.append(connection)

        await connection.run(self._client)
        await websocket.close()

        self._connections.remove(connection)

    def run(self):
        self._server = websockets.serve(self._client_connection, self.config.proxy_host, self.config.proxy_port)
        return self._server

    def stop(self):
        for connection in self._connections:
            try:
                connection.stop()
            except:
                pass

        if self._server:
            self._server.ws_server.close()
