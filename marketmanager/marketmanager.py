"""Market Manager - manage crypto exchange data."""
import os
import sys
import pickle
import logging.config
import django
from django.utils import timezone
from time import sleep
from concurrent.futures import ThreadPoolExecutor
from socket import (socket, AF_INET, SOCK_STREAM, SOL_SOCKET, SO_REUSEADDR)
from socket import timeout as SOCKET_TIMEOUT
from django_celery_results.models import TaskResult

from api.tasks import fetch_exchange_data
from api.models import Exchange, ExchangeStatus
from marketmanager.celery import app



class MarketManager(object):
    """MarketManager main class.

    Methods:
    init - start up by passing the daemon config(found in settings.py)
    incoming - incoming request loop. See incoming method for details.
    scheduler - marketmanager scheduling event loop.
    poller - marketmanager polling loop. See poller for details.
    """

    def __init__(self, **config):
        """Set up our initial parameters."""
        self.socket_port = config["socket_port"]
        self.lock_file = config["lock_file"]
        self.worker_limit = int(config["threads"])
        self.logger = logging.getLogger("marketmanager")

    def checkCeleryStatus(self):
        """Check the status of celery."""
        # Run the check 3 times in case of failure
        for i in range(1, 3):
            result = app.control.inspect().stats()
            if result:
                self.logger.info("Got celery stats: {}".format(result))
                return result
            self.logger.error("Couldn't get celery stats on {} try".format(i))

    def checkTaskResult(self, status):
        """Check the status of a running exchange in celery."""
        self.logger.info("Running poller check on {}".format(status.adapter))
        if not status.time_started:
            msg = "Exchange {} is without start time!".format(status.adapter)
            self.logger.error(msg)
            status.running = False
            status.save()
            return
        time_now = timezone.now().timestamp()
        time_started = status.time_started.timestamp()
        timeout = status.timeout
        if time_now <= time_started + timeout:
            # Still haven't reached the timeout
            msg = "Exchange {} is within timeout!".format(status.exchange)
            self.logger.info(msg)
            return
        run_id = status.last_run_id
        msg = "Timeout reached for {}.Revoking task: {}".format(status.adapter,
                                                                run_id)
        self.logger.error(msg)
        app.control.revoke(run_id, terminate=True, timeout=3)
        status.running = False
        status.last_run_status = "Timeout reached"
        status.save()

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
            msg += " Delta: {}".format(current_time-last_run)
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
        """Get the status of the market manager process and db."""
        response = {"id": request_id,
                    "type": "status-response",
                    "status": "running"}
        return response

    def handler(self, connection, addr):
        """Handle an incoming request.
        We support 2 types of incoming - configure and status."""
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
        connection.send(pickle.dumps(response))
        connection.close()

    def incoming(self):
        """Loop upon the incoming queue for incoming requests."""
        with ThreadPoolExecutor(max_workers=self.worker_limit) as executor:
            with socket(AF_INET, SOCK_STREAM) as sock:
                sock.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
                sock.bind(("0.0.0.0", self.socket_port))
                sock.listen(10)
                self.logger.info("Server listening on local TCP socket %s",
                                 self.socket_port)
                while True:
                    conn, addr = sock.accept()
                    executor.submit(self.handler, conn, addr)
                self.logger.info("Server shutting down")

    def getExchanges(self, exchange_id=None):
        """Get the exchange(s) from the db. Wrap around the DB Errors."""
        if not exchange_id:
            exchanges = Exchange.objects.filter(enabled=True)
        else:
            exchanges = Exchange.objects.filter(pk=exchange_id)
        self.logger.info("Got exchanges: {}".format(exchanges))
        return exchanges

    def getExchangeStatus(self, exc_id=None):
        """Get the ExchangeStatus entry(s). Wrap errors from the DB."""
        if exc_id:
            queryset = ExchangeStatus.objects.filter(exchange_id=exc_id)
            if not queryset:
                statuses = ExchangeStatus.objects.create(exchange_id=exc_id)
                statuses.save()
            else:
                statuses = queryset[0]
        else:
            statuses = ExchangeStatus.objects.filter(running=True)
        try:
            # Django executes the SQL on the first invokation of the result
            # Make sure we capture an error
            self.logger.info("Got statuses: {}".format(statuses))
        except django.db.utils.OperationalError as e:
            msg = "DB operational error. Error: {}".format(e)
            self.logger.error(msg)
            # statuses = []
        return statuses

    def poller(self):
        """Poller - checks the status of each RUNNING exchange."""
        self.logger.info("Starting poller.")
        while True:
            statuses = self.getExchangeStatus()
            if not statuses:
                sleep(5)
                continue
            for status in statuses:
                if not status.last_run_id:
                    msg = "Missing last run id for exchange [{}]".format(
                                                              status.exchange)
                    self.logger.info(msg)
                    continue
                self.checkTaskResult(status)
            msg = "Finished running through all exchanges."
            self.logger.info(msg)
            sleep(10)

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
            if not exchanges:
                sleep(5)
                continue
            for exchange in exchanges:
                status = self.getExchangeStatus(exchange.id)
                should_run = self.checkExchange(exchange, status)
                if not should_run:
                    continue
                task_id = fetch_exchange_data.delay(exchange.id)
                if task_id:
                    status.time_started = timezone.now()
                    status.last_run_id = task_id
                    status.running = True
                    status.save()
            msg = "Finished running through all exchanges."
            self.logger.info(msg)
            sleep(10)
