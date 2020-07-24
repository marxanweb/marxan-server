#!/bin/bash -i
##
## Copyright (c) 2020 Andrew Cottam.
##
## This file is part of marxan-server
## (see https://github.com/marxanweb/marxan-server).
##
## License: European Union Public Licence V. 1.2, see https://opensource.org/licenses/EUPL-1.2
##
. /etc/profile.d/marxan-server.sh
conda activate base 
#start marxan-server using a detached screen session that can be resumed
screen -d -m ${CONDA_PYTHON_EXE} ${MARXAN_SERVER_DIRECTORY}\/marxan-server.py
echo "Starting marxan-server .."
echo "Server started"
#if gcloud is installed, get the external ip address so we can add the testTornado link
if [ -x "$(command -v gcloud)" ]; then
    #get the external IP address of this instance
    externalip=$(gcloud compute instances list --filter="name=($HOSTNAME)" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
    if [ "$externalip" != '' ]
    then
        echo "To test the marxan-server is accessible goto:"
        echo "  http://"$externalip"/marxan-server/testTornado"
    fi
fi
echo "To connect to the running instance:"
echo "  sudo screen -r"
# sudo screen -r