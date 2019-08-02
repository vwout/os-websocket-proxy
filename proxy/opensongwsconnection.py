import asyncio
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
        self._subscribed = False

    async def _client_on_response_callback(self, websocket: websockets.WebSocketServerProtocol, response: str,
                                           resource: str = None, action: str = None, identifier: str = None):
        self.config.logger.info("Callback response on %s/%s/%s: %s" % (resource or "", action or "", identifier or "", response))
        print("Callback response: %s" % response)

        if self._subscribed and (resource, action) == ("presentation", "status"):
            await websocket.send(response)
        else:
            # todo: only send the data to the client in case of a pending response
            pass

    async def _client_on_image_callback(self, websocket: websockets.WebSocketServerProtocol, image: bytes):
        self.config.logger.info("Callback image: {}" % image)
        await websocket.send(image)

    async def process_request(self, resource: str, client: OpenSongWsClient):
        if resource == "/ws/subscribe/presentation":
            self._subscribed = True
            await self._websocket.send("OK")
        elif resource == "/ws/unsubscribe/presentation":
            self._subscribed = False
            await self._websocket.send("OK")
        else:
            await self._websocket.send("The requested resource could not be found")

    async def run(self, client: OpenSongWsClient):
        response_callback = partial(self._client_on_response_callback, self._websocket)
        image_callback = partial(self._client_on_image_callback, self._websocket)

        client.register_response_callback(response_callback)
        client.register_image_callback(image_callback)

        while not self._shutdown:
            try:
                resource = await self._websocket.recv()
                if resource:
                    handler = lambda: asyncio.ensure_future(self.process_request(resource, client))
                    asyncio.get_event_loop().call_soon(handler)
            except ConnectionClosed:
                self._shutdown = True
            except Exception as e:
                self.config.logger.error("Error during receiving of client connection: %s" % str(e))

        client.unregister_response_callback(response_callback)
        client.unregister_image_callback(image_callback)

    def stop(self):
        self._shutdown = True
