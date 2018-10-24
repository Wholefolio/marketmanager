import ccxt
import logging
from django.db.utils import OperationalError

from marketmanager.updater import ExchangeUpdater
from marketmanager.celery import app
from api.models import Exchange


@app.task
def fetch_exchange_data(exchange_id):
    """Task to fetch and update exchange data via ccxt."""
    logger = logging.getLogger(__name__)
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        logger.info("Got exchange {}".format(exchange))
    except OperationalError as e:
        msg = "DB operational error. Error: {}".format(e)
        logger.error(msg)
        return msg
    if exchange.name.lower() not in ccxt.exchanges:
        return "Exchange doesn't exist"
    # Init the exchange from the ccxt module
    ccxt_exchange = getattr(ccxt, exchange.name.lower())()
    if not ccxt_exchange.has.get('fetchTickers'):
        # Exchange doesn't support fetching all tickers
        if ccxt_exchange.symbols:
            data = {}
            for symbol in ccxt_exchange.symbols:
                data[symbol] = ccxt_exchange.fetchTicker(symbol)
        else:
            return "No symbols listed in exchange {}".format(exchange.name)
    else:
        data = ccxt_exchange.fetchTickers()
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
    updater = ExchangeUpdater(exchange_id, update_data)
    return updater.run()
