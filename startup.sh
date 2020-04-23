#!/bin/bash -i
#running in an interactive bash session to load the .bashrc script
#run conda activate base - this sets environment variables that are needed e.g. GDAL_DATA
${CONDA_EXE} activate base
# on unix the following may be required
#sudo service postgresql start
#start marxan-server using a detached screen session that can be resumed
screen -d -m ${CONDA_PYTHON_EXE} /home/a_cottam/marxan-server/marxan-server.py