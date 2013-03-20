import unittest

from wsgiproxy.sampleapp import application
from wsgiproxy.middleware import WSGIProxyMiddleware

def start_response(status, headers, exc_info=None):
    # print('*** start_response: status=%r; headers=%r' % (status, headers))
    pass

def get_app():
    return WSGIProxyMiddleware(application)

class WSGIProxyMiddlewareTests(unittest.TestCase):
    def test_blank_environ(self):
        app = get_app()
        environ = {}
        app(environ, start_response)

    def test_exception_HTTPBadRequest(self):
        app = get_app()
        environ = {
            'HTTP_X_SCRIPT_NAME': 'no_leading_slash_should_raise_HTTPBadRequest',
            'PATH_INFO': '/path/to/page',
            'SCRIPT_NAME': 'foo.py',
            }
        app(environ, start_response)
