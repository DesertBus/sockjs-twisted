#!/usr/bin/env python
# -*- coding: utf-8 -*-

from six import PY2
from twisted.trial import unittest
from txsockjs import utils

class MockTransport(object):
    value = b""
    def writeRaw(self, data):
        self.value += data


class UtilsTestCase(unittest.TestCase):
    encoding = "cp1252"
    def test_normalize(self):
        for s in [
                b"Hello!",
                u"こんにちは！",
                ("Hello!", u"こんにちは！"),
                {"Hello!": u"こんにちは！"}]:
            n = utils.normalize(s, self.encoding)
            self.assertTrue(isinstance(n, str))
            if PY2:
                self.assertEqual(
                    n, n.decode('utf-8', 'ignore').encode('utf-8', 'ignore'))

    def test_broadcast(self):
        targets = [MockTransport(), MockTransport(), MockTransport()]
        utils.broadcast("Hello!", targets, self.encoding)
        for t in targets:
            self.assertEqual(t.value, b'a["Hello!"]')
