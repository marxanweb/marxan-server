# marxan-server
Back end Marxan Server installation for running Marxan Web. 

## Installation
The following installation was testing on Ubuntu 14.04. Replace \<VERSION> with the actual version, e.g. 1.1.  
### Download and unzip the required files:  
```
wget https://github.com/andrewcottam/marxan-server/archive/v<VERSION>.zip    
wget https://github.com/andrewcottam/marxan-server/releases/download/v<VERSION>/dump.sql  
unzip v<VERSION>.zip   
```
### Install Python prerequisites
Install miniconda (Enter yes at: Do you wish the installer to initialize Miniconda2 in your /home/ubuntu/.bashrc ?):  
```
wget https://repo.anaconda.com/miniconda/Miniconda2-latest-Linux-x86_64.sh  
bash Miniconda2-latest-Linux-x86_64.sh  
```  
Install prerequisites:  
```  
conda install tornado psycopg2 pandas gdal  
pip install mapbox  
```  
### Install Postgresql/PostGIS
```
sudo apt-get update  
sudo apt-get install postgresql postgresql-contrib postgis postgresql-9.3-postgis-scripts  
sudo apt-get update  
```
### Create database  
Create the database, user and PostGIS functions and import the required data:
```  
createuser jrc -P -s  
createdb -T template0 marxanserver  
psql -c 'CREATE EXTENSION IF NOT EXISTS postgis;'   
psql -c 'CREATE EXTENSION IF NOT EXISTS postgis_topology;'  
psql -h 127.0.0.1 -d marxanserver -U jrc -f /home/ubuntu/workspace/dump.sql  
```
### Cleanup
Remove the downloaded files  
```
rm dump.sql   
rm Miniconda2-latest-Linux-x86_64.sh   
rm v<VERSION>.zip  
```
### Start the services
Start the PostGIS instance, the webserver (in this case Apache2) and the Marxan Server  
```
sudo service postgresql restart  
service apache2 restart
python marxan-server-<VERSION>/webAPI_tornado.py  
```
