#installs miniconda silently
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O ./miniconda.sh
chmod +x ./miniconda.sh
./miniconda.sh -b -p ./miniconda
#add conda to current shell
eval "$(./miniconda/bin/conda shell.bash hook)"
#initialise so we can use conda from bash
conda init
#install the python prerequisites silently
conda install -y tornado psycopg2 pandas gdal colorama psutil sqlalchemy    
pip install mapbox aiopg aiohttp -q
#install postgresql/postgis
sudo -i apt-get update  
sudo -i apt-get install postgresql-10 postgis -y
sudo -i apt-get update  
#create the postgis extensions
sudo -u postgres psql -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -c "CREATE EXTENSION postgis_topology;"
#create the jrc user
sudo -u postgres psql -c "CREATE USER jrc WITH PASSWORD 'thargal88' LOGIN NOSUPERUSER IN GROUP postgres;"
#create the marxanserver database
sudo -u postgres psql -c "CREATE DATABASE marxanserver WITH TEMPLATE = template0 ENCODING='UTF8';"
#get the database dump 
https://github.com/andrewcottam/marxan-server/releases/download/Beta2/dump.sql 
#restore the database
sudo -u postgres pg_restore ./dump.sql -d marxanserver
#create the default server.dat file for the server configuration
cp ./marxan-server/server.dat.default ./marxan-server/server.dat
#clean up
rm ./dump.sql   
rm ./miniconda.sh