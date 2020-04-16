import unittest, importlib, tornado, aiopg
from tornado.testing import AsyncHTTPSTestCase
from tornado.testing import gen_test

#import the marxan-server module
m = importlib.import_module("marxan-server")

class TestMarxanServerApp(AsyncHTTPSTestCase):
    @gen_test
    def get_app(self):
        m._setGlobalVariables()
        _pool = yield aiopg.create_pool(m.CONNECTION_STRING, timeout = None)
        return m.Application(_pool)

    def test_toggleEnableGuestUser(self):
        response = self.fetch('/marxan-server/toggleEnableGuestUser')
        self.assertEqual(response.code, 200)
        