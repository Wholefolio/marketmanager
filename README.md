The coiner maanger app is an adapter based daemon with a REST API, which manages the adapters in a interval based fashion. Adapter CRUD is done via the REST API. The daemon runs through all currently added adapters, checks timestamps and sends them to coiner to run them. More details on the mechanics are listed below.  


# API endpoints:
1. http://$COINER_IP/api/adapters/ - allowed operations are POST/GET.  
2. http://$COINER_IP/api/adapters/$ID/ - allowed operations are GET/PATCH/DELETE  
3. http://$COINER_IP/api/adapters/$ID/run/ - allowed operations are POST  
4. http://$COINER_IP/api/status/ - get the status of the daemon

# Adapter parameters on creation:
**Adapter name** - the name of the adapter.  
**Enabled** - whether the daemon should work on the adapter or not.
**Storage source ID** - each individual adapter MUST have exactly ONE source in the storage app. This ID is the ID given to the source in the storage app.  
**Created** - Timestamp of the adapter creation date and time.  
**Updated** - Timestamp for the last modification on the adapter via the API.  
**Last run** - Timestamp for when was the last execution of the adapter.  
**Source code** - the adapter source code in Python.  
**Adapter params** - JSON based optional parameters for the adapter(can be null).  
**Interval** - the interval between each adapter run.  
**Adapter types** - the adapter type defines what the adapter will be populating in the storage app:  
1. Common (CMN) - populate the currencies endpoint.   
2. Exchange (EXC) - populate the markets endpoint.  
3. Icos (ICO) - populate the icos endpoint.  
4. Fiat (FIAT) - populate the fiatexchangerates endpoint.  


# Scripts:
There are two scripts written for managing adapters and for updating the fiat list in storage(this doesn't need to be done periodically as in the world we don't see a new fiat currency emerge often).  
1. manage_adapters.py - CLI based adapter creation/list/deletion. The script prompts for the details on creation like adapter directory/interval/etc. For deletion it requires an adapter ID, which can be taken from the list. Must change the coiner API IP before usage!  
2. get_fiat.py -populate the FIAT endpoint in storage(check the STORAGE IP before usage).  

# Coiner daemon:  
The daemon is managed via the coiner.py entry point in the root directory. It has 4 parameters - start/stop/restart/status.

# Daemon explanation and working:  
The daemon uses the UNIX double fork mechanism to daemonize itself upon launch. It has 4 starting Processes(not threads) - the Main process, the Incoming process, the Poller process and the Manager process. All three are part of the main coiner class in src/coiner.py.    

1. Manager process:
The manager process simply passes pickled objects between the starter process(before the 2 forks) and the incoming/main processes.

2. Incoming process - listens for incoming events on a UNIX socket. This is still WIP and isn't finished - the only thing that it supports right now is for getting the status of the daemon

3. Main process - this is where the main looping logic lies. This is based of the MarketManager class method main. It fetches all adapters via the django model and runs through each adapter, checking if it's enabled and comparing the last run timestamp and the current time. If it's meant to be run, the main process sends it to the Coiner App for execution. The response is then checked and if the response is 200 OK, it updates the adapter last_run_id and state to running.  

4. Poller process - this process runs periodic checks against the Coiner app. It fetches all the adapters that are in state running and then checks if the adapter has finished running and if it has crashed.  

# Configs:
Daemon and API configuration is dependent on the environment. Configuration is fetched from environmental variables.    
Dev config in marketmanager/config_dev.py. Staging config in marketmanager/config_staging. Additional configurations plus the requirements for the container, nginx, uwsgi are in ./configs.


# Adapter:
The main "worker" is an adapter - it must follow certain requirements to work properly.  
1. The adapter filename and the the main class name MUST be the same.  
2. The main event method MUST be named "run" and MUST NOT take any parameters.  
3. The adapter class contructor MUST take in two arguments - adapter params(optional parameters for the adapter, if the programmer sees fit) and STORAGE_SOURCE_ID (mentioned above). The storage source ID is needed when returning the parsed data in JSON format to the adapterworker class.  
The adapter can have as many other methods as you want.  
