# marxan-server
Back end Marxan Server installation for running Marxan Web. See also [marxan-web](https://github.com/andrewcottam/marxan-web) and [marxan-client](https://github.com/andrewcottam/marxan-client).

## Architecture
The following image shows the high level architecture of marxan-server. 
![marxan-server architecture](https://github.com/andrewcottam/marxan-web/documentation/images/architecture.png)  

## Installation
The following installation was testing on Ubuntu 16.04.  
### Clone the repo  
In the folder where you want to install marxan-server, type the following:
```
git clone https://github.com/andrewcottam/marxan-server.git
cd marxan-server
```

### Install Python and dependencies
Install miniconda (Enter yes at: Do you wish the installer to initialize Miniconda3 by running conda init? [yes|no] ?):  
```
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh  
bash Miniconda3-latest-Linux-x86_64.sh  
```  
Enter yes at the prompt Do you wish the installer to initialize Miniconda3 by running conda init?  

Install dependencies:  
```  
conda install tornado psycopg2 pandas gdal colorama psutil    
pip install mapbox  
```  

### Install Postgresql/PostGIS
marxan-server requires Postgresql version 10+ and PostGIS version 2.4+  
```
sudo apt-get update  
sudo apt-get install postgresql postgis 
sudo apt-get update  
sudo -u postgres psql -c "CREATE EXTENSION postgis;"
sudo -u postgres psql -c "CREATE EXTENSION postgis_topology;"
```  

### Create database  
Download the database:  
```
wget https://github.com/andrewcottam/marxan-server/releases/download/beta/dump.sql
```

Import the data:
```  
sudo -u postgres psql -c "CREATE USER jrc WITH PASSWORD 'thargal88' LOGIN NOSUPERUSER IN GROUP postgres;"
sudo -u postgres psql -c "CREATE DATABASE marxanserver WITH TEMPLATE = template0 ENCODING='UTF8';"
sudo -u postgres pg_restore dump.sql -d marxanserver
```

### Create the server.dat file
The server.dat.default file contains the default configuration information for your installation of marxan-server and must be copied to server.dat where you can customise it with your own organisations information (this customisation is optional - see [configuration](#configuration)). This file will not be overwritten when any future updates to the marxan-server repo are pulled from GitHub. 
```
cp server.dat.default server.dat
```

### Cleanup
Remove the downloaded files  
```
rm dump.sql   
rm Miniconda3-latest-Linux-x86_64.sh   
```  

### Start marxan-server:

```
python marxan-server.py  
```

NOTE: On some Cloud hosts like Google Cloud Platform, when the SSH connection is closed then the instances may be shut down, thus terminating the marxan-server. To avoid this, use Virtual Terminal software like screen. For more information see [here](https://www.tecmint.com/keep-remote-ssh-sessions-running-after-disconnection/).  For example:  

```
screen python marxan-server.py
```

You can also configure marxan-server to start automatically whenever the server is started. For example, on a Google Cloud Platform VM you can use a startup script (/home/a_cottam/startup.sh) like the following:

```
#! /bin/bash
sudo service postgresql start
screen -d -m /home/a_cottam/miniconda3/bin/python /home/a_cottam/marxan-server/marxan-server.py
```

Then this can be added to the VM so that it is run when the server starts:

```
gcloud compute instances add-metadata <instance> --metadata-from-file startup-script=/home/a_cottam/startup.sh
```

### Configuration  
marxan-server can be configured to change various settings including linking to an existing database, configuring security etc. For more information see the [Administrator Guide - Configuration](https://andrewcottam.github.io/marxan-web/documentation/docs_admin.html#configuration).  
