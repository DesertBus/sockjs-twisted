var ajax_simple_factory, ajax_streaming_factory, ajax_wrong_port_factory, newIframe, onunload_test_factory, test_wrong_url, u;

module('Dom');

u = SockJS.getUtils();

newIframe = function(path) {
  var err, hook;
  if (path == null) path = '/iframe.html';
  hook = u.createHook();
  err = function() {
    return log('iframe error. bad.');
  };
  hook.iobj = u.createIframe(path + '?a=' + Math.random() + '#' + hook.id, err);
  return hook;
};

onunload_test_factory = function(code) {
  return function() {
    var hook;
    expect(3);
    hook = newIframe();
    hook.open = function() {
      ok(true, 'open hook called by an iframe');
      return hook.callback(code);
    };
    hook.load = function() {
      var f;
      ok(true, 'onload hook called by an iframe');
      f = function() {
        return hook.iobj.cleanup();
      };
      return setTimeout(f, 1);
    };
    return hook.unload = function() {
      ok(true, 'onunload hook called by an iframe');
      hook.del();
      return start();
    };
  };
};

if (navigator.userAgent.indexOf('Konqueror') !== -1 || navigator.userAgent.indexOf('Opera') !== -1) {
  test("onunload [unsupported by client]", function() {
    return ok(true);
  });
} else {
  asyncTest('onunload', onunload_test_factory("var u = SockJS.getUtils();\nu.attachEvent('load', function(){\n    hook.load();\n});\nvar w = 0;\nvar run = function(){\n    if(w === 0) {\n        w = 1;\n        hook.unload();\n    }\n};\nu.attachEvent('beforeunload', run);\nu.attachEvent('unload', run);"));
}

if (!SockJS.getIframeTransport().enabled()) {
  test("onmessage [unsupported by client]", function() {
    return ok(true);
  });
} else {
  asyncTest('onmessage', function() {
    var hook;
    expect(3);
    hook = newIframe();
    hook.open = function() {
      ok(true, 'open hook called by an iframe');
      return hook.callback("var u = SockJS.getUtils();\nu.attachMessage(function(e) {\n    var b = e.data;\n    parent.postMessage(window_id + ' ' + 'e', '*');\n});\nparent.postMessage(window_id + ' ' + 's', '*');");
    };
    return u.attachMessage(function(e) {
      var data, origin, window_id, _ref;
      _ref = e.data.split(' '), window_id = _ref[0], data = _ref[1];
      if (window_id === hook.id) {
        switch (data) {
          case 's':
            hook.iobj.loaded();
            ok(true, 'start frame send');
            origin = u.getOrigin(u.amendUrl('/'));
            return hook.iobj.post(hook.id + ' ' + 's', origin);
          case 'e':
            ok(true, 'done hook called by an iframe');
            hook.iobj.cleanup();
            hook.del();
            return start();
        }
      }
    });
  });
}

ajax_simple_factory = function(name) {
  return asyncTest(name + ' simple', function() {
    var x;
    expect(2);
    x = new u[name]('GET', '/simple.txt', null);
    return x.onfinish = function(status, text) {
      equal(text.length, 2051);
      equal(text.slice(-2), 'b\n');
      return start();
    };
  });
};

ajax_streaming_factory = function(name) {
  return asyncTest(name + ' streaming', function() {
    var x;
    expect(4);
    x = new u[name]('GET', '/streaming.txt', null);
    x.onchunk = function(status, text) {
      equal(status, 200);
      ok(text.length <= 2049, 'Most likely you\'re behind a transparent Proxy that can\'t do streaming. QUnit tests won\'t work properly. Sorry!');
      return delete x.onchunk;
    };
    return x.onfinish = function(status, text) {
      equal(status, 200);
      equal(text.slice(-4), 'a\nb\n');
      return start();
    };
  });
};

test_wrong_url = function(name, url, statuses) {
  var x;
  if (window.console && console.log) {
    console.log(' [*] Connecting to wrong url ' + url);
  }
  expect(2);
  x = new u[name]('GET', url, null);
  x.onchunk = function() {
    return ok(false, "chunk shall not be received");
  };
  return x.onfinish = function(status, text) {
    ok(u.arrIndexOf(statuses, status) !== -1);
    equal(text, '');
    return start();
  };
};

ajax_wrong_port_factory = function(name) {
  var port, _i, _len, _ref, _results;
  _ref = [25, 8999, 65300];
  _results = [];
  for (_i = 0, _len = _ref.length; _i < _len; _i++) {
    port = _ref[_i];
    _results.push(asyncTest(name + ' wrong port ' + port, function() {
      return test_wrong_url(name, 'http://localhost:' + port + '/wrong_url_indeed.txt', [0]);
    }));
  }
  return _results;
};

ajax_simple_factory('XHRLocalObject');

if (window.XDomainRequest) ajax_simple_factory('XDRObject');

if (!window.ActiveXObject) ajax_streaming_factory('XHRLocalObject');

if (window.XDomainRequest) ajax_streaming_factory('XDRObject');

ajax_wrong_port_factory('XHRLocalObject');

if (window.XDomainRequest) ajax_wrong_port_factory('XDRObject');

asyncTest('XHRLocalObject wrong url', function() {
  return test_wrong_url('XHRLocalObject', '/wrong_url_indeed.txt', [0, 404]);
});

if (window.XDomainRequest) {
  asyncTest('XDRObject wrong url', function() {
    return test_wrong_url('XDRObject', '/wrong_url_indeed.txt', [0]);
  });
}
