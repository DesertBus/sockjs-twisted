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

# Copyright (c) 2011 Oregon State University Open Source Lab
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN
# NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
# DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
# USE OR OTHER DEALINGS IN THE SOFTWARE.

from hashlib import md5, sha1
from string import digits
from struct import pack, unpack
from base64 import b64encode, b64decode
from twisted.internet.interfaces import ISSLTransport
from twisted.web.http import datetimeToString
from twisted.protocols.policies import ProtocolWrapper
from zope.interface import directlyProvides, providedBy
from twisted.internet.protocol import Protocol
from txsockjs.protocols.base import normalize

REQUEST, CHALLENGE, FRAMES = range(3)
HIXIE75, HYBI00, HYBI07, HYBI10, RFC6455 = range(5)
NORMAL, CLOSE, PING, PONG = range(4)
encoders = {
    "base64": b64encode,
}
decoders = {
    "base64": b64decode,
}
opcodes = {
    0x0: NORMAL,
    0x1: NORMAL,
    0x2: NORMAL,
    0x8: CLOSE,
    0x9: PING,
    0xA: PONG,
}
types = {
    HIXIE75: "HIXIE75",
    HYBI00: "HYBI00",
    HYBI07: "HYBI07",
    HYBI10: "HYBI10",
    RFC6455: "RFC6455"
}

