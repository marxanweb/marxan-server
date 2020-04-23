## MINICONDA
download the miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
#installs miniconda silently
bash ./Miniconda3-latest-Linux-x86_64.sh -b -p ./miniconda3
#remove the installer
rm ./Miniconda3-latest-Linux-x86_64.sh 
#initialise so we can use conda from bash (this is for the root user)
sudo su -c "./miniconda3/bin/conda init bash"
#and current user
./miniconda3/bin/conda init bash
### PYTHON PREREQUISITES
#install the python prerequisites silently
./miniconda3/bin/conda install -y tornado psycopg2 pandas gdal colorama psutil sqlalchemy    
./miniconda3/bin/pip install mapbox aiopg aiohttp -q
### POSTGRESQL/POSTGIS
#install postgresql/postgis
sudo apt-get update  
sudo apt-get install postgresql-10 postgis -y
sudo apt-get update  
#create the postgis extensions
sudo -u postgres psql -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -c "CREATE EXTENSION postgis_topology;"
### MARXAN DATABASE
#create the jrc user
sudo -u postgres psql -c "CREATE USER jrc WITH PASSWORD 'thargal88' LOGIN NOSUPERUSER IN GROUP postgres;"
#create the marxanserver database
sudo -u postgres psql -c "CREATE DATABASE marxanserver WITH TEMPLATE = template0 ENCODING='UTF8';"
#get the database dump 
wget https://github.com/marxanweb/marxan-server/releases/download/Beta2/dump.sql 
#restore the database
sudo -u postgres pg_restore ./dump.sql -d marxanserver
#remove dump file
rm ./dump.sql   
#create the default server.dat file for the server configuration
cp ./marxan-server/server.dat.default ./marxan-server/server.dat

echo "marxan-server installed."
