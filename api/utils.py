"""Scheduler daemon client."""
from socket import socket, AF_UNIX, SOCK_STREAM
import pickle
import requests

from marketmanager.settings import MARKET_MANAGER_DAEMON, STORAGE_SOURCE_URL


def create_source(name):
    """Create an exchange source in the Storage app."""
    data = {"name": name}
    response = requests.post(STORAGE_SOURCE_URL, data)
    if response.status_code != 200:
        return response.status_code
    return response.json()


def get_source(name):
    """Get an existing source from storage."""
    url_filter = "{}?name={}".format(STORAGE_SOURCE_URL, name)
    response = requests.get(url_filter)
    if response.status_code != 200:
        return response.status_code
    return response.json()


class Client(object):
    """This class interacts with scheduler daemon via sockets."""

    def __init__(self):
        """Read the scheduler config and connect to the daemon."""
        self.sock = socket(AF_UNIX, SOCK_STREAM)

    def connect(self):
        self.sock.connect(MARKET_MANAGER_DAEMON['sock_file'])

    def exchangeRun(self, exchange_id):
        """Run the fetching of data for the exchange."""
        request = {"type": "exchange_run", "exchange_id": exchange_id}
        self.sock.sendall(pickle.dumps(request))
        response = self.sock.recv(1024)
        return pickle.loads(response)

    def sendRequest(self, request):
        """Send the given request to scheduler."""
        self.sock.sendall(pickle.dumps(request))
        response = self.sock.recv(1024)
        return pickle.loads(response)

    def getStatus(self, request_id):
        """Get the current status of the scheduler daemon."""
        status_request = {'id': request_id, 'type': 'status'}
        self.sock.sendall(pickle.dumps(status_request))
        response = self.sock.recv(1024)
        return pickle.loads(response)
