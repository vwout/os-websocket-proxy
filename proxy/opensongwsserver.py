import asyncio
import websockets
from websockets.http import Headers as HTTPHeaders
from http import HTTPStatus
from typing import Optional, List, Tuple
from .proxyconfig import ProxyConfig
from .opensongwsclient import OpenSongWsClient
from .opensongwsconnection import OpenSongWsConnection
from .opensongendpoint import OpenSongEndpoint

HTTPResponse = Tuple[HTTPStatus, HTTPHeaders, bytes]


class OpenSongWsServer:
    def __init__(self, config: ProxyConfig, client: OpenSongWsClient):
        self.config = config
        self._client = client
        self._server: Optional[websockets.serve] = None
        self._connections: List[OpenSongWsConnection] = []
        self._response_queue = asyncio.Queue(loop=asyncio.get_event_loop())
        self._client.register_response_callback(self._client_on_response_callback)
        self._client.register_image_callback(self._client_on_image_callback)

    async def _client_on_response_callback(self, response: str,
                                           resource: str = None, action: str = None, identifier: str = None):
        await self._response_queue.put((resource, action, identifier, response))

    async def _client_on_image_callback(self, image: bytes,
                                        resource: str = None, action: str = None, identifier: str = None):
        await self._response_queue.put((resource, action, identifier, image))

    async def _client_connection(self, websocket: websockets.WebSocketServerProtocol, _path: str):
        self.config.logger.debug("New connection")

        connection = OpenSongWsConnection(websocket, self.config)
        self._connections.append(connection)

        await connection.run(self._client)
        await websocket.close()

        self._connections.remove(connection)

    async def _receive_resource(self, endpoint: OpenSongEndpoint) -> Optional[HTTPResponse]:
        while True:
            response = await self._response_queue.get()
            if response is not None:
                resource, action, identifier, response_data = response
                if endpoint.matches_endpoint(resource, action, identifier):
                    if type(response_data) is str:
                        headers = HTTPHeaders()
                        if response_data[:5] == "<?xml":
                            headers["Content-Type"] = "text/xml"
                        return HTTPStatus.OK, headers, response_data.encode()
                    elif type(response_data) is bytes:
                        headers = HTTPHeaders()
                        headers["Content-Type"] = "image/jpeg"
                        return HTTPStatus.OK, headers, response_data
                    else:
                        break
            else:
                break

        return None

    async def _process_request(self, path: str, request_headers: HTTPHeaders) -> Optional[HTTPResponse]:
        if "Upgrade" not in request_headers:
            endpoint = OpenSongEndpoint(url=path)
            if OpenSongWsConnection.resource_supported(endpoint) and not endpoint.resource == "ws":
                print("Request", path)
                if await self._client.request_resource(endpoint):
                    response = await self._receive_resource(endpoint)
                    if response:
                        return response
                    else:
                        return HTTPStatus.INTERNAL_SERVER_ERROR, HTTPHeaders(), bytes()
                else:
                    return HTTPStatus.NOT_IMPLEMENTED, HTTPHeaders(), bytes()
        else:
            return None

    def run(self):
        self._server = websockets.serve(ws_handler=self._client_connection, host=self.config.proxy_host,
                                        port=self.config.proxy_port, process_request=self._process_request)
        return self._server

    def stop(self):
        # await self._response_queue.put(None)
        for connection in self._connections:
            try:
                connection.stop()
            except:
                pass

        if self._server:
            self._server.ws_server.close()
