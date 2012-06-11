==============
SockJS-Twisted
==============

A simple library for adding SockJS support to your twisted application.

Usage
=====

Use ``txsockjs.factory.SockJSFactory`` to wrap your factories. That's it!

    >>> from txsockjs.factory import SockJSFactory
	>>> reactor.listenTCP(8080, SockJSFactory(factory_to_wrap))

There is nothing else to it, no special setup involved.

Do you want a secure connection? Use ``listenSSL()`` instead of ``listenTCP()``.

Advanced Usage
==============

For those who want to host multiple SockJS services off of one port,
``txsockjs.factory.SockJSMultiFactory`` is designed to handle routing for you.

    >>> from txsockjs.factory import SockJSMultiFactory
    >>> f = SockJSMultiFactory()
    >>> f.addFactory(EchoFactory(), "echo")
    >>> f.addFactory(ChatFactory(), "chat")
    >>> reactor.listenTCP(8080, f)

http://localhost:8080/echo and http://localhost:8080/chat will give you access
to your EchoFactory and ChatFactory.

Caveats
=======

SockJS-Twisted does not attempt to offer multiple endpoints on one connection,
and is not designed to be run on port 80 or 443 alongside a webserver. It is primarily
for existing TCP based applications to offer a backwards compatible web connection,
similar to `txWS <https://github.com/MostAwesomeDude/txWS/>`_.

License
=======

SockJS-Twisted is (c) 2012 Christopher Gamble and is made available under the BSD license.