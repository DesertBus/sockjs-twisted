from twisted.internet import reactor, protocol
from txsockjs.factory import SockJSMultiFactory

class Echo(protocol.Protocol):
    def dataReceived(self, data):
        #print ">>> %s" % data
        self.transport.write(data)

class EchoFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Echo()

class Close(protocol.Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

class CloseFactory(protocol.Factory):
    def buildProtocol(self, addr):
        return Close()

echo = EchoFactory()
close = CloseFactory()

s = SockJSMultiFactory()
s.addFactory(echo, "echo", {'streaming_limit': 4 * 1024})
s.addFactory(close, "close", {'streaming_limit': 4 * 1024})
s.addFactory(echo, "disabled_websocket_echo", {'websocket': False, 'streaming_limit': 4 * 1024})
s.addFactory(echo, "cookie_needed_echo", {'cookie_needed': True, 'streaming_limit': 4 * 1024})

reactor.listenTCP(8081, s)
reactor.run()