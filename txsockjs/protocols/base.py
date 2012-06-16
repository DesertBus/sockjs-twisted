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
import json

class SessionProtocol(ProtocolWrapper):
    allowedMethods = ['OPTIONS']
    contentType = 'text/plain; charset=UTF-8'
    writeOnly = False
    chunked = True
    def __init__(self, parent):
        self.method = parent.method
        self.headers = parent.headers
        self.session = parent.session
        self.location = parent.location
        self.query = parent.query
        self.version = parent.version
        self.factory = parent.factory
        self.buf = ""
        self.transport = parent
        self.wrappedProtocol = None
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        
        if not self.method in self.allowedMethods:
            self.sendHeaders({'status': '405 Method Not Supported','allow': ', '.join(self.allowedMethods)})
            self.transport.loseConnection()
            return
        elif self.method == 'OPTIONS':
            self.sendHeaders()
            self.transport.loseConnection()
            return
        
        if not self.writeOnly:
            if self.session in self.factory.sessions:
                self.wrappedProtocol = self.factory.sessions[self.session]
            else:
                self.wrappedProtocol = RelayProtocol(self.factory, self.factory.wrappedFactory.buildProtocol(self.transport.addr), self.session)
            
            if self.wrappedProtocol.attached:
                self.wrappedProtocol = None
                self.failConnect()
            else:
                if not self.prepConnection():
                    self.wrappedProtocol.makeConnection(self)
        else:
            if self.session in self.factory.sessions:
                self.wrappedProtocol = self.factory.sessions[self.session]
            else:
                self.sendHeaders({'status': '404 Not Found'})
                self.transport.loseConnection()
    def connectionLost(self, reason):
        if not self.writeOnly and self.wrappedProtocol:
            self.wrappedProtocol.connectionLost(reason)
    def prepConnection(self):
        self.sendHeaders()
    def failConnect(self):
        self.prepConnection()
        self.write('c[2010,"Another connection still open"]')
        self.loseConnection()
    def sendHeaders(self, h = {}):
        if 'Origin' in self.headers and self.headers['Origin'] != 'null':
            origin = self.headers['Origin']
        else:
            origin = '*'
        headers = {
            'status': '200 OK',
            'content-type': self.contentType,
            'access-control-allow-origin': origin,
            'access-control-allow-credentials': 'true',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
            'Connection': 'close'
        }
        if self.chunked and not self.writeOnly and self.version == 'HTTP/1.1':
            headers['transfer-encoding'] = 'chunked'
        if 'Access-Control-Request-Headers' in self.headers and self.headers['Access-Control-Request-Headers']:
            headers['Access-Control-Allow-Headers'] = self.headers['Access-Control-Request-Headers']
        if self.method == 'OPTIONS':
            headers.update({
                'status': '204 No Body',
                'Cache-Control': 'public, max-age=31536000',
                'access-control-max-age': '31536000',
                'Access-Control-Allow-Methods': ', '.join(self.allowedMethods)
            })
        elif self.factory.options['cookie_needed']:
            cookie = 'JSESSIONID=dummy;path=/;' if 'Cookie' not in self.headers else self.headers['Cookie']
            headers.update({'Set-Cookie':cookie})
        headers.update(h)
        h = ''
        if 'status' in headers:
            h += "HTTP/1.1 %s\r\n" % headers['status']
            del headers['status']
        for k, v in headers.iteritems():
            h += "%s: %s\r\n" % (k, v)
        self.transport.write(h + "\r\n")
    def write(self, data):
        if not self.chunked or self.writeOnly or self.version != 'HTTP/1.1':
            self.transport.write(data)
        else:
            self.transport.write("%X\r\n%s\r\n" % (len(data), data))
    def loseConnection(self):
        if self.chunked and not self.writeOnly and self.version == 'HTTP/1.1':
            self.write('')
        self.transport.loseConnection()
    def dataReceived(self, data):
        if not self.wrappedProtocol or not self.writeOnly:
            return
        self.buf += data
        if 'Content-Length' in self.headers and len(self.buf) < int(self.headers['Content-Length']):
            return
        ret = self.wrappedProtocol.dataReceived(data)
        if ret:
            self.sendHeaders({'status':'500 Internal Server Error'})
            self.write(ret)
        else:
            self.sendHeaders()
            self.sendBody()
        self.loseConnection()
    def sendBody(self):
        pass
        
class RelayProtocol(ProtocolWrapper):
    def __init__(self, factory, protocol, session):
        self.session = session
        self.wrappedProtocol = protocol
        self.factory = factory
        self.transport = None
        self.pending = ['o']
        self.attached = False
        self.disconnecting = False
        self.factory.registerProtocol(self)
        self.wrappedProtocol.makeConnection(self)
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.attached = True
        if self.pending:
            self.transport.writeSequence(self.pending)
            self.pending = []
        if self.disconnecting:
            self.loseConnection()
    def loseConnection(self):
        self.disconnecting = True
        if self.transport:
            self.transport.write('c[3000,"Go away!"]')
            self.transport.loseConnection()
    def connectionLost(self, reason):
        self.transport = None
        self.attached = False
    def write(self, data):
        self.writeSequence([data])
    def writeSequence(self, data):
        data = 'a'+json.dumps(data)
        if self.transport:
            self.transport.write(data)
        else:
            self.pending.append(data)
    def dataReceived(self, data):
        if data == '':
            return "Payload expected."
        try:
            packets = json.loads(data)
            for p in packets:
                self.wrappedProtocol.dataReceived(p)
            return None
        except ValueError:
            return "Broken JSON encoding."
