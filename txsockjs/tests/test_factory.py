#!/usr/bin/env python
# -*- coding: utf-8 -*-

from twisted.web.resource import NoResource
from txsockjs.factory import SockJSFactory, SockJSResource
from txsockjs.protocols.eventsource import EventSource
from txsockjs.protocols.htmlfile import HTMLFile
from txsockjs.protocols.jsonp import JSONP, JSONPSend
from txsockjs.protocols.static import Info, IFrame
from txsockjs.protocols.websocket import RawWebSocket, WebSocket
from txsockjs.protocols.xhr import XHR, XHRSend, XHRStream
from tests.common import EchoFactory, Request, BaseUnitTest

class FactoryUnitTest(BaseUnitTest):
    valid_sessions = (['a','a'],['_','_'],['1','1'],['abcdefgh_i-j%20','abcdefgh_i-j%20'])
    invalid_sessions = (['',''],['a.','a'],['a','a.'],['.','.'],[''],['','',''])
    
    def setUp(self):
        self.site = SockJSFactory(EchoFactory())
    
    def _test(self, path, resource):
        req = Request("OPTIONS", path)
        # Also tests that OPTIONS requests don't produce upstream connections
        res = self.site.getResourceFor(req)
        self.assertTrue(isinstance(res, resource))
    
    def _test_wrapper(self, path, resource):
        for s in self.valid_sessions:
            self._test(s + [path], resource)
            self._test(s + [path,''], NoResource)
        for s in self.invalid_sessions:
            self._test(s + [path], NoResource)
            self._test(s + [path,''], NoResource)
    
    def test_greeting(self):
        self._test([], SockJSResource)
        self._test([''], SockJSResource)
    
    def test_info(self):
        self._test(['info'], Info)
        self._test(['info',''], NoResource)
    
    def test_iframe(self):
        self._test(['iframe.html'], IFrame)
        self._test(['iframe-a.html'], IFrame)
        self._test(['iframe-.html'], IFrame)
        self._test(['iframe-0.1.2.html'], IFrame)
        self._test(['iframe-0.1.2abc-dirty.2144.html'], IFrame)
        self._test(['iframe.htm'], NoResource)
        self._test(['iframe'], NoResource)
        self._test(['IFRAME.HTML'], NoResource)
        self._test(['IFRAME'], NoResource)
        self._test(['iframe.HTML'], NoResource)
        self._test(['iframe.xml'], NoResource)
        self._test(['iframe-','.html'], NoResource)
    
    def test_rawwebsocket(self):
        self._test(['websocket'], RawWebSocket)
        self._test(['websocket',''], RawWebSocket)
    
    def test_websocket(self):
        self._test_wrapper('websocket', WebSocket)
    
    def test_eventsource(self):
        self._test_wrapper('eventsource', EventSource)
    
    def test_htmlfile(self):
        self._test_wrapper('htmlfile', HTMLFile)
    
    def test_xhr_stream(self):
        self._test_wrapper('xhr_streaming', XHRStream)
    
    def test_xhr(self):
        self._test_wrapper('xhr', XHR)
    
    def test_jsonp(self):
        self._test_wrapper('jsonp', JSONP)
    
    def test_xhr_send(self):
        self._test_wrapper('xhr_send', XHRSend)
    
    def test_jsonp_send(self):
        self._test_wrapper('jsonp_send', JSONPSend)
    
    def test_invalid_endpoint(self):
        self._test(['a','a','a'], NoResource)
    
    def test_nonexistant_session_write(self):
        req = Request("POST", ['a','a','xhr_send'])
        res = self.site.getResourceFor(req)
        self.assertTrue(isinstance(res, NoResource))
    
    def test_ignore_server_id(self):
        # Open session
        req = Request("POST", ['000','a','xhr'])
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        self.assertEqual(req.value(), 'o\n')
        # Write data to session
        req = Request("POST", ['000','a','xhr_send'])
        req.writeContent('["a"]')
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        # Ensure it appears despite different Server ID
        req = Request("POST", ['999','a','xhr'])
        res = self.site.getResourceFor(req)
        yield self._render(res, req)
        self.assertEqual(req.value(), 'a["a"]\n')
        # Clean up
        for p in self.site.resource._sessions.values():
            p.disconnect()
