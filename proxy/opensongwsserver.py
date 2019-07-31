import websockets
from websockets.exceptions import ConnectionClosed
from functools import partial
from .proxyconfig import ProxyConfig
from .opensongwsclient import OpenSongWsClient


class OpenSongWsServer:
    def __init__(self, config: ProxyConfig, client: OpenSongWsClient):
        self.config = config
        self._shutdown = False
        self._server = None
        self._client = client

    async def _client_on_response_callback(self, websocket: websockets.WebSocketServerProtocol, response: str):
        self.config.logger.info("Callback response: %s" % response)
        print("Callback response: %s" % response)

        # todo: only send the data to the client in case of a pending reponse
        #       or when a subscription is active

        await websocket.send(response)

    async def _client_on_image_callback(self, websocket: websockets.WebSocketServerProtocol, image: bytes):
        self.config.logger.info("Callback image: {}" % image)
        await websocket.send(image)

    async def _client_connection(self, websocket: websockets.WebSocketServerProtocol, _path: str):
        self.config.logger.debug("New connection")

        response_callback = partial(self._client_on_response_callback, websocket)
        image_callback = partial(self._client_on_image_callback, websocket)

        self._client.register_response_callback(response_callback)
        self._client.register_image_callback(image_callback)

        while not self._shutdown:
            try:
                data = await websocket.recv()
                print("_client_connection", data)
            except ConnectionClosed:
                pass
            except Exception as e:
                self.config.logger.error("Error during receiving of client connection: %s" % str(e))

        self._client.unregister_response_callback(response_callback)
        self._client.unregister_image_callback(image_callback)

    def run(self):
        self._server = websockets.serve(self._client_connection, self.config.proxy_host, self.config.proxy_port)
        return self._server

    def stop(self):
        self._shutdown = True

        # todo: Close connected clients
        # if self._server:
        #    self._server.close()
