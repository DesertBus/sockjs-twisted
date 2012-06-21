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
from twisted.internet.protocol import Protocol
from twisted.protocols.policies import ProtocolWrapper
from txsockjs import utils

REQUEST, NEGOTIATING, ROUTED = range(3)

class SockJSNegotiator(ProtocolWrapper):
    buf = ""
    state = REQUEST
    method = None
    headers = None
    session = None
    location = None
    query = None
    version = None
    factory = None
    wrappedProtocol = None
    addr = None
    
    def __init__(self, factory, addr):
        ProtocolWrapper.__init__(self,factory,None)
        self.addr = addr
        #print("Negotiator Started")
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
    def dataReceived(self, data):
        #print("Negotiator recieved data - %s" % data)
        if self.state == ROUTED:
            return self.wrappedProtocol.dataReceived(data)
        self.buf += data
        oldstate = None
        while oldstate != self.state:
            oldstate = self.state
            if self.state == REQUEST:
                if "\r\n" in self.buf:
                    request, chaff, self.buf = self.buf.partition("\r\n")
                    try:
                        self.method, self.location, self.version = request.split(" ")
                    except ValueError:
                        #print("Could not determine location, closing connection")
                        self.loseConnection()
                    else:
                        #print("Negotiator entered NEGOTIATING state")
                        self.state = NEGOTIATING
            elif self.state == NEGOTIATING:
                if "\r\n\r\n" in self.buf:
                    head, chaff, self.buf = self.buf.partition("\r\n\r\n")
                    self.headers = utils.httpHeaders(head)
                    self.negotiate()
            elif self.state == ROUTED:
                self.wrappedProtocol.dataReceived(self.buf)
                self.buf = ""
    #def write(self, data):
    #    print ">>> %s" % data
    #    self.transport.write(data)
    def connectionLost(self, reason):
        #print("Negotiator lost connection - %s" % reason)
        if self.wrappedProtocol:
            self.wrappedProtocol.connectionLost(reason)
    def negotiate(self):
        prefix, self.session, method, self.query = utils.parsePath(self.location,self.factory.routes.keys())
        self.factory = self.factory.resolvePrefix(prefix)
        if self.factory is None:
            method = utils.methods['ERROR404']
        #print("Negotiator location is %s" % self.location)
        #print("Negotiator factory is %s" % self.factory.__class__.__name__)
        #print("Negotiator protocol is %s" % method.__name__)
        self.wrappedProtocol = method(self)
        self.wrappedProtocol.makeConnection(self)
        self.state = ROUTED
        #print("Negotiator entered ROUTED state")
