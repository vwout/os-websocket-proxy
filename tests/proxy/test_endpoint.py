from proxy.opensongendpoint import OpenSongEndpoint


def test_endpoint_url_empty():
    endpoint = OpenSongEndpoint(url=None)
    assert endpoint.resource is None
    assert endpoint.action is None
    assert endpoint.identifier is None


def test_endpoint_resource():
    endpoint = OpenSongEndpoint(url="/presentation")
    assert endpoint.resource == "presentation"
    assert endpoint.action is None
    assert endpoint.identifier is None
    assert endpoint.matches_url("/presentation")
    assert not endpoint.matches_url("/presentation/slide")
    assert not endpoint.matches_url("/presentation/slide/list")
    assert not endpoint.matches_url("/presentation/slide/123")


def test_endpoint_resource_and_action():
    endpoint = OpenSongEndpoint(url="/presentation/slide")
    assert endpoint.resource == "presentation"
    assert endpoint.action == "slide"
    assert endpoint.identifier is None
    assert not endpoint.matches_url("/presentation")
    assert endpoint.matches_url("/presentation/slide")
    assert not endpoint.matches_url("/presentation/slide/list")
    assert not endpoint.matches_url("/presentation/slide/123")


def test_endpoint_resource_action_ident():
    endpoint = OpenSongEndpoint(url="/presentation/slide/list")
    assert endpoint.resource == "presentation"
    assert endpoint.action == "slide"
    assert endpoint.identifier == "list"
    assert not endpoint.matches_url("/presentation")
    assert not endpoint.matches_url("/presentation/slide")
    assert endpoint.matches_url("/presentation/slide/list")
    assert not endpoint.matches_url("/presentation/slide/123")


def test_endpoint_resource_action_anyident():
    endpoint = OpenSongEndpoint(url="/presentation/slide/*")
    assert endpoint.resource == "presentation"
    assert endpoint.action == "slide"
    assert endpoint.identifier == "*"
    assert not endpoint.matches_url("/presentation")
    assert not endpoint.matches_url("/presentation/slide")
    assert endpoint.matches_url("/presentation/slide/list")
    assert endpoint.matches_url("/presentation/slide/123")
