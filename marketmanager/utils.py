import ccxt
import logging
from django.utils import timezone
from api.models import Exchange, ExchangeStatus

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
