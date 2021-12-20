
import unittest
from marketmanager import utils


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.quote = "ICX"
        self.base = "BNBTEST"
        self.pair = f"{self.quote}-{self.base}"
        self.fiatpair = f"{self.base}-USD"
        self.fiat_measurement = "tests-fiat-mm"
        self.fiat_data = {self.fiatpair: {
            'base': 'BNBTEST', 'quote': 'USD', 'last': 150.0,
            'bid': 0, 'ask': 0, 'volume': 50,
            'exchange_id': 1
        }}

    def test_prepare_fiat_data_no_data(self):
        """Test when there are no fiat pairs in InfluxDB and in the data"""
        fiat_data = utils.prepare_fiat_data({})
        self.assertFalse(fiat_data)

    def test_prepare_fiat_data_with_data(self):
        """Test when there is a fiat pair in the data"""
        base = "SOL"
        symbol = f"{base}-{self.base}"
        self.fiat_data[symbol] = {
            'base': 'SOL', 'quote': 'BNBTEST', 'last': 0.015,
            'bid': 0, 'ask': 0, 'volume': 140,
            'exchange_id': 1
        }
        fiat_data = utils.prepare_fiat_data(self.fiat_data)
        self.assertEqual(len(fiat_data), 2)
        # Assert the calculations are correct
        self.assertEqual(fiat_data[self.base], self.fiat_data[self.fiatpair]['last'])
        price = self.fiat_data[self.fiatpair]['last'] * self.fiat_data[symbol]["last"]
        self.assertEqual(price, fiat_data[base])

    def test_prepare_fiat_data_not_valid_last(self):
        """Test when there are the last trade value is 0"""
        self.fiat_data[self.fiatpair]['last'] = 0
        fiat_data = utils.prepare_fiat_data(self.fiat_data)
        self.assertEqual(len(fiat_data), 0)
