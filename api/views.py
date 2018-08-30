"""API views."""
import hashlib
import time
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework import status
from rest_framework.filters import OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from django.conf import settings
from django.http import Http404

from applib.daemonclient import Client
from api.models import Exchange, ExchangeStatus
from api.serializers import ExchangeSerializer, ExchangeStatusSerializer
from api.filters import ExchangeFilter, ExchangeStatusFilter


def get_object(pk, exchange_name=None):
    """Get a exchange object given the ID."""
    try:
        if exchange_name:
            return Exchange.objects.get(name=exchange_name)
        return Exchange.objects.get(pk=pk)
    except Exchange.DoesNotExist:
        raise Http404


def get_request_id(exchange_name):
    """Create a request ID using the exchange_name and current time."""
    to_hash = "{}{}".format(time.time(), exchange_name)
    request_id = hashlib.sha224(to_hash.encode('utf-8')).hexdigest()[:15]
    return request_id


class DaemonStatus(ViewSet):
    """Get the status of the coiner daemon."""

    def list(self, request):
        """Get the status of coiner daemon."""
        try:
            client = Client(settings.MARKET_MANAGER_DAEMON['sock_file'])
            client.connect()
            output = client.getStatus(get_request_id('status'))
            return Response(output, status=status.HTTP_200_OK)
        except ConnectionError:
            output = "Can't connect to Coiner daemon."
            return Response(output, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except FileNotFoundError:
            output = "Marketmanager socket file not found."
            return Response(output, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangeRun(ViewSet):
    def create(self, request, pk):
        client = Client(settings.MARKET_MANAGER_DAEMON['sock_file'])
        client.connect()
        request = {"type": "exchange_run", "exchange_id": pk}
        output = client.sendRequest(request)
        if output:
            return Response(output, status=status.HTTP_200_OK)
        else:
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)


class ExchangeViewSet(ModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = Exchange.objects.all()
    serializer_class = ExchangeSerializer
    filter_class = ExchangeFilter


class ExchangeStatusViewSet(ModelViewSet):
    """Handle exchange creation, listing and deletion."""

    queryset = ExchangeStatus.objects.all()
    serializer_class = ExchangeStatusSerializer
    filter_class = ExchangeStatusFilter
    filter_backends = (DjangoFilterBackend, OrderingFilter)
    ordering_fields = ('name', 'volume', 'top_pair_volume', 'top_pair')