class RawWebSocket(ProtocolWrapper):
    allowedMethods = ['GET']
    buf = ""
    host = 'example.com'
    origin = 'http://example.com'
    codec = None
    flavor = None
    state = REQUEST
    def __init__(self, parent):
        self.method = parent.method
        self.headers = parent.headers
        self.session = parent.session
        self.location = parent.location
        self.factory = parent.factory
        self.transport = parent
        self.wrappedProtocol = None
        self.pendingFrames = []
        if self.validateHeaders():
            self.wrappedProtocol = self.factory.wrappedFactory.buildProtocol(self.transport.addr)
    def getType(self):
        if self.flavor in types:
            return types[self.flavor]
        return None
    def prepConnection(self):
        pass
    def makeConnection(self, transport):
        directlyProvides(self, providedBy(transport))
        Protocol.makeConnection(self, transport)
        if self.wrappedProtocol:
            self.prepConnection()
            self.wrappedProtocol.makeConnection(self)
        else:
            self.failConnect()
    def failConnect(self):
        self.transport.loseConnection()
    def loseConnection(self):
        self.close()
    def connectionLost(self, reason):
        if self.wrappedProtocol:
            self.wrappedProtocol.connectionLost(reason)
    def relayData(self, data):
        data = normalize(data, self.factory.options['encoding'])
        self.wrappedProtocol.dataReceived(data)
    def isWebsocket(self):
        return ("Upgrade" in self.headers.get("Connection", "") and self.headers.get("Upgrade").lower() == "websocket")
    def isSecure(self):
        return ISSLTransport(self.transport, None) is not None
    def isHixie75(self):
        return "Sec-WebSocket-Version" not in self.headers and "Sec-WebSocket-Key1" not in self.headers and "Sec-WebSocket-Key2" not in self.headers
    def isHybi00(self):
        return "Sec-WebSocket-Key1" in self.headers and "Sec-WebSocket-Key2" in self.headers
    def validateHeaders(self):
        if not self.method in self.allowedMethods:
            return False
        if not self.isWebsocket():
            return False
        if "Host" in self.headers:
            self.host = self.headers["Host"]
        if "Origin" in self.headers:
            self.origin = self.headers["Origin"]
        protocol = None
        if "WebSocket-Protocol" in self.headers:
            protocol = self.headers["WebSocket-Protocol"]
        elif "Sec-WebSocket-Protocol" in self.headers:
            protocol = self.headers["Sec-WebSocket-Protocol"]
        if protocol:
            if protocol not in encoders or protocol not in decoders:
                return False
            self.codec = protocol
        if self.isHixie75():
            self.flavor = HIXIE75
            self.state = FRAMES
            protocol = "wss" if self.isSecure() else "ws"
            self.sendHeaders({
                'WebSocket-Origin': self.origin,
                'WebSocket-Location': '%s://%s%s' % (protocol, self.host, self.location),
                'WebSocket-Protocol': self.codec
            })
        elif self.isHybi00():
            self.flavor = HYBI00
            self.state = CHALLENGE
            protocol = "wss" if self.isSecure() else "ws"
            self.sendHeaders({
                'Sec-WebSocket-Origin': self.origin,
                'Sec-WebSocket-Location': '%s://%s%s' % (protocol, self.host, self.location),
                'Sec-WebSocket-Protocol': self.codec
            })
        elif "Sec-WebSocket-Version" in self.headers:
            version = self.headers["Sec-WebSocket-Version"]
            if version == "7":
                self.flavor = HYBI07
            elif version == "8":
                self.flavor = HYBI10
            elif version == "13":
                self.flavor = RFC6455
            else:
                return False
            self.state = FRAMES
            key = self.headers["Sec-WebSocket-Key"]
            guid = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            accept = sha1("%s%s" % (key, guid)).digest().encode("base64").strip()
            self.sendHeaders({"Sec-WebSocket-Accept":accept})
        else:
            return False
        return True
    def sendHeaders(self, headers = {}):
        h = {
            'status': '101 FYI I am not a webserver',
            'Server': 'SockJSTwisted/1.0',
            'Date': datetimeToString(),
            'Upgrade': 'WebSocket',
            'Connection': 'Upgrade'
        }
        h.update(headers)
        headers = ""
        if 'status' in h:
            headers += "HTTP/1.1 %s\r\n" % h['status']
            del h['status']
        for k, v in h.iteritems():
            headers += "%s: %s\r\n" % (k, v)
        self.transport.write(headers + "\r\n")
    def sendFrames(self):
        if self.state != FRAMES:
            return
        if self.flavor in (HIXIE75, HYBI00):
            maker = self.makeHybi00Frame
        elif self.flavor in (HYBI07, HYBI10, RFC6455):
            maker = self.makeHybi07Frame
        else:
            raise Exception("Unknown flavor %r" % self.flavor)
        for frame in self.pendingFrames:
            if self.codec:
                frame = encoders[self.codec](frame)
            packet = maker(frame)
            self.transport.write(packet)
        self.pendingFrames = []
    def parseFrames(self):
        if self.flavor in (HIXIE75, HYBI00):
            parser = self.parseHybi00Frame
        elif self.flavor in (HYBI07, HYBI10, RFC6455):
            parser = self.parseHybi07Frame
        else:
            raise Exception("Unknown flavor %r" % self.flavor)
        try:
            frames = parser()
        except:
            self.close()
            return
        for frame in frames:
            opcode, data = frame
            if opcode == NORMAL:
                if self.codec:
                    data = decoders[self.codec](data)
                self.relayData(data)
            elif opcode == CLOSE:
                self.close()
    def dataReceived(self, data):
        self.buf += data
        oldstate = None
        while oldstate != self.state:
            oldstate = self.state
            if self.state == CHALLENGE and len(self.buf) >= 8:
                challenge, self.buf = self.buf[:8], self.buf[8:]
                key1 = self.headers["Sec-WebSocket-Key1"]
                key2 = self.headers["Sec-WebSocket-Key2"]
                first = int("".join(i for i in key1 if i in digits)) / key1.count(" ")
                second = int("".join(i for i in key2 if i in digits)) / key2.count(" ")
                nonce = md5(pack(">II8s", first, second, challenge)).digest()
                self.transport.write(nonce)
                self.state = FRAMES
            elif self.state == FRAMES:
                self.parseFrames()
        if self.pendingFrames:
            self.sendFrames()
    def write(self, data):
        self.pendingFrames.append(data)
        self.sendFrames()
    def writeSequence(self, data):
        self.pendingFrames.extend(data)
        self.sendFrames()
    def close(self, reason=""):
        if self.flavor in (HYBI07, HYBI10, RFC6455):
            frame = self.makeHybi07Frame(reason, opcode=0x8)
            self.transport.write(frame)
        self.transport.loseConnection()
    def makeHybi00Frame(self, data):
        return "\x00%s\xFF" % data
    def makeHybi07Frame(self, data, opcode = 0x1):
        if len(data) > 0xFFFF:
            length = "\x7f%s" % pack(">Q", len(data))
        elif len(data) > 0x7D:
            length = "\x7e%s" % pack(">H", len(data))
        else:
            length = chr(len(data))
        header = chr(0x80 | opcode)
        frame = "%s%s%s" % (header, length, data)
        return frame
    def parseHybi00Frame(self):
        start = self.buf.find("\x00")
        tail = 0
        frames = []
        while start != -1:
            end = self.buf.find("\xFF",start+1)
            if end == -1:
                break
            frame = self.buf[start+1:end]
            frames.append((NORMAL, frame))
            tail = end + 1
            start = self.buf.find("\x00", tail)
        self.buf = self.buf[tail:]
        return frames
    def parseHybi07Frame(self):
        start = 0
        frames = []
        while True:
            if len(self.buf) - start < 2:
                break
            header = ord(self.buf[start])
            if header & 0x70:
                raise Exception("Reserved flag in HyBi-07 frame (%d)" % header)
            opcode = header & 0xF
            try:
                opcode = opcodes[opcode]
            except KeyError:
                raise Exception("Unknown opcode %d in HyBi-07 frame" % opcode)
            length = ord(self.buf[start+1])
            masked = length & 0x80
            length &= 0x7F
            offset = 2
            if length == 0x7E:
                if len(self.buf) - start < 4:
                    break
                length = self.buf[start+2:start+4]
                length = unpack(">H", length)[0]
                offset += 2
            elif length == 0x7F:
                if len(self.buf) - start < 10:
                    break
                length = self.buf[start+2:start+10]
                length = unpack(">Q", length)[0]
                offset += 8
            if masked:
                if len(self.buf) - (start+offset) < 4:
                    break
                key = self.buf[start+offset:start+offset+4]
                offset += 4
            if len(self.buf) - (start+offset) < length:
                break
            data = self.buf[start+offset:start+offset+length]
            if masked:
                key = [ord(i) for i in key]
                data = list(data)
                for i, char in enumerate(data):
                    data[i] = chr(ord(char) ^ key[i%4])
                data = "".join(data)
            if opcode == CLOSE:
                if len(data) >= 2:
                    data = unpack(">H", data[:2])[0], data[2:]
                else:
                    data = 1000, "No reason given"
            frames.append((opcode,data))
            start += offset + length
        self.buf = self.buf[start:]
        return frames
