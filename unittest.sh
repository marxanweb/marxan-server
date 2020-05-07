#!/bin/bash -i
conda activate base 
echo "Running unit tests"
printf "\n"
python -W ignore -m unittest test -v