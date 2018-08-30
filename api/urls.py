"""URL configuration for the Scheduler API."""
from django.conf.urls import url
from rest_framework import routers
from . import views

app_name = "api"
router = routers.DefaultRouter()

router.register(r"exchanges", views.ExchangeViewSet)
router.register(r"exchange_statuses", views.ExchangeStatusViewSet)
router.register(r"daemon_status", views.DaemonStatus, base_name="daemonstatus")

urlpatterns = router.urls
urlpatterns.append(url(r'^exchanges/(?P<pk>[0-9]+)/run/',
                       views.ExchangeRun.as_view({'post': 'create'}),
                       name="adapter_run"))
