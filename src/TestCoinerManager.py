"""Coiner class test suite."""
import unittest
from unittest.mock import patch
from requests.exceptions import ConnectionError, Timeout
import os
import time
import pickle
import multiprocessing as mp
from socket import socket, AF_UNIX, SOCK_STREAM
from django.db.models.query import QuerySet
from django.utils import timezone
from datetime import datetime

# Local imports
from src import marketmanager
from marketmanager import settings
from api.models import Adapter, AdapterStatus

config = settings.COINER_MANAGER_DAEMON

test_request_status = {"id": 1,
                       "type": "status"}

with open("tests/TestAdapter.py", "r") as f:
    source = f.read()
adapter_dict = {"name": "TestAdapter", "type": "CMN", "source_id": 1,
                "source_code": source, "interval": 300}


def get_json():
    return {"id": "1234"}


class TestMarketManager(unittest.TestCase):
    """Test the Coiner class and methods."""

    def setUp(self):
        self.manager = marketmanager.MarketManager(**config)
        self.adapter = Adapter(name=adapter_dict["name"],
                               type=adapter_dict["type"],
                               interval=adapter_dict["interval"],
                               storage_source_id=adapter_dict["source_id"],
                               source_code=adapter_dict["source_code"])
        self.adapter.save()
        self.status = AdapterStatus(adapter=self.adapter)
        self.status.adapter_id = self.adapter.id
        self.status.save()

    def tearDown(self):
        """Cleanup."""
        self.status.delete()
        self.adapter.delete()
        try:
            os.remove(config['main']['sock_file'])
        except FileNotFoundError:
            pass

    def testInit(self):
        """Test that the DB class was created."""
        self.assertIsInstance(self.manager, marketmanager.MarketManager)

    def testCheckAdapterNew(self):
        """Run the checkAdapter method with new adapter.

        It must return run now(aka True)
        """
        self.status.last_run = None
        self.status.running = False
        run = self.manager.checkAdapter(self.adapter, self.status)
        self.assertTrue(run)

    def testCheckAdapterRunning(self):
        """Run the checkAdapter method which is running.

        It must return not to run(aka False)
        """
        self.status.running = True
        run = self.manager.checkAdapter(self.adapter, self.status)
        self.assertFalse(run)

    def testCheckAdapterDisabled(self):
        """Run the checkAdapter method with a disabled adapter.

        It must return not to run(aka False)
        """
        self.adapter.enabled = False
        run = self.manager.checkAdapter(self.adapter, self.status)
        self.assertFalse(run)

    def testCheckAdapterWithinLastRun(self):
        """Run the checkAdapter method.

        Test with a last run time within the interval - the method must return
        False."""
        last_run = timezone.now().timestamp() - 150
        time = datetime.fromtimestamp(last_run)
        self.status.last_run = timezone.make_aware(time)
        self.status.running = False
        self.status.save()
        run = self.manager.checkAdapter(self.adapter, self.status)
        self.assertFalse(run)

    def testCheckAdapterOutsideLastRun(self):
        """Run the checkAdapter method.

        Test with a last run time outside the interval - the method must return
        False."""
        last_run = timezone.now().timestamp() - 350
        time = datetime.fromtimestamp(last_run)
        self.status.last_run = timezone.make_aware(time)
        run = self.manager.checkAdapter(self.adapter, self.status)
        self.assertTrue(run)

    def testGetStatus(self):
        """Test the get status on empty Coiner."""
        res = self.manager.handleStatusEvent(1)
        self.assertEqual((res['id'], res['type']), (1, "status-response"))

    def testGetAdapter(self):
        """Test getting the adapter objects from the DB."""
        result = self.manager.getAdapters()
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
        s.connect((config['main']['sock_file']))
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

    def testcoinerNoResultEmptyList(self):
        """Test the method with a empty list result"""
        self.manager.coinerNoResult([], self.status)
        self.assertIsNotNone(self.status.last_run_status)

    def testcoinerNoResultEmptyListWithStartTime(self):
        """Test the method with a empty list result"""
        self.status.running = True
        timestamp = timezone.now().timestamp() - 600
        time = datetime.fromtimestamp(timestamp)
        self.status.time_started = timezone.make_aware(time)
        self.manager.coinerNoResult([], self.status)
        self.assertIsNotNone(self.status.last_run_status)

    def testMainWithoutAdapters(self):
        """Test the main process with no adapters."""
        p = mp.Process(target=self.manager.main)
        p.start()
        time.sleep(3)
        # The process should be alive
        self.assertTrue(p.is_alive)
        p.terminate()

    # Mock tests with Coiner
    @patch(marketmanager.__name__ + ".MarketManager.coinerRunAdapter")
    def testHandleRunRequest(self, mock_item):
        """Test running an adapter through this method."""
        mock_item.return_value = True
        result = self.manager.handleRunRequest(self.adapter.id)
        self.assertTrue(isinstance(result, AdapterStatus))

    @patch(marketmanager.__name__ + ".MarketManager.coinerRunAdapter")
    def testHandleRunRequestFalseResult(self, mock_item):
        """Test running an adapter through this method."""
        mock_item.return_value = False
        result = self.manager.handleRunRequest(self.adapter.id)
        self.assertFalse(result)

    @patch(marketmanager.__name__ + ".requests.request")
    def testMainWithAdapter(self, mock_item):
        """Test the main process with no adapters."""
        mock_item.return_value.status_code = 200
        mock_item.return_value.json = get_json
        source_code = "print('test')"
        adapter = Adapter(name="Test", interval=30, source_code=source_code,
                          storage_source_id=1, type="CMN")
        adapter.save()
        p = mp.Process(target=self.manager.main)
        p.start()
        time.sleep(0.5)
        # The process should be alive
        self.assertTrue(p.is_alive())
        # Cleanup
        p.terminate()

    @patch(marketmanager.__name__ + ".requests.request")
    def testCoinerRequestWithResponse(self, mock_item):
        """Test with a mocked response"""
        mock_item.return_value.ok = True
        mock_item.return_value.status_code = 200
        result = self.manager.coinerRequest("test", "test")
        self.assertTrue(result)

    @patch(marketmanager.__name__ + ".requests.request", autospec=True)
    def testCoinerRequestWithConnectionError(self, mock_item):
        """Test with a mocked response"""
        mock_item.side_effect = ConnectionError
        resp = self.manager.coinerRequest("post", "test_url")
        self.assertFalse(resp)

    @patch(marketmanager.__name__ + ".requests.request", autospec=True)
    def testCoinerRequestWithTiemout(self, mock_item):
        mock_item.side_effect = Timeout
        resp = self.manager.coinerRequest("post", "test_url")
        self.assertFalse(resp)

    @patch(marketmanager.__name__ + ".requests.request")
    def testCoinerRunAdapter(self, mock_item):
        mock_item.return_value.ok = True
        mock_item.return_value.status_code = 200
        mock_item.return_value.json = get_json
        resp = self.manager.coinerRunAdapter(self.adapter, self.status)
        self.assertTrue(resp)
        self.assertTrue(self.status.running)

    @patch(marketmanager.__name__ + ".requests.request")
    def testCoinerRunAdapterBadResponse(self, mock_item):
        mock_item.return_value.ok = False
        mock_item.return_value.status_code = 404
        resp = self.manager.coinerRunAdapter(self.adapter, self.status)
        self.assertFalse(resp)

    @patch(marketmanager.__name__ + ".MarketManager.coinerRequest")
    def testCheckResultNoTimeStarted(self, mock_item):
        mock_item.return_value = [get_json()]
        self.status.last_run_id = get_json()["id"]
        self.status.running = True
        resp = self.manager.coinerCheckResult(self.status)
        self.assertFalse(resp)
        self.assertFalse(self.status.running)

    @patch(marketmanager.__name__ + ".MarketManager.coinerRequest")
    def testCheckResultWithTimeStarted(self, mock_item):
        mock_item.return_value = [get_json()]
        self.status.last_run_id = get_json()["id"]
        self.status.time_started = timezone.now()
        self.status.running = True
        resp = self.manager.coinerCheckResult(self.status)
        self.assertFalse(resp)
        self.assertTrue(self.status.running)

    @patch(marketmanager.__name__ + ".MarketManager.coinerRequest")
    def testCheckResultWithTimeStartedLong(self, mock_item):
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
