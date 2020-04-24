#!/bin/bash -i
#import the environment variables for marxan-server
. /etc/profile.d/marxan-server.sh
conda activate base 
#start marxan-server using a detached screen session that can be resumed
screen -d -m ${CONDA_PYTHON_EXE} ${MARXAN_SERVER_DIRECTORY}\/marxan-server.py
echo "marxan-server is running"
#get the external IP address of this instance
externalip=$(gcloud compute instances list --filter="name=($HOSTNAME)" --format="value(networkInterfaces[0].accessConfigs[0].natIP)")
if [ "$externalip" != '' ]
then
    echo "To test the marxan-server is accessible goto:"
    echo "  http://"$externalip"//marxan-server/testTornado"
fi
echo "To connect to the running instance:"
echo "  sudo screen -r"