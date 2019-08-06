import asyncio
import time
import xml.etree.ElementTree as Et
import websockets
from collections import OrderedDict
from typing import Optional, List, Union
from .proxyconfig import ProxyConfig
from .opensongendpoint import OpenSongEndpoint
from .opensongresponsecache import OpenSongResponseCache


class OpenSongWsClient:
    def __init__(self, config: ProxyConfig):
        self.config = config
        self.reconnect_delay: int = 0
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._shutdown = False
        self._response_callbacks: List = []
        self._image_callbacks: List = []
        self._pending_requests: OrderedDict[OpenSongEndpoint, int] = OrderedDict()
        self._response_cache = OpenSongResponseCache()

    def register_response_callback(self, callback):
        if callback not in self._response_callbacks:
            self._response_callbacks.append(callback)

    def unregister_response_callback(self, callback):
        if callback in self._response_callbacks:
            self._response_callbacks.remove(callback)

    async def _response_callback(self, response: str, resource: str = None, action: str = None, identifier: str = None):
        for callback in self._response_callbacks:
            try:
                await callback(response, resource, action, identifier)
            except:
                pass

    def register_image_callback(self, callback):
        if callback not in self._image_callbacks:
            self._image_callbacks.append(callback)

    def unregister_image_callback(self, callback):
        if callback in self._image_callbacks:
            self._image_callbacks.remove(callback)

    async def _image_callback(self, image: bytes, resource: str = None, action: str = None, identifier: str = None):
        for callback in self._image_callbacks:
            try:
                await callback(image, resource, action, identifier)
            except:
                pass

    def _schedule_response_callback(self, endpoint: OpenSongEndpoint, response: Union[str, bytes]):
        if type(response) is str:
            cb_future = lambda: asyncio.ensure_future(
                self._response_callback(response, endpoint.resource if endpoint else None,
                                        endpoint.action if endpoint else None,
                                        endpoint.identifier if endpoint else None))
            asyncio.get_event_loop().call_soon(cb_future)
        elif type(response) is bytes:
            cb_future = lambda: asyncio.ensure_future(
                self._image_callback(response, endpoint.resource if endpoint else None,
                                     endpoint.action if endpoint else None, endpoint.identifier if endpoint else None))
            asyncio.get_event_loop().call_soon(cb_future)

    def _add_pending_request(self, endpoint: OpenSongEndpoint):
        # First cleanup the pending requests
        for ep, added in self._pending_requests.items():
            if added < time.time() - 5:
                del self._pending_requests[ep]
        if endpoint in self._pending_requests:
            del self._pending_requests[endpoint]
        self._pending_requests[endpoint] = int(time.time())

    def _schedule_websocket_send(self, websocket: websockets.WebSocketClientProtocol, endpoint: OpenSongEndpoint,
                                 delay: int = 0, add_pending_request: bool = True):
        if add_pending_request:
            self._add_pending_request(endpoint)
        send_future = lambda: asyncio.ensure_future(websocket.send(endpoint.url))
        asyncio.get_event_loop().call_later(delay, send_future)
        return True

    def _ws_subscribe(self, websocket: websockets.WebSocketClientProtocol, identifier: str, delay: int = 0):
        endpoint = OpenSongEndpoint(url="/ws/subscribe/%s" % identifier)
        self._schedule_websocket_send(websocket, endpoint, delay, add_pending_request=False)

    async def run(self):
        uri = "ws://%s:%d/ws" % (self.config.opensong_host, self.config.opensong_port)

        while not self._shutdown:
            try:
                async with websockets.connect(uri) as websocket:
                    self._websocket = websocket
                    # Request OpenSong subscription, delayed to ensure proper initialization
                    self._ws_subscribe(websocket, "presentation", 5)

                    async for data in websocket:
                        endpoint = None
                        if type(data) is str:
                            if data[:5] == "<?xml":
                                try:
                                    xml_root = Et.fromstring(data)
                                except:
                                    xml_root = None
                                    self.config.logger.debug("Failed to parse message from OpenSong:", data)

                                if xml_root:
                                    # xml_root object is <response> node
                                    resource = xml_root.get("resource")
                                    action = xml_root.get("action")
                                    identifier = xml_root.get("identifier")

                                    endpoint = OpenSongEndpoint(url=None, resource=resource, action=action,
                                                                identifier=identifier)
                                    for ep in reversed(self._pending_requests.keys()):
                                        if ep.expect_binary_response():
                                            continue
                                        elif ep.matches_endpoint(resource, action, identifier):
                                            endpoint = ep
                                            del self._pending_requests[ep]
                                            break

                                    self.config.logger.debug("Received data for endpoint '%s'" %
                                                             endpoint.url if endpoint else "unknown")
                                    self._schedule_response_callback(endpoint, data)
                            else:
                                if data == "OK":
                                    # Ignore the confirmation
                                    pass
                                else:
                                    self.config.logger.debug("Not parsing: {}".format(data))

                        elif type(data) is bytes:
                            for ep in reversed(self._pending_requests.keys()):
                                if ep.expect_binary_response():
                                    endpoint = ep
                                    del self._pending_requests[ep]
                                    break

                            self.config.logger.debug("Received image for endpoint '%s'" %
                                                     endpoint.url if endpoint else "unknown")
                            self._schedule_response_callback(endpoint, data)

                        if endpoint:
                            self._response_cache.add_response(endpoint, data)

                        if self._shutdown:
                            break

                    self._websocket = None

            except Exception as e:
                if isinstance(e, SystemExit):
                    self._shutdown = True
                else:
                    self.config.logger.error("Websocket connection caused a failure (%s): %s" %
                                             (type(e).__name__, str(e)))
            finally:
                self._websocket = None

            if not self._shutdown:
                self.config.logger.info("Waiting to (re)connect to OpenSong at %s ..." % uri)
                if self.reconnect_delay:
                    await asyncio.sleep(self.reconnect_delay)

    async def request_resource(self, endpoint: OpenSongEndpoint) -> bool:
        if self._websocket:
            self._response_cache.purge()
            cached_response = self._response_cache.get_response_by_url(endpoint.url)
            if cached_response:
                self.config.logger.debug("Serve response for %s from cache" % endpoint.url)
                self._schedule_response_callback(endpoint, cached_response)
                return True
            else:
                self.config.logger.debug("Request response for %s at OpenSong" % endpoint.url)
                return self._schedule_websocket_send(self._websocket, endpoint)
        else:
            return False

    def stop(self):
        self._shutdown = True
        if self._websocket:
            self._websocket.close()
