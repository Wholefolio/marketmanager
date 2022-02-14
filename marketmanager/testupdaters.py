import unittest
from unittest.mock import patch
from django.conf import settings
from influxdb_client import InfluxDBClient

from marketmanager.updaters import ExchangeUpdater, InfluxUpdater, FiatMarketModel, PairsMarketModel
from api.models import Market, Exchange, CurrencyFiatPrices
from marketmanager import utils

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
        self.last = 15
        self.data = {"ICX-BNB": {'base': 'BNB', 'quote': 'ICX', 'last': self.last,
                                 'bid': 0, 'ask': 0, 'volume': 50,
                                 'exchange_id': self.exchange.id}}
        self.updater = ExchangeUpdater(self.exchange.id, self.data)

    def tearDown(self):
        self.exchange.delete()

    @classmethod
    def tearDownClass(cls):
        Market.objects.all().delete()

    def testInit(self):
        """Test that the Updater class was created."""
        self.assertIsInstance(self.updater, ExchangeUpdater)

    def test_create_map(self):
        """Test the creation of a data map using some values."""
        result = self.updater.create_map(CURRENCY_DATA, "symbol", "price")
        for i in CURRENCY_DATA:
            self.assertTrue(i["symbol"] in result)
            self.assertEqual(i["price"], result[i["symbol"]])

    def test_create_markets(self):
        """Test the creation of new markets."""
        self.updater.create_markets()
        market = Market.objects.all()
        self.assertEqual(len(market), 1)
        self.assertEqual(market[0].name, "ICX-BNB")

    def testupdate_existing_markets(self):
        """Test the update of existing data."""
        market = Market(name="ICX-BNB", **self.data["ICX-BNB"])
        market.save()
        volume = 1000
        last = 15
        new_data = {"ICX-BNB": {'base': 'BNB', 'quote': 'ICX', 'last': last,
                                'bid': 0, 'ask': 0, 'volume': volume,
                                'exchange_id': self.exchange.id}}
        updater = ExchangeUpdater(self.exchange.id, new_data)
        updater.update_existing_markets()
        after_update = Market.objects.all()
        self.assertEqual(len(after_update), 1)
        self.assertEqual(after_update[0].last, last)
        self.assertEqual(after_update[0].volume, volume)

    def testUpdateExchange(self):
        """Test the updateExchange method."""
        self.updater.updateExchange()
        exchange = Exchange.objects.get(name="Test")
        self.assertTrue(exchange.last_data_fetch)

    # Mock testing
    @patch("marketmanager.updaters.ExchangeUpdater.get_base_prices")
    def testRun(self, mock_result):
        """Test the main run method."""
        data_map = {"ICX": 6, "BNB": 10}
        mock_result.return_value = data_map
        self.updater.run()
        markets = Market.objects.all()
        # Check if the market has been created
        self.assertEqual(len(markets), 1)
        # Check if the exchange has been updated
        self.assertTrue(Exchange.objects.get(name=self.exchange.name).last_data_fetch)

    @patch("marketmanager.updaters.ExchangeUpdater.get_base_prices")
    def testsummarize_data(self, mock_result):
        data_map = {"ICX": 6, "BNB": 10}
        mock_result.return_value = data_map
        self.updater.summarize_data()
        base = self.data["ICX-BNB"]["base"]
        exchange_volume = self.data["ICX-BNB"]["volume"] * data_map[base]
        exchange = Exchange.objects.get(name="Test")
        self.assertEqual(exchange.volume, exchange_volume)
        self.assertEqual(exchange.top_pair, "ICX-BNB")

    @patch("marketmanager.updaters.ExchangeUpdater.get_base_prices")
    def testsummarize_data_NoBasePrices(self, mock_result):
        """There shouldn't be any summaries if there are no base results"""
        mock_result.return_value = {}
        self.updater.summarize_data()
        exchange = Exchange.objects.get(name="Test")
        self.assertFalse(exchange.volume)
        self.assertFalse(exchange.top_pair)

    @patch("marketmanager.updaters.appRequest")
    def testget_base_prices_WithCurrencies(self, mock_result):
        mock_result.return_value = get_json()
        output = self.updater.get_base_prices()
        for item in CURRENCY_DATA:
            self.assertTrue(item["symbol"] in output)

    @patch("marketmanager.updaters.appRequest")
    def testget_base_prices_WithoutCurrencies_WithoutLocal(self, mock_result):
        """Test the method without an existing local fiat market."""
        mock_result.return_value = APP_REQUEST_ERROR
        output = self.updater.get_base_prices()
        self.assertFalse(output)

    @patch("marketmanager.updaters.appRequest")
    def testget_base_prices_WithoutCurrencies_WithLocal(self, mock_result):
        """Test the method with an existing local fiat market."""
        data = {'quote': 'USD', 'base': 'BNB', 'last': 10, 'bid': 9, 'ask': 10,
                'volume': 50, 'exchange_id': self.exchange.id}
        m = Market(name="BNB-USD", **data)
        m.save()
        mock_result.return_value = APP_REQUEST_ERROR
        output = self.updater.get_base_prices()
        self.assertTrue(data["base"] in output)

    def test_update_fiat_prices_no_data(self):
        """Test updating without any fiat data"""
        self.updater.update_fiat_prices()

    def test_update_fiat_prices_new_prices(self):
        """Test creating new entries"""
        currency = "BTC"
        fiat_data = {currency: 50000}
        self.updater.fiat_data = fiat_data
        self.updater.update_fiat_prices()
        obj = CurrencyFiatPrices.objects.get(currency=currency, exchange=self.exchange.id)
        self.assertEqual(obj.price, fiat_data[currency])

    def test_update_fiat_prices_existing_prices(self):
        """Test updating existing entries"""
        currency = "BTC"
        obj = CurrencyFiatPrices(currency=currency, exchange=self.exchange, price=10000)
        obj.save()
        fiat_data = {currency: 50000}
        self.updater.fiat_data = fiat_data
        self.updater.update_fiat_prices()
        obj.refresh_from_db()
        self.assertEqual(obj.price, fiat_data[currency])


