import unittest

from wsgiproxy.wsgiapp import make_app


class MiscTests(unittest.TestCase):
    def test_make_app(self):
        global_conf = {}
        app = make_app(global_conf, href='http://example.com/testform')
