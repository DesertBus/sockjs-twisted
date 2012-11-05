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
import json, random
from twisted.internet.protocol import Protocol


class Static(Protocol):
    def __init__(self,parent):
        self.parent = parent

    def makeConnection(self, transport):
        Protocol.makeConnection(self, transport)
        self.send()

    def validateMethod(self):
        for method in self.allowedMethods:
            if self.parent.method == method:
                return True
        return False

    def send(self):
        if not self.validateMethod():
            h = {
                'status': '405 Method Not Supported',
                'allow': ', '.join(self.allowedMethods)
            }
            self.sendHeaders(h)
            self.transport.loseConnection()
            return False
        return True

    def sendHeaders(self, headers=None):
        headers = headers or {}
        if 'Origin' in self.parent.headers and self.parent.headers['Origin'] != 'null':
            origin = self.parent.headers['Origin']
        else:
            origin = '*'
        h = {
            'status': '200 OK',
            'access-control-allow-origin': origin,
            'access-control-allow-credentials': 'true',
            'Connection': 'close'
        }
        h.update(headers)
        if self.parent.method == 'OPTIONS':
            h.update({
                'status': '204 No Body',
                'Cache-Control': 'public, max-age=31536000',
                'access-control-max-age': '31536000',
                'Access-Control-Allow-Methods': ', '.join(self.allowedMethods),
                'Expires': 'Fri, 01 Jan 2500 00:00:00 GMT' #Get a new library by then
            })
        headers = ""
        if 'status' in h:
            headers += "HTTP/1.1 %s\r\n" % h['status']
            del h['status']
        for k, v in h.iteritems():
            headers += "%s: %s\r\n" % (k, v)
        self.transport.write(headers + "\r\n")

    def sendBody(self, body):
        self.transport.write(body)
        self.transport.loseConnection()

    def sendDocument(self, body, headers=None):
        headers = dict(((key.lower(), value) for key, value in (headers or {}).items()))
        headers['content-length'] = len(body)
        self.sendHeaders(headers)
        self.sendBody(body)
        

class Greeting(Static):
    allowedMethods = ['GET']

    def send(self):
        if not Static.send(self):
            return
        h = {
            'content-type': 'text/plain; charset=UTF-8',
            }
        self.sendDocument("Welcome to SockJS!\n", h)


class Info(Static):
    allowedMethods = ['OPTIONS','GET']

    def send(self):
        if not Static.send(self):
            return
        h = {
            'content-type': 'application/json; charset=UTF-8',
            'Cache-Control': 'no-store, no-cache, must-revalidate, max-age=0',
        }
        if self.parent.method == "OPTIONS":
            self.sendHeaders(h)
            self.transport.loseConnection()
            return
        b = {
            'websocket': self.parent.factory.options['websocket'],
            'cookie_needed': self.parent.factory.options['cookie_needed'],
            'origins': ['*:*'],
            'entropy': random.randint(0,2**32-1)
        }
        self.sendDocument(json.dumps(b), h)

class IFrame(Static):
    allowedMethods = ['GET']
    etag = '00000000-0000-0000-0000-000000000000'

    def send(self):
        if not Static.send(self):
            return
        if 'If-None-Match' in self.parent.headers and self.parent.headers['If-None-Match'].find(self.etag) >= 0: #Could result in false positives
            h = {'status': '304 Not Modified'}
            self.sendHeaders(h)
            self.transport.loseConnection()
            return
        h = {
            'Cache-Control': 'public, max-age=31536000',
            'Expires': 'January 1st, 3000',
            'ETag': self.etag,
            'content-type': 'text/html; charset=UTF-8',
        }
        self.sendDocument('''
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function(){SockJS.bootstrap_iframe();};
  </script>
  <script src="https://d1fxtkz8shb9d2.cloudfront.net/sockjs-0.3.js"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html>''', h)


class Error404(Static):
    def send(self):
        h = {
            'status': '404 Not Found',
        }
        self.sendDocument("Not Found", h)
        self.transport.loseConnection()
