import ccxt
import logging
from django.db.utils import OperationalError
from django_celery_results.models import TaskResult
from django.db import transaction

from marketmanager.updater import ExchangeUpdater
from marketmanager.celery import app
from api.models import Exchange
from api import utils


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
    # Get the data
    data = utils.fetch_tickers(ccxt_exchange)
    # Parse the data
    update_data = utils.parse_market_data(data, exchange_id)
    # Create/update the data
    updater = ExchangeUpdater(exchange_id, update_data)
    return updater.run()


@app.task
def clear_task_results():
    """Aggregate and clear all task results from the DB."""
    tasks = TaskResult.objects.all()
    with transaction.atomic():
        for task in tasks:
            task.delete()
    return "Clearing success"
