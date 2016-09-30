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

from twisted.web import resource, http
from txsockjs.protocols.base import StubResource

class XHR(StubResource):
    written = False
    
    def render_POST(self, request):
        self.parent.setBaseHeaders(request)
        request.setHeader('content-type', 'application/javascript; charset=UTF-8')
        return self.connect(request)
    
    def write(self, data):
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        if self.written:
            self.session.requeue([data])
            return
        self.written = True
        self.request.write(data + b'\n')
        self.disconnect()
    
    def writeSequence(self, data):
        if not self.written:
            self.write(data.pop(0))
        self.session.requeue(data)

class XHRSend(StubResource):
    def render_POST(self, request):
        self.parent.setBaseHeaders(request)
        request.setResponseCode(http.NO_CONTENT)
        request.setHeader(b'content-type', b'text/plain; charset=UTF-8')
        ret = self.session.dataReceived(request.content.read())
        if not ret:
            return ""
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        return "{0}\r\n".format(ret)

class XHRStream(StubResource):
    sent = 0
    done = False
    
    def render_POST(self, request):
        self.parent.setBaseHeaders(request)
        request.setHeader(b'content-type', b'application/javascript; charset=UTF-8')
        request.write((b'h' * 2048) + b'\n')
        return self.connect(request)
    
    def write(self, data):
        if not isinstance(data, bytes):
            data = data.encode('utf-8')
        if self.done:
            self.session.requeue([data])
            return
        packet = data + b'\n'
        self.sent += len(packet)
        self.request.write(packet)
        if self.sent > self.parent._options['streaming_limit']:
            self.done = True
            self.disconnect()
    
    def writeSequence(self, data):
        for d in data:
            self.write(d)
