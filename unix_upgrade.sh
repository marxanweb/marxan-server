#!/bin/bash -i
#import the environment variables for marxan-server
. /etc/profile.d/marxan-server.sh
#kill the screen process that is running marxan-server
pkill screen
if [ $? -eq 1 ]
then
    echo 'screen killed'
fi
#pull the new github repo
echo "Pulling from GitHub.."
cd $MARXAN_SERVER_DIRECTORY
git pull
#restart marxan-server
echo "Restarting marxan-server.."
sudo ./unix_startup.sh