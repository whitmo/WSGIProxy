import unittest

from wsgiproxy.sampleapp import application
from wsgiproxy.middleware import WSGIProxyMiddleware

def start_response(status, headers):
    # print('*** start_response: status=%r; headers=%r' % (status, headers))
    pass

def get_app():
    return WSGIProxyMiddleware(application)

class WSGIProxyMiddlewareTests(unittest.TestCase):
    def test_blank_environ(self):
        app = get_app()
        environ = {}
        app(environ, start_response)

    # This test triggers an error:
    #
    #   File "/Users/marca/dev/git-repos/WSGIProxy/wsgiproxy/middleware.py", line 162, in _fixup_environ
    #     return exc(environ, start_response)
    # NameError: global name 'start_response' is not defined
    #
    # def test_exception_HTTPBadRequest(self):
    #     app = get_app()
    #     environ = {'HTTP_X_SCRIPT_NAME': 'no_leading_slash_should_raise_HTTPBadRequest'}
    #     app(environ, start_response)
