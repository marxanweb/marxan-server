#!/bin/bash -i
##
## Copyright (c) 2020 Andrew Cottam.
##
## This file is part of marxan-server
## (see https://github.com/marxanweb/marxan-server).
##
## License: European Union Public Licence V. 1.2, see https://opensource.org/licenses/EUPL-1.2
##
conda activate base 
#set the environment variable to supress any ogr2ogr warnings/errors
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    export CPL_LOG=/dev/null
elif [[ "$OSTYPE" == "freebsd"* ]]; then
    SET CPL_LOG=/dev/null    
fi
printf "\n"
echo "Running unit tests.."
python -W ignore -m unittest test -v -b