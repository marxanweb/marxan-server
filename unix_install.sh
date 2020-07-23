##
## Copyright (c) 2020 Andrew Cottam.
##
## This file is part of marxan-server
## (see https://github.com/marxanweb/marxan-server).
##
## License: European Union Public Licence V. 1.2, see https://opensource.org/licenses/EUPL-1.2
##
echo "Installing miniconda .."
#download the miniconda installer
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
echo "Installing Python packages .."
#install the python prerequisites silently
./miniconda3/bin/conda install -y tornado psycopg2 pandas gdal colorama psutil sqlalchemy    
./miniconda3/bin/pip install mapbox aiopg aiohttp google-cloud-logging -q
### POSTGRESQL/POSTGIS
echo "Installing PostGIS .."
#install postgresql/postgis
sudo apt-get update  
sudo apt-get install postgresql-10 postgis -y
sudo apt-get update  
#create the postgis extensions
sudo -u postgres psql -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -c "CREATE EXTENSION postgis_topology;"
### MARXAN DATABASE
echo "Creating the marxan-server database .."
#create the jrc user
sudo -u postgres psql -c "CREATE USER jrc WITH PASSWORD 'thargal88' LOGIN NOSUPERUSER IN GROUP postgres;"
#create the marxanserver database
sudo -u postgres psql -c "CREATE DATABASE marxanserver WITH TEMPLATE = template0 ENCODING='UTF8';"
#get the database dump 
wget https://github.com/marxanweb/marxan-server/releases/download/v1.0.0/dump.sql 
#restore the database
echo "Restoring database objects .."
sudo -u postgres pg_restore ./dump.sql -d marxanserver
#remove dump file
rm ./dump.sql   
#create the default server.dat file for the server configuration
cp ./marxan-server/server.dat.default ./marxan-server/server.dat
#create the default admin user.dat file - this allows git resets without overwriting any password changes
cp ./marxan-server/users/admin/user.dat.default ./marxan-server/users/admin/user.dat
#create the default marxan-server.log file - this allows git resets without overwriting log changes
cp ./marxan-server/marxan-server.log.default ./marxan-server/marxan-server.log
#create the default runlog.dat file - this allows git resets without overwriting run log changes
cp ./marxan-server/runlog.dat.default ./marxan-server/runlog.dat
#create a file in /etc/profile.d/ to store the MARXAN_SERVER_DIRECTORY environment variable for all users
sudo bash -c 'echo MARXAN_SERVER_DIRECTORY=\"$PWD\/marxan-server\" > /etc/profile.d/marxan-server.sh'
#source the MARXAN_SERVER_DIRECTORY environment variable to apply that environment variable
source /etc/profile.d/marxan-server.sh
echo "marxan-server installed to" $MARXAN_SERVER_DIRECTORY
