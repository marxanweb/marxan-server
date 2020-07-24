# marxan-server
Back end Marxan Server installation for running Marxan Web. See also [marxan-client](https://github.com/marxanweb/marxan-client).

## Architecture
The following image shows the high level architecture of marxan-server. 
![marxan-server architecture](https://github.com/marxanweb/marxan-server/raw/master/architecture-server.png)  

## Installation
The following instructions describe how to install marxan-server on Ubuntu 18.04 LTS. For Windows, see [here](https://github.com/marxanweb/general/releases)    

### Clone the repo:  
In the folder where you want to install marxan-server, type the following:
```
git clone https://github.com/marxanweb/marxan-server.git
```
### Install marxan-server:
```
marxan-server/unix_install.sh
```

### Start marxan-server:
```
cd marxan-server/
sudo ./unix_startup.sh
```

## Test the installation
To test the marxan-server is installed and running, goto: http://\<host\>/marxan-server/testTornado.  

To run a complete set of unit tests, stop the server and run the following:  
```
sudo ./unittest.sh
```
  
## Configuration  
marxan-server can be configured to change various settings including linking to an existing database, configuring security etc. For more information see the [Administrator Guide - Configuration](https://docs.marxanweb.org/admin.html#configuration).  

## Starting automatically
You can also configure marxan-server to start automatically whenever the server is restarted.  

For example, on a Google Cloud Platform VM configure the marxan-server/unix_startup.sh script to be run on restart:  

```
sudo gcloud compute instances add-metadata $HOSTNAME --metadata-from-file startup-script=$MARXAN_SERVER_DIRECTORY\/unix_startup.sh
```

## Updating
To download and apply the latest updates to marxan-server, go to the marxan-server folder and run the following (not as sudo):  
```
./unix_update.sh 
```

## DOCKER   
This is a standalone Docker image intended to be used with a standalone marxan-client image and a local database, though the database can be changed by updating the relevant env/dat files. 

The Dockerfile contained uses the ubuntu linux system.  
The instructions update the base image, a clean ubuntu image, and then install the requirements for the application, first the base system packages, then the software packages used by the application. 
It the copies over the relevant application code into the image, exposes port 80 and runs the app. 

To build the image go into the `marxan-server/` folder and run:  
`docker build -t repo_name:image_name .`  
This instruction builds an image using the tag option (`-t`). This gives the image a name in the format `repo_name:image_name`. If you dont provide an image_name it will default to `latest`  
The final part of the command is the path to the directory we want to build from. Given we are in the directory we want to build from we use `.`  

example:  
`docker build -t openmarxserver:test .`

Docker build options can be found here: https://docs.docker.com/engine/reference/commandline/build/

### Linux
The command for running the docker container is:  
`docker run -dp 80:80 --name oms --network='host' openmarxserver:test`  
This runs the docker container.  
 - `-d` is detatched mode, so you can use your terminal afterwards  
 - `-p` is the port command. In this instance we are using PORT 80 on our local machine and matching that to PORT 80 in the docker image. The Dockerfile exposes port 80 so thats the port our container is expecting to run on. If you wanted the image to run on PORT 5000 locally you would pass `-p 5000:80`. 
 - you can combine `-d` and `-p` together into `-dp`  
 - `--name` gives the container a name of your choice to make interacting with the container easier.  
 - `--network='host'` For standalone containers, remove network isolation between the container and the Docker host, and use the host’s networking directly. This allows connection to your local database, hosted on your machine. Network options can be found here: https://docs.docker.com/network/  
 - The final item is the name of the image you want to start the container from. 

### Mac  
See above for linux but replace the `--network='host'` option with `--add-host=database:<host-ip>`  
`docker run -dp 80:80 --name oms --add-host=database:<host-ip> openmarxserver:test`  

see   
 - https://docs.docker.com/docker-for-mac/networking/#use-cases-and-workarounds  
 - https://stackoverflow.com/questions/24319662/from-inside-of-a-docker-container-how-do-i-connect-to-the-localhost-of-the-mach


## DATABASE  
The local database needs to be set up to run with the Docker images. 
Postgres-10 needs to be installed, along with PostGIS 2.5 as per your system install instructions.
create your database and the extensions `postgis` and `postgis_topology`.  
create a user `jrc` with password `thargal88` in group `postgres`  
Get the database restore file   
`wget https://github.com/marxanweb/marxan-server/releases/download/v1.0.0/dump.sql`  
restore the database.  
If youre using pgadmin use pgadmin3 as pgadmin4 will not restore with `OIDS`  

