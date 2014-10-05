# =====================================================================================
# === THIS IS A DIRECT COPY OF twisted.web.websockets AS IT IS STILL IN DEVELOPMENT ===
# === IT WILL BE REPLACED BY THE ACTUAL VERSION WHEN IT IS PUBLICLY AVAILABLE.      ===
# =====================================================================================
# -*- test-case-name: twisted.web.test.test_websockets -*-
# Copyright (c) Twisted Matrix Laboratories.
#               2011-2012 Oregon State University Open Source Lab
#               2011-2012 Corbin Simpson
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

"""
The WebSockets protocol (RFC 6455), provided as a resource which wraps a
factory.
"""

__all__ = ["WebSocketsResource"]

from hashlib import sha1
from struct import pack, unpack

from zope.interface import implementer, Interface

from twisted.protocols.policies import ProtocolWrapper, WrappingFactory
from twisted.python import log
from twisted.python.constants import NamedConstant, Names
from twisted.web.resource import IResource
from twisted.web.server import NOT_DONE_YET



class _WSException(Exception):
    """
    Internal exception for control flow inside the WebSockets frame parser.
    """



# Control frame specifiers. Some versions of WS have control signals sent
# in-band. Adorable, right?

class _CONTROLS(Names):
    """
    Control frame specifiers.
    """

    NORMAL = NamedConstant()
    CLOSE = NamedConstant()
    PING = NamedConstant()
    PONG = NamedConstant()


_opcodeTypes = {
    0x0: _CONTROLS.NORMAL,
    0x1: _CONTROLS.NORMAL,
    0x2: _CONTROLS.NORMAL,
    0x8: _CONTROLS.CLOSE,
    0x9: _CONTROLS.PING,
    0xa: _CONTROLS.PONG}


_opcodeForType = {
    _CONTROLS.NORMAL: 0x1,
    _CONTROLS.CLOSE: 0x8,
    _CONTROLS.PING: 0x9,
    _CONTROLS.PONG: 0xa}


# Authentication for WS.

# The GUID for WebSockets, from RFC 6455.
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"



def _makeAccept(key):
    """
    Create an "accept" response for a given key.

    This dance is expected to somehow magically make WebSockets secure.

    @type key: C{str}
    @param key: The key to respond to.

    @rtype: C{str}
    @return: An encoded response.
    """
    return sha1("%s%s" % (key, _WS_GUID)).digest().encode("base64").strip()



# Frame helpers.
# Separated out to make unit testing a lot easier.
# Frames are bonghits in newer WS versions, so helpers are appreciated.



def _mask(buf, key):
    """
    Mask or unmask a buffer of bytes with a masking key.

    @type buf: C{str}
    @param buf: A buffer of bytes.

    @type key: C{str}
    @param key: The masking key. Must be exactly four bytes.

    @rtype: C{str}
    @return: A masked buffer of bytes.
    """

    # This is super-secure, I promise~
    key = [ord(i) for i in key]
    buf = list(buf)
    for i, char in enumerate(buf):
        buf[i] = chr(ord(char) ^ key[i % 4])
    return "".join(buf)



def _makeFrame(buf, _opcode=_CONTROLS.NORMAL):
    """
    Make a frame.

    This function always creates unmasked frames, and attempts to use the
    smallest possible lengths.

    @type buf: C{str}
    @param buf: A buffer of bytes.

    @type _opcode: C{_CONTROLS}
    @param _opcode: Which type of frame to create.

    @rtype: C{str}
    @return: A packed frame.
    """
    bufferLength = len(buf)

    if bufferLength > 0xffff:
        length = "\x7f%s" % pack(">Q", bufferLength)
    elif bufferLength > 0x7d:
        length = "\x7e%s" % pack(">H", bufferLength)
    else:
        length = chr(bufferLength)

    # Always make a normal packet.
    header = chr(0x80 | _opcodeForType[_opcode])
    frame = "%s%s%s" % (header, length, buf)
    return frame



