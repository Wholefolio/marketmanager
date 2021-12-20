from django.core.management.base import BaseCommand
import ccxt
import json
from api.models import Exchange, ExchangeStatus
from api.serializers import ExchangeSerializer


class Command(BaseCommand):
    help = 'Get a list of the exchanges.'

    def add_arguments(self, parser):
        parser.add_argument('--available', action="store_true",
                            dest="available",
                            help="List all ccxt exchanges", required=False)
        parser.add_argument('--enabled', action="store_true", dest="enabled",
                            help="Get all enabled exchanges", required=False)
        parser.add_argument('--disabled', action="store_true", dest="disabled",
                            help="Get all disabled exchanges", required=False)
        parser.add_argument('--json', action="store_true", dest="json",
                            help="Output the exchanges to JSON")

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
        elif options["disabled"]:
            exchanges = Exchange.objects.filter(enabled=False)
        else:
            exchanges = Exchange.objects.all()
        if options['json']:
            serializer = ExchangeSerializer(exchanges, many=True)
            self.stdout.write(self.style.SUCCESS(json.dumps(serializer.data, indent=4)))
            return
        for exchange in exchanges:
            msg = f'ID: {exchange.id}, Name: {exchange.name}, Interval: {exchange.interval},\
Enabled: {exchange.enabled}, Fiat: {exchange.fiat_markets}'
            try:
                status = ExchangeStatus.objects.get(exchange=exchange)
                msg += f", Last run: {exchange.updated}, Running: {status.running}"
            except ExchangeStatus.DoesNotExist:
                pass
            self.stdout.write(self.style.SUCCESS(msg))
