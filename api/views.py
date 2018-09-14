"""API views."""
import hashlib
import time
from rest_framework.viewsets import ModelViewSet, ViewSet, GenericViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import OrderingFilter
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

CACHE_TTL = getattr(settings, 'CACHE_TTL', 120)


def get_request_id(exchange_name):
    """Create a request ID using the exchange_name and current time."""
    to_hash = "{}{}".format(time.time(), exchange_name)
    request_id = hashlib.sha224(to_hash.encode('utf-8')).hexdigest()[:15]
    return request_id


class DaemonStatus(ViewSet):
    """Get the status of the marketmanager daemon."""

    def list(self, request):
        """Get the status of marketmanager daemon."""
        try:
            connection = (settings.MARKET_MANAGER_DAEMON_HOST,
                          settings.MARKET_MANAGER_DAEMON_PORT)
            client = Client(connection)
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
    def create(self, request, pk):
        host = request.META['HTTP_HOST']
        path = reverse("api:task_results-list")
        task_id = fetch_exchange_data.delay(pk)
        if task_id:
            output = "MarketManager has accepted exchange run. "
            output += "Task: http://{}{}?task_id={}".format(host, path,
                                                            task_id)
            return Response(output, status=status.HTTP_200_OK)
        else:
            msg = {"error":
                   "No task created in celery for exchange id: {}".format(pk)}
            return Response(msg, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangeViewSet(ModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = models.Exchange.objects.all()
    serializer_class = serializers.ExchangeSerializer
    filter_class = filters.ExchangeFilter

    @method_decorator(cache_page(CACHE_TTL))
    def dispatch(self, *args, **kwargs):
        return super(ExchangeViewSet, self).dispatch(*args, **kwargs)


class MarketViewSet(ModelViewSet):
    queryset = models.Market.objects.all()
    serializer_class = serializers.MarketSerializer
    filter_class = filters.MarketFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('name', 'source', 'volume', 'bid', 'ask', 'base')

    @method_decorator(cache_page(CACHE_TTL))
    def dispatch(self, *args, **kwargs):
        return super(MarketViewSet, self).dispatch(*args, **kwargs)


class ExchangeStatusViewSet(ModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = models.ExchangeStatus.objects.all()
    serializer_class = serializers.ExchangeStatusSerializer
    filter_class = filters.ExchangeStatusFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('name', 'volume', 'top_pair_volume', 'top_pair')


class TaskResults(GenericViewSet):
    queryset = TaskResult.objects.all()
    filter_class = filters.TaskResultFilter
    serializer_class = serializers.TaskResultSerializer
    filter_backends = (DjangoFilterBackend, )

    def list(self, request, *args, **kwargs):
        user_data = self.filter_queryset(queryset=self.queryset)
        page = self.paginate_queryset(user_data)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(user_data, many=True)
        return Response(serializer.data)