def _parseFrames(buf):
    """
    Parse frames in a highly compliant manner.

    @type buf: C{str}
    @param buf: A buffer of bytes.

    @rtype: C{list}
    @return: A list of frames.
    """
    start = 0
    frames = []

    while True:
        # If there's not at least two bytes in the buffer, bail.
        if len(buf) - start < 2:
            break

        # Grab the header. This single byte holds some flags nobody cares
        # about, and an opcode which nobody cares about.
        header = ord(buf[start])
        if header & 0x70:
            # At least one of the reserved flags is set. Pork chop sandwiches!
            raise _WSException("Reserved flag in frame (%d)" % header)

        # Get the opcode, and translate it to a local enum which we actually
        # care about.
        opcode = header & 0xf
        try:
            opcode = _opcodeTypes[opcode]
        except KeyError:
            raise _WSException("Unknown opcode %d in frame" % opcode)

        # Get the payload length and determine whether we need to look for an
        # extra length.
        length = ord(buf[start + 1])
        masked = length & 0x80
        length &= 0x7f

        # The offset we're gonna be using to walk through the frame. We use
        # this because the offset is variable depending on the length and
        # mask.
        offset = 2

        # Extra length fields.
        if length == 0x7e:
            if len(buf) - start < 4:
                break

            length = buf[start + 2:start + 4]
            length = unpack(">H", length)[0]
            offset += 2
        elif length == 0x7f:
            if len(buf) - start < 10:
                break

            # Protocol bug: The top bit of this long long *must* be cleared;
            # that is, it is expected to be interpreted as signed. That's
            # fucking stupid, if you don't mind me saying so, and so we're
            # interpreting it as unsigned anyway. If you wanna send exabytes
            # of data down the wire, then go ahead!
            length = buf[start + 2:start + 10]
            length = unpack(">Q", length)[0]
            offset += 8

        if masked:
            if len(buf) - (start + offset) < 4:
                # This is not strictly necessary, but it's more explicit so
                # that we don't create an invalid key.
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
                # Gotta unpack the opcode and return usable data here.
                data = unpack(">H", data[:2])[0], data[2:]
            else:
                # No reason given; use generic data.
                data = 1000, "No reason given"

        frames.append((opcode, data))
        start += offset + length

    return frames, buf[start:]



class _WebSocketsProtocol(ProtocolWrapper):
    """
    Protocol which wraps another protocol to provide a WebSockets transport
    layer.
    """
    _buffer = None


    def connectionMade(self):
        """
        Log the new connection and initialize the buffer list.
        """
        ProtocolWrapper.connectionMade(self)
        log.msg("Opening connection with %s" % self.transport.getPeer())
        self._buffer = []


    def _parseFrames(self):
        """
        Find frames in incoming data and pass them to the underlying protocol.
        """
        try:
            frames, rest = _parseFrames("".join(self._buffer))
        except _WSException:
            # Couldn't parse all the frames, something went wrong, let's bail.
            log.err()
            self.loseConnection()
            return

        self._buffer[:] = [rest]

        for frame in frames:
            opcode, data = frame
            if opcode == _CONTROLS.NORMAL:
                # Business as usual. Decode the frame, if we have a decoder.
                # Pass the frame to the underlying protocol.
                ProtocolWrapper.dataReceived(self, data)
            elif opcode == _CONTROLS.CLOSE:
                # The other side wants us to close. I wonder why?
                reason, text = data
                log.msg("Closing connection: %r (%d)" % (text, reason))

                # Close the connection.
                self.loseConnection()
                return
            elif opcode == _CONTROLS.PING:
                # 5.5.2 PINGs must be responded to with PONGs.
                # 5.5.3 PONGs must contain the data that was sent with the
                # provoking PING.
                self.transport.write(_makeFrame(data, _opcode=_CONTROLS.PONG))


    def _sendFrames(self, frames):
        """
        Send all pending frames.

        @param frames: A list of byte strings to send.
        @type frames: C{list}
        """
        for frame in frames:
            # Encode the frame before sending it.
            packet = _makeFrame(frame)
            self.transport.write(packet)


    def dataReceived(self, data):
        """
        Append the data to the buffer list and parse the whole.
        """
        self._buffer.append(data)

        self._parseFrames()


    def write(self, data):
        """
        Write to the transport.

        This method will only be called by the underlying protocol.
        """
        self._sendFrames([data])


    def writeSequence(self, data):
        """
        Write a sequence of data to the transport.

        This method will only be called by the underlying protocol.
        """
        self._sendFrames(data)


    def loseConnection(self):
        """
        Close the connection.

        This includes telling the other side we're closing the connection.

        If the other side didn't signal that the connection is being closed,
        then we might not see their last message, but since their last message
        should, according to the spec, be a simple acknowledgement, it
        shouldn't be a problem.
        """
        # Send a closing frame. It's only polite. (And might keep the browser
        # from hanging.)
        if not self.disconnecting:
            frame = _makeFrame("", _opcode=_CONTROLS.CLOSE)
            self.transport.write(frame)

            ProtocolWrapper.loseConnection(self)



class _WebSocketsFactory(WrappingFactory):
    """
    Factory which wraps another factory to provide WebSockets frames for all
    of its protocols.

    This factory does not provide the HTTP headers required to perform a
    WebSockets handshake; see C{WebSocketsResource}.
    """
    protocol = _WebSocketsProtocol



