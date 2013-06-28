========================
SockJS-Twisted Changelog
========================

1.1
===

**1.1.1**
 * Add python 2.6 compatability
 * Fix heartbeats not being sent until data was written from wrapped protocol

**1.1.0**
 * Add proxy_header to expose proxied IPs
 * Remove pubsub from multiplexing as it was misleading

1.0
===

**1.0.0**
 * Refactor entire library to use twisted.web
 * Use t.w.websockets for websocket support instead of txWS
 * Add experimental multiplexing and pubsub functionality

0.1
===

**0.1.1**
 * Converts all text to UTF-8 (prevents crashing websockets in chrome)
 * Minor bug fixes

**0.1.0**
 * Initial release
