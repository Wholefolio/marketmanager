"""API models."""
from django.db import models


class Exchange(models.Model):
    """Adapters model that houses the created exchanges.

    Fields: name, created(UNIX timestmap), last(UNIX timestamp),
    storage_source_id - ID id of the entry in the storage app.
    """

    name = models.CharField(max_length=64, unique=True)
    enabled = models.BooleanField(default=True, blank=True)
    storage_source_id = models.IntegerField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    interval = models.IntegerField()

    def __str__(self):
        """Return a human readable representation of the model instance."""
        return "{}, Source: {}".format(self.name, self.storage_source_id)

    class Meta():
        """Define the db table name."""
        db_table = "exchanges"


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
