import asyncio
import xml.etree.ElementTree as Et
import websockets
from typing import Optional
from .proxyconfig import ProxyConfig


class OpenSongWsClient:
    def __init__(self, config: ProxyConfig):
        self.config = config
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._shutdown = False
        self._response_callbacks = []
        self._image_callbacks = []

    def register_response_callback(self, callback):
        if callback not in self._response_callbacks:
            print("register response callback", callback)
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

    async def _image_callback(self, image: bytes):
        for callback in self._image_callbacks:
            try:
                await callback(image)
            except:
                pass

    @staticmethod
    def _websocket_send(websocket: websockets.WebSocketClientProtocol, resource: str, delay: int = 0):
        send_future = lambda: asyncio.ensure_future(websocket.send(resource))
        asyncio.get_event_loop().call_later(delay, send_future)
        return True

    @classmethod
    def _ws_subscribe(cls, websocket: websockets.WebSocketClientProtocol, identifier: str, delay: int = 0):
        resource = "/ws/subscribe/%s" % identifier
        cls._websocket_send(websocket, resource, delay)

    async def run(self):
        uri = "ws://%s:%d/ws" % (self.config.opensong_host, self.config.opensong_port)

        while not self._shutdown:
            try:
                async with websockets.connect(uri) as websocket:
                    self._websocket = websocket
                    # Request OpenSong subscription, delayed to ensure proper initialization
                    self._ws_subscribe(websocket, "presentation", 5)

                    async for data in websocket:
                        if type(data) is str:
                            self.config.logger.debug("received str: %s" % data)
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

                                    cb_future = lambda: asyncio.ensure_future(
                                        self._response_callback(data, resource, action, identifier))
                                    asyncio.get_event_loop().call_soon(cb_future)

                            else:
                                if data == "OK":
                                    # Ignore the confirmation
                                    pass
                                else:
                                    self.config.logger.debug("Not parsing: {}".format(data))

                        elif type(data) is bytes:
                            self.config.logger.debug("Received image")
                            cb_future = lambda: asyncio.ensure_future(self._image_callback(data))
                            asyncio.get_event_loop().call_soon(cb_future)

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
                # await asyncio.sleep(5)

    async def request_resource(self, resource: str) -> bool:
        if self._websocket:
            return self._websocket_send(self._websocket, resource)
        else:
            return False

    def stop(self):
        self._shutdown = True
        if self._websocket:
            self._websocket.close()
