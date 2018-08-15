"""URL configuration for the Scheduler API."""
from django.conf.urls import url
from rest_framework import routers
from . import views

router = routers.DefaultRouter()

router.register(r"adapters", views.ExchangeViewSet)
router.register(r"adapter_statuses", views.ExchangeStatusViewSet)
router.register(r"statuses", views.DaemonStatus, base_name="status")

urlpatterns = router.urls
urlpatterns.append(url(r'^adapters/(?P<pk>[0-9]+)/run/',
                       views.ExchangeRun.as_view({'post': 'create'}),
                       name="adapter_run"))
