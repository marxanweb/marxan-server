# marxan-server
Back end Marxan Server installation for running Marxan Web. 

# Install script
wget https://github.com/andrewcottam/marxan-server/archive/v0.2.zip    
unzip v0.2.zip   
wget https://github.com/andrewcottam/marxan-server/releases/download/v0.2/dump.sql  
wget https://repo.anaconda.com/miniconda/Miniconda2-latest-Linux-x86_64.sh  
bash Miniconda2-latest-Linux-x86_64.sh  (Enter yes at: Do you wish the installer to initialize Miniconda2 in your /home/ubuntu/.bashrc ? [yes|no])  
conda install tornado psycopg2 pandas gdal  
pip install mapbox  
sudo apt-get update  
sudo apt-get install postgresql postgresql-contrib postgis postgresql-9.3-postgis-scripts  
sudo apt-get update  
createuser jrc -P -s  
createdb -T template0 marxanserver  
psql -c 'CREATE EXTENSION IF NOT EXISTS postgis;'   
psql -c 'CREATE EXTENSION IF NOT EXISTS postgis_topology;'
psql -h 127.0.0.1 -d marxanserver -U jrc -f /home/ubuntu/workspace/dump.sql  
rm dump.sql   
rm Miniconda2-latest-Linux-x86_64.sh   
rm v0.2.zip  
sudo service postgresql restart  
python marxan-server-0.2/webAPI_tornado.py  
