import unittest
from api import utils


class TestParseMarket(unittest.TestCase):

    def setUp(self):
        self.symbol = "ETH/BTC"
        self.symbol_data = {
            "base": "ETH",
            "quote": "BTC",
            "last": 0.09,
            "ask": 0.095,
            "bid": 0.085,
        }
        self.data = {self.symbol: self.symbol_data}
        self.exchange_id = 1

    def testSimple(self):
        parsed_data = utils.parse_market_data(self.data, self.exchange_id)
        self.assertEqual(len(parsed_data), 1)
        for symbol, data in parsed_data.items():
            for key, value in self.symbol_data.items():
                self.assertEqual(value, data[key])

    def testSymbolOnly(self):
        """If we have a symbol and empty data - assert we don't throw it out """
        parsed_data = utils.parse_market_data({self.symbol: {}}, self.exchange_id)
        self.assertTrue(parsed_data)
        self.assertTrue(self.symbol.replace("/", "-") in parsed_data)


class TestGetBaseAndQuote(unittest.TestCase):
    def test_underlying_start(self):
        """Test when the market info has underlying quote key in the start of the market name"""
        data = {'name': 'THETA-PERP', 'underlying': 'THETA'}
        base, quote = utils.get_base_and_quote(data)
        assert base == "PERP"
        assert quote == "THETA"

    def test_underlying_end(self):
        """Test when the market info has underlying quote key in the end of the market name"""
        data = {'name': 'PERP-THETA', 'underlying': 'THETA'}
        base, quote = utils.get_base_and_quote(data)
        assert base == "PERP"
        assert quote == "THETA"

    def test_symbol_market_name(self):
        """Test with a market/name/symbol key in the dict"""
        base = 'ETH'
        quote = 'BTC'
        # Test with all the symbols in between
        for key in ["symbol", "market", "name"]:
            for i in "-/_":
                data = {key: f'{base}{i}{quote}'}
                base, quote = utils.get_base_and_quote(data)
                assert base == base
                assert quote == quote
