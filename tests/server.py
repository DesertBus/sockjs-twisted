from twisted.internet import reactor, protocol
from twisted.web import server, resource
from txsockjs.factory import SockJSMultiFactory, SockJSResource

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

root = resource.Resource()
root.putChild("echo", SockJSResource(echo, {'streaming_limit': 4 * 1024}))
root.putChild("close", SockJSResource(close, {'streaming_limit': 4 * 1024}))
root.putChild("disabled_websocket_echo", SockJSResource(echo, {'websocket': False, 'streaming_limit': 4 * 1024}))
root.putChild("cookie_needed_echo", SockJSResource(echo, {'cookie_needed': True, 'streaming_limit': 4 * 1024}))
site = server.Site(root)

reactor.listenTCP(8081, s)
reactor.listenTCP(8082, site)
reactor.run()