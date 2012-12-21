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

from twisted.internet import reactor

# ============================================================================================================
# === THIS IS A MODIFIED COPY OF twisted.web.websockets TO BE COMPATIBLE WITH OLDER VERSIONS OF WEBSOCKETS ===
# === IT WILL BE REMOVED WHEN SOCKJS STOPS NEEDING TO SUPPORT OLD, DUMB VERSIONS OF WEBSOCKETS             ===
# ============================================================================================================

# Copyright (c) 2011-2012 Oregon State University Open Source Lab
#               2011-2012 Corbin Simpson
#                         Twisted Matrix Laboratories
#
# See LICENSE for details.

"""
The WebSockets protocol (RFC 6455), provided as a resource which wraps a
factory.
"""

__all__ = ("OldWebSocketsResource",)

from base64 import b64encode, b64decode
from hashlib import md5, sha1
from struct import pack, unpack
from string import digits

from zope.interface import implementer

from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.python import log
from twisted.python.constants import NamedConstant, Names
from twisted.web.resource import IResource, NoResource
from twisted.web.server import NOT_DONE_YET

class _WSException(Exception):
    """
    Internal exception for control flow inside the WebSockets frame parser.
    """

class _CONTROLS(Names):
    """
    Control frame specifiers.
    """

    NORMAL = NamedConstant()
    CLOSE = NamedConstant()
    PING = NamedConstant()
    PONG = NamedConstant()

_opcode_types = {
    0x0: _CONTROLS.NORMAL,
    0x1: _CONTROLS.NORMAL,
    0x2: _CONTROLS.NORMAL,
    0x8: _CONTROLS.CLOSE,
    0x9: _CONTROLS.PING,
    0xa: _CONTROLS.PONG,
}

_opcode_for_type = {
    _CONTROLS.NORMAL: 0x1,
    _CONTROLS.CLOSE: 0x8,
    _CONTROLS.PING: 0x9,
    _CONTROLS.PONG: 0xa,
}

_encoders = {
    "base64": b64encode,
}

_decoders = {
    "base64": b64decode,
}

_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"

def _isHixie75(request):
    return request.getHeader("Sec-WebSocket-Version") is None and \
        request.getHeader("Sec-WebSocket-Key1") is None and \
        request.getHeader("Sec-WebSocket-Key2") is None

def _isHybi00(request):
    return request.getHeader("Sec-WebSocket-Key1") is not None and \
        request.getHeader("Sec-WebSocket-Key2") is not None

def _challenge(key1, key2, challenge):
    first = int("".join(i for i in key1 if i in digits)) / key1.count(" ")
    second = int("".join(i for i in key2 if i in digits)) / key2.count(" ")
    nonce = md5(pack(">II8s", first, second, challenge)).digest()
    return nonce

def _makeAccept(key):
    return sha1("%s%s" % (key, _WS_GUID)).digest().encode("base64").strip()

def _mask(buf, key):
    key = [ord(i) for i in key]
    buf = list(buf)
    for i, char in enumerate(buf):
        buf[i] = chr(ord(char) ^ key[i % 4])
    return "".join(buf)

def _makeFrame(buf, old, _opcode=_CONTROLS.NORMAL):
    if old:
        if _opcode != _CONTROLS.NORMAL:
            return None
        return "\x00{}\xFF".format(buf)
    else:
        bufferLength = len(buf)

        if bufferLength > 0xffff:
            length = "\x7f%s" % pack(">Q", bufferLength)
        elif bufferLength > 0x7d:
            length = "\x7e%s" % pack(">H", bufferLength)
        else:
            length = chr(bufferLength)

        # Always make a normal packet.
        header = chr(0x80 | _opcode_for_type[_opcode])
        frame = "%s%s%s" % (header, length, buf)
        return frame

