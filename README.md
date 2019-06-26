# marxan-server
Back end Marxan Server installation for running Marxan Web. 

## Architecture
The following image shows the high level architecture of marxan-server. 
![marxan-server architecture](architecture.png)  

## Installation
The following installation was testing on Ubuntu 18.04.  
### Download the required files  
In the folder where you want to install marxan-server, type the following:
```
git clone https://github.com/andrewcottam/marxan-server.git
```
Then download the database:  
```
wget https://github.com/andrewcottam/marxan-server/releases/download/beta/dump.sql
```
### Install Python dependencies
Install miniconda (Enter yes at: Do you wish the installer to initialize Miniconda2 by running conda init? [yes|no] ?):  
```
wget https://repo.anaconda.com/miniconda/Miniconda2-latest-Linux-x86_64.sh  
bash Miniconda2-latest-Linux-x86_64.sh  
```  
Install dependencies:  
```  
conda install tornado psycopg2 pandas gdal colorama    
pip install mapbox  
```  

### Install Postgresql/PostGIS
marxan-server requires Postgresql version 10+ and PostGIS version 2.4+  
```
sudo apt-get update  
sudo apt-get install postgresql postgis 
sudo apt-get update  
sudo -u postgres psql -c 'CREATE EXTENSION postgis;'
sudo -u postgres psql -c 'CREATE EXTENSION postgis_topology;'
```  

### Create database  
```  
sudo -u postgres psql -f dump.sql postgres://
```

### Configure https
If you want to enable the marxan-server to serve over SSL, then in the server.dat file put the following info:  
- CERTFILE /home/a_cottam/andrewcottam.com.crt
- KEYFILE /home/a_cottam/andrewcottam_com.key  

If you get an error 'SEC_ERROR_UNKNOWN_ISSUER' in Firefox it is because the crt certificate does not include the full chain of certificates. To fix this, copy the \*.crt certificate and paste it into the top of the full \*.ca-bundle certificate and save this as a new certificate, e.g. certificate_chain.crt. It should then work in Firefox.  

### Create the server.dat file
The server.dat.default file contains the default configuration information for your installation of marxan-server and must be copied to server.dat where you can customise it with your own organisations information (this customisation is optional). This file will not be overwritten when any future updates to the marxan-server repo are pulled from GitHub. For more information on the values in the configuration file see the [Administrator Documentation](https://andrewcottam.github.io/marxan-web/documentation/docs_admin.html).  

### Deploying onto GCP
Use screen otherwise when the ssh connection drops the python process will be killed.  

### Cleanup
Remove the downloaded files  
```
rm dump.sql   
rm Miniconda2-latest-Linux-x86_64.sh   
rm v<VERSION>.zip  
``` 
### Start the services
Start the PostGIS instance and the Marxan Server  
```
sudo service postgresql restart  
python marxan-server-<VERSION>/webAPI_tornado.py  
```
### Navigate the marxan-client
https://\<host>:8081/index.html

### Configuration  
marxan-server can be configured to change various settings including linking to an existing database, configuring security etc. For more information see the [Administrator Guide - Configuration](https://andrewcottam.github.io/marxan-web/documentation/docs_admin.html#configuration).  
