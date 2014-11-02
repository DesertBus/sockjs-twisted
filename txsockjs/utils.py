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

def normalize(s, encoding):
    if not isinstance(s, basestring):
        try:
            return str(s)
        except UnicodeEncodeError:
            return unicode(s).encode('utf-8','backslashreplace')
    elif isinstance(s, unicode):
        return s.encode('utf-8', 'backslashreplace')
    else:
        if s.decode('utf-8', 'ignore').encode('utf-8', 'ignore') == s: # Ensure s is a valid UTF-8 string
            return s
        else: # Otherwise assume it is Windows 1252
            return s.decode(encoding, 'replace').encode('utf-8', 'backslashreplace')

def broadcast(message, targets, encoding="cp1252"):
    message = normalize(message, encoding)
    json_msg = 'a{0}'.format(json.dumps([message], separators=(',',':')))
    for t in targets:
        if getattr(t, "writeRaw", None) is not None:
            t.writeRaw(json_msg)
        else:
            t.write(message)

try:
    from twisted.internet.ssl import DefaultOpenSSLContextFactory
    # The only difference is using ctx.use_certificate_chain_file instead of ctx.use_certificate_file
    class ChainedOpenSSLContextFactory(DefaultOpenSSLContextFactory):
        def cacheContext(self):
            DefaultOpenSSLContextFactory.cacheContext(self)
            self._context.use_certificate_chain_file(self.certificateFileName)
except ImportError:
    pass # no SSL support
