from twisted.internet import reactor, protocol, ssl
from twisted.web import static, server, resource
from OpenSSL import SSL
from txsockjs.factory import SockJSResource

SECURE = False

### The website

class Config(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader('content-type', 'application/javascript; charset=UTF-8')
        return """var client_opts = {{
    // Address of a sockjs test server.
    url: 'http{}://localhost:8081',
    sockjs_opts: {{
        devel: true,
        debug: true,
        info: {{cookie_needed:false}}
    }}
}};""".format("s" if SECURE else "").encode('ascii')

class SlowScript(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader('content-type', 'application/javascript; charset=UTF-8')
        request.write(b"")
        reactor.callLater(0.500, self.done, request)
        return server.NOT_DONE_YET
    
    def done(self, request):
        request.write(b"var a = 1;\n")
        request.finish()

class Streaming(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader('content-type', 'text/plain; charset=UTF-8')
        request.setHeader('Access-Control-Allow-Origin', '*')
        request.write(b"a"*2048+b"\n")
        reactor.callLater(0.250, self.done, request)
        return server.NOT_DONE_YET
    
    def done(self, request):
        request.write(b"b\n")
        request.finish()

class Simple(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setHeader('content-type', 'text/plain; charset=UTF-8')
        request.setHeader('Access-Control-Allow-Origin', '*')
        return b"a"*2048+b"\nb\n"

class WrongURL(resource.Resource):
    isLeaf = True
    def render_GET(self, request):
        request.setResponseCode(404)
        return b""

website_root = static.File("qunit/html")
website_root.putChild(b"slow-script.js", SlowScript())
website_root.putChild(b"streaming.txt", Streaming())
website_root.putChild(b"simple.txt", Simple())
website_root.putChild(b"wrong_url_indeed.txt", WrongURL())
website_root.putChild(b"config.js", Config())
website = server.Site(website_root)
reactor.listenTCP(8082, website)

### The SockJS server

class Echo(protocol.Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class EchoFactory(protocol.Factory):
    protocol = Echo

class Close(protocol.Protocol):
    def connectionMade(self):
        self.transport.loseConnection()

class CloseFactory(protocol.Factory):
    protocol = Close

class Ticker(protocol.Protocol):
    ticker = None
    def connectionMade(self):
        self.ticker = reactor.callLater(1, self.tick)
    
    def tick(self):
        self.transport.write(b"tick!")
        self.ticker = reactor.callLater(1, self.tick)
    
    def connectionLost(self, reason=None):
        if self.ticker:
            self.ticker.cancel()

class TickerFactory(protocol.Factory):
    protocol = Ticker

class Amplify(protocol.Protocol):
    def dataReceived(self, data):
        length = int(data)
        length = length if length > 0 and length < 19 else 1
        self.transport.write(b"x" * 2**length)

class AmplifyFactory(protocol.Factory):
    protocol = Amplify

class Broadcast(protocol.Protocol):
    def connectionMade(self):
        self.factory.connections[self] = 1
    
    def dataReceived(self, data):
        for p in self.factory.connections.keys():
            p.transport.write(data)
    
    def connectionLost(self, reason=None):
        del self.factory.connections[self]

class BroadcastFactory(protocol.Factory):
    protocol = Broadcast
    connections = {}

echo = EchoFactory()
close = CloseFactory()
ticker = TickerFactory()
amplify = AmplifyFactory()
broadcast = BroadcastFactory()

sockjs_root = resource.Resource()
sockjs_root.putChild(b"echo", SockJSResource(echo, {'streaming_limit': 4 * 1024}))
sockjs_root.putChild(b"disabled_websocket_echo", SockJSResource(echo, {'websocket': False}))
sockjs_root.putChild(b"cookie_needed_echo", SockJSResource(echo, {'cookie_needed': True}))
sockjs_root.putChild(b"close", SockJSResource(close))
sockjs_root.putChild(b"ticker", SockJSResource(ticker))
sockjs_root.putChild(b"amplify", SockJSResource(amplify))
sockjs_root.putChild(b"broadcast", SockJSResource(broadcast))
sockjs = server.Site(sockjs_root)


### SSL shenanigans

# A direct copy of DefaultOpenSSLContextFactory as of Twisted 12.2.0
# The only difference is using ctx.use_certificate_chain_file instead of ctx.use_certificate_file
class ChainedOpenSSLContextFactory(ssl.DefaultOpenSSLContextFactory):
    def cacheContext(self):
        if self._context is None:
            ctx = self._contextFactory(self.sslmethod)
            ctx.set_options(SSL.OP_NO_SSLv2)
            ctx.use_certificate_chain_file(self.certificateFileName)
            ctx.use_privatekey_file(self.privateKeyFileName)
            self._context = ctx

if SECURE:
    ssl_cert = ChainedOpenSSLContextFactory("ssl.key","ssl.pem")
    reactor.listenSSL(8081, sockjs, ssl_cert)
else:
    reactor.listenTCP(8081, sockjs)

### Run the reactor

reactor.run()
