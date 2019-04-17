import ccxt
import logging
from django.db.utils import OperationalError
from django_celery_results.models import TaskResult
from django.db import transaction
from django.utils import timezone

from marketmanager.updater import ExchangeUpdater
from marketmanager.celery import app
from api.models import Exchange, ExchangeStatus
from api import utils


@app.task(bind=True)
def fetch_exchange_data(self, exchange_id):
    """Task to fetch and update exchange data via ccxt."""
    logger = logging.getLogger("marketmanager-celery")
    extra = {"task_id": self.request.id, "exchange": None}
    logger = logging.LoggerAdapter(logger, extra)
    try:
        exchange = Exchange.objects.get(id=exchange_id)
        logger.info("Got exchange {}".format(exchange))
        extra['exchange'] = exchange
        logger = logging.LoggerAdapter(logger, extra)
    except OperationalError as e:
        msg = "DB operational error. Error: {}".format(e)
        logger.error(msg)
        return msg
    if exchange.name.lower() not in ccxt.exchanges:
        msg = "Exchange doesn't exist"
        logger.error(msg)
        return
    # Init the exchange from the ccxt module
    ccxt_exchange = getattr(ccxt, exchange.name.lower())()
    # Get the data
    logger.info("Fetching tickers.")
    data = utils.fetch_tickers(ccxt_exchange)
    # Parse the data
    logger.info("Parsing the data.")
    update_data = utils.parse_market_data(data, exchange_id)
    # Create/update the data
    logger.info("Starting updater.")
    updater = ExchangeUpdater(exchange_id, update_data, self.request.id)
    result = updater.run()
    logger.info("Finished updater, updating ExchangeStatus.")
    status = ExchangeStatus.objects.get(exchange=exchange)
    status.running = False
    status.last_run = timezone.now()
    status.save()
    return result


@app.task
def clear_task_results():
    """Aggregate and clear all task results from the DB."""
    tasks = TaskResult.objects.all()
    with transaction.atomic():
        for task in tasks:
            task.delete()
    return "Clearing success"
