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

from twisted.protocols.policies import WrappingFactory
from twisted.internet.protocol import ClientFactory
from txsockjs.negotiator import SockJSNegotiator
from txsockjs.utils import validatePrefix

class SockJSFactory(WrappingFactory):
    options = None
    sessions = None
    routes = None
    protocol = SockJSNegotiator
    def __init__(self, factory, options = None):
        self.options = {
            'websocket': True,
            'cookie_needed': False,
            'heartbeat': 25,
            'timeout': 5,
            'streaming_limit': 128 * 1024
        }
        self.sessions = {}
        self.routes = {'':self}
        self.wrappedFactory = factory
        
        if options is not None:
            self.options.update(options)
    def buildProtocol(self, addr):
        return self.protocol(self, addr)
    def registerProtocol(self, p):
        self.sessions[p.session] = p
    def unregisterProtocol(self, p):
        del self.sessions[p.session]
    def resolvePrefix(self, prefix):
        return self

class SockJSMultiFactory(ClientFactory):
    routes = None
    protocol = SockJSNegotiator
    def __init__(self):
        self.routes = {}
    def doStop(self):
        for factory in self.routes.itervalues():
            factory.doStop()
        ClientFactory.doStop(self)
    def buildProtocol(self, addr):
        return self.protocol(self, addr)
    def addFactory(self, factory, prefix, options = None):
        if not validatePrefix(prefix):
            raise ValueError()
        self.routes[prefix] = SockJSFactory(factory, options)
    def resolvePrefix(self, prefix):
        if prefix in self.routes:
            return self.routes[prefix]
        return None