class TestInfluxUpdater(unittest.TestCase):
    """Test the InfluxUpdater and its methods."""

    def setUp(self):
        self.exchange = Exchange(name="Test1", interval=300)
        self.exchange.save()
        self.quote = "ICX"
        self.base = "BNBTEST"
        self.pair = f"{self.quote}-{self.base}"
        self.fiatpair = f"{self.base}-USD"
        self.pair_measurement = "tests-pair-mm"
        self.fiat_measurement = "tests-fiat-mm"
        self.data = {self.pair: {'base': self.base, 'quote': self.quote, 'last': 15.0, 'bid': 0, 'ask': 0,
                                 'volume': 50, 'open': 1, 'close': 1, 'high': 1, 'low': 1,
                                 'exchange_id': str(self.exchange.id)}}
        self.fiat_data = {self.fiatpair: {
            'base': 'BNBTEST', 'quote': 'USD', 'last': 150.0,
            'bid': 0, 'ask': 0, 'volume': 50,
            'exchange_id': self.exchange.id
        }}
        self.bucket = "test-influxdb-bucket"
        PairsMarketModel.measurement = self.pair_measurement
        PairsMarketModel.bucket = self.bucket
        FiatMarketModel.measurement = self.fiat_measurement
        FiatMarketModel.bucket = self.bucket
        self.updater = InfluxUpdater(self.exchange.id, self.data, self.fiat_data)
        self.influx_client = InfluxDBClient(url=settings.INFLUXDB_URL, token=settings.INFLUXDB_TOKEN)
        self.buckets_api = self.influx_client.buckets_api()
        self.org = self._get_org()
        self.buckets_api.create_bucket(bucket_name=self.bucket, org_id=self.org.id)
        self.query_api = self.influx_client.query_api()

    def tearDown(self):
        self.exchange.delete()
        # Delete the data from influx
        bucket_id = self.buckets_api.find_bucket_by_name(self.bucket).id
        self.buckets_api.delete_bucket(bucket_id)

    def _get_org(self):
        org_api = self.influx_client.organizations_api()
        orgs = org_api.find_organizations()
        for o in orgs:
            if o.name == settings.INFLUXDB_ORG:
                return o

    def testInit(self):
        """Test that the Updater class was created."""
        self.assertIsInstance(self.updater, InfluxUpdater)

    def test_write_pairs(self):
        """Test inserting pair timeseries into Influx"""
        self.updater._write_pairs()
        query = f"from(bucket: \"{self.bucket}\") |> range(start: -1m)"
        query += f' |> filter(fn: (r) => (r._measurement == "{self.pair_measurement}"))'
        query += f' |> filter(fn: (r) => (r.quote == "{self.quote}"))'
        query += f' |> filter(fn: (r) => (r.base == "{self.base}"))'
        query += ' |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")'
        tables = self.query_api.query(query, org=settings.INFLUXDB_ORG)
        self.assertEqual(len(tables), 1)
        for i in tables:
            self.assertEqual(len(i.records), 1)
            record = i.records[0]
            for key in self.data[self.pair]:
                self.assertEqual(record[key], self.data[self.pair][key])

    def test_write_fiat(self):
        """Test inserting fiat timeseries into Influx"""
        FiatMarketModel.measurement = self.fiat_measurement
        fiat_data = utils.prepare_fiat_data(self.fiat_data)
        updater = InfluxUpdater(self.exchange.id, self.data, fiat_data)
        updater._write_fiat()
        query = f"from(bucket: \"{self.bucket}\") |> range(start: -1m)"
        query += f' |> filter(fn: (r) => (r._measurement == "{self.fiat_measurement}"))'
        query += f' |> filter(fn: (r) => (r.currency == "{self.base}"))'
        tables = self.query_api.query(query, org=settings.INFLUXDB_ORG)
        self.assertEqual(len(tables), 1)
        for i in tables:
            self.assertEqual(len(i.records), 1)
            record = i.records[0]
            self.assertEqual(record["_value"], self.fiat_data[self.fiatpair]["last"])
