"""marketmanager URL Configuration."""
import os
from django.conf.urls import url, include
from rest_framework.documentation import include_docs_urls

from marketmanager.healthcheck import Health


urlpatterns = [
    url(r'^healthz/',  Health.as_view({"get": "get"})),
    url(r'^', include('api.urls', namespace="api")),
]
PY_ENV = os.environ.get('PY_ENV', "dev")
if PY_ENV == "dev":
    urlpatterns.append(url(r'^docs/',
                           include_docs_urls(title='MarketManager API')))
