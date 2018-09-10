"""Market Manager - manage crypto exchange data."""
import os
import sys
import pickle
import logging.config
import django
from django.utils import timezone
from django.conf import settings
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from socket import (socket, AF_UNIX, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR)
from socket import timeout as SOCKET_TIMEOUT

from applib.tools import appRequest

# Set the django settings env variable and load django
if "DJANGO_SETTINGS_MODULE" not in os.environ:
    os.environ["DJANGO_SETTINGS_MODULE"] = "marketmanager.settings"
    django.setup()
    from api.models import Exchange, ExchangeStatus
else:
    from api.models import Exchange, ExchangeStatus


class MarketManager(object):
    """Coiner class.

    Methods:
    init - start up by passing two queues(in/out),
           database params(host/port/user/pass)
    incoming - incoming request loop. See incoming method for details.
    main - marketmanager main event loop. See main method for details.
    poller - marketmanager polling loop. See poller for details.
    """

    def __init__(self, **config):
        """Set up our initial parameters."""
        self.socket_file = config["sock_file"]
        self.lock_file = config["lock_file"]
        self.worker_limit = int(config["threads"])
        self.logger = logging.getLogger(__name__)
        logging.config.dictConfig(config["logging"])

    def coinerRunExchange(self, exchange, status):
        """Send a request to coiner"""
        msg = "Sending request to coiner for {}".format(exchange.name)
        self.logger.info(msg)
        name = exchange.name
        data = {"name": name, "exchange_id": exchange.id}
        response = appRequest("post", settings.COINER_URLS["exchange"], data)
        # Check the response
        if "error" in response:
            msg = "Exchange run failed with: {}".format(response["error"])
            self.logger.error(msg)
            # No response
            return msg
        # Request is successful
        msg = "Coiner accepted run request for exchange {}.".format(name)
        self.logger.info(msg)
        status.running = True
        status.last_run_id = response["id"]
        status.time_started = timezone.now()
        status.save()
        return True

    def coinerNoResult(self, result, status):
        """Work through the empty result from coiner.

        If false - then there was a timeout/connection error.
        If an empty list - coiner couldn't find the celery task ID.
        """
        if isinstance(result, list):
            msg = "Exchange run failed - no task ID in coiner!"
            self.logger.critical(msg)
            # Set the status and running to false
            status.last_run_status = msg
            # Check since how long is the start time
            if not status.time_started:
                # There is no start time, so the exchange was not run
                return
            time_now = timezone.now().timestamp()
            start_time = status.time_started.timestamp()
            if start_time + 10 < time_now:
                status.running = False
        else:
            msg = "Failed to fetch exchange results from coiner!"
            self.logger.critical(msg)
            status.last_run_status = msg
        status.save()

    def coinerCheckResult(self, status):
        """Check the status of an running exchange in coiner."""
        self.logger.info("Running poller check on {}".format(status.exchange))
        url = "{}?task_id={}".format(settings.COINER_URLS['results'],
                                     status.last_run_id)
        response = appRequest("get", url)
        if not response:
            return self.coinerNoResult(response, status)
        if "error" in response:
            return response
        current_status = response[0].get("status")
        success = False
        if current_status != "FAILURE" and current_status != "SUCCESS":
            # Exchange is still in pending or running
            msg = "Exchange {} is in state: {}".format(status.exchange,
                                                       current_status)
            self.logger.info(msg)
            # Check if the exchange is running for more than 10 minutes
            if not status.time_started:
                status.running = False
                status.save()
                return
            time_now = timezone.now().timestamp()
            start_time = status.time_started.timestamp()
            if start_time + 120 < time_now:
                status.running = False
                status.last_run_status = "STUCK"
            else:
                status.last_run_status = msg
            status.save()
            return
        elif current_status == "FAILURE":
            msg = "Exchange run for {} failed!".format(status.exchange)
            self.logger.critical(msg)
        elif current_status == "SUCCESS":
            success = False
            msg = "Exchange run for {} successfull".format(status.exchange)
            self.logger.info(msg)
        else:
            msg = "Missing exchange status for {}".format(status.exchange)
            self.logger.critical(msg)
        status.last_run_status = response[0]["result"]
        if success:
            # Only update the last run if it's sucessful
            status.last_run = timezone.now()
        status.running = False
        status.save()
        return True

    def checkExchange(self, exchange, status):
        """Check if the exchange data is meant to be fetched."""
        if not exchange.enabled:
            msg = "Exchange {} is disabled: Skipping".format(exchange.name)
            self.logger.info(msg)
            return False
        if status.running:
            msg = "Exchange fetch running: {}. Skipping.".format(exchange.name)
            self.logger.info(msg)
            return False
        if status.last_run:
            current_time = timezone.now().timestamp()
            last_run = status.last_run.timestamp()
            interval = int(exchange.interval)
            msg = "Running check for {}.".format(exchange.name)
            msg += " Last run: {},".format(last_run)
            msg += " Interval: {},".format(interval)
            msg += " Current time: {}".format(current_time)
            self.logger.debug(msg)
            if last_run + interval >= current_time:
                return False
        msg = "Exchange {} must run NOW!".format(exchange.name)
        self.logger.info(msg)
        return True

    def handleConfigEvent(self, **request):
        """Configure the running manager instance."""
        pass

    def handleStatusEvent(self, request_id):
        """Get the status of the coiner manager process and db."""
        response = {"id": request_id,
                    "type": "status-response",
                    "status": "running"}
        return response

    def handleRunRequest(self, exchange_id):
        """Immediately run the fetch on the exchange data."""
        self.logger.debug("Handling single run for exchange.")
        exchange = self.getExchanges(exchange_id)
        if not exchange:
            msg = "Couldn't find exchange."
            self.logger.debug(msg)
            return msg
        status = self.getExchangeStatus(exchange_id)
        result = self.coinerRunExchange(exchange[0], status)
        if result:
            msg = "Coiner has accepted exchange manual run!"
            self.logger.info(msg)
            return msg
        self.logger.info("Coiner couldn't handle manual run request")
        return False

    def handler(self, connection, addr):
        """Handle an incoming request."""
        pid = os.getpid()
        BUFFER = 1024
        self.logger.info("Handling connection [%s].", pid)
        received = bytes()
        while True:
            try:
                data = connection.recv(BUFFER)
            except SOCKET_TIMEOUT:
                break
            received += data
            # There is an extra 33 bytes that comes through the connection
            if sys.getsizeof(data) < (BUFFER + 33):
                break
            else:
                # Set a timeout. This is needed if the data is exactly the
                # length of the buffer - in that case without a timeout
                # we will get stuck in the recv part of the loop
                connection.settimeout(0.5)
        loaded_data = pickle.loads(data)
        self.logger.debug("Data loaded: %s", loaded_data)
        if not isinstance(loaded_data, dict):
            response = pickle.dumps("Bad request - expected dictionary.")
            connection.send(response)
            self.logger.debug("Bad request - expected dictionary")
            return False
        if loaded_data["type"] == "status":
            response = self.handleStatusEvent(loaded_data["id"])
            self.logger.debug("Response to status request: %s", response)
        elif loaded_data["type"] == "configure":
            response = self.handleConfigEvent(loaded_data["data"])
            self.logger.debug("Response to configure request: %s", response)
        elif loaded_data["type"] == "exchange_run":
            response = self.handleRunRequest(loaded_data["exchange_id"])
            self.logger.debug("exchange run finished! Response: {}".format(
                                                               response))
        connection.send(pickle.dumps(response))
        connection.close()

    def incoming(self):
        """Loop upon the incoming queue for incoming requests.

        Incoming request types: ['status', 'configure']
        Workflow:
        1) Get the request from the queue
        2) Sanitize it by checking the request type
        3) Pass it to the appropriate method for execution
        4) Put the response in the outbound queue and loop again
        """
        with ThreadPoolExecutor(max_workers=self.worker_limit) as executor:
            with socket(AF_UNIX, SOCK_STREAM) as sock:
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.bind(self.socket_file)
                sock.listen(10)
                self.logger.info("Server listening on local UNIX socket %s",
                                 self.socket_file)
                while True:
                    conn, addr = sock.accept()
                    executor.submit(self.handler, conn, addr)
                self.logger.info("Server shutting down")

    def getExchanges(self, exchange_id=None):
        """Get the enabled exchanges from the db."""
        if not exchange_id:
            return Exchange.objects.filter(enabled=True)
        return Exchange.objects.filter(pk=exchange_id)

    def getExchangeStatus(self, exchange_id):
        """Get the ExchangeStatus entry for the specific id."""
        queryset = ExchangeStatus.objects.filter(exchange_id=exchange_id)
        if not queryset:
            status = ExchangeStatus.objects.create(exchange_id=exchange_id)
            status.save()
            return status
        return queryset[0]

    def poller(self):
        self.logger.info("Starting poller.")
        while True:
            try:
                statuses = ExchangeStatus.objects.filter(running=True)
                self.logger.info("Got statuses: {}".format(statuses))
                if not statuses:
                    sleep(5)
                    continue
                for status in statuses:
                    if not status.last_run_id:
                        continue
                    self.coinerCheckResult(status)
                msg = "Finished running through all exchanges."
                self.logger.info(msg)
                sleep(10)
            except django.db.utils.OperationalError as e:
                msg = "Database operation failed: {}".format(e)
                self.logger.critical(msg)

    def scheduler(self):
        """Event loop which can be called as a separate Process.

        Workflow:
        1) Get the exchanges
        2) Run checks if the exchange should be run(enabled, time)
        3) Send the request to fetch the exchange data to coiner
        """
        self.logger.info("Starting main event loop.")
        while True:
            exchanges = self.getExchanges()
            self.logger.info("Got exchanges: {}".format(exchanges))
            if not exchanges:
                sleep(5)
                continue
            for exchange in exchanges:
                status = self.getExchangeStatus(exchange.id)
                should_run = self.checkExchange(exchange, status)
                if not should_run:
                    continue
                result = self.coinerRunExchange(exchange, status)
                if not result:
                    continue
            msg = "Finished running through all exchanges."
            self.logger.info(msg)
            sleep(10)
