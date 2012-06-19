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
from twisted.internet import reactor
from twisted.internet.protocol import Protocol
from twisted.protocols.policies import ProtocolWrapper
import json, Cookie, urllib

class SessionProtocol(ProtocolWrapper):
    allowedMethods = ['OPTIONS']
    contentType = 'text/plain; charset=UTF-8'
    writeOnly = False
    chunked = True
    disconnecting = True
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
            self.transport.write("\r\n")
            self.transport.loseConnection()
            return
        elif self.method == 'OPTIONS':
            self.sendHeaders()
            self.transport.write("")
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
                    self.disconnecting = False
                    self.wrappedProtocol.makeConnection(self)
        else:
            if self.session in self.factory.sessions:
                self.wrappedProtocol = self.factory.sessions[self.session]
            else:
                self.sendHeaders({'status': '404 Not Found'})
                self.transport.write("\r\n")
                self.transport.loseConnection()
    def connectionLost(self, reason):
        if not self.writeOnly and self.wrappedProtocol:
            self.wrappedProtocol.connectionLost(reason)
        if not self.writeOnly and not self.disconnecting and self.wrappedProtocol:
            self.wrappedProtocol.disconnect()
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
        if self.chunked and not self.writeOnly and self.version == 'HTTP/1.1' and self.method != 'OPTIONS':
            headers['transfer-encoding'] = 'chunked'
        if 'Access-Control-Request-Headers' in self.headers and self.headers['Access-Control-Request-Headers']:
            headers['Access-Control-Allow-Headers'] = self.headers['Access-Control-Request-Headers']
        if self.method == 'OPTIONS':
            headers.update({
                'status': '204 No Body',
                'Cache-Control': 'public, max-age=31536000',
                'access-control-max-age': '31536000',
                'Access-Control-Allow-Methods': ', '.join(self.allowedMethods),
                'Expires': 'Fri, 01 Jan 2500 00:00:00 GMT' #Get a new library by then
            })
        elif self.factory.options['cookie_needed']:
            c = Cookie.SimpleCookie()
            c['JSESSIONID'] = 'dummy'
            if 'Cookie' in self.headers:
                c.load(self.headers['Cookie'])
            c['JSESSIONID']['path'] = '/'
            headers.update({'Set-Cookie':c['JSESSIONID'].OutputString()})
        headers.update(h)
        h = ''
        if 'status' in headers:
            h += "HTTP/1.1 %s\r\n" % headers['status']
            print "HTTP/1.1 %s %s" % (headers['status'], self.location)
            del headers['status']
        for k, v in headers.iteritems():
            h += "%s: %s\r\n" % (k, v)
        self.transport.write(h + "\r\n")
    def write(self, data):
        if not self.chunked or self.writeOnly or self.version != 'HTTP/1.1':
            self.transport.write(data)
        else:
            #print "SENDING CHUNKED DATA - LEN = %d" % len(data)
            self.transport.write("%X\r\n%s\r\n" % (len(data), data))
    def loseConnection(self):
        if self.chunked and not self.writeOnly and self.version == 'HTTP/1.1':
            self.transport.write('0\r\n\r\n')
        self.disconnecting = True
        self.transport.loseConnection()
    def dataReceived(self, data):
        if not self.wrappedProtocol or not self.writeOnly:
            return
        self.buf += data
        if 'Content-Length' in self.headers and len(self.buf) < int(self.headers['Content-Length']):
            return
        ret = self.wrappedProtocol.dataReceived(self.buf)
        self.buf = ""
        if ret:
            print ret
            ret += "\r\n"
            self.sendHeaders({'status':'500 Internal Server Error','Content-Length':str(len(ret))})
            self.transport.write(ret)
        else:
            self.sendBody()
        self.loseConnection()
    def sendBody(self):
        self.sendHeaders()
        
class RelayProtocol(ProtocolWrapper):
    def __init__(self, factory, protocol, session):
        self.session = session
        self.wrappedProtocol = protocol
        self.factory = factory
        self.transport = None
        self.pending = []
        self.buffer = []
        self.attached = False
        self.connecting = True
        self.disconnecting = False
        
        self.factory.registerProtocol(self)
        self.wrappedProtocol.makeConnection(self)
        reactor.callLater(self.factory.options['heartbeat'], self.heartbeat)
        self.timeout = reactor.callLater(self.factory.options['timeout'], self.disconnect)
    def heartbeat(self):
        self.pending.append('h')
        reactor.callLater(self.factory.options['heartbeat'], self.heartbeat)
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        self.attached = True
        if self.timeout.active():
            self.timeout.cancel()
        self.sendData()
    def loseConnection(self):
        self.disconnecting = True
        self.sendData()
    def disconnect(self):
        self.wrappedProtocol.connectionLost(None)
        self.factory.unregisterProtocol(self)
    def connectionLost(self, reason):
        self.transport = None
        self.attached = False
        self.timeout = reactor.callLater(self.factory.options['timeout'], self.disconnect)
    def write(self, data):
        self.buffer.append(data)
        self.sendData()
    def writeSequence(self, data):
        self.buffer.extend(data)
        self.sendData()
    def sendData(self):
        if self.transport:
            if self.connecting:
                self.transport.write('o')
                self.connecting = False
                self.sendData()
            elif self.disconnecting:
                self.transport.write('c[3000,"Go away!"]')
                self.transport.loseConnection()
            else:
                self.flushData()
                if self.pending:
                    self.transport.writeSequence(self.pending)
                    self.pending = []
    def flushData(self):
        if self.buffer:
            data = 'a'+json.dumps(self.buffer, separators=(',',':'))
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
                self.wrappedProtocol.dataReceived(p)
            return None
        except ValueError:
            return "Broken JSON encoding."
