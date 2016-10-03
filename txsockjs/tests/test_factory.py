#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.internet.defer import inlineCallbacks
from twisted.web.resource import NoResource
from txsockjs.factory import SockJSFactory, SockJSResource
from txsockjs.protocols.eventsource import EventSource
from txsockjs.protocols.htmlfile import HTMLFile
from txsockjs.protocols.jsonp import JSONP, JSONPSend
from txsockjs.protocols.static import Info, IFrame
from txsockjs.protocols.websocket import RawWebSocket, WebSocket
from txsockjs.protocols.xhr import XHR, XHRSend, XHRStream
from .common import EchoFactory, Request, BaseUnitTest

class FactoryUnitTest(BaseUnitTest):
    valid_sessions = (
        [b'a', b'a'],
        [b'_', b'_'],
        [b'1', b'1'],
        [b'abcdefgh_i-j%20', b'abcdefgh_i-j%20'],
    )
    invalid_sessions = (
        [b'', b''],
        [b'a.', b'a'],
        [b'a', b'a.'],
        [b'.', b'.'],
        [b''],
        [b'', b'', b''],
    )
    
    def setUp(self):
        self.site = SockJSFactory(EchoFactory())
    
    def _test(self, path, resource):
        req = Request(b"OPTIONS", path)
        # Also tests that OPTIONS requests don't produce upstream connections
        res = self.site.getResourceFor(req)
        self.assertTrue(isinstance(res, resource))
    
    def _test_wrapper(self, path, resource):
        for s in self.valid_sessions:
            self._test(s + [path], resource)
            self._test(s + [path, b''], NoResource)
        for s in self.invalid_sessions:
            self._test(s + [path], NoResource)
            self._test(s + [path, b''], NoResource)
    
    def test_greeting(self):
        self._test([], SockJSResource)
        self._test([b''], SockJSResource)
    
    def test_info(self):
        self._test([b'info'], Info)
        self._test([b'info', b''], NoResource)
    
    def test_iframe(self):
        self._test([b'iframe.html'], IFrame)
        self._test([b'iframe-a.html'], IFrame)
        self._test([b'iframe-.html'], IFrame)
        self._test([b'iframe-0.1.2.html'], IFrame)
        self._test([b'iframe-0.1.2abc-dirty.2144.html'], IFrame)
        self._test([b'iframe.htm'], NoResource)
        self._test([b'iframe'], NoResource)
        self._test([b'IFRAME.HTML'], NoResource)
        self._test([b'IFRAME'], NoResource)
        self._test([b'iframe.HTML'], NoResource)
        self._test([b'iframe.xml'], NoResource)
        self._test([b'iframe-', b'.html'], NoResource)
    
    def test_rawwebsocket(self):
        self._test([b'websocket'], RawWebSocket)
        self._test([b'websocket', b''], RawWebSocket)
    
    def test_websocket(self):
        self._test_wrapper(b'websocket', WebSocket)
    
    def test_eventsource(self):
        self._test_wrapper(b'eventsource', EventSource)
    
    def test_htmlfile(self):
        self._test_wrapper(b'htmlfile', HTMLFile)
    
    def test_xhr_stream(self):
        self._test_wrapper(b'xhr_streaming', XHRStream)
    
    def test_xhr(self):
        self._test_wrapper(b'xhr', XHR)
    
    def test_jsonp(self):
        self._test_wrapper(b'jsonp', JSONP)
    
    def test_xhr_send(self):
        self._test_wrapper(b'xhr_send', XHRSend)
    
    def test_jsonp_send(self):
        self._test_wrapper(b'jsonp_send', JSONPSend)
    
    def test_invalid_endpoint(self):
        self._test([b'a', b'a', b'a'], NoResource)
    
    def test_nonexistent_session_write(self):
        req = Request(b"POST", [b'a', b'a', b'xhr_send'])
        res = self.site.getResourceFor(req)
        self.assertTrue(isinstance(res, NoResource))

    @inlineCallbacks
    def test_ignore_server_id(self):
        # Open session
        req = Request(b"POST", [b'000', b'a', b'xhr'])
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        self.assertEqual(req.value(), b'o\n')
        # Write data to session
        req = Request(b"POST", [b'000', b'a', b'xhr_send'])
        req.writeContent(b'["a"]')
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        # Ensure it appears despite different Server ID
        req = Request(b"POST", [b'999', b'a', b'xhr'])
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        self.assertEqual(req.value(), b'a["a"]\n')
        # Clean up
        for p in list(self.site.resource._sessions.values()):
            p.disconnect()
