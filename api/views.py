"""API views."""
import hashlib
import time
from rest_framework.viewsets import (ViewSet, ReadOnlyModelViewSet)
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import OrderingFilter, SearchFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django_celery_results.models import TaskResult
from django.urls import reverse

from applib.daemonclient import Client
from api import models
from api import serializers
from api import filters
from api.tasks import fetch_exchange_data
from django_influxdb.views import ListViewSet as InfluxListViewSet

CACHE_TTL = getattr(settings, 'CACHE_TTL', 120)


def get_request_id(base_name):
    """Create a request ID a base name and current time."""
    to_hash = "{}{}".format(time.time(), base_name)
    request_id = hashlib.sha224(to_hash.encode('utf-8')).hexdigest()[:15]
    return request_id


class DaemonStatus(ViewSet):
    """Get the status of the marketmanager daemon."""

    def list(self, request):
        """Get the status of marketmanager daemon."""
        try:
            addr = (settings.MARKET_MANAGER_DAEMON_HOST, int(settings.MARKET_MANAGER_DAEMON_PORT))
            client = Client(addr)
            client.connect()
            output = client.getStatus(get_request_id('status'))
            return Response(output, status=status.HTTP_200_OK)
        except ConnectionError:
            output = {"error": "Can't connect to MarketManager daemon."}
            return Response(output, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except FileNotFoundError:
            output = {"error": "Marketmanager socket file not found."}
            return Response(output, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangeRun(ViewSet):
    def create(self, request):
        host = request.META['HTTP_HOST']
        path = reverse("api:task_results-list")
        exchange_id = request.data.get("exchange_id")
        if not exchange_id:
            msg = {"error": "Missing exchange id"}
            return Response(msg, status=status.HTTP_400_BAD_REQUEST)
        task_id = fetch_exchange_data.delay(exchange_id)
        if task_id:
            response = "MarketManager has accepted exchange run. "
            response += "Task: http://{}{}?task_id={}".format(host, path, task_id)
            return Response(response, status=status.HTTP_200_OK)
        msg = {"error": "No task created for exchange id: {}".format(exchange_id)}
        return Response(msg, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangeViewSet(ReadOnlyModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = models.Exchange.objects.all()
    serializer_class = serializers.ExchangeSerializer
    filter_class = filters.ExchangeFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('name', 'volume', 'top_pair', 'top_pair_volume')

    @method_decorator(cache_page(CACHE_TTL))
    def dispatch(self, *args, **kwargs):
        return super(ExchangeViewSet, self).dispatch(*args, **kwargs)


class MarketViewSet(ReadOnlyModelViewSet):
    queryset = models.Market.objects.all()
    serializer_class = serializers.MarketSerializer
    filter_class = filters.MarketFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter, SearchFilter)
    search_fields = ['base', 'quote']
    ordering_fields = ('name', 'source', 'volume', 'bid', 'ask', 'base')

    @method_decorator(cache_page(CACHE_TTL))
    def dispatch(self, *args, **kwargs):
        return super(MarketViewSet, self).dispatch(*args, **kwargs)


class MarketHistoricalData(InfluxListViewSet):
    """Endpoint for market historical data from InfluxDB"""
    additional_filter_params = ["exchange_id", "time_end"]
    required_filter_params = ["base", "quote", "time_start"]
    sorting_tags = ["timestamp", "base", "quote"]
    influx_model = models.PairsMarketModel


class AggregatedFiatHistoricalData(InfluxListViewSet):
    """Endpoint for fiat historical data from InfluxDB"""
    additional_filter_params = ["time_end"]
    required_filter_params = ["currency", "time_start"]
    sorting_tags = ["timestamp"]
    influx_model = models.AggregatedFiatMarketModel


class ExchangeFiatHistoricalData(InfluxListViewSet):
    """Endpoint for fiat historical data from InfluxDB"""
    additional_filter_params = ["time_end", "exchange_id"]
    required_filter_params = ["currency", "time_start"]
    sorting_tags = ["timestamp"]
    influx_model = models.FiatMarketModel


class ExchangeStatusViewSet(ReadOnlyModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = models.ExchangeStatus.objects.all()
    serializer_class = serializers.ExchangeStatusSerializer
    filter_class = filters.ExchangeStatusFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('name', 'volume', 'top_pair_volume', 'top_pair')


class TaskResults(ReadOnlyModelViewSet):
    queryset = TaskResult.objects.all()
    filter_class = filters.TaskResultFilter
    serializer_class = serializers.TaskResultSerializer
    filter_backends = (DjangoFilterBackend, )
