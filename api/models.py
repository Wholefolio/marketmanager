"""API models."""
from django.db import models
from django.conf import settings
from django_influxdb.models import InfluxModel


class Exchange(models.Model):
    """Exchange model - summary and info on different crypto exchanges."""
    name = models.CharField(max_length=64, unique=True)
    logo = models.CharField(max_length=256, null=True)
    url = models.URLField(max_length=128, null=True)
    api_url = models.URLField(max_length=128, null=True)
    volume = models.FloatField(null=True)
    top_pair = models.CharField(max_length=20, null=True)
    top_pair_volume = models.FloatField(null=True)

    fiat_markets = models.BooleanField(default=False, blank=True)
    last_data_fetch = models.DateTimeField(null=True)
    enabled = models.BooleanField(default=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    interval = models.IntegerField()

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{} (Interval: {}, Enabled: {})".format(self.name,
                                                       self.interval,
                                                       self.enabled)

    class Meta():
        """Define the db table name."""
        db_table = "exchanges"


class Market(models.Model):
    """A market is a place to trade 2 coins within each exchange."""
    name = models.CharField(max_length=48)
    base = models.CharField(max_length=32)
    quote = models.CharField(max_length=32)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    volume = models.FloatField(null=True)
    last = models.FloatField()
    bid = models.FloatField()
    ask = models.FloatField()
    open = models.FloatField(default=0)
    close = models.FloatField(default=0)
    high = models.FloatField(default=0)
    low = models.FloatField(default=0)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{} (Volume: {}, Exchange: {})".format(self.name,
                                                      self.volume,
                                                      self.exchange)

    class Meta:
        db_table = "markets"
        unique_together = (('name', 'exchange'))


class CurrencyFiatPrices(models.Model):
    """Model for current fiat prices per each symbol"""
    currency = models.CharField(unique=True, max_length=64)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    price = models.FloatField()

    class Meta:
        db_table = "currency_fiat_prices"
        unique_together = (('currency', 'exchange'))


class ExchangeStatus(models.Model):
    """Exchange status model - current status of the exchange data gather."""

    exchange = models.OneToOneField(Exchange, on_delete=models.CASCADE)
    last_run = models.DateTimeField(null=True)
    last_run_id = models.CharField(max_length=256, null=True)
    last_run_status = models.TextField(null=True)
    time_started = models.DateTimeField(null=True)
    running = models.BooleanField(blank=True, default=False)
    timeout = models.IntegerField(blank=True,
                                  default=settings.EXCHANGE_TIMEOUT)

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}(Running: {}; Last run: {})".format(self.exchange.name,
                                                      self.running,
                                                      self.last_run)

    class Meta():
        """Define the db table name."""
        db_table = "exchange_status"


class FiatMarketModel(InfluxModel):
    required_influx_tags = ["currency"]
    optional_influx_tags = ["exchange_id"]
    sorting_tags = ["_time"]
    fields = [
        {"name": "price", "type": float},
    ]
    measurement = settings.INFLUX_MEASUREMENT_FIAT_MARKETS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET


class AggregatedFiatMarketModel(InfluxModel):
    required_influx_tags = ["currency"]
    sorting_tags = ["_time"]
    fields = [
        {"name": "price", "type": float},
    ]
    measurement = settings.INFLUX_MEASUREMENT_FIAT_MARKETS
    bucket = settings.INFLUX_AGGREGATION_BUCKET


class PairsMarketModel(InfluxModel):
    required_influx_tags = ["base", "quote"]
    optional_influx_tags = ["symbol", "exchange_id", "ask", "bid", "open", "close", "high", "low"]
    sorting_tags = ["_time"]
    fields = [
        {"name": "last", "type": float}
    ]
    measurement = settings.INFLUX_MEASUREMENT_PAIRS
    bucket = settings.INFLUXDB_DEFAULT_BUCKET
