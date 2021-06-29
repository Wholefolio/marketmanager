import logging
from rest_framework.viewsets import ViewSet
from rest_framework.response import Response
from django.conf import settings

from marketmanager.influxdb import Client
from api.models import Exchange
logger = logging.getLogger("marketmanager")


class Health(ViewSet):
    def get(self, request):
        influx_client = Client()
        try:
            influx_client.query(settings.INFLUX_MEASUREMENT_PAIRS, "5s")
        except Exception as e:
            return Response({"error": f"Couldn't connect to InfluxDB. Exception: {e}"}, status=503)
        try:
            Exchange.objects.count()
        except Exception as e:
            return Response({"error": f"Couldn't connect to PostgreSQL. Exception: {e}"}, status=503)
        return Response({"status": "Service is OK"})
