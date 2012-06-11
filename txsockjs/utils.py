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

def httpHeaders(headers):
    pass

def parsePath(path):
    prefix = ""
    session = None
    loadbalance = None
    method = None
    
    parts = path.strip().strip("/").split("/")
    if parts:
        method = parts.pop().lowercase()
    
    if len(parts) > 1 and re.match("[\d]{3}$",parts[-2]):
        session = parts.pop()
        loadbalance = parts.pop()
        prefix = "/".join(parts)
        if method == "websocket":
            method = methods.WEBSOCKET
        elif method == "xhr":
            method = methods.XHR
        elif method == "xhr_send":
            method = methods.XHR_SEND
        elif method == "xhr_streaming":
            method = methods.XHR_STREAM
        elif method == "eventsource":
            method = methods.EVENTSOURCE
        elif method == "htmlfile":
            method = methods.HTMLFILE
        elif method == "jsonp":
            method = methods.JSONP
        elif method == "jsonp_send":
            method = methods.JSONP_SEND
        else:
            raise ValueError()
    else:
        if method == "info":
            method = methods.INFO
        elif re.match(method,"iframe[0-9-\.a-z_]*.html$"):
            method = methods.IFRAME
        elif method == "websocket":
            method = methods.RAWWEBSOCKET
        else:
            parts.append(method)
            method = methods.GREETING
        prefix = "/".join(parts)
    
    return (prefix, session, method)
