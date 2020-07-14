from ccxt.base import errors
import logging


def fetch_tickers(ccxt_exchange, exchange):
    """Try to fetch the tickers data from the CCXT exchange."""
    logger = logging.getLogger("marketmanager")
    name = exchange.name
    data = {}
    if not ccxt_exchange.has.get('fetchTickers'):
        logger.info("Exchange {} does not have fetchTickers method".format(name))
        # Exchange doesn't support fetching all tickers
        if ccxt_exchange.symbols:
            logger.info("Exchange {} does have the symbols".format(name))
            data = {}
            for symbol in ccxt_exchange.symbols:
                try:
                    data[symbol] = ccxt_exchange.fetchTicker(symbol)
                except errors.ExchangeError:
                    pass
        elif ccxt_exchange.has.get("fetchMarkets"):
            logger.info("Exchange {} does have the fetchMarkets method".format(name))
            markets = ccxt_exchange.fetchMarkets()
            for market in markets:
                # We only want USD markets if the exchange is fiat
                if market["quote"] != "USD" and exchange.fiat_markets:
                    continue
                market_name = market["symbol"]
                logger.debug("Fetching {}".format(market_name))
                data[name] = ccxt_exchange.fetchTicker(market_name)
        else:
            msg = "No symbols in exchange {}".format(ccxt_exchange.name)
            logger.warning(msg)
            return msg
    else:
        data = ccxt_exchange.fetchTickers()
    return data


def parse_market_data(data, exchange_id):
    """Build meaningful objects from the exchange data"""
    update_data = {}

    for symbol, values in data.items():
        if values['symbol']:
            base, quote = values['symbol'].split("/")
        elif "symbol" in values['info']:
            base, quote = values['info']['symbol'].split("_")
        else:
            base, quote = symbol.split("/")
        name = "{}-{}".format(base, quote)
        # Set them to 0 as there might be nulls
        temp = {"last": 0, "bid": 0, "ask": 0, "baseVolume": 0}
        for item in temp.keys():
            if values[item]:
                temp[item] = values[item]
        update_data[name] = {"base": base,
                             "quote": quote,
                             "last": temp["last"],
                             "bid": temp["bid"],
                             "ask": temp["ask"],
                             "volume": temp["baseVolume"],
                             "exchange_id": exchange_id
                             }
    return update_data