def _parseFrames(buf, old):
    if old:
        start = buf.find("\x00")
        tail = 0
        frames = []
        while start != -1:
            end = buf.find("\xFF",start+1)
            if end == -1:
                break
            frame = buf[start+1:end]
            frames.append((_CONTROLS.NORMAL, frame))
            tail = end + 1
            start = buf.find("\x00", tail)
        return frames, buf[tail:]
    else:
        start = 0
        frames = []
        while True:
            if len(buf) - start < 2:
                break
            header = ord(buf[start])
            if header & 0x70:
                raise _WSException("Reserved flag in frame (%d)" % header)
            opcode = header & 0xf
            try:
                opcode = _opcode_types[opcode]
            except KeyError:
                raise _WSException("Unknown opcode %d in frame" % opcode)
            length = ord(buf[start + 1])
            masked = length & 0x80
            length &= 0x7f
            offset = 2
            if length == 0x7e:
                if len(buf) - start < 4:
                    break
                length = buf[start + 2:start + 4]
                length = unpack(">H", length)[0]
                offset += 2
            elif length == 0x7f:
                if len(buf) - start < 10:
                    break
                length = buf[start + 2:start + 10]
                length = unpack(">Q", length)[0]
                offset += 8
            if masked:
                if len(buf) - (start + offset) < 4:
                    break
                key = buf[start + offset:start + offset + 4]
                offset += 4
            if len(buf) - (start + offset) < length:
                break
            data = buf[start + offset:start + offset + length]
            if masked:
                data = _mask(data, key)
            if opcode == _CONTROLS.CLOSE:
                if len(data) >= 2:
                    data = unpack(">H", data[:2])[0], data[2:]
                else:
                    data = 1000, "No reason given"
            frames.append((opcode, data))
            start += offset + length
        return frames, buf[start:]

class _WebSocketsProtocol(ProtocolWrapper):
    buf = ""
    codec = None
    challenge = None
    connected = False

    def __init__(self, *args, **kwargs):
        ProtocolWrapper.__init__(self, *args, **kwargs)
        self._pending_frames = []

    def connectionMade(self):
        connected = True
        if not self.challenge:
            ProtocolWrapper.connectionMade(self)
        log.msg("Opening connection with %s" % self.transport.getPeer())

    def parseFrames(self):
        try:
            frames, self.buf = _parseFrames(self.buf, self.old)
        except _WSException:
            log.err()
            self.loseConnection()
            return

        for frame in frames:
            opcode, data = frame
            if opcode == _CONTROLS.NORMAL:
                if self.codec:
                    data = _decoders[self.codec](data)
                ProtocolWrapper.dataReceived(self, data)
            elif opcode == _CONTROLS.CLOSE:
                reason, text = data
                log.msg("Closing connection: %r (%d)" % (text, reason))
                self.loseConnection()
                return
            elif opcode == _CONTROLS.PING:
                self.transport.write(_makeFrame(data, self.old, _opcode=_CONTROLS.PONG))

    def sendFrames(self):
        # Don't send anything before the challenge
        if self.challenge:
            return
        for frame in self._pending_frames:
            # Encode the frame before sending it.
            if self.codec:
                frame = _encoders[self.codec](frame)
            packet = _makeFrame(frame, self.old)
            self.transport.write(packet)
        self._pending_frames = []

    def dataReceived(self, data):
        self.buf += data
        if self.challenge:
            if len(self.buf) >= 8:
                challenge, self.buf = self.buf[:8], self.buf[8:]
                nonce = self.challenge(challenge)
                self.transport.write(nonce)
                self.challenge = None
                if self.connected:
                    ProtocolWrapper.connectionMade(self)
                self.dataReceived("") # Kick it off proper
        else:
            self.parseFrames()
            if self._pending_frames:
                self.sendFrames()

    def write(self, data):
        self._pending_frames.append(data)
        self.sendFrames()

    def writeSequence(self, data):
        self._pending_frames.extend(data)
        self.sendFrames()

    def loseConnection(self):
        if not self.disconnecting:
            if not self.challenge:
                frame = _makeFrame("", self.old, _opcode=_CONTROLS.CLOSE)
                if frame:
                    self.transport.write(frame)
            ProtocolWrapper.loseConnection(self)

