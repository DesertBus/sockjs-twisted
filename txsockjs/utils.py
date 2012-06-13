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

from txsockjs.constants import methods
import re

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

def parsePath(path,checker):
    prefix = ""
    session = None
    loadbalance = None
    method = None
    
    match = re.match('/?(.*?)/(|info|iframe[0-9-a-z._-]*\.html|websocket|[^./]+/[^./]+/(websocket|xhr|xhr_send|xhr_streaming|eventsource|htmlfile|jsonp|jsonp_send))$',path)
    if match is None:
        return (prefix, session, methods['ERROR404'])
    prefix = match.group(1)
    suffix = match.group(2)
    if suffix.find('/') >= 0:
        loadbalance, session, method = suffix.split('/',2)
    else:
        method = suffix
    
    # Since websocket is both a root level and session level command, we have to ensure we split it properly
    if method == "websocket":
        if checker(prefix) is None:
            prefix += '/' + loadbalance + '/' + session
            loadbalance = session = None
    
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
    
    return (prefix, session, method)
