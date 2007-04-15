from paste.deploy import converters

def make_app(
    global_conf,
    href=None,
    secret_file=None):
    from wsgiproxy.app import WSGIProxyApp
    if href is None:
        raise ValueError(
            "You must give an href value")
    if secret_file is None and 'secret_file' in global_conf:
        secret_file = global_conf['secret_file']
    return WSGIProxyApp(href=href, secret_file=secret_file)

def make_middleware(
    app, global_conf,
    secret_file=None,
    trust_ips=None):
    from wsgiproxy.middleware import WSGIProxyMiddleware
    if secret_file is None and 'secret_file' in global_conf:
        secret_file = global_conf['secret_file']
    if trust_ips is None and 'trust_ips' in global_conf:
        trust_ips = global_conf['trust_ips']
    trust_ips = converters.aslist(trust_ips)
    return WSGIProxyMiddleware(app, secret_file=secret_file,
                               trust_ips=trust_ips)

def make_real_proxy(global_conf):
    from wsgiproxy import exactproxy
    return exactproxy.filter_paste_httpserver_proxy(
        exactproxy.proxy_exact_request)

    