class IWebSocketsResource(Interface):
    """
    A WebSockets resource.

    @since: 13.0
    """

    def lookupProtocol(protocolNames, request):
        """
        Build a protocol instance for the given protocol options and request.

        @param protocolNames: The asked protocols from the client.
        @type protocolNames: C{list} of C{str}

        @param request: The connecting client request.
        @type request: L{IRequest<twistd.web.iweb.IRequest>}

        @return: A tuple of (protocol, C{None}).
        @rtype: C{tuple}
        """



@implementer(IResource, IWebSocketsResource)
class WebSocketsResource(object):
    """
    A resource for serving a protocol through WebSockets.

    This class wraps a factory and connects it to WebSockets clients. Each
    connecting client will be connected to a new protocol of the factory.

    Due to unresolved questions of logistics, this resource cannot have
    children.

    @since: 13.0
    """
    isLeaf = True

    def __init__(self, factory):
        self._factory = _WebSocketsFactory(factory)


    def getChildWithDefault(self, name, request):
        """
        Reject attempts to retrieve a child resource.  All path segments beyond
        the one which refers to this resource are handled by the WebSocket
        connection.
        """
        raise RuntimeError(
            "Cannot get IResource children from WebsocketsResourceTest")


    def putChild(self, path, child):
        """
        Reject attempts to add a child resource to this resource.  The
        WebSocket connection handles all path segments beneath this resource,
        so L{IResource} children can never be found.
        """
        raise RuntimeError(
            "Cannot put IResource children under WebSocketsResource")


    def lookupProtocol(self, protocolNames, request):
        """
        Build a protocol instance for the given protocol options and request.
        This default implementation ignores the protocols and just return an
        instance of protocols built by C{self._factory}.

        @param protocolNames: The asked protocols from the client.
        @type protocolNames: C{list} of C{str}

        @param request: The connecting client request.
        @type request: L{Request<twistd.web.http.Request>}

        @return: A tuple of (protocol, C{None}).
        @rtype: C{tuple}
        """
        protocol = self._factory.buildProtocol(request.transport.getPeer())
        return protocol, None


    def render(self, request):
        """
        Render a request.

        We're not actually rendering a request. We are secretly going to handle
        a WebSockets connection instead.

        @param request: The connecting client request.
        @type request: L{Request<twistd.web.http.Request>}

        @return: a strinf if the request fails, otherwise C{NOT_DONE_YET}.
        """
        request.defaultContentType = None
        # If we fail at all, we're gonna fail with 400 and no response.
        # You might want to pop open the RFC and read along.
        failed = False

        if request.method != "GET":
            # 4.2.1.1 GET is required.
            failed = True

        upgrade = request.getHeader("Upgrade")
        if upgrade is None or "websocket" not in upgrade.lower():
            # 4.2.1.3 Upgrade: WebSocket is required.
            failed = True

        connection = request.getHeader("Connection")
        if connection is None or "upgrade" not in connection.lower():
            # 4.2.1.4 Connection: Upgrade is required.
            failed = True

        key = request.getHeader("Sec-WebSocket-Key")
        if key is None:
            # 4.2.1.5 The challenge key is required.
            failed = True

        version = request.getHeader("Sec-WebSocket-Version")
        if version != "13":
            # 4.2.1.6 Only version 13 works.
            failed = True
            # 4.4 Forward-compatible version checking.
            request.setHeader("Sec-WebSocket-Version", "13")

        if failed:
            request.setResponseCode(400)
            return ""

        askedProtocols = request.requestHeaders.getRawHeaders(
            "Sec-WebSocket-Protocol")
        protocol, protocolName = self.lookupProtocol(askedProtocols, request)

        # If a protocol is not created, we deliver an error status.
        if not protocol.wrappedProtocol:
            request.setResponseCode(502)
            return ""

        # We are going to finish this handshake. We will return a valid status
        # code.
        # 4.2.2.5.1 101 Switching Protocols
        request.setResponseCode(101)
        # 4.2.2.5.2 Upgrade: websocket
        request.setHeader("Upgrade", "WebSocket")
        # 4.2.2.5.3 Connection: Upgrade
        request.setHeader("Connection", "Upgrade")
        # 4.2.2.5.4 Response to the key challenge
        request.setHeader("Sec-WebSocket-Accept", _makeAccept(key))
        # 4.2.2.5.5 Optional codec declaration
        if protocolName:
            request.setHeader("Sec-WebSocket-Protocol", protocolName)

        # Provoke request into flushing headers and finishing the handshake.
        request.write("")

        # And now take matters into our own hands. We shall manage the
        # transport's lifecycle.
        transport, request.transport = request.transport, None

        # Connect the transport to our factory, and make things go. We need to
        # do some stupid stuff here; see #3204, which could fix it.
        if request.isSecure():
            # Secure connections wrap in TLSMemoryBIOProtocol too.
            transport.protocol.wrappedProtocol = protocol
        else:
            transport.protocol = protocol
        protocol.makeConnection(transport)

        return NOT_DONE_YET