class _WebSocketsFactory(WrappingFactory):
    protocol = _WebSocketsProtocol

@implementer(IResource)
class OldWebSocketsResource(object):
    isLeaf = True

    def __init__(self, factory):
        self.__factory = _WebSocketsFactory(factory)

    def getChildWithDefault(self, name, request):
        return NoResource("No such child resource.")

    def putChild(self, path, child):
        pass

    def render(self, request):
        """
        Render a request.

        We're not actually rendering a request. We are secretly going to
        handle a WebSockets connection instead.
        """
        # If we fail at all, we're gonna fail with 400 and no response.
        failed = False

        if request.method != "GET":
            failed = True

        upgrade = request.getHeader("Upgrade")
        if upgrade is None or "websocket" not in upgrade.lower():
            failed = True

        connection = request.getHeader("Connection")
        if connection is None or "upgrade" not in connection.lower():
            failed = True
        
        codec = request.getHeader("Sec-WebSocket-Protocol") or request.getHeader("WebSocket-Protocol")
        if codec:
            if codec not in _encoders or codec not in _decoders:
                log.msg("Codec %s is not implemented" % codec)
                failed = True
        
        ## This is a big mess of setting various headers based on which version we are
        ## And determining whether to use "old frames" or "new frames"
        if _isHixie75(request) or _isHybi00(request):
            old = True
            host = request.getHeader("Host") or "example.com"
            origin = request.getHeader("Origin") or "http://example.com"
            location = "{}://{}{}".format("wss" if request.isSecure() else "ws", host, request.path)
            if _isHixie75(request):
                request.setHeader("WebSocket-Origin", origin)
                request.setHeader("WebSocket-Location", location)
                if codec:
                    request.setHeader("WebSocket-Protocol", codec)
            else:
                request.setHeader("Sec-WebSocket-Origin", origin)
                request.setHeader("Sec-WebSocket-Location", location)
                if codec:
                    request.setHeader("Sec-WebSocket-Protocol", codec)
        else:
            old =  False
            key = request.getHeader("Sec-WebSocket-Key")
            if key is None:
                failed = True
            version = request.getHeader("Sec-WebSocket-Version")
            if version not in ("7","8","13"):
                failed = True
                request.setHeader("Sec-WebSocket-Version", "13")
            if not failed:
                request.setHeader("Sec-WebSocket-Version", version)
                request.setHeader("Sec-WebSocket-Accept", _makeAccept(key))
                if codec:
                    request.setHeader("Sec-WebSocket-Protocol", codec)

        if failed:
            request.setResponseCode(400)
            return ""

        # We are going to finish this handshake. We will return a valid status code.
        request.setResponseCode(101)
        request.setHeader("Upgrade", "WebSocket")
        request.setHeader("Connection", "Upgrade")

        # Create the protocol. This could fail, in which case we deliver an
        # error status. Status 502 was decreed by glyph; blame him.
        protocol = self.__factory.buildProtocol(request.transport.getPeer())
        if not protocol:
            request.setResponseCode(502)
            return ""
        protocol.old = old
        if _isHybi00(request):
            protocol.challenge = lambda x: _challenge(request.getHeader("Sec-WebSocket-Key1"), request.getHeader("Sec-WebSocket-Key2"), x)
        if codec:
            protocol.codec = codec
        
        ## This must be first, since makeConnection will butcher our headers otherwise
        request.write("")
        
        ## Then we wire it into the protocol wrapper
        transport, request.transport = request.transport, None
        transport.protocol = protocol
        protocol.makeConnection(transport)
        
        ## Copy the buffer
        protocol.dataReceived(request.channel.clearLineBuffer())
        
        return NOT_DONE_YET
