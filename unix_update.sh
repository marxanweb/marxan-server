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