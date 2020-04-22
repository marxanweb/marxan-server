#unit tests for marxan-server.py. 
# PREREQUISITES: The test data in the general repo
# To test:
# 1. change to the marxan-server directory
# 2. conda activate base (or whatever environment was used in the install of marxan-server)
# 3. In marxan-server.py uncomment the log_exception function
# 4. python3 -m unittest marxan-server_test -v
# When finished:
# 1. In marxan-server.py comment out the log_exception function

# To test against an SSL localhost
# 1. Replace all AsyncHTTPTestCase with AsyncHTTPSTestCase
# 2. Set TEST_HTTP, TEST_WS and TEST_REFERER to point to secure endpoints, e.g. https and wss
import unittest, importlib, tornado, aiopg, json, urllib, os
from tornado.testing import AsyncHTTPTestCase, gen_test
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado import httputil
from shutil import copyfile

#CONSTANTS
LOGIN_USER = "admin"
LOGIN_PASSWORD = "password"
TEST_HTTP = "http://localhost"
TEST_WS = "ws://localhost"
TEST_REFERER = "http://localhost"
TEST_USER = "unit_tester"
TEST_PROJECT = "test_project"
TEST_IMPORT_PROJECT = "test_import_project"
TEST_DATA_FOLDER = os.path.dirname(os.getcwd()) + os.sep + "general" + os.sep + "test-data" + os.sep 
TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES = "multiple_features.zip"

#global variables
cookie = None
projects = ''
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

