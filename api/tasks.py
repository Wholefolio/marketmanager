import ccxt
import logging
import traceback
from copy import deepcopy
from django.db.utils import OperationalError
from django_celery_results.models import TaskResult
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from celery import Task
from django_influxdb.models import InfluxTasks
from django_influxdb.tasks import EveryTask

from marketmanager.updaters import ExchangeUpdater, InfluxUpdater
from marketmanager.celery import app
from api.models import Exchange, Market
from api import utils
from marketmanager.utils import set_running_status


class LogErrorsTask(Task):
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        logger = logging.getLogger("marketmanager-celery")
        extra = {"task_id": self.request.id, "exchange": None}
        logger = logging.LoggerAdapter(logger, extra)
        logger.exception('Celery task failure!!!{}{}'.format(args, kwargs), exc_info=exc)
        super(LogErrorsTask, self).on_failure(exc, task_id, args, kwargs, einfo)


@app.task(bind=True, base=LogErrorsTask)
def fetch_exchange_data(self, exchange_id: int):
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
        msg = "Exchange doesn't exist in CCXT."
        logger.error(msg)
        raise ValueError(msg)
    set_running_status(exchange, running=True)
    # Init the exchange from the ccxt module
    ccxt_exchange = getattr(ccxt, exchange.name.lower())()
    # Check if the exchange has new fiat markets and is not flagged
    if not exchange.fiat_markets:
        if utils.check_fiat_markets(ccxt_exchange):
            exchange.fiat_markets = True
            exchange.save()
    # Get the data
    logger.info("Fetching tickers.")
    data = utils.fetch_tickers(ccxt_exchange, exchange)
    logger.debug("Raw data: {}".format(data))
    # Parse the data
    logger.info("Parsing the data.")
    update_data = utils.parse_market_data(data, exchange_id)
    # Create/update the data
    logger.info("Starting updaters.")
    fiat_data = result = None
    try:
        influx_data = deepcopy(update_data)
        influx_updater = InfluxUpdater(exchange_id, influx_data, self.request.id)
        fiat_data = influx_updater.write()
    except Exception as e:
        traceback.print_exc()
        logger.critical("Influx updater failed. Exception: {}".format(e))
    try:
        updater = ExchangeUpdater(exchange_id, update_data, self.request.id)
        result = updater.run(fiat_data)
    except Exception as e:
        traceback.print_exc()
        logger.critical("DB updater failed. Exception: {}".format(e))
    set_running_status(exchange, running=False)
    return result


@app.task
def clear_task_results():
    """Aggregate and clear all task results from the DB."""
    tasks = TaskResult.objects.all()
    with transaction.atomic():
        for task in tasks:
            task.delete()
    return "Clearing success"


@app.task
def clear_stale_markets():
    """ Clear markets that haven't been updated in the configured period"""
    d = timezone.now() - timezone.delta(days=settings.MARKET_STALE_DAYS)
    markets = Market.objects.filter(updated__lte=d)
    markets.delete()
    return "Cleared {} stale markets".format(len(markets))


@app.task
def sync_influx_tasks():
    """Get or create existing InfluxDB tasks from the DB"""
    for task in InfluxTasks.objects.all():
        influx_task = EveryTask(name=task.name)
        if influx_task._get_influx_task():
            influx_task.create_from_db()
