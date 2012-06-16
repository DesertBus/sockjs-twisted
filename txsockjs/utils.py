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

from txsockjs.protocols.static import Greeting, Info, IFrame, Error404
from txsockjs.protocols.rawwebsocket import RawWebSocket
from txsockjs.protocols.websocket import WebSocket
from txsockjs.protocols.xhr import XHR, XHRSend, XHRStream
from txsockjs.protocols.eventsource import EventSource
from txsockjs.protocols.htmlfile import HTMLFile
from txsockjs.protocols.jsonp import JSONP, JSONPSend
from urlparse import parse_qs
import re

methods = {
    'GREETING': Greeting,
    'INFO': Info,
    'IFRAME': IFrame,
    'RAWWEBSOCKET': RawWebSocket,
    'websocket': WebSocket,
    'xhr': XHR,
    'xhr_send': XHRSend,
    'xhr_streaming': XHRStream,
    'eventsource': EventSource,
    'htmlfile': HTMLFile,
    'jsonp': JSONP,
    'jsonp_send': JSONPSend,
    
    'ERROR404': Error404
}

pathValidator = re.compile('(|/(.*?))(|/(|info|iframe[0-9-a-z._-]*\.html|websocket|[^./]+/[^./]+/(websocket|xhr|xhr_send|xhr_streaming|eventsource|htmlfile|jsonp|jsonp_send)))(|\?(.*))$')

def httpHeaders(headers):
    """
    Create a dictionary of data from raw HTTP headers.
    """
    d = {}
    for line in headers.split("\r\n"):
        try:
            key, value = [i.strip() for i in line.split(":", 1)]
            d[key] = value
        except ValueError:
            pass
    return d

def parsePath(path,prefixes):
    prefix = ""
    session = None
    loadbalance = None
    method = None
    query = None
    
    match = pathValidator.match(path)
    if match is None:
        return (prefix, session, methods['ERROR404'], query)
    prefix = match.group(2) or ''
    suffix = match.group(4) or ''
    query = match.group(7)
    if suffix.find('/') >= 0:
        loadbalance, session, method = suffix.split('/',2)
    else:
        method = suffix
    
    # Since websocket is both a root level and session level command, we have to ensure we split it properly
    if method == "websocket":
        if prefix not in prefixes:
            prefix += '/' + loadbalance + '/' + session
            loadbalance = session = None
    
    if prefix not in prefixes:
        return (prefix, session, methods['ERROR404'], query)
    if session:
        if method in methods:
            method = methods[method]
        else:
            method = methods['ERROR404']
    else:
        if method == "info":
            method = methods['INFO']
        elif re.match("iframe[0-9-\.a-z_]*\.html$",method):
            method = methods['IFRAME']
        elif method == "websocket":
            method = methods['RAWWEBSOCKET']
        else:
            method = methods['GREETING']
    
    if query:
        query = parse_qs(query.lstrip('?'), True)
    
    return (prefix, session, method, query)

def validatePrefix(prefix):
    checks = {
        '': methods['GREETING'],
        '/': methods['GREETING'],
        '/info': methods['INFO'],
        '/iframe.html': methods['IFRAME'],
        '/websocket': methods['RAWWEBSOCKET'],
        '/a/a/websocket': methods['websocket'],
        '/a/a/xhr': methods['xhr'],
        '/a/a/xhr_send': methods['xhr_send'],
        '/a/a/xhr_streaming': methods['xhr_streaming'],
        '/a/a/eventsource': methods['eventsource'],
        '/a/a/htmlfile': methods['htmlfile'],
        '/a/a/jsonp': methods['jsonp'],
        '/a/a/jsonp_send': methods['jsonp_send']
    }
    checker = [prefix]
    for path, method in checks.iteritems():
        p, s, m, q = parsePath('/'+prefix+path,checker)
        if p != prefix or m != method:
            return False
    p, s, m, q = parsePath('/'+prefix+'/invalid',checker)
    if m != methods['ERROR404']:
        return False
    p, s, m, q = parsePath('/'+prefix+'/a/a/invalid',checker)
    if m != methods['ERROR404']:
        return False
    return True