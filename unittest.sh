#!/bin/bash -i
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