import unittest

from wsgiproxy.sampleapp import application
from wsgiproxy.middleware import WSGIProxyMiddleware


class WSGIProxyMiddlewareTests(unittest.TestCase):
    def test_create(self):
        app = WSGIProxyMiddleware(application)
