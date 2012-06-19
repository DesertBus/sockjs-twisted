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

from txsockjs.protocols.base import SessionProtocol
from urlparse import parse_qs
from urllib import quote

class JSONP(SessionProtocol):
    allowedMethods = ['OPTIONS','GET']
    contentType = 'application/javascript; charset=UTF-8'
    chunked = False
    written = False
    def prepConnection(self):
        if not self.query or 'c' not in self.query:
            self.sendHeaders({'status': '500 Internal Server Error'})
            SessionProtocol.write(self, '"callback" parameter required')
            self.loseConnection()
            return True
        self.sendHeaders()
    def write(self, data):
        if self.written:
            self.wrappedProtocol.requeue([data])
            return
        packet = "%s(\"%s\");\r\n" % (self.query['c'][0], data.replace('"','\\"'))
        SessionProtocol.write(self, packet)
        self.written = True
        self.loseConnection()
    def writeSequence(self, data):
        self.write(data.pop(0))
        self.wrappedProtocol.requeue(data)

class JSONPSend(SessionProtocol):
    allowedMethods = ['OPTIONS','POST']
    contentType = 'text/plain; charset=UTF-8'
    writeOnly = True
    def sendBody(self):
        self.sendHeaders({'Content-Length':'2'})
        SessionProtocol.write(self, 'ok')
    def dataReceived(self, data):
        self.buf += data
        if 'Content-Length' in self.headers and len(self.buf) < int(self.headers['Content-Length']):
            return
        data = self.buf
        self.buf = ""
        del self.headers['Content-Length']
        if 'Content-Type' in self.headers and self.headers['Content-Type'] == 'application/x-www-form-urlencoded':
            query = parse_qs(data, True)
            data = query.get('d',[''])[0]
        SessionProtocol.dataReceived(self, data)
