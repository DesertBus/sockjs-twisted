==============
SockJS-Twisted
==============

A simple library for adding SockJS support to your twisted application.

Status
======

SockJS-Twisted passes all `SockJS-Protocol v0.3.3 <https://github.com/sockjs/sockjs-protocol>`_ tests,
and all `SockJS-Client qunit <https://github.com/sockjs/sockjs-client>`_ tests. It has been used in
production environments, and should be free of any critical bugs.

Usage
=====

Use ``txsockjs.factory.SockJSFactory`` to wrap your factories. That's it!

.. code-block:: python

    from txsockjs.factory import SockJSFactory
    reactor.listenTCP(8080, SockJSFactory(factory_to_wrap))

There is nothing else to it, no special setup involved.

Do you want a secure connection? Use ``listenSSL()`` instead of ``listenTCP()``.

Advanced Usage
==============

For those who want to host multiple SockJS services off of one port,
``txsockjs.factory.SockJSMultiFactory`` is designed to handle routing for you.

.. code-block:: python

    from txsockjs.factory import SockJSMultiFactory
    f = SockJSMultiFactory()
    f.addFactory(EchoFactory(), "echo")
    f.addFactory(ChatFactory(), "chat")
    reactor.listenTCP(8080, f)

http://localhost:8080/echo and http://localhost:8080/chat will give you access
to your EchoFactory and ChatFactory.

Integration With Websites
=========================

It is possible to offer static resources, dynamic pages, and SockJS endpoints off of
a single port by using ``txsockjs.factory.SockJSResource``.

.. code-block:: python

    from txsockjs.factory import SockJSResource
    root = resource.Resource()
    root.putChild("echo", SockJSResource(EchoFactory()))
    root.putChild("chat", SockJSResource(ChatFactory()))
    site = server.Site(root)
    reactor.listenTCP(8080, site)

Multiplexing [Experimental]
===========================

SockJS-Twisted also has built-in support for multiplexing. See the
``Websocket-Multiplex <https://github.com/sockjs/websocket-multiplex>``_ library
for how to integrate multiplexing client side.

.. code-block:: python

    from txsockjs.multiplex import SockJSMultiplexResource
    multiplex = SockJSMultiplexResource()
    multiplex.addFactory("echo", EchoFactory())
    multiplex.addFactory("chat", ChatFactory())
    root = resource.Resource()
    root.putChild("multiplex", multiplex)
    site = server.Site(root)
    reactor.listenTCP(8080, site)

If you want PubSub functionality, just use ``txsockjs.multiplex.SockJSPubSubResource`` instead!

Options
=======

A dictionary of options can be passed into the factory to control SockJS behavior.

.. code-block:: python

    options = {
        'websocket': True,
        'cookie_needed': False,
        'heartbeat': 25,
        'timeout': 5,
        'streaming_limit': 128 * 1024,
        'encoding': 'cp1252', # Latin1
        'sockjs_url': 'https://d1fxtkz8shb9d2.cloudfront.net/sockjs-0.3.js'
    }
    SockJSFactory(factory_to_wrap, options)
    SockJSMultiFactory().addFactory(factory_to_wrap, prefix, options)
    SockJSResource(factory_to_wrap, options)
    SockJSMultiplexResource(options)
    SockJSPubSubResource(options)

websocket :
    whether websockets are supported as a protocol. Useful for proxies or load balancers that don't support websockets.

cookie_needed :
    whether the JSESSIONID cookie is set. Results in less performant protocols being used, so don't require them unless your load balancer requires it.

heartbeat :
    how often a heartbeat message is sent to keep the connection open. Do not increase this unless you know what you are doing.

timeout :
    maximum delay between connections before the underlying protocol is disconnected

streaming_limit :
    how many bytes can be sent over a streaming protocol before it is cycled. Allows browser-side garbage collection to lower RAM usage.

encoding :
    All messages to and from txsockjs should be valid UTF-8. In the event that a message received by txsockjs is not UTF-8, fall back to this encoding.

sockjs_url :
    The url of the SockJS library to use in iframes. By default this is served over HTTPS and therefore shouldn't need changing.

License
=======

SockJS-Twisted is (c) 2012 Christopher Gamble and is made available under the BSD license.
