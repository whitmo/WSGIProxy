import httplib
import unittest

from minimock import mock, restore, Mock, TraceTracker, assert_same_trace
from webob import Request
from wsgiproxy.exactproxy import proxy_exact_request


def h(**kw):
    """Convenience function for headers"""

    d = {}
    for name, value in kw.items():
        d[name.replace('_', '-')] = str(value)
    return d

def expected_trace_for_request(request):
    return """
Called httplib.HTTPConnection('%(server_name)s:%(server_port)d')
Called httplib.HTTPConnection.request(
    '%(method)s',
    '%(path_qs)s',
    '%(body)s',
    {'Host': '%(host)s', 'Content-Length': %(content_length)s})
Called httplib.HTTPConnection.getresponse()
Called httpresponse.getheader('content-length')
Called httpresponse.read()
Called httplib.HTTPConnection.close()
    """.strip() % dict(
        server_name=request.server_name,
        server_port=request.server_port,
        host=request.host,
        method=request.method,
        path_qs=request.path_qs,
        body=request.body,
        content_length=request.content_length if request.content_length else 0,
        )


class ExactProxyTests(unittest.TestCase):
    def setUp(self):
        """Mock out httplib.HTTPConnection and
        httplib.HTTPSConnection"""

        self.trace_tracker = TraceTracker()
        self.conn = Mock('httplib.HTTPConnection', tracker=self.trace_tracker)
        mock('httplib.HTTPConnection', mock_obj=self.conn)
        mock('httplib.HTTPSConnection', mock_obj=self.conn)
        self.conn.mock_returns = self.conn

    def set_response(self, status, headers, body):
        mock_response = Mock('httpresponse', tracker=self.trace_tracker)
        mock_response.status = int(status.split()[0])
        mock_response.reason = status.split(None, 1)[1]
        mock_response.read.mock_returns = body
        mock_response.getheader.mock_returns_func = headers.get
        mock_response.msg.headers = [
            '%s: %s' % (name, value) for name, value in headers.items()]
        self.conn.getresponse.mock_returns = mock_response

    def test_simple_request_200(self):
        req = Request.blank('http://example.com/testform')
        self.set_response(
            status='200 OK',
            headers=h(content_type='text/html'),
            body='some stuff',
            )

        res = req.get_response(proxy_exact_request)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, 'some stuff')
        self.assertEqual(res.headers['Content-Type'], 'text/html')
        assert_same_trace(self.trace_tracker, expected_trace_for_request(req))

    def test_simple_request_302(self):
        req = Request.blank('http://example.com/testform')
        self.set_response(
            status='302 Found',
            headers=h(content_type='text/html', set_cookie='foo=bar'),
            body='some content',
            )

        res = req.get_response(proxy_exact_request)

        self.assertEqual(res.status_code, 302)
        self.assertEqual(res.body, 'some content')
        self.assertEqual(res.headers['Content-Type'], 'text/html')
        self.assertEqual(res.headers['Set-Cookie'], 'foo=bar')
        assert_same_trace(self.trace_tracker, expected_trace_for_request(req))

    def test_simple_request_799(self):
        req = Request.blank('http://example.com/testform')
        self.set_response(
            status='799 Silly Response',
            headers=h(x_foobar='blaz'),
            body='blahblah',
            )

        res = req.get_response(proxy_exact_request)

        self.assertEqual(res.status_code, 799)
        self.assertEqual(res.body, 'blahblah')
        self.assertEqual(res.headers['X-Foobar'], 'blaz')
        assert_same_trace(self.trace_tracker, expected_trace_for_request(req))

    def test_post(self):
        req = Request.blank('http://example.com/testform')
        req.method = 'POST'
        req.query_string = 'test=result'
        req.body = 'var=value&var2=value2'
        req.environ['SERVER_NAME'] = 'example.org'
        req.environ['SERVER_PORT'] = '443'
        req.host = 'differenthost.com'
        req.scheme = 'https'
        self.set_response(
            status='200 OK',
            headers=h(content_type='text/html'),
            body='blahblah',
            )

        res = req.get_response(proxy_exact_request)

        self.assertEqual(res.status_code, 200)
        self.assertEqual(res.body, 'blahblah')
        self.assertEqual(res.headers['Content-Type'], 'text/html')
        assert_same_trace(self.trace_tracker, expected_trace_for_request(req))

