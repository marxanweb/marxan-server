#!/bin/bash -i
#import the environment variables for marxan-server
. /etc/profile.d/marxan-server.sh
#kill the screen process that is running marxan-server
sudo pkill screen
if [ $? -eq 1 ]
then
    echo 'screen killed'
fi
#pull the new github repo
echo "Pulling from GitHub.."
cd $MARXAN_SERVER_DIRECTORY
git reset --hard
git pull
#restart marxan-server
printf "\n"
echo "Restarting marxan-server"
printf "\n"
sudo ./unix_startup.sh