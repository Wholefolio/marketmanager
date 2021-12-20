import ccxt
import logging
from django.utils import timezone
from django.conf import settings

from api.models import Exchange, ExchangeStatus, FiatMarketModel

logger = logging.getLogger("marketmanager")


def get_exchange_details(name):
    """Create the data dict with the exchange name, api url and www url."""
    try:
        exchange_object = getattr(ccxt, name.lower())()
    except AttributeError:
        msg = {"error": "Not existing exchange"}
        return msg
    if isinstance(exchange_object.urls['api'], dict):
        if "public" in exchange_object.urls['api']:
            api_url = exchange_object.urls['api']['public']
        elif "rest" in exchange_object.urls['api']:
            api_url = exchange_object.urls['api']['rest']
        elif "current" in exchange_object.urls['api']:
            api_url = exchange_object.urls['api']['current']
        else:
            api_url = None
    else:
        api_url = exchange_object.urls['api']
    url = exchange_object.urls['www']
    logo = exchange_object.urls['logo']
    return {"api_url": api_url, "url": url, "logo": logo}


def set_running_status(exchange: Exchange, running: bool):
    """Set the exchange status running status.
    This function assumes the ExchangeStatus exists, otherwise it will raise the DoesNotExist exception.
    """
    logger.info(f"Updating ExchangeStatus for {exchange.id}")
    try:
        status = ExchangeStatus.objects.get(exchange=exchange)
    except ExchangeStatus.DoesNotExist:
        status = ExchangeStatus(exchange=exchange)
        status.save()
    status.running = running
    status.time_started = timezone.now()
    status.save()


def prepare_fiat_data(data, limit_to_exchange=False):
    """Prepare the market pairs for fiat insertion.
    We must map out all quotes and bases so they have a corresponding value in fiat prior to insertion.
    If limit_to_exchange is True then filter fiat rates only from current exchange if any
    """
    tags_for_fetch = []
    initial_quote_map = {}
    base_map = {}
    for symbol, values in data.items():
        base = values["base"]
        quote = values["quote"]
        last = values["last"]
        if last == 0:
            continue
        if base not in initial_quote_map and quote in settings.FIAT_SYMBOLS:
            initial_quote_map[base] = last
        elif quote in initial_quote_map and base not in initial_quote_map:
            initial_quote_map[base] = last * initial_quote_map[quote]
        else:
            if quote not in tags_for_fetch and quote not in settings.FIAT_SYMBOLS:
                tags_for_fetch.append(quote)
            if base not in base_map:
                base_map[base] = data[symbol]
    if tags_for_fetch:
        tags = {"currency": tags_for_fetch}
        if limit_to_exchange:
            tags = {"exchange_id": data[symbol]["exchange_id"]}
        results = FiatMarketModel(data=tags).filter("10m")
        quote_map = {x["currency"]: x["price"] for x in results}
    else:
        quote_map = {}
    quote_map = {**quote_map, **initial_quote_map}
    for symbol, values in data.items():
        if values["base"] in quote_map:
            continue
        if values["quote"] in settings.FIAT_SYMBOLS and values["last"] > 0:
            quote_map[base] = values["last"]
        elif values["quote"] not in quote_map:
            logger.warning(f"Couldn't find quote {values['quote']} for base {base}")
        else:
            quote_map[base] = quote_map[values["quote"]] * values["last"]
    return quote_map
