# MarketManager - application for harvesting Crypto Exchange data(Bittrex, Binance, Coinbase, etc)
The marketmanager is a project used to collect and store market data from various exchanges based on the administrator's preferences. The data is exposed via a REST interface and can be queried and fetched from it.  
We have built and use it at [Wholefolio](https://wholefolio.io) as a backbone for our data gathering and analytics services.

# Disclaimer
This project can be used under the Apache v2 license and we (Wholefolio) provide it AS IS. Issues and Merge requests are welcome, please check out our [Contributions page](./CONTRIBUTE.md). This project is hosted in Gitlab due to the CI/CD pipeline and mirrored in Github. Issues/Bugs will be reviewed in both places. Pull/Merge requests MUST be opened in Gitlab.

# Installation
[Installation docs](./INSTALL.md)

# Application management:  
The market manager app has 3 different aspects to its workings - the REST API, the daemon and Celery(the task executor).
1. The daemon is managed via the django manage.py entry point in the root directory. It has 4 parameters - start/stop/restart/status.  
Examples:  
```python3 manage.py daemon start``` - start the daemon.  
```python3 manage.py daemon stop``` - stop the daemon.  
2. The API can be exposed via the standard django dev server or via uwsgi:
```python3 manage.py runserver``` - django dev server for testing.  
```uwsgi configs/uwsgi.ini``` - uwsgi server for production/staging.  
3. Celery task executor is started via celery:  
```celery worker -A marketmanager -B  --loglevel=DEBUG``` - debug worker with 1 process.  
```celery multi start worker1 worker2 -A marketmanager``` - daemon workers.  
You can use all of these in docker :  
```docker run --name marketmanager -d wholefolio/marketmanager:latest $COMMAND```  

# Exchange management:
The exchanges can be managed either via CLI (manage.py commands) or via the REST API
* Get the list of added(available) exchanges:
```python3 manage.py get_exchanges [--available]```
* Add an exchange from the list of available exchanges:
```python3 manage.py add_exchange --name coinbase```
* Add all exchanges from the available list
```python3 manage.py add_exchange --all```
* Disable exchanges
```python3 manage.py disable_exchanges 1 5 13 ``` or ```python3 manage.py disable_exchanges --all```
* Enable exchanges
```python3 manage.py enable_exchanges 1 5 13 ``` or ```python3 manage.py enable_exchanges --all```
* Gather data for an exchange (via celery or not)
```python3 manage.py fetch_exchange_data 1```

## Our setup:
Our setup requires a PostgreSQL DB, InfluxDB and for the setup we have а total of 6 containers:
1. API - running uwsgi for access to the REST API
2. Daemon - container managing scheduling jobs for fetching exchange data
3. Redis - container for messaging between the Daemon and Celery deployments.  
4. Celery - task executor.  
5. InfluxDB - timeseries market data  
6. PostgreSQL - exchange and market data storage


# API endpoints
We have Swagger docs on the REST endpoints. To access it you must be in development mode:
`export ENV=dev && python3 manage.py runserver`


# Developer notes
## How it works
The daemon runs through all currently enabled exchanges, checks timestamps and uses a celery task to gather data for them based on the python3 ccxt module.
## Marketmanager daemon processes:
1. Incoming process - listens for incoming events on a UNIX socket. This is still WIP and isn't finished - the only thing that it supports right now is for getting the status of the daemon. Check the daemonlib repo.  

2. Main process - this is where the main event logic lies. It fetches all ENABLED exchanges via the django model and runs through each exchange, checking if it's currently running and comparing the last run timestamp and the current time. If it's meant to be run, the main process sends it to celery for task execution.

3. Poller process - this process runs periodic checks against the celery status app. It fetches all the exchanges that are in state running and then checks if the exchange has finished running or it has crashed.  

# Other
## Configs:
Configuration is fetched from environmental variables. UWSGI config is present in the ./configs folder.
## Exchange:
The main "actor" is an exchange - it must be present in the ccxt python3 library. Each exchange has methods for fetching data from the respective exchanges (checkout the github page of the lib:https://github.com/ccxt/ccxt/tree/master/python)
