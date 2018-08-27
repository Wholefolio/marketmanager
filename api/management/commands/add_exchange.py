from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
import ccxt
from api.models import Exchange
from applib.tools import appRequest
from marketmanager.settings import STORAGE_EXCHANGE_URL


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available ccxt exchanges and create\
                    sources for them in the storage APP."
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument("--name", action="store", dest="name",
                           help="source code file")
        group.add_argument("--all", action="store_true", dest="all",
                           help=all_help)
        parser.add_argument("--interval", action="store", dest="interval",
                            help="adapter interval", default=300)
        parser.add_argument("--exchange-id", action="store",
                            dest="exchange_id",
                            help="Storage app exchangeID.", required=False)

    def create_source(self, data):
        result = appRequest("post", STORAGE_EXCHANGE_URL, data)
        if not result:
            self.stderr.write("Failed to ")
            return False
        return result["id"]

    def create_all(self, interval):
        for exc in ccxt.exchanges:
            data = self.get_exchange_details(exc)
            name = exc.capitalize()
            exc = Exchange(name=name, interval=interval, **data)
            try:
                exc.save()
                self.stdout.write("Created exchange {}".format(name))
            except IntegrityError:
                self.stderr.write("Exchange {} already exists".format(name))

    def get_exchange_details(self, name):
        """Create the data dict with the exchange name, api url and www url."""
        exchange_object = getattr(ccxt, name)()
        if isinstance(exchange_object.urls['api'], dict):
            print(exchange_object.urls)
            if "public" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['public']
            elif "rest" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['rest']
            elif "current" in exchange_object.urls['api']:
                api_url = exchange_object.urls['api']['current']
        else:
            api_url = exchange_object.urls['api']
        url = exchange_object.urls['www']
        logo = exchange_object.urls['logo']
        return {"api_url": api_url, "url": url, "logo": logo}

    def handle(self, *args, **options):
        if options["all"]:
            return self.create_all(options["interval"])
        data = self.get_exchange_details(options["name"])
        exc = Exchange(name=options["name"], interval=options["interval"],
                       **data)
        exc.save()
        msg = "Exchange successfully created - {}".format(exc.id)
        self.stdout.write(self.style.SUCCESS(msg))
