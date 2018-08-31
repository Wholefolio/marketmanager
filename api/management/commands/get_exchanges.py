from django.core.management.base import BaseCommand
from django.conf import settings
import datetime
import requests

from api.models import Exchange, ExchangeStatus


class Command(BaseCommand):
    help = 'Get a list of the exchanges.'

    def add_arguments(self, parser):
        parser.add_argument('--available', action="store_true",
                            dest="available",
                            help="List all ccxt exchanges", required=False)
        parser.add_argument('--enabled', action="store_true", dest="enabled",
                            help="Get all enabled exchanges", required=False)
        parser.add_argument('--blocked', action="store_true", dest="blocked",
                            help="Get all blocked exchanges", required=False)

    def handle(self, *args, **options):
        if options["available"]:
            self.stdout.write("All Current CCXT Exchanges:")
            url = settings.COINER_URLS.get("available-exchanges")
            exchanges = requests.get(url).json().get("exchanges")
            self.stdout.write("\n".join(exchanges))
            return "Finished running through available exchanges."
        exchanges = Exchange.objects.all()
        if not exchanges:
            self.stdout.write("No exchanges configured")
            return
        if options["enabled"]:
            exchanges = Exchange.objects.filter(enabled=True)
        elif options["blocked"]:
            exchanges = Exchange.objects.filter(enabled=False)
        else:
            exchanges = Exchange.objects.all()
        for exchange in exchanges:
            msg = 'ID: {}, Name: {}, Interval: {}, Enabled: {}'.format(
                           exchange.id, exchange.name,
                           str(datetime.timedelta(seconds=exchange.interval)),
                           exchange.enabled)
            try:
                status = ExchangeStatus.objects.get(exchange=exchange)
                msg += ", Last run: {}, Running: {}".format(status.last_run,
                                                            status.running)
            except ExchangeStatus.DoesNotExist:
                pass
            self.stdout.write(self.style.SUCCESS(msg))
