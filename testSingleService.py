#
# Copyright (c) 2020 Andrew Cottam.
#
# This file is part of marxan-server
# (see https://github.com/marxanweb/marxan-server).
#
# License: European Union Public Licence V. 1.2, see https://opensource.org/licenses/EUPL-1.2
#
import unittest, importlib, tornado, aiopg, json, urllib, os, sys
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado import httputil
from shutil import copyfile

#CONSTANTS
MARXAN_SERVER_FOLDER = os.getcwd()
LOGIN_USER = "admin"
LOGIN_PASSWORD = "password"
TEST_HTTP = "http://localhost"
TEST_WS = "ws://localhost"
TEST_REFERER = "http://localhost"
TEST_USER = "unit_tester"
TEST_PROJECT = "test_project"
TEST_IMPORT_PROJECT = "test_import_project"
TEST_DATA_FOLDER = MARXAN_SERVER_FOLDER + os.sep + "test-data" + os.sep 
TEST_FILE = "readme.md"
TEST_ZIP_SHP_MULTIPLE = "multiple_features.zip"
TEST_ZIP_SHP_INVALID_GEOM = "invalid_geometry.zip"
TEST_ZIP_SHP_MISSING_FILE = "pulayer_missing_file.zip"
TEST_ZIP_SHP_PLANNING_GRID = "pu_sample.zip"

#global variables
cookie = None
projects = ''
fcns = []

#import the marxan-server module
m = importlib.import_module("marxan-server")
#set the ASYNC_TEST_TIMEOUT environment variable as described here http://www.tornadoweb.org/en/stable/testing.html#tornado.testing.AsyncTestCase.wait
os.environ['ASYNC_TEST_TIMEOUT'] = '600' # 10 minutes

def initialiseServer():
    m.SHOW_START_LOG = False
    #set the global variables
    m._setGlobalVariables()
    m.DISABLE_SECURITY = False
    m.SHOW_START_LOG = False
    return 
    
def setCookies(response):
    #get the cookies
    cookies = response.headers['set-cookie'].split(",")
    parsed = [httputil.parse_cookie(c) for c in cookies]
    #get the user cookie
    userCookie = next((c for c in parsed if "user" in c.keys()), None)
    #get the role cookie
    roleCookie = next((c for c in parsed if "role" in c.keys()), None)
    global cookie
    cookie = "user=" + userCookie['user'] + ";role=" + roleCookie['role']

def copyTestData(filename):
    """
    Copies a file from the unittests/test-data folder to the marxan-server folder
    
    Arguments:
        filename (str): the name of the file to copy including the extension
    """
    testFile = TEST_DATA_FOLDER + filename
    destFile = MARXAN_SERVER_FOLDER + os.sep + filename
    if os.path.exists(destFile):
        os.remove(destFile)
    copyfile(testFile, destFile)

