# marxan-server
Back end Marxan Server installation for running Marxan Web. 

## Architecture
The following image shows the high level architecture of marxan-server. 
![marxan-server architecture](architecture.png)  

## Installation
The following installation was testing on Ubuntu 14.04. Replace \<VERSION> with the actual version, e.g. 1.1.  
### Download and unzip the required files  
Click on the releases link above, copy the link to the download files and download and unzip them.  
```
wget https://github.com/andrewcottam/marxan-server/archive/v<VERSION>.zip    
wget https://github.com/andrewcottam/marxan-server/releases/download/v<VERSION>/dump.sql  
unzip v<VERSION>.zip   
```
### Install Python dependencies
Install miniconda (Enter yes at: Do you wish the installer to initialize Miniconda2 in your /home/ubuntu/.bashrc ?):  
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
```
sudo apt-get update  
sudo apt-get install postgresql postgresql-contrib postgis postgresql-9.3-postgis-scripts  
sudo apt-get update  
```
### Create database  
Create the database user, database and PostGIS functions and import the required data:
```  
createuser -P -s jrc
createdb -T template0 marxanserver  
psql -c 'CREATE EXTENSION IF NOT EXISTS postgis;'   
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
Start the PostGIS instance and the Marxan Server  
```
sudo service postgresql restart  
python marxan-server-<VERSION>/webAPI_tornado.py  
```
### Navigate the marxan-client
https://\<host>:8081/index.html
