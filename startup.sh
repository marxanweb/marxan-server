#run conda activate base - this sets environment variables that are needed e.g. GDAL_DATA
/home/a_cottam/miniconda3/bin/conda activate base
#start marxan-server using a detached screen session that can be resumed
screen -d -m /home/a_cottam/miniconda3/bin/python /home/a_cottam/marxan-server/marxan-server.py