class TestClass(AsyncHTTPTestCase):
    @gen_test
    def get_app(self):
        #set variables
        m.SHOW_START_LOG = False
        #set the global variables
        yield m._setGlobalVariables()
        m.DISABLE_SECURITY = False
        m.SHOW_START_LOG = False
        #create the app
        self._app = m.Application()
        return self._app
    
    @gen_test
    def tearDownHelper(self):
        # From Ben Darnell article: https://stackoverflow.com/a/32992727
        #free the database connection
        m.pg.pool.close()
        yield m.pg.pool.wait_closed()
        
    def tearDown(self):
        self.tearDownHelper()
        super().tearDown()
        
    def getDictResponse(self, response, mustReturnError):
        """
        Parses the response from either a GET/POST request or a WebSocket message to check for errors
        """
        #set a flag to indicate if the request is complete or not
        requestComplete = False
        if hasattr(response, 'body'):
            #for GET/POST requests there is only one response
            _dict = dict(json.loads(response.body.decode("utf-8"))) 
            requestComplete = True
        else:
            #for WebSocket requests there will be more than one message
            _dict = dict(json.loads(response)) 
            #if the status is Finished then the request is complete
            requestComplete = _dict['status'] == "Finished"
        #print any error messages
        if ('error' in _dict.keys()):
            err = _dict['error']
            #leave out the href link to the error message
            if err.find("See <")!=-1:
                err = err[:err.find("See <")]
            # print(err, end=' ', flush=True)
        print(_dict)
        #assertions for errors
        if requestComplete:
            if mustReturnError:
                self.assertTrue('error' in _dict.keys())
            else:
                self.assertFalse('error' in _dict.keys())
        return _dict
    
    @gen_test
    def makeRequest(self, url, mustReturnError, **kwargs):
        """Makes a GET/POST request to the url using the optional kwargs arguments
        
        Parameters:
            url (str): The query part of the url to request - this excludes the /marxan-server prefix
            mustReturnError (bool): If True, the request must return an error and the assertTrue will be run
            **kwargs (optional): Additional parameters that are passed by keyword to the url fetch function, e.g. headers, body
        
        Returns:
            dict: The json response from the marxan-server
        """
        #get any existing headers
        if "headers" in kwargs.keys():
            d1 = kwargs['headers']
        else:
            d1 = {}
        # get the generic headers
        d2 = {'Cookie': cookie, "referer": TEST_REFERER} if cookie else {"referer": TEST_REFERER}
        #merge the headers
        kwargs.update({'headers': {**d1, **d2}})
        #make the request
        response = yield self.http_client.fetch(TEST_HTTP + ':' + str(self.get_http_port()) + "/marxan-server" + url, **kwargs)
        #assert a valid response
        self.assertEqual(response.code, 200)
        #if the response has cookies then set them globally
        if ('set-cookie' in response.headers.keys() and response.headers['set-cookie']):
            setCookies(response)
        # get the response as a dictionary
        _dict = self.getDictResponse(response, mustReturnError)
        return _dict

    @gen_test
    def makeWebSocketRequest(self, request, mustReturnError, **kwargs):
        msgs = []
        # add the cookies if they have been set
        if cookie:
            kwargs.update({'headers':{'Cookie': cookie, "referer": TEST_REFERER}})
        else:
            kwargs.update({'headers':{"referer": TEST_REFERER}})
        #dont attempt to validate the SSL certificate otherwise you get SSL errors - not sure why and set the request timeout (5 seconds by default)
        kwargs.update({'validate_cert': False, 'request_timeout': None})
        #get the websocket url
        ws_url = TEST_WS + ":" + str(self.get_http_port()) + "/marxan-server" + request
        #make the request
        ws_client = yield tornado.websocket.websocket_connect(HTTPRequest(ws_url, **kwargs))
        #log the messages from the websocket
        print("\n")
        while True:
            msg = yield ws_client.read_message()
            if not msg:
                break
            _dict = self.getDictResponse(msg, mustReturnError)
            msgs.append(_dict)
            # print(_dict)
        return msgs
    
    def uploadFile(self, fullPath, formData, mustReturnError):
        headers, body = self.getRequestHeaders(fullPath, formData, mustReturnError)
        self.makeRequest('/uploadFile', mustReturnError, method='POST', headers=headers, body=body)

    def uploadFileToFolder(self, fullPath, formData, mustReturnError):
        headers, body = self.getRequestHeaders(fullPath, formData, mustReturnError)
        self.makeRequest('/uploadFileToFolder', mustReturnError, method='POST', headers=headers, body=body)
    
    def getRequestHeaders(self, fullPath, formData, mustReturnError):
        #get the filename from the full path
        filename = fullPath[fullPath.rfind(os.sep) + 1:]
        boundary = 'SomeRandomBoundary'
        headers = {'Content-Type': 'multipart/form-data; boundary=%s' % boundary}
        body = '--%s\r\n' % boundary 
        #add the form-data to the request
        for k in formData.keys():
            body += 'Content-Disposition: form-data; name="' + k + '"\r\n'
            body += '\r\n' 
            body += formData[k] + "\r\n"
            body += '--%s\r\n' % boundary 
        body += 'Content-Disposition: form-data; name="value"; filename="' + filename + '"\r\n'
        body += 'Content-Type: application/zip\r\n'
        body += '\r\n' # blank line
        with open(fullPath, 'rb') as f:
            body += '%s\r\n' % f.read() #TODO This needs to be written as binary data!
        body += "--%s--\r\n" % boundary
        return headers, body
        
    ###########################################################################
    # start of individual tests
    ###########################################################################

    #asynchronous/synchronous GET request
    def test_0050_validateUser(self):
        self.makeRequest('/validateUser?user=' + LOGIN_USER + '&password=' + LOGIN_PASSWORD, False) 

    #WebSocket request
    # def test_2300_exportProject(self):
    #     self.makeWebSocketRequest('/exportProject?user=admin&project=Start%20project', False)

    # def test_2400_importProject(self):
    #     self.makeWebSocketRequest('/importProject?user=admin&project=Start%20project2&filename=admin_Start%20project.mxw&description=wibble%20description', False)

    # def test_1080_createFeaturesFromWFS(self):
    #     features = self.makeWebSocketRequest('/createFeaturesFromWFS2?endpoint=https%3A%2F%2Fdservices2.arcgis.com%2F7p8XMQ9sy7kJZN4K%2Farcgis%2Fservices%2FCranes_Species_Ranges%2FWFSServer%3Fservice%3Dwfs&featuretype=Cranes_Species_Ranges%3ABlack_Crowned_Cranes&name=test&description=wibble&srs=EPSG:3857', False)
    #     #get the feature class names of those that have been imported
    #     fcns = [feature['feature_class_name'] for feature in features if feature['status'] == 'FeatureCreated']
    #     for f in fcns:
    #         self.makeRequest('/deleteFeature?feature_name=' + f, False)

    # def test_1450_updateCosts(self):
    #     self.makeRequest('/updateCosts?user=admin&project=Start%20project&costname=Uniform', False)
    
    # def test_2200_exportPlanningUnitGrid(self):
    #     self.makeRequest('/exportPlanningUnitGrid?name=pu_ton_marine_hexagon_50', False)

    # def test_2201_exportFeature(self):
    #     self.makeRequest('/exportFeature?name=intersesting_habitat', False)

    # def test_066_runSQLFile(self):
    #     self.makeRequest('/runSQLFile?filename=test.sql&suppressOutput=True', False)

    # def test_3000_unzipShapefile(self):
    #     copyTestData(TEST_ZIP_SHP_MULTIPLE)
    #     self.makeRequest('/unzipShapefile?filename=' + TEST_ZIP_SHP_MULTIPLE, False)

    # #asynchronous/synchronous POST request
    # def test_1600_updateProjectParameters(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_IMPORT_PROJECT, 'COLORCODE':'wibble'})
    #     self.makeRequest('/updateProjectParameters', False, method="POST", body=body)

    # #WebSocket request
    # def test_2300_updateWDPA(self):
    #     self.makeWebSocketRequest('/updateWDPA?downloadUrl=whatever&unittest=True', False)
    
    def test_2301_reprocessProtectedAreas(self):
        self.makeWebSocketRequest('/reprocessProtectedAreas?user=case_studies', False)
    