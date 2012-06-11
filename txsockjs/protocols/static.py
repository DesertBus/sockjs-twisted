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

class Static(Protocol):
    def sendHeaders(headers = {}):
        h = {
            'status': '200 OK',
            'Cache-Control': 'public, max-age=31536000',
            'access-control-max-age': '31536000',
            'Access-Control-Allow-Methods': ???,
            'access-control-allow-origin': origin ? origin : '*',
            'access-control-allow-credentials': 'true'
        }
        h.update(headers)
        
class Greeting(Static):
    def send(self):
        h = {
            'content-type': 'text/plain; charset=UTF-8',
        }
        self.sendHeaders(h)
        self.sendBody("Welcome to SockJS!\n")

class Info(Static):
    def send(self):
        h = {
            'content-type': 'text/plain; charset=UTF-8',
        }
        self.sendHeaders(h)
        self.sendBody()

class IFrame(Static):
    def send(self):
        h = {
            'Expires': 'January 1st, 3000',
            'ETag': '00000000-0000-0000-0000-000000000000',
            'content-type': 'text/html; charset=UTF-8',
        }
        self.sendHeaders(h)
        self.sendBody('''
<!DOCTYPE html>
<html>
<head>
  <meta http-equiv="X-UA-Compatible" content="IE=edge" />
  <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
  <script>
    document.domain = document.domain;
    _sockjs_onload = function(){SockJS.bootstrap_iframe();};
  </script>
  <script src="/sockjs.js"></script>
</head>
<body>
  <h2>Don't panic!</h2>
  <p>This is a SockJS hidden iframe. It's used for cross domain magic.</p>
</body>
</html
        ''')