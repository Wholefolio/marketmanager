from rest_framework.viewsets import ViewSet
from rest_framework.response import Response


class Health(ViewSet):
    def get(self, request):
        return Response({"status": "Service is OK"})
