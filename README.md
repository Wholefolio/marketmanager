The market manager app is an exchange based daemon with a REST API, which manages the exchanges in a interval based fashion. Exchange CRUD is done via the REST API. The daemon runs through all currently enabled exchanges, checks timestamps and sends them to coiner to gather data for them based on the python3 ccxt module. More details on the mechanics are listed below.  


# API endpoints:
1. http://$MANAGER_IP/api/exchanges/ - allowed operations are POST/GET.  
2. http://$MANAGER_IP/api/exchanges/$ID/ - allowed operations are GET/PATCH/DELETE  
3. http://$MANAGER_IP/api/exchanges/$ID/run/ - allowed operations are POST  
4. http://$MANAGER_IP/api/status/ - get the status of the daemon

# Exchange parameters on creation:
**Name** - the name of the exchange.  
**Enabled** - whether the daemon should work on the exchange or not.
**Logo** - the url to logo of the exchange
**Url** - URL to the website of the exchange
**API_URL** - URL to the API of the exchange
**Volume** - Total volume of the exchange in USD
**Top_Pair** - the top pair by trading volume
**Top_Pair_volume** - total trading volume of the top trading pair(calculated based on the base symbol - aka the left of the pair. Example USDT-ETH, USDT is the base)

**Created** - Timestamp of the exchange creation date and time.  
**Updated** - Timestamp for the last modification on the exchange via the API.  
**Interval** - the interval between each exchange run.  
**Last update** - this shows when was the last time COINER SUCCESSFULLY gathered data for this exchange.

# ExchangeStatus
This model defines the exchange status - whether it's currently running, when was the last run and the last run's ID. Fields:
**Exchange** - foreign key to the exchange model.  
**Last_run** - date and time of the last run.  
**Last_run_id** - ID of the last run in the Coiner APP.  
**Time_started** - time 

# Market manager daemon:  
The daemon is managed via the marketmanager.py entry point in the root directory. It has 4 parameters - start/stop/restart/status.

# Daemon explanation and working:  
The daemon uses the UNIX double fork mechanism to daemonize itself upon launch. It has 4 starting Processes(not threads) - the Main process, the Incoming process, the Poller process and the Manager process. The first three are part of the main coiner class in src/coiner.py and the last(Manager) is created during instantiation for passing pickleble objects between the processes.  

1. Manager process:
The manager process simply passes pickled objects between the starter process(before the 2 forks) and the incoming/main processes.

2. Incoming process - listens for incoming events on a UNIX socket. This is still WIP and isn't finished - the only thing that it supports right now is for getting the status of the daemon and running an exchange on demand.  

3. Main process - this is where the main looping logic lies. This is based of the MarketManager class method main. It fetches all ENABLED exchanges via the django model and runs through each exchange, checking if it's currently running and comparing the last run timestamp and the current time. If it's meant to be run, the main process sends it to the Coiner App for execution. The response is then checked and if the response is 200 OK, it updates the ExchangeStatus last_run_id and state to running.  

4. Poller process - this process runs periodic checks against the Coiner app. It fetches all the exchanges that are in state running and then checks if the exchange has finished running and if it has crashed.  

# Configs:
Daemon and API configuration is dependent on the environment. Configuration is fetched from environmental variables.    
Dev config in marketmanager/config_dev.py. Staging config in marketmanager/config_staging. Additional configurations plus the requirements for the container, nginx, uwsgi are in ./configs.


# exchange:
The main "worker" is an exchange - it must follow certain requirements to work properly.  
1. The exchange filename and the the main class name MUST be the same.  
2. The main event method MUST be named "run" and MUST NOT take any parameters.  
3. The exchange class contructor MUST take in two arguments - exchange params(optional parameters for the exchange, if the programmer sees fit) and STORAGE_SOURCE_ID (mentioned above). The storage source ID is needed when returning the parsed data in JSON format to the exchangeworker class.  
The exchange can have as many other methods as you want.  
