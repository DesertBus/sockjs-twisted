var factory_body_check;

module('End to End');

factory_body_check = function(protocol) {
  var n;
  if (!SockJS[protocol] || !SockJS[protocol].enabled(client_opts.sockjs_opts)) {
    n = " " + protocol + " [unsupported by client]";
    return test(n, function() {
      return log('Unsupported protocol (by client): "' + protocol + '"');
    });
  } else {
    return asyncTest(protocol, function() {
      var code, hook, url;
      expect(5);
      url = client_opts.url + '/echo';
      code = "hook.test_body(!!document.body, typeof document.body);\n\nvar sock = new SockJS('" + url + "', null,\n{protocols_whitelist:['" + protocol + "']});\nsock.onopen = function() {\n    var m = hook.onopen();\n    sock.send(m);\n};\nsock.onmessage = function(e) {\n    hook.onmessage(e.data);\n    sock.close();\n};";
      hook = newIframe('sockjs-in-head.html');
      hook.open = function() {
        hook.iobj.loaded();
        ok(true, 'open');
        return hook.callback(code);
      };
      hook.test_body = function(is_body, type) {
        return equal(is_body, false, 'body not yet loaded ' + type);
      };
      hook.onopen = function() {
        ok(true, 'onopen');
        return 'a';
      };
      return hook.onmessage = function(m) {
        equal(m, 'a');
        ok(true, 'onmessage');
        hook.iobj.cleanup();
        hook.del();
        return start();
      };
    });
  }
};

module('connection errors');

asyncTest("invalid url 404", function() {
  var r;
  expect(4);
  r = newSockJS('/invalid_url', 'jsonp-polling');
  ok(r);
  r.onopen = function(e) {
    return ok(false);
  };
  r.onmessage = function(e) {
    return ok(false);
  };
  return r.onclose = function(e) {
    if (u.isXHRCorsCapable() < 4) {
      equals(e.code, 1002);
      equals(e.reason, 'Can\'t connect to server');
    } else {
      equals(e.code, 2000);
      equals(e.reason, 'All transports failed');
    }
    equals(e.wasClean, false);
    return start();
  };
});

asyncTest("invalid url port", function() {
  var dl, r;
  expect(4);
  dl = document.location;
  r = newSockJS(dl.protocol + '//' + dl.hostname + ':1079', 'jsonp-polling');
  ok(r);
  r.onopen = function(e) {
    return ok(false);
  };
  return r.onclose = function(e) {
    if (u.isXHRCorsCapable() < 4) {
      equals(e.code, 1002);
      equals(e.reason, 'Can\'t connect to server');
    } else {
      equals(e.code, 2000);
      equals(e.reason, 'All transports failed');
    }
    equals(e.wasClean, false);
    return start();
  };
});

asyncTest("disabled websocket test", function() {
  var r;
  expect(3);
  r = newSockJS('/disabled_websocket_echo', 'websocket');
  r.onopen = function(e) {
    return ok(false);
  };
  r.onmessage = function(e) {
    return ok(false);
  };
  return r.onclose = function(e) {
    equals(e.code, 2000);
    equals(e.reason, "All transports failed");
    equals(e.wasClean, false);
    return start();
  };
});

asyncTest("close on close", function() {
  var r;
  expect(4);
  r = newSockJS('/close', 'jsonp-polling');
  r.onopen = function(e) {
    return ok(true);
  };
  r.onmessage = function(e) {
    return ok(false);
  };
  return r.onclose = function(e) {
    equals(e.code, 3000);
    equals(e.reason, "Go away!");
    equals(e.wasClean, true);
    r.onclose = function() {
      return ok(false);
    };
    r.close();
    return u.delay(10, function() {
      return start();
    });
  };
});

asyncTest("EventEmitter exception handling", function() {
  var prev_onerror, r;
  expect(1);
  r = newSockJS('/echo', 'xhr-streaming');
  prev_onerror = window.onerror;
  window.onerror = function(e) {
    ok(/onopen error/.test('' + e));
    window.onerror = prev_onerror;
    return r.close();
  };
  r.onopen = function(e) {
    throw "onopen error";
  };
  return r.onclose = function() {
    return start();
  };
});
