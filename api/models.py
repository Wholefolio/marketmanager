"""API models."""
from django.db import models


class Exchange(models.Model):
    """Adapters model that houses the created exchanges.

    Fields: name, created(UNIX timestmap), last(UNIX timestamp),
    storage_exchange_id - ID id of the exchange in the storage app.
    """
    name = models.CharField(max_length=64, unique=True)
    logo = models.CharField(max_length=256, null=True)
    url = models.CharField(max_length=128, null=True)
    api_url = models.CharField(max_length=128, null=True)
    volume = models.FloatField(null=True)
    top_pair = models.CharField(max_length=20, null=True)
    top_pair_volume = models.FloatField(null=True)

    last_updated = models.DateTimeField(null=True)
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
    name = models.CharField(max_length=24)
    base = models.CharField(max_length=10)
    quote = models.CharField(max_length=25)
    exchange = models.ForeignKey(Exchange, on_delete=models.CASCADE)
    volume = models.FloatField(null=True)
    last = models.FloatField()
    bid = models.FloatField()
    ask = models.FloatField()

    class Meta:
        db_table = "markets"
        unique_together = (('name', 'exchange'))


class ExchangeStatus(models.Model):
    """Adapter status model."""

    exchange = models.OneToOneField(Exchange, on_delete=models.CASCADE)
    last_run = models.DateTimeField(null=True)
    last_run_id = models.CharField(max_length=256, null=True)
    last_run_status = models.TextField(null=True)
    time_started = models.DateTimeField(null=True)
    running = models.BooleanField(blank=True, default=False)

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}(Running: {}; Last run: {})".format(self.exchange.name,
                                                      self.running,
                                                      self.last_run)

    class Meta():
        """Define the db table name."""
        db_table = "exchange_status"
