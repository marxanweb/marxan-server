##
## Copyright (c) 2020 Andrew Cottam.
##
## This file is part of marxan-server
## (see https://github.com/marxanweb/marxan-server).
##
## License: European Union Public Licence V. 1.2, see https://opensource.org/licenses/EUPL-1.2
##
echo "Installing wget"
apt-get update
apt-get install wget -y
apt-get update
echo "Downloading miniconda .."
#download the miniconda installer
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh 
#installs miniconda silently
echo "Installing miniconda .."
bash ./Miniconda3-latest-Linux-x86_64.sh -b -p ./miniconda3
#remove the installer
echo "Removing the installer .."
rm ./Miniconda3-latest-Linux-x86_64.sh 
echo "Initialising so we can use conda from bash (this is for the current user)"
./miniconda3/bin/conda init bash
### PYTHON PREREQUISITES
echo "Installing Python packages .."
#install the python prerequisites silently
./miniconda3/bin/conda install -y tornado psycopg2 pandas gdal colorama psutil sqlalchemy    
./miniconda3/bin/pip install mapbox aiopg aiohttp google-cloud-logging -q