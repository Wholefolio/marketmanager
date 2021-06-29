from django.core.management.base import BaseCommand
import datetime
import ccxt
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
            self.stdout.write("All Current CCXT Exchanges")
            self.stdout.write("\n".join(ccxt.exchanges))
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
            msg = 'ID: {}, Name: {}, Interval: {}, Enabled: {}, Fiat: {}'.format(
                           exchange.id, exchange.name,
                           str(datetime.timedelta(seconds=exchange.interval)),
                           exchange.enabled,
                           exchange.fiat_markets)
            try:
                status = ExchangeStatus.objects.get(exchange=exchange)
                msg += ", Last run: {}, Running: {}".format(status.last_run,
                                                            status.running)
            except ExchangeStatus.DoesNotExist:
                pass
            self.stdout.write(self.style.SUCCESS(msg))
