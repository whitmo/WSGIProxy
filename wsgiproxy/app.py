class WSGIProxyApp(object):

    def __init__(self, href):
        self.href = href

    def __call__(self, environ, start_response):
        raise NotImplementedError
    
