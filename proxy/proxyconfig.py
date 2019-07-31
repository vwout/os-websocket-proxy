import os
import logging


class ProxyConfig:
    default_proxy_host = 'localhost'
    default_proxy_port = 8082
    default_opensong_host = 'opensong'
    default_opensong_port = 8082

    def __init__(self):
        self.proxy_host = os.getenv("PROXY_HOST", self.default_proxy_host)
        self.proxy_port = os.getenv("PROXY_PORT", self.default_proxy_port)
        self.opensong_host = os.getenv("OPENSONG_HOST", self.default_opensong_host)
        self.opensong_port = os.getenv("OPENSONG_PORT", self.default_opensong_port)

        self.logger = logging.getLogger("OpenSongWsProxy")
        self.logger.setLevel(logging.DEBUG)

        handler = logging.StreamHandler()
        handler.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