class TestClass(AsyncHTTPTestCase):
    @gen_test
    def get_app(self):
        #set variables
        initialiseServer()
        #create a connection pool 
        self._pool = yield aiopg.create_pool(m.CONNECTION_STRING, timeout = None)
        #create the app
        return m.Application(self._pool)
    
    @gen_test
    def tearDown(self):
        #free the database connection
        self._pool.close()
        yield self._pool.wait_closed()
        
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
            print("\n")
            print(_dict['error'])
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
        while True:
            msg = yield ws_client.read_message()
            if not msg:
                break
            _dict = self.getDictResponse(msg, mustReturnError)
            # print(_dict)
    
    def uploadFile(self, fullPath, formData, mustReturnError):
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
        port = str(self.get_http_port())
        self.makeRequest('/uploadShapefile', mustReturnError, method='POST', headers=headers, body=body)
        
    ###########################################################################
    # start of individual tests
    ###########################################################################

    #synchronous GET request
    def test_0050_validateUser(self):
        self.makeRequest('/validateUser?user=' + LOGIN_USER + '&password=' + LOGIN_PASSWORD, False) 

    # def test_0100_getServerData(self):
    #     self.makeRequest('/getServerData', False)

    # def test_0300_createUser(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"password":"wibble","fullname":"wibble","email":"a@b.com"})
    #     self.makeRequest('/createUser', False, method="POST", body=body)
        
    # def test_0600_toggleEnableGuestUser(self):
    #     _dict = self.makeRequest('/toggleEnableGuestUser', False)
    #     self.assertTrue('enabled' in _dict.keys())
        
    # def test_0800_getProjectsWithGrids(self):
    #     self.makeRequest('/getProjectsWithGrids', False)

    # def test_1000_createProject(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_PROJECT,"description":"whatever","planning_grid_name":"pu_ton_marine_hexagon_50", 'interest_features':'63407942,63408405,63408475,63767166','target_values':'33,17,45,17','spf_values':'40,40,40,40'})
    #     self.makeRequest('/createProject', False, method="POST", body=body)

    # def test_1100_createImportProject(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_IMPORT_PROJECT})
    #     self.makeRequest('/createImportProject', False, method="POST", body=body)

    # def test_1125_getProjects(self):
    #     self.makeRequest('/getProjects?user=' + TEST_USER, False)
        
    # def test_1150_getProject(self):
    #     self.makeRequest('/getProject?user=' + TEST_USER + '&project=' + TEST_PROJECT, False)

    # def test_1200_cloneProject(self):
    #     self.makeRequest('/cloneProject?user=' + TEST_USER + '&project=' + TEST_PROJECT, False)

    # def test_1300_createProjectGroup(self):
    #     _dict = self.makeRequest('/createProjectGroup?user=' + TEST_USER + '&project=' + TEST_PROJECT + '&copies=5&blmValues=0.1,0.2,0.3,0.4,0.5', False)
    #     global projects
    #     # get the names of the projects so we can delete them in the next test
    #     projects = ",".join([i['projectName'] for i in _dict['data']])

    # def test_1400_deleteProjects(self): 
    #     self.makeRequest('/deleteProjects?projectNames=' + projects, False)

    # def test_1500_renameProject(self):
    #     self.makeRequest('/renameProject?user=' + TEST_USER + '&project=' + TEST_PROJECT + "&newName=wibble", False)
 
    # def test_1600_updateProjectParameters(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_IMPORT_PROJECT, 'COLORCODE':'wibble'})
    #     self.makeRequest('/updateProjectParameters', False, method="POST", body=body)

    # def test_1700_deleteProject(self):
    #     self.makeRequest('/deleteProject?user=' + TEST_USER + '&project=wibble', False)

    # def test_1800_listProjectsForFeature(self):
    #     self.makeRequest('/listProjectsForFeature?feature_class_id=63407942', False)

    # def test_1900_listProjectsForPlanningGrid(self):
    #     self.makeRequest('/listProjectsForPlanningGrid?feature_class_name=pu_89979654c5d044baa27b6008f9d06', False)

    # def test_2000_getCountries(self):
    #     self.makeRequest('/getCountries', False)

    # def test_2100_getPlanningUnitGrids(self):
    #     self.makeRequest('/getPlanningUnitGrids', False)

    # def test_2200_deletePlanningUnitGrid(self):
    #     self.makeRequest('/deletePlanningUnitGrid?planning_grid_name=pu_and_terrestrial_square_50', False)

    # def test_2300_createPlanningUnitGrid(self):
    #     self.makeWebSocketRequest('/createPlanningUnitGrid?iso3=AND&domain=Terrestrial&areakm2=50&shape=square', False)

    # def test_2400_uploadTilesetToMapBox(self):
    #     self.makeRequest('/uploadTilesetToMapBox?feature_class_name=pu_and_terrestrial_square_50&mapbox_layer_name=square', False)
    
    # def test_2500_getUser(self):
    #     self.makeRequest('/getUser?user=' + TEST_USER, False)

    # def test_2600_getUsers(self):
    #     self.makeRequest('/getUsers', False)

    # def test_2700_updateUserParameters(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER, 'EMAIL':'wibble2'})
    #     self.makeRequest('/updateUserParameters', False, method="POST", body=body)

    # def test_2800_getFeature(self):
    #     self.makeRequest('/getFeature?oid=63407942', False)
        
    # def test_2900_uploadShapefile(self):
    #     testFile = TEST_DATA_FOLDER + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES
    #     destFile = os.getcwd() + os.sep + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES
    #     self.uploadFile(testFile, {'name': 'whatever', 'description': 'whatever2', 'filename': TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES}, False)
    #     # TODO The following is a hack as I cant upload a zip file as a binary file so all subsequent operations on the zip shapefile fail
    #     os.remove(destFile)
    #     copyfile(testFile, destFile)

    # def test_3000_unzipShapefile(self):
    #     testFile = TEST_DATA_FOLDER + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES
    #     self.makeRequest('/unzipShapefile?filename=' + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES, False)

    # def test_3100_getShapefileFieldnames(self):
    #     self.makeRequest('/getShapefileFieldnames?filename=' + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES[:-4] + ".shp", False)

    # def test_3200_deleteShapefile(self):
    #     self.makeRequest('/deleteShapefile?zipfile=' + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES + '&shapefile=' + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES[:-4] + ".shp", False)

    def test_3300_importFeatures(self):
        #non-existing shapefile
        self.makeWebSocketRequest('/importFeatures?zipfile=ignored&shapefile=nonexisting', True)
        # self.makeWebSocketRequest('/importFeatures?zipfile=' + TEST_ZIPPED_SHAPEFILE_MULTIPLE_FEATURES)

    # def test_(self):
    #     self.makeRequest('/')

            # ("/upgradeProject", upgradeProject),
            # ("/deleteShapefile", deleteShapefile),
            # ("/uploadFile", uploadFile),
            # ("/importPlanningUnitGrid", importPlanningUnitGrid),
            # ("/createFeaturePreprocessingFileFromImport", createFeaturePreprocessingFileFromImport),
            # ("/logout", logout),
            # ("/resendPassword", resendPassword),

            # ("/importFeatures", importFeatures),
            # ("/deleteFeature", deleteFeature),
            # ("/createFeatureFromLinestring", createFeatureFromLinestring),
            # ("/getFeaturePlanningUnits", getFeaturePlanningUnits),
            # ("/getPlanningUnitsData", getPlanningUnitsData), #currently not used
            # ("/getPlanningUnitsCostData", getPlanningUnitsCostData), 
            # ("/updatePUFile", updatePUFile),
            # ("/getPUData", getPUData),
            # ("/getSpeciesData", getSpeciesData), #currently not used
            # ("/getAllSpeciesData", getAllSpeciesData), 
            # ("/getSpeciesPreProcessingData", getSpeciesPreProcessingData), #currently not used
            # ("/updateSpecFile", updateSpecFile),
            # ("/getProtectedAreaIntersectionsData", getProtectedAreaIntersectionsData), #currently not used
            # ("/getMarxanLog", getMarxanLog), #currently not used - bugs in the Marxan output log
            # ("/getBestSolution", getBestSolution), #currently not used
            # ("/getOutputSummary", getOutputSummary), #currently not used
            # ("/getSummedSolution", getSummedSolution), #currently not used
            # ("/getResults", getResults),
            # ("/getSolution", getSolution),
            # ("/getMissingValues", getMissingValues), #currently not used
            # ("/preprocessFeature", preprocessFeature),
            # ("/preprocessPlanningUnits", preprocessPlanningUnits),
            # ("/preprocessProtectedAreas", preprocessProtectedAreas),
            # ("/runMarxan", runMarxan),
            # ("/stopProcess", stopProcess),
            # ("/getRunLogs", getRunLogs),
            # ("/clearRunLogs", clearRunLogs),
            # ("/updateWDPA", updateWDPA),
            # ("/runGapAnalysis", runGapAnalysis),
            # ("/importGBIFData", importGBIFData),
            # ("/dismissNotification", dismissNotification),
            # ("/resetNotifications", resetNotifications),
            # ("/deleteGapAnalysis", deleteGapAnalysis),
            # ("/testRoleAuthorisation", testRoleAuthorisation),
            # ("/addParameter", addParameter),
            # ("/shutdown", shutdown),
            # ("/block", block),
            # ("/testTornado", testTornado),
        
    # def test_9999_deleteUser(self):
    #     self.makeRequest('/deleteUser?user=' + TEST_USER, False)
        
        