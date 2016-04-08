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

from zope.interface import directlyProvides, providedBy
from twisted.internet import reactor, protocol, address
from twisted.web import resource, server, http
from twisted.protocols.policies import ProtocolWrapper
from txsockjs.utils import normalize
import json, re

class StubResource(resource.Resource, ProtocolWrapper):
    isLeaf = True
    def __init__(self, parent, session):
        resource.Resource.__init__(self)
        ProtocolWrapper.__init__(self, None, session)
        self.parent = parent
        self.session = session
        self.putChild("", self)
    
    def render_OPTIONS(self, request):
        method = "POST" if getattr(self, "render_POST", None) is not None else "GET"
        request.setResponseCode(http.NO_CONTENT)
        self.parent.setBaseHeaders(request,False)
        request.setHeader('Cache-Control', 'public, max-age=31536000')
        request.setHeader('access-control-max-age', '31536000')
        request.setHeader('Expires', 'Fri, 01 Jan 2500 00:00:00 GMT') #Get a new library by then
        request.setHeader('Access-Control-Allow-Methods', 'OPTIONS, {0}'.format(method)) # Hardcoding this may be bad?
        return ""
    
    def connect(self, request):
        if self.session.attached:
            return 'c[2010,"Another connection still open"]\n'
        self.request = request
        directlyProvides(self, providedBy(request.transport))
        protocol.Protocol.makeConnection(self, request.transport)
        self.session.makeConnection(self)
        request.notifyFinish().addErrback(self.connectionLost)
        return server.NOT_DONE_YET
    
    def disconnect(self):
        self.request.finish()
        self.session.transportLeft()
    
    def loseConnection(self):
        self.request.finish()
        self.session.transportLeft()
    
    def connectionLost(self, reason=None):
        self.wrappedProtocol.connectionLost(reason)

    def getPeer(self):
        if self.parent._options["proxy_header"] and self.request.requestHeaders.hasHeader(self.parent._options["proxy_header"]):
            ip = self.request.requestHeaders.getRawHeaders(self.parent._options["proxy_header"])[0].split(",")[-1].strip()
            if re.match("\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", ip):
                return address.IPv4Address("TCP", ip, None)
            else:
                return address.IPv6Address("TCP", ip, None)
        return ProtocolWrapper.getPeer(self)


class Stub(ProtocolWrapper):
    def __init__(self, parent, session):
        self.parent = parent
        self.session = session
        self.pending = []
        self.buffer = []
        self.connecting = True
        self.disconnecting = False
        self.attached = False
        self.transport = None # Upstream (SockJS)
        self.protocol = None # Downstream (Wrapped Factory)
        self.peer = None
        self.host = None
        self.timeout = reactor.callLater(self.parent._options['timeout'], self.disconnect)
        self.heartbeat_timer = reactor.callLater(self.parent._options['heartbeat'], self.heartbeat)
    
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        protocol.Protocol.makeConnection(self, transport)
        self.attached = True
        self.peer = self.transport.getPeer()
        self.host = self.transport.getHost()
        if self.timeout.active():
            self.timeout.cancel()
        if self.protocol is None:
            self.protocol = self.parent._factory.buildProtocol(self.transport.getPeer())
            if self.protocol is None:
                self.connectionLost()
            else:
                self.protocol.makeConnection(self)
        self.sendData()
    
    def loseConnection(self):
        self.disconnecting = True
        self.sendData()
    
    def connectionLost(self, reason=None):
        if self.attached:
            self.disconnecting = True
            self.transport = None
            self.attached = False
            self.disconnect(reason=reason)
    
    def heartbeat(self):
        self.pending.append('h')
        self.heartbeat_timer = reactor.callLater(self.parent._options['heartbeat'], self.heartbeat)
        self.sendData()
    
    def disconnect(self, reason=None):
        if self.protocol:
            self.protocol.connectionLost(reason)
        del self.parent._sessions[self.session]
        if self.timeout.active():
            self.timeout.cancel()
        if self.heartbeat_timer.active():
            self.heartbeat_timer.cancel()
    
    def transportLeft(self):
        self.transport = None
        self.attached = False
        self.timeout = reactor.callLater(self.parent._options['timeout'], self.disconnect)
    
    def write(self, data):
        data = normalize(data, self.parent._options['encoding'])
        self.buffer.append(data)
        self.sendData()
    
    def writeSequence(self, data):
        for index, p in enumerate(data):
            data[index] = normalize(p, self.parent._options['encoding'])
        self.buffer.extend(data)
        self.sendData()
    
    def writeRaw(self, data):
        self.flushData()
        self.pending.append(data)
        self.sendData()
    
    def sendData(self):
        if self.transport:
            if self.connecting:
                self.transport.write('o')
                self.connecting = False
                self.sendData()
            elif self.disconnecting:
                self.transport.write('c[3000,"Go away!"]')
                if self.transport:
                    self.transport.loseConnection()
            else:
                self.flushData()
                if self.pending:
                    data = list(self.pending)
                    self.pending = []
                    self.transport.writeSequence(data)
    
    def flushData(self):
        if self.buffer:
            data = 'a{0}'.format(json.dumps(self.buffer, separators=(',',':')))
            self.buffer = []
            self.pending.append(data)
    
    def requeue(self, data):
        data.extend(self.pending)
        self.pending = data
    
    def dataReceived(self, data):
        if self.timeout.active():
            self.timeout.reset(5)
        if data == '':
            return "Payload expected."
        try:
            packets = json.loads(data)
            for p in packets:
                p = normalize(p, self.parent._options['encoding'])
                if self.protocol:
                    self.protocol.dataReceived(p)
            return None
        except ValueError:
            return "Broken JSON encoding."
        
    def getPeer(self):
        return self.peer
    
    def getHost(self):
        return self.host
    
    def registerProducer(self, producer, streaming):
        if self.transport:
            self.transport.registerProducer(producer, streaming)
    
    def unregisterProducer(self):
        if self.transport:
            self.transport.unregisterProducer()
    
    def stopConsuming(self):
        if self.transport:
            self.transport.stopConsuming()
