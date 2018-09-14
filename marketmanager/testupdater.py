import unittest

from marketmanager.updater import ExchangeUpdater
from api.models import Market, Exchange


class TestUpdater(unittest.TestCase):
    """Test the MarketManager class and methods."""

    def setUp(self):
        self.exchange = Exchange(name="Test", interval=300)
        self.exchange.save()
        self.data = {"ICX-BNB": {'base': 'BNB', 'quote': 'ICX', 'last': 0,
                                 'bid': 0, 'ask': 0, 'volume': 0,
                                 'exchange_id': self.exchange.id}}
        self.updater = ExchangeUpdater(self.exchange.id, self.data)

    def tearDown(self):
        self.exchange.delete()

    def testInit(self):
        """Test that the Updater class was created."""
        self.assertIsInstance(self.updater, ExchangeUpdater)

    def testCreateMarkets(self):
        """Test the creation of new markets."""
        self.updater.createMarkets()
        market = Market.objects.all()
        self.assertEqual(len(market), 1)
        self.assertEqual(market[0].name, "ICX-BNB")

    def testUpdateExistingMarkets(self):
        """Test the update of existing data."""
        market = Market(name="ICX-BNB", **self.data["ICX-BNB"])
        market.save()
        volume = 1000
        last = 15
        new_data = {"ICX-BNB": {'base': 'BNB', 'quote': 'ICX', 'last': last,
                                'bid': 0, 'ask': 0, 'volume': volume,
                                'exchange_id': self.exchange.id}}
        existing_data = Market.objects.all()
        updater = ExchangeUpdater(self.exchange.id, new_data)
        updater.updateExistingMarkets(existing_data)
        after_update = Market.objects.all()
        self.assertEqual(len(existing_data), 1)
        self.assertEqual(after_update[0].last, last)
        self.assertEqual(after_update[0].volume, volume)

    def testUpdateExchange(self):
        """Test the updateExchange method."""
        self.updater.updateExchange(self.exchange)
        self.assertTrue(self.exchange.last_updated)

    def testRun(self):
        """Test the main run method."""
        result = self.updater.run()
        # We receieve a success string on finish
        self.assertTrue(isinstance(result, str))
        markets = Market.objects.all()
        # Check if the market has been created
        self.assertEqual(len(markets), 1)
        # Check if the exchange has been updated
        self.assertTrue(Exchange.objects.all()[0].last_updated)
