
# Use https://github.com/hathawsh/sockjs-protocol
# to run a test against this server.

# Known issues:
#
# - The websocket server does not support the old hixie-76 or
#   hybi-10 protocols, so 5 of the tests fail.
#
# - The test_abort_xhr_polling and test_abort_xhr_streaming tests
#   apparently expect the server to close the session when the client makes
#   a parallel connection. Is that really desired behavior?
#   Because we decide to keep sessions alive instead, 2 of the tests fail.

from twisted.internet import reactor
from twisted.internet.protocol import Factory
from twisted.internet.protocol import Protocol
from twisted.web.resource import Resource
from twisted.web.server import Site
from txsockjs.factory import SockJSResource


class EchoProtocol(Protocol):
    def dataReceived(self, msg):
        self.transport.write(msg)


class ImmediateCloseProtocol(Protocol):
    def connectionMade(self):
        reactor.callLater(0.001, self.transport.loseConnection)


def main():
    root = Resource()

    echo_factory = Factory.forProtocol(EchoProtocol)

    echo_resource = SockJSResource(echo_factory, options={
        'streaming_limit': 4096,
    })
    root.putChild(b'echo', echo_resource)

    disabled_websocket_resource = SockJSResource(echo_factory, options={
        'streaming_limit': 4096,
        'websocket': False,
    })
    root.putChild(b'disabled_websocket_echo', disabled_websocket_resource)

    cookie_needed_resource = SockJSResource(echo_factory, options={
        'streaming_limit': 4096,
        'cookie_needed': True,
    })
    root.putChild(b'cookie_needed_echo', cookie_needed_resource)

    close_factory = Factory.forProtocol(ImmediateCloseProtocol)
    root.putChild(b'close', SockJSResource(close_factory))

    site = Site(root)
    reactor.listenTCP(8081, site)
    reactor.run()


if __name__ == '__main__':
    main()
