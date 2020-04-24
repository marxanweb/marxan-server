# marxan-server
Back end Marxan Server installation for running Marxan Web. See also [marxan-client](https://github.com/marxanweb/marxan-client).

## Architecture
The following image shows the high level architecture of marxan-server. 
![marxan-server architecture](https://github.com/marxanweb/marxan-client/raw/master/architecture_client.png)  

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
sudo marxan-server/unix_startup.sh
```

## Test the installation
To test the installation goto: http://\<host\>/marxan-server/testTornado.  

To run a complete set of unit tests, start a new shell and run the following:  
```
cd marxan-server/
./unittest.sh
```
  
## Configuration  
marxan-server can be configured to change various settings including linking to an existing database, configuring security etc. For more information see the [Administrator Guide - Configuration](https://docs.marxanweb.org/admin.html#configuration).  

## Starting automatically
You can also configure marxan-server to start automatically whenever the server is restarted.  

For example, on a Google Cloud Platform VM configure the marxan-server/unix_startup.sh script to be run on restart (replace the \<instancename\> with the name of the VM):  

```
gcloud compute instances add-metadata <instancename> --metadata-from-file startup-script=$MARXAN_SERVER_DIRECTORY\/unix_startup.sh
```

## Updating
To download and apply the latest updates to marxan-server:  
```
marxan-server/unix_update.sh 
```

## Troubleshooting
### Cannot connect to marxan-server
If you see a connection refused error on attempting to connect, then it is likely that a Firewall is blocking the connections. Add the following rules: Allow TCP:80, TCP:8080, TCP:8081 for the IP ranges 0.0.0.0/0. 
