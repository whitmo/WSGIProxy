import unittest

from wsgiproxy.spawn import SpawningApplication


class SpawningApplicationTests(unittest.TestCase):
    def test_create(self):
        app = SpawningApplication(start_script='/usr/bin/true')
