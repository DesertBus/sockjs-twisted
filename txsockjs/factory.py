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

from twisted.web import resource, server
from txsockjs.protocols.base import Stub
from txsockjs.protocols.eventsource import EventSource
from txsockjs.protocols.htmlfile import HTMLFile
from txsockjs.protocols.jsonp import JSONP, JSONPSend
from txsockjs.protocols.static import Info, IFrame
from txsockjs.protocols.websocket import RawWebSocket, WebSocket
from txsockjs.protocols.xhr import XHR, XHRSend, XHRStream

class SockJSFactory(server.Site):
    def __init__(self, factory, options = None):
        server.Site.__init__(self, SockJSResource(factory, options))

class SockJSMultiFactory(server.Site):
    def __init__(self):
        server.Site.__init__(self, resource.Resource())
    
    def addFactory(self, factory, prefix, options = None):
        self.resource.putChild(prefix, SockJSResource(factory, options))

class SockJSResource(resource.Resource):
    def __init__(self, factory, options = None):
        resource.Resource.__init__(self)
        self._factory = factory
        self._sessions = {}
        self._options = {
            'websocket': True,
            'cookie_needed': False,
            'heartbeat': 25,
            'timeout': 5,
            'streaming_limit': 128 * 1024,
            'encoding': 'latin-1',
            'sockjs_url': 'https://d1fxtkz8shb9d2.cloudfront.net/sockjs-0.3.js',
            'proxy_header': None
        }
        if options is not None:
            self._options.update(options)
        # Just in case somebody wants to mess with these
        self._methods = {
            b'xhr': XHR,
            b'xhr_send': XHRSend,
            b'xhr_streaming': XHRStream,
            b'eventsource': EventSource,
            b'htmlfile': HTMLFile,
            b'jsonp': JSONP,
            b'jsonp_send': JSONPSend,
        }
        self._writeMethods = (b'xhr_send', b'jsonp_send')
        # Static Resources
        self.putChild(b"info", Info())
        self.putChild(b"iframe.html", IFrame())
        self.putChild(b"websocket", RawWebSocket())
        # Since it's constant, we can declare the websocket handler up here
        self._websocket = WebSocket()
        self._websocket.parent = self
    
    def getChild(self, name, request):
        # Check if it is the greeting url
        if not name and not request.postpath:
            return self
        # Hacks to resove the iframe even when people are dumb
        if len(name) > 10 and name[:6] == b"iframe" and name[-5:] == b".html":
            return self.children[b"iframe.html"]
        # Sessions must have 3 parts, name is already the first. Also, no periods in the loadbalancer
        if len(request.postpath) != 2 or b"." in name or not name:
            return resource.NoResource("No such child resource.")
        # Extract session & request type. Discard load balancer
        session, name = request.postpath
        # No periods in the session
        if b"." in session or not session:
            return resource.NoResource("No such child resource.")
        # Websockets are a special case
        if name == b"websocket":
            return self._websocket
        # Reject invalid methods
        if name not in self._methods:
            return resource.NoResource("No such child resource.")
        # Reject writes to invalid sessions, unless just checking options
        if name in self._writeMethods and session not in self._sessions and request.method != b"OPTIONS":
            return resource.NoResource("No such child resource.")
        # Generate session if doesn't exist, unless just checking options
        if session not in self._sessions and request.method != b"OPTIONS":
            self._sessions[session] = Stub(self, session)
        # Delegate request to appropriate handler
        return self._methods[name](self, self._sessions[session] if request.method != b"OPTIONS" else None)
    
    def putChild(self, path, child):
        child.parent = self
        resource.Resource.putChild(self, path, child)
    
    def setBaseHeaders(self, request, cookie=True):
        origin = request.getHeader(b"Origin")
        headers = request.getHeader(b'Access-Control-Request-Headers')
        if origin is None or origin == b'null':
            origin = b"*"
        request.setHeader(b'access-control-allow-origin', origin)
        request.setHeader(b'access-control-allow-credentials', b'true')
        request.setHeader(b'Cache-Control', b'no-store, no-cache, must-revalidate, max-age=0')
        if headers is not None:
            request.setHeader(b'Access-Control-Allow-Headers', headers)
        if self._options["cookie_needed"] and cookie:
            cookie = request.getCookie(b"JSESSIONID") if request.getCookie(b"JSESSIONID") else b"dummy"
            request.addCookie(b"JSESSIONID", cookie, path=b"/")
    
    def render_GET(self, request):
        self.setBaseHeaders(request,False)
        request.setHeader(b'content-type', b'text/plain; charset=UTF-8')
        return b"Welcome to SockJS!\n"
