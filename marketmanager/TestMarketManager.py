"""MarketManager class test suite."""
import unittest
from unittest.mock import patch
import os
import time
import pickle
import multiprocessing as mp
from socket import socket, AF_UNIX, SOCK_STREAM
from django.db.models.query import QuerySet
from django.utils import timezone
from django.conf import settings
from datetime import datetime

# Local imports
from marketmanager import marketmanager
from marketmanager.marketmanager import MarketManager
from api.models import Exchange, ExchangeStatus

config = settings.MARKET_MANAGER_DAEMON
test_request_status = {"id": 1,
                       "type": "status"}


def get_json():
    return {"id": "1234"}


class TestMarketManager(unittest.TestCase):
    """Test the Coiner class and methods."""

    def setUp(self):
        self.manager = MarketManager(**config)
        self.exchange = Exchange(name="TestExchange", interval=300)
        self.exchange.save()
        self.status = ExchangeStatus(exchange=self.exchange)
        self.status.save()

    def tearDown(self):
        """Cleanup."""
        self.exchange.delete()
        self.status.delete()
        try:
            os.remove(config['sock_file'])
        except FileNotFoundError:
            pass

    def testInit(self):
        """Test that the DB class was created."""
        self.assertIsInstance(self.manager, MarketManager)

    def testCheckExchangeNew(self):
        """Run the checkExchange method with new adapter.

        It must return run now(aka True)
        """
        self.status.last_run = None
        self.status.running = False
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertTrue(run)

    def testCheckExchangeRunning(self):
        """Run the checkExchange method which is running.

        It must return not to run(aka False)
        """
        self.status.running = True
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertFalse(run)

    def testCheckExchangeDisabled(self):
        """Run the checkExchange method with a disabled adapter.

        It must return not to run(aka False)
        """
        self.exchange.enabled = False
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertFalse(run)

    def testCheckExchange_WithinLastRun(self):
        """Run the checkExchange method.

        Test with a last run time within the interval - the method must return
        False."""
        last_run = timezone.now().timestamp() - 150
        time = datetime.fromtimestamp(last_run)
        self.status.last_run = timezone.make_aware(time)
        self.status.running = False
        self.status.save()
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertFalse(run)

    def testCheckExchnage_OutsideLastRun(self):
        """Run the checkExchange method.

        Test with a last run time outside the interval - the method must return
        False."""
        last_run = timezone.now().timestamp() - 350
        time = datetime.fromtimestamp(last_run)
        self.status.last_run = timezone.make_aware(time)
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertTrue(run)

    def testGetStatus(self):
        """Test the get status on empty Coiner."""
        res = self.manager.handleStatusEvent(1)
        self.assertEqual((res['id'], res['type']), (1, "status-response"))

    def testGetExchange(self):
        """Test getting the adapter objects from the DB."""
        result = self.manager.getExchanges()
        self.assertTrue(isinstance(result, QuerySet))

    def testHandleRunRequestNotExisting(self):
        """Test running an adapter through this method."""
        result = self.manager.handleRunRequest(150)
        # The result is a message we relay back as a HTTP response
        self.assertTrue(isinstance(result, str))

    def testIncoming(self):
        """Test the incoming loop with a status type request."""
        p = mp.Process(target=self.manager.incoming)
        p.start()
        time.sleep(0.1)
        s = socket(AF_UNIX, SOCK_STREAM)
        s.connect((config['sock_file']))
        data = pickle.dumps({'id': 1, 'type': 'status'})
        s.sendall(data)
        data = s.recv(1024)
        res = pickle.loads(data)
        s.close()
        self.assertEqual((res["type"], res["id"]), ("status-response", 1))
        p.terminate()

    def testcoinerNoResultFalse(self):
        """Test the method with a False result"""
        self.manager.coinerNoResult(False, self.status)
        self.assertIsNotNone(self.status.last_run_status)

    def testcoinerNoResult_EmptyList(self):
        """Test the method with a empty list result"""
        self.manager.coinerNoResult([], self.status)
        self.assertIsNotNone(self.status.last_run_status)

    def testcoinerNoResult_EmptyListWithStartTime(self):
        """Test the method with a empty list result"""
        self.status.running = True
        timestamp = timezone.now().timestamp() - 600
        time = datetime.fromtimestamp(timestamp)
        self.status.time_started = timezone.make_aware(time)
        self.manager.coinerNoResult([], self.status)
        self.assertIsNotNone(self.status.last_run_status)

    def testMain_WithoutExchanges(self):
        """Test the main process with no adapters."""
        p = mp.Process(target=self.manager.main)
        p.start()
        time.sleep(3)
        # The process should be alive
        self.assertTrue(p.is_alive)
        p.terminate()

    # Mock tests with Coiner
    @patch(marketmanager.__name__ + ".MarketManager.coinerRunExchange")
    def testHandleRunRequest_WithRequest(self, mock_item):
        """Test running an adapter through this method."""
        mock_item.return_value = True
        result = self.manager.handleRunRequest(self.exchange.id)
        self.assertTrue(isinstance(result, str))

    @patch(marketmanager.__name__ + ".MarketManager.coinerRunExchange")
    def testHandleRunRequest_FalseResult(self, mock_item):
        """Test running an adapter through this method."""
        mock_item.return_value = False
        result = self.manager.handleRunRequest(self.exchange.id)
        self.assertFalse(result)

    @patch("marketmanager.marketmanager.appRequest")
    def testMain_WithExchange(self, mock_item):
        """Test the main process with no adapters."""
        mock_item.return_value = get_json()
        exchange = Exchange(name="Test", interval=30)
        exchange.save()
        p = mp.Process(target=self.manager.main)
        p.start()
        time.sleep(0.5)
        # The process should be alive
        self.assertTrue(p.is_alive())
        # Cleanup
        p.terminate()

    @patch("marketmanager.marketmanager.appRequest")
    def testCoinerRunExchange(self, mock_item):
        mock_item.return_value = get_json()
        resp = self.manager.coinerRunExchange(self.exchange, self.status)
        self.assertTrue(resp)
        self.assertTrue(self.status.running)

    @patch("marketmanager.marketmanager.appRequest")
    def testcoinerRunExchange_BadResponse(self, mock_item):
        mock_item.return_value = {"error": "400 Bad request"}
        resp = self.manager.coinerRunExchange(self.exchange, self.status)
        self.assertFalse(resp)

    @patch("marketmanager.marketmanager.appRequest")
    def testCheckResult_NoTimeStarted(self, mock_item):
        mock_item.return_value = [get_json()]
        self.status.last_run_id = get_json()["id"]
        self.status.running = True
        resp = self.manager.coinerCheckResult(self.status)
        self.assertFalse(resp)
        self.assertFalse(self.status.running)

    @patch("marketmanager.marketmanager.appRequest")
    def testCheckResult_WithTimeStarted(self, mock_item):
        mock_item.return_value = [get_json()]
        self.status.last_run_id = get_json()["id"]
        self.status.time_started = timezone.now()
        self.status.running = True
        resp = self.manager.coinerCheckResult(self.status)
        self.assertFalse(resp)
        self.assertTrue(self.status.running)

    @patch("marketmanager.marketmanager.appRequest")
    def testCheckResult_WithTimeStartedLong(self, mock_item):
        timestamp = timezone.now().timestamp() - 1500
        time = datetime.fromtimestamp(timestamp)
        self.status.last_run_id = get_json()["id"]
        self.status.running = True
        self.status.time_started = timezone.make_aware(time)
        resp = self.manager.coinerCheckResult(self.status)
        self.assertFalse(resp)
        self.assertFalse(self.status.running)


if __name__ == "__main__":
    unittest.main()
