# Copyright (c) 2012, Christopher Gamble
# All rights reserved.
# 
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#    * Redistributions of source code must retain the above copyright
#      notice, this list of conditions and the following disclaimer.
#    * Redistributions in binary form must reproduce the above copyright
#      notice, this list of conditions and the following disclaimer in the
#      documentation and/or other materials provided with the distribution.
#    * Neither the name of the Christopher Gamble nor the names of its 
#      contributors may be used to endorse or promote products derived 
#      from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED 
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE DISCLAIMED.
# IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT,
# INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING,
# BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
# DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE
# OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED
# OF THE POSSIBILITY OF SUCH DAMAGE.

from twisted.internet.protocol import Protocol, Factory
from twisted.protocols.policies import ProtocolWrapper
from txsockjs.factory import SockJSResource

class BroadcastProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.broadcast(data)

class BroadcastFactory(Factory):
    protocol = BroadcastProtocol

class MultiplexProxy(ProtocolWrapper):
    def __init__(self, factory, wrappedProtocol, transport, topic):
        ProtocolWrapper.__init__(self, factory, wrappedProtocol)
        self.topic = topic
        self.makeConnection(transport)
    
    def write(self, data):
        self.transport.transport.write(",".join(["msg", self.topic, data]))
    
    def writeSequence(self, data):
        for d in data:
            self.write(d)
    
    def broadcast(self, data):
        self.factory.broadcast(self.topic, data)

class MultiplexProtocol(Protocol):
    def connectionMade(self):
        self.factory._connections[self] = {}
    
    def dataReceived(self, message):
        type, topic, payload = message.split(",", 2)
        if type == "sub":
            self.factory.subscribe(self, topic)
        elif type == "msg":
            self.factory.handleMessage(self, topic, payload)
        elif type == "uns":
            self.factory.unsubscribe(self, topic)
    
    def connectionLost(self, reason=None):
        for conn in self.factory._connections[self].values():
            conn.connectionLost(reason)
        del self.factory._connections[self]

class MultiplexFactory(Factory):
    protocol = MultiplexProtocol
    
    def __init__(self, resource):
        self._resource = resource
        self._topics = {}
        self._connections = {}
    
    def addFactory(self, name, factory):
        self._topics[name] = factory
    
    def broadcast(self, name, message):
        for topics in self._connections.values():
            if name in topics:
                topics[name].write(message)
    
    def removeFactory(self, name, factory):
        del self._topics[name]
    
    def subscribe(self, p, name):
        if name not in self._topics:
            return
        self._connections[p][name] = MultiplexProxy(self, self._topics[name].buildProtocol(p.transport.getPeer()), p, name)
    
    def handleMessage(self, p, name, message):
        if p not in self._connections:
            return
        if name not in self._connections[p]:
            return
        self._connections[p][name].dataReceived(message)
    
    def unsubscribe(self, p, name):
        if p not in self._connections:
            return
        if name not in self._connections[p]:
            return
        self._connections[p][name].connectionLost(None)
        del self._connections[p][name]
    
    def registerProtocol(self, p):
        pass
    
    def unregisterProtocol(self, p):
        pass
        
class PubSubFactory(MultiplexFactory):
    broadcastFactory = BroadcastFactory()
    
    def subscribe(self, p, name):
        if name not in self._topics:
            self._topics[name] = self.broadcastFactory
        MultiplexFactory.subscribe(self, p, name)

class SockJSMultiplexResource(SockJSResource):
    def __init__(self, options=None):
        SockJSResource.__init__(self, MultiplexFactory(self), options)
    
    def addFactory(self, name, factory):
        return self._factory.addFactory(name, factory)
    
    def broadcast(self, name, message):
        return self._factory.broadcast(name, message)
    
    def removeFactory(self, name):
        return self._factory.removeFactory(name)

class SockJSPubSubResource(SockJSMultiplexResource):
    def __init__(self, options=None):
        SockJSResource.__init__(self, PubSubFactory(self), options)
