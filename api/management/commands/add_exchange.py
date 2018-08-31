from django.core.management.base import BaseCommand
from django.db.utils import IntegrityError
from django.conf import settings
import requests

from api.models import Exchange, ExchangeStatus


class Command(BaseCommand):
    help = "Add an exchange for scheduling(must be available in CCXT)."

    def add_arguments(self, parser):
        all_help = "This will add all available exchanges and create\
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

    def create_all(self, interval):
        url = settings.COINER_URLS.get("available-exchanges")
        exchanges = requests.get(url).json().get("exchanges")
        for exc in exchanges:
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
        url = "{}?name={}".format(settings.COINER_URLS.get("exchange-details"),
                                  name)
        return requests.get(url).json()

    def handle(self, *args, **options):
        if options["all"]:
            return self.create_all(options["interval"])
        data = self.get_exchange_details(options["name"])
        if "error" in data:
            return data["error"]
        exc = Exchange(name=options["name"], interval=options["interval"],
                       **data)
        exc.save()
        status = ExchangeStatus(exchnage=exc)
        status.save()
        msg = "Exchange successfully created - {}".format(exc.id)
        self.stdout.write(self.style.SUCCESS(msg))
