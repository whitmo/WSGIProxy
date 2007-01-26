class WSGIProxyMiddleware(object):

    def __init__(self, application):
        self.application = application

    def __call__(self, environ, start_response):
        self._fixup_environ(environ)
        return self.application(environ, start_response)

    def _fixup_environ(self, environ):
        raise NotImplementedError
    
