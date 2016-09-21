#!/usr/bin/env python
# -*- coding: utf-8 -*-

from six import BytesIO
from twisted.internet.protocol import Protocol, Factory
from twisted.trial import unittest
from twisted.web.test.test_web import DummyRequest
from twisted.test.proto_helpers import StringTransport
from twisted.internet.defer import succeed
from twisted.internet.defer import inlineCallbacks
from txsockjs.factory import SockJSFactory

class EchoProtocol(Protocol):
    def dataReceived(self, data):
        self.transport.write(data)

class EchoFactory(Factory):
    protocol = EchoProtocol

class Request(DummyRequest):
    def __init__(self, method, *args, **kwargs):
        DummyRequest.__init__(self, *args, **kwargs)
        self.method = method
        self.content = BytesIO()
        self.transport = StringTransport()
    
    def writeContent(self, data):
        if not isinstance(data, bytes):
            data = data.encode('ascii')
        self.content.seek(0,2) # Go to end of content
        self.content.write(data) # Write the data
        self.content.seek(0,0) # Go back to beginning of content
    
    def write(self, data):
        DummyRequest.write(self, data)
        self.transport.write(b"".join(self.written))
        self.written = []
    
    def value(self):
        return self.transport.value()

class BaseUnitTest(unittest.TestCase):
    path = ['']
    
    def setUp(self):
        self.site = SockJSFactory(EchoFactory())
        self.request = Request(self.path)
    
    @inlineCallbacks
    def _load(self):
        self.resource = self.site.getResourceFor(self.request)
        yield self._render(self.resource, self.request)
    
    def _render(resource, request):
        result = resource.render(request)
        if isinstance(result, str):
            request.write(result)
            request.finish()
            return succeed(None)
        elif result is server.NOT_DONE_YET:
            if request.finished:
                return succeed(None)
            else:
                return request.notifyFinish()
        else:
            raise ValueError("Unexpected return value: %r" % (result,))
