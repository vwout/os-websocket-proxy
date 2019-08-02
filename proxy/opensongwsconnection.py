import websockets
from functools import partial
from websockets.exceptions import ConnectionClosed
from .proxyconfig import ProxyConfig
from .opensongwsclient import OpenSongWsClient


class OpenSongWsConnection:
    def __init__(self, websocket: websockets.WebSocketServerProtocol, config: ProxyConfig):
        self._websocket = websocket
        self.config = config
        self._shutdown = False

    async def _client_on_response_callback(self, websocket: websockets.WebSocketServerProtocol, response: str):
        self.config.logger.info("Callback response: %s" % response)
        print("Callback response: %s" % response)

        # todo: only send the data to the client in case of a pending response
        #       or when a subscription is active

        await websocket.send(response)

    async def _client_on_image_callback(self, websocket: websockets.WebSocketServerProtocol, image: bytes):
        self.config.logger.info("Callback image: {}" % image)
        await websocket.send(image)

    async def run(self, client: OpenSongWsClient):
        response_callback = partial(self._client_on_response_callback, self._websocket)
        image_callback = partial(self._client_on_image_callback, self._websocket)

        client.register_response_callback(response_callback)
        client.register_image_callback(image_callback)

        while not self._shutdown:
            try:
                data = await self._websocket.recv()
                print("_client_connection", data)
            except ConnectionClosed:
                self._shutdown = True
            except Exception as e:
                self.config.logger.error("Error during receiving of client connection: %s" % str(e))

        client.unregister_response_callback(response_callback)
        client.unregister_image_callback(image_callback)

    def stop(self):
        self._shutdown = True
