from typing import Tuple, Optional


class Endpoint:
    def __init__(self, url: str):
        self._url: str = url
        (self._resource, self._action, self._identifier) = self._parse_resource()

    def _parse_resource(self) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        components = []
        if self._url:
            url = self._url.lstrip("/")
            components = url.split("/")

        # Ensure components has at least 3 items
        components.extend([None, None, None])
        return tuple(components[:3])

    @property
    def url(self) -> str:
        return self._url

    @property
    def resource(self) -> Optional[str]:
        return self._resource

    @property
    def action(self) -> Optional[str]:
        return self._action

    @property
    def identifier(self) -> Optional[str]:
        return self._identifier

    def matches_url(self, url: str) -> bool:
        endpoint = Endpoint(url)
        return self.matches_endpoint(endpoint.resource, endpoint.action, endpoint.identifier)

    def matches_endpoint(self, resource: str = None, action: str = None, identifier: str = None) -> bool:
        return resource is not None and resource == self._resource and \
               (action == self._action or (action and self._action in ["", "*"])) and \
               (identifier == self._identifier or (identifier and self._identifier in ["", "*"]))
