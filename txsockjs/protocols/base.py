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

class SessionProtocol(ProtocolWrapper):
    def __init__(self, parent):
        self.method = parent.method
        self.headers = parent.headers
        self.session = parent.session
        self.location = parent.location
        self.factory = parent.factory
        self.transport = parent
        self.wrappedProtocol = None
    def connect(self):
        print("Connect dis bitch")
        self.wrappedProtocol = self.factory.wrappedFactory.buildProtocol(self.transport.addr)
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.factory.registerProtocol(self)
        if self.wrappedProtocol:
            self.wrappedProtocol.makeConnection(self)
        else:
            print("No wrappedProtocol, attempting disconnect")
            self.loseConnection()
    def relayData(self, data):
        self.wrappedProtocol.dataReceived(data)
    def sendHeaders(self, headers):
        h = ""
        if 'status' in headers:
            h += "HTTP/1.1 %s\r\n" % headers['status']
            del headers['status']
        for k, v in headers.iteritems():
            h += "%s: %s\r\n" % (k, v)
        self.transport.write(h + "\r\n")