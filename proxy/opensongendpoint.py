from typing import Tuple, Optional


class OpenSongEndpoint:
    def __init__(self, url: Optional[str], resource: Optional[str] = None, action: Optional[str] = None,
                 identifier: Optional[str] = None):
        if url:
            self._url: str = url
            (self._resource, self._action, self._identifier, self._sub_command) = self._parse_resource()
        else:
            self._resource = resource
            self._action = action
            self._identifier = identifier
            self._sub_command = None
            self._url = self._construct_url()

    def _parse_resource(self) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
        components = []
        if self._url:
            url = self._url.lstrip("/")
            components = url.split("/")

        # Ensure components has at least 4 items
        components.extend([None, None, None, None])
        return tuple(components[:4])

    def _construct_url(self) -> str:
        url = ""

        if self._resource or self._action or self._identifier:
            url = "/%s" % self._resource or ""
        if self._action or self._identifier:
            url += "/%s" % self._action or ""
        if self._identifier:
            url += "/%s" % self._identifier

        return url

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
        endpoint = OpenSongEndpoint(url=url)
        return self.matches_endpoint(endpoint.resource, endpoint.action, endpoint.identifier)

    def matches_endpoint(self, resource: str = None, action: str = None, identifier: str = None) -> bool:
        return resource is not None and resource == self._resource and \
               (action == self._action or (action and self._action in ["", "*"])) and \
               (identifier == self._identifier or (identifier and self._identifier in ["", "*"]))

    def expect_binary_response(self):
        return self._resource == "presentation" and self._action == "slide" and \
               self._sub_command in ["preview", "image"]
