#!/bin/bash -i
#import the environment variables for marxan-server
. /etc/profile.d/marxan-server.sh
#kill the screen process that is running marxan-server
printf "\n"
echo "Stopping marxan-server.."
sudo pkill screen
if [ $? -eq 1 ]
then
    echo 'marxan-server stopped'
fi
#pull the new github repo
printf "\n"
echo "Pulling from GitHub.."
cd $MARXAN_SERVER_DIRECTORY
git reset --hard
git pull
#running unit tests
sudo ./unittest.sh
#restart marxan-server
printf "\n"
sudo ./unix_startup.sh