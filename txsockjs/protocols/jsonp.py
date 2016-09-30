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

from twisted.web import http
from txsockjs.protocols.base import StubResource

class JSONP(StubResource):
    written = False
    
    def render_GET(self, request):
        self.parent.setBaseHeaders(request)
        self.callback = request.args.get('c',[None])[0]
        if self.callback is None:
            request.setResponseCode(http.INTERNAL_SERVER_ERROR)
            return '"callback" parameter required'
        request.setHeader(b'content-type', b'application/javascript; charset=UTF-8')
        return self.connect(request)
    
    def write(self, data):
        if self.written:
            self.session.requeue([data])
            return
        self.written = True
        content = "/**/{0}(\"{1}\");\r\n".format(self.callback, data.replace('\\','\\\\').replace('"','\\"'))
        self.request.write(content.encode('utf-8'))
        self.disconnect()
    
    def writeSequence(self, data):
        self.write(data.pop(0))
        self.session.requeue(data)

class JSONPSend(StubResource):
    def render_POST(self, request):
        self.parent.setBaseHeaders(request)
        request.setHeader(b'content-type', b'text/plain; charset=UTF-8')
        urlencoded = request.getHeader(b"Content-Type") == b'application/x-www-form-urlencoded'
        data = request.args.get('d', [b''])[0] if urlencoded else request.content.read()
        ret = self.session.dataReceived(data)
        if not ret:
            return b"ok"
        request.setResponseCode(http.INTERNAL_SERVER_ERROR)
        return ret + b"\r\n"
