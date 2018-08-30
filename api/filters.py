from django.db import models as django_models
from django_filters import FilterSet, IsoDateTimeFilter
from api.models import Exchange, ExchangeStatus


class ExchangeFilter(FilterSet):
    """Django filters Exchange filter meta class."""

    class Meta:
        model = Exchange
        fields = {
            "name": ["exact"],
            "enabled": ["exact"],
            "last_updated": ["lte", "gte"],
            "volume": ["lte", "gte"],
            "interval": ["lte", "gte", "exact"],
            "created": ["lte", "gte"],
        }


class ExchangeStatusFilter(FilterSet):
    """Django filters ExchangeStatus filter meta class."""

    class Meta:
        model = ExchangeStatus
        fields = {
            "exchange": ["exact"],
            "running": ["exact"],
            "last_run": ["lte", "gte"],
            "time_started": ["lte", "gte"]
        }
    filter_overrides = {
            django_models.DateTimeField: {
                "filter_class": IsoDateTimeFilter
            }
    }
