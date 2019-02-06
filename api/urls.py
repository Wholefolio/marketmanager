"""URL configuration for the Scheduler API."""
from rest_framework import routers
from . import views

app_name = "api"
router = routers.DefaultRouter()

router.register(r"exchanges", views.ExchangeViewSet)
router.register(r"exchange_statuses", views.ExchangeStatusViewSet)
router.register(r"markets", views.MarketViewSet)
router.register(r"daemon_status", views.DaemonStatus, base_name="daemonstatus")
router.register(r"task_results", views.TaskResults, base_name="task_results")
router.register(r"run_exchange", views.ExchangeRun, base_name="run_exchange")

urlpatterns = router.urls
