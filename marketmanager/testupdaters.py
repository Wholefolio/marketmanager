import unittest
from unittest.mock import patch
from django.conf import settings
from django.utils import timezone
from influxdb_client import InfluxDBClient

from marketmanager.updaters import ExchangeUpdater, InfluxUpdater
from api.models import Market, Exchange


CURRENCY_DATA = [{"name": "Bitcoin", "symbol": "BTC", "price": 6500},
                 {"name": "Ethereum", "symbol": "ETH", "price": 350}]
APP_REQUEST_ERROR = {"error": "Couldn't reach app"}


def get_json():
    return {"count": 2, "results": CURRENCY_DATA}


class TestExchangeUpdater(unittest.TestCase):
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
        self.updater.updateExchange()
        exchange = Exchange.objects.get(name="Test")
        self.assertTrue(exchange.last_updated)

    # Mock testing
    @patch("marketmanager.updaters.ExchangeUpdater.getBasePrices")
    def testRun(self, mock_result):
        """Test the main run method."""
        data_map = {"ICX": 6, "BNB": 10}
        mock_result.return_value = data_map
        result = self.updater.run()
        # We receieve a success string on finish
        self.assertTrue(isinstance(result, str))
        markets = Market.objects.all()
        # Check if the market has been created
        self.assertEqual(len(markets), 1)
        # Check if the exchange has been updated
        self.assertTrue(Exchange.objects.all()[0].last_updated)

    @patch("marketmanager.updaters.ExchangeUpdater.getBasePrices")
    def testSummarizeData(self, mock_result):
        data_map = {"ICX": 6, "BNB": 10}
        mock_result.return_value = data_map
        self.updater.summarizeData()
        quote = self.data["ICX-BNB"]["base"]
        exchange_volume = self.data["ICX-BNB"]["volume"] * data_map[quote]
        exchange = Exchange.objects.get(name="Test")
        self.assertEqual(exchange.volume, exchange_volume)
        self.assertEqual(exchange.top_pair, "ICX-BNB")

    @patch("marketmanager.updaters.ExchangeUpdater.getBasePrices")
    def testSummarizeData_NoBasePrices(self, mock_result):
        """There shouldn't be any summaries if there are no base results"""
        mock_result.return_value = {}
        self.updater.summarizeData()
        exchange = Exchange.objects.get(name="Test")
        self.assertFalse(exchange.volume, 0)
        self.assertFalse(exchange.top_pair)

    @patch("marketmanager.updaters.appRequest")
    def testGetBasePrices_WithCurrencies(self, mock_result):
        mock_result.return_value = get_json()
        output = self.updater.getBasePrices()
        for item in CURRENCY_DATA:
            self.assertTrue(item["symbol"] in output)

    @patch("marketmanager.updaters.appRequest")
    def testGetBasePrices_WithoutCurrencies_WithoutLocal(self, mock_result):
        """Test the method without an existing local fiat market."""
        mock_result.return_value = APP_REQUEST_ERROR
        output = self.updater.getBasePrices()
        self.assertFalse(output)

    @patch("marketmanager.updaters.appRequest")
    def testGetBasePrices_WithoutCurrencies_WithLocal(self, mock_result):
        """Test the method with an existing local fiat market."""
        data = {'base': 'USD', 'quote': 'BNB', 'last': 10, 'bid': 9, 'ask': 10,
                'volume': 50, 'exchange_id': self.exchange.id}
        m = Market(name="BNB-USD", **data)
        m.save()
        mock_result.return_value = APP_REQUEST_ERROR
        output = self.updater.getBasePrices()
        self.assertTrue(data["quote"] in output)
        self.assertEqual(data["last"], output[data['quote']])


class TestInfluxUpdater(unittest.TestCase):
    """Test the InfluxUpdater and its methods."""

    def setUp(self):
        self.exchange = Exchange(name="Test1", interval=300)
        self.exchange.save()
        self.quote = "ICX"
        self.base = "BNB"
        self.pair = f"{self.quote}-{self.base}"
        self.fiatpair = f"{self.base}-USD"
        self.pair_measurement = "test-pair-mm"
        self.fiat_measurement = "test-fiat-mm"
        self.data = {self.pair: {'base': 'BNB', 'quote': 'ICX', 'last': 15,
                                 'bid': 0, 'ask': 0, 'volume': 50,
                                 'exchange_id': self.exchange.id}}
        self.fiat_data = {"BNB-USD": {
            'base': 'BNB', 'quote': 'USD', 'last': 150,
            'bid': 0, 'ask': 0, 'volume': 50,
            'exchange_id': self.exchange.id
        }}
        self.updater = InfluxUpdater(self.exchange.id, self.data)
        self.influx_client = InfluxDBClient(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN)
        self.query_api = self.influx_client.query_api()

    def tearDown(self):
        self.exchange.delete()
        delete_api = self.influx_client.delete_api()
        # Delete the data from influx
        for i in [self.pair_measurement, self.fiat_measurement]:
            delete_api.delete(
                start=timezone.now()-timezone.timedelta(hours=1),
                stop=timezone.now(),
                predicate=f"_measurement=\"{i}\"",
                bucket=settings.INFLUXDB_DEFAULT_BUCKET,
                org=settings.INFLUXDB_ORG)

    def testInit(self):
        """Test that the Updater class was created."""
        self.assertIsInstance(self.updater, InfluxUpdater)

    def testTransformInsertPairs(self):
        """Test inserting timeseries into Influx"""
        self.updater._transformInsertPairs(self.pair_measurement)
        query = f"from(bucket: \"{settings.INFLUXDB_DEFAULT_BUCKET}\") |> range(start: -1m)"
        query += f' |> filter(fn: (r) => (r._measurement == "{self.pair_measurement}"))'
        query += f' |> filter(fn: (r) => (r.quote == "{self.quote}"))'
        query += f' |> filter(fn: (r) => (r.base == "{self.base}"))'
        tables = self.query_api.query(query, org=settings.INFLUXDB_ORG)
        self.assertEqual(len(tables), 1)
        for i in tables:
            self.assertEqual(len(i.records), 1)
            record = i.records[0]
            self.assertEqual(record["_value"], self.data[self.pair]["last"])

    def testTransformInsertFiat(self):
        """Test inserting timeseries into Influx"""
        updater = InfluxUpdater(self.exchange, self.fiat_data)
        updater._transformInsertFiat(self.fiat_measurement)
        query = f"from(bucket: \"{settings.INFLUXDB_DEFAULT_BUCKET}\") |> range(start: -1m)"
        query += f' |> filter(fn: (r) => (r._measurement == "{self.fiat_measurement}"))'
        query += f' |> filter(fn: (r) => (r.symbol == "{self.base}"))'
        tables = self.query_api.query(query, org=settings.INFLUXDB_ORG)
        self.assertEqual(len(tables), 1)
        for i in tables:
            self.assertEqual(len(i.records), 1)
            record = i.records[0]
            self.assertEqual(record["_value"], self.fiat_data[self.fiatpair]["last"])