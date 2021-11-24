import logging
from django.conf import settings
from ccxt.base import exchange, errors
from api.models import Exchange as ExchangeModel


logger = logging.getLogger("marketmanager")


def check_fiat_markets(ccxt_exchange: exchange):
    """Check if the ccxt exchange has markets that we consider fiat"""
    if hasattr(ccxt_exchange, "fetch_currencies"):
        logger.info("Exchange has fetch currencies")
        info = ccxt_exchange.fetch_currencies()
        if info:
            for fiat_symbol in settings.FIAT_SYMBOLS:
                if fiat_symbol in info:
                    return True
    if hasattr(ccxt_exchange, "fetch_markets"):
        logger.info("Exchange has fetch markets")
        info = ccxt_exchange.fetch_markets()
        for symbol in info:
            if symbol["quote"] in settings.FIAT_SYMBOLS:
                return True


def fetch_tickers(ccxt_exchange: exchange, exchange: ExchangeModel):
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
                except (errors.DDoSProtection, errors.RequestTimeout):
                    break
        elif ccxt_exchange.has.get("fetchMarkets"):
            logger.info("Exchange {} has the fetchMarkets method".format(name))
            markets = ccxt_exchange.fetchMarkets()
            for market in markets:
                # We only want USD markets if the exchange is fiat
                if market["quote"] not in settings.FIAT_SYMBOLS and exchange.fiat_markets:
                    logger.debug("Skipping {}".format(market))
                    continue
                market_name = market["symbol"]
                try:
                    logger.debug("Fetching {}".format(market_name))
                    data[market_name] = ccxt_exchange.fetchTicker(market_name)
                except (errors.DDoSProtection, errors.RequestTimeout):
                    break
                except errors.ExchangeError:
                    continue
        else:
            msg = "No symbols in exchange {}".format(ccxt_exchange.name)
            logger.warning(msg)
            return msg
    else:
        data = ccxt_exchange.fetchTickers()
    return data


def get_split_symbol(market: str):
    """Get the symbol we are going to use to split the market pair into base+quote"""
    if "/" in market:
        split_symbol = "/"
    elif "-" in market:
        split_symbol = "-"
    elif "_" in market:
        split_symbol = "_"
    else:
        raise ValueError("Couldn't determine split symbol")
    return split_symbol


def get_base_and_quote(market_info: dict):
    """Get the market base/quote from market['info']"""
    base = quote = None
    if market_info.get("quote"):
        quote = market_info['quote']
    if market_info.get("underlying"):
        # Exchange FTX doesn't add quote/base info but underlying
        quote = market_info['underlying']
        split_symbol = get_split_symbol(market_info['name'])
        start = market_info['name'].find(quote)
        if start == 0:
            # quote is in the start of the string - the rest is the base
            base = market_info['name'][len(quote) + 1:]
        else:
            base = market_info['name'][:start - 1]
        return base, quote
    for key in ["symbol", "market", "name"]:
        if key in market_info:
            split_symbol = get_split_symbol(market_info[key])
            base, quote = market_info[key].split(split_symbol)
            return base, quote
    return base, quote


def parse_market_data(data: dict, exchange_id: int):
    """Build meaningful objects from the exchange data for DB insertion"""
    update_data = {}
    for symbol, values in data.items():
        base = quote = None
        if values.get('symbol'):
            try:
                get_base_and_quote(values)
            except ValueError:
                logger.debug(f'Couldn\'t find base and quote from values symbol: {values["symbol"]}')
        if values.get('info') and (not base or not quote):
            try:
                get_base_and_quote(values['info'])
            except ValueError:
                logger.debug(f'Couldn\'t find base and quote from values info: {values["info"]}')
        if not base or not quote:
            try:
                base, quote = symbol.split(get_split_symbol(symbol))
            except ValueError:
                logger.debug(f"Couldn't find base and quote from symbol name: {symbol}")
                continue
        # Normalize the name
        name = "{}-{}".format(base, quote)
        # Set them to 0 as there might be nulls
        temp = {"last": 0, "bid": 0, "ask": 0, "high": 0, "low": 0, "open": 0, "close": 0,
                "baseVolume": 0}
        for item in temp.keys():
            if values.get(item):
                temp[item] = values[item]
        update_data[name] = {"base": base,
                             "quote": quote,
                             "last": temp["last"],
                             "bid": temp["bid"],
                             "ask": temp["ask"],
                             "high": temp["high"],
                             "low": temp["low"],
                             "open": temp["open"],
                             "close": temp["close"],
                             "volume": temp["baseVolume"],
                             "exchange_id": exchange_id
                             }
    return update_data
