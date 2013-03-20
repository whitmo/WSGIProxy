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
        result = app(environ, start_response)

        self.assertEqual(len(result), 6)
        self.assertEqual(result[0], '<html><head><title>Hello world</title></head>\n')
        self.assertEqual(result[1], '<body><h1>Hello world!</h1>\n')
        self.assertEqual(result[2], '<table border=1>\n')
        self.assertEqual(result[3], "<tr><td>PATH_INFO</td><td>''</td></tr>\n")
        self.assertEqual(result[4], "<tr><td>SCRIPT_NAME</td><td>''</td></tr>\n")
        self.assertEqual(result[5], '</table></body></html>')

    def test_exception_HTTPBadRequest(self):
        app = get_app()
        environ = {
            'HTTP_X_SCRIPT_NAME': 'no_leading_slash_should_raise_HTTPBadRequest',
            'PATH_INFO': '/path/to/page',
            'SCRIPT_NAME': 'foo.py',
            'HTTP_X_WSGIPROXY_VERSION': '0.1',
            }
        result = app(environ, start_response)

        # @todo: Should this return an error response?
        self.assertEqual(len(result), 6)
        self.assertEqual(result[0], '<html><head><title>Hello world</title></head>\n')
        self.assertEqual(result[1], '<body><h1>Hello world!</h1>\n')
        self.assertEqual(result[2], '<table border=1>\n')
        self.assertEqual(result[3], "<tr><td>PATH_INFO</td><td>'/path/to/page'</td></tr>\n")
        self.assertEqual(result[4], "<tr><td>SCRIPT_NAME</td><td>'foo.py'</td></tr>\n")
        self.assertEqual(result[5], '</table></body></html>')
