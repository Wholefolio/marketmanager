import ccxt
from django.core.management.base import BaseCommand
from django.conf import settings
from api.models import Exchange, Market
from api.tasks import fetch_exchange_data


class Command(BaseCommand):
    help = "Run integration tests."

    def compare_missing_markets(self, markets, ccxt_markets):
        """Find which markets from CCXT are missing in our DB"""
        market_symbols = [x["name"] for x in markets.values()]
        for market in ccxt_markets:
            symbol = market["symbol"].replace("/", "-")
            if symbol not in market_symbols:
                self.stdout.write(self.style.WARNING(f"Missing market {market}"))

    def get_ccxt_markets(self, exchange):
        ccxt_exchange = getattr(ccxt, exchange.name.lower())()
        markets = ccxt_exchange.fetch_markets()
        return markets

    def handle(self, *args, **options):
        exchange_ids = []
        for exc in settings.ENABLED_EXCHANGES:
            try:
                obj = Exchange.objects.get(name=exc)
            except Exchange.DoesNotExist:
                obj = Exchange(name=exc, interval=settings.EXCHANGE_DEFAULT_FETCH_INTERVAL)
                obj.save()
            exchange_ids.append(obj)
        for current in exchange_ids:
            self.stdout.write(f"Running fetch for exchange {current.name}")
            try:
                fetch_exchange_data(current.id)
            except ValueError as e:
                self.stdout.write(self.style.ERROR(e))
                continue
            markets = Market.objects.filter(exchange=current)
            assert markets.count() > 0
            ccxt_markets = self.get_ccxt_markets(current)
            if len(ccxt_markets) != markets.count():
                msg = "Mismatch in count between ccxt markets and DB markets."
                msg += "CCXT: {}, Our: {}".format(len(ccxt_markets), markets.count())
                self.stdout.write(self.style.WARNING(msg))
                self.compare_missing_markets(markets, ccxt_markets)
            self.stdout.write(self.style.SUCCESS(f"Finished fetch for exchange {current.name}"))
