"""Serializers module."""
from rest_framework import serializers
from .models import Exchange, ExchangeStatus, Market


class ExchangeSerializer(serializers.ModelSerializer):
    """Serializer to map the Model instance into JSON format."""

    class Meta:
        """Meta class to map serializer's fields with the model fields."""

        model = Exchange
        fields = ('id', 'name', 'created', 'updated', "url", "api_url",
                  "volume", "top_pair", "top_pair_volume", "interval",
                  "enabled", "last_updated")
        read_only_fields = ('created', 'updated')

    def get_type(self, obj):
        return obj.get_type_display()


class MarketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Market
        fields = ("id", "name", "exchange", "volume", "last", "bid", "ask",
                  "base", "quote")


class ExchangeStatusSerializer(serializers.ModelSerializer):
    """Serializer to map the Model instance into JSON format."""

    class Meta:
        """Meta class to map serializer's fields with the model fields."""

        model = ExchangeStatus
        fields = ('id', 'exchange', 'last_run', 'last_run_id',
                  'last_run_status', 'time_started', 'running')
