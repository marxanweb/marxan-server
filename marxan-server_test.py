#unit tests for marxan-server.py. 
# To test:
# 1. change to the marxan-server directory
# 2. conda activate base (or whatever environment was used in the install of marxan-server)
# 3. python3 -m unittest marxan-server_test -v
import unittest, importlib, tornado, aiopg, json, urllib
from tornado.testing import AsyncHTTPSTestCase, gen_test
from tornado.ioloop import IOLoop
from tornado.httpclient import HTTPRequest
from tornado import httputil
#CONSTANTS
TEST_USER = "unit_tester"
TEST_PROJECT = "test_project"
TEST_IMPORT_PROJECT = "test_import_project"
#global variables
cookie = None
projects = []
#import the marxan-server module
m = importlib.import_module("marxan-server")

class TestMarxanServerApp(AsyncHTTPSTestCase):
    @gen_test
    def get_app(self):
        m.SHOW_START_LOG = False
        #set the global variables
        m._setGlobalVariables()
        m.DISABLE_SECURITY = True
        m.SHOW_START_LOG = False
        #create a connection pool 
        self._pool = yield aiopg.create_pool(m.CONNECTION_STRING, timeout = None)
        #create the app
        self._app = m.Application(self._pool)
        return self._app
    
    @gen_test
    def tearDown(self):
        #free the database connection
        self._pool.close()
        yield self._pool.wait_closed()
        
    def setCookies(self, response):
        #get the cookies
        cookies = response.headers['set-cookie'].split(",")
        parsed = [httputil.parse_cookie(c) for c in cookies]
        #get the user cookie
        userCookie = next((c for c in parsed if "user" in c.keys()), None)
        #get the role cookie
        roleCookie = next((c for c in parsed if "role" in c.keys()), None)
        global cookie
        cookie = "user=" + userCookie['user'] + ";role=" + roleCookie['role']
        
    @gen_test
    def makeRequest(self, request, **kwargs):
        # add the cookies if they have been set
        if cookie:
            kwargs.update({'headers':{'Cookie': cookie, "referer": "https://www.marxanweb.org"}})
        else:
            kwargs.update({'headers':{"referer": "https://www.marxanweb.org"}})
        # ports are different for each request
        port = str(self.get_http_port())
        response = yield self.http_client.fetch('https://localhost:' + port + request, **kwargs)
        #if the response has cookies then set them globally
        if ('set-cookie' in response.headers.keys() and response.headers['set-cookie']):
            self.setCookies(response)
        # get the response as a dictionary
        _dict = dict(json.loads(response.body.decode("utf-8")))
        if ('error' in _dict.keys()):
            print(_dict['error'])
        #check there is a valid response and no error
        self.assertEqual(response.code, 200)
        self.assertFalse('error' in _dict.keys())
        return _dict

    @gen_test
    def makeWebSocketRequest(self, request, **kwargs):
        # add the cookies if they have been set
        if cookie:
            kwargs.update({'headers':{'Cookie': cookie, "referer": "https://www.marxanweb.org"}})
        else:
            kwargs.update({'headers':{"referer": "https://www.marxanweb.org"}})
        #dont attempt to validate the SSL certificate otherwise you get SSL errors - not sure why
        kwargs.update({'validate_cert': False})
        #get the websocket url
        ws_url = "wss://localhost:" + str(self.get_http_port()) + request
        #make the request
        ws_client = yield tornado.websocket.websocket_connect(HTTPRequest(ws_url, **kwargs))
        #log the messages from the websocket
        while True:
            msg = yield ws_client.read_message()
            if not msg:
                break
            print(msg)
        
    ###########################################################################
    # start of individual tests
    ###########################################################################

    #synchronous GET request
    def test_0050_validateUser(self):
        self.makeRequest('/marxan-server/validateUser?user=admin&password=password') 

    # def test_0100_getServerData(self):
    #     self.makeRequest('/marxan-server/getServerData')

    # def test_0200_deleteUser(self):
    #     self.makeRequest('/marxan-server/deleteUser?user=' + TEST_USER)
        
    # def test_0300_createUser(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"password":"wibble","fullname":"wibble","email":"a@b.com"})
    #     self.makeRequest('/marxan-server/createUser', method="POST", body=body)
        
    # def test_0600_toggleEnableGuestUser(self):
    #     _dict = self.makeRequest('/marxan-server/toggleEnableGuestUser')
    #     self.assertTrue('enabled' in _dict.keys())
        
    # def test_0800_getProjectsWithGrids(self):
    #     self.makeRequest('/marxan-server/getProjectsWithGrids')

    # def test_1000_createProject(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_PROJECT,"description":"whatever","planning_grid_name":"pu_ton_marine_hexagon_50", 'interest_features':'63407942,63408405,63408475,63767166','target_values':'33,17,45,17','spf_values':'40,40,40,40'})
    #     self.makeRequest('/marxan-server/createProject', method="POST", body=body)

    # def test_1100_createImportProject(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_IMPORT_PROJECT})
    #     self.makeRequest('/marxan-server/createImportProject', method="POST", body=body)

    # def test_1125_getProjects(self):
    #     _dict = self.makeRequest('/marxan-server/getProjects?user=' + TEST_USER)
        
    # def test_1150_getProject(self):
    #     _dict = self.makeRequest('/marxan-server/getProject?user=' + TEST_USER + '&project=' + TEST_PROJECT)

    # def test_1200_cloneProject(self):
    #     self.makeRequest('/marxan-server/cloneProject?user=' + TEST_USER + '&project=' + TEST_PROJECT)

    # def test_1300_createProjectGroup(self):
    #     _dict = self.makeRequest('/marxan-server/createProjectGroup?user=' + TEST_USER + '&project=' + TEST_PROJECT + '&copies=5&blmValues=0.1,0.2,0.3,0.4,0.5')
    #     global projects
    #     # get the names of the projects so we can delete them in the next test
    #     projects = ",".join([i['projectName'] for i in _dict['data']])

    # def test_1400_deleteProjects(self):
    #     self.makeRequest('/marxan-server/deleteProjects?projectNames=' + projects)

    # def test_1500_renameProject(self):
    #     self.makeRequest('/marxan-server/renameProject?user=' + TEST_USER + '&project=' + TEST_PROJECT + "&newName=wibble")

    # def test_1600_updateProjectParameters(self):
    #     body = urllib.parse.urlencode({"user":TEST_USER,"project":TEST_IMPORT_PROJECT, 'params': {'COLORCODE':['wibble']}})
    #     self.makeRequest('/marxan-server/updateProjectParameters', method="POST", body=body)

    # def test_1700_deleteProject(self):
    #     self.makeRequest('/marxan-server/deleteProject?user=' + TEST_USER + '&project=wibble')

    # def test_1800_listProjectsForFeature(self):
    #     self.makeRequest('/marxan-server/listProjectsForFeature?feature_class_id=63407942')

    # def test_1900_listProjectsForPlanningGrid(self):
    #     self.makeRequest('/marxan-server/listProjectsForPlanningGrid?feature_class_name=pu_89979654c5d044baa27b6008f9d06')

    # def test_2000_getCountries(self):
    #     self.makeRequest('/marxan-server/getCountries')

    # def test_2100_getPlanningUnitGrids(self):
    #     self.makeRequest('/marxan-server/getPlanningUnitGrids')

    def test_2200_createPlanningUnitGrid(self):
        self.makeWebSocketRequest('/marxan-server/createPlanningUnitGrid?iso3=AND&domain=Terrestrial&areakm2=30&shape=hexagon')

    # def test_(self):
    #     self.makeRequest('/marxan-server/')

            # ("/marxan-server/upgradeProject", upgradeProject),
            # ("/marxan-server/createPlanningUnitGrid", createPlanningUnitGrid),
            # ("/marxan-server/deletePlanningUnitGrid", deletePlanningUnitGrid),
            # ("/marxan-server/uploadTilesetToMapBox", uploadTilesetToMapBox),
            # ("/marxan-server/uploadShapefile", uploadShapefile),
            # ("/marxan-server/unzipShapefile", unzipShapefile),
            # ("/marxan-server/deleteShapefile", deleteShapefile),
            # ("/marxan-server/getShapefileFieldnames", getShapefileFieldnames),
            # ("/marxan-server/uploadFile", uploadFile),
            # ("/marxan-server/importPlanningUnitGrid", importPlanningUnitGrid),
            # ("/marxan-server/createFeaturePreprocessingFileFromImport", createFeaturePreprocessingFileFromImport),
            # ("/marxan-server/toggleEnableGuestUser", toggleEnableGuestUser),
            # ("/marxan-server/createUser", createUser), 
            # ("/marxan-server/validateUser", validateUser),
            # ("/marxan-server/logout", logout),
            # ("/marxan-server/resendPassword", resendPassword),
            # ("/marxan-server/getUser", getUser),
            # ("/marxan-server/getUsers", getUsers),
            # ("/marxan-server/deleteUser", deleteUser),
            # ("/marxan-server/updateUserParameters", updateUserParameters),
            # ("/marxan-server/getFeature", getFeature),
            # ("/marxan-server/importFeatures", importFeatures),
            # ("/marxan-server/deleteFeature", deleteFeature),
            # ("/marxan-server/createFeatureFromLinestring", createFeatureFromLinestring),
            # ("/marxan-server/getFeaturePlanningUnits", getFeaturePlanningUnits),
            # ("/marxan-server/getPlanningUnitsData", getPlanningUnitsData), #currently not used
            # ("/marxan-server/getPlanningUnitsCostData", getPlanningUnitsCostData), 
            # ("/marxan-server/updatePUFile", updatePUFile),
            # ("/marxan-server/getPUData", getPUData),
            # ("/marxan-server/getSpeciesData", getSpeciesData), #currently not used
            # ("/marxan-server/getAllSpeciesData", getAllSpeciesData), 
            # ("/marxan-server/getSpeciesPreProcessingData", getSpeciesPreProcessingData), #currently not used
            # ("/marxan-server/updateSpecFile", updateSpecFile),
            # ("/marxan-server/getProtectedAreaIntersectionsData", getProtectedAreaIntersectionsData), #currently not used
            # ("/marxan-server/getMarxanLog", getMarxanLog), #currently not used - bugs in the Marxan output log
            # ("/marxan-server/getBestSolution", getBestSolution), #currently not used
            # ("/marxan-server/getOutputSummary", getOutputSummary), #currently not used
            # ("/marxan-server/getSummedSolution", getSummedSolution), #currently not used
            # ("/marxan-server/getResults", getResults),
            # ("/marxan-server/getSolution", getSolution),
            # ("/marxan-server/getMissingValues", getMissingValues), #currently not used
            # ("/marxan-server/preprocessFeature", preprocessFeature),
            # ("/marxan-server/preprocessPlanningUnits", preprocessPlanningUnits),
            # ("/marxan-server/preprocessProtectedAreas", preprocessProtectedAreas),
            # ("/marxan-server/runMarxan", runMarxan),
            # ("/marxan-server/stopProcess", stopProcess),
            # ("/marxan-server/getRunLogs", getRunLogs),
            # ("/marxan-server/clearRunLogs", clearRunLogs),
            # ("/marxan-server/updateWDPA", updateWDPA),
            # ("/marxan-server/runGapAnalysis", runGapAnalysis),
            # ("/marxan-server/importGBIFData", importGBIFData),
            # ("/marxan-server/dismissNotification", dismissNotification),
            # ("/marxan-server/resetNotifications", resetNotifications),
            # ("/marxan-server/deleteGapAnalysis", deleteGapAnalysis),
            # ("/marxan-server/testRoleAuthorisation", testRoleAuthorisation),
            # ("/marxan-server/addParameter", addParameter),
            # ("/marxan-server/shutdown", shutdown),
            # ("/marxan-server/block", block),
            # ("/marxan-server/testTornado", testTornado),
        
        
        