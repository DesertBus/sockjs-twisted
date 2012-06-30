==============
SockJS-Twisted
==============

A simple library for adding SockJS support to your twisted application.

Status
======

SockJS-Twisted passes all `SockJS-Protocol v0.3 <https://github.com/sockjs/sockjs-protocol>`_ tests
except for not supporting ``Connection: Keep-Alive``. There are no plans to support ``Connection: Keep-Alive``
at this time, and it should not negatively impact any applications using SockJS-Twisted.

SockJS-Twisted has been tested with the sample chat application in the tests directory, and it
has been shown to work on all supported transports on Chrome, Firefox, Internet Explorer, Safari,
and Opera. However, this testing was very light, and does not cover all edge cases.

**Therefore, SockJS-Twisted is not proven production ready.** Please feel free to use it for
projects where its failure would not be catastrophic, but it comes with no warranty. As
always, any reports on performance or bugs is greatly appreciated.

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

Options
=======

A dictionary of options can be passed into the factory to control SockJS behavior.

    >>> options = {
    >>>     'websocket': True,
    >>>     'cookie_needed': False,
    >>>     'heartbeat': 25,
    >>>     'timeout': 5,
    >>>     'streaming_limit': 128 * 1024
    >>> }
    >>> SockJSFactory(factory_to_wrap, options)
    >>> SockJSMultiFactory().addFactory(factory_to_wrap, prefix, options)

**websocket** - whether websockets are supported as a protocol. Useful for proxies or load balancers that don't support websockets.

**cookie_needed** - whether the JSESSIONID cookie is set. Results in less performant protocols being used, so don't require them unless your load balancer requires it.

**heartbeat** - how often a heartbeat message is sent to keep the connection open. Do not increase this unless you know what you are doing.

**timeout** - maximum delay between connections before the underlying protocol is disconnected

**streaming_limit** - how many bytes can be sent over a streaming protocol before it is cycled. Allows browser-side garbage collection to lower RAM usage.

Caveats
=======

SockJS-Twisted does not re-use any HTTP machinery, and is not designed to be run
on port 80 or 443 alongside a webserver. It is primarily for existing TCP based 
applications to offer a backwards compatible web connection, similar to 
`txWS <https://github.com/MostAwesomeDude/txWS/>`_.

License
=======

SockJS-Twisted is (c) 2012 Christopher Gamble and is made available under the BSD license.