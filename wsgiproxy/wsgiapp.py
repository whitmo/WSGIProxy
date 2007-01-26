def make_app(
    global_conf,
    href):
    from wsgiproxy.app import WSGIProxyApp
    return WSGIProxyApp(href)

def make_middleware(
    app, global_conf):
    from wsgiproxy.middleware import WSGIProxyMiddleware
    return WSGIProxyMiddleware(app)
