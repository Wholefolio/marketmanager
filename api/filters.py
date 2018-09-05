from django.db import models as django_models
from django_filters import FilterSet, IsoDateTimeFilter
from api.models import Exchange, ExchangeStatus, Market


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


class MarketFilter(FilterSet):
    class Meta:
        model = Market
        fields = {
            "id": ["exact"],
            "exchange": ["exact"],
            "name": ["exact"],
            "base": ["exact"],
            "quote": ["exact"],
            "volume": ["lte", "gte"],
            "last": ["lte", "gte"],
            "bid": ["lte", "gte"],
            "ask": ["lte", "gte"]
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
