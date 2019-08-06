import time
from typing import Union, Dict, Tuple, Optional
from .opensongendpoint import OpenSongEndpoint


class OpenSongResponseCache:
    Data = Union[str, bytes]

    def __init__(self):
        self._cache: Dict[OpenSongEndpoint, Tuple[int, OpenSongResponseCache.Data]] = {}

    def _get_response_by_endpoint(self, endpoint: OpenSongEndpoint) -> Optional[Data]:
        if endpoint in self._cache:
            expire, response = self._cache[endpoint]
            if expire >= int(time.time()):
                return response
            else:
                return None
        else:
            return None

    def get_response_by_url(self, url: str) -> Optional[Data]:
        for endpoint in self._cache:
            if endpoint.url == url:
                return self._get_response_by_endpoint(endpoint)
        else:
            return None

    def get_response_by_rai(self, resource: str = None, action: str = None, identifier: str = None) -> Optional[Data]:
        for endpoint in self._cache:
            if endpoint.matches_endpoint(resource, action, identifier):
                return self._get_response_by_endpoint(endpoint)
        return None

    def add_response(self, endpoint: OpenSongEndpoint, response: Data, ttl: Optional[int] = None):
        if not ttl:
            ttl = 10 * 60  # Set default TTL to 10 minutes
            if endpoint.resource == "presentation":
                if endpoint.action == "status":
                    ttl = 5
                elif endpoint.action == "list" and endpoint.identifier in [None, "list"]:
                    ttl = 5 * 60

        self._cache[endpoint] = (int(time.time()) + ttl, response)

    def purge(self):
        expired_endpoints = []
        for ep, (expire, _) in self._cache.items():
            if expire < int(time.time()):
                expired_endpoints.append(ep)

        for ep in expired_endpoints:
            del self._cache[ep]
