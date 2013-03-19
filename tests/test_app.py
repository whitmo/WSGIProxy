import unittest

from wsgiproxy.app import WSGIProxyApp


class WSGIProxyAppTests(unittest.TestCase):
    def test_create(self):
        app = WSGIProxyApp(href='http://example.com/testform')
