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

from twisted.internet.protocol import Protocol
from txsockjs.constants import states, methods
from txsockjs.protocols import *
from txsockjs import utils

class SockJSNegotiator(ProtocolWrapper):
    buf = ""
    state = states.REQUEST
    headers = None
    location = None
    factory = None
    wrappedProtocol = None
    
    def __init__(self, factory):
        ProtocolWrapper.__init__(self,factory,None)
    def dataRecieved(self, data):
        self.buf += data
        oldstate = None
        while oldstate != self.state:
            oldstate = self.state
            if self.state == states.REQUEST:
                if "\r\n" in self.buf:
                    request, chaff, self.buf = self.buf.partition("\r\n")
                    try:
                        verb, self.location, version = request.split(" ")
                    except ValueError:
                        self.loseConnection()
                    else:
                        self.state = states.NEGOTIATING
            elif: self.state == states.NEGOTIATING:
                if "\r\n\r\n" in self.buf:
                    head, chaff, self.buf = self.buf.partition("\r\n")
                    self.headers = utils.httpHeaders(head)
                    self.negotiate()
            elif self.state == states.ROUTED:
                self.wrappedProtocol.dataRecieved(self.buf)
                self.buf = ""
    def negotiate(self):
        prefix, session, method = utils.parsePath(self.location)
        self.factory = self.factory.resolvePrefix(prefix)
        if self.factory is None:
            self.loseConnection()
            return
        self.wrappedProtocol = method(self)
            