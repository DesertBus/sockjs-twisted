from twisted.internet import reactor, protocol
from twisted.web import server, resource
from txsockjs.multiplex import SockJSMultiplexResource

class AnnP(protocol.Protocol):
    def connectionMade(self):
        self.transport.write("Ann says hi!")
    
    def dataReceived(self, data):
        self.transport.write("Ann nods: " + data)

class BobP(protocol.Protocol):
    def connectionMade(self):
        self.transport.write("Bob doesn't agree.")
    
    def dataReceived(self, data):
        self.transport.write("Bob says no to: " + data)

class CarlP(protocol.Protocol):
    def connectionMade(self):
        self.transport.write("Carl says goodbye!")
        self.transport.loseConnection()

class AnnF(protocol.Factory):
    protocol = AnnP

class BobF(protocol.Factory):
    protocol = BobP

class CarlF(protocol.Factory):
    protocol = CarlP

multiplex = SockJSMultiplexResource()
multiplex.addFactory("ann", AnnF())
multiplex.addFactory("bob", BobF())
multiplex.addFactory("carl", CarlF())

root = resource.Resource()
root.putChild("multiplex", multiplex)
site = server.Site(root)

reactor.listenTCP(8081, site)
reactor.run()