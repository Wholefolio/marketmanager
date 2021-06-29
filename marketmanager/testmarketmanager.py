"""MarketManager class test suite."""
import unittest
import os
import time
import multiprocessing as mp
from unittest.mock import patch
from django.db.models.query import QuerySet
from django.utils import timezone
from django.conf import settings
from datetime import datetime
from django_celery_results.models import TaskResult

# Local imports
from marketmanager.marketmanager import MarketManager
from api.models import Exchange, ExchangeStatus

config = settings.MARKET_MANAGER_DAEMON
test_request_status = {"id": 1,
                       "type": "status"}


def get_json():
    return {"id": "1234"}


class TestMarketManager(unittest.TestCase):
    """Test the MarketManager class and methods."""

    def setUp(self):
        self.manager = MarketManager(**config)
        self.exchange = Exchange(name="TestExchange", interval=300)
        self.exchange.save()
        self.status = ExchangeStatus(exchange=self.exchange)
        self.status.save()
        self.task = TaskResult()
        self.task.task_id = get_json()["id"]
        self.task.save()

    def tearDown(self):
        """Cleanup."""
        for i in (self.exchange, self.status, self.task):
            try:
                i.delete()
            except AssertionError:
                pass
        try:
            os.remove(config['sock_file'])
        except FileNotFoundError:
            pass
        if hasattr(self, "extra_exchanges"):
            print(self.extra_exchanges)
            for i in self.extra_exchanges:
                obj = Exchange.objects.get(name=i)
                obj.delete()

    def testInit(self):
        """Test that the DB class was created."""
        self.assertIsInstance(self.manager, MarketManager)

    def testCheckEnabledExchanges_Existing(self):
        """Test the method with just the test exchange."""
        settings.ENABLED_EXCHANGES = [self.exchange.name]
        self.manager._checkEnabledExchanges()
        self.assertEqual(Exchange.objects.count(), 1)

    def testCheckExchange_New(self):
        """Run the checkExchange method with new exchange.

        It must return run now(aka True)
        """
        self.status.last_run = None
        self.status.running = False
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertTrue(run)

    def testCheckExchange_Running(self):
        """Run the checkExchange method which is running.

        It must return not to run(aka False)
        """
        self.status.running = True
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertFalse(run)

    def testCheckExchange_Disabled(self):
        """Run the checkExchange method with a disabled exchange.

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

    def testCheckExchange_OutsideLastRun(self):
        """Run the checkExchange method.

        Test with a last run time outside the interval - the method must return
        False."""
        last_run = timezone.now().timestamp() - 350
        time = datetime.fromtimestamp(last_run)
        self.status.last_run = timezone.make_aware(time)
        run = self.manager.checkExchange(self.exchange, self.status)
        self.assertTrue(run)

    def testGetExchange(self):
        """Test getting the exchange objects from the DB."""
        result = self.manager.getExchanges()
        self.assertTrue(isinstance(result, QuerySet))

# Test main processes - scheduler, poller

    def testScheduler_WithoutExchanges(self):
        """Test the scheduler process with no exchanges."""
        self.exchange.delete()
        p = mp.Process(target=self.manager.scheduler)
        p.start()
        time.sleep(1)
        # The process should be alive
        self.assertTrue(p.is_alive)
        p.terminate()

    def testScheduler_WithExchange(self):
        """Test the scheduler process with no exchanges."""
        p = mp.Process(target=self.manager.scheduler)
        p.start()
        time.sleep(1)
        # The process should be alive
        self.assertTrue(p.is_alive())
        # Cleanup
        p.terminate()

    def testPoller_WithoutStatuses(self):
        """Test the poller process with no statuses."""
        self.status.delete()
        p = mp.Process(target=self.manager.poller)
        p.start()
        time.sleep(1)
        # The process should be alive
        self.assertTrue(p.is_alive)
        p.terminate()

    def testPoller_WithStatuses(self):
        """Test the poller process with existing and statuses."""
        self.status.running = True
        p = mp.Process(target=self.manager.poller)
        p.start()
        time.sleep(1)
        # The process should be alive
        self.assertTrue(p.is_alive())
        # Cleanup
        p.terminate()

    def testCheckTaskResult_WithTimeStarted(self):
        self.status.last_run_id = get_json()["id"]
        self.status.time_started = timezone.now()
        self.status.running = True
        self.manager.checkTaskResult(self.status)
        self.assertTrue(self.status.running)

    @patch("marketmanager.marketmanager.app.control.revoke")
    def testCheckTaskResult_WithTimeStartedLong(self, mock_item):
        mock_item.return_value = True
        timestamp = timezone.now().timestamp() - 1500
        time = datetime.fromtimestamp(timestamp)
        self.status.last_run_id = get_json()["id"]
        self.status.running = True
        self.status.time_started = timezone.make_aware(time)
        self.manager.checkTaskResult(self.status)
        self.assertFalse(self.status.running)

    @patch("marketmanager.marketmanager.app.control.revoke")
    def testCheckTaskResult_Failure(self, mock_item):
        mock_item.return_value = True
        timestamp = timezone.now().timestamp() - 1500
        time = datetime.fromtimestamp(timestamp)
        self.status.last_run_id = get_json()["id"]
        self.status.running = True
        self.task.status = "FAILURE"
        self.task.save()
        self.status.time_started = timezone.make_aware(time)
        self.manager.checkTaskResult(self.status)
        self.assertFalse(self.status.last_run)
        self.assertFalse(self.status.running)


if __name__ == "__main__":
    unittest.main()
