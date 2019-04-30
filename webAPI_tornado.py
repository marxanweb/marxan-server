from tornado.iostream import StreamClosedError
from tornado.process import Subprocess
from tornado.log import LogFormatter
from tornado.web import HTTPError
from tornado.web import StaticFileHandler
from tornado.ioloop import IOLoop
from tornado import concurrent
from tornado import gen
from urlparse import urlparse
from psycopg2 import sql
from mapbox import Uploader
from mapbox import errors
from osgeo import ogr
import webbrowser
import tornado.ioloop
import tornado.web
import tornado.websocket
import tornado.options
import logging
import json
import psycopg2
import pandas
import os
import re
import traceback
import glob
import time
import datetime
import select
import subprocess
import sys
import zipfile
import shutil
import uuid
import signal
import platform
import colorama
import io
import requests

####################################################################################################################################################################################################################################################################
## constant declarations
####################################################################################################################################################################################################################################################################

##SECURITY SETTINGS
DISABLE_SECURITY = False                                                            # Set to True to turn off all security, i.e. authentication and authorisation
#domains that are allowed to access and update this server - add http://localhost:8081 if you want to allow access from all local installs
PERMITTED_METHODS = ["getServerData","createUser","validateUser","resendPassword","testTornado"]    # REST services that have no authentication/authorisation/CORS control
ROLE_UNAUTHORISED_METHODS = {                                                       # Add REST services that you want to lock down to specific roles - a class added to an array will make that method unavailable for that role
    "ReadOnly": ["createProject","createImportProject","upgradeProject","deleteProject","cloneProject","createProjectGroup","deleteProjects","renameProject","updateProjectParameters","getCountries","deletePlanningUnitGrid","createPlanningUnitGrid","uploadTilesetToMapBox","uploadShapefile","uploadFile","importPlanningUnitGrid","createFeaturePreprocessingFileFromImport","createUser","getUsers","updateUserParameters","getFeature","importFeature","getPlanningUnitsData","updatePUFile","getSpeciesData","getSpeciesPreProcessingData","updateSpecFile","getProtectedAreaIntersectionsData","getMarxanLog","getBestSolution","getOutputSummary","getSummedSolution","getMissingValues","preprocessFeature","preprocessPlanningUnits","preprocessProtectedAreas","runMarxan","stopMarxan","testRoleAuthorisation",'deleteFeature','deleteUser'],
    "User": ["testRoleAuthorisation","deleteProject","deleteFeature","getUsers","deleteUser","deletePlanningUnitGrid"],
    "Admin": []
}
GUEST_USERNAME = "guest"
NOT_AUTHENTICATED_ERROR = "Request could not be authenticated. No secure cookie found."
NO_REFERER_ERROR = "The request header does not specify a referer and this is required for CORS access."
MAPBOX_USER = "blishten"
MBAT = "sk.eyJ1IjoiYmxpc2h0ZW4iLCJhIjoiY2piNm1tOGwxMG9lajMzcXBlZDR4aWVjdiJ9.Z1Jq4UAgGpXukvnUReLO1g"
SERVER_CONFIG_FILENAME = "server.dat"
USER_DATA_FILENAME = "user.dat"
PROJECT_DATA_FILENAME = "input.dat"
OUTPUT_LOG_FILENAME = "output_log.dat"
PLANNING_UNITS_FILENAME ="pu.dat"
PUVSPR_FILENAME = "puvspr.dat"
SPEC_FILENAME ="spec.dat"
BOUNDARY_LENGTH_FILENAME = "bounds.dat"
BEST_SOLUTION_FILENAME = "output_mvbest"
OUTPUT_SUMMARY_FILENAME = "output_sum"
SUMMED_SOLUTION_FILENAME = "output_ssoln"
FEATURE_PREPROCESSING_FILENAME = "feature_preprocessing.dat"
PROTECTED_AREA_INTERSECTIONS_FILENAME = "protected_area_intersections.dat"
SOLUTION_FILE_PREFIX = "output_r"
MISSING_VALUES_FILE_PREFIX = "output_mv"

####################################################################################################################################################################################################################################################################
## generic functions that dont belong to a class so can be called by subclasses of tornado.web.RequestHandler and tornado.websocket.WebSocketHandler equally - underscores are used so they dont mask the equivalent url endpoints
####################################################################################################################################################################################################################################################################

