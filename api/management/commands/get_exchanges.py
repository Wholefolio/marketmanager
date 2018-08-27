from django.core.management.base import BaseCommand
from api.models import Exchange, ExchangeStatus

import datetime
import ccxt


class Command(BaseCommand):
    help = 'Get a list of the exchanges.'

    def add_arguments(self, parser):
        parser.add_argument('--available', action="store_true",
                            dest="available",
                            help="List all ccxt exchanges", required=False)

    def handle(self, *args, **options):
        if options["available"]:
            self.stdout.write("All Current CCXT Exchanges:")
            self.stdout.write("\n".join(ccxt.exchanges))
            return
        exchanges = Exchange.objects.all()
        if not exchanges:
            self.stdout.write("No exchanges configured")
            return
        for exchange in exchanges:
            status = ExchangeStatus.objects.get(exchange=exchange)
            msg = 'ID: {}, Name: {}, Interval: {}, Enabled: {}, '.format(
                           exchange.id, exchange.name,
                           str(datetime.timedelta(seconds=exchange.interval)),
                           exchange.enabled)
            msg += "Last run: {}, Running: {}".format(status.last_run,
                                                      status.running)
            self.stdout.write(self.style.SUCCESS(msg))
