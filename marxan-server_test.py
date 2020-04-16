#unit tests for marxan-server.py. test with python3 -m unittest marxan-server_test
import unittest, importlib, tornado, aiopg, json, urllib
from tornado.testing import AsyncHTTPSTestCase
from tornado.testing import gen_test

#import the marxan-server module
m = importlib.import_module("marxan-server")

def getDictResponse(response):
    _dict = dict(json.loads(response.body.decode("utf-8")))
    if ('error' in _dict.keys()):
        print(_dict['error'])
    return _dict
    
class TestMarxanServerApp(AsyncHTTPSTestCase):
    @gen_test
    def get_app(self):
        #set the global variables
        m._setGlobalVariables()
        #turn off security so we can test all methods
        m.DISABLE_SECURITY = True
        #create a connection pool 
        self._pool = yield aiopg.create_pool(m.CONNECTION_STRING, timeout = None)
        #create the app
        return m.Application(self._pool)
    
    def get_new_ioloop(self):
        return tornado.ioloop.IOLoop.current()

    def test_toggleEnableGuestUser(self):
        response = self.fetch('/marxan-server/toggleEnableGuestUser')
        _dict = getDictResponse(response)
        self.assertTrue('enabled' in _dict.keys())
        self.assertEqual(response.code, 200)
        
    def test_createUser(self):
        post_body = urllib.parse.urlencode({"user":"asd","password":"wibble","fullname":"wibble","email":"a@b.com"})
        response = self.fetch('/marxan-server/createUser', method="POST", body=post_body, headers={"referer": "localhost"})
        _dict = getDictResponse(response)
        self.assertEqual(response.code, 200)
        self.assertFalse('error' in _dict.keys())
        