import asyncio
import argparse
from .opensongwsclient import OpenSongWsClient
from .opensongwsserver import OpenSongWsServer
from .proxyconfig import ProxyConfig


def main():
    arg_parser = argparse.ArgumentParser(description='OpenSong WebSocket Proxy.',
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    arg_parser.add_argument("--host", default=ProxyConfig.default_proxy_host,
                            help='Address to run this proxy at')
    arg_parser.add_argument("--port", default=ProxyConfig.default_proxy_port, type=int,
                            help='Port the proxy accepts requests on')
    arg_parser.add_argument("--opensong-host", default=ProxyConfig.default_opensong_host,
                            help='Address of the OpenSong application')
    arg_parser.add_argument("--opensong-port", default=ProxyConfig.default_opensong_port, type=int,
                            help='Port of the OpenSong API server')
    args = arg_parser.parse_args()

    config = ProxyConfig()

    if args.host and args.host is not ProxyConfig.default_proxy_host:
        config.proxyhost = args.host
    if args.port and args.port is not ProxyConfig.default_proxy_port:
        config.proxy_port = args.port
    if args.opensong_host and args.opensong_host is not ProxyConfig.default_opensong_host:
        config.opensong_host = args.opensong_host
    if args.opensong_port and args.opensong_port is not ProxyConfig.default_opensong_port:
        config.opensong_port = args.opensong_port

    client = OpenSongWsClient(config)
    server = OpenSongWsServer(config, client)

    loop = asyncio.get_event_loop()

    loop.create_task(client.run())
    print("started client")
    loop.run_until_complete(server.run())
    print("started server")

    async def _nop():
        while True:
            await asyncio.sleep(1)

    # Workaround on Windows for capturing KeyboardInterrupt
    # see https://bugs.python.org/issue23057
    # source of workaround: https://stackoverflow.com/a/36925722
    loop.create_task(_nop())

    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass

    server.stop()
