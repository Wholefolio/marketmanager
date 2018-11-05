# MarketManager - a django application for harvesting Crypto Exchange data(Bittrex, Binance, Coinbase, etc)
[![pipeline status](https://gitlab.com/cryptohunters/marketmanager/badges/master/pipeline.svg)](https://gitlab.com/cryptohunters/marketmanager/commits/master)  
The market manager app has 3 different aspects to its workings - the REST API, the daemon and Celery(the task executor).

# Installation  
1. Install python3 and pip(Ubuntu examples):
```apt-get install python3```
```apt-get install python3-pip```
2. Install the app dependencies:
```pip3 install configs/requirements.txt```
3. Get docker: https://docs.docker.com/install/linux/docker-ce/ubuntu/#uninstall-old-versions
4. Start a POSTGRESQL database:
```docker run postgresql:latest -e POSTGRES_USERNAME=marketmanager -e POSTGRES_PASSWORD=marketmanager --name db```
5. Connect to the database in the container and create a database.
6. Create ENVIRONMENT variables with the IP of the container, username, password and database name(see dev.env):
```source dev.env```
7. Clone the application locally:
```git clone https://gitlab.com/cryptohunters/marketmanager/```

# Application management:  
1. The daemon is managed via the django manage.py entry point in the root directory. It has 4 parameters - start/stop/restart/status.  
Examples:  
```python3 manage.py daemon start``` - start the daemon.  
```python3 manage.py daemon stop``` - stop the daemon.  
2. The API can be exposed via the standard django dev server or via uwsgi:
```python3 manage.py runserver``` - django dev server for testing.  
```uwsgi configs/uwsgi.ini``` - uwsgi server for production/staging.  
3. Celery task executor is started via celery:  
```celery  worker -A marketmanager  --loglevel=DEBUG``` - debug worker with 1 process.  
```celery multi start worker1 worker2 -A marketmanager``` - daemon workers.  



## Our setup:
Our setup is in GKE with a PostgreSQL DB and for the basic setup we have 4 deployments:
1. API - separate pod(s) running uwsgi for access to the REST
2. Daemon - deployment for the daemon, which is the core of the data gathering.  
3. RabbitMQ - deployment for messaging between the Daemon and Celery deployments.  
4. Celery - pod(s) for executing the tasks passed from the daemon.
With this setup we achieve great speed in writing/fetching data from the DB due to deployments sharing the same models and being in the same project.

# API endpoints and data models:
## API endpoints
1. http://$MANAGER_IP/api/exchanges/ - list/create exchanges. Allowed operations are POST/GET.  
2. http://$MANAGER_IP/api/exchanges/$ID/ - details/deletion/update of an exchange. Allowed operations are GET/PATCH/DELETE  
3. http://$MANAGER_IP/api/exchanges/$ID/run/ - allowed operations are POST.  
4. http://$MANAGER_IP/api/status/ - get the status of the daemon
5. http://$MANAGER_IP/api/markets/ - list of markets in a exchange.  

## Exchange - the main exchange fields:
**Name** - the name of the exchange. Required  
**Enabled** - whether the daemon should gather data for the exchange or not. Default: True  
**Logo** - the url to logo of the exchange.  
**Url** - URL to the website of the exchange  
**API_URL** - URL to the API of the exchange  
**Volume** - Total volume of the exchange in USD  
**Top_Pair** - the top pair by trading volume  
**Top_Pair_volume** - total trading volume of the top trading pair(calculated based on the base symbol.  

**Created** - Timestamp of the exchange creation date and time.  
**Updated** - Timestamp for the last modification on the exchange.  
**Interval** - the interval between each exchange run.  
**Last update** - this shows when was the last time a task has SUCCESSFULLY gathered data for this exchange.

## ExchangeStatus:
This model defines the exchange status - whether it's currently running, when was the last run and the last run's ID. **Automatically created**. The poller method uses this model to determine the current state of the exchange - running, stale or not running.
Fields:  
**Exchange** - foreign key to the exchange model.  
**Last_run** - date and time of the last run.  
**Last_run_id** - ID of the last known task from celery.  
**Time_started** - time of starting the task.  

## Market model:
This model defines a Market - the basis for a trading pair within an exchange. Fields:  
**Name** - name of the trading pair. Required.  
**Base** - name of base in which the markets trades. Required.  
**Quote** - the name of the currency that is being traded against the base. Required.  
**Exchange** - foreign key to the Exchange model.  
All of the ones below are quantified by means of the **BASE**:
**Volume** - trading volume of the pair.  
**Last** - price of the last trade that has happened in the pair.  
**Bid** - current bid price for the pair.  
**Ask** - current ask price for the pair.  

# Developer notes
## How it works
The daemon runs through all currently enabled exchanges, checks timestamps and uses a celery task to gather data for them based on the python3 ccxt module.
## Marketmanager built-ins that are running in separate processes:
1. Incoming process - listens for incoming events on a UNIX socket. This is still WIP and isn't finished - the only thing that it supports right now is for getting the status of the daemon. Check the applib repo.  

2. Main process - this is where the main looping logic lies. It fetches all ENABLED exchanges via the django model and runs through each exchange, checking if it's currently running and comparing the last run timestamp and the current time. If it's meant to be run, the main process sends it to the Coiner App for execution. The response is then checked and if the response is 200 OK, it updates the ExchangeStatus last_run_id and state to running.  

3. Poller process - this process runs periodic checks against the Coiner app. It fetches all the exchanges that are in state running and then checks if the exchange has finished running and if it has crashed.  

# Other
## Configs:
Daemon and API configuration is dependent on the environment. Configuration is fetched from environmental variables.    
Dev config in marketmanager/config_dev.py. Staging config in marketmanager/config_staging. Additional configurations plus the requirements for the pip modules and uwsgi are in ./configs.

## Exchange:
The main "actor" is an exchange - it must be present in the ccxt python3 library. Each exchange has methods for fetching data from the respective exchanges (checkout the github page of the lib:https://github.com/ccxt/ccxt/tree/master/python)


