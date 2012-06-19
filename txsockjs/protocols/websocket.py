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

import json
from txsockjs.protocols.rawwebsocket import RawWebSocket

class WebSocket(RawWebSocket):
    def write(self, data):
        RawWebSocket.write(self, "a"+json.dumps([data]))
    def writeSequence(self, data):
        RawWebSocket.write(self, "a"+json.dumps(data))
    def relayData(self, data):
        if data == '':
            return
        try:
            #print "%s >>> %s" % (self.getType(), data)
            packets = json.loads(data)
            for p in packets:
                RawWebSocket.relayData(self,p)
        except ValueError:
            RawWebSocket.close(self)
    def prepConnection(self):
        RawWebSocket.write(self,"o")
    def failConnect(self):
        if not self.method in self.allowedMethods:
            self.sendHeaders({
                'status': '405 Method Not Allowed',
                'Allow': ', '.join(self.allowedMethods)
            })
            self.transport.write("\r\n")
        elif not self.headers.get("Upgrade","").lower() == "websocket":
            self.sendHeaders({'status':'400 Bad Request'})
            self.transport.write('Can "Upgrade" only to "WebSocket".'+"\r\n")
        elif not "Upgrade" in self.headers.get("Connection", ""):
            self.sendHeaders({'status':'400 Bad Request'})
            self.transport.write('Can "Upgrade" only to "WebSocket".'+"\r\n")
        self.transport.loseConnection()
    def close(self, code = 3000, reason = "Go away!"):
        RawWebSocket.write(self,'c[%d,"%s"]' % (code, reason))
        RawWebSocket.close(self)