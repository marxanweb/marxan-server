echo "Running startup script"
sudo service postgresql start
screen -d -m /home/a_cottam/miniconda3/bin/python /home/a_cottam/marxan-server/marxan-server.py