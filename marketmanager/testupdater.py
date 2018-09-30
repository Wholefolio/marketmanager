import unittest
from unittest.mock import patch

from marketmanager.updater import ExchangeUpdater
from api.models import Market, Exchange


CURRENCY_DATA = [{"name": "Bitcoin", "symbol": "BTC", "price": 6500},
                 {"name": "Ethereum", "symbol": "ETH", "price": 350}]


def get_json():
    return {"count": 2, "results": CURRENCY_DATA}


class TestUpdater(unittest.TestCase):
    """Test the MarketManager class and methods."""

    def setUp(self):
        self.exchange = Exchange(name="Test", interval=300)
        self.exchange.save()
        self.data = {"ICX-BNB": {'base': 'BNB', 'quote': 'ICX', 'last': 15,
                                 'bid': 0, 'ask': 0, 'volume': 50,
                                 'exchange_id': self.exchange.id}}
        self.updater = ExchangeUpdater(self.exchange.id, self.data)

    def tearDown(self):
        self.exchange.delete()

    def testInit(self):
        """Test that the Updater class was created."""
        self.assertIsInstance(self.updater, ExchangeUpdater)

    def test_createCurrencyMap(self):
        """Test the creation of a data map using some values."""
        result = self.updater.createCurrencyMap(CURRENCY_DATA)
        for i in CURRENCY_DATA:
            self.assertTrue(i["symbol"] in result)
            self.assertEqual(i["price"], result[i["symbol"]])

    def test_createMarkets(self):
        """Test the creation of new markets."""
        self.updater.createMarkets()
        market = Market.objects.all()
        self.assertEqual(len(market), 1)
        self.assertEqual(market[0].name, "ICX-BNB")

    def testupdateExistingMarkets(self):
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

    # Mock testing
    @patch("marketmanager.updater.ExchangeUpdater.getBasePrices")
    def testSummarizeData(self, mock_result):
        data_map = {"ICX": 6, "BNB": 10}
        mock_result.return_value = data_map
        self.updater.summarizeData(self.exchange)
        quote = self.data["ICX-BNB"]["base"]
        exchange_volume = self.data["ICX-BNB"]["volume"] * data_map[quote]
        self.assertEqual(self.exchange.volume, exchange_volume)
        self.assertEqual(self.exchange.top_pair, "ICX-BNB")

    @patch("marketmanager.updater.ExchangeUpdater.getBasePrices")
    def testSummarizeData_NoBasePrices(self, mock_result):
        mock_result.return_value = {}
        self.updater.summarizeData(self.exchange)
        self.assertEqual(self.exchange.volume, 0)
        self.assertEqual(self.exchange.top_pair, "ICX-BNB")

    @patch("marketmanager.updater.requests.get")
    def testGetBasePrices_WithCurrencies(self, mock_result):
        mock_result.return_value.status_code = 200
        mock_result.return_value.json = get_json
        output = self.updater.getBasePrices()
        for item in CURRENCY_DATA:
            self.assertTrue(item["symbol"] in output)

    @patch("marketmanager.updater.requests.get")
    def testGetBasePrices_WithoutCurrencies_WithoutLocal(self, mock_result):
        """Test the method without an existing local fiat market."""
        mock_result.return_value.status_code = 400
        output = self.updater.getBasePrices()
        self.assertFalse(output)

    @patch("marketmanager.updater.requests.get")
    def testGetBasePrices_WithoutCurrencies_WithLocal(self, mock_result):
        """Test the method with an existing local fiat market."""
        data = {'base': 'USD', 'quote': 'BNB', 'last': 10, 'bid': 9, 'ask': 10,
                'volume': 50, 'exchange_id': self.exchange.id}
        m = Market(name="BNB-USD", **data)
        m.save()
        mock_result.return_value.status_code = 400
        output = self.updater.getBasePrices()
        self.assertTrue(data["quote"] in output)
        self.assertEqual(data["last"], output[data['quote']])