#run when the server starts to set all of the global path variables
def _setGlobalVariables():
    global MARXAN_FOLDER
    global MARXAN_USERS_FOLDER
    global MARXAN_CLIENT_BUILD_FOLDER
    global CLUMP_FOLDER 
    global MARXAN_EXECUTABLE 
    global MARXAN_WEB_RESOURCES_FOLDER
    global START_PROJECT_FOLDER 
    global EMPTY_PROJECT_TEMPLATE_FOLDER 
    global OGR2OGR_EXECUTABLE
    global MARXAN_SERVER_VERSION
    global MARXAN_CLIENT_VERSION
    global CONNECTION_STRING 
    global COOKIE_RANDOM_VALUE
    global PERMITTED_DOMAINS
    global SERVER_NAME
    global SERVER_DESCRIPTION
    global DATABASE_NAME
    global DATABASE_HOST
    global DATABASE_USER
    global DATABASE_PASSWORD
    global DATABASE_VERSION_POSTGRESQL
    global DATABASE_VERSION_POSTGIS
    #initialise colorama to be able to show log messages on windows in color
    colorama.init()
    #get the folder from this files path
    MARXAN_FOLDER = os.path.dirname(os.path.realpath(__file__)) + os.sep
    #get the data in the server configuration file
    serverData = _getKeyValuesFromFile(MARXAN_FOLDER + SERVER_CONFIG_FILENAME)
    #get the database connection string
    SERVER_NAME = serverData['SERVER_NAME']
    SERVER_DESCRIPTION = serverData['SERVER_DESCRIPTION']
    DATABASE_NAME = serverData['DATABASE_NAME']
    DATABASE_HOST = serverData['DATABASE_HOST']
    DATABASE_USER = serverData['DATABASE_USER']
    DATABASE_PASSWORD = serverData['DATABASE_PASSWORD']
    DATABASE_NAME = serverData['DATABASE_NAME']
    CONNECTION_STRING = "dbname='" + DATABASE_NAME + "' host='" + DATABASE_HOST + "' user='" + DATABASE_USER + "' password='" + DATABASE_PASSWORD + "'"
    #get the database version
    postgis = PostGIS()
    DATABASE_VERSION_POSTGRESQL, DATABASE_VERSION_POSTGIS = postgis.execute("SELECT version(), PostGIS_Version();", None, "One")  
    COOKIE_RANDOM_VALUE = serverData['COOKIE_RANDOM_VALUE']
    PERMITTED_DOMAINS = serverData['PERMITTED_DOMAINS'].split(",")
    #OUTPUT THE INFORMATION ABOUT THE MARXAN-SERVER SOFTWARE
    try:
        pos = MARXAN_FOLDER.index("marxan-server-")
        MARXAN_SERVER_VERSION = MARXAN_FOLDER[pos + 14:-1]
        print "\x1b[1;32;48mStarting marxan-server v" + MARXAN_SERVER_VERSION + " ..\x1b[0m"
    except (ValueError):
        MARXAN_SERVER_VERSION = "Unknown"
        print '\n\x1b[1;32;48mStarting marxan-server.. (version unknown)\x1b[0m'
    #print out which operating system is being used
    print " Running under " + platform.system() + " operating system"
    print " Database connection: " + CONNECTION_STRING
    print " " + DATABASE_VERSION_POSTGRESQL
    print " PostGIS: " + DATABASE_VERSION_POSTGIS
    print " Python executable: " + sys.executable
    #get the path to the ogr2ogr file - it should be in the miniconda bin folder 
    if platform.system() == "Windows":
        ogr2ogr_executable = "ogr2ogr.exe"
        OGR2OGR_PATH = os.path.dirname(sys.executable) + os.sep + "library" + os.sep + "bin" + os.sep # sys.executable is the Python.exe file and will likely be in C:\Users\a_cottam\Miniconda2 folder - ogr2ogr is then in /library/bin on windows
        marxan_executable = "Marxan.exe"
    else:
        ogr2ogr_executable = "ogr2ogr"
        OGR2OGR_PATH = os.path.dirname(sys.executable) + os.sep # sys.executable is the Python.exe file and will likely be in /home/ubuntu//miniconda2/bin/ - the same place as ogr2ogr
        marxan_executable = "MarOpt_v243_Linux64"
    #if the ogr2ogr executable path is not in the miniconda bin directory, then hard-code it here and uncomment the line
    #OGR2OGR_PATH = ""
    OGR2OGR_EXECUTABLE = OGR2OGR_PATH + ogr2ogr_executable
    if not os.path.exists(OGR2OGR_EXECUTABLE):
        raise MarxanServicesError("The path to the ogr2ogr executable '" + OGR2OGR_EXECUTABLE + "' could not be found. Set it manually in the webAPI_tornado.py file.")
    else:
        print " ogr2ogr executable: " + OGR2OGR_EXECUTABLE
    #set the various folder paths
    MARXAN_USERS_FOLDER = MARXAN_FOLDER + "users" + os.sep
    CLUMP_FOLDER = MARXAN_USERS_FOLDER + "_clumping" + os.sep
    MARXAN_EXECUTABLE = MARXAN_FOLDER + marxan_executable
    MARXAN_WEB_RESOURCES_FOLDER = MARXAN_FOLDER + "_marxan_web_resources" + os.sep
    START_PROJECT_FOLDER = MARXAN_WEB_RESOURCES_FOLDER + "Start project" + os.sep
    EMPTY_PROJECT_TEMPLATE_FOLDER = MARXAN_WEB_RESOURCES_FOLDER + "empty_project" + os.sep
    print " Marxan executable: " + MARXAN_EXECUTABLE
    print "\x1b[1;32;48mStarted " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S") + "\x1b[0m\n"
    print "\x1b[1;31;48mPress CTRL+Break to stop the server\x1b[0m\n"
    #time.sleep(3)
    #get the parent folder
    PARENT_FOLDER = MARXAN_FOLDER[:MARXAN_FOLDER[:-1].rindex(os.sep)] + os.sep 
    #OUTPUT THE INFORMATION ABOUT THE MARXAN-CLIENT SOFTWARE IF PRESENT
    client_installs = glob.glob(PARENT_FOLDER + "marxan-client*")
    if len(client_installs)>0:
        if (len(client_installs)>1):
            MARXAN_CLIENT_BUILD_FOLDER = client_installs[len(client_installs)-1] + os.sep + "build"
            print "Multiple versions of the marxan-client found"
        else:
            MARXAN_CLIENT_BUILD_FOLDER = client_installs[0] + os.sep + "build"
        MARXAN_CLIENT_VERSION = MARXAN_CLIENT_BUILD_FOLDER[MARXAN_CLIENT_BUILD_FOLDER.rindex("-")+1:MARXAN_CLIENT_BUILD_FOLDER.rindex(os.sep)]
        print "Using marxan-client v" + MARXAN_CLIENT_VERSION 
    else:
        MARXAN_CLIENT_BUILD_FOLDER = ""
        MARXAN_CLIENT_VERSION = "Not installed"
        print "marxan-client not installed\n"
        
#gets that method part of the REST service path, e.g. /marxan-server/validateUser will return validateUser
def _getRESTMethod(path):
    pos = path.rfind("/")
    if pos > -1:
        return path[pos+1:] 
    else:
        return ""
    
#creates a new user
def _createUser(obj, user, fullname, email, password, mapboxaccesstoken):
    #get the list of users
    users = _getUsers()
    if user in users:
        raise MarxanServicesError("User '" + user + "' already exists")
    #create the user folder
    obj.folder_user = MARXAN_USERS_FOLDER + user + os.sep
    os.mkdir(obj.folder_user)
    #copy the user.dat file
    shutil.copyfile(MARXAN_WEB_RESOURCES_FOLDER + USER_DATA_FILENAME, obj.folder_user + USER_DATA_FILENAME)
    #update the user.dat file parameters
    _updateParameters(obj.folder_user + USER_DATA_FILENAME, {'NAME': fullname,'EMAIL': email,'PASSWORD': password,'MAPBOXACCESSTOKEN': mapboxaccesstoken})

#gets a simple list of users
def _getUsers():
    #get a list of folders underneath the marxan users folder
    user_folders = glob.glob(MARXAN_USERS_FOLDER + "*/")
    #convert these into a list of users
    users = [user[:-1][user[:-1].rfind(os.sep)+1:] for user in user_folders]
    if "input" in users: 
        users.remove("input")
    if "output" in users: 
        users.remove("output")
    if "MarxanData" in users: 
        users.remove("MarxanData")
    if "MarxanData_unix" in users: 
        users.remove("MarxanData_unix")
    return [u for u in users if u[:1] != "_"]
    
def _getUsersData(users):
    #gets all the users data for the passed users
    users.sort()
    usersData = []
    #create a extendable object to hold the user data
    tmpObj = ExtendableObject()
    #iterate through the users
    for user in users:
        tmpObj.folder_user = MARXAN_USERS_FOLDER + user + os.sep
        #get the data for the user
        _getUserData(tmpObj)
        #create a dict to save the data
        combinedDict = tmpObj.userData.copy() # pylint:disable=no-member
        combinedDict.update({'user': user})
        usersData.append(combinedDict)
    return usersData         
    
#gets the projects for the specified user
def _getProjectsForUser(user):
    #get a list of folders underneath the users home folder
    project_folders = glob.glob(MARXAN_USERS_FOLDER + user + os.sep + "*/")
    #sort the folders
    project_folders.sort()
    projects = []
    #iterate through the project folders and get the parameters for each project to return
    tmpObj = ExtendableObject()
    for dir in project_folders:
        #get the name of the folder 
        project = dir[:-1][dir[:-1].rfind(os.sep)+1:]
        if (project[:2] != "__"): #folders beginning with __ are system folders
            #get the data from the input file for this project
            tmpObj.project = project
            tmpObj.folder_project = MARXAN_USERS_FOLDER + user + os.sep + project + os.sep
            _getProjectData(tmpObj)
            #create a dict to save the data
            projects.append({'user': user, 'name': project,'description': tmpObj.projectData["metadata"]["DESCRIPTION"],'createdate': tmpObj.projectData["metadata"]["CREATEDATE"],'oldVersion': tmpObj.projectData["metadata"]["OLDVERSION"],'private': tmpObj.projectData["metadata"]["PRIVATE"]}) # pylint:disable=no-member
    return projects

#gets all projects for all users
def _getAllProjects():
    allProjects = []
    #get a list of users
    users = _getUsers()
    #get the data for each user
    _getUsersData(users)
    for user in users:
        projects = _getProjectsForUser(user)
        allProjects.extend(projects)
    return allProjects

#gets the projects for the current user
def _getProjects(obj):
    if ((obj.user == GUEST_USERNAME) or (obj.get_secure_cookie("role") == "Admin")):
        obj.projects = _getAllProjects()
    else:
        obj.projects = _getProjectsForUser(obj.user)

#creates a new empty project with the passed parameters
def _createProject(obj, name):
    #make sure the project does not already exist
    if os.path.exists(obj.folder_user + name):
        raise MarxanServicesError("The project '" + name + "' already exists")
    #copy the _project_template folder to the new location
    _copyDirectory(EMPTY_PROJECT_TEMPLATE_FOLDER, obj.folder_user + name)
    #set the paths to this project in the passed object - the arguments are normally passed as lists in tornado.get_argument
    _setFolderPaths(obj, {'user': [obj.user], 'project': [name]})

#deletes a project
def _deleteProject(obj):
    #delete the folder and all of its contents
    try:
        shutil.rmtree(obj.folder_project)
    except (WindowsError) as e: # pylint:disable=undefined-variable
        raise MarxanServicesError(e.strerror)

#clones a project from the source_folder which is a full folder path to the destination_folder which is a full folder path
def _cloneProject(source_folder, destination_folder):
    #get the project name
    original_project_name = source_folder[:-1].split(os.sep)[-1]
    #get the new project folder
    new_project_folder = destination_folder + original_project_name + os.sep
    #recursively check that the folder does not exist until we get a new folder that doesnt exist
    while (os.path.exists(new_project_folder)):
        new_project_folder = new_project_folder[:-1] + "_copy" + os.sep
    #copy the project
    shutil.copytree(source_folder, new_project_folder)
    #update the description and create date
    _updateParameters(new_project_folder + PROJECT_DATA_FILENAME, {'DESCRIPTION': "Clone of project '" + original_project_name + "'",  'CREATEDATE': datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S")})
    #return the name of the new project
    return new_project_folder[:-1].split(os.sep)[-1]

#sets the various paths to the users folder and project folders using the request arguments in the passed object
def _setFolderPaths(obj, arguments):
    if "user" in arguments.keys():
        user = arguments["user"][0]
        obj.folder_user = MARXAN_USERS_FOLDER + user + os.sep
        obj.user = user
        #get the project folder and the input and output folders
        if "project" in arguments.keys():
            obj.folder_project = obj.folder_user + arguments["project"][0] + os.sep
            obj.folder_input =  obj.folder_project + "input" + os.sep
            obj.folder_output = obj.folder_project + "output" + os.sep
            obj.project = obj.get_argument("project")

#get the project data from the input.dat file as a categorised list of settings - using the obj.folder_project path and creating an attribute called projectData in the obj for the return data
def _getProjectData(obj):
    paramsArray = []
    filesDict = {}
    metadataDict = {}
    rendererDict = {}
    #get the file contents
    s = _readFileUnicode(obj.folder_project + PROJECT_DATA_FILENAME)
    #get the keys from the file
    keys = _getKeys(s)
    #iterate through the keys and get their values
    for k in keys:
        #some parameters we do not need to return
        if k in ["PUNAME","SPECNAME","PUVSPRNAME","BOUNDNAME","BLOCKDEF"]: # Input Files section of input.dat file
            key, value = _getKeyValue(s, k) 
            filesDict.update({ key:  value})
        elif k in ['BLM', 'PROP', 'RANDSEED', 'NUMREPS', 'NUMITNS', 'STARTTEMP', 'NUMTEMP', 'COSTTHRESH', 'THRESHPEN1', 'THRESHPEN2', 'SAVERUN', 'SAVEBEST', 'SAVESUMMARY', 'SAVESCEN', 'SAVETARGMET', 'SAVESUMSOLN', 'SAVEPENALTY', 'SAVELOG', 'RUNMODE', 'MISSLEVEL', 'ITIMPTYPE', 'HEURTYPE', 'CLUMPTYPE', 'VERBOSITY', 'SAVESOLUTIONSMATRIX']:
            key, value = _getKeyValue(s, k) #run parameters 
            paramsArray.append({'key': key, 'value': value})
        elif k in ['DESCRIPTION','CREATEDATE','PLANNING_UNIT_NAME','OLDVERSION','IUCN_CATEGORY','PRIVATE']: # metadata section of the input.dat file
            key, value = _getKeyValue(s, k)
            metadataDict.update({key: value})
            if k=='PLANNING_UNIT_NAME':
                df2 = PostGIS().getDataFrame("select * from marxan.get_planning_units_metadata(%s)", [value])
                if (df2.shape[0] == 0):
                    metadataDict.update({'pu_alias': value,'pu_description': 'No description','pu_domain': 'Unknown domain','pu_area': 'Unknown area','pu_creation_date': 'Unknown date'})
                else:
                    #get the data from the metadata_planning_units table
                    metadataDict.update({'pu_alias': df2.iloc[0]['alias'],'pu_description': df2.iloc[0]['description'],'pu_domain': df2.iloc[0]['domain'],'pu_area': df2.iloc[0]['area'],'pu_creation_date': df2.iloc[0]['creation_date']})

        elif k in ['CLASSIFICATION', 'NUMCLASSES','COLORCODE', 'TOPCLASSES','OPACITY']: # renderer section of the input.dat file
            key, value = _getKeyValue(s, k)
            rendererDict.update({key: value})
    #set the project data
    obj.projectData = {}
    obj.projectData.update({'project': obj.project, 'metadata': metadataDict, 'files': filesDict, 'runParameters': paramsArray, 'renderer': rendererDict})
    
#gets the name of the input file from the projects input.dat file using the obj.folder_project path
def _getProjectInputFilename(obj, fileToGet):
    if not hasattr(obj, "projectData"):
        _getProjectData(obj)
    return obj.projectData["files"][fileToGet]

#gets the projects input data using the fileToGet, e.g. SPECNAME will return the data from the file corresponding to the input.dat file SPECNAME setting
def _getProjectInputData(obj, fileToGet, errorIfNotExists = False):
    filename = obj.folder_input + os.sep + _getProjectInputFilename(obj, fileToGet)
    return _loadCSV(filename, errorIfNotExists)

#gets the key/value pairs from a text file as a dictionary
def _getKeyValuesFromFile(filename):
    if not os.path.exists(filename):
        raise MarxanServicesError("The file '" + filename +"' does not exist") 
    #get the file contents
    s = _readFileUnicode(filename)
    #get the keys from the file
    keys = _getKeys(s)
    #iterate through the keys, get their values and add them to a dictionary
    data = {}
    for k in keys:
        key, value = _getKeyValue(s, k)
        #update the  dict
        if value == "true":
            value = True
        if value == "false":
            value = False
        data[key] = value
    return data

#gets the server data
def _getServerData(obj):
    #get the data from the server configuration file - these key/values are changed by the marxan-client
    obj.serverData = _getKeyValuesFromFile(MARXAN_FOLDER + SERVER_CONFIG_FILENAME)
    #set the return values: permitted CORS domains - these are set in this Python module; the server os and hardware; the version of the marxan-server software
    obj.serverData.update({"DATABASE_VERSION_POSTGIS": DATABASE_VERSION_POSTGIS, "DATABASE_VERSION_POSTGRESQL": DATABASE_VERSION_POSTGRESQL, "SYSTEM": platform.system(), "NODE": platform.node(), "RELEASE": platform.release(), "VERSION": platform.version(), "MACHINE": platform.machine(), "PROCESSOR": platform.processor(), "MARXAN_SERVER_VERSION": MARXAN_SERVER_VERSION,"MARXAN_CLIENT_VERSION": MARXAN_CLIENT_VERSION, "SERVER_NAME": SERVER_NAME, "SERVER_DESCRIPTION": SERVER_DESCRIPTION})
        
#get the data on the user from the user.dat file 
def _getUserData(obj):
    data = _getKeyValuesFromFile(obj.folder_user + USER_DATA_FILENAME)
    #set the userData attribute on this object
    obj.userData = data

#get the species data from the spec.dat file as a DataFrame (and joins it to the data from the PostGIS database if it is the Marxan web version)
def _getSpeciesData(obj):
    #get the values from the spec.dat file - speciesDataFilename will be empty if it doesn't exist yet
    df = _getProjectInputData(obj, "SPECNAME")
    #create the output data frame using the id field as an index
    output_df = df.set_index("id")
    #add the index as a column
    output_df['oid'] = output_df.index
    #see if the version of marxan is the old version
    if obj.projectData["metadata"]["OLDVERSION"]:
        #return the data from the spec.dat file with additional fields manually added
        output_df['tmp'] = 'Unique identifer: '
        output_df['alias'] = output_df['tmp'].str.cat((output_df['oid']).apply(str)) # returns: 'Unique identifer: 4702435'
        output_df['feature_class_name'] = output_df['oid']
        output_df['description'] = "No description"
        output_df['creation_date'] = "Unknown"
        output_df['area'] = -1
        output_df['tilesetid'] = ''
        try:
            output_df = output_df[["alias", "feature_class_name", "description", "creation_date", "area", "tilesetid", "prop", "spf", "oid"]]
        except (KeyError) as e:
            raise MarxanServicesError("Unable to load spec.dat data. " + e.message + ". Column names: " + ",".join(df.columns.to_list()).encode('unicode_escape')) #.encode('unicode_escape') in case there are tab characters which will be escaped to \\t
    else:
        #get the postgis feature data
        df2 = PostGIS().getDataFrame("select * from marxan.get_features()")
        #join the species data to the PostGIS data
        output_df = output_df.join(df2.set_index("oid"))
    #rename the columns that are sent back to the client as the names of various properties are different in Marxan compared to the web client
    output_df = output_df.rename(index=str, columns={'prop': 'target_value', 'oid':'id'})    
    #get the target as an integer - Marxan has it as a percentage, i.e. convert 0.17 -> 17
    output_df['target_value'] = (output_df['target_value'] * 100).astype(int)
    obj.speciesData = output_df
        
#gets data for a single feature
def _getFeature(obj, oid):
    obj.data = PostGIS().getDataFrame("SELECT * FROM marxan.get_feature(%s)", [oid])

#get all species information from the PostGIS database
def _getAllSpeciesData(obj):
    obj.allSpeciesData = PostGIS().getDataFrame("select oid::integer id,feature_class_name , alias , description , _area area, extent, to_char(creation_date, 'Dy, DD Mon YYYY HH24:MI:SS')::text as creation_date, tilesetid, source from marxan.metadata_interest_features order by alias;")

#get the information about which species have already been preprocessed
def _getSpeciesPreProcessingData(obj):
    obj.speciesPreProcessingData = _loadCSV(obj.folder_input + FEATURE_PREPROCESSING_FILENAME)

#get the planning units information
def _getPlanningUnitsData(obj):
    df = _getProjectInputData(obj, "PUNAME")
    #normalise the planning unit data to make the payload smaller        
    obj.planningUnitsData = _normaliseDataFrame(df, "status", "id")

#get the protected area intersections information
def _getProtectedAreaIntersectionsData(obj):
    df = _loadCSV(obj.folder_input + PROTECTED_AREA_INTERSECTIONS_FILENAME)
    #normalise the protected area intersections to make the payload smaller           
    obj.protectedAreaIntersectionsData = _normaliseDataFrame(df, "iucn_cat", "puid")
    
#gets the marxan log after a run
def _getMarxanLog(obj):
    if (os.path.exists(obj.folder_output + OUTPUT_LOG_FILENAME)):
        log = _readFileUnicode(obj.folder_output + OUTPUT_LOG_FILENAME)
    else:
        log = ""
    obj.marxanLog = log

#the extension of the output files depends on the settings SAVE* in the input.dat file and probably on the version of marxan. This function gets the correct filename+extension (normally either csv or txt)
def _getOutputFilename(filename):
    #filename is the full filename without an extension
    files = glob.glob(filename + "*") 
    if (len(files)) > 0:
        extension = files[0][-4:]
        return filename + extension
    else:
        raise MarxanServicesError("The output file '" + filename + "' does not exist")

#loads the data from the marxan best solution file
def _getBestSolution(obj):
    filename = _getOutputFilename(obj.folder_output + BEST_SOLUTION_FILENAME)
    obj.bestSolution = _loadCSV(filename)

#loads the data from the marxan output summary file
def _getOutputSummary(obj):
    filename = _getOutputFilename(obj.folder_output + OUTPUT_SUMMARY_FILENAME)
    obj.outputSummary = _loadCSV(filename)

#loads the data from the marxan summed solution file
def _getSummedSolution(obj):
    filename = _getOutputFilename(obj.folder_output + SUMMED_SOLUTION_FILENAME)
    df = _loadCSV(filename)
    obj.summedSolution = _normaliseDataFrame(df, "number", "planning_unit")

#loads the data from a marxan single solution file
def _getSolution(obj, solutionId):
    filename = _getOutputFilename(obj.folder_output + SOLUTION_FILE_PREFIX + "%05d" % int(solutionId))
    if os.path.exists(filename):
        df = _loadCSV(filename)
        #normalise the data by the planning unit field and solution field - these may be called planning_unit,solution or PUID,SOLUTION - so get their names by position 
        obj.solution = _normaliseDataFrame(df, df.columns[1], df.columns[0])
    else:
        obj.solution = []
        raise MarxanServicesError("Solution '" + str(solutionId) + "' in project '" + obj.get_argument('project') + "' no longer exists")
        
def _getMissingValues(obj, solutionId):
    df = _loadCSV(obj.folder_output + MISSING_VALUES_FILE_PREFIX + "%05d" % int(solutionId) + ".txt")
    obj.missingValues = df.to_dict(orient="split")["data"]

#updates/creates the spec.dat file with the passed interest features
def _updateSpeciesFile(obj, interest_features, target_values, spf_values, create = False):
    #get the features to create/update as a list of integer ids
    ids = _txtIntsToList(interest_features)
    props = _txtIntsToList(target_values) 
    spfs = spf_values.split(",") 
    if create:
        #there are no existing ids as we are creating a new pu.dat file
        removedIds = []    
    else:
        #get the current list of features
        df = _getProjectInputData(obj, "SPECNAME")
        if df.empty:
            currentIds = []
        else:
            currentIds = df.id.unique().tolist() 
        #get the list of features to remove from the current list (i.e. they are not in the passed list of interest features)
        removedIds = list(set(currentIds) - set(ids))
        #update the puvspr.dat file and the feature preprocessing files to remove any species that are no longer in the project
        if len(removedIds) > 0:
            #get the name of the puvspr file from the project data
            puvsprFilename = _getProjectInputFilename(obj, "PUVSPRNAME")
            #update the puvspr.dat file
            _deleteRecordsInTextFile(obj.folder_input + puvsprFilename, "species", removedIds, False)
            #update the preprocessing.dat file to remove any species that are no longer in the project - these will need to be preprocessed again
            _deleteRecordsInTextFile(obj.folder_input + FEATURE_PREPROCESSING_FILENAME, "id", removedIds, False)
    #create the dataframe to write to file
    records = []
    for i in range(len(ids)):
        if i not in removedIds:
            records.append({'id': ids[i], 'prop': str(float(props[i])/100), 'spf': spfs[i]})
    df = pandas.DataFrame(records)
    #sort the records by the id field
    df = df.sort_values(by=['id'])
    #write the data to file
    _writeCSV(obj, "SPECNAME", df)

#create the array of the puids 
def _puidsArrayToPuDatFormat(puid_array, pu_status):
    return pandas.DataFrame([[int(i),pu_status] for i in puid_array], columns=['id','status_new']).astype({'id':'int64','status_new':'int64'})

#creates the pu.dat file using the ids from the PostGIS feature class as the planning unit ids in the pu.dat file
def _createPuFile(obj, planning_grid_name):
    #get the path to the pu.dat file
    filename = obj.folder_input + PLANNING_UNITS_FILENAME
    #create the pu.dat file using a postgis query
    PostGIS().executeToText(sql.SQL("COPY (SELECT puid as id,1::double precision as cost,0::integer as status FROM marxan.{}) TO STDOUT WITH CSV HEADER;").format(sql.Identifier(planning_grid_name)), filename)
    #update the input.dat file
    _updateParameters(obj.folder_project + PROJECT_DATA_FILENAME, {'PUNAME': PLANNING_UNITS_FILENAME})

#updates the pu.dat file with the passed arrays of ids for the various statuses
def _updatePuFile(obj, status1_ids, status2_ids, status3_ids):
    status1 = _puidsArrayToPuDatFormat(status1_ids,1)
    status2 = _puidsArrayToPuDatFormat(status2_ids,2)
    status3 = _puidsArrayToPuDatFormat(status3_ids,3)
    #read the data from the pu.dat file 
    df = _getProjectInputData(obj, "PUNAME")
    #reset the status for all planning units
    df['status'] = 0
    #concatenate the status arrays
    df2 = pandas.concat([status1, status2, status3])
    #join the new statuses to the ones from the pu.dat file
    df = df.merge(df2, on='id', how='left')
    #update the status value
    df['status_final'] = df['status_new'].fillna(df['status']).astype('int')
    df = df.drop(['status_new', 'status'], axis=1)
    df.rename(columns={'status_final':'status'}, inplace=True)
    #set the datatypes
    df = df.astype({'id':'int64','cost':'int64','status':'int64'})
    #sort the records by the id fied
    df = df.sort_values(by=['id'])
    #write to file
    _writeCSV(obj, "PUNAME", df)
    
#loads a csv file and returns the data as a dataframe or an empty dataframe if the file does not exist. If errorIfNotExists is True then it raises an error.
def _loadCSV(filename, errorIfNotExists = False):
    if (os.path.exists(filename)):
        df = pandas.read_csv(filename, sep = None, engine = 'python') #sep = None forces the Python parsing engine to detect the separator as it can be tab or comman in marxan
    else:
        if errorIfNotExists:
            raise MarxanServicesError("The file '" + filename + "' does not exist")
        else:
            df = pandas.DataFrame()
    return df

#saves the dataframe to a csv file specified by the fileToWrite, e.g. _writeCSV(self, "PUVSPRNAME", df) - this only applies to the files managed by Marxan in the input.dat file, e.g. SPECNAME, PUNAME, PUVSPRNAME, BOUNDNAME
def _writeCSV(obj, fileToWrite, df, writeIndex = False):
    _filename = _getProjectInputFilename(obj, fileToWrite)
    if _filename == "": #the file has not previously been created
        raise MarxanServicesError("The filename for the " + fileToWrite + ".dat file has not been set in the input.dat file")
    df.to_csv(obj.folder_input + _filename, index = writeIndex)

#writes the dataframe to the file - for files not managed in the input.dat file or if the filename has not yet been set in the input.dat file
def _writeToDatFile(file, dataframe):
    #see if the file exists
    if (os.path.exists(file)):
        #read the current data
        df = pandas.read_csv(file, sep = None, engine = 'python') #sep = None forces the Python parsing engine to detect the separator as it can be tab or comman in marxan
    else:
        #create the new dataframe
        df = pandas.DataFrame()
    #append the new records
    df = df.append(dataframe)
    #write the file
    df.to_csv(file, index=False)
    
def _writeFile(filename, data):
    f = open(filename, 'wb')
    f.write(data)
    f.close()
    
#gets a files contents as a string
def _readFile(filename):
    f = open(filename)
    s = f.read()
    f.close()
    return s

#gets a files contents as a unicode string
def _readFileUnicode(filename):
    f = io.open(filename, mode="r", encoding="utf-8")
    s = f.read()
    return s

#writes a files contents as a unicode string
def _writeFileUnicode(filename, s):
    f = io.open(filename, 'w', encoding="utf-8")
    f.write(s)
    f.close()    
    
#deletes all of the files in the passed folder
def _deleteAllFiles(folder):
    files = glob.glob(folder + "*")
    for f in files:
        if f[:-3]!='dat': #dont try to remove the log file as it is accessed by the runMarxan function to return the data as it is written
            os.remove(f)

#copies a directory from src to dest recursively
def _copyDirectory(src, dest):
    try:
        shutil.copytree(src, dest)
    # Directories are the same
    except shutil.Error as e:
        raise MarxanServicesError('Directory not copied. Error: %s' % e)
    # Any error saying that the directory doesn't exist
    except OSError as e:
        raise MarxanServicesError('Directory not copied. Error: %s' % e)
        
#updates the parameters in the *.dat file with the new parameters passed as a dict
def _updateParameters(data_file, newParams):
    if newParams:
        #get the existing parameters 
        s = _readFileUnicode(data_file)
        #update any that are passed in as query params
        for k, v in newParams.iteritems():
            try:
                p1 = s.index(k) #get the first position of the parameter
                if p1>-1:
                    p2 = _getEndOfLine(s[p1:]) #get the position of the end of line
                    s = s[:p1] + k + " " + v + s[(p1 + p2):]
                #write these parameters back to the *.dat file
                _writeFileUnicode(data_file, s)
            except ValueError:
                continue
    return 

#gets the position of the end of the line which may be different in windows/unix generated files
def _getEndOfLine(text):
    try:
        p = text.index("\r\n")  #windows uses carriage return + line feed
    except (ValueError):
        p = text.index("\n") #unix uses just line feed
    return p

#returns all the keys from a set of KEY/VALUE pairs in a string expression
def _getKeys(s):
    #get all the parameter keys
    matches = re.findall('\\n[A-Z1-9_]{2,}', s, re.DOTALL) #this will match against both windows and unix line endings, e.g. \r\n and \n
    return [m[1:] for m in matches]
  
#gets the key value combination from the text, e.g. PUNAME pu.dat    
def _getKeyValue(text, parameterName):
    p1 = text.index(parameterName)
    #the end of line marker could either be a \r\n or a \n - get the position of both and see which is the first
    try:    
        pCrLf = text[p1:].index("\r\n")
    except (ValueError):
        pCrLf = -1
    pLf = text[p1:].index("\n")
    if pCrLf > -1:
        if pLf > -1:
            if pLf < pCrLf:
                p2 = pLf
            else:
                p2 = pCrLf
    else:
        p2 = pLf
    value = text[p1 + len(parameterName) + 1:(p2 + p1)] 
    #convert any boolean text strings to boolean values - these will then get returned as javascript bool types
    if value == "True":
        value = True
    if value == "False":
        value = False
    return parameterName, value

#converts a data frame with duplicate values into a normalised array
def _normaliseDataFrame(df, columnToNormaliseBy, puidColumnName):
    if df.empty:
        return []
    #get the groups from the data
    groups = df.groupby(by = columnToNormaliseBy).groups
    #build the response, e.g. a normal data frame with repeated values in the columnToNormaliseBy -> [["VI", [7, 8, 9]], ["IV", [0, 1, 2, 3, 4]], ["V", [5, 6]]]
    response = [[g, df[puidColumnName][groups[g]].values.tolist()] for g in groups if g not in [0]]
    return response

#gets the statistics for a species from the puvspr.dat file, i.e. count and area, as a dataframe record
def _getPuvsprStats(df, speciesId):
    #get the count of intersecting planning units
    pu_count = df[df.species.isin([speciesId])].agg({'pu' : ['count']})['pu'].iloc[0]
    #get the total area of the feature across all planning units
    pu_area = df[df.species.isin([speciesId])].agg({'amount': ['sum']})['amount'].iloc[0]
    #return the pu_area and pu_count to the preprocessing.dat file 
    return pandas.DataFrame({'id':speciesId, 'pu_area': [pu_area], 'pu_count': [pu_count]}).astype({'id': 'int', 'pu_area':'float', 'pu_count':'int'})
            
#deletes the records in the text file that have id values that match the passed ids
def _deleteRecordsInTextFile(filename, id_columnname, ids, write_index):
    if (filename) and (os.path.exists(filename)):
        #if the file exists then get the existing data
        df = _loadCSV(filename)
        #remove the records with the matching ids
        df = df[~df[id_columnname].isin(ids)]
        #write the results back to the file
        df.to_csv(filename, index = write_index)
    else:
        raise MarxanServicesError("The file '" + filename + "' does not exist")

#converts a comma-separated set of integer values to a list of integers
def _txtIntsToList(txtInts):
    if txtInts:
        return [int(s) for s in txtInts.split(",")] 
    else:
        return []

#checks that all of the arguments in argumentList are in the arguments dictionary
def _validateArguments(arguments, argumentList):
    for argument in argumentList:
        if argument not in arguments.keys():
            raise MarxanServicesError("Missing input argument:" + argument)

#converts the raw arguments from the request.arguments parameter into a simple dict excluding those in omitArgumentList
#e.g. _getSimpleArguments(self, ['user','project','callback']) would convert {'project': ['Tonga marine 30km2'], 'callback': ['__jp13'], 'COLORCODE': ['PiYG'], 'user': ['andrew']} to {'COLORCODE': 'PiYG'}
def _getSimpleArguments(obj, omitArgumentList):
    returnDict = {}
    for argument in obj.request.arguments:
        if argument not in omitArgumentList:
            returnDict.update({argument: obj.get_argument(argument)}) #get_argument gets the argument as unicode - HTTPRequest.arguments gets it as a byte string
    return returnDict

#gets the passed argument name as an array of integers, e.g. ['12,15,4,6'] -> [12,15,4,6]
def _getIntArrayFromArg(arguments, argName):
    if argName in arguments.keys():
        return [int(s) for s in arguments[argName][0].split(",")]
    else:
        return []
    
#creates a zip file with the list of files in the folder with the filename zipfilename
def _createZipfile(lstFileNames, folder, zipfilename):
    with zipfile.ZipFile(folder + zipfilename, 'w') as myzip:
        for f in lstFileNames:   
            arcname = os.path.split(f)[1]
            myzip.write(f,arcname)

#deletes a zip file and the archive files, e.g. deleteZippedShapefile(MARXAN_FOLDER, "pngprovshapes.zip","pngprov")
def _deleteZippedShapefile(folder, zipfile, archivename):
    files = glob.glob(folder + archivename + '.*')
    if len(files)>0:
        [os.remove(f) for f in files if f[-3:] in ['shx','shp','xml','sbx','prj','sbn','zip','dbf','cpg','qpj']]       
    if (os.path.exists(folder + zipfile)):
        os.remove(folder + zipfile)

#unzips a zip file
def _unzipFile(filename):
    #unzip the shapefile
    if not os.path.exists(MARXAN_FOLDER + filename):
        raise MarxanServicesError("The zip file '" + filename + "' does not exist")
    zip_ref = zipfile.ZipFile(MARXAN_FOLDER + filename, 'r')
    filenames = zip_ref.namelist()
    rootfilename = filenames[0][:-4]
    zip_ref.extractall(MARXAN_FOLDER)
    zip_ref.close()
    return rootfilename

def _uploadTilesetToMapbox(feature_class_name, mapbox_layer_name):
    #create the file to upload to MapBox - now using shapefiles as kml files only import the name and description properties into a mapbox tileset
    cmd = OGR2OGR_EXECUTABLE + ' -f "ESRI Shapefile" ' + MARXAN_FOLDER + feature_class_name + '.shp' + ' "PG:host=' + DATABASE_HOST + ' dbname=' + DATABASE_NAME + ' user=' + DATABASE_USER + ' password=' + DATABASE_PASSWORD + '" -sql "select * from Marxan.' + feature_class_name + '" -nln ' + mapbox_layer_name + ' -s_srs EPSG:3410 -t_srs EPSG:3857'
    try:
        subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
    #catch any unforeseen circumstances
    except subprocess.CalledProcessError as e:
        raise MarxanServicesError("Error exporting shapefile. " + e.output)
    #zip the shapefile to upload to Mapbox
    lstFilenames = glob.glob(MARXAN_FOLDER + feature_class_name + '.*')
    zipfilename = MARXAN_FOLDER + feature_class_name + ".zip"
    _createZipfile(lstFilenames, MARXAN_FOLDER, feature_class_name + ".zip")
    #upload to mapbox
    uploadId = _uploadTileset(zipfilename, feature_class_name)
    #delete the temporary shapefile file and zip file
    _deleteZippedShapefile(MARXAN_FOLDER, feature_class_name + ".zip", feature_class_name)
    return uploadId
    
#uploads a tileset to mapbox using the filename of the file (filename) to upload and the name of the resulting tileset (_name)
def _uploadTileset(filename, _name):
    #create an instance of the upload service
    service = Uploader(access_token=MBAT)    
    with open(filename, 'rb') as src:
        upload_resp = service.upload(src, _name)
        upload_id = upload_resp.json()['id']
        return upload_id
        
#deletes a tileset 
def _deleteTileset(tilesetid):
    url = "https://api.mapbox.com/tilesets/v1/" + MAPBOX_USER + "." + tilesetid + "?access_token=" + MBAT
    response = requests.delete(url)    
        
#deletes a feature
def _deleteFeature(feature_class_name):
    #delete the feature class
    postgis = PostGIS()
    postgis.execute(sql.SQL("DROP TABLE IF EXISTS marxan.{};").format(sql.Identifier(feature_class_name)))
    #delete the record in the metadata_interest_features
    postgis.execute("DELETE FROM marxan.metadata_interest_features WHERE feature_class_name =%s;", [feature_class_name])
    #delete the Mapbox tileset
    _deleteTileset(feature_class_name)
    
def _getUniqueFeatureclassName(prefix):
    return prefix + uuid.uuid4().hex[:(32 - len(prefix))] #mapbox tileset ids are limited to 32 characters
    
#imports the feature from a zipped shapefile (given by filename)
def _importFeature(filename, name, description):
    #unzip the shapefile
    rootfilename = _unzipFile(filename) 
    #get a unique feature class name for the import
    feature_class_name = _getUniqueFeatureclassName("f_")
    try:
        #import the shapefile into a PostGIS undissolved feature class in EPSG:3410
        postgis = PostGIS()
        postgis.importShapefile(rootfilename + ".shp", "undissolved", "EPSG:3410")
        #finish the import by dissolving the undissolved feature class
        id = _importUndissolvedFeature(feature_class_name, name, description, "Import shapefile")
        #upload the feature class to Mapbox
        uploadId = _uploadTileset(MARXAN_FOLDER + filename, feature_class_name)
    except (MarxanServicesError):
        raise
    else:
        #no error so delete the shapefile and the zip file
        _deleteZippedShapefile(MARXAN_FOLDER, filename, rootfilename)
    finally:
        pass
    return {'feature_class_name': feature_class_name, 'uploadId': uploadId, 'id': id}

#imports the undissolved feature class into the marxan schema with the featureclassname and inserts a record in the metadata_interest_features table
def _importUndissolvedFeature(featureclassname, name, description, source):
    #get the Mapbox tilesetId 
    tilesetId = MAPBOX_USER + "." + featureclassname
    #dissolve the feature class
    postgis = PostGIS()
    postgis.execute(sql.SQL("SELECT ST_Union(geometry) geometry INTO marxan.{} FROM marxan.undissolved;").format(sql.Identifier(featureclassname)))   
    #create an index
    postgis.execute(sql.SQL("CREATE INDEX idx_" + uuid.uuid4().hex + " ON marxan.{} USING GIST (geometry);").format(sql.Identifier(featureclassname)))
    #drop the undissolved feature class
    postgis.execute("DROP TABLE IF EXISTS marxan.undissolved;") 
    #create a record for this new feature in the metadata_interest_features table
    id = postgis.execute(sql.SQL("INSERT INTO marxan.metadata_interest_features (feature_class_name, alias, description, creation_date, _area, tilesetid, extent, source) SELECT %s, %s, %s, now(), sub._area, %s, sub.extent, %s FROM (SELECT ST_Area(geometry) _area, box2d(ST_Transform(ST_SetSRID(geometry,3410),4326)) extent FROM marxan.{} GROUP BY geometry) AS sub RETURNING oid;").format(sql.Identifier(featureclassname)), [featureclassname, name, description, tilesetId, source], "One")[0]
    return id

#imports the planning unit grid from a zipped shapefile (given by filename) and starts the upload to Mapbox - this is for importing marxan old version files
def _importPlanningUnitGrid(filename, name, description):
    #unzip the shapefile and get the name of the shapefile without an extension, e.g. PlanningUnitsData.zip -> planningunits.shp -> planningunits
    rootfilename = _unzipFile(filename)
    #get a unique feature class name for the import
    feature_class_name = _getUniqueFeatureclassName("pu_")
    #make sure the puid column is lowercase
    if _shapefileHasField(MARXAN_FOLDER + rootfilename + ".shp", "PUID"):
        raise MarxanServicesError("The field 'puid' in the zipped shapefile is uppercase and it must be lowercase")
    try:
        #import the shapefile into PostGIS
        postgis = PostGIS()
        #create a record for this new feature in the metadata_planning_units table
        postgis.execute("INSERT INTO marxan.metadata_planning_units(feature_class_name,alias,description,creation_date, source) VALUES (%s,%s,%s,now(),'Imported from shapefile');", [feature_class_name, name, description])
        #import the shapefile
        postgis.importShapefile(rootfilename + ".shp", feature_class_name, "EPSG:3410")
        #create the envelope for the new planning grid
        postgis.execute(sql.SQL("UPDATE marxan.metadata_planning_units SET envelope = (SELECT ST_Transform(ST_Envelope(ST_Collect(f.geometry)), 4326) FROM (SELECT ST_Envelope(geometry) AS geometry FROM marxan.{}) AS f) WHERE feature_class_name = %s;").format(sql.Identifier(feature_class_name)), [feature_class_name])
        #start the upload to mapbox
        uploadId = _uploadTileset(MARXAN_FOLDER + filename, feature_class_name)
    except (MarxanServicesError):
        raise
    else:
        #delete the shapefile and the zip file
        _deleteZippedShapefile(MARXAN_FOLDER, filename, rootfilename)
    finally:
        pass
    return {'feature_class_name': feature_class_name, 'uploadId': uploadId}
    
#populates the data in the feature_preprocessing.dat file from an existing puvspr.dat file, e.g. after an import from an old version of Marxan
def _createFeaturePreprocessingFileFromImport(obj):
    #load the puvspr data
    df = _getProjectInputData(obj, "PUVSPRNAME")
    #calculate the statistics for all features - each record will have the species id, the sum of the planning unit areas for that species and the count of the planning units
    pivotted = df.pivot_table(index=['species'], aggfunc=['sum','count'], values='amount')
    #flatten the pivot table
    pivotted.columns = pivotted.columns.to_series().str.join('_')
    #create a field called id which has the same values as the species column
    pivotted['id'] = pivotted.index
    #reorder the columns
    pivotted = pivotted[['id', 'sum_amount', 'count_amount']]
    #rename the columns
    pivotted.columns = ['id','pu_area','pu_count']
    #output the file
    pivotted.to_csv(obj.folder_input + FEATURE_PREPROCESSING_FILENAME, index = False)
    
#detects whether the request is for a websocket from a tornado.httputil.HTTPServerRequest
def _requestIsWebSocket(request):
    if "upgrade" in request.headers:
        if request.headers["upgrade"] == "websocket":
            return True
        else:
            return False
    else:
        return True

#to prevent CORS errors in the client
def _checkCORS(obj):
    #no CORS policy if security is disabled or if the server is running on localhost or if the request is for a permitted method
    # or if the user is 'guest' (if this is enabled) - dont set any headers - this will only work for GET requests - cross-domwin POST requests must have the headers
    if (obj.request.method == "GET" or DISABLE_SECURITY or obj.request.host[:9] == "localhost" or (obj.current_user == GUEST_USERNAME)):
        return 
    #get the referer
    if "Referer" in obj.request.headers.keys():
        #get the referer url, e.g. https://marxan-client-blishten.c9users.io:8081/ or https://beta.biopama.org/marxan-client/build/
        referer = obj.request.headers.get("Referer")
        #get the origin
        parsed = urlparse(referer) 
        origin = parsed.scheme + "://" + parsed.netloc
        #check the origin is permitted either by being in the list of permitted domains or if the referer and host are on the same machine, i.e. not cross domain
        if (origin in PERMITTED_DOMAINS) or (referer.find(obj.request.host_name)!=-1):
            #if so, write the headers
            obj.set_header("Access-Control-Allow-Origin", origin)
            obj.set_header("Access-Control-Allow-Credentials", "true")
        else:
            raise HTTPError(403, "The origin '" + origin + "' does not have permission to access the service (CORS error)") #, reason = "The origin '" + referer + "' does not have permission to access the service (CORS error)"
    else:
        raise HTTPError(403, NO_REFERER_ERROR)

#test all requests to make sure the user is authenticated - if not returns a 403
def _authenticate(obj):
    if DISABLE_SECURITY:
        return 
    #check for an authenticated user
    if not obj.current_user: 
        #if not return a 401
        raise HTTPError(401, NOT_AUTHENTICATED_ERROR)

#tests the role has access to the method
def _authoriseRole(obj, method):
    if DISABLE_SECURITY:
        return 
    #get the requested role
    role = obj.get_secure_cookie("role")
    #get the list of methods that this role cannot access
    unauthorised = ROLE_UNAUTHORISED_METHODS[role]
    if method in unauthorised:
        raise HTTPError(403, "The '" + role + "' role does not have permission to access the '" + method + "' service")

#tests if the user can access the service - Admin users can access projects belonging to other users
def _authoriseUser(obj):
    if DISABLE_SECURITY:
        return 
    #if the call includes a user argument
    if "user" in obj.request.arguments.keys():
        #see if the user argument matches the obj.current_user and is not the _clumping project (this is the only exception as it is needed for the clumping)
        if ((obj.get_argument("user") != obj.current_user) and (obj.get_argument("user") != "_clumping") and (obj.current_user != GUEST_USERNAME)):
            #get the requested role
            role = obj.get_secure_cookie("role")
            if role != "Admin":
                raise HTTPError(403, "The user '" + obj.current_user + "' has no permission to access a project of another user")    
    
#returns a boolean indicating whether the guest user is enabled on this server
def _guestUserEnabled(obj):
    _getServerData(obj)
    #get the current state
    return obj.serverData['ENABLE_GUEST_USER']
    
#returns true if the passed shapefile has the fieldname - this is case sensitive
def _shapefileHasField(shapefile, fieldname):
    ogr.UseExceptions()
    try:
        dataSource = ogr.Open(shapefile)
        daLayer = dataSource.GetLayer(0)
    except (RuntimeError) as e:
        raise MarxanServicesError(e.message)
    else:
        layerDefinition = daLayer.GetLayerDefn()
        count = layerDefinition.GetFieldCount()
        for i in range(count):
            if (layerDefinition.GetFieldDefn(i).GetName() == fieldname):
                return True
    return False

####################################################################################################################################################################################################################################################################
## generic classes
####################################################################################################################################################################################################################################################################

class MarxanServicesError(Exception):
    """Exception Class that allows the Marxan Services REST Server to raise custom exceptions"""
    pass

class ExtendableObject(object):
    pass

####################################################################################################################################################################################################################################################################
## class to return data from postgis synchronously - the asynchronous version is the QueryWebSocketHandler class
####################################################################################################################################################################################################################################################################

class PostGIS():
    def __init__(self):
        #get a connection to the database
        self.connection = psycopg2.connect(CONNECTION_STRING)
        self.cursor = self.connection.cursor()

    #does argument binding to prevent sql injection attacks
    def _mogrify(self, sql, data):
        if data is not None:
            return self.cursor.mogrify(sql, data)
        else:
            return sql
    
    #get a pandas data frame 
    def _getDataFrame(self, sql, data):
        #do any argument binding 
        sql = self._mogrify(sql, data)
        return pandas.read_sql_query(sql, self.connection)

    #called in exceptions to close the cursor and connection
    def _cleanup(self):
        self.cursor.close()
        # self.connection.commit()
        self.connection.close()
        
    #executes a query and returns the data as a data frame
    def getDataFrame(self, sql, data = None):
        return self._getDataFrame(sql, data)

    #executes a query and returns the data as a records array
    def getDict(self, sql, data = None):
        df = self._getDataFrame(sql, data)
        return df.to_dict(orient="records")
            
    #executes a query and returns the first records as specified by the numberToFetch parameter
    def execute(self, sql, data = None, numberToFetch = "None", commitImmediately = True):
        try:
            records = []
            #do any argument binding 
            sql = self._mogrify(sql, data)
            self.cursor.execute(sql)
            #commit the transaction immediately
            if commitImmediately:
                self.connection.commit()
            if numberToFetch == "One":
                records = self.cursor.fetchone()
            elif numberToFetch == "All":
                records = self.cursor.fetchall()
            return records
        except Exception as e:
            self._cleanup()
            raise MarxanServicesError(e.message)
    
    #executes a query and writes the results to a text file
    def executeToText(self, sql, filename):
        try:
            with open(filename, 'w') as f:
                self.cursor.copy_expert(sql, f)
                self.connection.commit()
        except Exception as e:
            self._cleanup()
            raise MarxanServicesError(e.message)
        
    #imports a shapefile into PostGIS
    def importShapefile(self, shapefile, feature_class_name, epsgCode):
        try:
            #drop the feature class if it already exists
            self.execute(sql.SQL("DROP TABLE IF EXISTS marxan.{};").format(sql.Identifier(feature_class_name)))
            #using ogr2ogr produces an additional field - the ogc_fid field which is an autonumbering oid. Here we import into the marxan schema and rename the geometry field from the default (wkb_geometry) to geometry
            cmd = OGR2OGR_EXECUTABLE + ' -f "PostgreSQL" PG:"host=' + DATABASE_HOST + ' user=' + DATABASE_USER + ' dbname=' + DATABASE_NAME + ' password=' + DATABASE_PASSWORD + '" ' + MARXAN_FOLDER + shapefile + ' -nlt GEOMETRY -lco SCHEMA=marxan -lco GEOMETRY_NAME=geometry -nln ' + feature_class_name + ' -t_srs ' + epsgCode
            #run the import
            subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        #catch any unforeseen circumstances
        except subprocess.CalledProcessError as e:
            raise MarxanServicesError("Error importing shapefile.\n" + e.output)
        except Exception as e:
            if not self.connection.closed:
                self._cleanup()
            raise MarxanServicesError(e.message)
                
    #creates a primary key on the column in the passed feature_class
    def createPrimaryKey(self, feature_class_name, column):
        try:
            self.execute(sql.SQL("ALTER TABLE marxan.{tbl} ADD CONSTRAINT {key} PRIMARY KEY ({col});").format(tbl=sql.Identifier(feature_class_name), key=sql.Identifier("idx_" + uuid.uuid4().hex), col=sql.Identifier(column)))
        except Exception as e:
            raise MarxanServicesError(e.message)
        
    def __del__(self):
        self._cleanup()

####################################################################################################################################################################################################################################################################
## baseclass for handling REST requests
####################################################################################################################################################################################################################################################################

class MarxanRESTHandler(tornado.web.RequestHandler):
    #to prevent CORS errors in the client
    def set_default_headers(self):
        if DISABLE_SECURITY:
            self.set_header("Access-Control-Allow-Origin", "*")

    #get the current user
    def get_current_user(self):
        return self.get_secure_cookie("user")

    #called before the request is processed - does the neccessary authentication/authorisation
    def prepare(self):
        #check the referer can call the REST end point from their domain
        _checkCORS(self)
        #get the requested method
        method = _getRESTMethod(self.request.path)
        #allow access to some methods without authentication/authorisation, e.g. to create new users or validate a user
        if method not in PERMITTED_METHODS:
            #check the request is authenticated
            _authenticate(self)
            #check the users role has access to the requested service
            _authoriseRole(self, method)
            #check the user has access to the specific resource, i.e. the 'User' role cannot access projects from other users
            _authoriseUser(self)
            #instantiate the response dictionary
            self.response = {}
        #set the folder paths for the user and optionally project
        _setFolderPaths(self, self.request.arguments)
        # self.send_response({"error": repr(e)})
    
    #used by all descendent classes to write the return payload and send it
    def send_response(self, response):
        try:
            #set the return header as json
            self.set_header('Content-Type','application/json')
            #convert the response dictionary to json
            content = json.dumps(response)
        #sometimes the Marxan log causes json encoding issues
        except (UnicodeDecodeError) as e: 
            if 'log' in response.keys():
                response.update({"log": "Server warning: Unable to encode the Marxan log. <br/>" + repr(e), "warning": "Unable to encode the Marxan log"})
                content = json.dumps(response)        
        finally:
            if "callback" in self.request.arguments.keys():
                self.write(self.get_argument("callback") + "(" + content + ")")
            else:
                self.write(content)
    
    #uncaught exception handling that captures any exceptions in the descendent classes and writes them back to the client - RETURNING AN HTTP STATUS CODE OF 200 CAN BE CAUGHT BY JSONP
    def write_error(self, status_code, **kwargs):
        if "exc_info" in kwargs:
            trace = ""
            for line in traceback.format_exception(*kwargs["exc_info"]):
                trace = trace + line
            lastLine = traceback.format_exception(*kwargs["exc_info"])[len(traceback.format_exception(*kwargs["exc_info"]))-1]
            #when an error is encountered, the headers are reset causing CORS errors - so set them again here
            if not DISABLE_SECURITY:
                try:
                    _checkCORS(self) #may throw a 403
                except: #so handle the exception
                    pass
            # self.set_status(status_code) #this will return an HTTP server error rather than a 200 status code
            self.set_status(200)
            self.send_response({"error": lastLine, "trace" : trace})
            self.finish()
    
####################################################################################################################################################################################################################################################################
## RequestHandler subclasses
####################################################################################################################################################################################################################################################################

#toggles whether the guest user is enabled or not on this server
class toggleEnableGuestUser(MarxanRESTHandler):
    def get(self):
        _getServerData(self)
        #get the current state
        enabled = self.serverData['ENABLE_GUEST_USER']
        if enabled:
            enabledString = "False"
        else:
            enabledString = "True"
        _updateParameters(MARXAN_FOLDER + SERVER_CONFIG_FILENAME, {"ENABLE_GUEST_USER": enabledString})
        #set the response
        self.send_response({'enabled': not enabled})
        
#creates a new user
#POST ONLY
class createUser(MarxanRESTHandler):
    def post(self):
        #validate the input arguments 
        _validateArguments(self.request.arguments, ["user","password", "fullname", "email", "mapboxaccesstoken"])  
        #create the user
        _createUser(self, self.get_argument('user'), self.get_argument('fullname'), self.get_argument('email'), self.get_argument('password'), self.get_argument('mapboxaccesstoken'))
        #copy the start project into the users folder
        _cloneProject(START_PROJECT_FOLDER, MARXAN_USERS_FOLDER + self.get_argument('user') + os.sep)
        #set the response
        self.send_response({'info': "User '" + self.get_argument('user') + "' created"})

#creates a project
#POST ONLY
class createProject(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','description','planning_grid_name','interest_features','target_values','spf_values'])  
        #create the empty project folder
        _createProject(self, self.get_argument('project'))
        #update the projects parameters
        _updateParameters(self.folder_project + PROJECT_DATA_FILENAME, {'DESCRIPTION': self.get_argument('description'), 'CREATEDATE': datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S"), 'PLANNING_UNIT_NAME': self.get_argument('planning_grid_name')})
        #create the spec.dat file
        _updateSpeciesFile(self, self.get_argument("interest_features"), self.get_argument("target_values"), self.get_argument("spf_values"), True)
        #create the pu.dat file
        _createPuFile(self, self.get_argument('planning_grid_name'))
        #set the response
        self.send_response({'info': "Project '" + self.get_argument('project') + "' created", 'name': self.get_argument('project'), 'user': self.get_argument('user')})

#creates a simple project for the import wizard
#POST ONLY
class createImportProject(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])  
        #create the empty project folder
        _createProject(self, self.get_argument('project'))
        #set the response
        self.send_response({'info': "Project '" + self.get_argument('project') + "' created", 'name': self.get_argument('project')})

#updates a project from the Marxan old version to the new version
#https://db-server-blishten.c9users.io:8081/marxan-server/upgradeProject?user=andrew&project=test2&callback=__jp7
class upgradeProject(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])  
        #get the projects existing data from the input.dat file
        old = _readFileUnicode(self.folder_project + PROJECT_DATA_FILENAME)
        #get an empty projects data
        new = _readFileUnicode(EMPTY_PROJECT_TEMPLATE_FOLDER + PROJECT_DATA_FILENAME)
        #everything from the 'DESCRIPTION No description' needs to be added
        pos = new.find("DESCRIPTION No description")
        if pos > -1:
            newText = new[pos:]
            old = old + "\n" + newText
            _writeFileUnicode(self.folder_project + PROJECT_DATA_FILENAME, old)
        else:
            raise MarxanServicesError("Unable to update the old version of Marxan to the new one")
        #populate the feature_preprocessing.dat file using data in the puvspr.dat file
        _createFeaturePreprocessingFileFromImport(self)
        #delete the contents of the output folder
        _deleteAllFiles(self.folder_output)
        #set the response
        self.send_response({'info': "Project '" + self.get_argument("project") + "' updated", 'project': self.get_argument("project")})

#deletes a project
#https://db-server-blishten.c9users.io:8081/marxan-server/deleteProject?user=andrew&project=test2&callback=__jp7
class deleteProject(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])  
        #get the existing projects
        _getProjects(self)
        if len(self.projects) == 1:
            raise MarxanServicesError("You cannot delete all projects")   
        _deleteProject(self)
        #set the response
        self.send_response({'info': "Project '" + self.get_argument("project") + "' deleted", 'project': self.get_argument("project")})

#clones the project
#https://db-server-blishten.c9users.io:8081/marxan-server/cloneProject?user=andrew&project=Tonga%20marine%2030km2&callback=__jp15
class cloneProject(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])  
        #clone the folder recursively
        clonedName = _cloneProject(self.folder_project, self.folder_user)
        #set the response
        self.send_response({'info': "Project '" + clonedName + "' created", 'name': clonedName})

#creates n clones of the project with a range of BLM values in the _clumping folder
#https://db-server-blishten.c9users.io:8081/marxan-server/createProjectGroup?user=andrew&project=Tonga%20marine%2030km2&copies=5&blmValues=0.1,0.2,0.3,0.4,0.5&callback=__jp15
class createProjectGroup(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','copies','blmValues'])  
        #get the BLM values as a list
        blmValuesList = self.get_argument("blmValues").split(",")
        #initialise the project name array
        projects = []
        #clone the users project folder n times
        for i in range(int(self.get_argument("copies"))):
            #get the project name
            projectName = uuid.uuid4().hex
            #add the project name to the array
            projects.append({'projectName': projectName, 'clump': i})
            shutil.copytree(self.folder_project, CLUMP_FOLDER + projectName)
            #delete the contents of the output folder in that cloned project
            _deleteAllFiles(CLUMP_FOLDER + projectName + os.sep + "output" + os.sep)
            #update the BLM and NUMREP values in the project
            _updateParameters(CLUMP_FOLDER + projectName + os.sep + PROJECT_DATA_FILENAME, {'BLM': blmValuesList[i], 'NUMREPS': '1'})
        #set the response
        self.send_response({'info': "Project group created", 'data': projects})

#deletes a project cluster
#https://db-server-blishten.c9users.io:8081/marxan-server/deleteProjects?projectNames=2dabf1b862da4c2e87b2cd9d8b38bb73,81eda0a43a3248a8b4881caae160667a,313b0d3f733142e3949cf6129855be19,739f40f4d1c94907b2aa814470bcd7f7,15210235bec341238a816ce43eb2b341&callback=__jp15
class deleteProjects(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['projectNames'])  
        #get the project names
        projectNames = self.get_argument("projectNames").split(",")
        #delete the folders
        for projectName in projectNames:
            if os.path.exists(CLUMP_FOLDER + projectName):
                shutil.rmtree(CLUMP_FOLDER + projectName)        
        #set the response
        self.send_response({'info': "Projects deleted"})

#renames a project
#https://db-server-blishten.c9users.io:8081/marxan-server/renameProject?user=andrew&project=Tonga%20marine%2030km2&newName=Tonga%20marine%2030km&callback=__jp5
class renameProject(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','newName'])  
        #rename the folder
        os.rename(self.folder_project, self.folder_user + self.get_argument("newName"))
        #set the new name as the users last project so it will load on login
        _updateParameters(self.folder_user + USER_DATA_FILENAME, {'LASTPROJECT': self.get_argument("newName")})
        #set the response
        self.send_response({"info": "Project renamed to '" + self.get_argument("newName") + "'", 'project': self.get_argument("project")})

#https://db-server-blishten.c9users.io:8081/marxan-server/getCountries?callback=__jp0
class getCountries(MarxanRESTHandler):
    def get(self):
        content = PostGIS().getDict("SELECT iso3, original_n FROM marxan.gaul_2015_simplified_1km where original_n not like '%|%' and iso3 not like '%|%' order by 2;")
        self.send_response({'records': content})        

#https://db-server-blishten.c9users.io:8081/marxan-server/getPlanningUnitGrids?callback=__jp0
class getPlanningUnitGrids(MarxanRESTHandler):
    def get(self):
        content = PostGIS().getDict("SELECT feature_class_name ,alias ,description ,creation_date::text ,country_id ,aoi_id,domain,_area,ST_AsText(envelope) envelope, pu.source, original_n country FROM marxan.metadata_planning_units pu LEFT OUTER JOIN marxan.gaul_2015_simplified_1km ON id_country = country_id order by 2;")
        self.send_response({'info': 'Planning unit grids retrieved', 'planning_unit_grids': content})        
        
#https://db-server-blishten.c9users.io:8081/marxan-server/createPlanningUnitGrid?iso3=AND&domain=Terrestrial&areakm2=50&shape=hexagon&callback=__jp10        
class createPlanningUnitGrid(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['iso3','domain','areakm2','shape'])    
        #create the new planning unit and get the first row back
        data = PostGIS().execute("SELECT * FROM marxan.planning_grid(%s,%s,%s,%s);", [self.get_argument('areakm2'), self.get_argument('iso3'), self.get_argument('domain'), self.get_argument('shape')], "One")
        #get the feature class name
        fc = "pu_" + self.get_argument('iso3').lower() + "_" + self.get_argument('domain').lower() + "_" + self.get_argument('shape').lower() + "_" + self.get_argument('areakm2')
        #create a primary key so the feature class can be used in ArcGIS
        PostGIS().createPrimaryKey(fc, "puid")        
        #set the response
        self.send_response({'info':'Planning unit grid created', 'planning_unit_grid': data[0]})

#https://db-server-blishten.c9users.io:8081/marxan-server/deletePlanningUnitGrid?planning_grid_name=pu_sample&callback=__jp10        
class deletePlanningUnitGrid(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['planning_grid_name'])    
        postgis = PostGIS()
        #Delete the tileset on Mapbox only if the planning grid is an imported one - we dont want to delete standard country tilesets from Mapbox as they may be in use elsewhere
        records = postgis.execute("SELECT source FROM marxan.metadata_planning_units WHERE feature_class_name = %s;", [self.get_argument('planning_grid_name')], "One")
        if records:
            source = records[0]
            if (source != 'planning_grid function'):
                _deleteTileset(self.get_argument('planning_grid_name'))
            #delete the new planning unit record from the metadata_planning_units table
            postgis.execute("DELETE FROM marxan.metadata_planning_units WHERE feature_class_name = %s;", [self.get_argument('planning_grid_name')])
            #delete the feature class
            postgis.execute(sql.SQL("DROP TABLE IF EXISTS marxan.{};").format(sql.Identifier(self.get_argument('planning_grid_name'))))
            #set the response
            self.send_response({'info':'Planning grid deleted'})
        else:
            self.send_response({'info': "Nothing deleted - the planning grid does not exist"})

#validates a user with the passed credentials
#https://db-server-blishten.c9users.io:8081/marxan-server/validateUser?user=andrew&password=thargal88&callback=__jp2
class validateUser(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','password'])  
        #see if the guest user is enabled
        if ((not _guestUserEnabled(self)) and (self.get_argument("user") == GUEST_USERNAME)):
            raise MarxanServicesError("The guest user is not enabled on this server")        
        try:
            #get the user data from the user.dat file
            _getUserData(self)
        except (MarxanServicesError) as e:
            raise MarxanServicesError(e.message)
        #compare the passed password to the one in the user.dat file
        if self.get_argument("password") == self.userData["PASSWORD"]:
            #set a response cookie for the authenticated user
            self.set_secure_cookie("user", self.get_argument("user"), httponly = True) 
            #set a response cookie for the authenticated users role
            self.set_secure_cookie("role", self.userData["ROLE"], httponly = True)
            #set the response
            self.send_response({'info': "User " + self.user + " validated"})
        else:
            #invalid login
            raise MarxanServicesError("Invalid login")    

#resends the password to the passed email address (NOT CURRENTLY IMPLEMENTED)
class resendPassword(MarxanRESTHandler):
    def get(self):
        #set the response
        self.send_response({'info': 'Not currently implemented'})
        

#gets a users information from the user folder
#curl 'https://db-server-blishten.c9users.io:8081/marxan-server/getUser?user=andrew&callback=__jp1' -H 'If-None-Match: "0798406453417c47c0b5ab5bd11d56a60fb4df7d"' -H 'Accept-Encoding: gzip, deflate, br' -H 'Accept-Language: en-US,en;q=0.9,fr;q=0.8' -H 'User-Agent: Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/70.0.3538.110 Safari/537.36' -H 'Accept: */*' -H 'Referer: https://marxan-client-blishten.c9users.io:8081/' -H 'Cookie: c9.live.user.jwt=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjE2MzQxNDgiLCJuYW1lIjoiYmxpc2h0ZW4iLCJjb2RlIjoiOWNBUzdEQldsdWYwU2oyU01ZaEYiLCJpYXQiOjE1NDgxNDg0MTQsImV4cCI6MTU0ODIzNDgxNH0.yJ9mPz4bM7L3htL8vXVFMCcQpTO0pkRvhNHJP9WnJo8; c9.live.user.sso=eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpZCI6IjE2MzQxNDgiLCJuYW1lIjoiYmxpc2h0ZW4iLCJpYXQiOjE1NDgxNDg0MTQsImV4cCI6MTU0ODIzNDgxNH0.ifW5qlkpC19iyMNBgZLtGZzxuMRyHKWldGg3He-__gI; role="2|1:0|10:1548151226|4:role|8:QWRtaW4=|d703b0f18c81cf22c85f41c536f99589ce11492925d85833e78d3d66f4d7fd62"; user="2|1:0|10:1548151226|4:user|8:YW5kcmV3|e5ed3b87979273b1b8d1b8983310280507941fe05fb665847e7dd5dacf36348d"' -H 'Connection: keep-alive' --compressed
class getUser(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user'])    
        #get the user data from the user.dat file
        _getUserData(self)
        #get the permissions for the users role
        role = self.userData["ROLE"]
        unauthorised = ROLE_UNAUTHORISED_METHODS[role]
        #set the response
        self.send_response({'info': "User data received", "userData" : {k: v for k, v in self.userData.iteritems() if k != 'PASSWORD'}, "unauthorisedMethods": unauthorised})

#gets a list of all users
#https://db-server-blishten.c9users.io:8081/marxan-server/getUsers
class getUsers(MarxanRESTHandler):
    def get(self):
        #get the users
        users = _getUsers()
        #get all the data for those users
        usersData = _getUsersData(users)
        #set the response
        self.send_response({'info': 'Users data received', 'users': usersData})

#deletes a user
#https://db-server-blishten.c9users.io:8081/marxan-server/deleteUser?user=asd2
class deleteUser(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user']) 
        shutil.rmtree(self.folder_user)
        #set the response
        self.send_response({'info': 'User deleted'})
    
#gets project information from the input.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getProject?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getProject(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project']) 
        if (self.get_argument("user") == GUEST_USERNAME):
            self.send_response({'error': "Logged on as read-only guest user"})
        else:
            #see if the project exists
            if not os.path.exists(self.folder_project):
                raise MarxanServicesError("The project '" + self.get_argument("project") + "' does not exist")
            #if the project name is an empty string, then get the first project for the user
            if (self.get_argument("project") == ""):
                self.projects = _getProjectsForUser(self.get_argument("user"))
                project = self.projects[0]['name']
                #set the project argument
                self.request.arguments['project'] = [project]
                #and set the paths to this project
                _setFolderPaths(self, self.request.arguments)
            #get the project data from the input.dat file
            _getProjectData(self)
            #get the species data from the spec.dat file and the PostGIS database
            _getSpeciesData(self)
            #get the species preprocessing from the feature_preprocessing.dat file
            _getSpeciesPreProcessingData(self)
            #get the planning units information
            _getPlanningUnitsData(self)
            #get the protected area intersections
            _getProtectedAreaIntersectionsData(self)
            #set the project as the users last project so it will load on login - but only if the current user is loading one of their own projects
            if (self.current_user == self.get_argument("user")):
                _updateParameters(self.folder_user + USER_DATA_FILENAME, {'LASTPROJECT': self.get_argument("project")})
            #set the response
            self.send_response({'user': self.get_argument("user"), 'project': self.projectData["project"], 'metadata': self.projectData["metadata"], 'files': self.projectData["files"], 'runParameters': self.projectData["runParameters"], 'renderer': self.projectData["renderer"], 'features': self.speciesData.to_dict(orient="records"), 'feature_preprocessing': self.speciesPreProcessingData.to_dict(orient="split")["data"], 'planning_units': self.planningUnitsData, 'protected_area_intersections': self.protectedAreaIntersectionsData})

#gets feature information from postgis
#https://db-server-blishten.c9users.io:8081/marxan-server/getFeature?oid=63407942&callback=__jp2
class getFeature(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['oid'])    
        #get the data
        _getFeature(self, self.get_argument("oid"))
        #set the response
        self.send_response({"data": self.data.to_dict(orient="records")})

#gets the features planning unit ids from the puvspr.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getFeaturePlanningUnits?user=andrew&project=Tonga%20marine%2030Km2&oid=63407942&callback=__jp2
class getFeaturePlanningUnits(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','oid'])    
        #get the data from the puvspr.dat file as a dataframe
        df = _getProjectInputData(self, "PUVSPRNAME")
        #get the planning unit ids as a list
        puids = df.loc[df['species'] == int(self.get_argument("oid"))]['pu'].tolist()
        #set the response
        self.send_response({"data": puids})

#gets species information for a specific project from the spec.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getSpeciesData?user=andrew&project=Tonga%20marine%2030Km2&callback=__jp3
class getSpeciesData(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the species data from the spec.dat file and PostGIS
        _getSpeciesData(self)
        #set the response
        self.send_response({"data": self.speciesData.to_dict(orient="records")})

#gets all species information from the PostGIS database
#https://db-server-blishten.c9users.io:8081/marxan-server/getAllSpeciesData?callback=__jp2
class getAllSpeciesData(MarxanRESTHandler):
    def get(self):
        #get all the species data
        _getAllSpeciesData(self)
        #set the response
        self.send_response({"info": "All species data received", "data": self.allSpeciesData.to_dict(orient="records")})

#gets the species preprocessing information from the feature_preprocessing.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getSpeciesPreProcessingData?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getSpeciesPreProcessingData(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the species preprocessing data
        _getSpeciesPreProcessingData(self)
        #set the response
        self.send_response({"data": self.speciesPreProcessingData.to_dict(orient="split")["data"]})

#gets the planning units information from the pu.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getPlanningUnitsData?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getPlanningUnitsData(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the planning units information
        _getPlanningUnitsData(self)
        #set the response
        self.send_response({"data": self.planningUnitsData})

#gets the intersections of the planning units with the protected areas from the protected_area_intersections.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/getProtectedAreaIntersectionsData?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getProtectedAreaIntersectionsData(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the protected area intersections
        _getProtectedAreaIntersectionsData(self)
        #set the response
        self.send_response({"data": self.protectedAreaIntersectionsData})

#gets the Marxan log for the project
#https://db-server-blishten.c9users.io:8081/marxan-server/getMarxanLog?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getMarxanLog(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the log
        _getMarxanLog(self)
        #set the response
        self.send_response({"log": self.marxanLog})

#gets the best solution for the project
#https://db-server-blishten.c9users.io:8081/marxan-server/getBestSolution?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getBestSolution(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the best solution
        _getBestSolution(self)
        #set the response
        self.send_response({"data": self.bestSolution.to_dict(orient="split")["data"]})

#gets the output summary for the project
#https://db-server-blishten.c9users.io:8081/marxan-server/getOutputSummary?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getOutputSummary(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the output sum
        _getOutputSummary(self)
        #set the response
        self.send_response({"data": self.outputSummary.to_dict(orient="split")["data"]})

#gets the summed solution for the project
#https://db-server-blishten.c9users.io:8081/marxan-server/getSummedSolution?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getSummedSolution(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        #get the summed solution
        _getSummedSolution(self)
        #set the response
        self.send_response({"data": self.summedSolution})

#gets an individual solution
#https://db-server-blishten.c9users.io:8081/marxan-server/getSolution?user=andrew&project=Tonga%20marine%2030km2&solution=1&callback=__jp7
class getSolution(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','solution'])  
        #get the solution
        _getSolution(self, self.get_argument("solution"))
        #get the corresponding missing values file, e.g. output_mv00031.txt
        _getMissingValues(self, self.get_argument("solution"))
        #set the response
        self.send_response({'solution': self.solution, 'mv': self.missingValues, 'user': self.get_argument("user"), 'project': self.get_argument("project")})
 
#gets the missing values for a single solution
#https://db-server-blishten.c9users.io:8081/marxan-server/getMissingValues?user=andrew&project=Tonga%20marine%2030km2&solution=1&callback=__jp7
class getMissingValues(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','solution'])  
        #get the missing values file, e.g. output_mv00031.txt
        _getMissingValues(self, self.get_argument("solution"))
        #set the response
        self.send_response({'missingValues': self.missingValues})
 
#gets the combined results for the project
#https://db-server-blishten.c9users.io:8081/marxan-server/getResults?user=andrew&project=Tonga%20marine%2030km2&callback=__jp2
class getResults(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])    
        try:
            #get the log
            _getMarxanLog(self)
            #get the best solution
            _getBestSolution(self)
            #get the output sum
            _getOutputSummary(self)
            #get the summed solution
            _getSummedSolution(self)
            #set the response
            self.send_response({'info':'Results loaded', 'log': self.marxanLog, 'mvbest': self.bestSolution.to_dict(orient="split")["data"], 'summary':self.outputSummary.to_dict(orient="split")["data"], 'ssoln': self.summedSolution})
        except (MarxanServicesError):
            self.send_response({'info':'No results available'})

#gets the data from the server.dat file as an abject
class getServerData(MarxanRESTHandler):
    def get(self):
        #get the data from the server.dat file
        _getServerData(self)
        #delete sensitive information from the server config data
        del self.serverData['COOKIE_RANDOM_VALUE']
        del self.serverData['DATABASE_HOST']
        del self.serverData['DATABASE_NAME']
        del self.serverData['DATABASE_PASSWORD']
        del self.serverData['DATABASE_USER']
        #get the version of postgis
        
        #set the response
        self.send_response({'info':'Server data loaded', 'serverData': self.serverData})

#gets a list of projects for the user
#https://db-server-blishten.c9users.io:8081/marxan-server/getProjects?user=andrew&callback=__jp2
class getProjects(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user'])    
        #get the projects
        _getProjects(self)
        #set the response
        self.send_response({"projects": self.projects})

#updates the spec.dat file with the posted data
class updateSpecFile(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','interest_features','spf_values','target_values'])    
        #update the spec.dat file and other related files 
        _updateSpeciesFile(self, self.get_argument("interest_features"), self.get_argument("target_values"), self.get_argument("spf_values"))
        #set the response
        self.send_response({'info': "spec.dat file updated"})

#updates the pu.dat file with the posted data
class updatePUFile(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project']) 
        #get the ids for the different statuses
        status1_ids = _getIntArrayFromArg(self.request.arguments, "status1")
        status2_ids = _getIntArrayFromArg(self.request.arguments, "status2")
        status3_ids = _getIntArrayFromArg(self.request.arguments, "status3")
        #update the file 
        _updatePuFile(self, status1_ids, status2_ids, status3_ids)
        #set the response
        self.send_response({'info': "pu.dat file updated"})

#used to populate the feature_preprocessing.dat file from an imported puvspr.dat file
#https://db-server-blishten.c9users.io:8081/marxan-server/createFeaturePreprocessingFileFromImport?user=andrew&project=test&callback=__jp2
class createFeaturePreprocessingFileFromImport(MarxanRESTHandler): #not currently used
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project']) 
        #run the internal routine
        _createFeaturePreprocessingFileFromImport(self)
        #set the response
        self.send_response({'info': "feature_preprocessing.dat file populated"})

#updates parameters in the users user.dat file       
#POST ONLY
class updateUserParameters(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user'])  
        #get the parameters to update as a simple dict
        params = _getSimpleArguments(self, ['user','callback'])
        #update the parameters
        _updateParameters(self.folder_user + USER_DATA_FILENAME, params)
        #set the response
        self.send_response({'info': ",".join(params.keys()) + " parameters updated"})

#updates parameters in the projects input.dat file       
#POST ONLY
class updateProjectParameters(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project'])  
        #get the parameters to update as a simple dict
        params = _getSimpleArguments(self, ['user','project','callback'])
        #update the parameters
        _updateParameters(self.folder_project + PROJECT_DATA_FILENAME, params)
        #set the response
        self.send_response({'info': ",".join(params.keys()) + " parameters updated"})
        
#uploads a feature class with the passed feature class name to MapBox as a tileset using the MapBox Uploads API
#https://db-server-blishten.c9users.io:8081/marxan-server/uploadTilesetToMapBox?feature_class_name=pu_ton_marine_hexagon_20&mapbox_layer_name=hexagon&callback=__jp9
class uploadTilesetToMapBox(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['feature_class_name','mapbox_layer_name'])  
        uploadId = _uploadTilesetToMapbox(self.get_argument('feature_class_name'),self.get_argument('mapbox_layer_name'))
        #set the response for uploading to mapbox
        self.send_response({'info': "Tileset '" + self.get_argument('feature_class_name') + "' uploading",'uploadid': uploadId})
            
#uploads a shapefile to the marxan root folder
#POST ONLY 
class uploadShapefile(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['filename','name','description'])   
        #write the file to the server
        _writeFile(MARXAN_FOLDER + self.get_argument('filename'), self.request.files['value'][0].body)
        #set the response
        self.send_response({'info': "File '" + self.get_argument('filename') + "' uploaded", 'file': self.get_argument('filename')})
        
#saves an uploaded file to the filename - 3 input parameters: user, project, filename (relative) and the file itself as a request file
#POST ONLY 
class uploadFile(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['user','project','filename'])   
        #write the file to the server
        _writeFile(self.folder_project + self.get_argument('filename'), self.request.files['value'][0].body)
        #set the response
        self.send_response({'info': "File '" + self.get_argument('filename') + "' uploaded", 'file': self.get_argument('filename')})
            
#imports a shapefile which has been uploaded to the marxan root folder into PostGIS as a new feature dataset
#https://db-server-blishten.c9users.io:8081/marxan-server/importFeature?filename=netafu.zip&name=Netafu%20island%20habitat&description=Digitised%20in%20ArcGIS%20Pro&callback=__jp5
class importFeature(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['filename','name','description'])   
        #import the shapefile
        results = _importFeature(self.get_argument('filename'), self.get_argument('name'), self.get_argument('description'))
        #set the response
        self.send_response({'info': "File '" + self.get_argument('filename') + "' imported", 'file': self.get_argument('filename'), 'id': results['id'], 'feature_class_name': results['feature_class_name'], 'uploadId': results['uploadId']})

#deletes a feature from the PostGIS database
#https://db-server-blishten.c9users.io:8081/marxan-server/deleteFeature?feature_name=test_feature1&callback=__jp5
class deleteFeature(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['feature_name'])   
        _deleteFeature(self.get_argument('feature_name'))
        #set the response
        self.send_response({'info': "Feature deleted"})

#creates a new feature from a passed linestring 
class createFeatureFromLinestring(MarxanRESTHandler):
    def post(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['name','description','linestring']) 
        #create the undissolved feature class
        PostGIS().execute("DROP TABLE IF EXISTS marxan.undissolved")
        PostGIS().execute("CREATE TABLE marxan.undissolved AS SELECT ST_Transform(ST_SetSRID(ST_MakePolygon(%s)::geometry, 4326), 3410) AS geometry;",[self.get_argument('linestring')])
        #import the undissolved feature class
        feature_class_name = _getUniqueFeatureclassName("f_")
        id = _importUndissolvedFeature(feature_class_name, self.get_argument('name'), self.get_argument('description'), "Draw on screen")
        #start the upload to mapbox
        uploadId = _uploadTilesetToMapbox(feature_class_name, feature_class_name)
        #set the response
        self.send_response({'info': "Feature '" + feature_class_name + "' created", 'id': id, 'feature_class_name': feature_class_name, 'uploadId': uploadId})
        
#imports a zipped planning unit shapefile which has been uploaded to the marxan root folder into PostGIS as a planning unit grid feature class
#https://db-server-blishten.c9users.io:8081/marxan-server/importPlanningUnitGrid?filename=pu_sample.zip&name=pu_test&description=wibble&callback=__jp5
class importPlanningUnitGrid(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['filename','name','description'])   
        #import the shapefile
        data = _importPlanningUnitGrid(self.get_argument('filename'), self.get_argument('name'), self.get_argument('description'))
        #set the response
        self.send_response({'info': "File '" + self.get_argument('filename') + "' imported", 'feature_class_name': data['feature_class_name'], 'uploadId': data['uploadId']})

#kills a running marxan job
#https://db-server-blishten.c9users.io:8081/marxan-server/stopMarxan?pid=12345&callback=__jp5
class stopMarxan(MarxanRESTHandler):
    def get(self):
        #validate the input arguments
        _validateArguments(self.request.arguments, ['pid'])   
        try:
            os.kill(int(self.get_argument('pid')), signal.SIGTERM)
        except OSError:
            raise MarxanServicesError("The PID does not exist")
        else:
            self.send_response({'info': "PID '" + self.get_argument('pid') + "' terminated"})
            
#for testing role access to servivces            
#https://db-server-blishten.c9users.io:8081/marxan-server/testRoleAuthorisation&callback=__jp5
class testRoleAuthorisation(MarxanRESTHandler):
    def get(self):
        self.send_response({'info': "Service successful"})

#tests tornado is working properly
class testTornado(MarxanRESTHandler):
    def get(self):
        self.send_response({'info': "Tornado running"})

####################################################################################################################################################################################################################################################################
## baseclass for handling WebSockets
####################################################################################################################################################################################################################################################################

class MarxanWebSocketHandler(tornado.websocket.WebSocketHandler):
    #get the current user
    def get_current_user(self):
        return self.get_secure_cookie("user")

    #check CORS access for the websocket
    def check_origin(self, origin):
        if DISABLE_SECURITY:
            return True
        #the request is valid for CORS if the origin is in the list of permitted domains, or the origin is the same as the host, i.e. same machine
        parsed = urlparse(origin) # we need to get the host_name from the origin so parse it with urlparse
        if (origin in PERMITTED_DOMAINS) or (parsed.netloc.find(self.request.host_name)!=-1):
            return True
        else:
            raise HTTPError(403, "The origin '" + origin + "' does not have permission to access the service (CORS error)")

    #called when the websocket is opened - does authentication/authorisation then gets the folder paths for the user and optionally the project
    def open(self):
        #set the start time of the websocket
        self.startTime = datetime.datetime.now()
        #set the folder paths for the user and optionally project
        _setFolderPaths(self, self.request.arguments)
        #check the request is authenticated
        _authenticate(self)
        #get the requested method
        method = _getRESTMethod(self.request.path)
        #check the users role has access to the requested service
        _authoriseRole(self, method)
        #check the user has access to the specific resource, i.e. the 'User' role cannot access projects from other users
        _authoriseUser(self)

    #sends the message with a timestamp
    def send_response(self, message):
        if self.startTime: 
            elapsedtime = str((datetime.datetime.now() - self.startTime).seconds) + " seconds"
            message.update({'elapsedtime': elapsedtime})
        self.write_message(message)

####################################################################################################################################################################################################################################################################
## MarxanWebSocketHandler subclasses
####################################################################################################################################################################################################################################################################

#wss://db-server-blishten.c9users.io:8081/marxan-server/runMarxan?user=andrew&project=Tonga%20marine%2030km2
#starts a Marxan run on the server and streams back the output as websockets
class runMarxan(MarxanWebSocketHandler):
    #authenticate and get the user folder and project folders
    def open(self):
        try:
            super(runMarxan, self).open()
        except (HTTPError) as e:
            self.send_response({'error': e.reason, 'status': 'Finished'})
        else:
            self.send_response({'info': "Running Marxan", 'status':'Started'})
            #set the current folder to the project folder so files can be found in the input.dat file
            if (os.path.exists(self.folder_project)):
                os.chdir(self.folder_project)
                #delete all of the current output files
                _deleteAllFiles(self.folder_output)
                #run marxan 
                #the "exec " in front allows you to get the pid of the child process, i.e. marxan, and therefore to be able to kill the process using os.kill(pid, signal.SIGTERM) instead of the tornado process - see here: https://stackoverflow.com/questions/4789837/how-to-terminate-a-python-subprocess-launched-with-shell-true/4791612#4791612
                try:
                    if platform.system() != "Windows":
                        #in Unix operating systems, the log is streamed from stdout to a Tornado STREAM
                        self.marxanProcess = Subprocess(["exec " + MARXAN_EXECUTABLE], stdout=Subprocess.STREAM, stdin=subprocess.PIPE, shell=True)
                    else:
                        #the Subprocess.STREAM option does not work on Windows - see here: https://www.tornadoweb.org/en/stable/process.html?highlight=Subprocess#tornado.process.Subprocess
                        self.marxanProcess = Subprocess([MARXAN_EXECUTABLE], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                except (WindowsError) as e: # pylint:disable=undefined-variable
                    if (e.winerror == 1260):
                        self.send_response({'error': "The executable '" + MARXAN_EXECUTABLE + "' is blocked by group policy. For more information, contact your system administrator.", 'status': 'Finished','info':''})
                        #close the websocket
                        self.close()
                else:
                    #return the pid so that the process can be stopped
                    self.send_response({'pid': self.marxanProcess.pid, 'status':'pid'})
                    IOLoop.current().spawn_callback(self.stream_output)
                    self.marxanProcess.stdin.write('\n') # to end the marxan process by sending ENTER to the stdin
            else:
                self.send_response({'error': "Project '" + self.get_argument("project") + "' does not exist", 'status': 'Finished', 'project': self.get_argument("project"), 'user': self.get_argument("user")})
                #close the websocket
                self.close()

    @gen.coroutine
    def stream_output(self):
        if platform.system() != "Windows":
            try:
                while True:
                    #read from the stdout stream
                    print "getting a line at " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S") + "\x1b[0m" 
                    line = yield self.marxanProcess.stdout.read_bytes(1024, partial=True)
                    print "got a line at " + datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S") + "\x1b[0m\n" 
                    self.send_response({'info':line, 'status':'RunningMarxan'})
            except StreamClosedError: #fired when the stream closes
                self.send_response({'info': 'Run completed', 'status': 'Finished', 'project': self.get_argument("project"), 'user': self.get_argument("user")})
                #close the websocket
                self.close()
            except (Exception) as e:
                print "Unexpected Exception: " + e.message
        else:
            while True:
                #read from the stdout file object
                line = self.marxanProcess.stdout.readline()
                self.send_response({'info': line, 'status':'RunningMarxan'})
                #bit of a hack to see when it has finished running
                if line.find("Press return to exit") > -1:
                    break
            self.send_response({'info': 'Run completed', 'status': 'Finished', 'project': self.get_argument("project"), 'user': self.get_argument("user")})
            #close the websocket
            self.close()

####################################################################################################################################################################################################################################################################
## baseclass for handling long-running PostGIS queries using WebSockets
####################################################################################################################################################################################################################################################################

class QueryWebSocketHandler(MarxanWebSocketHandler):
    
    #authenticate and get the user folder and project folders
    def open(self):
        super(QueryWebSocketHandler, self).open()

    #required for asyncronous queries
    def wait(self):
        while 1:
            state = self.conn.poll()
            if state == psycopg2.extensions.POLL_OK:      #0
                break
            elif state == psycopg2.extensions.POLL_WRITE: #2
                select.select([], [self.conn.fileno()], [])
            elif state == psycopg2.extensions.POLL_READ:  #1
                select.select([self.conn.fileno()], [], [])
            else:
                raise psycopg2.OperationalError("poll() returned %s" % state)
                
    @gen.coroutine
    #runs a PostGIS query asynchronously, i.e. non-blocking
    def executeQueryAsynchronously(self, sql, data = None, startedMessage = "", processingMessage = "", finishedMessage = ""):
        try:
            self.send_response({'info': startedMessage, 'status':'Started'})
            #connect to postgis asyncronously
            self.conn = psycopg2.connect(CONNECTION_STRING, async = True)
            #wait for the connection to be ready
            self.wait()
            #get a cursor
            cur = self.conn.cursor()
            #parameter bind if necessary
            if data is not None:
                sql = cur.mogrify(sql, data)
                print cur.mogrify(sql, data)
            #execute the query
            cur.execute(sql)
            #poll to get the state of the query
            state = self.conn.poll()
            #poll at regular intervals to see if the query has finished
            while (state != psycopg2.extensions.POLL_OK):
                yield gen.sleep(1)
                state = self.conn.poll()
                self.send_response({'info': processingMessage, 'status':'RunningQuery'})
            #if the query returns data, then return the data
            if cur.description is not None:
                #get the column names for the query
                columns = [desc[0] for desc in cur.description]
                #get the query results
                records = cur.fetchall()
                #set the values on the current object
                self.queryResults = {}
                self.queryResults.update({'columns': columns, 'records': records})

        #handle any issues with the query syntax
        except (psycopg2.Error) as e:
            self.send_response({'error': e.pgerror, 'status':' RunningQuery'})
        #clean up code
        finally:
            cur.close()
            self.conn.close()
            self.send_response({'info': finishedMessage, 'status':'FinishedQuery'})

####################################################################################################################################################################################################################################################################
## WebSocket subclasses
####################################################################################################################################################################################################################################################################

#preprocesses the features by intersecting them with the planning units
#wss://db-server-blishten.c9users.io:8081/marxan-server/preprocessFeature?user=andrew&project=Tonga%20marine%2030km2&planning_grid_name=pu_ton_marine_hexagon_30&feature_class_name=volcano&alias=volcano&id=63408475
class preprocessFeature(QueryWebSocketHandler):

    #run the preprocessing
    def open(self):
        try:
            super(preprocessFeature, self).open()
        except (HTTPError) as e:
            self.send_response({'error': e.reason, 'status': 'Finished'})
        else:
            _validateArguments(self.request.arguments, ['user','project','id','feature_class_name','alias','planning_grid_name'])    
            #get the project data
            _getProjectData(self)
            if (not self.projectData["metadata"]["OLDVERSION"]):
                #new version of marxan - do the intersection
                future = self.executeQueryAsynchronously("SELECT * FROM marxan.get_pu_areas_for_interest_feature(%s,%s);", [self.get_argument('planning_grid_name'),self.get_argument('feature_class_name')], "Preprocessing '" + self.get_argument('alias') + "'", "  Preprocessing..", "  Preprocessing finished")
                future.add_done_callback(self.intersectionComplete) # pylint:disable=no-member
            else:
                #pass None as the Future object to the callback for the old version of marxan
                self.intersectionComplete(None) 

    #callback which is called when the intersection has been done
    def intersectionComplete(self, future):
        #get an empty dataframe 
        d = {'amount':pandas.Series([], dtype='float64'), 'species':pandas.Series([], dtype='int64'), 'pu':pandas.Series([], dtype='int64')}
        emptyDataFrame = pandas.DataFrame(data=d)[['species', 'pu', 'amount']] #reorder the columns
        #get the intersection data
        if (future): #i.e. new version of marxan
            #get the intersection data as a dataframe from the queryresults - TODO - this needs to be rewritten to be scalable - getting the records in this way fails when you have > 1000 records and you need to use a method that creates a tmp table - see preprocessPlanningUnits
            intersectionData = pandas.DataFrame.from_records(self.queryResults["records"], columns = self.queryResults["columns"])
        else:
            #old version of marxan so an empty dataframe
            intersectionData = emptyDataFrame
        #get the existing data
        try:
            #load the existing preprocessing data
            df = _getProjectInputData(self, "PUVSPRNAME", True)
        except:
            #no existing preprocessing data so use the empty data frame
            df = emptyDataFrame
        #get the species id from the arguments
        speciesId = int(self.get_argument('id'))
        #make sure there are not existing records for this feature - otherwise we will get duplicates
        df = df[~df.species.isin([speciesId])]
        #append the intersection data to the existing data
        df = df.append(intersectionData)
        #sort the values by the species column then pu column
        df = df.sort_values(by=['pu'])
        try: 
            #write the data to the PUVSPR.dat file
            _writeCSV(self, "PUVSPRNAME", df)
            #get the summary information and write it to the feature preprocessing file
            record = _getPuvsprStats(df, speciesId)
            _writeToDatFile(self.folder_input + FEATURE_PREPROCESSING_FILENAME, record)
        except (MarxanServicesError) as e:
            self.send_response({'error': e.message, 'status':'Finished'})
        #update the input.dat file
        _updateParameters(self.folder_project + PROJECT_DATA_FILENAME, {'PUVSPRNAME': PUVSPR_FILENAME})
        #set the response
        self.send_response({'info': "Feature '" + self.get_argument('alias') + "' preprocessed", "feature_class_name": self.get_argument('feature_class_name'), "pu_area" : str(record.iloc[0]['pu_area']),"pu_count" : str(record.iloc[0]['pu_count']), "id":str(speciesId), 'status':'Finished'})
        #close the websocket
        self.close()

#preprocesses the protected areas by intersecting them with the planning units
#wss://db-server-blishten.c9users.io:8081/marxan-server/preprocessProtectedAreas?user=andrew&project=Tonga%20marine%2030km2&planning_grid_name=pu_ton_marine_hexagon_30
class preprocessProtectedAreas(QueryWebSocketHandler):

    #run the preprocessing
    def open(self):
        try:
            super(preprocessProtectedAreas, self).open()
        except (HTTPError) as e:
            self.send_response({'error': e.reason, 'status': 'Finished'})
        else:
            _validateArguments(self.request.arguments, ['user','project','planning_grid_name'])    
            #get the project data
            _getProjectData(self)
            #do the intersection with the protected areas
            future = self.executeQueryAsynchronously(sql.SQL("SELECT DISTINCT iucn_cat, grid.puid FROM (SELECT iucn_cat, geom FROM marxan.wdpa) AS wdpa, marxan.{} grid WHERE ST_Intersects(wdpa.geom, ST_Transform(grid.geometry, 4326)) ORDER BY 1,2;").format(sql.Identifier(self.get_argument('planning_grid_name'))), None, "Preprocessing protected areas", "  Preprocessing protected areas..", "  Preprocessing finished")
            future.add_done_callback(self.preprocessProtectedAreasComplete) # pylint:disable=no-member
    
    #callback which is called when the intersection has been done
    def preprocessProtectedAreasComplete(self, future):
        if hasattr(self, "queryResults"):
            #get the intersection data as a dataframe from the queryresults
            df = pandas.DataFrame.from_records(self.queryResults["records"], columns = self.queryResults["columns"])
            #write the intersections to file
            df.to_csv(self.folder_input + PROTECTED_AREA_INTERSECTIONS_FILENAME, index =False)
        #get the data
        _getProtectedAreaIntersectionsData(self)
        #set the response
        self.send_response({'info': 'Preprocessing finished', 'intersections': self.protectedAreaIntersectionsData, 'status':'Finished'})
    
#preprocesses the planning units to get the boundary lengths where they intersect - produces the bounds.dat file
#wss://db-server-blishten.c9users.io:8081/marxan-server/preprocessPlanningUnits?user=andrew&project=Tonga%20marine%2030km2
class preprocessPlanningUnits(QueryWebSocketHandler):

    #run the preprocessing
    def open(self):
        try:
            super(preprocessPlanningUnits, self).open()
        except (HTTPError) as e:
            self.send_response({'error': e.reason, 'status': 'Finished'})
        else:
            _validateArguments(self.request.arguments, ['user','project'])    
            #get the project data
            _getProjectData(self)
            if (not self.projectData["metadata"]["OLDVERSION"]):
                #new version of marxan - get the boundary lengths
                PostGIS().execute("DROP TABLE IF EXISTS marxan.tmp;") 
                future = self.executeQueryAsynchronously(sql.SQL("CREATE TABLE marxan.tmp AS SELECT DISTINCT a.puid id1, b.puid id2, ST_Length(ST_CollectionExtract(ST_Intersection(a.geometry, b.geometry), 2))/1000 boundary  FROM marxan.{0} a, marxan.{0} b  WHERE a.puid < b.puid AND ST_Touches(a.geometry, b.geometry);").format(sql.Identifier(self.projectData["metadata"]["PLANNING_UNIT_NAME"])), None, "Getting boundary lengths", "  Processing ..", "  Preprocessing finished")
                future.add_done_callback(self.preprocessPlanningUnitsComplete) # pylint:disable=no-member
            else:
                #pass None as the Future object to the callback for the old version of marxan
                self.preprocessPlanningUnitsComplete(None) 
    
    #callback which is called when the boundary lengths have been calculated
    def preprocessPlanningUnitsComplete(self, future):
        try:
            if (future): #i.e. new version of marxan
                #delete the file if it already exists
                if (os.path.exists(self.folder_input + BOUNDARY_LENGTH_FILENAME)):
                    os.remove(self.folder_input + BOUNDARY_LENGTH_FILENAME)
                #write the boundary lengths to file
                postgis = PostGIS()
                postgis.executeToText("COPY (SELECT * FROM marxan.tmp) TO STDOUT WITH CSV HEADER;", self.folder_input + BOUNDARY_LENGTH_FILENAME)
                #delete the tmp table
                postgis.execute("DROP TABLE IF EXISTS marxan.tmp;") 
                #update the input.dat file
                _updateParameters(self.folder_project + PROJECT_DATA_FILENAME, {'BOUNDNAME': 'bounds.dat'})
                #set the response
                self.send_response({'info': 'Boundary lengths calculated', 'status':'Finished'})
        except Exception as e:
            print e.message

####################################################################################################################################################################################################################################################################
## tornado functions
####################################################################################################################################################################################################################################################################

def make_app():
    return tornado.web.Application([
        ("/marxan-server/getServerData", getServerData),
        ("/marxan-server/getProjects", getProjects),
        ("/marxan-server/getProject", getProject),
        ("/marxan-server/createProject", createProject),
        ("/marxan-server/createImportProject", createImportProject),
        ("/marxan-server/upgradeProject", upgradeProject),
        ("/marxan-server/deleteProject", deleteProject),
        ("/marxan-server/cloneProject", cloneProject),
        ("/marxan-server/createProjectGroup", createProjectGroup),
        ("/marxan-server/deleteProjects", deleteProjects),
        ("/marxan-server/renameProject", renameProject),
        ("/marxan-server/updateProjectParameters", updateProjectParameters),
        ("/marxan-server/getCountries", getCountries),
        ("/marxan-server/getPlanningUnitGrids", getPlanningUnitGrids),
        ("/marxan-server/createPlanningUnitGrid", createPlanningUnitGrid),
        ("/marxan-server/deletePlanningUnitGrid", deletePlanningUnitGrid),
        ("/marxan-server/uploadTilesetToMapBox", uploadTilesetToMapBox),
        ("/marxan-server/uploadShapefile", uploadShapefile),
        ("/marxan-server/uploadFile", uploadFile),
        ("/marxan-server/importPlanningUnitGrid", importPlanningUnitGrid),
        ("/marxan-server/createFeaturePreprocessingFileFromImport", createFeaturePreprocessingFileFromImport),
        ("/marxan-server/toggleEnableGuestUser", toggleEnableGuestUser),
        ("/marxan-server/createUser", createUser), 
        ("/marxan-server/validateUser", validateUser),
        ("/marxan-server/resendPassword", resendPassword),
        ("/marxan-server/getUser", getUser),
        ("/marxan-server/getUsers", getUsers),
        ("/marxan-server/deleteUser", deleteUser),
        ("/marxan-server/updateUserParameters", updateUserParameters),
        ("/marxan-server/getFeature", getFeature),
        ("/marxan-server/importFeature", importFeature),
        ("/marxan-server/deleteFeature", deleteFeature),
        ("/marxan-server/createFeatureFromLinestring", createFeatureFromLinestring),
        ("/marxan-server/getFeaturePlanningUnits", getFeaturePlanningUnits),
        ("/marxan-server/getPlanningUnitsData", getPlanningUnitsData), #currently not used
        ("/marxan-server/updatePUFile", updatePUFile),
        ("/marxan-server/getSpeciesData", getSpeciesData), #currently not used
        ("/marxan-server/getAllSpeciesData", getAllSpeciesData), 
        ("/marxan-server/getSpeciesPreProcessingData", getSpeciesPreProcessingData), #currently not used
        ("/marxan-server/updateSpecFile", updateSpecFile),
        ("/marxan-server/getProtectedAreaIntersectionsData", getProtectedAreaIntersectionsData), #currently not used
        ("/marxan-server/getMarxanLog", getMarxanLog), #currently not used - bugs in the Marxan output log
        ("/marxan-server/getBestSolution", getBestSolution), #currently not used
        ("/marxan-server/getOutputSummary", getOutputSummary), #currently not used
        ("/marxan-server/getSummedSolution", getSummedSolution), #currently not used
        ("/marxan-server/getResults", getResults),
        ("/marxan-server/getSolution", getSolution),
        ("/marxan-server/getMissingValues", getMissingValues), #currently not used
        ("/marxan-server/preprocessFeature", preprocessFeature),
        ("/marxan-server/preprocessPlanningUnits", preprocessPlanningUnits),
        ("/marxan-server/preprocessProtectedAreas", preprocessProtectedAreas),
        ("/marxan-server/runMarxan", runMarxan),
        ("/marxan-server/stopMarxan", stopMarxan),
        ("/marxan-server/testRoleAuthorisation", testRoleAuthorisation),
        ("/marxan-server/testTornado", testTornado),
        (r"/(.*)", StaticFileHandler, {"path": MARXAN_CLIENT_BUILD_FOLDER}) # assuming the marxan-client is installed in the same folder as the marxan-server all files will go to the client build folder
    ], cookie_secret=COOKIE_RANDOM_VALUE, websocket_ping_timeout=30, websocket_ping_interval=29)

if __name__ == "__main__":
    try:
        #turn on tornado logging 
        tornado.options.parse_command_line() 
        # create an instance of tornado formatter
        my_log_formatter = LogFormatter(fmt='%(color)s[%(levelname)1.1s %(asctime)s.%(msecs)03d]%(end_color)s %(message)s', datefmt='%d-%m-%y %H:%M:%S', color=True)
        # get the parent logger of all tornado loggers 
        root_logger = logging.getLogger()
        # set your format to root_logger
        root_streamhandler = root_logger.handlers[0]
        root_streamhandler.setFormatter(my_log_formatter)
        # logging.disable(logging.ERROR)
        #set the global variables
        _setGlobalVariables()
        app = make_app()
        #start listening on port 8081
        app.listen(8081)
        #open the web browser if the call includes a url, e.g. python webAPI_tornado.py http://localhost:8081/index.html
        if len(sys.argv)>1:
            if MARXAN_CLIENT_VERSION == "Not installed":
                print "Ignoring start url parameter as the marxan-client is not installed"
            else:
                url = sys.argv[1] # normally "http://localhost:8081/index.html"
                print "\x1b[1;32;48mOpening Marxan Web at '" + url + "' ..\x1b[0m\n"
                #time.sleep(3)
                webbrowser.open(url, new=1, autoraise=True)
        else:
            if MARXAN_CLIENT_VERSION != "Not installed":
                print "No url parameter specified for 'python webAPI_tornado.py <url>'\n"
        tornado.ioloop.IOLoop.current().start()
    except Exception as e:
        print e.message