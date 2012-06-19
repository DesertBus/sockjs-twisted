from twisted.internet.protocol import Factory
from twisted.protocols.basic import LineReceiver
from twisted.internet import reactor, ssl
from txws import WebSocketFactory
from txsockjs.factory import SockJSFactory
from OpenSSL import SSL

class Chat(LineReceiver):
    def __init__(self, users):
        self.users = users
        self.name = None
        self.state = "GETNAME"
    def connectionMade(self):
        print("IRC Connection Made!")
        self.sendLine("What's your name?")
    def connectionLost(self, reason):
        print("IRC Connection Lost!")
        if self.users.has_key(self.name):
            del self.users[self.name]
    def lineReceived(self, line):
        if self.state == "GETNAME":
            self.handle_GETNAME(line)
        else:
            self.handle_CHAT(line)
    def handle_GETNAME(self, name):
        if self.users.has_key(name):
            self.sendLine("Name taken, please choose another.")
            return
        print("IRC User chose name - %s!" % name)
        self.sendLine("Welcome, %s!" % (name,))
        self.name = name
        self.users[name] = self
        self.state = "CHAT"
    def handle_CHAT(self, message):
        message = "<%s> %s" % (self.name, message)
        print(message)
        for name, protocol in self.users.iteritems():
            protocol.sendLine(message)

class ChatFactory(Factory):
    def __init__(self):
        self.users = {} # maps user names to Chat instances
    def buildProtocol(self, addr):
        return Chat(self.users)

f = ChatFactory()
s = SockJSFactory(f)
reactor.listenTCP(6667, f)
reactor.listenTCP(6672, s)
reactor.run()