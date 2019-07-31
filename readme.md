# OpenSong Websocket Proxy

This is a proxy server for the [OpenSong API](http://www.opensong.org/home/api) over Websockets.

The OpenSong API allows interaction with OpenSong.
This means that external applications can request for example status information, or control a presentation.
The required server is integrated in OpenSong itself.

To use this API in for example an app on a tablet for use by people with bad sight, so that they can read the slides, the tablets need access to OpenSong.
This would required providing direct access by these devices to OpenSong.
In a properly setup configuration, the network for congregation member devices is separated from the network used for equipment to run the service, e.g. OpenSong.

This proxy solves exactly that problem.
The OpenSong Websocket Proxy acts as an intermediate, connecting clients to an OpenSong instance.
It isolates clients from the interal infrastructure and it reduces the load on OpenSong by (rate) limiting requests.

## Requirements

- OpenSong
- Python 3.7, with some packages. For easy installation, run pip with `requirements.txt`

    ```
    $ pip install -r requirements.txt
    ```
  