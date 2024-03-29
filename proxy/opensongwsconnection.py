import asyncio
import websockets
from functools import partial
from typing import Optional
from websockets.exceptions import ConnectionClosed
from .proxyconfig import ProxyConfig
from .opensongwsclient import OpenSongWsClient
from .opensongendpoint import OpenSongEndpoint


class OpenSongWsConnection:
    _allowed_endpoints = [
        OpenSongEndpoint("/presentation/status"),
        OpenSongEndpoint("/presentation/slide"),
        OpenSongEndpoint("/presentation/slide/list"),
        OpenSongEndpoint("/presentation/slide/*"),
        OpenSongEndpoint("/presentation/slide/*/preview"),
        OpenSongEndpoint("/presentation/slide/*/image"),

        OpenSongEndpoint("/song"),
        OpenSongEndpoint("/song/list"),
        OpenSongEndpoint("/song/list/*"),
        OpenSongEndpoint("/song/*/*"),
        OpenSongEndpoint("/song/detail/*"),
        OpenSongEndpoint("/song/folders"),

        OpenSongEndpoint("/set"),
        OpenSongEndpoint("/set/list"),
        OpenSongEndpoint("/set/slide/*"),
        OpenSongEndpoint("/set/slide/*"),

        OpenSongEndpoint("/ws/subscribe/*"),
        OpenSongEndpoint("/ws/unsubscribe/*"),
    ]

    def __init__(self, websocket: websockets.WebSocketServerProtocol, config: ProxyConfig):
        self._websocket = websocket
        self.config = config
        self._shutdown = False
        self._subscribed = False
        self._last_requested_endpoint: Optional[OpenSongEndpoint] = None

    async def _client_on_response_callback(self, websocket: websockets.WebSocketServerProtocol, response: str,
                                           resource: str = None, action: str = None, identifier: str = None):
        self.config.logger.info("Callback response on %s/%s/%s: %s" %
                                (resource or "", action or "", identifier or "",
                                 response if len(response) < 1000 else response[:1000] + "..."))

        forward_future = lambda: asyncio.ensure_future(websocket.send(response))

        if self._subscribed and (resource, action) == ("presentation", "status"):
            asyncio.get_event_loop().call_soon(forward_future)
        elif self._last_requested_endpoint and \
                not self._last_requested_endpoint.expect_binary_response() and \
                self._last_requested_endpoint.matches_endpoint(resource, action, identifier):
            asyncio.get_event_loop().call_soon(forward_future)
            self._last_requested_endpoint = None
        else:
            # Ignore the response for this connection
            pass

    async def _client_on_image_callback(self, websocket: websockets.WebSocketServerProtocol, image: bytes,
                                        resource: str = None, action: str = None, identifier: str = None):
        self.config.logger.info("Callback image on %s/%s/%s: %d bytes" %
                                (resource or "", action or "", identifier or "", len(image)))

        forward_future = lambda: asyncio.ensure_future(websocket.send(image))

        if self._last_requested_endpoint and \
                self._last_requested_endpoint.expect_binary_response() and \
                self._last_requested_endpoint.matches_endpoint(resource, action, identifier):
            asyncio.get_event_loop().call_soon(forward_future)
            self._last_requested_endpoint = None
        else:
            # Ignore the response for this connection
            pass

    @classmethod
    def resource_supported(cls, ep: OpenSongEndpoint) -> bool:
        return any(aep.matches_endpoint(ep.resource, ep.action, ep.identifier) for aep in cls._allowed_endpoints)

    async def process_request(self, resource: str, client: OpenSongWsClient):
        supported = False

        endpoint = OpenSongEndpoint(url=resource)
        if self.resource_supported(endpoint):
            if endpoint.resource == "ws":
                if resource == "/ws/subscribe/presentation":
                    self._subscribed = True
                    await self._websocket.send("OK")
                    supported = True
                elif resource == "/ws/unsubscribe/presentation":
                    self._subscribed = False
                    await self._websocket.send("OK")
                    supported = True
            else:
                if await client.request_resource(endpoint):
                    self._last_requested_endpoint = endpoint
                    supported = True

        if not supported:
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
